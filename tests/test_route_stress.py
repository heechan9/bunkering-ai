import pandas as pd
import pytest

from envs.bunkering_env import BunkeringEnv, STATE_VARS
from route_stress import RouteStressAdapter, RouteStressScenario, parse_ons_crossings


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
