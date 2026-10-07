"""Tests for the planner time limit / process isolation of shadow mode (no training, no official checkpoint)."""

from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import os
import sys
import time
from functools import partial
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.fair_replacement_eval import shadow, shadow_isolation, shadow_testing  # noqa: E402
from research.fair_replacement_eval.shadow_isolation import SubprocessPlanner, planner_factory_for  # noqa: E402
from research.fair_replacement_eval.test_preflight import ENV, good_meta, make_checkpoint  # noqa: E402
from research.fair_replacement_eval.test_shadow import ScriptedDQN, SEEDS  # noqa: E402

TIMEOUT = 0.4  # short, only to keep the hang tests quick; the CLI default is 1 s
GENEROUS = 10.0  # for tests where every call is expected to answer (no flakiness on a loaded machine)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run(factory, seeds=SEEDS[:1], *, timeout=TIMEOUT, max_consecutive=3, **kwargs):
    primary = ScriptedDQN()
    result = shadow.run_shadow(
        primary, factory, seeds, dict(ENV), planner_isolation="subprocess", timeout_sec=timeout,
        max_consecutive_timeouts=max_consecutive, **kwargs,
    )
    return result


def statuses(result, seed=None):
    return [r["planner_status"] for r in result["steps"] if seed is None or r["seed"] == seed]


@pytest.fixture(autouse=True)
def no_children_left_behind():
    yield
    assert mp.active_children() == []  # every worker was joined and released


# ---------------------------------------------------------------------- normal


@pytest.mark.parametrize("name", ["planner_ops", "planner_ops_hist"])
def test_subprocess_recommendations_equal_the_in_process_ones(name):
    from research.fair_replacement_eval.policies import make_planners

    factory = planner_factory_for(name, [0.0])
    remote = run(factory, SEEDS, timeout=GENEROUS)
    inproc = shadow.run_shadow(ScriptedDQN(), lambda: make_planners([0.0], {})[name], SEEDS, dict(ENV), isolation_check=False)
    key = lambda rows: [(r["seed"], r["step"], r["planner_status"], r["planner_action"]) for r in rows]
    assert key(remote["steps"]) == key(inproc["steps"])
    assert set(statuses(remote)) == {"ok"}
    assert all(r["planner_history_intact"] for r in remote["steps"])
    assert remote["planner_isolation"]["workers"]["workers_started"] == 1  # one worker serves all episodes


def test_compute_roundtrip_and_ipc_time_are_recorded_separately():
    result = run(planner_factory_for("planner_ops", [0.0]), timeout=GENEROUS)
    for r in result["steps"]:
        assert r["planner_ns"] > 0 and r["planner_roundtrip_ns"] >= r["planner_ns"]
        assert r["planner_ipc_ns"] == r["planner_roundtrip_ns"] - r["planner_ns"] >= 0
    first = result["steps"][0]
    assert first["planner_startup_ns"] is not None and first["planner_startup_ns"] > 0  # worker start, outside the round trip
    assert all(r["planner_startup_ns"] is None for r in result["steps"][1:])
    summary = shadow.summarize(result["steps"], result["episodes"])
    for key in ("latency_planner_compute", "latency_planner_roundtrip", "latency_planner_ipc"):
        assert summary[key]["n"] == len(result["steps"]) and summary[key]["p99_ms"] is not None
    assert summary["latency_planner_roundtrip"]["mean_ms"] >= summary["latency_planner_compute"]["mean_ms"]
    assert summary["planner_worker_startup_ms_total"] > 0


# ---------------------------------------------------------------------- exception / invalid / death


def test_planner_exception_in_the_worker_is_recorded_and_the_worker_keeps_serving():
    result = run(partial(shadow_testing.Scripted, 1, (3,), "raise"))
    st = statuses(result)
    assert st[3] == "error" and "scripted planner failure" in result["steps"][3]["planner_error"]
    assert st.count("error") == 1 and st[4:6] == ["ok", "ok"]
    assert result["planner_isolation"]["workers"]["workers_started"] == 1  # an exception does not cost a restart
    assert result["steps"][4]["planner_history_intact"] is True  # the planner saw every observation


