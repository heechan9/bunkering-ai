import json
from pathlib import Path

import pytest

from evaluation.paper_audit import (
    CSV_FIELDS,
    PaperAuditReport,
    PaperClaim,
    audit_paper_claims,
    export_audit_csv,
    export_audit_json,
    get_git_commit_sha,
    read_upa_metrics,
    verify_canonical_evidence,
)
from scripts.audit_paper_evidence import main as audit_main


def make_claim(**overrides) -> PaperClaim:
    data = {
        "claim_id": "TEST-001",
        "paper_reference": "docs/test_ref.md",
        "metric_name": "test_metric",
        "expected_spec_value": "100",
        "actual_system_value": "100",
        "status": "passed",
        "notes": "unit test claim",
    }
    data.update(overrides)
    return PaperClaim(**data)


def test_paper_claim_validation():
    claim = make_claim()
    assert claim.claim_id == "TEST-001"
    assert claim.status == "passed"
    assert claim.to_row()["claim_id"] == "TEST-001"
    assert tuple(claim.to_row().keys()) == CSV_FIELDS


@pytest.mark.parametrize(
    ("overrides", "error_msg"),
    [
        ({"claim_id": ""}, "claim_id"),
        ({"paper_reference": ""}, "paper_reference"),
        ({"metric_name": ""}, "metric_name"),
        ({"status": "invalid_status"}, "status"),
    ],
)
def test_paper_claim_rejects_invalid_inputs(overrides, error_msg):
    with pytest.raises(ValueError, match=error_msg):
        make_claim(**overrides)


def test_audit_paper_claims_aggregation():
    claims = [
        make_claim(claim_id="C1", status="passed"),
        make_claim(claim_id="C2", status="failed"),
        make_claim(claim_id="C3", status="provisional"),
        make_claim(claim_id="C4", status="missing_evidence"),
    ]
    report = audit_paper_claims(claims)

    assert report.total_claims == 4
    assert report.passed_claims == 1
    assert report.failed_claims == 1
    assert report.provisional_claims == 1
    assert report.missing_evidence_claims == 1
    assert "source_commit_sha" in report.to_dict()["summary"]
    assert "generated_at_utc" in report.to_dict()["summary"]


def test_get_git_commit_sha_fallback(tmp_path):
    # Non-git directory returns "unavailable"
    assert get_git_commit_sha(tmp_path) == "unavailable"


def test_audit_paper_claims_rejects_empty_sequence():
    with pytest.raises(ValueError, match="empty"):
        audit_paper_claims([])


def test_verify_canonical_evidence_returns_passed_and_missing_claims_on_clean_repo():
    claims = verify_canonical_evidence()
    assert len(claims) >= 8
    claims_by_id = {c.claim_id: c for c in claims}
    assert claims_by_id["CLAIM-001"].status == "passed"
    assert claims_by_id["CLAIM-002"].status == "passed"
    assert claims_by_id["CLAIM-003"].status == "passed"
    assert claims_by_id["CLAIM-004"].status == "passed"
    assert claims_by_id["CLAIM-005"].status == "passed"
    assert claims_by_id["CLAIM-006"].status == "passed"
    assert claims_by_id["CLAIM-007"].status == "missing_evidence"  # Official evaluation results not present
    assert claims_by_id["CLAIM-008"].status == "passed"


def test_export_audit_artifacts(tmp_path):
    claims = verify_canonical_evidence()
    report = audit_paper_claims(claims)
    csv_file = tmp_path / "summary.csv"
    json_file = tmp_path / "report.json"

    export_audit_csv(report, csv_file)
    export_audit_json(report, json_file)

    assert csv_file.exists()
    assert json_file.exists()

    with json_file.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["summary"]["total_claims"] == len(claims)
    assert len(data["claims"]) == len(claims)
    assert "source_commit_sha" in data["summary"]
    assert "generated_at_utc" in data["summary"]


def test_audit_cli_main_missing_evidence_returns_exit_code_1(tmp_path):
    # On clean repo, CLAIM-007 (official evaluation results CSV) is missing_evidence -> exit code 1
    out_dir = tmp_path / "audit_output"
    exit_code = audit_main(["--output-dir", str(out_dir)])

    assert exit_code == 1
    assert (out_dir / "paper_evidence_summary.csv").exists()
    assert (out_dir / "paper_evidence_report.json").exists()


def test_audit_cli_main_clean_checkout_with_eval_csv_returns_exit_code_0(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    # Create valid evaluation results CSV and manifest
    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_json = repo_copy / "results/evaluation_manifest.json"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)

    header = "seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n"
    row = "42,0,fixed_fueling,-2.03,0.0,False,True,0,fuel_depleted\n"
    eval_csv.write_text(header + row, encoding="utf-8")

    manifest = {
        "policies": ["fixed_fueling"],
        "cases": [
            {
                "seed": 42,
                "episode": 0,
                "policy": "fixed_fueling",
                "env_config": {"n_ports": 3},
            }
        ],
    }
    eval_json.write_text(json.dumps(manifest), encoding="utf-8")

    out_dir = tmp_path / "audit_output"
    exit_code = audit_main(["--output-dir", str(out_dir), "--repo-root", str(repo_copy)])

    assert exit_code == 0


