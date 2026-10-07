"""Shadow-mode recommendation comparison (research CLI; the default evaluation path is unchanged).

The checkpointed DQN keeps choosing every action that is applied to the environment. At each
step the same observation is also given to ``planner_ops`` (or ``planner_ops_hist``), and its
*recommended* action is recorded next to the DQN action. The planner is isolated:

* it runs after the DQN decision, so it cannot influence it;
* it receives a read-only copy of the observation and a minimal read-only stand-in carrying only
  ``max_steps`` and ``min_safe_fuel``, never the live environment (so it cannot read or change
  environment state or its random generator);
* python/numpy global random states are restored after each planner call;
* any planner exception or invalid action is recorded and the DQN run continues.

Information tiers (recorded in ``summary.json``): ``planner_ops`` is ``I_ops``, i.e. it sees only
the current observation, the same single observation the DQN receives. ``planner_ops_hist`` is
``I_ops_hist``: it also uses the previous observation of the same episode, so it does NOT have
the same information as the DQN. Variants that look at the true future price are rejected.

What this measures: how often the recommendation differs from the DQN action, how long each
computation takes, and how often the planner fails. What it does NOT measure: the planner's
cost or safety. Those require applying the planner's actions, which is done by the fair
comparison harness (``evaluate.py``) and is not repeated here.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

import numpy as np

from research.fair_replacement_eval import common, preflight
from envs.bunkering_env import BunkeringEnv
from evaluation.safety_accounting import VoyageAudit
from research.fair_replacement_eval.common import Episode, PROJECT_ROOT, file_sha256, load_criteria
from research.fair_replacement_eval.policies import PlannerPolicy, make_planners

MODE = "shadow_recommendation_comparison"
CLAIM = (
    "Recommendation comparison only. No cost or safety performance of the planner is measured; "
    "the planner's actions were never applied to the environment."
)
PLANNER_TIERS = {
    "planner_ops": {
        "tier": "I_ops",
        "same_information_as_dqn": True,
        "note": "current observation only (memoryless): the same single observation the DQN receives",
    },
    "planner_ops_hist": {
        "tier": "I_ops_hist",
        "same_information_as_dqn": False,
        "note": "current plus previous observation of the same episode (estimates consumption): more information than the DQN's single observation",
    },
}
ALLOWED_PLANNERS = tuple(PLANNER_TIERS)  # no variant may read the true future price
STEP_FIELDS = [
    "seed", "step", "dqn_action", "planner_action", "planner_status", "disagree_raw", "disagree_buy",
    "dqn_ns", "planner_ns", "planner_error", "obs",
]
TRACE_FIELDS = ["seed", "step", "obs_sha256", "action", "reward", "terminated", "truncated", "next_obs_sha256"]
# Deterministic fields compared to show the DQN voyage is identical with the shadow on and off.
OUTCOME_FIELDS = [
    "seed", "cost_index", "adjusted_sci", "safe", "arrived", "depleted", "stops", "end_reason",
    "shortage_steps", "reserve_violation_steps", "final_fuel",
]


class ShadowPolicy:
    """Wrap the DQN policy: delegate every decision to it, record the planner's recommendation."""

    def __init__(self, primary: Any, planner: Any | None, *, enabled: bool = True, name: str | None = None) -> None:
        self.primary = primary
        self.planner = planner
        self.enabled = bool(enabled and planner is not None)
        self.name = name or getattr(primary, "name", type(primary).__name__)
        self.records: list[dict[str, Any]] = []
        self.seed: int | None = None

    def begin_episode(self, seed: int) -> None:
        self.seed = int(seed)

    def select_action(self, env: Any, observation: Any, step_index: int) -> Any:
        t0 = time.perf_counter_ns()
        action = self.primary.select_action(env, observation, step_index)
        dqn_ns = time.perf_counter_ns() - t0
        if self.enabled:
            self._recommend(env, observation, step_index, action, dqn_ns)
        return action  # the DQN action is applied unchanged, whatever the planner did

    # ------------------------------------------------------------------ planner side
    def _recommend(self, env: Any, observation: Any, step_index: int, dqn_action: Any, dqn_ns: int) -> None:
        n_actions = int(env.action_space.n)
        obs_copy = np.array(observation, dtype=float, copy=True)
        obs_copy.setflags(write=False)
        view = SimpleNamespace(max_steps=int(env.max_steps), min_safe_fuel=float(env.min_safe_fuel))
        py_state, np_state = random.getstate(), np.random.get_state()
        status, error, planner_action, planner_ns = "ok", "", None, 0
        t0 = time.perf_counter_ns()
        try:
            raw = self.planner.select_action(view, obs_copy, step_index)
            planner_ns = time.perf_counter_ns() - t0
            planner_action, status, error = self._validate(raw, n_actions)
        except Exception as exc:  # noqa: BLE001 - a planner failure must never stop the DQN run
            planner_ns = time.perf_counter_ns() - t0
            status, error = "error", f"{type(exc).__name__}: {exc}"
        finally:
            random.setstate(py_state)
            np.random.set_state(np_state)
        valid = status == "ok"
        dqn_int = int(dqn_action)
        self.records.append({
            "seed": self.seed,
            "step": int(step_index),
            "dqn_action": dqn_int,
            "planner_action": planner_action if valid else None,
            "planner_status": status,
            "disagree_raw": int(planner_action != dqn_int) if valid else None,
            # Actions 1..n_ports are the same refill in this environment, so buy/wait is the
            # meaningful comparison; raw disagreement is kept for transparency.
            "disagree_buy": int((planner_action > 0) != (dqn_int > 0)) if valid else None,
            "dqn_ns": int(dqn_ns),
            "planner_ns": int(planner_ns),
            "planner_error": error,
            "obs": [round(float(v), 6) for v in obs_copy],
        })

    @staticmethod
    def _validate(raw: Any, n_actions: int) -> tuple[int | None, str, str]:
        if isinstance(raw, bool) or not isinstance(raw, (int, np.integer)):
            return None, "invalid_action", f"non-integer action {raw!r} ({type(raw).__name__})"
        value = int(raw)
        if not 0 <= value < n_actions:
            return None, "invalid_action", f"action {value} outside [0, {n_actions - 1}]"
        return value, "ok", ""


