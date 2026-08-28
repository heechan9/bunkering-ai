from pathlib import Path

from scripts.analyze_upa_public_data import build_metrics, load_data


DATA_PATH = Path("data/public/upa_bunkering_anchorage_20240819.csv")


def test_upa_public_data_schema_and_record_count():
    frame = load_data(DATA_PATH)

    assert len(frame) == 6028
    assert frame.isna().sum().sum() == 0
    assert set(frame["입항구분명"]) == {"입항", "출항", "통과"}


def test_upa_public_data_reference_metrics():
    frame = load_data(DATA_PATH)
    metrics = build_metrics(frame).set_index("metric")["value"]

    assert metrics["exact_duplicate_rows"] == 38
    assert metrics["bunker_quantity_median"] == 200.0
    assert metrics["bunker_quantity_zero_rows"] == 250
    assert metrics["negative_schedule_duration_rows"] == 55
