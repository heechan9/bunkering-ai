import pytest
from scripts.baseline import FixedFuelingStrategy, SafeStockStrategy
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
    with pytest.raises(SystemExit):
        main(["--output-dir", str(tmp_path)])


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
