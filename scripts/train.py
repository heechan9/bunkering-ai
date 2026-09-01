"""Train a Double DQN agent on the synthetic bunkering environment."""

from __future__ import annotations

import argparse
import random
import site
import sys
from datetime import datetime
from pathlib import Path

# Some embedded Python distributions do not add the user site-packages path.
site.addsitedir(site.getusersitepackages())

import numpy as np
import torch
import yaml
from torch.utils.tensorboard import SummaryWriter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.dqn import DQNAgent, ReplayBuffer
from envs.bunkering_env import BunkeringEnv


def load_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def train(
    config: dict,
    n_episodes: int,
    seed: int,
    checkpoint_path: Path | None = None,
) -> list[float]:
    """Run the configured training loop and return episode rewards.

    When ``checkpoint_path`` is given, the trained policy is persisted there so
    a later independent evaluation can reload exactly these weights instead of
    re-training.
    """
    set_seed(seed)
    env_config = config["env"]
    train_config = config["train"]
    exploration_config = config["exploration"]
    env = BunkeringEnv(**env_config)
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n
    agent = DQNAgent(state_dim, action_dim, config)
    buffer = ReplayBuffer(int(train_config["replay_buffer_size"]))

    epsilon = float(exploration_config["epsilon_start"])
    epsilon_end = float(exploration_config["epsilon_end"])
    epsilon_decay = (epsilon - epsilon_end) / int(exploration_config["epsilon_decay_steps"])
    batch_size = int(train_config["batch_size"])
    target_update_freq = int(train_config["target_update_freq"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = PROJECT_ROOT / "runs" / f"dqn_{timestamp}"
    episode_rewards: list[float] = []
    global_step = 0

    with SummaryWriter(log_dir=str(log_dir)) as writer:
        for episode in range(n_episodes):
            state, _ = env.reset(seed=seed + episode)
            episode_reward = 0.0
            episode_ended = False

            while not episode_ended:
                action = agent.select_action(state, epsilon)
                next_state, reward, terminated, truncated, _ = env.step(action)
                episode_ended = terminated or truncated
                buffer.push(
                    state,
                    action,
                    reward,
                    next_state,
                    terminated=terminated,
                )
                if len(buffer) >= batch_size:
                    loss = agent.update(buffer.sample(batch_size))
                    if not np.isfinite(loss):
                        raise FloatingPointError("DQN loss became non-finite")

                state = next_state
                episode_reward += reward
                global_step += 1
                epsilon = max(epsilon_end, epsilon - epsilon_decay)
                if global_step % target_update_freq == 0:
                    agent.sync_target_network()

            if not np.isfinite(episode_reward):
                raise FloatingPointError("Episode reward became non-finite")
            episode_rewards.append(episode_reward)
            writer.add_scalar("episode_reward", episode_reward, episode)
            writer.add_scalar("epsilon", epsilon, episode)
            print(
                f"episode={episode + 1}/{n_episodes} "
                f"reward={episode_reward:.4f} epsilon={epsilon:.4f}"
            )

    print(f"TensorBoard logs saved to: {log_dir}")

    if checkpoint_path is not None:
        saved_path = agent.save_checkpoint(
            checkpoint_path,
            metadata={
                "train_seed": int(seed),
                "n_episodes": int(n_episodes),
                "global_steps": int(global_step),
                "final_epsilon": float(epsilon),
                "env_config": dict(env_config),
            },
        )
        print(f"Checkpoint saved to: {saved_path}")

    return episode_rewards


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Double DQN on BunkeringEnv.")
    parser.add_argument("--episodes", type=int, default=None, help="Override configured episode count")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "dqn.yaml",
        help="Path to DQN YAML configuration",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=PROJECT_ROOT / "checkpoints" / "dqn_final.pt",
        help="Where to save the trained policy checkpoint",
    )
    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Train without writing a checkpoint file",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    episodes = args.episodes if args.episodes is not None else int(config["train"]["n_episodes"])
    if episodes < 1:
        raise ValueError("episodes must be at least 1")
    train(
        config,
        episodes,
        args.seed,
        checkpoint_path=None if args.no_checkpoint else args.checkpoint,
    )


if __name__ == "__main__":
    main()
