import pytest

from route_stress import RouteImpactAssumption, get_route_impact
from scripts.route_stress.evaluate_rulebased import run_evaluation


def test_sca_representative_route_scales_30_steps_to_43():
    impact = get_route_impact("suez_cape_representative")

    assert impact.extra_distance_nm == 3467
    assert impact.distance_multiplier == pytest.approx(11755 / 8288)
    assert impact.scenario_max_steps == 43
    assert impact.env_config()["max_steps"] == 43


def test_hormuz_observation_does_not_fabricate_detour_effect():
    normal = get_route_impact("normal")
    hormuz = get_route_impact("hormuz_observation_only")

    assert hormuz.operational_effect is False
    assert hormuz.extra_distance_nm == 0
    assert hormuz.env_config() == normal.env_config()


def test_observation_only_assumption_cannot_change_distance():
    with pytest.raises(ValueError, match="cannot change route distance"):
        RouteImpactAssumption(
            assumption_id="invalid",
            scenario_id="invalid",
            baseline_distance_nm=100,
            scenario_distance_nm=120,
            operational_effect=False,
        )


def test_normal_and_hormuz_rows_match_for_same_seed_and_policy():
    raw = run_evaluation(n_seeds=1, base_seed=42)
    columns = [
        "policy",
        "reward",
        "synthetic_cost_index",
        "success",
        "fuel_depletion",
        "bunkering_count",
        "termination_reason",
    ]
    normal = raw[raw["scenario_id"] == "normal"][columns].reset_index(drop=True)
    hormuz = raw[raw["scenario_id"] == "hormuz_observation_only"][columns].reset_index(drop=True)

    assert normal.equals(hormuz)
