"""Analyze the Ulsan Port Authority bunkering anchorage public dataset.

This script creates descriptive reference artifacts only. It does not feed the
public dataset into BunkeringEnv or train/evaluate the Double DQN agent.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = (
    PROJECT_ROOT / "data" / "public" / "upa_bunkering_anchorage_20240819.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "public_data"

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


def _display_number(value: int | float, digits: int | None = None) -> str:
    """Format metric values without turning integer counts into 8.0-style text."""
    if digits is None:
        return str(int(value))
    rendered = f"{float(value):.{digits}f}"
    return rendered.rstrip("0").rstrip(".")


def build_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Return auditable, single-value summary metrics as display-safe strings."""
    duration_days = (frame["예정종료일"] - frame["예정시작일"]).dt.days
    lead_days = (frame["예정시작일"] - frame["등록일"]).dt.days
    corr = frame[["총톤수", "벙커량"]].corr().iloc[0, 1]
    values = [
        ("records", _display_number(len(frame))),
        ("columns", _display_number(len(frame.columns))),
        ("missing_cells", _display_number(frame.isna().sum().sum())),
        ("exact_duplicate_rows", _display_number(frame.duplicated().sum())),
        ("year_min", _display_number(frame["입항년도"].min())),
        ("year_max", _display_number(frame["입항년도"].max())),
        (
            "bunker_quantity_zero_rows",
            _display_number((frame["벙커량"] == 0).sum()),
        ),
        ("bunker_quantity_mean", _display_number(frame["벙커량"].mean(), 2)),
        ("bunker_quantity_median", _display_number(frame["벙커량"].median(), 2)),
        ("bunker_quantity_q1", _display_number(frame["벙커량"].quantile(0.25), 2)),
        ("bunker_quantity_q3", _display_number(frame["벙커량"].quantile(0.75), 2)),
        ("bunker_quantity_p95", _display_number(frame["벙커량"].quantile(0.95), 2)),
        ("bunker_quantity_max", _display_number(frame["벙커량"].max(), 2)),
        ("gross_tonnage_median", _display_number(frame["총톤수"].median(), 2)),
        ("gross_tonnage_max", _display_number(frame["총톤수"].max(), 2)),
        (
            "gross_tonnage_over_400000_rows",
            _display_number((frame["총톤수"] > 400000).sum()),
        ),
        (
            "negative_schedule_duration_rows",
            _display_number((duration_days < 0).sum()),
        ),
        (
            "application_lead_time_median_days",
            _display_number(lead_days.median(), 2),
        ),
        (
            "application_lead_time_q1_days",
            _display_number(lead_days.quantile(0.25), 2),
        ),
        (
            "application_lead_time_q3_days",
            _display_number(lead_days.quantile(0.75), 2),
        ),
        (
            "application_lead_time_min_days",
            _display_number(lead_days.min()),
        ),
        (
            "application_lead_time_max_days",
            _display_number(lead_days.max()),
        ),
        (
            "negative_application_lead_time_rows",
            _display_number((lead_days < 0).sum()),
        ),
        (
            "gross_tonnage_bunker_quantity_correlation",
            _display_number(corr, 4),
        ),
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

    final_calendar_year = int(frame["예정시작일"].dt.year.max())
    final_date = frame["예정시작일"].max()
    by_year["partial_year"] = (
        (by_year["입항년도"] == final_calendar_year)
        & ((final_date.month, final_date.day) != (12, 31))
    )
    return by_year, by_entry_type


def save_chart(frame: pd.DataFrame, output_path: Path) -> None:
    """Create a report-safe chart with English labels for portable rendering."""
    by_year = frame.groupby("입항년도")["벙커량"].median()
    entry_counts = frame["입항구분명"].value_counts().reindex(["입항", "출항", "통과"])

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    by_year.plot.bar(ax=axes[0], color="#57A7B3", edgecolor="#2F6570")
    axes[0].set_title("Median bunker quantity by year")
    axes[0].set_xlabel("Year (2024 is partial)")
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
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
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
