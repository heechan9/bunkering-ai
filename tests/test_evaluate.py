import csv
import json
from pathlib import Path

import numpy as np
import pytest

from agents.dqn import DQNAgent
from envs.bunkering_env import BunkeringEnv
from evaluation.contract import (
    CSV_FIELDS,
    EpisodeResult,
    EvaluationCase,
    aggregate_results,
    validate_fair_evaluation_plan,
)
from evaluation.paper_audit import parse_strict_bool
from scripts import evaluate


ENV_CONFIG = {"n_ports": 3, "max_steps": 30, "min_safe_fuel": 0.15}
AGENT_CONFIG = {
    "network": {"hidden_dims": [16, 16]},
    "train": {"learning_rate": 1e-3, "gamma": 0.99},
}


class _ConstantPolicy:
    """Deterministic stand-in so plan/IO tests do not depend on a checkpoint."""

    def __init__(self, name: str, action: int) -> None:
        self.name = name
        self.action = action

    def select_action(self, env, observation, step_index):
        del env, observation, step_index
        return self.action


@pytest.fixture
def checkpoint_path(tmp_path):
    """A real, loadable checkpoint sized for the evaluation environment."""
    env = BunkeringEnv(**ENV_CONFIG)
    agent = DQNAgent(
        env.observation_space.shape[0], env.action_space.n, AGENT_CONFIG
    )
    path = tmp_path / "agent.pt"
    agent.save_checkpoint(path, metadata={"train_seed": 42, "n_episodes": 5})
    return path


def _plan(policy_names, n_episodes=4, base_seed=42):
    return evaluate.build_evaluation_plan(
        policy_names,
        n_episodes=n_episodes,
        base_seed=base_seed,
        env_config=ENV_CONFIG,
    )


def _results(policy_names, n_episodes=4):
    cases = _plan(policy_names, n_episodes=n_episodes)
    policies = {
        name: _ConstantPolicy(name, index % 2)
        for index, name in enumerate(policy_names)
    }
    return cases, evaluate.run_evaluation(policies, cases)


def test_plan_gives_every_policy_the_same_seed_and_episode_cases():
    policy_names = ["fixed_fueling", "double_dqn"]
    cases = _plan(policy_names, n_episodes=5, base_seed=100)

    assert len(cases) == 10
    per_policy = {
        name: sorted(
            (case.episode, case.seed) for case in cases if case.policy == name
        )
        for name in policy_names
    }
    assert per_policy["fixed_fueling"] == per_policy["double_dqn"]
    assert per_policy["double_dqn"] == [(index, 100 + index) for index in range(5)]
    # Building the plan is what enforces fairness, so it must stay valid.
    validate_fair_evaluation_plan(cases, policy_names)


def test_plan_rejects_non_positive_episode_count():
    with pytest.raises(ValueError, match="n_episodes"):
        _plan(["a", "b"], n_episodes=0)


def test_plan_rejects_policies_that_are_not_unique():
    with pytest.raises(ValueError):
        _plan(["safe_stock", "safe_stock"])


def test_run_episode_produces_a_contract_valid_record():
    case = EvaluationCase(seed=42, episode=0, policy="always_wait", env_config=ENV_CONFIG)
    result = evaluate.run_episode(_ConstantPolicy("always_wait", 0), case)

    assert isinstance(result, EpisodeResult)
    assert (result.seed, result.episode, result.policy) == (42, 0, "always_wait")
    assert result.success == (result.termination_reason == "arrived")
    assert result.fuel_depletion == (result.termination_reason == "fuel_depleted")
    assert result.synthetic_cost_index >= 0.0
    # Never bunkering cannot record a bunkering event.
    assert result.bunkering_count == 0


def test_run_episode_is_deterministic_for_a_repeated_seed():
    case = EvaluationCase(seed=7, episode=0, policy="always_bunker", env_config=ENV_CONFIG)
    first = evaluate.run_episode(_ConstantPolicy("always_bunker", 1), case)
    second = evaluate.run_episode(_ConstantPolicy("always_bunker", 1), case)

    assert first == second


def test_run_evaluation_runs_exactly_the_planned_cases():
    policy_names = ["fixed_fueling", "price_reactive"]
    cases, results = _results(policy_names, n_episodes=3)

    assert len(results) == len(cases)
    assert [(r.seed, r.episode, r.policy) for r in results] == [
        (c.seed, c.episode, c.policy) for c in cases
    ]


def test_run_evaluation_refuses_a_policy_without_a_runner():
    cases = _plan(["fixed_fueling", "double_dqn"], n_episodes=2)

    with pytest.raises(KeyError, match="double_dqn"):
        evaluate.run_evaluation({"fixed_fueling": _ConstantPolicy("fixed_fueling", 0)}, cases)


