"""Evaluate the published Double DQN checkpoint under route stress.

This exploratory run loads one frozen checkpoint and only performs greedy
inference.  It is deliberately separate from the canonical four-policy result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from envs.bunkering_env import BunkeringEnv
from route_stress import get_route_impact
from scripts.evaluate import (
    CHECKPOINT_ARCHIVE,
    DoubleDQNPolicy,
    file_sha256,
    load_dqn_policy,
)
from scripts.route_stress.evaluate_rulebased import SCENARIOS, summarize


DEFAULT_CHECKPOINT = Path("checkpoints/dqn_final.pt")
DEFAULT_OUTPUT_DIR = Path("results/route_stress/frozen_double_dqn_100seed")


def run_episode(
    policy: DoubleDQNPolicy, scenario_id: str, seed: int, episode: int
) -> dict:
    """Run greedy inference without training or mutating the checkpoint."""
    impact = get_route_impact(scenario_id)
    env = BunkeringEnv(**impact.env_config())
    observation, _ = env.reset(seed=seed)
    total_reward = 0.0
    bunkering_count = 0
    step_index = 0
    while True:
        action = policy.select_action(env, observation, step_index)
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
        "policy": policy.name,
        "seed": seed,
        "episode": episode,
        "max_steps": impact.scenario_max_steps,
        "distance_multiplier": impact.distance_multiplier,
        "reward": total_reward,
        "synthetic_cost_index": info["cumulative_cost_index"],
        "success": info["end_reason"] == "arrived",
        "fuel_depletion": info["end_reason"] == "fuel_depleted",
        "bunkering_count": bunkering_count,
        "termination_reason": info["end_reason"],
    }


def run_evaluation(
    policy: DoubleDQNPolicy, n_seeds: int = 100, base_seed: int = 42
) -> pd.DataFrame:
    if n_seeds < 1:
        raise ValueError("n_seeds must be at least 1")
    policy.agent.policy_net.eval()
    rows = [
        run_episode(policy, scenario_id, base_seed + episode, episode)
        for scenario_id in SCENARIOS
        for episode in range(n_seeds)
    ]
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    normal_config = get_route_impact("normal").env_config()
    policy = load_dqn_policy(args.checkpoint, normal_config)
    raw = run_evaluation(policy, args.seeds, args.base_seed)
    summary = summarize(raw)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.output_dir / "raw.csv", index=False)
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    manifest = {
        "purpose": "Exploratory frozen Double DQN route-stress evaluation",
        "separate_from_official_evaluation": True,
        "inference_only": True,
        "base_seed": args.base_seed,
        "n_seeds": args.seeds,
        "scenarios": [get_route_impact(value).to_manifest() for value in SCENARIOS],
        "policies": [policy.name],
        "checkpoint": {
            "path": args.checkpoint.name,
            "sha256": file_sha256(args.checkpoint),
            "archive": dict(CHECKPOINT_ARCHIVE),
            "metadata": policy.agent.checkpoint_metadata,
        },
        "std_convention": "population standard deviation (numpy.std, ddof=0)",
        "claim_boundary": (
            "Single training-seed checkpoint in a representative synthetic scenario; "
            "not retraining, actual-voyage, fuel, cost, deployment, or "
            "realized-diversion validation."
        ),
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(summary.to_string(index=False))
    print(f"\nwrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
