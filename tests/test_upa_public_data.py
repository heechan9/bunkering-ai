from pathlib import Path

from scripts.analyze_upa_public_data import (
    build_group_summaries,
    build_metrics,
    load_data,
)


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "public"
    / "upa_bunkering_anchorage_20240819.csv"
)


def test_upa_public_data_schema_and_record_count():
    frame = load_data(DATA_PATH)

    assert len(frame) == 6028
    assert frame.isna().sum().sum() == 0
    assert set(frame["입항구분명"]) == {"입항", "출항", "통과"}


def test_upa_public_data_reference_metrics():
    frame = load_data(DATA_PATH)
    metrics = build_metrics(frame).set_index("metric")["value"]

    assert metrics["exact_duplicate_rows"] == "38"
    assert metrics["bunker_quantity_median"] == "200"
    assert metrics["bunker_quantity_zero_rows"] == "250"
    assert metrics["negative_schedule_duration_rows"] == "55"
    assert metrics["application_lead_time_median_days"] == "1"
    assert metrics["negative_application_lead_time_rows"] == "71"
    assert metrics["gross_tonnage_max"] == "628121"


def test_upa_year_summary_marks_partial_2024():
    frame = load_data(DATA_PATH)
    by_year, _ = build_group_summaries(frame)
    partial = by_year.set_index("입항년도")["partial_year"].to_dict()

    assert partial == {2022: False, 2023: False, 2024: True}