def test_invalid_action_from_the_worker_is_recorded_not_applied():
    result = run(partial(shadow_testing.Scripted, 1, (2,), "invalid"))
    assert statuses(result)[2] == "invalid_action" and result["steps"][2]["planner_action"] is None
    assert result["isolation_check"]["identical"] is True


def test_a_planner_that_kills_its_worker_is_recorded_and_the_next_step_gets_a_new_worker():
    result = run(partial(shadow_testing.Scripted, 1, (4,), "die"))
    st = statuses(result)
    assert st[4] == "error" and "PlannerWorkerDied" in result["steps"][4]["planner_error"]
    assert st[5] == "ok" and st.count("error") == 1
    workers = result["planner_isolation"]["workers"]
    assert workers["workers_died"] == 1 and workers["workers_started"] == 2
    assert result["steps"][5]["planner_history_intact"] is False  # the new worker has no history
    assert result["isolation_check"]["identical"] is True


# ---------------------------------------------------------------------- timeout


@pytest.mark.parametrize("mode", ["sleep", "spin"])
def test_a_timeout_is_recorded_the_dqn_run_continues_and_the_worker_is_reclaimed(mode):
    started = time.perf_counter()
    with SubprocessPlanner(partial(shadow_testing.Scripted, 1, (2,), mode), timeout_sec=TIMEOUT) as remote:
        first = remote.call(0, [0.0] * 6, 30, 0.15)
        assert first["status"] == "ok"
        pid_before = remote._proc.pid
        hung = remote.call(2, [0.0] * 6, 30, 0.15)
        assert hung["status"] == "timeout" and hung["raw"] is None and hung["compute_ns"] is None
        assert hung["roundtrip_ns"] >= TIMEOUT * 1e9 and hung["cleanup_ns"] > 0
        assert not remote.has_worker and not pid_alive(pid_before)  # terminated and reaped, nothing runs on
        assert pid_before in remote.reaped_pids
        after = remote.call(3, [0.0] * 6, 30, 0.15)
        assert after["status"] == "ok" and after["worker_restarted"] is True and after["startup_ns"] > 0
    assert remote.stats["workers_killed_on_timeout"] == 1 and remote.stats["workers_not_reaped"] == 0
    assert time.perf_counter() - started < 30


def test_episode_with_one_timeout_matches_the_dqn_alone_step_by_step():
    result = run(partial(shadow_testing.Scripted, 1, (2,), "sleep"))
    st = statuses(result)
    assert st[2] == "timeout" and st.count("timeout") == 1 and set(st) <= {"ok", "timeout"}
    row = result["steps"][2]
    assert row["planner_action"] is None and row["planner_ns"] is None and row["planner_roundtrip_ns"] >= TIMEOUT * 1e9
    assert row["disagree_raw"] is None and row["disagree_buy"] is None
    iso = result["isolation_check"]
    assert iso["identical"] is True and iso["trace_identical"] is True and iso["outcome_identical"] is True
    # and against a run with no shadow object at all
    plain_row, _, plain_trace = shadow.run_traced_episode(ScriptedDQN(), None, SEEDS[0], dict(ENV), enabled=False)
    assert result["traces_on"] == plain_trace and shadow.outcome(result["episodes"][0]) == shadow.outcome(plain_row)
    assert result["planner_isolation"]["workers"]["workers_killed_on_timeout"] == 1


def test_planner_history_state_after_a_timeout_is_explicit():
    healthy = run(partial(shadow_testing.PrevStepProbe), SEEDS[:1], timeout=GENEROUS, isolation_check=False)
    assert all(r["planner_history_intact"] and r["planner_action"] == 1 for r in healthy["steps"])  # nothing lost

    result = run(partial(shadow_testing.Scripted, 1, (2,), "sleep"), isolation_check=False)
    flags = [r["planner_history_intact"] for r in result["steps"]]
    assert flags[:3] == [True, True, True]  # the call that times out still had its full history
    assert not any(flags[3:])  # afterwards the restarted worker lacks the history: flagged for the rest of the episode
    summary = shadow.summarize(result["steps"], result["episodes"])
    ok_after = sum(1 for r in result["steps"][3:] if r["planner_status"] == "ok")
    assert summary["valid_recommendations_with_incomplete_planner_history"] == ok_after
    assert summary["disagreement_buy_vs_wait_history_intact_only"]["n"] == 2  # only steps 0 and 1 are intact


