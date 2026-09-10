"""Validate and aggregate completed multi-training-seed evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OFFICIAL_METRICS = (
    "reward_mean",
    "synthetic_cost_index_mean",
    "success_mean",
    "fuel_depletion_mean",
    "bunkering_count_mean",
)
ROUTE_METRICS = (
    "reward_mean",
    "sci_per_step_mean",
    "bunkering_per_30_steps_mean",
    "success_rate",
    "fuel_depletion_rate",
)
EFFECT_METRICS = (
    "sci_per_step_mean",
    "bunkering_per_30_steps_mean",
)
NORMAL_SCENARIO = "normal"
STRESS_SCENARIO = "suez_cape_representative"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _training_seed(manifest: dict, path: Path) -> int:
    try:
        return int(manifest["checkpoint"]["metadata"]["train_seed"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"missing checkpoint training seed: {path}") from exc


def collect(official_root: Path, route_root: Path) -> pd.DataFrame:
    rows: list[dict] = []
    directories = sorted(path for path in official_root.glob("seed_*") if path.is_dir())
    if not directories:
        raise ValueError(f"no seed_* directories found under {official_root}")

    reference_contract: tuple[int, int] | None = None
    seen_seeds: set[int] = set()
    for directory in directories:
        official_manifest_path = directory / "evaluation_manifest.json"
        official_manifest = _read_json(official_manifest_path)
        train_seed = _training_seed(official_manifest, official_manifest_path)
        if train_seed in seen_seeds:
            raise ValueError(f"duplicate training seed: {train_seed}")
        seen_seeds.add(train_seed)

        contract = (
            int(official_manifest["n_episodes"]),
            int(official_manifest["base_seed"]),
        )
        if reference_contract is None:
            reference_contract = contract
        elif contract != reference_contract:
            raise ValueError("official evaluation seed contract differs across runs")

        checkpoint_sha = str(official_manifest["checkpoint"]["sha256"])
        official = pd.read_csv(directory / "evaluation" / "summary.csv")
        dqn = official.loc[official["policy"] == "double_dqn"]
        if len(dqn) != 1:
            raise ValueError(f"expected one double_dqn summary row: {directory}")
        for metric in OFFICIAL_METRICS:
            rows.append(
                {
                    "train_seed": train_seed,
                    "evaluation": "official_normal",
                    "scenario": "normal",
                    "metric": metric,
                    "value": float(dqn.iloc[0][metric]),
                    "checkpoint_sha256": checkpoint_sha,
                }
            )

        route_directory = route_root / directory.name
        route_manifest_path = route_directory / "manifest.json"
        route_manifest = _read_json(route_manifest_path)
        if _training_seed(route_manifest, route_manifest_path) != train_seed:
            raise ValueError(f"route training seed mismatch: {route_directory}")
        if str(route_manifest["checkpoint"]["sha256"]) != checkpoint_sha:
            raise ValueError(f"checkpoint hash mismatch: {route_directory}")
        route_contract = (
            int(route_manifest["n_seeds"]),
            int(route_manifest["base_seed"]),
        )
        if route_contract != reference_contract:
            raise ValueError(f"route evaluation seed contract mismatch: {route_directory}")

        route = pd.read_csv(route_directory / "summary.csv")
        for _, scenario_row in route.iterrows():
            for metric in ROUTE_METRICS:
                rows.append(
                    {
                        "train_seed": train_seed,
                        "evaluation": "route_stress",
                        "scenario": str(scenario_row["scenario_id"]),
                        "metric": metric,
                        "value": float(scenario_row[metric]),
                        "checkpoint_sha256": checkpoint_sha,
                    }
                )
    return pd.DataFrame(rows)


def aggregate(per_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in per_seed.groupby(["evaluation", "scenario", "metric"], sort=True):
        evaluation, scenario, metric = keys
        values = group["value"].to_numpy(dtype=float)
        rows.append(
            {
                "evaluation": evaluation,
                "scenario": scenario,
                "metric": metric,
                "training_seeds": len(values),
                "mean_across_training_seeds": float(values.mean()),
                "std_across_training_seeds_ddof0": float(np.std(values, ddof=0)),
                "min_across_training_seeds": float(values.min()),
                "max_across_training_seeds": float(values.max()),
            }
        )
    return pd.DataFrame(rows)



def route_effects(per_seed: pd.DataFrame) -> pd.DataFrame:
    """Calculate paired route-stress changes within each trained checkpoint."""
    route = per_seed.loc[per_seed["evaluation"] == "route_stress"]
    rows: list[dict] = []
    for train_seed in sorted(int(value) for value in route["train_seed"].unique()):
        seed_rows = route.loc[route["train_seed"] == train_seed]
        for metric in EFFECT_METRICS:
            normal = seed_rows.loc[
                (seed_rows["scenario"] == NORMAL_SCENARIO)
                & (seed_rows["metric"] == metric),
                "value",
            ]
            stress = seed_rows.loc[
                (seed_rows["scenario"] == STRESS_SCENARIO)
                & (seed_rows["metric"] == metric),
                "value",
            ]
            if len(normal) != 1 or len(stress) != 1:
                raise ValueError(
                    f"expected paired normal and route-stress values: "
                    f"seed={train_seed}, metric={metric}"
                )
            normal_value = float(normal.iloc[0])
            stress_value = float(stress.iloc[0])
            rows.append(
                {
                    "train_seed": train_seed,
                    "metric": metric,
                    "normal_value": normal_value,
                    "stress_value": stress_value,
                    "absolute_change": stress_value - normal_value,
                    "percent_change": (
                        100.0 * (stress_value - normal_value) / normal_value
                        if normal_value != 0.0
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def aggregate_effects(effects: pd.DataFrame) -> pd.DataFrame:
    """Summarize paired route effects across independently trained checkpoints."""
    rows: list[dict] = []
    for metric, group in effects.groupby("metric", sort=True):
        percent = group["percent_change"].to_numpy(dtype=float)
        rows.append(
            {
                "metric": metric,
                "training_seeds": len(group),
                "normal_mean": float(group["normal_value"].mean()),
                "normal_std_ddof0": float(np.std(group["normal_value"], ddof=0)),
                "stress_mean": float(group["stress_value"].mean()),
                "stress_std_ddof0": float(np.std(group["stress_value"], ddof=0)),
                "absolute_change_mean": float(group["absolute_change"].mean()),
                "percent_change_mean": float(np.nanmean(percent)),
                "percent_change_std_ddof0": float(np.nanstd(percent, ddof=0)),
                "percent_change_min": float(np.nanmin(percent)),
                "percent_change_max": float(np.nanmax(percent)),
            }
        )
    return pd.DataFrame(rows)


def write_markdown_report(effect_summary: pd.DataFrame, output_path: Path) -> None:
    """Write a compact, publication-oriented report with explicit claim limits."""
    labels = {
        "sci_per_step_mean": "SCI / step",
        "bunkering_per_30_steps_mean": "Bunkering / 30 steps",
    }
    seed_count = int(effect_summary["training_seeds"].max())
    lines = [
        "# Multi-training-seed route-stress summary",
        "",
        f"Independent training seeds: **{seed_count}**",
        "",
        "| Metric | Normal mean | Suez/Cape mean | Paired change |",
        "|---|---:|---:|---:|",
    ]
    for _, row in effect_summary.iterrows():
        label = labels.get(str(row["metric"]), str(row["metric"]))
        lines.append(
            f'| {label} | {row["normal_mean"]:.3f} | '
            f'{row["stress_mean"]:.3f} | '
            f'{row["percent_change_mean"]:+.2f}% '
            f'± {row["percent_change_std_ddof0"]:.2f}% |'
        )
    lines.extend(
        [
            "",
            "The change is paired within each frozen checkpoint and then summarized "
            "across independently trained checkpoints (population standard deviation, "
            "ddof=0).",
            "",
            "> Claim boundary: synthetic training-seed stability and exploratory "
            "route-stress sensitivity only. This is not actual-voyage, operational "
            "savings, or causal route validation.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def plot_effect_summary(effect_summary: pd.DataFrame, output_path: Path) -> None:
    """Create a general-audience comparison figure from the aggregated effects."""
    labels = {
        "sci_per_step_mean": "SCI / step",
        "bunkering_per_30_steps_mean": "Bunkering / 30 steps",
    }
    figure, axes = plt.subplots(1, len(effect_summary), figsize=(10, 4.5))
    axes_array = np.atleast_1d(axes)
    for axis, (_, row) in zip(axes_array, effect_summary.iterrows()):
        values = [row["normal_mean"], row["stress_mean"]]
        errors = [row["normal_std_ddof0"], row["stress_std_ddof0"]]
        bars = axis.bar(
            ["Normal", "Suez/Cape"],
            values,
            yerr=errors,
            capsize=5,
            color=["#3776AB", "#E67E22"],
        )
        axis.set_title(labels.get(str(row["metric"]), str(row["metric"])))
        axis.set_ylabel("Mean across training seeds")
        axis.grid(axis="y", alpha=0.25)
        axis.bar_label(bars, fmt="%.2f", padding=3)
        axis.text(
            0.5,
            0.96,
            f'{row["percent_change_mean"]:+.2f}% paired change',
            transform=axis.transAxes,
            ha="center",
            va="top",
            fontsize=9,
        )
    figure.suptitle("Frozen Double DQN: exploratory route-stress comparison")
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-root", type=Path, default=Path("results/multiseed"))
    parser.add_argument(
        "--route-root", type=Path, default=Path("results/route_stress/multiseed")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/multiseed_summary"))
    args = parser.parse_args(argv)

    per_seed = collect(args.official_root, args.route_root)
    summary = aggregate(per_seed)
    effects = route_effects(per_seed)
    effect_summary = aggregate_effects(effects)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_seed.to_csv(args.output_dir / "per_training_seed.csv", index=False)
    summary.to_csv(args.output_dir / "aggregate.csv", index=False)
    effects.to_csv(args.output_dir / "route_stress_effects.csv", index=False)
    effect_summary.to_csv(
        args.output_dir / "route_stress_effect_summary.csv", index=False
    )
    write_markdown_report(effect_summary, args.output_dir / "summary.md")
    plot_effect_summary(effect_summary, args.output_dir / "route_stress_comparison.png")
    manifest = {
        "training_seeds": sorted(int(value) for value in per_seed["train_seed"].unique()),
        "training_seed_count": int(per_seed["train_seed"].nunique()),
        "std_convention": "population standard deviation across training seeds (ddof=0)",
        "paired_effect_definition": (
            "Within-checkpoint Suez/Cape minus normal, summarized across training seeds."
        ),
        "generated_artifacts": [
            "per_training_seed.csv",
            "aggregate.csv",
            "route_stress_effects.csv",
            "route_stress_effect_summary.csv",
            "summary.md",
            "route_stress_comparison.png",
        ],
        "claim_boundary": (
            "Synthetic multi-training-seed stability result; not actual-voyage, "
            "operational, or causal validation."
        ),
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(summary.to_string(index=False))
    print("\nPaired route-stress effects")
    print(effect_summary.to_string(index=False))
    print(f"\nwrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
