"""Tests for the shadow-mode recommendation comparison (no training, no official checkpoint)."""

from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.fair_replacement_eval import common, shadow  # noqa: E402
from research.fair_replacement_eval.policies import make_planners  # noqa: E402
from research.fair_replacement_eval.test_preflight import ENV, good_meta, make_checkpoint  # noqa: E402

LEGS = ENV["max_steps"]
SEEDS = [60_000_000, 60_000_001, 60_000_002]


class ScriptedDQN:
    """Deterministic stand-in for the DQN: buys on a fixed schedule; records what it was asked."""

    name = "scripted_dqn"

    def __init__(self, buy_steps=(0, 9, 19)):
        self.buy_steps = set(buy_steps)
        self.calls = []

    def select_action(self, env, observation, step_index):
        self.calls.append((step_index, float(observation[3])))
        return 2 if step_index in self.buy_steps else 0  # action 2 = refill at another port


class FixedPlanner:
    name = "fixed_planner"

    def __init__(self, action):
        self.action = action

    def select_action(self, env, observation, step_index):
        return self.action


class RaisingPlanner:
    name = "raising_planner"

    def select_action(self, env, observation, step_index):
        raise RuntimeError("planner exploded")


class FlakyPlanner:
    name = "flaky_planner"

    def select_action(self, env, observation, step_index):
        if step_index == 5:
            raise ValueError("bad step")
        return 0


def episode(primary, planner, seed=SEEDS[0], enabled=True):
    return shadow.run_shadow_episode(primary, planner, seed, dict(ENV), enabled=enabled)


def baseline_row(primary, seed=SEEDS[0]):
    """The unmodified evaluation loop with no shadow wrapper at all."""
    return common.run_episode(primary, seed, dict(ENV), "shadow", timed=False).row()


# ---------------------------------------------------------------------- normal


def test_normal_run_records_every_step_with_real_planner():
    primary = ScriptedDQN()
    row, recs = episode(primary, make_planners([0.0], {})["planner_ops"])
    assert [r["step"] for r in recs] == list(range(LEGS))
    assert all(r["planner_status"] == "ok" and r["planner_action"] in (0, 1) for r in recs)
    assert all(set(r) >= set(shadow.STEP_FIELDS) for r in recs)
    assert all(r["dqn_ns"] > 0 and r["planner_ns"] > 0 for r in recs)
    assert [r["dqn_action"] for r in recs] == [2 if s in (0, 9, 19) else 0 for s in range(LEGS)]
    assert row["end_reason"] in ("arrived", "fuel_depleted")


def test_dqn_action_is_exactly_what_was_applied():
    primary = ScriptedDQN()
    _, recs = episode(primary, FixedPlanner(1))
    assert [r["dqn_action"] for r in recs] == [2 if s in primary.buy_steps else 0 for s in range(LEGS)]
    # the DQN saw the real observation of the voyage, in order, once per step
    assert [c[0] for c in primary.calls] == list(range(LEGS))


# ------------------------------------------------------------------- disagreement


def test_disagreement_is_recorded_both_raw_and_buy_vs_wait():
    # Planner always recommends refilling at port 1; the DQN buys (action 2) on 3 steps.
    _, recs = episode(ScriptedDQN(), FixedPlanner(1))
    buy_agree = [r for r in recs if r["dqn_action"] == 2]
    assert all(r["disagree_raw"] == 1 and r["disagree_buy"] == 0 for r in buy_agree)  # 1 vs 2: same refill
    wait = [r for r in recs if r["dqn_action"] == 0]
    assert all(r["disagree_raw"] == 1 and r["disagree_buy"] == 1 for r in wait)
    summary = shadow.summarize(recs, [baseline_row(ScriptedDQN())])
    assert summary["disagreement_buy_vs_wait"]["count"] == LEGS - 3
    assert summary["disagreement_raw"]["count"] == LEGS
    assert summary["episodes_with_any_disagreement"] == 1


def test_agreement_when_planner_matches():
    _, recs = episode(ScriptedDQN(), type("Mirror", (), {"select_action": lambda self, e, o, s: 1 if s in (0, 9, 19) else 0})())
    assert all(r["disagree_buy"] == 0 for r in recs)


# ---------------------------------------------------------------- planner failure


def test_planner_exception_is_recorded_and_dqn_run_is_unchanged():
    primary = ScriptedDQN()
    row, recs = episode(primary, RaisingPlanner())
    assert len(recs) == LEGS
    assert all(r["planner_status"] == "error" and r["planner_action"] is None for r in recs)
    assert all(r["disagree_raw"] is None and r["disagree_buy"] is None for r in recs)
    assert "RuntimeError: planner exploded" in recs[0]["planner_error"]
    assert shadow.outcome(row) == shadow.outcome(baseline_row(ScriptedDQN()))


