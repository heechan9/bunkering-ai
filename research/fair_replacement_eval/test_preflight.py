"""Tests for the pre-evaluation validation (no training, no episode is run)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.dqn import CHECKPOINT_FORMAT_VERSION, DQNAgent  # noqa: E402
from envs.bunkering_env import BunkeringEnv  # noqa: E402
from research.fair_replacement_eval import common, evaluate, preflight  # noqa: E402

ENV = {"n_ports": 3, "max_steps": 30, "min_safe_fuel": 0.15}
AGENT_CONFIG = {"network": {"hidden_dims": [8, 8]}, "train": {"learning_rate": 1e-3, "gamma": 0.99}}


@pytest.fixture(scope="module")
def crit():
    return common.load_criteria()


@pytest.fixture
def seeds(crit):
    """Seeds of the currently designated confirmation and reuse sets, from criteria.json."""
    sets = crit["evaluation_sets"]
    conf = [int(sets["confirmation"]["base_seed"]) + i for i in range(int(sets["confirmation"]["episodes"]))]
    reuse = [int(sets["reuse"]["base_seed"]) + i for i in range(int(sets["reuse"]["episodes"]))]
    return conf, reuse


def make_checkpoint(path: Path, metadata, *, env_config=ENV, state_dim=None, action_dim=None) -> Path:
    env = BunkeringEnv(**ENV)
    agent = DQNAgent(
        state_dim or env.observation_space.shape[0], action_dim or env.action_space.n, AGENT_CONFIG
    )
    agent.save_checkpoint(path, metadata=metadata)
    return path


def good_meta(**overrides):
    meta = {"train_seed": 42, "n_episodes": 5000, "env_config": dict(ENV)}
    meta.update(overrides)
    return {k: v for k, v in meta.items() if v is not Ellipsis}


def run(tmp_path, crit, seeds, metadata, **kwargs):
    ckpt = make_checkpoint(tmp_path / "m.pt", metadata, **kwargs)
    conf, reuse = seeds
    return preflight.run_preflight(ckpt, crit, ENV, conf, reuse)


def status(result, check_id):
    return next(c for c in result["checks"] if c["id"] == check_id)


# ------------------------------------------------------------------ normal input


def test_valid_input_passes_every_check(tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, good_meta())
    assert result["overall"] == preflight.PASS, result
    gates = preflight.gate_values(result)
    assert all(gates.values())
    # A surrogate is allowed but labelled: sha is informational, never a pass/fail input.
    sha = status(result, "checkpoint_sha256")
    assert sha["status"] == preflight.INFO and sha["official"] is False
    # Reuse seeds (42..141) overlapping the training range is expected and only recorded.
    seed_check = status(result, "seed_ranges")
    assert seed_check["reuse_overlaps_training_seeds"] is True
    assert seed_check["confirmation_overlaps_training_seeds"] is False


def test_checkpoint_format_constant_matches_agent():
    assert preflight.CHECKPOINT_FORMAT_VERSION == CHECKPOINT_FORMAT_VERSION


# ---------------------------------------------------------- missing / invalid seeds


def test_missing_n_episodes_is_not_treated_as_zero(tmp_path, crit, seeds):
    """Regression: evaluate.py used meta.get('n_episodes', 0), which made the overlap check pass."""
    result = run(tmp_path, crit, seeds, good_meta(n_episodes=Ellipsis))
    meta_check = status(result, "training_seed_metadata")
    assert meta_check["status"] == preflight.UNDECIDABLE
    assert any("n_episodes missing" in r for r in meta_check["reasons"])
    seed_check = status(result, "seed_ranges")
    assert seed_check["status"] == preflight.UNDECIDABLE
    assert seed_check["confirmation_overlaps_training_seeds"] is None  # not False
    assert result["overall"] == preflight.UNDECIDABLE
    gates = preflight.gate_values(result)
    assert gates["G2_holdout_disjoint"] is False and gates["G0_preflight"] is False


def test_missing_train_seed_is_undecidable(tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, good_meta(train_seed=Ellipsis))
    assert status(result, "training_seed_metadata")["status"] == preflight.UNDECIDABLE
    assert any("train_seed missing" in r for r in status(result, "training_seed_metadata")["reasons"])
    assert preflight.gate_values(result)["G2_holdout_disjoint"] is False


def test_missing_metadata_entirely_is_undecidable(tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, {})
    assert status(result, "training_seed_metadata")["status"] == preflight.UNDECIDABLE
    assert status(result, "env_config")["status"] == preflight.UNDECIDABLE
    assert result["overall"] == preflight.UNDECIDABLE


@pytest.mark.parametrize("bad", [-1, "42", 4.0, True, None])
def test_invalid_train_seed(bad, tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, good_meta(train_seed=bad))
    assert status(result, "training_seed_metadata")["status"] == preflight.UNDECIDABLE
    assert preflight.gate_values(result)["G2_holdout_disjoint"] is False


@pytest.mark.parametrize("bad", [0, -3, "5", 5.5, True, None])
def test_invalid_n_episodes(bad, tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, good_meta(n_episodes=bad))
    assert status(result, "training_seed_metadata")["status"] == preflight.UNDECIDABLE
    assert status(result, "seed_ranges")["confirmation_overlaps_training_seeds"] is None
    assert preflight.gate_values(result)["G2_holdout_disjoint"] is False


def test_training_seed_range_helper():
    assert preflight.training_seed_range({"train_seed": 42, "n_episodes": 5000}) == ((42, 5041), [])
    rng, reasons = preflight.training_seed_range({"train_seed": 42})
    assert rng is None and reasons


# ------------------------------------------------------------------ environment


def test_missing_env_config_is_undecidable(tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, good_meta(env_config=Ellipsis))
    env_check = status(result, "env_config")
    assert env_check["status"] == preflight.UNDECIDABLE
    assert "metadata.env_config missing" in env_check["reasons"][0]
    assert preflight.gate_values(result)["G0_preflight"] is False


@pytest.mark.parametrize(
    "field,value",
    [("max_steps", 25), ("min_safe_fuel", 0.2), ("n_ports", 2), ("fuel_consumption_per_step", 0.06)],
)
def test_env_mismatch_fails_and_names_the_field(field, value, tmp_path, crit, seeds):
    env_meta = {**ENV, field: value}
    result = run(tmp_path, crit, seeds, good_meta(env_config=env_meta))
    env_check = status(result, "env_config")
    assert env_check["status"] == preflight.FAIL
    assert [m["field"] for m in env_check["mismatches"]] == [field]
    assert result["overall"] == preflight.FAIL


def test_env_key_absent_on_one_side_resolves_to_default():
    ok = preflight.check_env_config({"env_config": {**ENV, "fuel_consumption_per_step": 0.05}}, ENV)
    assert ok["status"] == preflight.PASS
    bad = preflight.check_env_config({"env_config": ENV}, {**ENV, "fuel_consumption_per_step": 0.07})
    assert bad["status"] == preflight.FAIL


def test_unknown_env_field_fails():
    result = preflight.check_env_config({"env_config": {**ENV, "bogus": 1}}, ENV)
    assert result["status"] == preflight.FAIL and result["unknown_fields"] == ["bogus"]


# ------------------------------------------------------------------------ seeds


def test_confirmation_overlapping_training_range_fails(tmp_path, crit, seeds):
    conf, _ = seeds
    meta = good_meta(train_seed=conf[0] - 10, n_episodes=100)
    result = run(tmp_path, crit, seeds, meta)
    seed_check = status(result, "seed_ranges")
    assert seed_check["status"] == preflight.FAIL
    assert seed_check["confirmation_overlaps_training_seeds"] is True
    assert preflight.gate_values(result)["G2_holdout_disjoint"] is False
    assert result["overall"] == preflight.FAIL


def test_training_range_ending_just_before_confirmation_passes(tmp_path, crit, seeds):
    conf, _ = seeds
    meta = good_meta(train_seed=conf[0] - 100, n_episodes=100)  # last training seed = conf[0] - 1
    assert status(run(tmp_path, crit, seeds, meta), "seed_ranges")["status"] == preflight.PASS


def test_confirmation_seeds_hitting_used_range_fail(tmp_path, crit, seeds):
    _, reuse = seeds
    used = crit["evaluation_sets"]["seed_ranges_already_used"][0]["range"][0]
    hits = [used + i for i in range(1000)]
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    result = preflight.run_preflight(ckpt, crit, ENV, hits, reuse)
    assert status(result, "seed_ranges")["status"] == preflight.FAIL


def test_confirmation_intersecting_reuse_fails(tmp_path, crit, seeds):
    _, reuse = seeds
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    result = preflight.run_preflight(ckpt, crit, ENV, reuse, reuse)
    assert status(result, "seed_ranges")["status"] == preflight.FAIL


@pytest.mark.parametrize("bad", [[], [-1, 0], [1.5, 2.5]])
def test_malformed_seed_list_fails(bad, crit, seeds):
    _, reuse = seeds
    assert preflight.check_seed_ranges(crit, good_meta(), bad, reuse)["status"] == preflight.FAIL


def test_every_used_range_is_detected(crit):
    for lo, hi in preflight.used_ranges(crit):
        assert preflight.hits_used_ranges([lo], crit) and preflight.hits_used_ranges([hi], crit)


# ---------------------------------------------------------- checkpoint / criteria


def test_wrong_dimensions_fail(tmp_path, crit, seeds):
    result = run(tmp_path, crit, seeds, good_meta(), state_dim=5)
    dims = status(result, "checkpoint_dimensions")
    assert dims["status"] == preflight.FAIL and dims["checkpoint"][0] == 5
    assert result["overall"] == preflight.FAIL


def test_wrong_format_version_fails(tmp_path, crit, seeds):
    env = BunkeringEnv(**ENV)
    payload = {
        "format_version": 99, "state_dim": 6, "action_dim": int(env.action_space.n),
        "config": {}, "policy_net": {}, "target_net": {}, "metadata": good_meta(),
    }
    conf, reuse = seeds
    result = preflight.run_preflight(tmp_path / "x.pt", crit, ENV, conf, reuse, payload=payload, sha256="0" * 64)
    assert status(result, "checkpoint_format")["status"] == preflight.FAIL


def test_unreadable_checkpoint_fails(tmp_path, crit, seeds):
    bad = tmp_path / "bad.pt"
    bad.write_bytes(b"not a checkpoint")
    conf, reuse = seeds
    result = preflight.run_preflight(bad, crit, ENV, conf, reuse)
    assert status(result, "checkpoint_format")["status"] == preflight.FAIL
    assert result["overall"] == preflight.FAIL


def test_official_sha_is_recognised(crit, seeds):
    official = crit["incumbent"]["official_checkpoint_sha256"]
    entry = preflight.check_checkpoint(
        {"format_version": 1, "state_dim": 6, "action_dim": 4, "config": {}, "policy_net": {}, "target_net": {}},
        official, official, ENV,
    )[0]
    assert entry["official"] is True and entry["reasons"] == []


def test_tampered_criteria_fails_hash_check(tmp_path, monkeypatch):
    criteria = tmp_path / "criteria.json"
    shutil.copy(common.CRITERIA_PATH, criteria)
    shutil.copy(common.CRITERIA_HASH_PATH, tmp_path / "criteria.sha256")
    monkeypatch.setattr(common, "CRITERIA_PATH", criteria)
    monkeypatch.setattr(common, "CRITERIA_HASH_PATH", tmp_path / "criteria.sha256")
    ok, loaded = preflight.check_criteria_hash(common.load_criteria)
    assert ok["status"] == preflight.PASS and loaded is not None
    criteria.write_bytes(criteria.read_bytes() + b" ")
    bad, loaded = preflight.check_criteria_hash(common.load_criteria)
    assert bad["status"] == preflight.FAIL and loaded is None


def test_overall_status_ordering():
    assert preflight.overall_status([{"status": "info"}, {"status": "pass"}]) == "pass"
    assert preflight.overall_status([{"status": "undecidable"}, {"status": "pass"}]) == "undecidable"
    assert preflight.overall_status([{"status": "undecidable"}, {"status": "fail"}]) == "fail"


# ------------------------------------------------------------ evaluate.py wiring


def _main(tmp_path, metadata, extra=()):
    ckpt = make_checkpoint(tmp_path / "m.pt", metadata)
    out = tmp_path / "out"
    code = evaluate.main(["--checkpoint", str(ckpt), "--out", str(out), "--smoke", *extra])
    return code, out


def test_main_stops_before_any_episode_when_undecidable(tmp_path):
    code, out = _main(tmp_path, good_meta(n_episodes=Ellipsis))
    assert code == 3
    assert not (out / "episodes").exists() and not (out / "summary.json").exists()
    record = json.loads((out / "preflight.json").read_text(encoding="utf-8"))
    assert record["overall"] == preflight.UNDECIDABLE
    assert any("n_episodes missing" in r for c in record["checks"] for r in c["reasons"])


def test_main_stops_before_any_episode_on_env_mismatch(tmp_path):
    code, out = _main(tmp_path, good_meta(env_config={**ENV, "max_steps": 20}))
    assert code == 3
    assert not (out / "episodes").exists()
    assert json.loads((out / "preflight.json").read_text(encoding="utf-8"))["overall"] == preflight.FAIL


@pytest.mark.parametrize(
    "case",
    ["missing_train_seed", "missing_n_episodes", "invalid_n_episodes", "missing_env_config", "env_mismatch", "train_eval_seed_overlap"],
)
def test_main_never_starts_workers_for_blocked_input(case, tmp_path, monkeypatch, crit):
    """Entry-path check: evaluate.main must stop before run_jobs (where worker processes start)."""
    conf0 = int(crit["evaluation_sets"]["confirmation"]["base_seed"])
    metas = {
        "missing_train_seed": good_meta(train_seed=Ellipsis),
        "missing_n_episodes": good_meta(n_episodes=Ellipsis),
        "invalid_n_episodes": good_meta(n_episodes=-5),
        "missing_env_config": good_meta(env_config=Ellipsis),
        "env_mismatch": good_meta(env_config={**ENV, "min_safe_fuel": 0.3}),
        "train_eval_seed_overlap": good_meta(train_seed=conf0 - 5, n_episodes=100),
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("run_jobs (worker start) reached despite failed pre-flight")

    monkeypatch.setattr(evaluate, "run_jobs", forbidden)
    code, out = _main(tmp_path, metas[case])
    assert code == 3
    assert not (out / "episodes").exists() and not (out / "summary.json").exists()
    assert (out / "preflight.json").is_file()


@pytest.mark.parametrize("case", ["missing", "directory", "corrupt", "permission"])
@pytest.mark.parametrize("continue_undecidable", [False, True])
def test_main_records_checkpoint_read_failure_before_workers(
    case, continue_undecidable, tmp_path, monkeypatch
):
    checkpoint = tmp_path / "checkpoint.pt"
    expected_error = {"missing": "FileNotFoundError", "directory": "IsADirectoryError",
                      "permission": "PermissionError"}.get(case)
    if case == "directory":
        checkpoint.mkdir()
    elif case == "corrupt":
        checkpoint.write_bytes(b"not a checkpoint")
    elif case == "permission":
        checkpoint.write_bytes(b"unreadable")
        original_hash = evaluate.file_sha256

        def denied(path):
            if path == checkpoint:
                raise PermissionError("checkpoint access denied")
            return original_hash(path)

        monkeypatch.setattr(evaluate, "file_sha256", denied)

    def forbidden(*args, **kwargs):
        raise AssertionError("workers started after checkpoint failure")

    monkeypatch.setattr(evaluate, "run_jobs", forbidden)
    out = tmp_path / "out"
    args = ["--checkpoint", str(checkpoint), "--out", str(out), "--smoke"]
    if continue_undecidable:
        args.append("--continue-undecidable")
    assert evaluate.main(args) == 3
    record = json.loads((out / "preflight.json").read_text())
    assert record["overall"] == preflight.FAIL
    if expected_error:
        assert expected_error in " ".join(status(record, "checkpoint_file")["reasons"])
    else:
        assert status(record, "checkpoint_format")["status"] == preflight.FAIL
    assert not (out / "episodes").exists()
    assert not (out / "summary.json").exists()
