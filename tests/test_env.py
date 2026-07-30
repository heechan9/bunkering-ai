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


def test_in_progress_info_has_empty_end_reason_and_false_success():
    env = BunkeringEnv()
    env.reset(seed=12)

    _, _, terminated, truncated, info = env.step(0)

    assert not terminated
    assert not truncated
    assert info["end_reason"] == ""
    assert info["voyage_success"] is False


def test_fuel_depleted_terminates_as_failure():
    env = BunkeringEnv(max_steps=30)
    env.reset(seed=12)

    for _ in range(30):
        _, _, terminated, truncated, info = env.step(0)
        if terminated or truncated:
            break

    assert terminated
    assert not truncated
    assert info["end_reason"] == "fuel_depleted"
    assert info["voyage_success"] is False


def test_arrival_terminates_as_success():
    env = BunkeringEnv(max_steps=4)
    env.reset(seed=12)

    for _ in range(4):
        _, _, terminated, truncated, info = env.step(1)
        if terminated or truncated:
            break

    assert terminated
    assert not truncated
    assert info["end_reason"] == "arrived"
    assert info["voyage_success"] is True


def test_fractional_route_completion_uses_tolerance():
    env = BunkeringEnv(max_steps=3)
    env.reset(seed=12)

    for _ in range(3):
        _, _, terminated, truncated, info = env.step(1)
        if terminated or truncated:
            break

    assert terminated
    assert not truncated
    assert info["end_reason"] == "arrived"
    assert info["voyage_success"] is True


def test_fuel_depletion_takes_precedence_over_arrival():
    env = BunkeringEnv(max_steps=1)
    env.reset(seed=12)
    env._fuel_remaining = env._FUEL_CONSUMPTION_PER_STEP

    _, _, terminated, truncated, info = env.step(0)

    assert terminated
    assert not truncated
    assert info["end_reason"] == "fuel_depleted"
    assert info["voyage_success"] is False
