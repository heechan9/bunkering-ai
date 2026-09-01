"""Run the official same-condition comparison of rule-based policies and Double DQN.

Every policy is executed on an identical, pre-validated set of
``(episode, seed, env_config)`` cases, so no policy can gain an advantage from a
different environment configuration or seed order. The plan is checked by
``evaluation.contract.validate_fair_evaluation_plan`` *before* a single episode
runs; a plan that is not fair aborts the run instead of producing results.

Run from the project root::

    python scripts/train.py --episodes 1000 --seed 42
    python scripts/evaluate.py --episodes 20 --seed 42

This script reports what the runs actually produced. It does not assume, assert,
or rank Double DQN against the rule-based baselines.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import matplotlib

# Select a headless backend before pyplot binds one, so the script runs on CI
# and over SSH exactly as it does on a desktop.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import yaml

# Allow direct execution via ``python scripts/evaluate.py``.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.dqn import DQNAgent
from envs.bunkering_env import BunkeringEnv
from evaluation.contract import (
    CSV_FIELDS,
    TERMINATION_REASONS,
    AggregateResult,
    EpisodeResult,
    EvaluationCase,
    aggregate_results,
    validate_fair_evaluation_plan,
)
from scripts.baseline import (
    FixedFuelingStrategy,
    PriceReactiveStrategy,
    SafeStockStrategy,
)

DQN_POLICY_NAME = "double_dqn"
# Stable reporting order: the three rule-based baselines, then the learned policy.
RULE_BASED_POLICY_NAMES = ("fixed_fueling", "price_reactive", "safe_stock")
# Termination reasons are reported in a fixed order so CSV columns stay stable
# across runs even when a reason never occurs.
TERMINATION_REASON_ORDER = ("arrived", "fuel_depleted", "timeout")

SUMMARY_METRIC_NAMES = (
    "reward",
    "synthetic_cost_index",
    "success",
    "fuel_depletion",
    "bunkering_count",
)
SUMMARY_FIELDS = (
    ("policy", "episodes")
    + tuple(
        f"{metric}_{statistic}"
        for metric in SUMMARY_METRIC_NAMES
        for statistic in ("mean", "std")
    )
    + tuple(f"termination_{reason}" for reason in TERMINATION_REASON_ORDER)
)


class Policy(Protocol):
    """Decision interface shared by rule-based strategies and the DQN policy."""

    name: str

    def select_action(
        self, env: BunkeringEnv, observation: np.ndarray, step_index: int
    ) -> int: ...


@dataclass(frozen=True)
class DoubleDQNPolicy:
    """Greedy wrapper exposing a trained checkpoint through the Policy interface."""

    agent: DQNAgent
    name: str = DQN_POLICY_NAME

    def select_action(
        self, env: BunkeringEnv, observation: np.ndarray, step_index: int
    ) -> int:
        del env, step_index
        return self.agent.greedy_action(observation)


def load_env_config(config_path: Path) -> dict[str, Any]:
    """Read the single environment configuration shared by every policy."""
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    env_config = config.get("env")
    if not isinstance(env_config, Mapping):
        raise ValueError(f"{config_path} does not define an 'env' mapping")
    return dict(env_config)


def load_dqn_policy(
    checkpoint_path: Path, env_config: Mapping[str, Any]
) -> DoubleDQNPolicy:
    """Load a checkpoint and reject it if it cannot act on this environment.

    A silently mismatched checkpoint would still emit numbers, so the shapes are
    compared against the evaluation environment before any episode is run.
    """
    if not checkpoint_path.is_file():
        raise FileNotFoundError(
            f"checkpoint not found: {checkpoint_path}\n"
            "Train one first, e.g. python scripts/train.py --episodes 1000 --seed 42"
        )

    agent = DQNAgent.load_checkpoint(checkpoint_path)
    reference_env = BunkeringEnv(**env_config)
    expected_state_dim = int(reference_env.observation_space.shape[0])
    expected_action_dim = int(reference_env.action_space.n)
    if (agent.state_dim, agent.action_dim) != (expected_state_dim, expected_action_dim):
        raise ValueError(
            "checkpoint does not match the evaluation environment: checkpoint has "
            f"state_dim={agent.state_dim}, action_dim={agent.action_dim}; environment "
            f"needs state_dim={expected_state_dim}, action_dim={expected_action_dim}"
        )

    agent.policy_net.eval()
    return DoubleDQNPolicy(agent=agent)


def build_evaluation_plan(
    policy_names: Sequence[str],
    *,
    n_episodes: int,
    base_seed: int,
    env_config: Mapping[str, Any],
) -> list[EvaluationCase]:
    """Build and validate one identical case set per policy."""
    if n_episodes < 1:
        raise ValueError("n_episodes must be at least 1")

    cases = [
        EvaluationCase(
            seed=base_seed + episode_offset,
            episode=episode_offset,
            policy=policy_name,
            env_config=dict(env_config),
        )
        for policy_name in policy_names
        for episode_offset in range(n_episodes)
    ]
    validate_fair_evaluation_plan(cases, policy_names)
    return cases


def run_episode(policy: Policy, case: EvaluationCase) -> EpisodeResult:
    """Run one seeded episode and convert it into a validated contract record."""
    env = BunkeringEnv(**case.env_config)
    observation, _ = env.reset(seed=case.seed)
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

    end_reason = info["end_reason"]
    if end_reason not in TERMINATION_REASONS:
        raise ValueError(
            f"environment returned unsupported end_reason {end_reason!r} for "
            f"policy {case.policy!r} seed {case.seed}"
        )

    return EpisodeResult(
        seed=case.seed,
        episode=case.episode,
        policy=case.policy,
        reward=total_reward,
        synthetic_cost_index=info["cumulative_cost_index"],
        success=end_reason == "arrived",
        fuel_depletion=end_reason == "fuel_depleted",
        bunkering_count=bunkering_count,
        termination_reason=end_reason,
    )


def run_evaluation(
    policies: Mapping[str, Policy], cases: Sequence[EvaluationCase]
) -> list[EpisodeResult]:
    """Execute every planned case, so results cannot drift from the fair plan."""
    missing = sorted({case.policy for case in cases} - set(policies))
    if missing:
        raise KeyError(f"no runner supplied for planned policies: {missing}")
    return [run_episode(policies[case.policy], case) for case in cases]


def count_termination_reasons(
    results: Sequence[EpisodeResult],
) -> dict[str, dict[str, int]]:
    """Count end reasons per policy, including reasons that never occurred."""
    counts = {
        policy: dict.fromkeys(TERMINATION_REASON_ORDER, 0)
        for policy in {result.policy for result in results}
    }
    for result in results:
        counts[result.policy][result.termination_reason] += 1
    return counts


def _ordered_policies(present: set[str], policy_names: Sequence[str]) -> list[str]:
    """Report declared policies first, then any extras, without dropping either."""
    ordered = [name for name in policy_names if name in present]
    return ordered + sorted(present - set(ordered))


def write_results_csv(results: Sequence[EpisodeResult], path: Path) -> Path:
    """Write the canonical per-episode CSV in the contract's column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for result in results:
            row = result.to_row()
            # The audit parses these as strict lowercase 'true'/'false'.
            row["success"] = str(row["success"]).lower()
            row["fuel_depletion"] = str(row["fuel_depletion"]).lower()
            writer.writerow(row)
    return path