def test_audit_cli_tamper_upa_metrics_csv_fails(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    upa_csv = repo_copy / "results/public_data/upa_summary_metrics.csv"
    original_text = upa_csv.read_text(encoding="utf-8")
    # Tamper records from 6028 to 9999
    upa_csv.write_text(original_text.replace("6028.0", "9999.0"), encoding="utf-8")

    out_dir = tmp_path / "tamper_output"
    exit_code = audit_main(["--output-dir", str(out_dir), "--repo-root", str(repo_copy)])

    assert exit_code == 1

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c3 = next(c for c in claims if c.claim_id == "CLAIM-003")
    assert c3.status == "failed"
    assert c3.actual_system_value == "9999"


def test_audit_cli_tamper_safe_stock_status_fails(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    spec_file = repo_copy / "docs/technical/state_action_reward_spec.md"
    original_text = spec_file.read_text(encoding="utf-8")
    # Tamper Safe Stock provisional to final
    spec_file.write_text(original_text.replace("provisional", "final"), encoding="utf-8")

    out_dir = tmp_path / "tamper_output"
    exit_code = audit_main(["--output-dir", str(out_dir), "--repo-root", str(repo_copy)])

    assert exit_code == 1

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c5 = next(c for c in claims if c.claim_id == "CLAIM-005")
    assert c5.status == "failed"
    assert c5.actual_system_value == "final"


def test_audit_cli_ungrounded_dqn_superiority_claim_fails(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    doc_file = repo_copy / "docs/technical/dqn_design.md"
    # Insert ungrounded claim of DQN outperforming rule-based baseline
    doc_file.write_text("DQN이 Rule-based보다 우수하며 뛰어난 성능을 보인다.", encoding="utf-8")

    out_dir = tmp_path / "tamper_output"
    exit_code = audit_main(["--output-dir", str(out_dir), "--repo-root", str(repo_copy)])

    assert exit_code == 1

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c6 = next(c for c in claims if c.claim_id == "CLAIM-006")
    assert c6.status == "failed"


def test_audit_cli_invalid_evaluation_csv_row_schema_fails(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_json = repo_copy / "results/evaluation_manifest.json"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)

    header = "seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n"
    # Negative bunkering_count breaks EpisodeResult contract
    invalid_row = "42,0,fixed_fueling,-2.03,100.0,False,True,-5,fuel_depleted\n"
    eval_csv.write_text(header + invalid_row, encoding="utf-8")

    manifest = {"policies": ["fixed_fueling"], "cases": [{"seed": 42, "episode": 0, "policy": "fixed_fueling", "env_config": {}}]}
    eval_json.write_text(json.dumps(manifest), encoding="utf-8")

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c7 = next(c for c in claims if c.claim_id == "CLAIM-007")
    assert c7.status == "failed"
    assert "Contract validation failure" in c7.actual_system_value


@pytest.mark.parametrize("invalid_bool", ["invalid", "0", "1", "yes", "no"])
def test_audit_cli_invalid_boolean_string_fails(tmp_path, invalid_bool):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_json = repo_copy / "results/evaluation_manifest.json"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)

    header = "seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n"
    invalid_row = f"42,0,fixed_fueling,-2.03,100.0,{invalid_bool},True,0,fuel_depleted\n"
    eval_csv.write_text(header + invalid_row, encoding="utf-8")

    manifest = {"policies": ["fixed_fueling"], "cases": [{"seed": 42, "episode": 0, "policy": "fixed_fueling", "env_config": {}}]}
    eval_json.write_text(json.dumps(manifest), encoding="utf-8")

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c7 = next(c for c in claims if c.claim_id == "CLAIM-007")
    assert c7.status == "failed"
    assert "must be 'true' or 'false'" in c7.actual_system_value


def test_audit_cli_empty_evaluation_csv_fails(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_json = repo_copy / "results/evaluation_manifest.json"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)
    eval_csv.write_text("seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n", encoding="utf-8")

    manifest = {"policies": [], "cases": []}
    eval_json.write_text(json.dumps(manifest), encoding="utf-8")

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c7 = next(c for c in claims if c.claim_id == "CLAIM-007")
    assert c7.status == "failed"
    assert c7.actual_system_value == "empty_csv"


def test_audit_cli_evaluation_csv_present_but_manifest_missing_is_missing_evidence(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)
    header = "seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n"
    row = "42,0,fixed_fueling,-2.03,0.0,False,True,0,fuel_depleted\n"
    eval_csv.write_text(header + row, encoding="utf-8")

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c7 = next(c for c in claims if c.claim_id == "CLAIM-007")
    assert c7.status == "missing_evidence"
    assert c7.actual_system_value == "missing_manifest"


def test_audit_cli_evaluation_csv_and_manifest_case_mismatch_fails(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_json = repo_copy / "results/evaluation_manifest.json"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)

    header = "seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n"
    row = "42,0,fixed_fueling,-2.03,0.0,False,True,0,fuel_depleted\n"
    eval_csv.write_text(header + row, encoding="utf-8")

    # Manifest defines seed 999 instead of 42
    manifest = {
        "policies": ["fixed_fueling"],
        "cases": [
            {
                "seed": 999,
                "episode": 0,
                "policy": "fixed_fueling",
                "env_config": {"n_ports": 3},
            }
        ],
    }
    eval_json.write_text(json.dumps(manifest), encoding="utf-8")

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c7 = next(c for c in claims if c.claim_id == "CLAIM-007")
    assert c7.status == "failed"
    assert c7.actual_system_value == "csv_manifest_case_mismatch"
