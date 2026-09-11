"""Evaluate V1.5 consumption and horizon sensitivity under one fair contract.

The experiment is intentionally separate from the canonical policy comparison.
It changes only an explicit environment parameter, uses the same cases for every
policy, and performs greedy inference with a frozen Double DQN checkpoint.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from envs.bunkering_env import BunkeringEnv
from scripts.baseline import (
    FixedFuelingStrategy,
    PriceReactiveStrategy,
    SafeStockStrategy,
)
from scripts.evaluate import (
    CHECKPOINT_ARCHIVE,
    DoubleDQNPolicy,
    Policy,
    file_sha256,
    load_dqn_policy,
)


DEFAULT_CHECKPOINT = Path("checkpoints/dqn_final.pt")
DEFAULT_OUTPUT_DIR = Path("results/robustness/v1_5")
REFERENCE_SCENARIOS = {
    "fuel_consumption": "consumption_baseline",
    "horizon": "horizon_43_reference",
}
EFFECT_METRICS = (
    "reward_mean",
    "sci_per_step_mean",
    "success_rate",
    "fuel_depletion_rate",
    "bunkering_per_30_steps_mean",
)


@dataclass(frozen=True)
class RobustnessScenario:
    scenario_id: str
    family: str
    max_steps: int
    fuel_consumption_per_step: float
    reference: bool = False

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if not np.isfinite(self.fuel_consumption_per_step) or not (
            0.0 < self.fuel_consumption_per_step <= 1.0
        ):
            raise ValueError("fuel_consumption_per_step must be in (0, 1]")

    @property
    def consumption_multiplier(self) -> float:
        return (
            self.fuel_consumption_per_step
            / BunkeringEnv._FUEL_CONSUMPTION_PER_STEP
        )

    def env_config(self) -> dict[str, int | float]:
        return {
            "n_ports": 3,
            "max_steps": self.max_steps,
            "min_safe_fuel": 0.15,
            "fuel_consumption_per_step": self.fuel_consumption_per_step,
        }

    def to_manifest(self) -> dict:
        return {**asdict(self), "consumption_multiplier": self.consumption_multiplier}


SCENARIOS: tuple[RobustnessScenario, ...] = (
    RobustnessScenario("consumption_minus_10", "fuel_consumption", 30, 0.045),
    RobustnessScenario(
        "consumption_baseline", "fuel_consumption", 30, 0.05, reference=True
    ),
    RobustnessScenario("consumption_plus_10", "fuel_consumption", 30, 0.055),
    RobustnessScenario("consumption_plus_20", "fuel_consumption", 30, 0.06),
    RobustnessScenario("horizon_42", "horizon", 42, 0.05),
    RobustnessScenario(
        "horizon_43_reference", "horizon", 43, 0.05, reference=True
    ),
    RobustnessScenario("horizon_44", "horizon", 44, 0.05),
)


def run_episode(
    policy: Policy, scenario: RobustnessScenario, seed: int, episode: int
) -> dict:
    env = BunkeringEnv(**scenario.env_config())
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
        "scenario_id": scenario.scenario_id,
        "scenario_family": scenario.family,
        "reference_scenario": scenario.reference,
        "policy": policy.name,
        "seed": seed,
        "episode": episode,
        "max_steps": scenario.max_steps,
        "fuel_consumption_per_step": scenario.fuel_consumption_per_step,
        "consumption_multiplier": scenario.consumption_multiplier,
        "steps": step_index,
        "reward": total_reward,
        "synthetic_cost_index": info["cumulative_cost_index"],
        "success": info["end_reason"] == "arrived",
        "fuel_depletion": info["end_reason"] == "fuel_depleted",
        "bunkering_count": bunkering_count,
        "termination_reason": info["end_reason"],
    }


def run_evaluation(
    policies: Mapping[str, Policy],
    *,
    n_episodes: int = 100,
    base_seed: int = 42,
    scenarios: Sequence[RobustnessScenario] = SCENARIOS,
) -> pd.DataFrame:
    if n_episodes < 1:
        raise ValueError("n_episodes must be at least 1")
    if not policies:
        raise ValueError("at least one policy is required")
    if not scenarios:
        raise ValueError("at least one scenario is required")
    for policy in policies.values():
        if isinstance(policy, DoubleDQNPolicy):
            policy.agent.policy_net.eval()
    rows = [
        run_episode(policy, scenario, base_seed + episode, episode)
        for scenario in scenarios
        for policy in policies.values()
        for episode in range(n_episodes)
    ]
    return pd.DataFrame(rows)


def _tail_mean(values: pd.Series, *, largest: bool) -> float:
    count = max(1, math.ceil(len(values) * 0.05))
    ordered = values.nlargest(count) if largest else values.nsmallest(count)
    return float(ordered.mean())


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    """Summarize central, normalized, safety, and empirical tail metrics."""
    rows: list[dict] = []
    for (scenario_id, policy), group in raw.groupby(
        ["scenario_id", "policy"], sort=True
    ):
        sci_per_step = group["synthetic_cost_index"] / group["steps"]
        bunkering_per_30 = group["bunkering_count"] / group["steps"] * 30
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_family": str(group["scenario_family"].iloc[0]),
                "reference_scenario": bool(group["reference_scenario"].iloc[0]),
                "policy": policy,
                "episodes": len(group),
                "max_steps": int(group["max_steps"].iloc[0]),
                "fuel_consumption_per_step": float(
                    group["fuel_consumption_per_step"].iloc[0]
                ),
                "consumption_multiplier": float(
                    group["consumption_multiplier"].iloc[0]
                ),
                "reward_mean": float(group["reward"].mean()),
                "reward_std_ddof0": float(np.std(group["reward"], ddof=0)),
                "reward_min": float(group["reward"].min()),
                "reward_bottom_5pct_mean": _tail_mean(
                    group["reward"], largest=False
                ),
                "sci_mean": float(group["synthetic_cost_index"].mean()),
                "sci_std_ddof0": float(
                    np.std(group["synthetic_cost_index"], ddof=0)
                ),
                "sci_max": float(group["synthetic_cost_index"].max()),
                "sci_top_5pct_mean": _tail_mean(
                    group["synthetic_cost_index"], largest=True
                ),
                "sci_per_step_mean": float(sci_per_step.mean()),
                "success_rate": float(group["success"].mean()),
                "fuel_depletion_rate": float(group["fuel_depletion"].mean()),
                "bunkering_count_mean": float(group["bunkering_count"].mean()),
                "bunkering_count_max": int(group["bunkering_count"].max()),
                "bunkering_per_30_steps_mean": float(bunkering_per_30.mean()),
            }
        )
    return pd.DataFrame(rows)


def paired_effects(summary: pd.DataFrame) -> pd.DataFrame:
    """Compare every scenario with its family reference for each policy."""
    rows: list[dict] = []
    for family, reference_id in REFERENCE_SCENARIOS.items():
        family_rows = summary.loc[summary["scenario_family"] == family]
        for policy in sorted(family_rows["policy"].unique()):
            policy_rows = family_rows.loc[family_rows["policy"] == policy]
            reference = policy_rows.loc[policy_rows["scenario_id"] == reference_id]
            if len(reference) != 1:
                raise ValueError(
                    f"expected one reference row: family={family}, policy={policy}"
                )
            for _, scenario_row in policy_rows.iterrows():
                if str(scenario_row["scenario_id"]) == reference_id:
                    continue
                for metric in EFFECT_METRICS:
                    baseline = float(reference.iloc[0][metric])
                    stressed = float(scenario_row[metric])
                    rows.append(
                        {
                            "scenario_family": family,
                            "reference_scenario": reference_id,
                            "scenario_id": str(scenario_row["scenario_id"]),
                            "policy": policy,
                            "metric": metric,
                            "reference_value": baseline,
                            "scenario_value": stressed,
                            "absolute_change": stressed - baseline,
                            "percent_change": (
                                100.0 * (stressed - baseline) / baseline
                                if metric != "reward_mean" and baseline != 0.0
                                else np.nan
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def plot_robustness(summary: pd.DataFrame, output_path: Path) -> None:
    """Plot the two scenario families without converting SCI to real cost."""
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    panels = (
        ("fuel_consumption", "consumption_multiplier", "success_rate", "Success rate"),
        (
            "fuel_consumption",
            "consumption_multiplier",
            "sci_per_step_mean",
            "SCI / step",
        ),
        ("horizon", "max_steps", "success_rate", "Success rate"),
        ("horizon", "max_steps", "sci_per_step_mean", "SCI / step"),
    )
    for axis, (family, x_field, metric, title) in zip(axes.flatten(), panels):
        family_rows = summary.loc[summary["scenario_family"] == family]
        for policy, group in family_rows.groupby("policy", sort=True):
            ordered = group.sort_values(x_field)
            axis.plot(
                ordered[x_field],
                ordered[metric],
                marker="o",
                label=policy,
            )
        axis.set_title(f"{family.replace('_', ' ').title()}: {title}")
        axis.set_xlabel(
            "Consumption multiplier" if family == "fuel_consumption" else "Max steps"
        )
        axis.grid(alpha=0.3)
    axes[0, 0].set_ylim(-0.02, 1.02)
    axes[1, 0].set_ylim(-0.02, 1.02)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=4)
    figure.suptitle("V1.5 synthetic robustness sensitivity")
    figure.tight_layout(rect=(0, 0.06, 1, 0.96))
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated V1.5 fuel-consumption and horizon sensitivity."
    )
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    policy = load_dqn_policy(
        args.checkpoint,
        {
            "n_ports": 3,
            "max_steps": 30,
            "min_safe_fuel": 0.15,
            "fuel_consumption_per_step": BunkeringEnv._FUEL_CONSUMPTION_PER_STEP,
        },
    )
    policies: dict[str, Policy] = {
        FixedFuelingStrategy().name: FixedFuelingStrategy(),
        PriceReactiveStrategy().name: PriceReactiveStrategy(),
        SafeStockStrategy().name: SafeStockStrategy(),
        policy.name: policy,
    }
    raw = run_evaluation(
        policies, n_episodes=args.episodes, base_seed=args.base_seed
    )
    summary = summarize(raw)
    effects = paired_effects(summary)
    checkpoint_archive = (
        dict(CHECKPOINT_ARCHIVE)
        if args.checkpoint.name == CHECKPOINT_ARCHIVE["asset_name"]
        else {
            "kind": "local_file",
            "status": "not_archived",
            "claim_boundary": "Reproduction requires the exact recorded SHA-256.",
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.output_dir / "raw.csv", index=False)
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    effects.to_csv(args.output_dir / "paired_effects.csv", index=False)
    plot_robustness(summary, args.output_dir / "robustness_comparison.png")
    manifest = {
        "schema_version": "bunkering-ai-v1.5-robustness/v1",
        "purpose": "Exploratory hidden-consumption and horizon sensitivity",
        "separate_from_official_evaluation": True,
        "inference_only": True,
        "base_seed": args.base_seed,
        "n_episodes": args.episodes,
        "policies": list(policies),
        "scenarios": [scenario.to_manifest() for scenario in SCENARIOS],
        "checkpoint": {
            "path": args.checkpoint.name,
            "sha256": file_sha256(args.checkpoint),
            "archive": checkpoint_archive,
            "metadata": policy.agent.checkpoint_metadata,
        },
        "tail_definition": (
            "Empirical 5% tail with ceil(0.05 * episodes), minimum one case."
        ),
        "std_convention": "population standard deviation (numpy.std, ddof=0)",
        "generated_artifacts": [
            "raw.csv",
            "summary.csv",
            "paired_effects.csv",
            "robustness_comparison.png",
        ],
        "percent_change_note": (
            "Percent change is omitted for signed reward and zero references; "
            "absolute change remains available."
        ),
        "claim_boundary": (
            "Synthetic robustness sensitivity only. Consumption is an unobserved "
            "transition shock, not a calibrated SFC/engine model. Horizon cases are "
            "not measured voyage distance or duration."
        ),
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(summary.to_string(index=False))
    print("\nPaired effects written to paired_effects.csv")
    print(f"\nwrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
