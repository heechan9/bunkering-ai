"""Independent 200-seed evaluation of the repository's three Rule-based
strategies (FixedFuelingStrategy, PriceReactiveStrategy, SafeStockStrategy).

This is an independent robustness check, run OUTSIDE the repository's own
scripts/evaluate.py pipeline. It reuses the repository's actual strategy
classes and BunkeringEnv (imported directly, no reimplementation of policy
logic) so behavior cannot drift from what is committed, but the harness,
seed range, and result files below are produced by this script alone.

It does NOT modify, re-run, or supersede the repository's existing official
100-seed four-policy comparison in results/evaluation/ (fixed_fueling,
price_reactive, safe_stock, double_dqn, seeds 42-141). That official result
is left untouched. This script only extends the three Rule-based strategies
to a larger, independently executed seed range for a separate robustness
appendix.

Reproduction
------------
Environment used to run this script:
    - Repository: https://github.com/heechan9/bunkering-ai
    - Commit (main) checked out: f915df9922b63bade92c2efba0f7c74f66c21316
    - Python 3.12.3, numpy, pandas (torch/DQN is NOT imported or needed)

Exact commands used:
    git clone https://github.com/heechan9/bunkering-ai.git
    cd bunkering-ai
    git checkout f915df9922b63bade92c2efba0f7c74f66c21316   # main HEAD at run time
    pip install -r requirements.txt
    python script2_baseline_200seed_eval.py

The script must be run from the repository root (it imports envs.bunkering_env
and scripts.baseline directly, matching what scripts/evaluate.py itself does).
`envs/bunkering_env.py` imports `gymnasium`, so gymnasium must be installed —
plain `pip install numpy pandas` is NOT sufficient and will fail at the
`from envs.bunkering_env import BunkeringEnv` import.

Using the repository's own `pip install -r requirements.txt` guarantees every
declared dependency (including gymnasium) is present and keeps this script's
environment identical to what a reviewer following the repo's own README
would set up. That file also lists torch/tensorboard/matplotlib/plotly/
streamlit, none of which this script actually imports (no DQN, no plotting
here) — if a minimal environment is preferred instead of the full
requirements.txt, the exact and complete package list this script needs is:

    pip install numpy pandas gymnasium

Statistics
----------
All "_std" columns are population standard deviation, i.e. numpy.std(...)
with the default ddof=0 (divide by N, not N-1). This matches how the
repository's own results/evaluation/summary.csv computes std (also via
numpy.std with ddof left at its default). No sample-std (ddof=1) values
are produced by this script.

Seed windows
------------
The 20/50/100/150/200-seed stability breakdown is NOT five independent
samples. All windows start at the same BASE_SEED and are cumulative
prefixes of the same 200-seed run, e.g. the 50-seed window is the first
50 seeds of the 200-seed run, which are also included in the 100-, 150-,
and 200-seed windows. Treat this as "how the running estimate evolves as
more seeds are added," not as five separate experiments.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from envs.bunkering_env import BunkeringEnv
from scripts.baseline import (
    FixedFuelingStrategy,
    PriceReactiveStrategy,
    SafeStockStrategy,
)

# --- fixed run parameters (must be recorded verbatim in the paper) ---
REPO_URL = "https://github.com/heechan9/bunkering-ai"
MAIN_COMMIT_SHA = "f915df9922b63bade92c2efba0f7c74f66c21316"
PUBLIC_DATA_SHA256 = (
    "b42537ebde057e87ef15f91a8c0fca6ab0ee010ff557b78a531112d4e79da1b7"
)

ENV_CONFIG = {"n_ports": 3, "max_steps": 30, "min_safe_fuel": 0.15}
N_EPISODES = 200
BASE_SEED = 42  # seed range used: 42 .. 241 inclusive (200 seeds)
SEED_RANGE = (BASE_SEED, BASE_SEED + N_EPISODES - 1)  # (42, 241)

STRATEGIES = {
    "fixed_fueling": FixedFuelingStrategy(),
    "price_reactive": PriceReactiveStrategy(),
    "safe_stock": SafeStockStrategy(),
}
STABILITY_WINDOWS = [20, 50, 100, 150, 200]


def run_episode(strategy, seed: int) -> dict:
    env = BunkeringEnv(**ENV_CONFIG)
    obs, _ = env.reset(seed=seed)
    total_reward = 0.0
    bunkering_count = 0
    step_index = 0
    while True:
        action = strategy.select_action(env, obs, step_index)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        bunkering_count += int(info["actual_bunker_amount"] > env._BUNKER_AMOUNT_EPSILON)
        step_index += 1
        if terminated or truncated:
            break
    end_reason = info["end_reason"]
    return {
        "seed": seed,
        "episode": seed - BASE_SEED,  # seed 42 -> episode 0 ... seed 241 -> episode 199
        "reward": total_reward,
        "synthetic_cost_index": info["cumulative_cost_index"],
        "success": end_reason == "arrived",
        "fuel_depletion": end_reason == "fuel_depleted",
        "bunkering_count": bunkering_count,
        "termination_reason": end_reason,
    }


def main() -> None:
    all_rows = []
    for name, strat in STRATEGIES.items():
        for i in range(N_EPISODES):
            seed = BASE_SEED + i
            row = run_episode(strat, seed)
            row["policy"] = name
            all_rows.append(row)

    raw_path = Path("independent_eval_raw_with_episode.csv")
    fieldnames = [
        "policy", "seed", "episode", "reward", "synthetic_cost_index",
        "success", "fuel_depletion", "bunkering_count", "termination_reason",
    ]
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    # summary (ddof=0 / population std, explicit)
    summary_rows = []
    for name in STRATEGIES:
        rows = [r for r in all_rows if r["policy"] == name]
        rewards = np.array([r["reward"] for r in rows])
        sci = np.array([r["synthetic_cost_index"] for r in rows])
        succ = np.array([1.0 if r["success"] else 0.0 for r in rows])
        depl = np.array([1.0 if r["fuel_depletion"] else 0.0 for r in rows])
        bcount = np.array([r["bunkering_count"] for r in rows])
        term = {"arrived": 0, "fuel_depleted": 0, "timeout": 0}
        for r in rows:
            term[r["termination_reason"]] += 1
        summary_rows.append({
            "policy": name,
            "episodes": len(rows),
            "reward_mean": rewards.mean(), "reward_std_ddof0": rewards.std(ddof=0),
            "sci_mean": sci.mean(), "sci_std_ddof0": sci.std(ddof=0),
            "success_mean": succ.mean(), "success_std_ddof0": succ.std(ddof=0),
            "fuel_depletion_mean": depl.mean(), "fuel_depletion_std_ddof0": depl.std(ddof=0),
            "bunkering_count_mean": bcount.mean(), "bunkering_count_std_ddof0": bcount.std(ddof=0),
            "term_arrived": term["arrived"],
            "term_fuel_depleted": term["fuel_depleted"],
            "term_timeout": term["timeout"],
        })

    # cumulative stability windows (NOT independent samples, all start at BASE_SEED)
    stability_rows = []
    for name in STRATEGIES:
        rows = [r for r in all_rows if r["policy"] == name]
        for n in STABILITY_WINDOWS:
            window = [r for r in rows if r["episode"] < n]  # episodes 0..n-1, i.e. seeds 42..42+n-1
            rewards = np.array([r["reward"] for r in window])
            arrived = sum(1 for r in window if r["termination_reason"] == "arrived")
            stability_rows.append({
                "policy": name,
                "cumulative_seed_window": f"seed {BASE_SEED}-{BASE_SEED+n-1} (episodes 0-{n-1})",
                "n_seeds_in_window": n,
                "arrived_count": arrived,
                "arrival_rate": round(arrived / n, 4),
                "reward_mean": round(float(rewards.mean()), 4),
                "reward_std_ddof0": round(float(rewards.std(ddof=0)), 4),
            })

    # manifest
    manifest = {
        "purpose": "Independent robustness check of the 3 Rule-based strategies "
                   "over an extended seed range; separate from and does not "
                   "modify the repository's official 100-seed 4-policy evaluation.",
        "repository": REPO_URL,
        "main_commit_sha_at_verification_time": MAIN_COMMIT_SHA,
        "public_data_utf8_copy_sha256": PUBLIC_DATA_SHA256,
        "env_config": ENV_CONFIG,
        "seed_range": {"start": SEED_RANGE[0], "end": SEED_RANGE[1], "count": N_EPISODES},
        "policies": list(STRATEGIES.keys()),
        "std_convention": "population standard deviation (numpy.std, ddof=0)",
        "cases": [
            {"policy": name, "seed": BASE_SEED + i, "episode": i, "env_config": ENV_CONFIG}
            for name in STRATEGIES
            for i in range(N_EPISODES)
        ],
    }
    with open("independent_eval_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    pd.DataFrame(summary_rows).to_csv("independent_eval_summary_final.csv", index=False)
    pd.DataFrame(stability_rows).to_csv("independent_eval_stability_final.csv", index=False)

    print(pd.DataFrame(summary_rows).to_string(index=False))
    print()
    print(pd.DataFrame(stability_rows).to_string(index=False))


if __name__ == "__main__":
    main()
