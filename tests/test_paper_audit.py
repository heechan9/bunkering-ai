import json

import pytest

from evaluation.paper_audit import (
    CSV_FIELDS,
    PaperAuditReport,
    PaperClaim,
    audit_paper_claims,
    export_audit_csv,
    export_audit_json,
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
    ]
    report = audit_paper_claims(claims)

    assert report.total_claims == 3
    assert report.passed_claims == 1
    assert report.failed_claims == 1
    assert report.provisional_claims == 1


def test_audit_paper_claims_rejects_empty_sequence():
    with pytest.raises(ValueError, match="empty"):
        audit_paper_claims([])


def test_verify_canonical_evidence_returns_passed_and_provisional_claims():
    claims = verify_canonical_evidence()
    assert len(claims) >= 6
    assert all(c.status in ("passed", "provisional") for c in claims)


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


def test_audit_cli_main_success(tmp_path):
    out_dir = tmp_path / "audit_output"
    exit_code = audit_main(["--output-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "paper_evidence_summary.csv").exists()
    assert (out_dir / "paper_evidence_report.json").exists()


def test_audit_cli_main_fails_on_mismatched_claim(monkeypatch, tmp_path):
    failing_claim = make_claim(status="failed")
    monkeypatch.setattr(
        "scripts.audit_paper_evidence.verify_canonical_evidence",
        lambda: [failing_claim],
    )
    out_dir = tmp_path / "audit_failure_output"
    exit_code = audit_main(["--output-dir", str(out_dir)])

    assert exit_code == 1
