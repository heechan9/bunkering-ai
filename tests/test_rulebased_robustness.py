"""Guard the committed Rule-based 200-seed robustness artifacts.

These files are produced outside ``scripts/evaluate.py`` by
``scripts/robustness/script2_baseline_200seed_eval.py``. The checks below keep
them internally consistent and, more importantly, keep the seeds they share
with the official 100-seed comparison in exact agreement with it. A drift in
either direction means the two harnesses no longer describe the same policies.
"""

import json
from pathlib import Path

import pandas as pd

ROBUSTNESS_DIR = Path("results/robustness")
RAW_PATH = ROBUSTNESS_DIR / "independent_eval_raw_with_episode.csv"
SUMMARY_PATH = ROBUSTNESS_DIR / "independent_eval_summary_final.csv"
STABILITY_PATH = ROBUSTNESS_DIR / "independent_eval_stability_final.csv"
MANIFEST_PATH = ROBUSTNESS_DIR / "independent_eval_manifest.json"

RULE_BASED_POLICIES = ("fixed_fueling", "price_reactive", "safe_stock")
BASE_SEED = 42
N_EPISODES = 200
OFFICIAL_SEED_END = 141  # official evaluation covers seeds 42-141


def test_raw_covers_every_policy_and_seed_exactly_once():
    raw = pd.read_csv(RAW_PATH)

    assert set(raw["policy"]) == set(RULE_BASED_POLICIES)
    assert len(raw) == len(RULE_BASED_POLICIES) * N_EPISODES
    assert not raw.duplicated(subset=["policy", "seed"]).any()
    for policy in RULE_BASED_POLICIES:
        seeds = sorted(raw.loc[raw["policy"] == policy, "seed"])
        assert seeds == list(range(BASE_SEED, BASE_SEED + N_EPISODES))


def test_manifest_case_set_matches_raw_rows():
    raw = pd.read_csv(RAW_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    manifest_cases = {(case["policy"], case["seed"]) for case in manifest["cases"]}
    raw_cases = set(zip(raw["policy"], raw["seed"]))

    assert manifest_cases == raw_cases
    assert manifest["seed_range"] == {
        "start": BASE_SEED,
        "end": BASE_SEED + N_EPISODES - 1,
        "count": N_EPISODES,
    }
    assert manifest["env_config"] == {
        "n_ports": 3,
        "max_steps": 30,
        "min_safe_fuel": 0.15,
    }


def test_summary_is_recomputable_from_raw():
    raw = pd.read_csv(RAW_PATH)
    summary = pd.read_csv(SUMMARY_PATH).set_index("policy")

    for policy in RULE_BASED_POLICIES:
        rows = raw[raw["policy"] == policy]
        expected = summary.loc[policy]

        assert expected["episodes"] == len(rows)
        assert rows["reward"].mean() == pytest_approx(expected["reward_mean"])
        assert rows["reward"].std(ddof=0) == pytest_approx(expected["reward_std_ddof0"])
        assert rows["synthetic_cost_index"].mean() == pytest_approx(expected["sci_mean"])
        assert rows["bunkering_count"].mean() == pytest_approx(
            expected["bunkering_count_mean"]
        )
        assert (rows["termination_reason"] == "arrived").sum() == expected["term_arrived"]
        assert (
            rows["termination_reason"] == "fuel_depleted"
        ).sum() == expected["term_fuel_depleted"]
        assert (rows["termination_reason"] == "timeout").sum() == expected["term_timeout"]


def test_overlapping_seeds_match_official_evaluation_exactly():
    raw = pd.read_csv(RAW_PATH)

    for policy in RULE_BASED_POLICIES:
        official = pd.read_csv(f"results/evaluation/raw_{policy}.csv").sort_values("seed")
        independent = (
            raw[(raw["policy"] == policy) & (raw["seed"] <= OFFICIAL_SEED_END)]
            .sort_values("seed")
            .reset_index(drop=True)
        )
        official = official.reset_index(drop=True)

        assert list(independent["seed"]) == list(official["seed"])
        assert list(independent["reward"]) == list(official["reward"])
        assert list(independent["synthetic_cost_index"]) == list(
            official["Synthetic Cost Index"]
        )
        assert list(independent["bunkering_count"]) == list(official["bunkering_count"])
        assert list(independent["termination_reason"]) == list(
            official["termination_reason"]
        )


def test_stability_windows_are_cumulative_prefixes_of_the_same_run():
    raw = pd.read_csv(RAW_PATH)
    stability = pd.read_csv(STABILITY_PATH)

    for row in stability.itertuples():
        window = raw[(raw["policy"] == row.policy) & (raw["episode"] < row.n_seeds_in_window)]

        assert len(window) == row.n_seeds_in_window
        arrived = (window["termination_reason"] == "arrived").sum()
        assert arrived == row.arrived_count
        assert round(arrived / row.n_seeds_in_window, 4) == row.arrival_rate
        assert round(float(window["reward"].mean()), 4) == row.reward_mean


def pytest_approx(value):
    from pytest import approx

    return approx(value, rel=1e-9, abs=1e-12)
