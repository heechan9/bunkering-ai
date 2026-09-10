import copy

import pytest
import torch

from agents.dqn import DQNAgent
from scripts.evaluate import DoubleDQNPolicy
from scripts.route_stress.evaluate_frozen_dqn import run_evaluation


def _policy() -> DoubleDQNPolicy:
    config = {
        "network": {"hidden_dims": [8]},
        "train": {"learning_rate": 1e-3, "gamma": 0.99, "device": "cpu"},
    }
    return DoubleDQNPolicy(DQNAgent(state_dim=6, action_dim=4, config=config))


def test_frozen_dqn_rejects_empty_seed_set():
    with pytest.raises(ValueError, match="at least 1"):
        run_evaluation(_policy(), n_seeds=0)


def test_frozen_dqn_evaluates_one_policy_across_all_scenarios():
    raw = run_evaluation(_policy(), n_seeds=2, base_seed=42)

    assert len(raw) == 6
    assert set(raw["policy"]) == {"double_dqn"}
    assert set(raw["scenario_id"]) == {
        "normal",
        "suez_cape_representative",
        "hormuz_observation_only",
    }
    assert (raw["steps"] > 0).all()


def test_frozen_dqn_normal_and_observation_only_rows_match():
    raw = run_evaluation(_policy(), n_seeds=2, base_seed=42)
    columns = [
        "reward",
        "synthetic_cost_index",
        "success",
        "fuel_depletion",
        "bunkering_count",
        "termination_reason",
    ]
    normal = raw[raw["scenario_id"] == "normal"][columns].reset_index(drop=True)
    hormuz = raw[raw["scenario_id"] == "hormuz_observation_only"][
        columns
    ].reset_index(drop=True)

    assert normal.equals(hormuz)


def test_frozen_dqn_evaluation_does_not_update_weights():
    policy = _policy()
    before = copy.deepcopy(policy.agent.policy_net.state_dict())

    run_evaluation(policy, n_seeds=1, base_seed=42)

    after = policy.agent.policy_net.state_dict()
    assert all(torch.equal(before[name], after[name]) for name in before)