def test_a_restarted_worker_really_has_no_history_and_the_flag_says_so():
    # PrevStepProbe answers 1 only if it saw the previous step; losing the worker must therefore show as 0
    with SubprocessPlanner(shadow_testing.PrevStepProbe, timeout_sec=GENEROUS) as remote:
        answers = [remote.call(i, [0.0] * 6, 30, 0.15)["raw"] for i in range(3)]
        assert answers == [1, 1, 1]
        remote._reap()  # simulate a worker loss between steps 2 and 3
        assert remote.call(3, [0.0] * 6, 30, 0.15)["raw"] == 0  # new worker: it never saw step 2
        assert remote.call(4, [0.0] * 6, 30, 0.15)["raw"] == 1  # and then follows the steps again
        assert remote.call(0, [0.0] * 6, 30, 0.15)["raw"] == 1  # a new episode starts clean


def test_consecutive_timeouts_open_a_circuit_for_the_rest_of_the_episode_and_reset_next_episode():
    started = time.perf_counter()
    result = run(partial(shadow_testing.Scripted, 1, (), "sleep", True), SEEDS[:2], max_consecutive=2)
    for seed in SEEDS[:2]:
        st = statuses(result, seed)
        assert st[:2] == ["timeout", "timeout"] and set(st[2:]) == {"skipped"}  # circuit resets with each episode
    skipped = [r for r in result["steps"] if r["planner_status"] == "skipped"][0]
    assert skipped["planner_ns"] is None and skipped["planner_roundtrip_ns"] is None and "consecutive timeouts" in skipped["planner_error"]
    workers = result["planner_isolation"]["workers"]
    # 2 timeouts per episode x 2 episodes x (shadow-on only) -> 4 workers, all killed; skipped steps start none
    assert workers["workers_started"] == 4 and workers["workers_killed_on_timeout"] == 4 and workers["workers_not_reaped"] == 0
    iso = result["isolation_check"]
    assert iso["identical"] is True  # the DQN voyages are unaffected by the hanging planner
    summary = shadow.summarize(result["steps"], result["episodes"])
    assert summary["planner_timeout_steps"] == 4 and summary["planner_skipped_steps"] == len(result["steps"]) - 4
    assert summary["planner_failure_kinds"]["timeout"] == 4 and summary["planner_ok_steps"] == 0
    assert summary["disagreement_buy_vs_wait"]["rate_of_valid_recommendations"] is None
    assert time.perf_counter() - started < 60


def test_a_success_between_timeouts_resets_the_consecutive_count():
    # step 1 and step 3 hang, the steps in between answer: with limit 2 the circuit must never open
    result = run(partial(shadow_testing.Scripted, 1, (1, 3, 5), "sleep"), isolation_check=False, max_consecutive=2)
    st = statuses(result)
    assert st[1] == st[3] == st[5] == "timeout" and "skipped" not in st


def test_limit_zero_never_skips():
    result = run(partial(shadow_testing.Scripted, 1, (0, 1, 2, 3), "sleep"), isolation_check=False, max_consecutive=0)
    assert statuses(result)[:4] == ["timeout"] * 4 and "skipped" not in statuses(result)


# ---------------------------------------------------------------------- startup problems


def test_startup_failure_makes_the_planner_unavailable_but_the_dqn_run_goes_on():
    result = run(shadow_testing.failing_factory)
    assert set(statuses(result)) == {"error"}
    assert "PlannerUnavailable" in result["steps"][0]["planner_error"] and "scripted startup failure" in result["steps"][0]["planner_error"]
    assert result["planner_isolation"]["workers"]["workers_started"] == 1  # no retry loop
    assert result["planner_isolation"]["workers"]["startup_failures"] == 1
    assert result["isolation_check"]["identical"] is True


def test_startup_timeout_is_enforced_and_the_stuck_worker_is_reclaimed():
    with SubprocessPlanner(shadow_testing.slow_factory, timeout_sec=TIMEOUT, startup_timeout_sec=1.0) as remote:
        reply = remote.call(0, [0.0] * 6, 30, 0.15)
        assert reply["status"] == "error" and "did not become ready" in reply["error"]
        assert not remote.has_worker and remote.stats["workers_not_reaped"] == 0
        assert remote.call(1, [0.0] * 6, 30, 0.15)["status"] == "error"  # stays unavailable, no new spawn
        assert remote.stats["workers_started"] == 1