def _digest(observation: Any) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(observation, dtype=np.float64)).tobytes()).hexdigest()


def run_traced_episode(
    primary: Any,
    planner: Any | None,
    seed: int,
    env_config: dict[str, Any],
    *,
    enabled: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """One voyage. Returns (DQN episode row, per-step shadow records, per-step DQN trace).

    The loop is the same as ``common.run_episode`` (a test asserts equal rows) plus a trace of what
    the DQN saw and did at every step: observation digest, action, reward, terminated/truncated
    flags and the digest of the next observation. Timing is deliberately not part of the trace.
    """
    shadow = ShadowPolicy(primary, planner, enabled=enabled)
    shadow.begin_episode(seed)
    env = BunkeringEnv(**dict(env_config))
    observation, _ = env.reset(seed=int(seed))
    audit = VoyageAudit(env._fuel_remaining, env.raw_fuel_price * env._raw_fx_rate, env.min_safe_fuel)
    stops, step_index = 0, 0
    trace: list[dict[str, Any]] = []
    while True:
        seen = _digest(observation)
        action = shadow.select_action(env, observation, step_index)
        audit.observe(env._fuel_remaining, env.fuel_consumption_per_step)
        observation, reward, terminated, truncated, info = env.step(action)
        stops += int(info["actual_bunker_amount"] > env._BUNKER_AMOUNT_EPSILON)
        trace.append({
            "seed": int(seed), "step": step_index, "obs_sha256": seen, "action": int(action),
            "reward": repr(float(reward)), "terminated": bool(terminated), "truncated": bool(truncated),
            "next_obs_sha256": _digest(observation),
        })
        step_index += 1
        if terminated or truncated:
            break
    end_reason = info["end_reason"]
    final = audit.finish(
        end_reason == "arrived", info["cumulative_cost_index"], env._fuel_remaining, env.raw_fuel_price * env._raw_fx_rate
    )
    row = Episode(
        seed=int(seed), policy=shadow.name, scenario="shadow", cost_index=float(info["cumulative_cost_index"]),
        adjusted_sci=float(final["inventory_adjusted_sci"]), safe=bool(final["safe_arrival"]),
        arrived=end_reason == "arrived", depleted=end_reason == "fuel_depleted", stops=stops, end_reason=end_reason,
        shortage_steps=int(final["pre_refill_shortage_steps"]),
        reserve_violation_steps=int(final["pre_refill_reserve_violation_steps"]),
        final_fuel=float(final["final_fuel"]), decision_ns=[], wall_ns=0,
    ).row()
    return row, shadow.records, trace


def run_shadow_episode(
    primary: Any,
    planner: Any | None,
    seed: int,
    env_config: dict[str, Any],
    *,
    enabled: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Like :func:`run_traced_episode` without the trace."""
    row, records, _ = run_traced_episode(primary, planner, seed, env_config, enabled=enabled)
    return row, records


def trace_sha256(trace: Sequence[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(list(trace), sort_keys=True).encode("utf-8")).hexdigest()


def first_trace_difference(on: Sequence[dict[str, Any]], off: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """First step/field where two DQN traces differ, or None if identical (same length and content)."""
    for a, b in zip(on, off):
        for key in TRACE_FIELDS:
            if a[key] != b[key]:
                return {"seed": a["seed"], "step": a["step"], "field": key, "shadow_on": a[key], "shadow_off": b[key]}
    if len(on) != len(off):
        return {"seed": (on or off)[0]["seed"], "step": min(len(on), len(off)), "field": "length", "shadow_on": len(on), "shadow_off": len(off)}
    return None


def outcome(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in OUTCOME_FIELDS}


def _percentiles(values: Sequence[int]) -> dict[str, float | None]:
    if not values:
        return {"n": 0, "mean_ms": None, "p50_ms": None, "p95_ms": None, "p99_ms": None, "max_ms": None}
    a = np.asarray(values, dtype=float) / 1e6
    return {
        "n": int(a.size), "mean_ms": float(a.mean()), "p50_ms": float(np.percentile(a, 50)),
        "p95_ms": float(np.percentile(a, 95)), "p99_ms": float(np.percentile(a, 99)), "max_ms": float(a.max()),
    }


def summarize(steps: Sequence[dict[str, Any]], episodes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(steps)
    ok = [s for s in steps if s["planner_status"] == "ok"]
    errors = [s for s in steps if s["planner_status"] == "error"]
    invalid = [s for s in steps if s["planner_status"] == "invalid_action"]
    error_kinds: dict[str, int] = {}
    for s in errors + invalid:
        key = s["planner_error"].split(":")[0] if s["planner_status"] == "error" else "invalid_action"
        error_kinds[key] = error_kinds.get(key, 0) + 1
    raw = sum(s["disagree_raw"] for s in ok)
    buy = sum(s["disagree_buy"] for s in ok)
    return {
        "steps": n,
        "episodes": len(episodes),
        "planner_ok_steps": len(ok),
        "planner_error_steps": len(errors),
        "planner_invalid_action_steps": len(invalid),
        "planner_failure_kinds": error_kinds,
        "disagreement_raw": {"count": raw, "rate_of_valid_recommendations": raw / len(ok) if ok else None},
        "disagreement_buy_vs_wait": {"count": buy, "rate_of_valid_recommendations": buy / len(ok) if ok else None},
        "agreement_buy_vs_wait_rate_of_valid_recommendations": (1 - buy / len(ok)) if ok else None,
        "episodes_with_any_disagreement": len({s["seed"] for s in ok if s["disagree_buy"]}),
        "latency_dqn": _percentiles([s["dqn_ns"] for s in steps]),
        "latency_planner": _percentiles([s["planner_ns"] for s in steps]),
        "dqn_executed_outcomes": {
            "note": "Outcomes of the DQN actions that were actually applied in this synthetic environment.",
            "safe_arrival": sum(int(e["safe"]) for e in episodes),
            "depleted": sum(int(e["depleted"]) for e in episodes),
            "mean_stops": float(np.mean([e["stops"] for e in episodes])) if episodes else None,
        },
        "planner_performance_measured": False,
    }


def _write_csv_gz(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = dict(row)
            if "obs" in fields:
                row["obs"] = json.dumps(row.get("obs", []))
            writer.writerow(row)


def run_shadow(
    primary: Any,
    planner_factory: Callable[[], Any],
    seeds: Sequence[int],
    env_config: dict[str, Any],
    *,
    isolation_check: bool = True,
) -> dict[str, Any]:
    """Run all seeds with the shadow on and (optionally) off and compare the DQN voyages.

    The comparison covers the voyage aggregates AND a per-step trace (observation digest, action,
    reward, terminated/truncated, next-observation digest); execution time is excluded.
    """
    planner = planner_factory()
    steps: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    traces_on: list[dict[str, Any]] = []
    traces_off: list[dict[str, Any]] = []
    outcome_bad: list[int] = []
    trace_bad: list[int] = []
    first_diff: dict[str, Any] | None = None
    for seed in seeds:
        row, recs, trace = run_traced_episode(primary, planner, int(seed), env_config, enabled=True)
        row = {**row, "shadow_steps": len(recs), "dqn_trace_sha256": trace_sha256(trace)}
        episodes.append(row)
        steps.extend(recs)
        traces_on.extend(trace)
        if isolation_check:
            off_row, _, off_trace = run_traced_episode(primary, None, int(seed), env_config, enabled=False)
            traces_off.extend(off_trace)
            if outcome(off_row) != outcome(row):
                outcome_bad.append(int(seed))
            diff = first_trace_difference(trace, off_trace)
            if diff is not None:
                trace_bad.append(int(seed))
                first_diff = first_diff or diff
    result: dict[str, Any] = {"steps": steps, "episodes": episodes, "traces_on": traces_on}
    if isolation_check:
        result["traces_off"] = traces_off
        result["isolation_check"] = {
            "compared_episodes": len(episodes),
            "identical": not outcome_bad and not trace_bad,
            "outcome_identical": not outcome_bad,
            "trace_identical": not trace_bad,
            "mismatching_seeds": sorted(set(outcome_bad) | set(trace_bad)),
            "outcome_mismatching_seeds": outcome_bad,
            "trace_mismatching_seeds": trace_bad,
            "first_trace_difference": first_diff,
            "fields": OUTCOME_FIELDS,
            "trace_fields": TRACE_FIELDS,
            "scope": "Per-step DQN observation digest, action, reward, terminated/truncated and next-observation digest plus voyage aggregates; "
                     "execution time excluded. Shows equality on the compared seeds only, not a general guarantee.",
        }
    return result


def parse_seed_range(text: str) -> list[int]:
    lo, _, hi = text.partition(":")
    a, b = int(lo), int(hi)
    if a < 0 or b < a:
        raise argparse.ArgumentTypeError("seed range must be 'first:last' with 0 <= first <= last")
    return list(range(a, b + 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seeds", required=True, type=parse_seed_range, help="inclusive range first:last, e.g. 60000000:60000099")
    parser.add_argument("--planner", choices=ALLOWED_PLANNERS, default="planner_ops",
                        help="planner_ops = I_ops (same single observation as the DQN); planner_ops_hist = I_ops_hist (also uses the previous observation: more information than the DQN)")
    parser.add_argument("--no-isolation-check", action="store_true", help="skip the second, shadow-off run used to prove DQN results are unchanged")
    args = parser.parse_args(argv)

    criteria_check, crit = preflight.check_criteria_hash(load_criteria)
    if crit is None:
        print("pre-flight failed: " + "; ".join(criteria_check["reasons"]), file=sys.stderr)
        return 3
    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        print(f"refusing to overwrite non-empty {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    from research.fair_replacement_eval.evaluate import base_env_config, scenario_config

    env_config = scenario_config(base_env_config(), crit, "nominal")
    sha, payload, load_error = None, None, None
    try:  # reading the file for the hash or the payload may fail (missing, unreadable, corrupt): record, do not crash
        sha = file_sha256(args.checkpoint)
        payload = preflight.load_payload(args.checkpoint)
    except Exception as exc:  # noqa: BLE001
        load_error = f"{type(exc).__name__}: {exc}"
    metadata = None if payload is None else payload.get("metadata")
    file_check = preflight._check(
        "checkpoint_file", preflight.PASS if sha is not None else preflight.FAIL,
        [] if sha is not None else [f"checkpoint file could not be read for hashing: {load_error}"],
    )
    checks = [criteria_check, file_check]
    checks += preflight.check_checkpoint(payload, sha, str(crit["incumbent"]["official_checkpoint_sha256"]), env_config, load_error)
    checks += [preflight.check_env_config(metadata, env_config), preflight.check_training_seed_metadata(metadata)]
    rng, _ = preflight.training_seed_range(metadata)
    seed_info = {
        "range": [args.seeds[0], args.seeds[-1]],
        "overlaps_training_seeds": None if rng is None else any(rng[0] <= s <= rng[1] for s in args.seeds),
        "hits_previously_used_ranges": preflight.hits_used_ranges(args.seeds, crit),
        "note": "Informational only: shadow results never count toward replacement gates.",
    }
    pre = {"overall": preflight.overall_status(checks), "checks": checks, "seeds": seed_info}
    (out / "preflight.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    for c in checks:
        print(f"preflight {c['status']:<11} {c['id']}" + "".join(f"\n    - {r}" for r in c["reasons"]), flush=True)
    if pre["overall"] == preflight.FAIL:
        print(f"pre-flight fail: shadow run not started (record: {out / 'preflight.json'})", file=sys.stderr)
        return 3

    from scripts.evaluate import load_dqn_policy
    import torch

    torch.set_num_threads(1)
    primary = load_dqn_policy(args.checkpoint, env_config)
    sigma_grid = crit["replacement_criteria"]["forecast_sigma_grid"]

    def planner_factory() -> PlannerPolicy:
        planner = make_planners(sigma_grid, {})[args.planner]
        if planner.forecast != "persistence":
            raise ValueError("shadow mode rejects planners that read the true future price")
        return planner

    started = time.time()
    result = run_shadow(primary, planner_factory, args.seeds, env_config, isolation_check=not args.no_isolation_check)
    _write_csv_gz(out / "shadow_steps.csv.gz", result["steps"], STEP_FIELDS)
    if "traces_off" in result:
        _write_csv_gz(out / "dqn_trace_shadow_on.csv.gz", result["traces_on"], TRACE_FIELDS)
        _write_csv_gz(out / "dqn_trace_shadow_off.csv.gz", result["traces_off"], TRACE_FIELDS)
    with gzip.open(out / "dqn_episodes.csv.gz", "wt", encoding="utf-8", newline="") as handle:
        fields = [k for k in result["episodes"][0] if k not in ("decision_ns_mean", "decision_ns_max", "wall_ns")] if result["episodes"] else OUTCOME_FIELDS
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["episodes"])

    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True).stdout.strip()
    summary = {
        "mode": MODE,
        "claim": CLAIM,
        "planner": args.planner,
        "planner_information": {"name": args.planner, **PLANNER_TIERS[args.planner]},
        "checkpoint": {"file": args.checkpoint.name, "sha256": sha, "official": sha == crit["incumbent"]["official_checkpoint_sha256"], "metadata": metadata},
        "preflight": {"overall": pre["overall"], "file": "preflight.json"},
        "seeds": seed_info,
        "isolation_check": result.get("isolation_check"),
        **summarize(result["steps"], result["episodes"]),
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_head": git_sha,
        "criteria_sha256": file_sha256(common.CRITERIA_PATH),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "elapsed_seconds": round(time.time() - started, 1),
        "files_sha256": {p.name: file_sha256(p) for p in sorted(out.glob("*.csv.gz"))},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    iso = result.get("isolation_check")
    print(f"planner={args.planner} information_tier={PLANNER_TIERS[args.planner]['tier']} same_information_as_dqn={PLANNER_TIERS[args.planner]['same_information_as_dqn']}")
    print(f"steps={summary['steps']} disagree_buy={summary['disagreement_buy_vs_wait']['count']} planner_failures={summary['planner_error_steps'] + summary['planner_invalid_action_steps']}")
    if iso is not None:
        print(f"isolation_check identical={iso['identical']} outcome={iso['outcome_identical']} trace={iso['trace_identical']} (episodes={iso['compared_episodes']})")
    print(f"wrote {out}")
    return 0 if (iso is None or iso["identical"]) else 4


if __name__ == "__main__":
    sys.exit(main())
