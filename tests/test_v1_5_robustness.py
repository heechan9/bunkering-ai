import copy

import pandas as pd
import pytest
import torch

from agents.dqn import DQNAgent
from scripts.baseline import SafeStockStrategy
from scripts.evaluate import DoubleDQNPolicy
from scripts.robustness.evaluate_v1_5 import (
    SCENARIOS,
    paired_effects,
    run_evaluation,
    summarize,
)


def _policy() -> DoubleDQNPolicy:
    config = {
        "network": {"hidden_dims": [8]},
        "train": {"learning_rate": 1e-3, "gamma": 0.99, "device": "cpu"},
    }
    return DoubleDQNPolicy(DQNAgent(state_dim=6, action_dim=4, config=config))


def test_scenarios_cover_consumption_and_local_horizon_sensitivity():
    by_id = {scenario.scenario_id: scenario for scenario in SCENARIOS}

    assert by_id["consumption_minus_10"].consumption_multiplier == pytest.approx(0.9)
    assert by_id["consumption_baseline"].consumption_multiplier == pytest.approx(1.0)
    assert by_id["consumption_plus_10"].consumption_multiplier == pytest.approx(1.1)
    assert by_id["consumption_plus_20"].consumption_multiplier == pytest.approx(1.2)
    assert {
        by_id["horizon_42"].max_steps,
        by_id["horizon_43_reference"].max_steps,
        by_id["horizon_44"].max_steps,
    } == {42, 43, 44}


def test_run_evaluation_uses_same_cases_for_each_policy():
    dqn = _policy()
    safe_stock = SafeStockStrategy()
    policies = {"double_dqn": dqn, safe_stock.name: safe_stock}

    raw = run_evaluation(policies, n_episodes=2, base_seed=42)

    assert len(raw) == len(SCENARIOS) * 2 * len(policies)
    assert set(raw["seed"]) == {42, 43}
    assert set(raw["scenario_id"]) == {scenario.scenario_id for scenario in SCENARIOS}
    case_policies = raw.groupby(["scenario_id", "seed"])["policy"].apply(set)
    assert all(value == set(policies) for value in case_policies)


def test_run_evaluation_keeps_dqn_weights_frozen():
    policy = _policy()
    before = copy.deepcopy(policy.agent.policy_net.state_dict())

    run_evaluation({policy.name: policy}, n_episodes=1, base_seed=42)

    after = policy.agent.policy_net.state_dict()
    assert all(torch.equal(before[name], after[name]) for name in before)


def test_summary_reports_empirical_five_percent_tails():
    rows = []
    for episode in range(20):
        rows.append(
            {
                "scenario_id": "consumption_baseline",
                "scenario_family": "fuel_consumption",
                "reference_scenario": True,
                "policy": "double_dqn",
                "max_steps": 30,
                "fuel_consumption_per_step": 0.05,
                "consumption_multiplier": 1.0,
                "steps": 30,
                "reward": float(episode),
                "synthetic_cost_index": float(episode * 100),
                "success": True,
                "fuel_depletion": False,
                "bunkering_count": episode,
            }
        )

    result = summarize(pd.DataFrame(rows)).iloc[0]

    assert result["reward_min"] == 0.0
    assert result["reward_bottom_5pct_mean"] == 0.0
    assert result["sci_max"] == 1900.0
    assert result["sci_top_5pct_mean"] == 1900.0
    assert result["bunkering_count_max"] == 19


def test_paired_effects_use_family_reference_per_policy():
    summary = pd.DataFrame(
        [
            {
                "scenario_id": scenario,
                "scenario_family": "fuel_consumption",
                "policy": "double_dqn",
                **{
                    metric: value
                    for metric in (
                        "reward_mean",
                        "sci_per_step_mean",
                        "success_rate",
                        "fuel_depletion_rate",
                        "bunkering_per_30_steps_mean",
                    )
                },
            }
            for scenario, value in (
                ("consumption_baseline", 10.0),
                ("consumption_plus_20", 12.0),
            )
        ]
    )

    effects = paired_effects(summary)

    assert len(effects) == 5
    assert set(effects["absolute_change"]) == {2.0}
    reward = effects.loc[effects["metric"] == "reward_mean"].iloc[0]
    operational = effects.loc[effects["metric"] != "reward_mean"]
    assert pd.isna(reward["percent_change"])
    assert set(operational["percent_change"]) == {20.0}
