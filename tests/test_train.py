import numpy as np

from scripts import train as train_module


class _TruncatingEnv:
    class _ObservationSpace:
        shape = (1,)

    class _ActionSpace:
        n = 1

    observation_space = _ObservationSpace()
    action_space = _ActionSpace()

    def __init__(self, **_kwargs):
        pass

    def reset(self, *, seed):
        del seed
        return np.zeros(1, dtype=np.float32), {}

    def step(self, action):
        del action
        return np.ones(1, dtype=np.float32), 0.0, False, True, {}


class _Agent:
    def __init__(self, *_args, **_kwargs):
        pass

    def select_action(self, state, epsilon):
        del state, epsilon
        return 0

    def sync_target_network(self):
        pass


class _RecordingBuffer:
    terminations: list[bool] = []

    def __init__(self, _capacity):
        self.terminations.clear()

    def push(self, _state, _action, _reward, _next_state, *, terminated):
        self.terminations.append(terminated)

    def __len__(self):
        return len(self.terminations)


class _Writer:
    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def add_scalar(self, *_args):
        pass


def test_train_stores_truncation_as_non_terminal_for_bootstrap(monkeypatch):
    monkeypatch.setattr(train_module, "BunkeringEnv", _TruncatingEnv)
    monkeypatch.setattr(train_module, "DQNAgent", _Agent)
    monkeypatch.setattr(train_module, "ReplayBuffer", _RecordingBuffer)
    monkeypatch.setattr(train_module, "SummaryWriter", _Writer)

    config = {
        "env": {},
        "train": {
            "replay_buffer_size": 8,
            "batch_size": 2,
            "target_update_freq": 100,
        },
        "exploration": {
            "epsilon_start": 0.0,
            "epsilon_end": 0.0,
            "epsilon_decay_steps": 1,
        },
    }

    rewards = train_module.train(config, n_episodes=1, seed=42)

    assert rewards == [0.0]
    assert _RecordingBuffer.terminations == [False]
