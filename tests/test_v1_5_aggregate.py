import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.robustness.aggregate_v1_5 import (
    SCHEMA_VERSION,
    SUMMARY_METRICS,
    aggregate,
    aggregate_effects,
    collect,
    plot_aggregate,
)


def _write_run(root: Path, seed: int, value: float, *, base_seed: int = 42) -> None:
    directory = root / f"seed_{seed}"
    directory.mkdir(parents=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "n_episodes": 100,
        "base_seed": base_seed,
        "scenarios": [{"scenario_id": "consumption_baseline"}],
        "checkpoint": {
            "sha256": str(seed) * 8,
            "metadata": {"train_seed": seed},
        },
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    pd.DataFrame(
        [
            {
                "scenario_id": "consumption_baseline",
                "scenario_family": "fuel_consumption",
                "policy": "double_dqn",
                "max_steps": 30,
                "consumption_multiplier": 1.0,
                **{metric: value for metric in SUMMARY_METRICS},
            }
        ]
    ).to_csv(directory / "summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "scenario_family": "fuel_consumption",
                "reference_scenario": "consumption_baseline",
                "scenario_id": "consumption_plus_20",
                "policy": "double_dqn",
                "metric": "sci_per_step_mean",
                "reference_value": value,
                "scenario_value": value + 1.0,
                "absolute_change": 1.0,
                "percent_change": 100.0 / value,
            }
        ]
    ).to_csv(directory / "paired_effects.csv", index=False)


def test_collect_and_aggregate_v1_5_training_seeds(tmp_path):
    _write_run(tmp_path, 42, 1.0)
    _write_run(tmp_path, 1042, 3.0)

    per_seed, effect_per_seed = collect(tmp_path)
    summary = aggregate(per_seed)
    effects = aggregate_effects(effect_per_seed)
    reward = summary.loc[summary["metric"] == "reward_mean"].iloc[0]

    assert set(per_seed["train_seed"]) == {42, 1042}
    assert reward["independent_training_seeds"] == 2
    assert reward["evaluation_replicates"] == 2
    assert reward["mean_across_training_seeds"] == 2.0
    assert reward["std_across_training_seeds_ddof0"] == 1.0
    assert effects.iloc[0]["absolute_change_mean"] == 1.0

    figure = tmp_path / "aggregate.png"
    plot_aggregate(summary, figure)
    assert figure.is_file()
    assert figure.stat().st_size > 0


def test_collect_rejects_contract_drift(tmp_path):
    _write_run(tmp_path, 42, 1.0)
    _write_run(tmp_path, 1042, 3.0, base_seed=43)

    with pytest.raises(ValueError, match="contract differs"):
        collect(tmp_path)


def test_rule_based_repetitions_are_not_counted_as_training_seeds():
    rows = pd.DataFrame(
        [
            {
                "scenario_id": "consumption_baseline",
                "scenario_family": "fuel_consumption",
                "policy": "safe_stock",
                "max_steps": 30,
                "consumption_multiplier": 1.0,
                "metric": "success_rate",
                "value": 1.0,
            }
            for _ in range(2)
        ]
    )

    result = aggregate(rows).iloc[0]

    assert result["independent_training_seeds"] == 0
    assert result["evaluation_replicates"] == 2
    assert result["std_across_training_seeds_ddof0"] == 0.0


def test_rule_based_repetition_drift_is_rejected():
    rows = pd.DataFrame(
        [
            {
                "scenario_id": "consumption_baseline",
                "scenario_family": "fuel_consumption",
                "policy": "safe_stock",
                "max_steps": 30,
                "consumption_multiplier": 1.0,
                "metric": "success_rate",
                "value": value,
            }
            for value in (1.0, 0.5)
        ]
    )

    with pytest.raises(ValueError, match="Rule-based result drift"):
        aggregate(rows)
