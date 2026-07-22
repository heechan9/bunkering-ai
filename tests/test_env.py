import numpy as np
import pytest

from envs.bunkering_env import BunkeringEnv, STATE_VARS


def test_reset_returns_expected_shape_and_dtype():
    env = BunkeringEnv()
    observation, info = env.reset(seed=7)

    assert observation.shape == (len(STATE_VARS),)
    assert observation.dtype == np.float32
    assert env.observation_space.contains(observation)
    assert info["state_vars"] == STATE_VARS


def test_invalid_action_raises_assertion_error():
    env = BunkeringEnv()
    env.reset()

    with pytest.raises(AssertionError, match="invalid action"):
        env.step(env.action_space.n)


def test_short_voyage_is_truncated():
    env = BunkeringEnv(max_steps=5)
    env.reset(seed=12)

    truncated = False
    for _ in range(5):
        _, _, terminated, truncated, _ = env.step(1)
        assert not terminated
        if truncated:
            break

    assert truncated
