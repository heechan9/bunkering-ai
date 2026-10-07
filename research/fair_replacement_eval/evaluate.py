"""Run the pre-registered fair comparison and write results.

    python -m research.fair_replacement_eval.evaluate \
        --checkpoint /path/to/dqn_final.pt --out research/fair_replacement_eval/results/<name>

The incumbent is whatever checkpoint is passed; the verdict is
SYNTHETIC_VALIDATION_ONLY unless its sha256 equals the official value in
criteria.json. Nothing here deploys, replaces or merges anything.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import multiprocessing as mp
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from research.fair_replacement_eval import common
from research.fair_replacement_eval.common import PROJECT_ROOT, file_sha256, load_criteria, run_episode
from research.fair_replacement_eval import preflight
from research.fair_replacement_eval.decision import evaluate_criteria, forecast_sensitivity, policy_summary, time_table
from research.fair_replacement_eval.policies import PlannerPolicy, make_planners

BASELINES = ("fixed_fueling", "price_reactive", "safe_stock")


def _hits_used_ranges(seeds: list[int], crit: dict[str, Any]) -> bool:
    """True if any seed lies in a range already used (reuse, development, diagnostics, surrogate)."""
    return preflight.hits_used_ranges(seeds, crit)


def base_env_config() -> dict[str, Any]:
    from scripts.evaluate import load_env_config

    return load_env_config(PROJECT_ROOT / "configs" / "dqn.yaml")


def scenario_config(base: dict[str, Any], crit: dict[str, Any], scenario: str) -> dict[str, Any]:
    cfg = dict(base)
    cfg["fuel_consumption_per_step"] = float(crit["env_scenarios"][scenario]["fuel_consumption_per_step"])
    return cfg


def deadline_stop_map(crit: dict[str, Any], legs: int) -> dict[str, int]:
    ov = crit["time_overlay"]
    out = {}
    for label, deadline in ov["deadlines_hours"].items():
        allowed = common.allowed_stops(deadline, legs, ov["leg_hours"], ov["stop_hours"])
        if allowed >= 1:
            out[label] = allowed
    return out


def build_policy(name: str, checkpoint: str | None, env_config: dict[str, Any], crit: dict[str, Any]) -> Any:
    from scripts import baseline
    from scripts.evaluate import load_dqn_policy

    if name == "fixed_fueling":
        return baseline.FixedFuelingStrategy()
    if name == "price_reactive":
        return baseline.PriceReactiveStrategy()
    if name == "safe_stock":
        return baseline.SafeStockStrategy()
    if name == "double_dqn":
        import torch

        torch.set_num_threads(1)
        return load_dqn_policy(Path(checkpoint), env_config)
    stops = deadline_stop_map(crit, int(env_config["max_steps"]))
    sigma_grid = crit["replacement_criteria"]["forecast_sigma_grid"]
    return make_planners(sigma_grid, stops)[name]


def _job(args: tuple) -> tuple[str, str, str, list[dict[str, Any]]]:
    which, name, scenario, seeds, env_config, checkpoint, crit, timed = args
    policy = build_policy(name, checkpoint, env_config, crit)
    rows = [run_episode(policy, int(s), env_config, scenario, timed=timed).row() for s in seeds]
    return which, name, scenario, rows


def run_jobs(jobs: list[tuple], workers: int) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    results: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=workers) as pool:
        for which, name, scenario, rows in pool.imap_unordered(_job, jobs):
            results[(which, name, scenario)] = sorted(rows, key=lambda r: r["seed"])
            print(f"  done {which:>7} {scenario:>20} {name:<24} n={len(rows)}", flush=True)
    return results


def write_episodes(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def runtime_benchmark(names: list[str], checkpoint: str, env_config: dict[str, Any], crit: dict[str, Any], seeds: list[int]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name in names:
        policy = build_policy(name, checkpoint, env_config, crit)
        run_episode(policy, seeds[0], env_config, "warmup")  # warm-up, discarded
        decisions: list[int] = []
        walls: list[int] = []
        for s in seeds:
            ep = run_episode(policy, s, env_config, "runtime")
            decisions.extend(ep.decision_ns)
            walls.append(ep.wall_ns)
        arr = np.asarray(decisions, dtype=float) / 1e6
        out[name] = {
            "decisions": int(len(arr)),
            "mean_ms": float(arr.mean()),
            "p50_ms": float(np.percentile(arr, 50)),
            "p99_ms": float(np.percentile(arr, 99)),
            "max_ms": float(arr.max()),
            "episode_wall_mean_ms": float(np.mean(walls) / 1e6),
        }
    return out


def reuse_consistency(checkpoint: str, env_config: dict[str, Any], seeds: list[int], mine: dict[tuple[str, str], list[dict[str, Any]]], crit: dict[str, Any]) -> dict[str, Any]:
    """Compare this runner with scripts.evaluate.run_episode (the existing path)."""
    from evaluation.contract import EvaluationCase
    from scripts.evaluate import run_episode as repo_run_episode

    detail: dict[str, Any] = {}
    ok = True
    for name in (*BASELINES, "double_dqn"):
        policy = build_policy(name, checkpoint, env_config, crit)
        mismatches = 0
        for row in mine[(name, "nominal")]:
            ref = repo_run_episode(policy, EvaluationCase(seed=row["seed"], episode=0, policy=name, env_config=dict(env_config)))
            same = (
                abs(ref.synthetic_cost_index - row["cost_index"]) <= 1e-9 * max(1.0, abs(ref.synthetic_cost_index))
                and ref.success == bool(row["arrived"])
                and ref.bunkering_count == row["stops"]
                and ref.termination_reason == row["end_reason"]
            )
            mismatches += int(not same)
        detail[name] = {"episodes": len(seeds), "mismatches_vs_scripts_evaluate": mismatches}
        ok = ok and mismatches == 0
    # Baselines do not depend on the checkpoint: compare with the committed CSV as well.
    csv_path = PROJECT_ROOT / "results" / "evaluation_results.csv"
    repo_csv: dict[str, Any] = {"path": "results/evaluation_results.csv", "compared": False}
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8") as handle:
            table = list(csv.DictReader(handle))
        repo_csv["compared"] = True
        for name in BASELINES:
            ref = {int(r["seed"]): r for r in table if r["policy"] == name}
            bad = 0
            for row in mine[(name, "nominal")]:
                r = ref.get(row["seed"])
                if r is None or abs(float(r["Synthetic Cost Index"]) - row["cost_index"]) > 1e-6 * max(1.0, row["cost_index"]):
                    bad += 1
            repo_csv[name] = {"missing_or_different": bad, "rows_in_repo_csv": len(ref)}
            ok = ok and bad == 0
    return {"pass": ok, "detail": detail, "repo_csv": repo_csv}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--smoke", action="store_true", help="tiny run: harness check only; fails gate G4")
    parser.add_argument(
        "--continue-undecidable",
        action="store_true",
        help="run even if pre-flight is undecidable (e.g. training-seed metadata missing); the verdict stays NOT_DECIDABLE",
    )
    args = parser.parse_args(argv)

    criteria_check, crit = preflight.check_criteria_hash(load_criteria)  # hash must equal criteria.sha256
    if crit is None:
        print("pre-flight failed: " + "; ".join(criteria_check["reasons"]), file=sys.stderr)
        return 3
    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        print(f"refusing to overwrite non-empty {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    base = base_env_config()
    legs, reserve = int(base["max_steps"]), float(base["min_safe_fuel"])
    reuse_cfg, hold_cfg = crit["evaluation_sets"]["reuse"], crit["evaluation_sets"]["confirmation"]
    th = crit["thresholds"]
    n_reuse = 12 if args.smoke else int(reuse_cfg["episodes"])
    n_conf = 40 if args.smoke else int(hold_cfg["episodes"])
    reuse_seeds = [int(reuse_cfg["base_seed"]) + i for i in range(n_reuse)]
    conf_seeds = [int(hold_cfg["base_seed"]) + i for i in range(n_conf)]
    sigma_grid = crit["replacement_criteria"]["forecast_sigma_grid"]
    stops_map = deadline_stop_map(crit, legs)

    ckpt = str(args.checkpoint)
    sha = file_sha256(args.checkpoint)
    # One pre-flight before any episode: checkpoint hash/format/dimensions, env_config, training-seed
    # metadata, criteria hash, seed ranges. A missing n_episodes is never treated as 0.
    pre = preflight.run_preflight(
        args.checkpoint,
        crit,
        scenario_config(base, crit, "nominal"),
        conf_seeds,
        reuse_seeds,
        sha256=sha,
        criteria_check=criteria_check,
    )
    pre["criteria_sha256"] = file_sha256(common.CRITERIA_PATH)
    (out / "preflight.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    for c in pre["checks"]:
        print(f"preflight {c['status']:<11} {c['id']}" + ("".join(f"\n    - {r}" for r in c["reasons"])), flush=True)
    if pre["overall"] == preflight.FAIL or (pre["overall"] == preflight.UNDECIDABLE and not args.continue_undecidable):
        print(f"pre-flight {pre['overall']}: evaluation not started (record: {out / 'preflight.json'})", file=sys.stderr)
        return 3

    from agents.dqn import DQNAgent

    meta = DQNAgent.load_checkpoint(args.checkpoint).checkpoint_metadata
    official = sha == crit["incumbent"]["official_checkpoint_sha256"]
    seed_check = next(c for c in pre["checks"] if c["id"] == "seed_ranges")
    conf_overlap = seed_check["confirmation_overlaps_training_seeds"]
    reuse_overlap = seed_check["reuse_overlaps_training_seeds"]

    planner_names = ["planner_ops", "planner_ops_hist"]
    voi_names = ["planner_oracle" if s == 0 else f"planner_fcst_{s:g}" for s in sigma_grid]
    dl_names = [f"planner_ops_dl_{label}" for label in stops_map]
    ref_names = [*BASELINES, "double_dqn"]

    jobs: list[tuple] = []
    for name in (*ref_names, *planner_names):
        jobs.append(("reuse", name, "nominal", reuse_seeds, scenario_config(base, crit, "nominal"), ckpt, crit, False))
    for scenario in crit["env_scenarios"]:
        if scenario == "note":
            continue
        names = [*ref_names, *planner_names]
        if scenario == "nominal":
            names += voi_names + dl_names
        for name in names:
            jobs.append(("confirmation", name, scenario, conf_seeds, scenario_config(base, crit, scenario), ckpt, crit, False))

    started = time.time()
    print(f"jobs={len(jobs)} workers={args.workers} confirmation_n={n_conf} reuse_n={n_reuse}", flush=True)
    raw = run_jobs(jobs, args.workers)
    confirmation: dict[str, dict[str, list[dict[str, Any]]]] = {}
    reuse_rows: dict[str, list[dict[str, Any]]] = {}
    for (which, name, scenario), rows in raw.items():
        if which == "reuse":
            reuse_rows[name] = rows
        else:
            confirmation.setdefault(scenario, {})[name] = rows

    print("runtime benchmark (serial)...", flush=True)
    bench_seeds = conf_seeds[: (10 if args.smoke else 200)]
    runtime = runtime_benchmark([*ref_names, *planner_names, "planner_oracle"], ckpt, scenario_config(base, crit, "nominal"), crit, bench_seeds)

    print("consistency vs scripts.evaluate ...", flush=True)
    consistency = reuse_consistency(ckpt, scenario_config(base, crit, "nominal"), reuse_seeds, {(n, "nominal"): r for n, r in reuse_rows.items()}, crit)

    pre_gates = preflight.gate_values(pre)
    gates = {
        "G0_preflight": pre_gates["G0_preflight"],
        "G1_official_incumbent": bool(official),
        "G2_holdout_disjoint": pre_gates["G2_holdout_disjoint"],
        "G3_criteria_hash": pre_gates["G3_criteria_hash"],
        "G4_holdout_size": n_conf >= int(th["min_confirmation_episodes"]),
        "G5_reuse_consistency": bool(consistency["pass"]),
    }
    decision = evaluate_criteria(confirmation, runtime, gates, official, crit, legs, reserve)
    voi = forecast_sensitivity(confirmation["nominal"], sigma_grid, crit)

    summaries = {sc: {name: policy_summary(rows) for name, rows in per.items()} for sc, per in confirmation.items()}
    nominal_time = time_table({n: r for n, r in confirmation["nominal"].items() if n in (*ref_names, *planner_names)}, float(crit["env_scenarios"]["nominal"]["fuel_consumption_per_step"]), legs, reserve, crit)
    dl_time = {}
    for label in stops_map:
        rows = confirmation["nominal"][f"planner_ops_dl_{label}"]
        dl_time[label] = {"deadline_hours": crit["time_overlay"]["deadlines_hours"][label], **policy_summary(rows)}
    reuse_summary = {name: policy_summary(rows) for name, rows in reuse_rows.items()}
    time_by_scenario = {
        sc: time_table({n: r for n, r in per.items() if n in (*ref_names, *planner_names)}, float(crit["env_scenarios"][sc]["fuel_consumption_per_step"]), legs, reserve, crit)
        for sc, per in confirmation.items()
    }

    for sc, per in confirmation.items():
        for name, rows in per.items():
            write_episodes(out / "episodes" / f"confirmation_{sc}_{name}.csv.gz", rows)
    for name, rows in reuse_rows.items():
        write_episodes(out / "episodes" / f"reuse_nominal_{name}.csv.gz", rows)

    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True).stdout.strip()
    summary = {
        "mode": "smoke" if args.smoke else "full",
        "verdict": decision["verdict"],
        "verdict_note": "SYNTHETIC_VALIDATION_ONLY means the incumbent was not the official checkpoint: numbers validate the harness only.",
        "would_pass_all_criteria_if_incumbent_were_official": decision["would_pass_all_if_official"],
        "incumbent": {"checkpoint_file": args.checkpoint.name, "sha256": sha, "official": official, "metadata": meta,
                      "confirmation_overlaps_training_seeds": conf_overlap, "reuse_overlaps_training_seeds": reuse_overlap},
        "gates": gates,
        "preflight": {"overall": pre["overall"], "file": "preflight.json", "statuses": {c["id"]: c["status"] for c in pre["checks"]}},
        "criteria": decision["criteria"],
        "nominal_comparison": decision["nominal_comparison"],
        "forecast_sensitivity": voi,
        "confirmation_summaries": summaries,
        "confirmation_time_nominal": nominal_time,
        "confirmation_time_by_scenario": time_by_scenario,
        "deadline_aware_extension_nominal": dl_time,
        "reuse_summaries": reuse_summary,
        "reuse_consistency": consistency,
        "runtime": runtime,
        "seeds": {"reuse": [reuse_seeds[0], reuse_seeds[-1]], "confirmation": [conf_seeds[0], conf_seeds[-1]]},
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_head": git_sha,
        "criteria_sha256": file_sha256(common.CRITERIA_PATH),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "elapsed_seconds": round(time.time() - started, 1),
        "episode_files_sha256": {p.name: file_sha256(p) for p in sorted((out / "episodes").glob("*.csv.gz"))},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"verdict={decision['verdict']} would_pass_all={decision['would_pass_all_if_official']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