# ---------------------------------------------------------------------- lifecycle / arguments


def test_close_is_idempotent_and_run_shadow_closes_the_worker_even_if_the_run_fails():
    remote = SubprocessPlanner(partial(shadow_testing.Scripted, 1), timeout_sec=TIMEOUT)
    assert remote.call(0, [0.0] * 6, 30, 0.15)["status"] == "ok"
    pid = remote._proc.pid
    remote.close()
    remote.close()
    assert not pid_alive(pid)

    class Boom(ScriptedDQN):
        def select_action(self, env, observation, step_index):
            if step_index == 3:
                raise RuntimeError("dqn failure")
            return super().select_action(env, observation, step_index)

    with pytest.raises(RuntimeError, match="dqn failure"):
        shadow.run_shadow(Boom(), partial(shadow_testing.Scripted, 1), SEEDS[:1], dict(ENV), planner_isolation="subprocess", timeout_sec=TIMEOUT)
    assert mp.active_children() == []


@pytest.mark.parametrize("bad", [0, -1, float("nan")])
def test_invalid_timeouts_are_rejected(bad):
    with pytest.raises(ValueError):
        SubprocessPlanner(partial(shadow_testing.Scripted, 1), timeout_sec=bad)


def test_run_shadow_rejects_unknown_isolation_mode():
    with pytest.raises(ValueError):
        shadow.run_shadow(ScriptedDQN(), partial(shadow_testing.Scripted, 1), SEEDS[:1], dict(ENV), planner_isolation="thread")


def test_the_worker_factory_rejects_planners_that_read_the_future():
    with pytest.raises(ValueError):
        shadow_isolation.build_planner("planner_oracle", [0.0, 0.1])


# ---------------------------------------------------------------------- summarize on crafted steps


def crafted(status, seed=1, step=0, intact=True, buy=0, rt=None, compute=None):
    ok = status == "ok"
    return {
        "seed": seed, "step": step, "dqn_action": 0, "planner_action": 1 if ok else None, "planner_status": status,
        "disagree_raw": buy if ok else None, "disagree_buy": buy if ok else None, "dqn_ns": 1000,
        "planner_ns": compute, "planner_roundtrip_ns": rt, "planner_ipc_ns": None if rt is None or compute is None else rt - compute,
        "planner_startup_ns": None, "planner_cleanup_ns": None, "planner_history_intact": intact, "planner_error": "", "obs": [],
    }


def test_summary_separates_timeouts_skips_failures_and_history():
    steps = [
        crafted("ok", step=0, buy=1, rt=3000, compute=2000), crafted("ok", step=1, buy=0, rt=3000, compute=2500),
        crafted("timeout", step=2, rt=400_000_000), crafted("ok", step=3, intact=False, buy=1, rt=5000, compute=4000),
        crafted("skipped", step=4, intact=False), crafted("error", step=5, rt=2000, compute=1500),
    ]
    s = shadow.summarize(steps, [{"safe": True, "depleted": False, "stops": 1}])
    assert (s["planner_ok_steps"], s["planner_timeout_steps"], s["planner_skipped_steps"], s["planner_error_steps"]) == (3, 1, 1, 1)
    assert s["disagreement_buy_vs_wait"]["count"] == 2 and s["disagreement_buy_vs_wait"]["rate_of_valid_recommendations"] == pytest.approx(2 / 3)
    assert s["valid_recommendations_with_incomplete_planner_history"] == 1
    assert s["disagreement_buy_vs_wait_history_intact_only"] == {**s["disagreement_buy_vs_wait_history_intact_only"], "count": 1, "n": 2, "rate": 0.5}
    assert s["latency_planner_compute"]["n"] == 4  # ok + error steps that ran; timeouts/skips have no compute time
    assert s["latency_planner_roundtrip"]["n"] == 4  # the timeout wait is reported separately, not mixed in
    assert s["planner_timeout_wait_ms_total"] == pytest.approx(400.0)
    assert s["planner_failure_kinds"]["timeout"] == 1 and s["planner_performance_measured"] is False


