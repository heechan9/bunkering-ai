"""Double DQN components used to train on :class:`envs.BunkeringEnv`."""

from __future__ import annotations

import random
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

# Bumped only when the persisted payload layout changes incompatibly.
CHECKPOINT_FORMAT_VERSION = 1


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
    """Fixed-size replay buffer with an explicit termination bootstrap mask."""

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
        *,
        terminated: bool,
    ) -> None:
        """Store whether the transition truly terminated the MDP.

        Time-limit truncations must be stored with ``terminated=False`` so the
        DQN target continues to bootstrap from ``next_state``.
        """
        self._buffer.append(
            (
                np.asarray(state, dtype=np.float32).copy(),
                int(action),
                float(reward),
                np.asarray(next_state, dtype=np.float32).copy(),
                bool(terminated),
            )
        )

    def sample(
        self, batch_size: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if batch_size > len(self):
            raise ValueError("batch_size cannot exceed the number of stored transitions")
        batch = random.sample(self._buffer, batch_size)
        states, actions, rewards, next_states, terminations = zip(*batch)
        return (
            np.asarray(states, dtype=np.float32),
            np.asarray(actions, dtype=np.int64),
            np.asarray(rewards, dtype=np.float32),
            np.asarray(next_states, dtype=np.float32),
            np.asarray(terminations, dtype=np.float32),
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
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dims = hidden_dims
        # Minimal self-contained config so a checkpoint can rebuild this agent
        # without the original YAML file being present.
        self.agent_config: dict[str, Any] = {
            "network": {"hidden_dims": list(hidden_dims)},
            "train": {
                "learning_rate": float(train_config["learning_rate"]),
                "gamma": self.gamma,
                "device": str(self.device),
            },
        }
        # Populated by load_checkpoint; empty for a freshly constructed agent.
        self.checkpoint_metadata: dict[str, Any] = {}
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
        return self.greedy_action(state)

    def greedy_action(self, state: np.ndarray) -> int:
        """Return the argmax action without drawing from any random source.

        Evaluation must not depend on global RNG state, so this deliberately
        skips the epsilon draw that :meth:`select_action` performs.
        """
        state_tensor = torch.as_tensor(state, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            return int(self.policy_net(state_tensor.unsqueeze(0)).argmax(dim=1).item())

    def update(
        self,
        batch: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    ) -> float:
        """Run one Double DQN update and return its scalar Huber loss."""
        states, actions, rewards, next_states, terminations = batch
        states_tensor = torch.as_tensor(states, dtype=torch.float32, device=self.device)
        actions_tensor = torch.as_tensor(actions, dtype=torch.int64, device=self.device)
        rewards_tensor = torch.as_tensor(rewards, dtype=torch.float32, device=self.device)
        next_states_tensor = torch.as_tensor(next_states, dtype=torch.float32, device=self.device)
        terminations_tensor = torch.as_tensor(
            terminations, dtype=torch.float32, device=self.device
        )

        current_q_values = self.policy_net(states_tensor).gather(
            1, actions_tensor.unsqueeze(1)
        ).squeeze(1)
        with torch.no_grad():
            next_actions = self.policy_net(next_states_tensor).argmax(dim=1, keepdim=True)
            next_q_values = self.target_net(next_states_tensor).gather(1, next_actions).squeeze(1)
            td_target = rewards_tensor + self.gamma * next_q_values * (
                1.0 - terminations_tensor
            )

        loss = self.loss_function(current_q_values, td_target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def sync_target_network(self) -> None:
        """Copy policy weights to the frozen target network."""
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def save_checkpoint(
        self, path: Path | str, *, metadata: dict[str, Any] | None = None
    ) -> Path:
        """Persist weights, optimizer state, and rebuild parameters to ``path``.

        ``metadata`` records provenance (training seed, episode count, env
        config) so a later independent evaluation can report exactly which run
        produced the policy it loaded. It is stored verbatim and never used to
        rebuild the network.
        """
        checkpoint_path = Path(path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format_version": CHECKPOINT_FORMAT_VERSION,
            "state_dim": int(self.state_dim),
            "action_dim": int(self.action_dim),
            "config": self.agent_config,
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "metadata": dict(metadata or {}),
        }
        torch.save(payload, checkpoint_path)
        return checkpoint_path

    @classmethod
    def load_checkpoint(
        cls, path: Path | str, *, device: str | torch.device | None = None
    ) -> "DQNAgent":
        """Rebuild an agent saved by :meth:`save_checkpoint`.

        The checkpoint carries its own architecture and optimizer settings, so
        loading never silently falls back to defaults that would change which
        action the stored weights select.
        """
        checkpoint_path = Path(path)
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"checkpoint not found: {checkpoint_path}")

        map_location = torch.device(device) if device is not None else None
        payload = torch.load(
            checkpoint_path, map_location=map_location, weights_only=True
        )

        format_version = payload.get("format_version")
        if format_version != CHECKPOINT_FORMAT_VERSION:
            raise ValueError(
                f"unsupported checkpoint format_version {format_version!r}; "
                f"expected {CHECKPOINT_FORMAT_VERSION}"
            )

        config = dict(payload["config"])
        if device is not None:
            config["train"] = {**config["train"], "device": str(torch.device(device))}

        agent = cls(int(payload["state_dim"]), int(payload["action_dim"]), config)
        agent.policy_net.load_state_dict(payload["policy_net"])
        agent.target_net.load_state_dict(payload["target_net"])
        agent.optimizer.load_state_dict(payload["optimizer"])
        for parameter in agent.target_net.parameters():
            parameter.requires_grad_(False)
        agent.checkpoint_metadata = dict(payload.get("metadata", {}))
        return agent
