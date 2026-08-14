import csv

import numpy as np
import pytest

from scripts import baseline


class AlwaysBunkerStrategy:
    name = "always_bunker"

    def select_action(self, env, observation, step_index):
        del env, observation, step_index
        return 1


class EpsilonBoundaryEnv:
    _BUNKER_AMOUNT_EPSILON = 1e-6

    def __init__(self):
        self._step_index = 0

    def reset(self, *, seed):
        del seed
        self._step_index = 0
        return np.zeros(1, dtype=np.float32), {}

    def step(self, action):
        del action
        bunker_amounts = (
            0.0,
            self._BUNKER_AMOUNT_EPSILON,
            self._BUNKER_AMOUNT_EPSILON * 1.01,
        )
        actual_bunker_amount = bunker_amounts[self._step_index]
        self._step_index += 1
        terminated = self._step_index == len(bunker_amounts)
        info = {
            "actual_bunker_amount": actual_bunker_amount,
            "cumulative_cost_index": 123.0 if terminated else 0.0,
            "end_reason": "arrived" if terminated else "",
            "voyage_success": terminated,
        }
        return np.zeros(1, dtype=np.float32), 0.0, terminated, False, info


def test_run_episode_counts_only_amounts_above_bunker_epsilon(monkeypatch):
    monkeypatch.setattr(baseline, "BunkeringEnv", EpsilonBoundaryEnv)

    record = baseline.run_episode(AlwaysBunkerStrategy(), seed=42, episode=0)

    assert record["n_bunkering"] == 1
    assert record["seed"] == 42
    assert record["cumulative_cost_index"] == 123.0


def test_fixed_fueling_does_not_count_zero_actual_bunker_amount():
    record = baseline.run_episode(
        baseline.FixedFuelingStrategy(), seed=42, episode=0
    )

    assert record["n_bunkering"] == 0
    assert record["cumulative_cost_index"] == 0.0


def test_run_baselines_records_the_seed_used_for_each_episode():
    # NOTE(PR #5A): run_baselines now runs 3 strategies (added safe_stock),
    # so the expected seed sequence grew from 4 to 6 entries. This assertion
    # was updated, not deleted, to match the new strategy count while
    # preserving the original intent (identical sequential seed set per
    # strategy).
    records = baseline.run_baselines(n_episodes=2, base_seed=100)

    assert [record["seed"] for record in records] == [
        100, 101,  # fixed_fueling
        100, 101,  # price_reactive
        100, 101,  # safe_stock
    ]


def test_write_results_includes_seed_and_cost_index_columns(tmp_path):
    record = baseline.run_episode(
        baseline.PriceReactiveStrategy(), seed=42, episode=0
    )
    output_path = tmp_path / "baseline_results.csv"

    baseline.write_results([record], output_path)

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == [
        "strategy",
        "episode",
        "seed",
        "total_reward",
        "n_bunkering",
        "cumulative_cost_index",
        "end_reason",
        "voyage_success",
    ]
    assert len(rows) == 1
    assert rows[0]["seed"] == "42"
    assert float(rows[0]["cumulative_cost_index"]) == pytest.approx(
        record["cumulative_cost_index"]
    )


# ---------------------------------------------------------------------------
# PR #5A: SafeStockStrategy
# ---------------------------------------------------------------------------


def _observation_with_fuel_remaining(fuel_remaining: float) -> np.ndarray:
    observation = np.zeros(len(baseline.STATE_VARS), dtype=np.float32)
    observation[baseline._FUEL_REMAINING_INDEX] = fuel_remaining
    return observation


def test_safe_stock_does_not_bunker_above_threshold():
    env = baseline.BunkeringEnv()
    strategy = baseline.SafeStockStrategy()
    observation = _observation_with_fuel_remaining(env.min_safe_fuel + 0.01)

    assert strategy.select_action(env, observation, step_index=0) == 0


