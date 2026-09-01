import json
from pathlib import Path

import pytest

from evaluation.paper_audit import (
    CSV_FIELDS,
    PaperAuditReport,
    PaperClaim,
    asserts_dqn_superiority,
    audit_paper_claims,
    export_audit_csv,
    export_audit_json,
    official_evaluation_state,
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


def test_verify_canonical_evidence_passes_on_repo_with_official_results():
    claims = verify_canonical_evidence()
    assert len(claims) >= 8
    claims_by_id = {c.claim_id: c for c in claims}
    for claim_id in (
        "CLAIM-001",
        "CLAIM-002",
        "CLAIM-003",
        "CLAIM-004",
        "CLAIM-005",
        "CLAIM-006",
        "CLAIM-008",
    ):
        assert claims_by_id[claim_id].status == "passed"
    # CLAIM-007 flipped from missing_evidence once results/evaluation_results.csv
    # and results/evaluation_manifest.json were produced by scripts/evaluate.py.
    assert claims_by_id["CLAIM-007"].status == "passed"


def _repo_copy_without_official_results(tmp_path: Path) -> Path:
    """Copy the repository and strip the official evaluation artifacts.

    Tests of the missing-evidence boundary must build that state themselves
    rather than relying on the working tree not having run an evaluation yet.
    """
    import shutil

    repo_copy = tmp_path / "repo_without_results"
    shutil.copytree(
        ".",
        repo_copy,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"),
    )
    (repo_copy / "results/evaluation_results.csv").unlink(missing_ok=True)
    (repo_copy / "results/evaluation_manifest.json").unlink(missing_ok=True)
    return repo_copy


def test_audit_cli_main_returns_exit_code_0_with_official_results(tmp_path):
    # The committed evaluation CSV and manifest satisfy CLAIM-007 -> exit code 0.
    out_dir = tmp_path / "audit_output"
    exit_code = audit_main(["--output-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "paper_evidence_summary.csv").exists()
    assert (out_dir / "paper_evidence_report.json").exists()


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


def test_audit_cli_main_missing_evidence_returns_exit_code_1(tmp_path):
    # Without the official evaluation artifacts, CLAIM-007 is missing_evidence -> exit code 1.
    out_dir = tmp_path / "audit_output"
    exit_code = audit_main(
        [
            "--output-dir",
            str(out_dir),
            "--repo-root",
            str(_repo_copy_without_official_results(tmp_path)),
        ]
    )

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
    # Both sides of the official comparison must be present: CLAIM-006 reads the
    # artifacts as evidence that the DQN-vs-rule-based comparison actually ran.
    rows = (
        "42,0,fixed_fueling,-2.03,0.0,False,True,0,fuel_depleted\n"
        "42,0,double_dqn,0.04,100.0,True,False,5,arrived\n"
    )
    eval_csv.write_text(header + rows, encoding="utf-8")

    manifest = {
        "policies": ["fixed_fueling", "double_dqn"],
        "cases": [
            {
                "seed": 42,
                "episode": 0,
                "policy": policy,
                "env_config": {"n_ports": 3},
            }
            for policy in ("fixed_fueling", "double_dqn")
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
    # Drop the committed manifest so only the CSV side of the pair is present.
    (repo_copy / "results/evaluation_manifest.json").unlink(missing_ok=True)
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


# --- CLAIM-006: comparison boundary judged from the official evaluation artifacts ---
#
# The rule used to key off a single README sentence, so deleting that sentence
# failed the audit even though the evaluation had been run. It now reads the
# canonical CSV and manifest and only then checks that README agrees with them.


PENDING_README = (
    "# bunkering-ai\n\n"
    "Rule-based와 DQN의 공식 동일조건 성능비교는 아직 수행하지 않았습니다.\n"
)


def _repo_copy(tmp_path: Path, name: str = "repo") -> Path:
    import shutil

    repo_copy = tmp_path / name
    shutil.copytree(
        ".",
        repo_copy,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "runs"),
    )
    return repo_copy


def _claim(repo_root: Path, claim_id: str = "CLAIM-006") -> PaperClaim:
    return next(
        c for c in verify_canonical_evidence(repo_root=repo_root) if c.claim_id == claim_id
    )


def test_official_evaluation_state_reads_the_committed_artifacts():
    state, detail = official_evaluation_state(".")

    assert state == "present"
    assert "double_dqn" in detail


def test_claim006_passes_after_the_official_evaluation():
    claim = _claim(Path("."))

    assert claim.status == "passed"
    assert claim.actual_system_value == "comparison_performed_and_declared"


def test_readme_no_longer_declares_the_comparison_as_pending():
    # The statement PR #13 made obsolete must be gone, and its removal must not
    # depend on the audit still looking for it.
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "공식 동일조건 성능비교는 아직 수행하지 않았습니다" not in readme


def test_claim006_fails_when_readme_claims_a_comparison_without_artifacts(tmp_path):
    # Pre-evaluation state with a post-evaluation README: the claim has no evidence.
    repo_copy = _repo_copy_without_official_results(tmp_path)

    claim = _claim(repo_copy)

    assert claim.status == "failed"
    assert claim.actual_system_value == "comparison_claimed_without_artifacts"


def test_claim006_passes_in_the_pre_evaluation_state_with_a_pending_statement(tmp_path):
    # The historical valid state: no artifacts, and README says so.
    repo_copy = _repo_copy_without_official_results(tmp_path)
    (repo_copy / "README.md").write_text(PENDING_README, encoding="utf-8")

    claim = _claim(repo_copy)

    assert claim.status == "passed"
    assert claim.actual_system_value == "comparison_pending_and_declared"


def test_claim006_fails_when_the_pre_evaluation_state_declares_nothing(tmp_path):
    repo_copy = _repo_copy_without_official_results(tmp_path)
    (repo_copy / "README.md").write_text("# bunkering-ai\n", encoding="utf-8")

    claim = _claim(repo_copy)

    assert claim.status == "failed"
    assert claim.actual_system_value == "missing_status_statement"


def test_claim006_fails_when_a_stale_pending_statement_survives_the_evaluation(tmp_path):
    # The exact regression this rewrite exists to catch, in the other direction.
    repo_copy = _repo_copy(tmp_path)
    readme = repo_copy / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + "\n공식 동일조건 성능비교는 아직 수행하지 않았습니다.\n",
        encoding="utf-8",
    )

    claim = _claim(repo_copy)

    assert claim.status == "failed"
    assert claim.actual_system_value == "stale_pending_statement"


def test_claim006_reports_missing_evidence_when_csv_and_manifest_disagree(tmp_path):
    repo_copy = _repo_copy(tmp_path)
    manifest_path = repo_copy / "results/evaluation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"] = manifest["cases"][:-1]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    claim = _claim(repo_copy)

    assert claim.status == "missing_evidence"
    assert claim.actual_system_value == "inconsistent_evaluation_artifacts"


def test_claim006_treats_artifacts_without_dqn_records_as_no_comparison(tmp_path):
    repo_copy = _repo_copy(tmp_path)
    header = ",".join(
        [
            "seed",
            "episode",
            "policy",
            "reward",
            "Synthetic Cost Index",
            "success",
            "fuel_depletion",
            "bunkering_count",
            "termination_reason",
        ]
    )
    (repo_copy / "results/evaluation_results.csv").write_text(
        f"{header}\n42,0,safe_stock,-0.49,545392.7,true,false,1,arrived\n",
        encoding="utf-8",
    )
    (repo_copy / "results/evaluation_manifest.json").write_text(
        json.dumps(
            {
                "policies": ["safe_stock"],
                "cases": [
                    {
                        "seed": 42,
                        "episode": 0,
                        "policy": "safe_stock",
                        "env_config": {"n_ports": 3},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    claim = _claim(repo_copy)

    assert claim.status == "failed"
    assert claim.actual_system_value == "comparison_claimed_without_artifacts"


@pytest.mark.parametrize(
    ("text", "asserted"),
    [
        ("DQN이 Rule-based보다 우수하며 뛰어난 성능을 보인다.", True),
        ("DQN이 베이스라인보다 우수하다.", True),
        ("실험에서 DQN 우수성이 확인됐다.", True),
        # Naming the claim in order to rule it out is not the claim itself.
        ("| 강화학습 구현 | DQN이 Rule-based보다 우수하다는 주장 |", False),
        ("DQN 우수성을 주장하지 않는다.", False),
        ("DQN이 Rule-based보다 우수하다는 서술은 하지 않는다.", False),
    ],
)
def test_superiority_detector_separates_assertions_from_disclaimers(text, asserted):
    assert asserts_dqn_superiority(text) is asserted


def test_claim006_fails_on_an_asserted_superiority_claim_even_with_artifacts(tmp_path):
    repo_copy = _repo_copy(tmp_path)
    (repo_copy / "docs/technical/dqn_design.md").write_text(
        "DQN이 Rule-based보다 우수하며 뛰어난 성능을 보인다.", encoding="utf-8"
    )

    claim = _claim(repo_copy)

    assert claim.status == "failed"
    assert claim.actual_system_value == "ungrounded_superiority_claim"
    assert "docs/technical/dqn_design.md" in claim.notes


def test_claim006_ignores_the_role_alignment_disclaimer_row():
    # docs/ROLE_ALIGNMENT.md lists "DQN이 Rule-based보다 우수하다는 주장" under the
    # "주장하지 않을 내용" column; the audit must not read that as the claim.
    role_doc = Path("docs/ROLE_ALIGNMENT.md")
    if not role_doc.is_file():
        pytest.skip("docs/ROLE_ALIGNMENT.md is not present in this checkout")

    assert "우수하다는 주장" in role_doc.read_text(encoding="utf-8")
    assert _claim(Path(".")).status == "passed"


def test_claim004_reports_termination_reasons_in_a_stable_order():
    # TERMINATION_REASONS is a frozenset, so an unsorted report would rewrite the
    # committed audit artifact on every run under a new PYTHONHASHSEED.
    claim = _claim(Path("."), "CLAIM-004")

    assert claim.actual_system_value == "arrived, fuel_depleted, timeout"
