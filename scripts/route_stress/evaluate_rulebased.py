"""Separate 100-seed Rule-based evaluation under route-impact assumptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from envs.bunkering_env import BunkeringEnv
from route_stress import get_route_impact
from scripts.baseline import (
    FixedFuelingStrategy,
    PriceReactiveStrategy,
    SafeStockStrategy,
)


SCENARIOS = ("normal", "suez_cape_representative", "hormuz_observation_only")
STRATEGIES = (
    FixedFuelingStrategy(),
    PriceReactiveStrategy(),
    SafeStockStrategy(),
)
DEFAULT_OUTPUT_DIR = Path("results/route_stress/rulebased_100seed")


def run_episode(strategy, scenario_id: str, seed: int, episode: int) -> dict:
    impact = get_route_impact(scenario_id)
    env = BunkeringEnv(**impact.env_config())
    observation, _ = env.reset(seed=seed)
    total_reward = 0.0
    bunkering_count = 0
    step_index = 0
    while True:
        action = strategy.select_action(env, observation, step_index)
        observation, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        bunkering_count += int(
            info["actual_bunker_amount"] > env._BUNKER_AMOUNT_EPSILON
        )
        step_index += 1
        if terminated or truncated:
            break
    return {
        "scenario_id": scenario_id,
        "assumption_id": impact.assumption_id,
        "policy": strategy.name,
        "seed": seed,
        "episode": episode,
        "max_steps": impact.scenario_max_steps,
        "distance_multiplier": impact.distance_multiplier,
        "steps": step_index,
        "reward": total_reward,
        "synthetic_cost_index": info["cumulative_cost_index"],
        "success": info["end_reason"] == "arrived",
        "fuel_depletion": info["end_reason"] == "fuel_depleted",
        "bunkering_count": bunkering_count,
        "termination_reason": info["end_reason"],
    }


def run_evaluation(n_seeds: int = 100, base_seed: int = 42) -> pd.DataFrame:
    if n_seeds < 1:
        raise ValueError("n_seeds must be at least 1")
    rows = []
    for scenario_id in SCENARIOS:
        for strategy in STRATEGIES:
            for episode in range(n_seeds):
                rows.append(
                    run_episode(strategy, scenario_id, base_seed + episode, episode)
                )
    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario_id, policy), group in raw.groupby(
        ["scenario_id", "policy"], sort=True
    ):
        sci_per_step = group["synthetic_cost_index"] / group["steps"]
        bunkering_per_step = group["bunkering_count"] / group["steps"]
        rows.append(
            {
                "scenario_id": scenario_id,
                "policy": policy,
                "episodes": len(group),
                "max_steps": int(group["max_steps"].iloc[0]),
                "distance_multiplier": float(group["distance_multiplier"].iloc[0]),
                "steps_mean": float(group["steps"].mean()),
                "reward_mean": float(group["reward"].mean()),
                "reward_std_ddof0": float(np.std(group["reward"], ddof=0)),
                "sci_mean": float(group["synthetic_cost_index"].mean()),
                "sci_per_step_mean": float(sci_per_step.mean()),
                "sci_per_30_steps_mean": float((sci_per_step * 30).mean()),
                "success_rate": float(group["success"].mean()),
                "fuel_depletion_rate": float(group["fuel_depletion"].mean()),
                "bunkering_count_mean": float(group["bunkering_count"].mean()),
                "bunkering_per_step_mean": float(bunkering_per_step.mean()),
                "bunkering_per_30_steps_mean": float(
                    (bunkering_per_step * 30).mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    raw = run_evaluation(args.seeds, args.base_seed)
    summary = summarize(raw)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.output_dir / "raw.csv", index=False)
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    manifest = {
        "purpose": "Exploratory Rule-based route-stress evaluation",
        "separate_from_official_evaluation": True,
        "base_seed": args.base_seed,
        "n_seeds": args.seeds,
        "scenarios": [get_route_impact(value).to_manifest() for value in SCENARIOS],
        "scenario_roles": {
            "normal": "quantitative reference",
            "suez_cape_representative": "quantitative synthetic sensitivity",
            "hormuz_observation_only": "contextual negative control; no quantitative shock applied",
        },
        "policies": [strategy.name for strategy in STRATEGIES],
        "std_convention": "population standard deviation (numpy.std, ddof=0)",
        "normalization": (
            "Per-step metrics divide each episode total by its realized step count; "
            "per-30-step metrics rescale that episode rate by 30 before averaging."
        ),
        "claim_boundary": (
            "Representative synthetic scenario; not actual-voyage, fuel, cost, "
            "deployment, or realized-diversion validation."
        ),
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(summary.to_string(index=False))
    print(f"\nwrote {args.output_dir}")


if __name__ == "__main__":
    main()
