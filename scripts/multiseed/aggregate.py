"""Validate and aggregate completed multi-training-seed evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_seed.to_csv(args.output_dir / "per_training_seed.csv", index=False)
    summary.to_csv(args.output_dir / "aggregate.csv", index=False)
    manifest = {
        "training_seeds": sorted(int(value) for value in per_seed["train_seed"].unique()),
        "training_seed_count": int(per_seed["train_seed"].nunique()),
        "std_convention": "population standard deviation across training seeds (ddof=0)",
        "claim_boundary": (
            "Synthetic multi-training-seed stability result; not actual-voyage, "
            "operational, or causal validation."
        ),
    }
    with (args.output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(summary.to_string(index=False))
    print(f"\nwrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
