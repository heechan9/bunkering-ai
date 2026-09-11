import json

import pandas as pd
import pytest

from scripts.diagnose_reward import main as diagnose
from scripts.summarize_reward_diagnostics import aggregate


@pytest.fixture
def runs(tmp_path):
    # Deliberately synthetic DQN fixture copied from a rule: validates aggregation only.
    paths = []
    for i in range(2):
        path = tmp_path / str(i)
        diagnose(["--episodes", "2", "--output-dir", str(path)])
        for name in ("steps.csv", "episodes.csv"):
            frame = pd.read_csv(path / name)
            fake = frame[frame.policy == "safe_stock"].copy()
            fake["policy"] = "double_dqn"
            pd.concat([frame, fake]).to_csv(path / name, index=False)
        manifest = json.loads((path / "manifest.json").read_text())
        manifest["policies"].append("double_dqn")
        manifest["checkpoint"] = {"name": "fixture", "sha256": str(i) * 64}
        (path / "manifest.json").write_text(json.dumps(manifest))
        paths.append(path)
    return paths


def test_deduplicates_rules_and_keeps_model_units(runs, tmp_path):
    out = tmp_path / "summary"
    result = aggregate(runs, out)
    assert len(result) == 5
    assert (result.evaluation_cases == 2).all()
    assert len(result[result.policy == "safe_stock"]) == 1
    safe = result[result.policy == "safe_stock"].iloc[0]
    assert safe.success_rate == 1
    assert safe.violation_episode_rate == 1
    assert safe.violation_steps_mean == 1
    assert safe.violation_step_fraction == pytest.approx(1 / 30)
    trace = pd.read_csv(out / "case_trace.csv")
    assert set(trace.seed) == {42}
    assert len(trace[trace.policy == "safe_stock"]) == 30
    with pytest.raises(ValueError, match="new directory"):
        aggregate(runs, out)


@pytest.mark.parametrize("fault", ["checkpoint", "contract", "missing", "accounting", "nan"])
def test_rejects_invalid_bundles(runs, tmp_path, fault):
    path = runs[1]
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if fault == "checkpoint":
        manifest["checkpoint"]["sha256"] = "0" * 64
    elif fault == "contract":
        manifest["env_config"]["max_steps"] = 43
    else:
        frame = pd.read_csv(path / "episodes.csv")
        if fault == "missing":
            frame = frame.iloc[1:]
        elif fault == "accounting":
            frame.loc[0, "step_sci"] += 1
        else:
            frame.loc[0, "reward"] = float("nan")
        frame.to_csv(path / "episodes.csv", index=False)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        aggregate(runs, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()
