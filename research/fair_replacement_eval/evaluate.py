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
from research.fair_replacement_eval.decision import evaluate_criteria, forecast_sensitivity, policy_summary, time_table
from research.fair_replacement_eval.policies import PlannerPolicy, make_planners

BASELINES = ("fixed_fueling", "price_reactive", "safe_stock")


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
    args = parser.parse_args(argv)

    crit = load_criteria()  # raises if criteria.json differs from criteria.sha256
    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        print(f"refusing to overwrite non-empty {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    base = base_env_config()
    legs, reserve = int(base["max_steps"]), float(base["min_safe_fuel"])
    reuse_cfg, hold_cfg = crit["evaluation_sets"]["reuse"], crit["evaluation_sets"]["holdout"]
    n_reuse = 12 if args.smoke else int(reuse_cfg["episodes"])
    n_hold = 40 if args.smoke else int(hold_cfg["episodes"])
    reuse_seeds = [int(reuse_cfg["base_seed"]) + i for i in range(n_reuse)]
    hold_seeds = [int(hold_cfg["base_seed"]) + i for i in range(n_hold)]
    sigma_grid = crit["replacement_criteria"]["forecast_sigma_grid"]
    stops_map = deadline_stop_map(crit, legs)

    ckpt = str(args.checkpoint)
    sha = file_sha256(args.checkpoint)
    from agents.dqn import DQNAgent

    meta = DQNAgent.load_checkpoint(args.checkpoint).checkpoint_metadata
    official = sha == crit["incumbent"]["official_checkpoint_sha256"]
    train_lo = meta.get("train_seed")
    train_hi = None if train_lo is None else int(train_lo) + int(meta.get("n_episodes", 0))
    def overlaps(seeds: list[int]) -> bool | None:
        if train_lo is None:
            return None
        return any(int(train_lo) <= s < train_hi for s in seeds)
    hold_overlap, reuse_overlap = overlaps(hold_seeds), overlaps(reuse_seeds)

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
            jobs.append(("holdout", name, scenario, hold_seeds, scenario_config(base, crit, scenario), ckpt, crit, False))

    started = time.time()
    print(f"jobs={len(jobs)} workers={args.workers} holdout_n={n_hold} reuse_n={n_reuse}", flush=True)
    raw = run_jobs(jobs, args.workers)
    holdout: dict[str, dict[str, list[dict[str, Any]]]] = {}
    reuse_rows: dict[str, list[dict[str, Any]]] = {}
    for (which, name, scenario), rows in raw.items():
        if which == "reuse":
            reuse_rows[name] = rows
        else:
            holdout.setdefault(scenario, {})[name] = rows

    print("runtime benchmark (serial)...", flush=True)
    bench_seeds = hold_seeds[: (10 if args.smoke else 200)]
    runtime = runtime_benchmark([*ref_names, *planner_names, "planner_oracle"], ckpt, scenario_config(base, crit, "nominal"), crit, bench_seeds)

    print("consistency vs scripts.evaluate ...", flush=True)
    consistency = reuse_consistency(ckpt, scenario_config(base, crit, "nominal"), reuse_seeds, {(n, "nominal"): r for n, r in reuse_rows.items()}, crit)

    gates = {
        "G1_official_incumbent": bool(official),
        "G2_holdout_disjoint": bool(hold_overlap is False and not set(hold_seeds) & set(reuse_seeds)),
        "G3_criteria_hash": True,
        "G4_holdout_size": n_hold >= 1000,
        "G5_reuse_consistency": bool(consistency["pass"]),
    }
    decision = evaluate_criteria(holdout, runtime, gates, official, crit, legs, reserve)
    voi = forecast_sensitivity(holdout["nominal"], sigma_grid, crit)

    summaries = {sc: {name: policy_summary(rows) for name, rows in per.items()} for sc, per in holdout.items()}
    nominal_time = time_table({n: r for n, r in holdout["nominal"].items() if n in (*ref_names, *planner_names)}, float(crit["env_scenarios"]["nominal"]["fuel_consumption_per_step"]), legs, reserve, crit)
    dl_time = {}
    for label in stops_map:
        rows = holdout["nominal"][f"planner_ops_dl_{label}"]
        dl_time[label] = {"deadline_hours": crit["time_overlay"]["deadlines_hours"][label], **policy_summary(rows)}
    reuse_summary = {name: policy_summary(rows) for name, rows in reuse_rows.items()}
    time_by_scenario = {
        sc: time_table({n: r for n, r in per.items() if n in (*ref_names, *planner_names)}, float(crit["env_scenarios"][sc]["fuel_consumption_per_step"]), legs, reserve, crit)
        for sc, per in holdout.items()
    }

    for sc, per in holdout.items():
        for name, rows in per.items():
            write_episodes(out / "episodes" / f"holdout_{sc}_{name}.csv.gz", rows)
    for name, rows in reuse_rows.items():
        write_episodes(out / "episodes" / f"reuse_nominal_{name}.csv.gz", rows)

    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True).stdout.strip()
    summary = {
        "mode": "smoke" if args.smoke else "full",
        "verdict": decision["verdict"],
        "verdict_note": "SYNTHETIC_VALIDATION_ONLY means the incumbent was not the official checkpoint: numbers validate the harness only.",
        "would_pass_all_criteria_if_incumbent_were_official": decision["would_pass_all_if_official"],
        "incumbent": {"checkpoint_file": args.checkpoint.name, "sha256": sha, "official": official, "metadata": meta,
                      "holdout_overlaps_training_seeds": hold_overlap, "reuse_overlaps_training_seeds": reuse_overlap},
        "gates": gates,
        "criteria": decision["criteria"],
        "nominal_comparison": decision["nominal_comparison"],
        "forecast_sensitivity": voi,
        "holdout_summaries": summaries,
        "holdout_time_nominal": nominal_time,
        "holdout_time_by_scenario": time_by_scenario,
        "deadline_aware_extension_nominal": dl_time,
        "reuse_summaries": reuse_summary,
        "reuse_consistency": consistency,
        "runtime": runtime,
        "seeds": {"reuse": [reuse_seeds[0], reuse_seeds[-1]], "holdout": [hold_seeds[0], hold_seeds[-1]]},
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
