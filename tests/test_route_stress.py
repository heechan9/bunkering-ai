import pandas as pd
import pytest

from envs.bunkering_env import BunkeringEnv, STATE_VARS
from route_stress import (
    RouteStressAdapter,
    RouteStressScenario,
    add_past_only_baseline,
    parse_ons_crossings,
)
from route_stress.source import verify_sha256


def _write_ons_csv(tmp_path, rows):
    path = tmp_path / "ons.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_parser_normalizes_valid_ons_contract(tmp_path):
    path = _write_ons_csv(
        tmp_path,
        [{
            "Passage": "Suez Canal",
            "Ship Type": "Tanker",
            "Number of crossings": 12,
            "Year": 2024,
            "Week of entry": 3,
        }],
    )

    parsed = parse_ons_crossings(path)

    assert parsed.loc[0, "transit_count"] == 12
    assert parsed.loc[0, "observation_date"] == pd.Timestamp("2024-01-15")


def test_parser_ignores_official_download_footnote_rows(tmp_path):
    path = _write_ons_csv(
        tmp_path,
        [
            {
                "Passage": "Suez Canal",
                "Ship Type": "Cargo",
                "Number of crossings": 10,
                "Year": 2024,
                "Week of entry": 1,
            },
            {
                "Passage": "Source: AIS, analysed by ONS",
                "Ship Type": None,
                "Number of crossings": None,
                "Year": None,
                "Week of entry": None,
            },
        ],
    )

    parsed = parse_ons_crossings(path)

    assert len(parsed) == 1


@pytest.mark.parametrize("count", [-1, None])
def test_parser_rejects_invalid_counts(tmp_path, count):
    path = _write_ons_csv(
        tmp_path,
        [{
            "Passage": "Suez Canal",
            "Ship Type": "Cargo",
            "Number of crossings": count,
            "Year": 2024,
            "Week of entry": 1,
        }],
    )

    with pytest.raises(ValueError):
        parse_ons_crossings(path)


def test_contraction_does_not_imply_route_closure_or_costs():
    scenario = RouteStressAdapter().get("suez_contraction")

    assert scenario.route_available is True
    assert scenario.detour_distance_nm is None
    assert scenario.detour_duration_hours is None
    assert scenario.estimated_extra_fuel is None


def test_adapter_does_not_change_canonical_env_contract():
    before = BunkeringEnv()
    metadata = RouteStressAdapter().episode_metadata("hormuz_contraction")
    after = BunkeringEnv()

    assert metadata["evidence_scope"] == "scenario_fixture"
    assert before.observation_space.shape == after.observation_space.shape == (6,)
    assert STATE_VARS == [
        "fuel_price",
        "fuel_price_ma30",
        "fx_rate",
        "fuel_remaining",
        "route_remaining",
        "sfc",
    ]


def test_negative_assumption_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        RouteStressScenario(
            scenario_id="bad",
            chokepoint_id="suez_canal",
            transit_baseline_ratio=0.5,
            disruption_level="moderate",
            detour_distance_nm=-1,
        )


def test_baseline_uses_only_prior_weeks(tmp_path):
    rows = [
        {
            "Passage": "Suez Canal",
            "Ship Type": "Cargo",
            "Number of crossings": count,
            "Year": 2024,
            "Week of entry": week,
        }
        for week, count in enumerate([10, 20, 30, 40], start=1)
    ]
    parsed = parse_ons_crossings(_write_ons_csv(tmp_path, rows))

    result = add_past_only_baseline(parsed, min_history_weeks=2)

    assert pd.isna(result.loc[0, "transit_baseline"])
    assert pd.isna(result.loc[1, "transit_baseline"])
    assert result.loc[2, "transit_baseline"] == pytest.approx(15.0)
    assert result.loc[3, "transit_baseline"] == pytest.approx(20.0)


def test_baseline_rejects_zero_history_window():
    with pytest.raises(ValueError, match="at least 1"):
        add_past_only_baseline(pd.DataFrame(), min_history_weeks=0)


def test_sha_verifier_fails_closed_on_changed_content():
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_sha256(b"changed", "0" * 64)
