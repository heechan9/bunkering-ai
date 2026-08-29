import math

import pytest

from evaluation.contract import (
    CSV_FIELDS,
    EpisodeResult,
    EvaluationCase,
    aggregate_results,
    validate_fair_evaluation_plan,
)


def make_result(**overrides):
    values = {
        "seed": 42,
        "episode": 0,
        "policy": "double_dqn",
        "reward": 1.5,
        "synthetic_cost_index": 100.0,
        "success": True,
        "fuel_depletion": False,
        "bunkering_count": 2,
        "termination_reason": "arrived",
    }
    values.update(overrides)
    return EpisodeResult(**values)


def test_episode_result_exports_required_schema():
    row = make_result().to_row()

    assert tuple(row) == CSV_FIELDS
    assert row["Synthetic Cost Index"] == 100.0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"policy": ""}, "policy"),
        ({"seed": -1}, "seed"),
        ({"episode": True}, "episode"),
        ({"reward": math.nan}, "reward"),
        ({"synthetic_cost_index": math.inf}, "synthetic_cost_index"),
        ({"synthetic_cost_index": -0.1}, "nonnegative"),
        ({"bunkering_count": -1}, "bunkering_count"),
        ({"success": 1}, "booleans"),
        ({"termination_reason": "unknown"}, "termination_reason"),
    ],
)
def test_episode_result_rejects_invalid_values(overrides, message):
    with pytest.raises(ValueError, match=message):
        make_result(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"success": False},
        {"fuel_depletion": True},
        {"termination_reason": "fuel_depleted"},
        {"termination_reason": "timeout", "success": True},
    ],
)
def test_episode_result_rejects_inconsistent_termination_flags(overrides):
    with pytest.raises(ValueError):
        make_result(**overrides)


def test_all_supported_termination_reasons_accept_consistent_flags():
    assert make_result().termination_reason == "arrived"
    assert make_result(
        success=False, fuel_depletion=True, termination_reason="fuel_depleted"
    ).fuel_depletion
    assert make_result(
        success=False, fuel_depletion=False, termination_reason="timeout"
    ).termination_reason == "timeout"


def test_aggregate_results_calculates_population_mean_and_standard_deviation():
    results = [
        make_result(episode=0, reward=1.0, synthetic_cost_index=10.0,
                    bunkering_count=1),
        make_result(episode=1, seed=43, reward=3.0, synthetic_cost_index=30.0,
                    success=False, fuel_depletion=True, bunkering_count=3,
                    termination_reason="fuel_depleted"),
    ]

    aggregate = aggregate_results(results)[0]

    assert aggregate.episodes == 2
    assert aggregate.reward_mean == pytest.approx(2.0)
    assert aggregate.reward_std == pytest.approx(1.0)
    assert aggregate.synthetic_cost_index_mean == pytest.approx(20.0)
    assert aggregate.synthetic_cost_index_std == pytest.approx(10.0)
    assert aggregate.success_mean == pytest.approx(0.5)
    assert aggregate.success_std == pytest.approx(0.5)
    assert aggregate.fuel_depletion_mean == pytest.approx(0.5)
    assert aggregate.bunkering_count_mean == pytest.approx(2.0)
    assert aggregate.bunkering_count_std == pytest.approx(1.0)


def test_aggregate_results_keeps_policies_separate_and_sorted():
    aggregates = aggregate_results(
        [make_result(policy="rule_b"), make_result(policy="rule_a")]
    )

    assert [aggregate.policy for aggregate in aggregates] == ["rule_a", "rule_b"]


def test_aggregate_results_rejects_missing_results_instead_of_fabricating_output():
    with pytest.raises(ValueError, match="empty"):
        aggregate_results([])


def fair_cases():
    config = {"n_ports": 3, "max_steps": 30, "nested": {"threshold": 0.15}}
    return [
        EvaluationCase(seed=seed, episode=episode, policy=policy, env_config=config)
        for policy in ("double_dqn", "fixed_fueling", "price_reactive", "safe_stock")
        for episode, seed in enumerate((42, 43))
    ]


def test_fairness_accepts_identical_seed_episode_and_environment_config():
    validate_fair_evaluation_plan(
        fair_cases(),
        ("double_dqn", "fixed_fueling", "price_reactive", "safe_stock"),
    )


@pytest.mark.parametrize("changed_field", ["seed", "episode", "env_config"])
def test_fairness_rejects_policy_with_different_run_conditions(changed_field):
    cases = fair_cases()
    target = cases[-1]
    replacement = {
        "seed": target.seed,
        "episode": target.episode,
        "policy": target.policy,
        "env_config": target.env_config,
    }
    replacement[changed_field] = (
        {"n_ports": 9} if changed_field == "env_config" else 999
    )
    cases[-1] = EvaluationCase(**replacement)

    with pytest.raises(ValueError, match="identical"):
        validate_fair_evaluation_plan(
            cases,
            ("double_dqn", "fixed_fueling", "price_reactive", "safe_stock"),
        )


def test_fairness_rejects_missing_policy_and_duplicate_case():
    policies = ("double_dqn", "fixed_fueling", "price_reactive", "safe_stock")
    with pytest.raises(ValueError, match="policies"):
        validate_fair_evaluation_plan(fair_cases()[:-2], policies)
    cases = fair_cases()
    with pytest.raises(ValueError, match="duplicate"):
        validate_fair_evaluation_plan(cases + [cases[0]], policies)