# ---------------------------------------------------------------------- CLI


def test_cli_rejects_non_positive_timeouts(tmp_path):
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    for flag, value in (("--planner-timeout-sec", "0"), ("--planner-timeout-sec", "-1"), ("--planner-timeout-sec", "nan"),
                        ("--planner-startup-timeout-sec", "0"), ("--max-consecutive-timeouts", "-1")):
        with pytest.raises(SystemExit):
            shadow.main(["--checkpoint", str(ckpt), "--out", str(tmp_path / "o"), "--seeds", "60000000:60000000", flag, value])


def test_cli_default_is_the_time_limited_subprocess_and_records_it(tmp_path):
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    out = tmp_path / "out"
    assert shadow.main(["--checkpoint", str(ckpt), "--out", str(out), "--seeds", "60000000:60000001", "--planner", "planner_ops_hist"]) == 0
    # (default 1 s limit: real planner calls take milliseconds, see SHADOW_MODE.md)
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    iso = s["planner_isolation"]
    assert iso["mode"] == "subprocess" and iso["time_limit_enforced"] is True
    assert iso["timeout_sec"] == shadow_isolation.DEFAULT_TIMEOUT_SEC and iso["max_consecutive_timeouts"] == shadow_isolation.DEFAULT_MAX_CONSECUTIVE_TIMEOUTS
    assert iso["workers"]["workers_started"] == 1 and iso["workers"]["workers_not_reaped"] == 0
    assert s["planner_timeout_steps"] == 0 and s["planner_skipped_steps"] == 0 and s["planner_ok_steps"] == s["steps"]
    assert s["planner_information"]["tier"] == "I_ops_hist" and s["planner_performance_measured"] is False
    assert s["isolation_check"]["trace_identical"] is True
    with gzip.open(out / "shadow_steps.csv.gz", "rt", encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    assert header == shadow.STEP_FIELDS and "planner_roundtrip_ns" in header and "planner_history_intact" in header


def test_cli_inprocess_mode_says_that_no_time_limit_is_enforced(tmp_path):
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    out = tmp_path / "out"
    assert shadow.main(["--checkpoint", str(ckpt), "--out", str(out), "--seeds", "60000000:60000000", "--planner-isolation", "inprocess"]) == 0
    iso = json.loads((out / "summary.json").read_text(encoding="utf-8"))["planner_isolation"]
    assert iso["mode"] == "inprocess" and iso["time_limit_enforced"] is False and iso["timeout_sec"] is None and iso["workers"] is None


def test_cli_with_a_hanging_planner_still_finishes_and_matches_the_dqn_alone(tmp_path, monkeypatch):
    """End to end through main(): every planner call hangs; the run ends with exit 0, timeouts recorded."""
    monkeypatch.setattr(shadow, "planner_factory_for", lambda name, grid: partial(shadow_testing.Scripted, 1, (), "sleep", True))
    ckpt = make_checkpoint(tmp_path / "m.pt", good_meta())
    out = tmp_path / "out"
    started = time.perf_counter()
    code = shadow.main(["--checkpoint", str(ckpt), "--out", str(out), "--seeds", "60000000:60000001",
                        "--planner-timeout-sec", "0.4", "--max-consecutive-timeouts", "2"])
    assert code == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["planner_timeout_steps"] == 4 and s["planner_ok_steps"] == 0
    assert s["planner_skipped_steps"] == s["steps"] - 4
    assert s["isolation_check"]["identical"] is True and s["isolation_check"]["trace_identical"] is True
    assert s["planner_isolation"]["workers"]["workers_not_reaped"] == 0
    assert time.perf_counter() - started < 60


# ---------------------------------------------------------------------- docs


def test_docs_describe_the_time_limit_its_basis_and_its_limits():
    text = (Path(__file__).parent / "SHADOW_MODE.md").read_text(encoding="utf-8")
    for needle in ("--planner-timeout-sec", "timeout", "skipped", "planner_history_intact", "planner_roundtrip_ns", "SIGKILL", "운영"):
        assert needle in text, needle
    assert "no time limit" in shadow.__doc__ or "inprocess" in shadow.__doc__
    assert "성능 개선" in text  # states this is not a planner performance improvement
