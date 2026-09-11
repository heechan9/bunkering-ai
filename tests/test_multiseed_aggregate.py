import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.multiseed.aggregate import (
    aggregate,
    aggregate_effects,
    aggregate_tail_risk,
    collect,
    collect_tail_risk,
    route_effects,
    write_markdown_report,
)


def _write_run(root: Path, route_root: Path, seed: int, sha: str, value: float) -> None:
    directory = root / f"seed_{seed}"
    (directory / "evaluation").mkdir(parents=True)
    manifest = {
        "n_episodes": 100,
        "base_seed": 42,
        "checkpoint": {"sha256": sha, "metadata": {"train_seed": seed}},
    }
    (directory / "evaluation_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    pd.DataFrame(
        [{"policy": "double_dqn", **{metric: value for metric in (
            "reward_mean", "synthetic_cost_index_mean", "success_mean",
            "fuel_depletion_mean", "bunkering_count_mean"
        )}}]
    ).to_csv(directory / "evaluation" / "summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "policy": "double_dqn",
                "reward": float(episode),
                "synthetic_cost_index": float(episode * 10),
                "bunkering_count": episode % 7,
            }
            for episode in range(100)
        ]
    ).to_csv(directory / "evaluation_results.csv", index=False)

    route_directory = route_root / f"seed_{seed}"
    route_directory.mkdir(parents=True)
    route_manifest = {
        "n_seeds": 100,
        "base_seed": 42,
        "checkpoint": {"sha256": sha, "metadata": {"train_seed": seed}},
    }
    (route_directory / "manifest.json").write_text(json.dumps(route_manifest), encoding="utf-8")
    pd.DataFrame([{
        "scenario_id": "normal", "reward_mean": value,
        "sci_per_step_mean": value, "bunkering_per_30_steps_mean": value,
        "success_rate": value, "fuel_depletion_rate": value,
    }]).to_csv(route_directory / "summary.csv", index=False)


def test_collect_and_aggregate_training_seeds(tmp_path):
    official = tmp_path / "official"
    route = tmp_path / "route"
    _write_run(official, route, 42, "a" * 64, 1.0)
    _write_run(official, route, 1042, "b" * 64, 3.0)

    per_seed = collect(official, route)
    summary = aggregate(per_seed)
    reward = summary[
        (summary["evaluation"] == "official_normal")
        & (summary["metric"] == "reward_mean")
    ].iloc[0]

    assert set(per_seed["train_seed"]) == {42, 1042}
    assert reward["training_seeds"] == 2
    assert reward["mean_across_training_seeds"] == 2.0
    assert reward["std_across_training_seeds_ddof0"] == 1.0


def test_collect_rejects_checkpoint_mismatch(tmp_path):
    official = tmp_path / "official"
    route = tmp_path / "route"
    _write_run(official, route, 42, "a" * 64, 1.0)
    manifest_path = route / "seed_42" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checkpoint"]["sha256"] = "b" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        collect(official, route)


def test_collect_and_aggregate_tail_risk(tmp_path):
    official = tmp_path / "official"
    route = tmp_path / "route"
    _write_run(official, route, 42, "a" * 64, 1.0)
    _write_run(official, route, 1042, "b" * 64, 3.0)

    per_seed = collect_tail_risk(official)
    summary = aggregate_tail_risk(per_seed)
    by_metric = summary.set_index("metric")

    assert set(per_seed["train_seed"]) == {42, 1042}
    assert by_metric.loc["reward_min", "mean_across_training_seeds"] == 0.0
    assert by_metric.loc[
        "reward_bottom_5pct_mean", "mean_across_training_seeds"
    ] == 2.0
    assert by_metric.loc[
        "synthetic_cost_index_top_5pct_mean", "mean_across_training_seeds"
    ] == 970.0
    assert by_metric.loc[
        "bunkering_count_max", "mean_across_training_seeds"
    ] == 6.0


def test_route_effects_are_paired_by_training_seed(tmp_path):
    per_seed = pd.DataFrame(
        [
            {"train_seed": seed, "evaluation": "route_stress", "scenario": scenario,
             "metric": metric, "value": value, "checkpoint_sha256": str(seed)}
            for seed, normal, stress in [(42, 100.0, 110.0), (1042, 200.0, 220.0)]
            for metric in ("sci_per_step_mean", "bunkering_per_30_steps_mean")
            for scenario, value in (("normal", normal), ("suez_cape_representative", stress))
        ]
    )

    effects = route_effects(per_seed)
    summary = aggregate_effects(effects)

    assert set(effects["percent_change"]) == {10.0}
    assert set(summary["training_seeds"]) == {2}
    assert set(summary["percent_change_mean"]) == {10.0}

    report = tmp_path / "summary.md"
    write_markdown_report(summary, report)
    text = report.read_text(encoding="utf-8")
    assert "Independent training seeds: **2**" in text
    assert "+10.00%" in text
    assert "not actual-voyage" in text


def test_route_effects_require_normal_stress_pair():
    per_seed = pd.DataFrame(
        [{
            "train_seed": 42,
            "evaluation": "route_stress",
            "scenario": "normal",
            "metric": "sci_per_step_mean",
            "value": 1.0,
            "checkpoint_sha256": "a" * 64,
        }]
    )

    with pytest.raises(ValueError, match="expected paired"):
        route_effects(per_seed)