def test_results_csv_matches_the_contract_columns_and_strict_bool_format(tmp_path):
    _, results = _results(["safe_stock", "double_dqn"], n_episodes=3)
    path = evaluate.write_results_csv(results, tmp_path / "evaluation_results.csv")

    with path.open(encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        assert reader.fieldnames == list(CSV_FIELDS)
        rows = list(reader)

    assert len(rows) == len(results)
    for row in rows:
        # The audit rejects anything but exact 'true'/'false' spellings.
        assert row["success"] in {"true", "false"}
        assert row["fuel_depletion"] in {"true", "false"}
        assert parse_strict_bool(row["success"], "success") == (
            row["termination_reason"] == "arrived"
        )


def test_manifest_round_trips_into_a_valid_fair_plan(tmp_path):
    policy_names = ["fixed_fueling", "price_reactive", "safe_stock", "double_dqn"]
    cases = _plan(policy_names, n_episodes=3)
    path = evaluate.write_manifest_json(
        cases, policy_names, tmp_path / "evaluation_manifest.json", provenance={"base_seed": 42}
    )

    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["policies"] == policy_names
    assert manifest["base_seed"] == 42

    restored = [
        EvaluationCase(
            seed=case["seed"],
            episode=case["episode"],
            policy=case["policy"],
            env_config=case["env_config"],
        )
        for case in manifest["cases"]
    ]
    validate_fair_evaluation_plan(restored, tuple(manifest["policies"]))
    assert all(case.env_config == ENV_CONFIG for case in restored)


def test_csv_and_manifest_describe_the_same_cases(tmp_path):
    policy_names = ["safe_stock", "double_dqn"]
    cases, results = _results(policy_names, n_episodes=4)
    csv_path = evaluate.write_results_csv(results, tmp_path / "evaluation_results.csv")
    manifest_path = evaluate.write_manifest_json(
        cases, policy_names, tmp_path / "evaluation_manifest.json", provenance={}
    )

    with csv_path.open(encoding="utf-8") as csv_file:
        csv_cases = {
            (int(row["seed"]), int(row["episode"]), row["policy"])
            for row in csv.DictReader(csv_file)
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_cases = {
        (case["seed"], case["episode"], case["policy"]) for case in manifest["cases"]
    }

    assert csv_cases == manifest_cases
    assert len(csv_cases) == len(cases)


def test_per_policy_csv_splits_results_without_losing_rows(tmp_path):
    policy_names = ["fixed_fueling", "safe_stock"]
    _, results = _results(policy_names, n_episodes=3)
    paths = evaluate.write_per_policy_csv(results, policy_names, tmp_path)

    assert [path.name for path in paths] == [
        "raw_fixed_fueling.csv",
        "raw_safe_stock.csv",
    ]
    total = 0
    for path, policy in zip(paths, policy_names):
        with path.open(encoding="utf-8") as csv_file:
            rows = list(csv.DictReader(csv_file))
        assert {row["policy"] for row in rows} == {policy}
        total += len(rows)
    assert total == len(results)


def test_termination_counts_include_reasons_that_never_occurred():
    _, results = _results(["fixed_fueling"], n_episodes=3)
    counts = evaluate.count_termination_reasons(results)

    assert set(counts["fixed_fueling"]) == set(evaluate.TERMINATION_REASON_ORDER)
    assert sum(counts["fixed_fueling"].values()) == len(results)


def test_summary_csv_reports_mean_std_and_termination_breakdown(tmp_path):
    policy_names = ["safe_stock", "double_dqn"]
    _, results = _results(policy_names, n_episodes=4)
    aggregates = aggregate_results(results)
    counts = evaluate.count_termination_reasons(results)
    path = evaluate.write_summary_csv(
        aggregates, counts, policy_names, tmp_path / "summary.csv"
    )

    with path.open(encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        assert reader.fieldnames == list(evaluate.SUMMARY_FIELDS)
        rows = {row["policy"]: row for row in reader}

    assert list(rows) == policy_names
    for metric in evaluate.SUMMARY_METRIC_NAMES:
        for statistic in ("mean", "std"):
            assert rows["safe_stock"][f"{metric}_{statistic}"] != ""
    for policy in policy_names:
        episodes = int(rows[policy]["episodes"])
        breakdown = sum(
            int(rows[policy][f"termination_{reason}"])
            for reason in evaluate.TERMINATION_REASON_ORDER
        )
        assert breakdown == episodes == 4


def test_termination_csv_rows_sum_to_the_episode_count(tmp_path):
    policy_names = ["safe_stock", "double_dqn"]
    _, results = _results(policy_names, n_episodes=5)
    counts = evaluate.count_termination_reasons(results)
    path = evaluate.write_termination_csv(
        counts, policy_names, tmp_path / "termination_reasons.csv"
    )

    with path.open(encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert [row["policy"] for row in rows] == policy_names
    for row in rows:
        reasons = sum(int(row[reason]) for reason in evaluate.TERMINATION_REASON_ORDER)
        assert reasons == int(row["episodes"]) == 5


def test_comparison_figure_is_written(tmp_path):
    policy_names = ["safe_stock", "double_dqn"]
    _, results = _results(policy_names, n_episodes=3)
    path = evaluate.plot_comparison(
        aggregate_results(results),
        evaluate.count_termination_reasons(results),
        policy_names,
        tmp_path / "comparison.png",
    )

    assert path.is_file()
    assert path.stat().st_size > 0


def test_load_dqn_policy_reports_a_missing_checkpoint(tmp_path):
    with pytest.raises(FileNotFoundError, match="checkpoint not found"):
        evaluate.load_dqn_policy(tmp_path / "absent.pt", ENV_CONFIG)


def test_load_dqn_policy_rejects_a_checkpoint_shaped_for_another_environment(tmp_path):
    mismatched = DQNAgent(3, 2, AGENT_CONFIG)
    path = tmp_path / "mismatched.pt"
    mismatched.save_checkpoint(path)

    with pytest.raises(ValueError, match="does not match the evaluation environment"):
        evaluate.load_dqn_policy(path, ENV_CONFIG)


def test_dqn_policy_is_greedy_and_independent_of_global_rng(checkpoint_path):
    policy = evaluate.load_dqn_policy(checkpoint_path, ENV_CONFIG)
    env = BunkeringEnv(**ENV_CONFIG)
    observation, _ = env.reset(seed=1)

    import random

    random.seed(0)
    first = policy.select_action(env, observation, 0)
    random.seed(999)
    second = policy.select_action(env, observation, 0)

    assert first == second
    assert policy.name == evaluate.DQN_POLICY_NAME
    assert 0 <= first < env.action_space.n


def test_main_writes_every_official_artifact(tmp_path, checkpoint_path):
    exit_code = evaluate.main(
        [
            "--episodes",
            "3",
            "--seed",
            "42",
            "--checkpoint",
            str(checkpoint_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    results_path = tmp_path / "evaluation_results.csv"
    manifest_path = tmp_path / "evaluation_manifest.json"
    evaluation_dir = tmp_path / "evaluation"
    assert results_path.is_file()
    assert manifest_path.is_file()
    assert (evaluation_dir / "summary.csv").is_file()
    assert (evaluation_dir / "termination_reasons.csv").is_file()
    assert (evaluation_dir / "comparison.png").is_file()
    for policy in evaluate.RULE_BASED_POLICY_NAMES + (evaluate.DQN_POLICY_NAME,):
        assert (evaluation_dir / f"raw_{policy}.csv").is_file()

    with results_path.open(encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Four policies times three episodes, with CSV and manifest in exact agreement.
    assert len(rows) == 12
    assert len(manifest["cases"]) == 12
    assert {(int(r["seed"]), int(r["episode"]), r["policy"]) for r in rows} == {
        (c["seed"], c["episode"], c["policy"]) for c in manifest["cases"]
    }
    assert manifest["checkpoint"]["sha256"]
    assert manifest["checkpoint"]["archive"] == evaluate.CHECKPOINT_ARCHIVE
    assert manifest["env_config"] == manifest["cases"][0]["env_config"]


def test_main_reruns_reproduce_identical_records(tmp_path, checkpoint_path):
    def run(output_dir):
        evaluate.main(
            [
                "--episodes",
                "3",
                "--seed",
                "42",
                "--checkpoint",
                str(checkpoint_path),
                "--output-dir",
                str(output_dir),
            ]
        )
        return (output_dir / "evaluation_results.csv").read_text(encoding="utf-8")

    assert run(tmp_path / "first") == run(tmp_path / "second")


def test_checkpoint_archive_names_a_retrievable_location():
    # Checkpoints are .gitignore'd, so the archive block is the only thing that
    # keeps an official result set traceable to a file anyone else can fetch.
    archive = evaluate.CHECKPOINT_ARCHIVE

    assert archive["kind"] == "github_release_asset"
    assert archive["download_url"].startswith("https://")
    assert archive["release_tag"] in archive["download_url"]
    assert archive["asset_name"] in archive["download_url"]
    assert archive["status"] in {"pending_upload", "published"}


def test_committed_manifest_records_the_same_archive_location():
    manifest = json.loads(
        Path("results/evaluation_manifest.json").read_text(encoding="utf-8")
    )
    checkpoint = manifest["checkpoint"]

    assert checkpoint["archive"] == evaluate.CHECKPOINT_ARCHIVE
    assert checkpoint["archive"]["asset_name"] == checkpoint["path"]
    # A 64-hex digest is what makes a downloaded asset checkable against this run.
    assert len(checkpoint["sha256"]) == 64
    assert checkpoint["metadata"]["train_seed"] == manifest["base_seed"]


def test_committed_manifest_evaluates_one_training_seed_over_many_eval_seeds():
    # The published numbers come from a single trained model, so the manifest must
    # not be read as a multi-training-seed study.
    manifest = json.loads(
        Path("results/evaluation_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["checkpoint"]["metadata"]["train_seed"] == 42
    evaluation_seeds = {case["seed"] for case in manifest["cases"]}
    assert evaluation_seeds == set(range(42, 42 + manifest["n_episodes"]))