def write_manifest_json(
    cases: Sequence[EvaluationCase],
    policy_names: Sequence[str],
    path: Path,
    *,
    provenance: Mapping[str, Any],
) -> Path:
    """Record the exact conditions every policy ran under."""
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "policies": list(policy_names),
        "cases": [
            {
                "seed": case.seed,
                "episode": case.episode,
                "policy": case.policy,
                "env_config": dict(case.env_config),
            }
            for case in cases
        ],
        **dict(provenance),
    }
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(manifest, json_file, ensure_ascii=False, indent=2)
        json_file.write("\n")
    return path


def write_per_policy_csv(
    results: Sequence[EpisodeResult], policy_names: Sequence[str], directory: Path
) -> list[Path]:
    """Write one raw CSV per policy alongside the combined canonical CSV."""
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    present = {result.policy for result in results}
    for policy in _ordered_policies(present, policy_names):
        policy_results = [result for result in results if result.policy == policy]
        written.append(
            write_results_csv(policy_results, directory / f"raw_{policy}.csv")
        )
    return written


def write_summary_csv(
    aggregates: Sequence[AggregateResult],
    termination_counts: Mapping[str, Mapping[str, int]],
    policy_names: Sequence[str],
    path: Path,
) -> Path:
    """Write per-policy mean/std plus the termination-reason breakdown."""
    path.parent.mkdir(parents=True, exist_ok=True)
    by_policy = {aggregate.policy: aggregate for aggregate in aggregates}

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(SUMMARY_FIELDS))
        writer.writeheader()
        for policy in _ordered_policies(set(by_policy), policy_names):
            row = asdict(by_policy[policy])
            counts = termination_counts.get(policy, {})
            for reason in TERMINATION_REASON_ORDER:
                row[f"termination_{reason}"] = counts.get(reason, 0)
            writer.writerow(row)
    return path


