"""Parser for the fixed ONS weekly maritime-passage CSV contract."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ONS_COLUMNS = {
    "Passage",
    "Ship Type",
    "Number of crossings",
    "Year",
    "Week of entry",
}
SHIP_TYPES = {"Cargo", "Tanker", "Other"}


def parse_ons_crossings(path: str | Path) -> pd.DataFrame:
    """Validate and normalize ONS crossings without imputing missing observations."""
    frame = pd.read_csv(path)
    missing = ONS_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"missing ONS columns: {sorted(missing)}")

    # The official download ends with three human-readable source/footnote rows.
    # They are metadata rather than suppressed weekly observations.
    result = frame.loc[frame["Year"].notna(), list(ONS_COLUMNS)].copy()
    result = result.rename(
        columns={
            "Passage": "chokepoint_id",
            "Ship Type": "vessel_type",
            "Number of crossings": "transit_count",
            "Year": "year",
            "Week of entry": "iso_week",
        }
    )
    result["transit_count"] = pd.to_numeric(result["transit_count"], errors="raise")
    result["year"] = pd.to_numeric(result["year"], errors="raise").astype(int)
    result["iso_week"] = pd.to_numeric(result["iso_week"], errors="raise").astype(int)

    if result["transit_count"].isna().any() or (result["transit_count"] < 0).any():
        raise ValueError("transit_count must be present and non-negative")
    if not result["iso_week"].between(1, 53).all():
        raise ValueError("iso_week must be between 1 and 53")
    unknown = set(result["vessel_type"].dropna()) - SHIP_TYPES
    if unknown:
        raise ValueError(f"unknown ONS vessel types: {sorted(unknown)}")
    if result.duplicated(["chokepoint_id", "vessel_type", "year", "iso_week"]).any():
        raise ValueError("duplicate ONS passage/type/week rows")

    result["observation_date"] = pd.to_datetime(
        result["year"].astype(str)
        + "-W"
        + result["iso_week"].astype(str).str.zfill(2)
        + "-1",
        format="%G-W%V-%u",
        errors="raise",
    )
    return result.sort_values(
        ["observation_date", "chokepoint_id", "vessel_type"]
    ).reset_index(drop=True)
