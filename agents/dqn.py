"""Double DQN components used to train on :class:`envs.BunkeringEnv`."""

from __future__ import annotations

import random
from collections import deque
from typing import Any

import numpy as np
import torch
from torch import nn


class QNetwork(nn.Module):
    """Configurable multilayer perceptron mapping a state to action Q-values."""

    def __init__(
        self, state_dim: int, action_dim: int, hidden_dims: list[int] | None = None
    ) -> None:
        super().__init__()
        hidden_dims = hidden_dims or [128, 128]
        layers: list[nn.Module] = []
        input_dim = state_dim
        for hidden_dim in hidden_dims:
            layers.extend((nn.Linear(input_dim, hidden_dim), nn.ReLU()))
            input_dim = hidden_dim
        layers.append(nn.Linear(input_dim, action_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, states: torch.Tensor) -> torch.Tensor:
        return self.network(states)


class ReplayBuffer:
    """Fixed-size experience replay buffer backed by a deque."""

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._buffer: deque[tuple[np.ndarray, int, float, np.ndarray, bool]] = deque(
            maxlen=capacity
        )

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self._buffer.append(
            (
                np.asarray(state, dtype=np.float32).copy(),
                int(action),
                float(reward),
                np.asarray(next_state, dtype=np.float32).copy(),
                bool(done),
            )
        )

    def sample(
        self, batch_size: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if batch_size > len(self):
            raise ValueError("batch_size cannot exceed the number of stored transitions")
        batch = random.sample(self._buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.asarray(states, dtype=np.float32),
            np.asarray(actions, dtype=np.int64),
            np.asarray(rewards, dtype=np.float32),
            np.asarray(next_states, dtype=np.float32),
            np.asarray(dones, dtype=np.float32),
        )

    def __len__(self) -> int:
        return len(self._buffer)


class DQNAgent:
    """Double DQN agent with a policy network and a frozen target network."""

    def __init__(self, state_dim: int, action_dim: int, config: dict[str, Any]) -> None:
        network_config = config.get("network", config)
        train_config = config.get("train", config)
        hidden_dims = list(network_config.get("hidden_dims", [128, 128]))

        self.gamma = float(train_config["gamma"])
        self.device = torch.device(train_config.get("device", "cpu"))
        self.action_dim = action_dim
        self.policy_net = QNetwork(state_dim, action_dim, hidden_dims).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim, hidden_dims).to(self.device)
        self.optimizer = torch.optim.Adam(
            self.policy_net.parameters(), lr=float(train_config["learning_rate"])
        )
        self.loss_function = nn.SmoothL1Loss()
        self.sync_target_network()
        self.target_net.eval()
        for parameter in self.target_net.parameters():
            parameter.requires_grad_(False)

    def select_action(self, state: np.ndarray, epsilon: float) -> int:
        """Choose a valid action using epsilon-greedy exploration."""
        if random.random() < epsilon:
            return random.randrange(self.action_dim)

        state_tensor = torch.as_tensor(state, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            return int(self.policy_net(state_tensor.unsqueeze(0)).argmax(dim=1).item())

    def update(
        self,
        batch: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    ) -> float:
        """Run one Double DQN update and return its scalar Huber loss."""
        states, actions, rewards, next_states, dones = batch
        states_tensor = torch.as_tensor(states, dtype=torch.float32, device=self.device)
        actions_tensor = torch.as_tensor(actions, dtype=torch.int64, device=self.device)
        rewards_tensor = torch.as_tensor(rewards, dtype=torch.float32, device=self.device)
        next_states_tensor = torch.as_tensor(next_states, dtype=torch.float32, device=self.device)
        dones_tensor = torch.as_tensor(dones, dtype=torch.float32, device=self.device)

        current_q_values = self.policy_net(states_tensor).gather(
            1, actions_tensor.unsqueeze(1)
        ).squeeze(1)
        with torch.no_grad():
            next_actions = self.policy_net(next_states_tensor).argmax(dim=1, keepdim=True)
            next_q_values = self.target_net(next_states_tensor).gather(1, next_actions).squeeze(1)
            td_target = rewards_tensor + self.gamma * next_q_values * (1.0 - dones_tensor)

        loss = self.loss_function(current_q_values, td_target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def sync_target_network(self) -> None:
        """Copy policy weights to the frozen target network."""
        self.target_net.load_state_dict(self.policy_net.state_dict())