def write_termination_csv(
    termination_counts: Mapping[str, Mapping[str, int]],
    policy_names: Sequence[str],
    path: Path,
) -> Path:
    """Write the termination-reason contingency table as its own artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["policy", *TERMINATION_REASON_ORDER, "episodes"])
        for policy in _ordered_policies(set(termination_counts), policy_names):
            counts = termination_counts[policy]
            values = [counts.get(reason, 0) for reason in TERMINATION_REASON_ORDER]
            writer.writerow([policy, *values, sum(values)])
    return path


def plot_comparison(
    aggregates: Sequence[AggregateResult],
    termination_counts: Mapping[str, Mapping[str, int]],
    policy_names: Sequence[str],
    path: Path,
) -> Path:
    """Draw the metric panels used in the report, with std shown as error bars."""
    path.parent.mkdir(parents=True, exist_ok=True)
    by_policy = {aggregate.policy: aggregate for aggregate in aggregates}
    ordered = _ordered_policies(set(by_policy), policy_names)
    positions = np.arange(len(ordered))

    panels = (
        ("Mean episode reward", "reward_mean", "reward_std"),
        (
            "Mean Synthetic Cost Index",
            "synthetic_cost_index_mean",
            "synthetic_cost_index_std",
        ),
        ("Success rate", "success_mean", "success_std"),
        ("Fuel depletion rate", "fuel_depletion_mean", "fuel_depletion_std"),
        ("Mean bunkering count", "bunkering_count_mean", "bunkering_count_std"),
    )

    figure, axes = plt.subplots(2, 3, figsize=(16, 9))
    flat_axes = axes.flatten()
    for axis, (title, mean_field, std_field) in zip(flat_axes, panels):
        means = [getattr(by_policy[policy], mean_field) for policy in ordered]
        stds = [getattr(by_policy[policy], std_field) for policy in ordered]
        axis.bar(positions, means, yerr=stds, capsize=4, color="#4c72b0")
        axis.set_title(title)
        axis.set_xticks(positions)
        axis.set_xticklabels(ordered, rotation=20, ha="right")
        axis.axhline(0.0, color="#444444", linewidth=0.8)
        axis.grid(axis="y", alpha=0.3)

    termination_axis = flat_axes[len(panels)]
    bottoms = np.zeros(len(ordered))
    for reason in TERMINATION_REASON_ORDER:
        values = np.array(
            [termination_counts.get(policy, {}).get(reason, 0) for policy in ordered],
            dtype=float,
        )
        termination_axis.bar(positions, values, bottom=bottoms, label=reason)
        bottoms += values
    termination_axis.set_title("Termination reason (episode count)")
    termination_axis.set_xticks(positions)
    termination_axis.set_xticklabels(ordered, rotation=20, ha="right")
    termination_axis.legend(fontsize="small")
    termination_axis.grid(axis="y", alpha=0.3)

    figure.suptitle(
        "Same-condition policy comparison (identical seeds, episodes, env config)"
    )
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def print_summary(
    aggregates: Sequence[AggregateResult],
    termination_counts: Mapping[str, Mapping[str, int]],
    policy_names: Sequence[str],
) -> None:
    """Print the observed numbers without ranking or interpreting them."""
    by_policy = {aggregate.policy: aggregate for aggregate in aggregates}
    ordered = _ordered_policies(set(by_policy), policy_names)

    header = (
        f"{'policy':<16}{'eps':>5}{'reward mean/std':>24}"
        f"{'cost index mean/std':>28}{'success':>9}{'fuel_dep':>10}"
        f"{'bunkers mean/std':>20}"
    )
    print(header)
    print("-" * len(header))
    for policy in ordered:
        aggregate = by_policy[policy]
        print(
            f"{policy:<16}{aggregate.episodes:>5}"
            f"{aggregate.reward_mean:>15.4f} / {aggregate.reward_std:>6.4f}"
            f"{aggregate.synthetic_cost_index_mean:>17.1f} / {aggregate.synthetic_cost_index_std:>8.1f}"
            f"{aggregate.success_mean:>9.3f}{aggregate.fuel_depletion_mean:>10.3f}"
            f"{aggregate.bunkering_count_mean:>13.2f} / {aggregate.bunkering_count_std:>4.2f}"
        )

    print("\ntermination reasons")
    for policy in ordered:
        counts = termination_counts.get(policy, {})
        breakdown = "  ".join(
            f"{reason}={counts.get(reason, 0)}" for reason in TERMINATION_REASON_ORDER
        )
        print(f"  {policy:<16}{breakdown}")


def file_sha256(path: Path) -> str:
    """Hash a file so a result set can be traced back to exact weights."""
    digest = hashlib.sha256()
    with path.open("rb") as binary_file:
        for chunk in iter(lambda: binary_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate rule-based baselines and a trained Double DQN checkpoint "
            "under identical seeds, episodes, and environment configuration."
        )
    )
    parser.add_argument("--episodes", type=int, default=20, help="Episodes per policy")
    parser.add_argument("--seed", type=int, default=42, help="First episode seed")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "dqn.yaml",
        help="YAML file whose 'env' section defines the shared environment",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=PROJECT_ROOT / "checkpoints" / "dqn_final.pt",
        help="Trained Double DQN checkpoint to evaluate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="Directory for the canonical CSV, manifest, and derived artifacts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    env_config = load_env_config(args.config)
    dqn_policy = load_dqn_policy(args.checkpoint, env_config)
    policies: dict[str, Policy] = {
        FixedFuelingStrategy().name: FixedFuelingStrategy(),
        PriceReactiveStrategy().name: PriceReactiveStrategy(),
        SafeStockStrategy().name: SafeStockStrategy(),
        dqn_policy.name: dqn_policy,
    }
    policy_names = list(RULE_BASED_POLICY_NAMES) + [dqn_policy.name]

    cases = build_evaluation_plan(
        policy_names,
        n_episodes=args.episodes,
        base_seed=args.seed,
        env_config=env_config,
    )
    results = run_evaluation(policies, cases)
    aggregates = aggregate_results(results)
    termination_counts = count_termination_reasons(results)

    output_dir: Path = args.output_dir
    evaluation_dir = output_dir / "evaluation"
    results_path = write_results_csv(results, output_dir / "evaluation_results.csv")
    manifest_path = write_manifest_json(
        cases,
        policy_names,
        output_dir / "evaluation_manifest.json",
        provenance={
            "n_episodes": int(args.episodes),
            "base_seed": int(args.seed),
            "env_config": dict(env_config),
            "checkpoint": {
                "path": args.checkpoint.name,
                "sha256": file_sha256(args.checkpoint),
                "metadata": dqn_policy.agent.checkpoint_metadata,
            },
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    per_policy_paths = write_per_policy_csv(results, policy_names, evaluation_dir)
    summary_path = write_summary_csv(
        aggregates, termination_counts, policy_names, evaluation_dir / "summary.csv"
    )
    termination_path = write_termination_csv(
        termination_counts, policy_names, evaluation_dir / "termination_reasons.csv"
    )
    plot_path = plot_comparison(
        aggregates, termination_counts, policy_names, evaluation_dir / "comparison.png"
    )

    print_summary(aggregates, termination_counts, policy_names)
    print(f"\nCanonical per-episode CSV: {results_path}")
    print(f"Evaluation manifest:       {manifest_path}")
    print(f"Summary CSV:               {summary_path}")
    print(f"Termination CSV:           {termination_path}")
    print(f"Comparison figure:         {plot_path}")
    for path in per_policy_paths:
        print(f"Per-policy raw CSV:        {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