def test_safe_stock_bunkers_at_threshold():
    # Real boundary test: put the exact env.min_safe_fuel value into a
    # float32 observation (as the real env would) and confirm the strategy
    # still treats it as "at or below" threshold. SafeStockStrategy casts
    # its threshold to observation.dtype before comparing (see
    # scripts/baseline.py), so this no longer needs any test-side rounding
    # workaround -- float32(0.15) would otherwise round-trip to
    # 0.15000000596046448 in float64, strictly above the float64 0.15, and
    # fail a naive `<=` comparison.
    env = baseline.BunkeringEnv()
    strategy = baseline.SafeStockStrategy()
    observation = _observation_with_fuel_remaining(env.min_safe_fuel)

    assert strategy.select_action(env, observation, step_index=0) == 1


def test_safe_stock_bunkers_below_threshold():
    env = baseline.BunkeringEnv()
    strategy = baseline.SafeStockStrategy()
    observation = _observation_with_fuel_remaining(env.min_safe_fuel - 0.01)

    assert strategy.select_action(env, observation, step_index=0) == 1


def test_safe_stock_action_is_always_within_action_space():
    env = baseline.BunkeringEnv()
    strategy = baseline.SafeStockStrategy()

    for fuel_remaining in (0.0, env.min_safe_fuel - 0.05, env.min_safe_fuel, env.min_safe_fuel + 0.05, 1.0):
        observation = _observation_with_fuel_remaining(fuel_remaining)
        action = strategy.select_action(env, observation, step_index=0)
        assert env.action_space.contains(action)


def test_safe_stock_follows_env_min_safe_fuel_when_changed():
    # Uses a non-default threshold to prove the strategy reads
    # env.min_safe_fuel rather than a hardcoded constant. No rounding
    # workaround needed here either, for the same dtype-matching reason as
    # test_safe_stock_bunkers_at_threshold above.
    env = baseline.BunkeringEnv(min_safe_fuel=0.30)
    strategy = baseline.SafeStockStrategy()

    assert strategy.select_action(
        env, _observation_with_fuel_remaining(env.min_safe_fuel), step_index=0
    ) == 1
    assert strategy.select_action(
        env, _observation_with_fuel_remaining(env.min_safe_fuel + 0.01), step_index=0
    ) == 0


def test_run_baselines_returns_60_rows_for_three_strategies_times_20_episodes():
    records = baseline.run_baselines(n_episodes=20, base_seed=42)

    assert len(records) == 60


def test_run_baselines_includes_safe_stock_strategy_name():
    records = baseline.run_baselines(n_episodes=20, base_seed=42)

    strategy_names = {record["strategy"] for record in records}
    assert "safe_stock" in strategy_names


def test_run_baselines_20_rows_per_strategy():
    records = baseline.run_baselines(n_episodes=20, base_seed=42)

    for strategy_name in ("fixed_fueling", "price_reactive", "safe_stock"):
        subset = [r for r in records if r["strategy"] == strategy_name]
        assert len(subset) == 20


def test_write_results_preserves_schema_with_safe_stock_rows(tmp_path):
    records = baseline.run_baselines(n_episodes=2, base_seed=42)
    output_path = tmp_path / "baseline_results.csv"

    baseline.write_results(records, output_path)

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == [
        "strategy",
        "episode",
        "seed",
        "total_reward",
        "n_bunkering",
        "cumulative_cost_index",
        "end_reason",
        "voyage_success",
    ]
    assert len(rows) == 6  # 3 strategies x 2 episodes
    assert {row["strategy"] for row in rows} == {
        "fixed_fueling", "price_reactive", "safe_stock",
    }


def test_run_baselines_end_reason_and_voyage_success_are_consistent():
    records = baseline.run_baselines(n_episodes=20, base_seed=42)

    for record in records:
        assert record["end_reason"] in {"arrived", "fuel_depleted", "timeout"}
        assert record["voyage_success"] == (record["end_reason"] == "arrived")


