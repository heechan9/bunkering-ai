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


def test_audit_paper_claims_rejects_empty_sequence():
    with pytest.raises(ValueError, match="empty"):
        audit_paper_claims([])


def test_verify_canonical_evidence_returns_passed_claims_on_clean_repo():
    claims = verify_canonical_evidence()
    assert len(claims) >= 8
    passed_ids = [c.claim_id for c in claims if c.status == "passed"]
    assert "CLAIM-001" in passed_ids  # State dim
    assert "CLAIM-002" in passed_ids  # Action space
    assert "CLAIM-003" in passed_ids  # UPA public data count
    assert "CLAIM-004" in passed_ids  # Termination reasons
    assert "CLAIM-005" in passed_ids  # Safe stock status
    assert "CLAIM-006" in passed_ids  # DQN boundary
    assert "CLAIM-008" in passed_ids  # Public data isolation


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


def test_audit_cli_main_clean_checkout(tmp_path):
    out_dir = tmp_path / "audit_output"
    exit_code = audit_main(["--output-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "paper_evidence_summary.csv").exists()
    assert (out_dir / "paper_evidence_report.json").exists()


def test_audit_cli_tamper_upa_metrics_csv_fails(tmp_path):
    # Copy repo files into temp repo directory to tamper with UPA metrics CSV
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

    # Verify claim 3 status is failed
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


def test_audit_cli_with_valid_official_evaluation_results(tmp_path):
    import shutil
    repo_copy = tmp_path / "repo"
    shutil.copytree(".", repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"))

    # Add valid official evaluation results CSV
    eval_csv = repo_copy / "results/evaluation_results.csv"
    eval_csv.parent.mkdir(parents=True, exist_ok=True)
    header = "seed,episode,policy,reward,Synthetic Cost Index,success,fuel_depletion,bunkering_count,termination_reason\n"
    row = "42,0,fixed_fueling,-2.03,0.0,False,True,0,fuel_depleted\n"
    eval_csv.write_text(header + row, encoding="utf-8")

    claims = verify_canonical_evidence(repo_root=repo_copy)
    c7 = next(c for c in claims if c.claim_id == "CLAIM-007")
    assert c7.status == "passed"
    assert "present" in c7.actual_system_value
