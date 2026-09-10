import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.multiseed.aggregate import aggregate, collect


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
