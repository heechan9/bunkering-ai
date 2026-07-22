import math

import numpy as np

from agents.dqn import DQNAgent, QNetwork, ReplayBuffer


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
        buffer.push(np.zeros(6), action % 4, 1.0, np.ones(6), action == 4)

    states, actions, rewards, next_states, dones = buffer.sample(4)
    assert len(buffer) == 5
    assert states.shape == (4, 6)
    assert actions.shape == rewards.shape == dones.shape == (4,)
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
            action % 2 == 0,
        )

    loss = agent.update(buffer.sample(8))
    assert math.isfinite(loss)