def test_fixed_fueling_and_price_reactive_regression_unchanged():
    """PR #5A must not change existing strategy behaviour or results."""
    records = baseline.run_baselines(n_episodes=20, base_seed=42)

    fixed = [r for r in records if r["strategy"] == "fixed_fueling"]
    reactive = [r for r in records if r["strategy"] == "price_reactive"]

    fixed_rewards = np.array([r["total_reward"] for r in fixed])
    reactive_rewards = np.array([r["total_reward"] for r in reactive])

    assert fixed_rewards.mean() == pytest.approx(-2.0300, abs=1e-4)
    assert fixed_rewards.std() == pytest.approx(0.0000, abs=1e-4)
    assert sum(1 for r in fixed if r["end_reason"] == "fuel_depleted") == 20
    assert sum(1 for r in fixed if r["end_reason"] == "arrived") == 0

    assert reactive_rewards.mean() == pytest.approx(-1.8395, abs=1e-4)
    assert reactive_rewards.std() == pytest.approx(0.5125, abs=1e-4)
    assert sum(1 for r in reactive if r["end_reason"] == "arrived") == 2
    assert sum(1 for r in reactive if r["end_reason"] == "fuel_depleted") == 18


def test_safe_stock_20_episode_batch_all_arrive_with_zero_failures():
    """Locks in the headline preliminary result: 20/20 arrived, 0 failures."""
    records = baseline.run_baselines(n_episodes=20, base_seed=42)
    safe_stock = [r for r in records if r["strategy"] == "safe_stock"]

    assert len(safe_stock) == 20
    assert sum(1 for r in safe_stock if r["end_reason"] == "arrived") == 20
    assert sum(1 for r in safe_stock if r["end_reason"] == "fuel_depleted") == 0
    assert sum(1 for r in safe_stock if r["end_reason"] == "timeout") == 0
    assert sum(1 for r in safe_stock if r["voyage_success"]) == 20


def test_safe_stock_bunkers_exactly_once_per_episode():
    """Locks in the observed n_bunkering pattern, with the reasoning why.

    fuel_remaining starts at 1.0 and drops by _FUEL_CONSUMPTION_PER_STEP
    (0.05) each step. At step_index=17 (the 18th transition), the
    pre-transition fuel_remaining reaches exactly env.min_safe_fuel (0.15),
    so SafeStockStrategy bunkers once, refilling close to
    _MAX_REFILLED_FUEL (0.95). After that 18th transition, route_remaining
    is 1.0 - 18/30 = 0.4, i.e. 12 steps remain (0.4 * max_steps). Those 12
    remaining steps consume 12 * 0.05 = 0.60 fuel, which fits inside the
    ~0.95 refill with margin, so the strategy does not need to bunker a
    second time in this Synthetic Environment configuration. This is
    seed-independent because the price/fx random walk does not affect fuel
    consumption or the min_safe_fuel threshold. (Verified numerically: see
    PR #5A review discussion -- an earlier version of this docstring said
    "13 steps remain / 0.65 fuel", which was off by one transition.)
    """
    records = baseline.run_baselines(n_episodes=20, base_seed=42)
    safe_stock = [r for r in records if r["strategy"] == "safe_stock"]

    assert all(r["n_bunkering"] == 1 for r in safe_stock)


def test_safe_stock_mean_reward_regression_preliminary():
    """Regression-locks the preliminary sandbox mean reward.

    Tolerance (abs=0.01) is intentionally loose, not a strict equality: this
    value depends on BunkeringEnv's Synthetic random-walk parameters
    (_FUEL_PRICE_MEAN/SCALE, _FX_RATE_MEAN/SCALE), which are config, not
    something this PR should pin exactly. The purpose of this test is to
    catch an accidental large behavioural change (e.g. a future edit that
    breaks the dtype-matched threshold fix), not to assert this exact float
    forever. This number has NOT been confirmed against the real gymnasium
    package -- see docs/technical/state_action_reward_spec.md 4.1 for the
    provisional-status note.

    IMPORTANT for whoever runs this in the real repo: if this assertion
    fails there, do NOT edit -0.4921 to match whatever the real run
    produces. Report the actual value and investigate why it differs
    (e.g. a different numpy/PCG64 seeding path than assumed here) before
    touching this number -- the sandbox value is a preliminary reference
    point, not a value to make the test pass around.
    """
    records = baseline.run_baselines(n_episodes=20, base_seed=42)
    safe_stock_rewards = np.array(
        [r["total_reward"] for r in records if r["strategy"] == "safe_stock"]
    )

    assert safe_stock_rewards.mean() == pytest.approx(-0.4921, abs=0.01)
