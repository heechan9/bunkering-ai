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
    records = baseline.run_baselines(n_episodes=2, base_seed=100)

    assert [record["seed"] for record in records] == [100, 101, 100, 101]


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
