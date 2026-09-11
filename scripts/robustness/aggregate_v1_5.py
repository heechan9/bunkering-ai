"""Aggregate completed V1.5 robustness runs across training seeds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCHEMA_VERSION = "bunkering-ai-v1.5-robustness/v1"
SUMMARY_METRICS = (
    "reward_mean",
    "reward_bottom_5pct_mean",
    "sci_per_step_mean",
    "success_rate",
    "fuel_depletion_rate",
    "bunkering_per_30_steps_mean",
    "bunkering_count_max",
)


def _read_manifest(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unexpected robustness schema: {path}")
    return value


def _training_seed(manifest: dict, path: Path) -> int:
    try:
        return int(manifest["checkpoint"]["metadata"]["train_seed"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"missing checkpoint training seed: {path}") from exc


def collect(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict] = []
    effect_rows: list[dict] = []
    directories = sorted(path for path in root.glob("seed_*") if path.is_dir())
    if not directories:
        raise ValueError(f"no seed_* directories found under {root}")
    reference_contract: tuple[int, int, str] | None = None
    seen_seeds: set[int] = set()
    for directory in directories:
        manifest_path = directory / "manifest.json"
        manifest = _read_manifest(manifest_path)
        train_seed = _training_seed(manifest, manifest_path)
        if train_seed in seen_seeds:
            raise ValueError(f"duplicate training seed: {train_seed}")
        seen_seeds.add(train_seed)
        checkpoint_sha = str(manifest["checkpoint"]["sha256"])
        contract = (
            int(manifest["n_episodes"]),
            int(manifest["base_seed"]),
            json.dumps(manifest["scenarios"], sort_keys=True),
        )
        if reference_contract is None:
            reference_contract = contract
        elif contract != reference_contract:
            raise ValueError("V1.5 evaluation contract differs across runs")

        summary = pd.read_csv(directory / "summary.csv")
        missing = set(SUMMARY_METRICS) - set(summary.columns)
        if missing:
            raise ValueError(f"missing summary columns {sorted(missing)}: {directory}")
        for _, row in summary.iterrows():
            for metric in SUMMARY_METRICS:
                summary_rows.append(
                    {
                        "train_seed": train_seed,
                        "checkpoint_sha256": checkpoint_sha,
                        "scenario_id": str(row["scenario_id"]),
                        "scenario_family": str(row["scenario_family"]),
                        "policy": str(row["policy"]),
                        "max_steps": int(row["max_steps"]),
                        "consumption_multiplier": float(
                            row["consumption_multiplier"]
                        ),
                        "metric": metric,
                        "value": float(row[metric]),
                    }
                )

        effects = pd.read_csv(directory / "paired_effects.csv")
        for _, row in effects.iterrows():
            effect_rows.append(
                {
                    "train_seed": train_seed,
                    "checkpoint_sha256": checkpoint_sha,
                    **row.to_dict(),
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(effect_rows)


def aggregate(per_seed: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "scenario_id",
        "scenario_family",
        "policy",
        "max_steps",
        "consumption_multiplier",
        "metric",
    ]
    rows: list[dict] = []
    for values, group in per_seed.groupby(keys, sort=True):
        observed = group["value"].to_numpy(dtype=float)
        policy = str(values[2])
        if policy != "double_dqn" and not np.allclose(observed, observed[0]):
            raise ValueError(f"Rule-based result drift across repeated runs: {values}")
        rows.append(
            {
                **dict(zip(keys, values)),
                "independent_training_seeds": (
                    len(observed) if policy == "double_dqn" else 0
                ),
                "evaluation_replicates": len(observed),
                "mean_across_training_seeds": float(observed.mean()),
                "std_across_training_seeds_ddof0": float(
                    np.std(observed, ddof=0)
                ),
                "min_across_training_seeds": float(observed.min()),
                "max_across_training_seeds": float(observed.max()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_effects(per_seed: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "scenario_family",
        "reference_scenario",
        "scenario_id",
        "policy",
        "metric",
    ]
    rows: list[dict] = []
    for values, group in per_seed.groupby(keys, sort=True):
        absolute = group["absolute_change"].to_numpy(dtype=float)
        percent = group["percent_change"].to_numpy(dtype=float)
        policy = str(values[3])
        if policy != "double_dqn" and not np.allclose(
            absolute, absolute[0], equal_nan=True
        ):
            raise ValueError(f"Rule-based effect drift across repeated runs: {values}")
        finite_percent = percent[np.isfinite(percent)]
        rows.append(
            {
                **dict(zip(keys, values)),
                "independent_training_seeds": (
                    len(group) if policy == "double_dqn" else 0
                ),
                "evaluation_replicates": len(group),
                "reference_mean": float(group["reference_value"].mean()),
                "scenario_mean": float(group["scenario_value"].mean()),
                "absolute_change_mean": float(absolute.mean()),
                "absolute_change_std_ddof0": float(np.std(absolute, ddof=0)),
                "percent_change_mean": (
                    float(finite_percent.mean()) if len(finite_percent) else np.nan
                ),
                "percent_change_std_ddof0": (
                    float(np.std(finite_percent, ddof=0))
                    if len(finite_percent)
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_aggregate(summary: pd.DataFrame, output_path: Path) -> None:
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
        selected = summary.loc[
            (summary["scenario_family"] == family) & (summary["metric"] == metric)
        ]
        for policy, group in selected.groupby("policy", sort=True):
            ordered = group.sort_values(x_field)
            axis.errorbar(
                ordered[x_field],
                ordered["mean_across_training_seeds"],
                yerr=ordered["std_across_training_seeds_ddof0"],
                marker="o",
                capsize=3,
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
    figure.suptitle("V1.5 robustness across independent training seeds")
    figure.tight_layout(rect=(0, 0.06, 1, 0.96))
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-root", type=Path, default=Path("results/robustness/v1_5_multiseed")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/robustness/v1_5_aggregate")
    )
    args = parser.parse_args(argv)

    per_seed, effect_per_seed = collect(args.input_root)
    summary = aggregate(per_seed)
    effect_summary = aggregate_effects(effect_per_seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_seed.to_csv(args.output_dir / "per_training_seed.csv", index=False)
    summary.to_csv(args.output_dir / "aggregate.csv", index=False)
    effect_per_seed.to_csv(
        args.output_dir / "paired_effects_per_training_seed.csv", index=False
    )
    effect_summary.to_csv(
        args.output_dir / "paired_effect_summary.csv", index=False
    )
    plot_aggregate(summary, args.output_dir / "robustness_comparison.png")
    manifest = {
        "schema_version": "bunkering-ai-v1.5-robustness-aggregate/v1",
        "training_seeds": sorted(
            int(value) for value in per_seed["train_seed"].unique()
        ),
        "training_seed_count": int(per_seed["train_seed"].nunique()),
        "std_convention": "population standard deviation across training seeds (ddof=0)",
        "rule_based_repetition_note": (
            "Rule-based rows are repeated only to preserve the same-case contract. "
            "They are validated for equality and are not counted as independent "
            "training seeds."
        ),
        "generated_artifacts": [
            "per_training_seed.csv",
            "aggregate.csv",
            "paired_effects_per_training_seed.csv",
            "paired_effect_summary.csv",
            "robustness_comparison.png",
        ],
        "claim_boundary": (
            "Synthetic multi-training-seed sensitivity only; not calibrated fuel, "
            "engine, voyage, savings, or deployment validation."
        ),
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(effect_summary.to_string(index=False))
    print(f"\nwrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
