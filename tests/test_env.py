from collections import deque

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


def test_no_bunkering_has_zero_amount_and_cost_index():
    env = BunkeringEnv()
    env.reset(seed=21)

    _, _, _, _, info = env.step(0)

    assert info["actual_bunker_amount"] == 0.0
    assert info["step_cost_index"] == 0.0
    assert info["cumulative_cost_index"] == 0.0
    assert {
        "decision_fuel_price",
        "decision_price_ma30",
        "decision_fx_rate",
    } <= info.keys()


def test_requested_bunker_amount_is_capped_by_available_capacity():
    env = BunkeringEnv()
    env.reset(seed=22)
    env._fuel_remaining = 0.2
    env._state = env._observation()

    _, _, _, _, info = env.step(1)

    expected_capacity = (
        env._MAX_REFILLED_FUEL
        - (0.2 - env._FUEL_CONSUMPTION_PER_STEP)
    )
    assert info["actual_bunker_amount"] == pytest.approx(expected_capacity)
    assert info["actual_bunker_amount"] < env._BUNKER_REFILL_AMOUNT
    assert env._fuel_remaining == pytest.approx(env._MAX_REFILLED_FUEL)


def test_bunkering_at_full_post_consumption_tank_has_zero_actual_amount():
    env = BunkeringEnv()
    env.reset(seed=23)

    _, _, _, _, info = env.step(1)

    assert info["actual_bunker_amount"] == 0.0
    assert info["step_cost_index"] == 0.0


def test_zero_actual_bunker_amount_has_zero_price_advantage_reward():
    env = BunkeringEnv()
    env.reset(seed=24)
    env._raw_fuel_price = 400.0
    env._price_history = deque([500.0], maxlen=30)

    _, _, _, _, info = env.step(1)

    assert info["actual_bunker_amount"] == 0.0
    assert info["reward_breakdown"]["fuel_cost_saving"] == 0.0


def test_reward_uses_decision_time_price_and_moving_average():
    env = BunkeringEnv()
    env.reset(seed=25)
    env._raw_fuel_price = 400.0
    env._price_history = deque([500.0], maxlen=30)
    env._fuel_remaining = 0.2
    env._state = env._observation()

    _, _, _, _, info = env.step(1)

    assert info["decision_fuel_price"] == 400.0
    assert info["decision_price_ma30"] == 500.0
    assert info["reward_breakdown"]["fuel_cost_saving"] == pytest.approx(0.2)


def test_step_cost_index_matches_decision_snapshot_formula():
    env = BunkeringEnv()
    env.reset(seed=26)
    env._raw_fuel_price = 420.0
    env._price_history = deque([500.0], maxlen=30)
    env._raw_fx_rate = 1325.0
    env._fuel_remaining = 0.2
    env._state = env._observation()

    _, _, _, _, info = env.step(1)

    expected = (
        info["actual_bunker_amount"]
        * info["decision_fuel_price"]
        * info["decision_fx_rate"]
    )
    assert info["step_cost_index"] == pytest.approx(expected)


def test_cumulative_cost_index_is_exact_running_sum():
    env = BunkeringEnv()
    env.reset(seed=27)
    observed_step_costs = []

    for fuel_remaining in (0.2, 0.3):
        env._fuel_remaining = fuel_remaining
        env._state = env._observation()
        _, _, _, _, info = env.step(1)
        observed_step_costs.append(info["step_cost_index"])

    assert info["cumulative_cost_index"] == pytest.approx(sum(observed_step_costs))


def test_reset_clears_cumulative_cost_index():
    env = BunkeringEnv()
    env.reset(seed=28)
    env._fuel_remaining = 0.2
    env._state = env._observation()
    env.step(1)
    assert env._cumulative_cost_index > 0.0

    env.reset(seed=29)

    assert env._cumulative_cost_index == 0.0


def test_reset_reinitializes_decision_snapshot_for_new_episode():
    env = BunkeringEnv()
    env.reset(seed=30)
    env.step(0)
    previous_snapshot = (
        env._decision_fuel_price,
        env._decision_price_ma30,
        env._decision_fx_rate,
    )

    env.reset(seed=31)
    reset_snapshot = (
        env._decision_fuel_price,
        env._decision_price_ma30,
        env._decision_fx_rate,
    )

    assert reset_snapshot == pytest.approx(
        (env.raw_fuel_price, env.raw_price_ma30, env._raw_fx_rate)
    )
    assert reset_snapshot != pytest.approx(previous_snapshot)


def test_cost_and_bunker_amount_are_finite_and_nonnegative():
    env = BunkeringEnv()
    env.reset(seed=32)
    env._fuel_remaining = 0.2
    env._state = env._observation()

    _, _, _, _, info = env.step(1)

    for key in (
        "actual_bunker_amount",
        "step_cost_index",
        "cumulative_cost_index",
    ):
        assert np.isfinite(info[key])
        assert info[key] >= 0.0


@pytest.mark.parametrize(
    ("actual_bunker_amount", "expected_price_advantage"),
    [
        (BunkeringEnv._BUNKER_AMOUNT_EPSILON, 0.0),
        (BunkeringEnv._BUNKER_AMOUNT_EPSILON * 1.01, 0.2),
    ],
)
def test_price_advantage_reward_respects_bunker_amount_epsilon(
    actual_bunker_amount, expected_price_advantage
):
    env = BunkeringEnv()
    state, _ = env.reset(seed=33)

    _, breakdown = env._compute_reward(
        state,
        1,
        state,
        decision_fuel_price=400.0,
        decision_price_ma30=500.0,
        actual_bunker_amount=actual_bunker_amount,
    )

    assert breakdown["fuel_cost_saving"] == pytest.approx(
        expected_price_advantage
    )
