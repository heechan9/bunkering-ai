import math
import random

import numpy as np
import pytest
import torch

from agents.dqn import (
    CHECKPOINT_FORMAT_VERSION,
    DQNAgent,
    QNetwork,
    ReplayBuffer,
)


CONFIG = {
    "network": {"hidden_dims": [128, 128]},
    "train": {"learning_rate": 1e-4, "gamma": 0.99},
}


def test_qnetwork_forward_output_shape():
    network = QNetwork(state_dim=6, action_dim=4, hidden_dims=[128, 128])
    output = network(__import__("torch").randn(5, 6))

    assert output.shape == (5, 4)


def test_replay_buffer_sample_shapes():
    buffer = ReplayBuffer(capacity=10)
    for action in range(5):
        buffer.push(
            np.zeros(6),
            action % 4,
            1.0,
            np.ones(6),
            terminated=action == 4,
        )

    states, actions, rewards, next_states, terminations = buffer.sample(4)
    assert len(buffer) == 5
    assert states.shape == (4, 6)
    assert actions.shape == rewards.shape == terminations.shape == (4,)
    assert next_states.shape == (4, 6)


def test_epsilon_greedy_actions_are_valid():
    agent = DQNAgent(state_dim=6, action_dim=4, config=CONFIG)

    actions = [agent.select_action(np.zeros(6, dtype=np.float32), epsilon=1.0) for _ in range(30)]
    assert all(0 <= action < 4 for action in actions)


def test_dqn_update_returns_finite_loss():
    agent = DQNAgent(state_dim=6, action_dim=4, config=CONFIG)
    buffer = ReplayBuffer(capacity=16)
    for action in range(8):
        buffer.push(
            np.random.randn(6).astype(np.float32),
            action % 4,
            float(action),
            np.random.randn(6).astype(np.float32),
            terminated=action % 2 == 0,
        )

    loss = agent.update(buffer.sample(8))
    assert math.isfinite(loss)


def test_dqn_update_bootstraps_after_truncation_but_not_termination():
    config = {
        "network": {"hidden_dims": [4]},
        "train": {"learning_rate": 0.0, "gamma": 0.5},
    }
    agent = DQNAgent(state_dim=1, action_dim=2, config=config)

    with torch.no_grad():
        for parameter in agent.policy_net.parameters():
            parameter.zero_()
        for parameter in agent.target_net.parameters():
            parameter.zero_()
        agent.target_net.network[-1].bias[0] = 2.0

    def single_transition(terminated: bool):
        return (
            np.zeros((1, 1), dtype=np.float32),
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.float32),
            np.ones((1, 1), dtype=np.float32),
            np.asarray([terminated], dtype=np.float32),
        )

    truncation_loss = agent.update(single_transition(terminated=False))
    termination_loss = agent.update(single_transition(terminated=True))

    # At truncation the target is gamma * next_q = 1.0, giving Huber loss 0.5.
    assert truncation_loss == pytest.approx(0.5)
    # At termination the bootstrap term is masked, so both Q and target are zero.
    assert termination_loss == pytest.approx(0.0)


def _trained_agent(hidden_dims=None):
    """Build an agent and take one update so weights differ from a fresh init."""
    config = {
        "network": {"hidden_dims": hidden_dims or [32, 16]},
        "train": {"learning_rate": 5e-4, "gamma": 0.95},
    }
    agent = DQNAgent(state_dim=6, action_dim=4, config=config)
    agent.update(
        (
            np.random.default_rng(0).random((8, 6)).astype(np.float32),
            np.arange(8, dtype=np.int64) % 4,
            np.ones(8, dtype=np.float32),
            np.random.default_rng(1).random((8, 6)).astype(np.float32),
            np.zeros(8, dtype=np.float32),
        )
    )
    return agent


def test_greedy_action_does_not_consume_the_global_random_stream():
    agent = _trained_agent()
    state = np.zeros(6, dtype=np.float32)

    random.seed(0)
    before = random.random()
    random.seed(0)
    agent.greedy_action(state)

    assert random.random() == before


def test_checkpoint_round_trip_preserves_every_greedy_action(tmp_path):
    agent = _trained_agent()
    path = agent.save_checkpoint(tmp_path / "agent.pt")
    restored = DQNAgent.load_checkpoint(path)

    states = np.random.default_rng(7).random((256, 6)).astype(np.float32)
    assert [agent.greedy_action(state) for state in states] == [
        restored.greedy_action(state) for state in states
    ]


def test_checkpoint_restores_architecture_and_optimizer_settings(tmp_path):
    agent = _trained_agent(hidden_dims=[8, 8, 8])
    restored = DQNAgent.load_checkpoint(agent.save_checkpoint(tmp_path / "agent.pt"))

    assert restored.hidden_dims == [8, 8, 8]
    assert restored.state_dim == 6
    assert restored.action_dim == 4
    assert restored.gamma == pytest.approx(0.95)
    assert restored.optimizer.param_groups[0]["lr"] == pytest.approx(5e-4)
    # The target network must stay frozen after a reload.
    assert all(not p.requires_grad for p in restored.target_net.parameters())


def test_checkpoint_round_trips_provenance_metadata(tmp_path):
    agent = _trained_agent()
    metadata = {
        "train_seed": 42,
        "n_episodes": 1000,
        "env_config": {"n_ports": 3, "max_steps": 30, "min_safe_fuel": 0.15},
    }
    restored = DQNAgent.load_checkpoint(
        agent.save_checkpoint(tmp_path / "agent.pt", metadata=metadata)
    )

    assert restored.checkpoint_metadata == metadata
    # A freshly built agent must not claim provenance it does not have.
    assert _trained_agent().checkpoint_metadata == {}


def test_load_checkpoint_reports_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="checkpoint not found"):
        DQNAgent.load_checkpoint(tmp_path / "absent.pt")


def test_load_checkpoint_rejects_an_unsupported_format_version(tmp_path):
    agent = _trained_agent()
    path = agent.save_checkpoint(tmp_path / "agent.pt")
    payload = torch.load(path, weights_only=True)
    payload["format_version"] = CHECKPOINT_FORMAT_VERSION + 1
    torch.save(payload, path)

    with pytest.raises(ValueError, match="unsupported checkpoint format_version"):
        DQNAgent.load_checkpoint(path)
