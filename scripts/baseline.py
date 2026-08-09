"""Run reproducible rule-based baselines for :class:`BunkeringEnv`.

Run from the project root with ``python scripts/baseline.py``.  Results are
written to ``results/baseline_results.csv`` for later comparison with DQN.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

# Allow direct execution via ``python scripts/baseline.py``.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from envs.bunkering_env import BunkeringEnv


class Strategy(Protocol):
    """Decision interface shared by all non-learning baseline strategies."""

    name: str

    def select_action(
        self, env: BunkeringEnv, observation: np.ndarray, step_index: int
    ) -> int: ...


@dataclass(frozen=True)
class FixedFuelingStrategy:
    """Bunker once at departure, then sail without further bunkering."""

    name: str = "fixed_fueling"

    def select_action(
        self, env: BunkeringEnv, observation: np.ndarray, step_index: int
    ) -> int:
        del env, observation
        return 1 if step_index == 0 else 0


@dataclass(frozen=True)
class PriceReactiveStrategy:
    """Bunker when the current raw price is at least 5% below MA30."""

    discount_threshold: float = 0.05
    name: str = "price_reactive"

    def select_action(
        self, env: BunkeringEnv, observation: np.ndarray, step_index: int
    ) -> int:
        del observation, step_index
        return 1 if env.raw_fuel_price <= env.raw_price_ma30 * (1 - self.discount_threshold) else 0


def run_episode(
    strategy: Strategy, seed: int, episode: int
) -> dict[str, str | int | float | bool]:
    """Run one deterministic-seed episode and return a DQN-comparable record."""
    env = BunkeringEnv()
    observation, _ = env.reset(seed=seed)
    total_reward = 0.0
    n_bunkering = 0
    step_index = 0

    while True:
        action = strategy.select_action(env, observation, step_index)
        observation, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        n_bunkering += int(
            info["actual_bunker_amount"] > env._BUNKER_AMOUNT_EPSILON
        )
        step_index += 1

        if terminated or truncated:
            break

    return {
        "strategy": strategy.name,
        "episode": episode,
        "seed": seed,
        "total_reward": total_reward,
        "n_bunkering": n_bunkering,
        "cumulative_cost_index": info["cumulative_cost_index"],
        "end_reason": info["end_reason"],
        "voyage_success": info["voyage_success"],
    }


def write_results(
    records: list[dict[str, str | int | float | bool]], output_path: Path
) -> None:
    """Persist per-episode records in a stable CSV schema for DQN comparison."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "strategy",
        "episode",
        "seed",
        "total_reward",
        "n_bunkering",
        "cumulative_cost_index",
        "end_reason",
        "voyage_success",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def print_summary(records: list[dict[str, str | int | float | bool]]) -> None:
    """Print aggregate return statistics for each strategy."""
    print(f"{'strategy':<18} {'episodes':>8} {'mean_reward':>14} {'std_reward':>14}")
    for strategy_name in sorted({str(record["strategy"]) for record in records}):
        rewards = np.array(
            [float(record["total_reward"]) for record in records if record["strategy"] == strategy_name]
        )
        print(
            f"{strategy_name:<18} {len(rewards):>8} "
            f"{rewards.mean():>14.4f} {rewards.std():>14.4f}"
        )


def run_baselines(
    n_episodes: int = 20, base_seed: int = 42
) -> list[dict[str, str | int | float | bool]]:
    """Run both strategies on identical sequential seed sets."""
    if n_episodes < 1:
        raise ValueError("n_episodes must be at least 1")

    records: list[dict[str, str | int | float | bool]] = []
    strategies: tuple[Strategy, ...] = (FixedFuelingStrategy(), PriceReactiveStrategy())
    for strategy in strategies:
        for episode_offset in range(n_episodes):
            records.append(
                run_episode(
                    strategy,
                    seed=base_seed + episode_offset,
                    episode=episode_offset,
                )
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BunkeringEnv rule-based baselines.")
    parser.add_argument("--episodes", type=int, default=20, help="Episodes per strategy")
    parser.add_argument("--seed", type=int, default=42, help="First episode seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "baseline_results.csv",
        help="CSV output path",
    )
    args = parser.parse_args()

    records = run_baselines(n_episodes=args.episodes, base_seed=args.seed)
    write_results(records, args.output)
    print_summary(records)
    print(f"\nSaved per-episode results to: {args.output}")


if __name__ == "__main__":
    main()