def test_single_failing_step_does_not_stop_later_steps():
    row, recs = episode(ScriptedDQN(), FlakyPlanner())
    statuses = [r["planner_status"] for r in recs]
    assert statuses.count("error") == 1 and statuses[5] == "error" and len(recs) == LEGS
    assert shadow.outcome(row) == shadow.outcome(baseline_row(ScriptedDQN()))


@pytest.mark.parametrize("bad", [99, -1, "1", 1.5, True, None, np.array([1])])
def test_invalid_planner_action_is_recorded_not_applied(bad):
    row, recs = episode(ScriptedDQN(), FixedPlanner(bad))
    assert all(r["planner_status"] == "invalid_action" and r["planner_action"] is None for r in recs)
    assert all(r["disagree_raw"] is None for r in recs)
    assert shadow.outcome(row) == shadow.outcome(baseline_row(ScriptedDQN()))


def test_failures_are_excluded_from_disagreement_rates():
    _, recs = episode(ScriptedDQN(), FlakyPlanner())
    summary = shadow.summarize(recs, [baseline_row(ScriptedDQN())])
    assert summary["planner_error_steps"] == 1 and summary["planner_ok_steps"] == LEGS - 1
    assert summary["disagreement_raw"]["rate_of_valid_recommendations"] == summary["disagreement_raw"]["count"] / (LEGS - 1)
    assert summary["planner_failure_kinds"] == {"ValueError": 1}


# ---------------------------------------------------------------------- isolation


def test_planner_cannot_see_or_change_the_live_environment():
    seen = {}

    class Probe:
        def select_action(self, env, observation, step_index):
            seen["env_type"] = type(env).__name__
            seen["attrs"] = sorted(a for a in vars(env))
            env.step(1)  # would advance the real environment if it were reachable
            return 0

    row, recs = episode(ScriptedDQN(), Probe())
    assert seen["attrs"] == ["max_steps", "min_safe_fuel"]  # nothing but the two constants
    assert all(r["planner_status"] == "error" and "AttributeError" in r["planner_error"] for r in recs)
    assert shadow.outcome(row) == shadow.outcome(baseline_row(ScriptedDQN()))


def test_planner_cannot_modify_the_observation_given_to_the_dqn():
    class Writer:
        def select_action(self, env, observation, step_index):
            observation[3] = 0.0
            return 0

    primary = ScriptedDQN()
    row, recs = episode(primary, Writer())
    assert all("ValueError" in r["planner_error"] for r in recs)  # read-only copy
    reference = ScriptedDQN()
    baseline_row(reference)
    assert primary.calls == reference.calls  # the DQN saw identical observations
    assert shadow.outcome(row) == shadow.outcome(baseline_row(ScriptedDQN()))


def test_global_random_state_is_restored_after_the_planner():
    class Noisy:
        def select_action(self, env, observation, step_index):
            random.random()
            np.random.rand(7)
            return 0

    random.seed(123)
    np.random.seed(123)
    expected = (random.random(), float(np.random.rand()))
    random.seed(123)
    np.random.seed(123)
    ShadowPolicy = shadow.ShadowPolicy(ScriptedDQN(), Noisy())
    ShadowPolicy.begin_episode(1)
    env = type("E", (), {"action_space": type("S", (), {"n": 4})(), "max_steps": LEGS, "min_safe_fuel": 0.15})()
    ShadowPolicy.select_action(env, np.zeros(6), 0)
    assert (random.random(), float(np.random.rand())) == expected
    assert ShadowPolicy.records[0]["planner_status"] == "ok"


def test_shadow_on_and_off_give_identical_dqn_voyages_with_a_real_checkpoint(tmp_path):
    from scripts.evaluate import load_dqn_policy

    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    dqn = load_dqn_policy(ckpt, dict(ENV))
    planner = make_planners([0.0], {})["planner_ops"]
    result = shadow.run_shadow(dqn, lambda: planner, SEEDS, dict(ENV), isolation_check=True)
    assert result["isolation_check"]["identical"] is True
    assert result["isolation_check"]["compared_episodes"] == len(SEEDS)
    for ep in result["episodes"]:
        plain = common.run_episode(dqn, ep["seed"], dict(ENV), "shadow", timed=False).row()
        assert shadow.outcome(ep) == shadow.outcome(plain)
    # Episode length varies (an untrained network may let fuel run out), so count per episode.
    assert len(result["steps"]) == sum(ep["shadow_steps"] for ep in result["episodes"])
    for ep in result["episodes"]:
        steps = [r["step"] for r in result["steps"] if r["seed"] == ep["seed"]]
        assert steps == list(range(ep["shadow_steps"])) and steps


