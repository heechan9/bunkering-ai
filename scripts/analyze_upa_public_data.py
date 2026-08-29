"""Analyze the Ulsan Port Authority bunkering anchorage public dataset.

This script creates descriptive reference artifacts only. It does not feed the
public dataset into BunkeringEnv or train/evaluate the Double DQN agent.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


EXPECTED_COLUMNS = [
    "입항구분명",
    "입항년도",
    "입항항차",
    "총톤수",
    "벙커량",
    "예정시작일",
    "예정종료일",
    "등록일",
]
DATE_COLUMNS = ["예정시작일", "예정종료일", "등록일"]


def load_data(path: Path) -> pd.DataFrame:
    """Load the normalized UTF-8 CSV and validate its declared schema."""
    frame = pd.read_csv(path, encoding="utf-8")
    if frame.columns.tolist() != EXPECTED_COLUMNS:
        raise ValueError(
            "Unexpected public-data schema: "
            f"expected {EXPECTED_COLUMNS}, got {frame.columns.tolist()}"
        )

    for column in DATE_COLUMNS:
        parsed = pd.to_datetime(frame[column], errors="coerce")
        if parsed.isna().any():
            raise ValueError(f"Invalid date values found in {column}")
        frame[column] = parsed

    return frame


def build_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Return auditable, single-value summary metrics."""
    duration_days = (frame["예정종료일"] - frame["예정시작일"]).dt.days
    corr = frame[["총톤수", "벙커량"]].corr().iloc[0, 1]
    values = [
        ("records", len(frame)),
        ("columns", len(frame.columns)),
        ("missing_cells", int(frame.isna().sum().sum())),
        ("exact_duplicate_rows", int(frame.duplicated().sum())),
        ("year_min", int(frame["입항년도"].min())),
        ("year_max", int(frame["입항년도"].max())),
        ("bunker_quantity_zero_rows", int((frame["벙커량"] == 0).sum())),
        ("bunker_quantity_mean", round(float(frame["벙커량"].mean()), 2)),
        ("bunker_quantity_median", round(float(frame["벙커량"].median()), 2)),
        ("bunker_quantity_q1", round(float(frame["벙커량"].quantile(0.25)), 2)),
        ("bunker_quantity_q3", round(float(frame["벙커량"].quantile(0.75)), 2)),
        ("bunker_quantity_p95", round(float(frame["벙커량"].quantile(0.95)), 2)),
        ("bunker_quantity_max", round(float(frame["벙커량"].max()), 2)),
        ("gross_tonnage_median", round(float(frame["총톤수"].median()), 2)),
        ("negative_schedule_duration_rows", int((duration_days < 0).sum())),
        ("gross_tonnage_bunker_quantity_correlation", round(float(corr), 4)),
    ]
    return pd.DataFrame(values, columns=["metric", "value"])


def build_group_summaries(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    aggregations = {
        "records": ("벙커량", "size"),
        "bunker_quantity_mean": ("벙커량", "mean"),
        "bunker_quantity_median": ("벙커량", "median"),
        "gross_tonnage_median": ("총톤수", "median"),
    }
    by_year = frame.groupby("입항년도").agg(**aggregations).reset_index()
    by_entry_type = frame.groupby("입항구분명").agg(**aggregations).reset_index()
    numeric = [
        "bunker_quantity_mean",
        "bunker_quantity_median",
        "gross_tonnage_median",
    ]
    by_year[numeric] = by_year[numeric].round(2)
    by_entry_type[numeric] = by_entry_type[numeric].round(2)
    return by_year, by_entry_type


def save_chart(frame: pd.DataFrame, output_path: Path) -> None:
    """Create a report-safe chart with English labels for portable rendering."""
    by_year = frame.groupby("입항년도")["벙커량"].median()
    entry_counts = frame["입항구분명"].value_counts().reindex(["입항", "출항", "통과"])

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    by_year.plot.bar(ax=axes[0], color="#57A7B3", edgecolor="#2F6570")
    axes[0].set_title("Median bunker quantity by year")
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Recorded bunker quantity")
    axes[0].tick_params(axis="x", rotation=0)

    axes[1].bar(
        ["Arrival", "Departure", "Transit"],
        entry_counts.values,
        color=["#89CBD3", "#57A7B3", "#D0D7D9"],
        edgecolor="#2F6570",
    )
    axes[1].set_title("Records by port-call classification")
    axes[1].set_ylabel("Records")

    fig.suptitle("UPA bunkering anchorage public data (descriptive reference)")
    fig.text(
        0.5,
        0.01,
        "Source: Ulsan Port Authority / data.go.kr, dataset 15132700. "
        "Not a DQN training or evaluation result.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/public/upa_bunkering_anchorage_20240819.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/public_data")
    )
    args = parser.parse_args()

    frame = load_data(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics = build_metrics(frame)
    by_year, by_entry_type = build_group_summaries(frame)

    metrics.to_csv(args.output_dir / "upa_summary_metrics.csv", index=False)
    by_year.to_csv(args.output_dir / "upa_summary_by_year.csv", index=False)
    by_entry_type.to_csv(
        args.output_dir / "upa_summary_by_entry_type.csv", index=False
    )
    save_chart(frame, args.output_dir / "upa_bunkering_reference_summary.png")

    print(metrics.to_string(index=False))
    print(f"Saved public-data reference artifacts to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
