import pytest
from scripts.baseline import FixedFuelingStrategy, SafeStockStrategy, PriceReactiveStrategy
from scripts.diagnose_reward import trace_episode, main


def test_fixed_departure_has_no_effective_purchase():
    rows, s = trace_episode(FixedFuelingStrategy())
    assert rows[0]["action"] == 1
    assert s["bunker_amount"] == pytest.approx(0)
    assert s["end_reason"] == "fuel_depleted"


def test_safe_accounting_and_reward_reconcile():
    rows, s = trace_episode(SafeStockStrategy())
    assert s["end_reason"] == "arrived"
    assert abs(s["fuel_balance_residual"]) < 1e-12
    assert s["reward"] == pytest.approx(sum(s[k] for k in (
        "price_advantage_reward", "safety_reward", "operational_reward", "imo_reward")))
    assert s["step_sci"] == pytest.approx(sum(
        r["bunker_amount"] * r["decision_price"] * r["decision_fx"] for r in rows))


def test_repeatability():
    assert trace_episode(SafeStockStrategy(), 43) == trace_episode(SafeStockStrategy(), 43)


def test_clipping_loss_is_explicit():
    _, s = trace_episode(SafeStockStrategy(), env_config={"fuel_consumption_per_step": 0.045})
    assert s["clipping_loss"] == pytest.approx(0.005)
    assert abs(s["fuel_balance_residual"]) < 1e-12


def test_does_not_overwrite(tmp_path):
    sentinel = tmp_path / "evaluation_results.csv"
    sentinel.write_bytes(b"official sentinel")
    with pytest.raises(SystemExit):
        main(["--output-dir", str(tmp_path)])
    assert sentinel.read_bytes() == b"official sentinel"


def test_cli_rule_only(tmp_path):
    path = tmp_path / "fresh"
    assert main(["--episodes", "1", "--output-dir", str(path)]) == 0
    assert (path / "manifest.json").is_file()


def test_frozen_weights():
    import torch
    from agents.dqn import DQNAgent
    from scripts.evaluate import DoubleDQNPolicy
    agent = DQNAgent(state_dim=6, action_dim=4, config={"gamma": 0.99, "learning_rate": 0.001})
    agent.policy_net.eval()
    before = {k: v.clone() for k,v in agent.policy_net.state_dict().items()}
    trace_episode(DoubleDQNPolicy(agent))
    assert all(torch.equal(v, before[k]) for k,v in agent.policy_net.state_dict().items())


@pytest.mark.parametrize("policy_name", ["fixed", "price", "safe", "dqn"])
@pytest.mark.parametrize("consumption", [0.045, 0.05, 0.055, 0.06])
def test_official_runner_parity_and_clipping(policy_name, consumption):
    import torch
    from agents.dqn import DQNAgent
    from scripts.evaluate import DoubleDQNPolicy, run_episode
    from evaluation.contract import EvaluationCase
    torch.manual_seed(7)
    policies = {"fixed": FixedFuelingStrategy(), "price": PriceReactiveStrategy(),
                "safe": SafeStockStrategy()}
    if policy_name == "dqn":
        agent = DQNAgent(6, 4, {"gamma": 0.99, "learning_rate": 0.001})
        agent.policy_net.eval()
        policy = DoubleDQNPolicy(agent)
    else:
        policy = policies[policy_name]
    config = {"fuel_consumption_per_step": consumption}
    for seed in range(42, 142):
        rows, s = trace_episode(policy, seed, config)
        official = run_episode(policy, EvaluationCase(seed, seed - 42, policy.name, config))
        assert s["reward"] == pytest.approx(official.reward)
        assert s["step_sci"] == pytest.approx(official.synthetic_cost_index)
        assert s["end_reason"] == official.termination_reason
        assert s["bunker_event"] == official.bunkering_count
        assert s["clipping_loss"] == pytest.approx(max(0, 1-consumption-0.95), abs=1e-12)
        assert abs(s["fuel_balance_residual"]) < 1e-12
        for r in rows:
            assert r["reward"] == pytest.approx(sum(r[k] for k in (
                "price_advantage_reward", "safety_reward", "operational_reward", "imo_reward")))
            assert r["step_sci"] == pytest.approx(r["bunker_amount"] * r["decision_price"] * r["decision_fx"])
            assert r["safety_reward"] <= 0