def test_isolation_check_detects_a_difference():
    class Leaky:
        """A (wrongly written) wrapper target whose behaviour changes when the shadow is on."""

        name = "leaky"
        shadow_calls = 0

        def select_action(self, env, observation, step_index):
            return 2 if Leaky.shadow_calls > 40 else 0

    class Counting:
        def select_action(self, env, observation, step_index):
            Leaky.shadow_calls += 1
            return 0

    Leaky.shadow_calls = 0
    result = shadow.run_shadow(Leaky(), Counting, SEEDS, dict(ENV), isolation_check=True)
    assert result["isolation_check"]["identical"] is False and result["isolation_check"]["mismatching_seeds"]


def test_disabled_shadow_records_nothing_and_matches_unwrapped_loop():
    row, recs = episode(ScriptedDQN(), RaisingPlanner(), enabled=False)
    assert recs == []
    assert shadow.outcome(row) == shadow.outcome(baseline_row(ScriptedDQN()))


# --------------------------------------------------------------------------- CLI


def run_cli(tmp_path, metadata, extra=()):
    ckpt = make_checkpoint(tmp_path / "m.pt", metadata)
    out = tmp_path / "out"
    code = shadow.main(["--checkpoint", str(ckpt), "--out", str(out), "--seeds", "60000000:60000002", *extra])
    return code, out


def test_cli_writes_records_and_states_no_performance_claim(tmp_path):
    code, out = run_cli(tmp_path, good_meta())
    assert code == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["mode"] == shadow.MODE and summary["planner_performance_measured"] is False
    assert "No cost or safety performance" in summary["claim"]
    assert summary["isolation_check"]["identical"] is True
    with gzip.open(out / "shadow_steps.csv.gz", "rt", encoding="utf-8") as handle:
        n_rows = sum(1 for _ in handle) - 1
    assert summary["steps"] == n_rows and 3 <= n_rows <= 3 * LEGS and summary["episodes"] == 3
    assert summary["planner_error_steps"] == 0
    assert summary["latency_planner"]["p99_ms"] is not None and summary["latency_dqn"]["p99_ms"] is not None
    assert summary["seeds"]["overlaps_training_seeds"] is False
    # no planner cost/safety metrics anywhere in the summary
    assert not any(k in summary for k in ("planner_cost", "planner_safe_arrival", "verdict", "gates"))
    with gzip.open(out / "shadow_steps.csv.gz", "rt", encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    assert header == shadow.STEP_FIELDS
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files_sha256"]) == {"shadow_steps.csv.gz", "dqn_episodes.csv.gz"}
    assert common.file_sha256(out / "shadow_steps.csv.gz") == manifest["files_sha256"]["shadow_steps.csv.gz"]


def test_cli_blocks_environment_mismatch_before_any_episode(tmp_path):
    code, out = run_cli(tmp_path, good_meta(env_config={**ENV, "max_steps": 20}))
    assert code == 3
    assert not (out / "shadow_steps.csv.gz").exists() and not (out / "summary.json").exists()
    assert json.loads((out / "preflight.json").read_text(encoding="utf-8"))["overall"] == "fail"


def test_cli_runs_but_flags_missing_training_seed_metadata(tmp_path):
    code, out = run_cli(tmp_path, good_meta(n_episodes=Ellipsis))
    assert code == 0  # shadow results never feed a decision; the gap is recorded, not hidden
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["preflight"]["overall"] == "undecidable"
    assert summary["seeds"]["overlaps_training_seeds"] is None


def test_cli_refuses_non_empty_output_directory(tmp_path):
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("x", encoding="utf-8")
    assert shadow.main(["--checkpoint", str(ckpt), "--out", str(out), "--seeds", "1:2"]) == 2


def test_cli_rejects_non_same_observation_planner(tmp_path):
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    with pytest.raises(SystemExit):
        shadow.main(["--checkpoint", str(ckpt), "--out", str(tmp_path / "o"), "--seeds", "1:2", "--planner", "planner_oracle"])


@pytest.mark.parametrize("text", ["5:1", "-1:3", "abc", "1"])
def test_seed_range_parser_rejects_bad_input(text):
    with pytest.raises((argparse.ArgumentTypeError, ValueError)):
        shadow.parse_seed_range(text)


def test_shadow_run_does_not_touch_registered_criteria():
    before = (common.CRITERIA_PATH.read_bytes(), common.CRITERIA_HASH_PATH.read_bytes())
    episode(ScriptedDQN(), FixedPlanner(0))
    assert before == (common.CRITERIA_PATH.read_bytes(), common.CRITERIA_HASH_PATH.read_bytes())
