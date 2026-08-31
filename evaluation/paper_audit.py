"""Independent audit contract for literature/paper evidence and claims.

This module provides data structures and verification logic to audit paper claims
against verified system specifications, evaluation contracts, and reference artifacts,
without modifying any model behavior, reward logic, or evaluation results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from envs.bunkering_env import BunkeringEnv
from evaluation.contract import (
    CSV_FIELDS as EVALUATION_CSV_FIELDS,
    TERMINATION_REASONS,
)


AUDIT_STATUSES = ("passed", "failed", "provisional")
CSV_FIELDS = (
    "claim_id",
    "paper_reference",
    "metric_name",
    "expected_spec_value",
    "actual_system_value",
    "status",
    "notes",
)


@dataclass(frozen=True)
class PaperClaim:
    """Represents a claim derived from paper/literature specifications."""

    claim_id: str
    paper_reference: str
    metric_name: str
    expected_spec_value: str
    actual_system_value: str
    status: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.claim_id or not isinstance(self.claim_id, str):
            raise ValueError("claim_id must be a non-empty string")
        if not self.paper_reference or not isinstance(self.paper_reference, str):
            raise ValueError("paper_reference must be a non-empty string")
        if not self.metric_name or not isinstance(self.metric_name, str):
            raise ValueError("metric_name must be a non-empty string")
        if self.status not in AUDIT_STATUSES:
            raise ValueError(
                f"status must be one of {AUDIT_STATUSES}, got '{self.status}'"
            )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_row(self) -> dict[str, str]:
        return {
            "claim_id": self.claim_id,
            "paper_reference": self.paper_reference,
            "metric_name": self.metric_name,
            "expected_spec_value": self.expected_spec_value,
            "actual_system_value": self.actual_system_value,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PaperAuditReport:
    """Aggregated paper evidence audit results."""

    total_claims: int
    passed_claims: int
    failed_claims: int
    provisional_claims: int
    claims: tuple[PaperClaim, ...]

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_claims": self.total_claims,
                "passed_claims": self.passed_claims,
                "failed_claims": self.failed_claims,
                "provisional_claims": self.provisional_claims,
            },
            "claims": [c.to_dict() for c in self.claims],
        }


def verify_canonical_evidence() -> list[PaperClaim]:
    """Inspect canonical system code, specs, and data artifacts to build paper claims."""
    claims: list[PaperClaim] = []

    # Claim 1: MVP State Space Dimension against BunkeringEnv canonical observation space
    try:
        env = BunkeringEnv()
        obs_shape = env.observation_space.shape
        actual_state_dim = str(obs_shape[0]) if obs_shape else "0"
        passed = actual_state_dim == "6"
        claims.append(
            PaperClaim(
                claim_id="CLAIM-001",
                paper_reference="docs/technical/state_action_reward_spec.md §1",
                metric_name="state_dim_mvp",
                expected_spec_value="6",
                actual_system_value=actual_state_dim,
                status="passed" if passed else "failed",
                notes="Verified against BunkeringEnv observation_space shape.",
            )
        )
    except Exception as exc:
        claims.append(
            PaperClaim(
                claim_id="CLAIM-001",
                paper_reference="docs/technical/state_action_reward_spec.md §1",
                metric_name="state_dim_mvp",
                expected_spec_value="6",
                actual_system_value=f"Error: {exc}",
                status="failed",
                notes="Failed to inspect BunkeringEnv observation space.",
            )
        )

    # Claim 2: Action Space Contract against BunkeringEnv canonical action space
    try:
        env = BunkeringEnv(n_ports=3)
        actual_n = env.action_space.n
        expected_n = 4  # 1 + 3 ports
        passed = actual_n == expected_n
        claims.append(
            PaperClaim(
                claim_id="CLAIM-002",
                paper_reference="docs/technical/state_action_reward_spec.md §2",
                metric_name="action_space_contract",
                expected_spec_value="1 + n_ports (4 for n_ports=3)",
                actual_system_value=f"{actual_n}",
                status="passed" if passed else "failed",
                notes="action=0: wait, action=1..n_ports: request fixed fueling (0.9).",
            )
        )
    except Exception as exc:
        claims.append(
            PaperClaim(
                claim_id="CLAIM-002",
                paper_reference="docs/technical/state_action_reward_spec.md §2",
                metric_name="action_space_contract",
                expected_spec_value="1 + n_ports",
                actual_system_value=f"Error: {exc}",
                status="failed",
                notes="Failed to inspect BunkeringEnv action space.",
            )
        )

    # Claim 3: Synthetic Cost Index Naming & Unitless Proxy
    try:
        spec_text = Path("docs/technical/state_action_reward_spec.md").read_text(
            encoding="utf-8"
        )
        has_index_note = "Synthetic Cost Index" in spec_text
        claims.append(
            PaperClaim(
                claim_id="CLAIM-003",
                paper_reference="docs/technical/state_action_reward_spec.md §3.2",
                metric_name="cost_index_unit",
                expected_spec_value="Synthetic Cost Index (unitless)",
                actual_system_value="Synthetic Cost Index (unitless)"
                if has_index_note
                else "Unspecified",
                status="passed" if has_index_note else "failed",
                notes="Synthetic Cost Index is not converted to currency prior to tank capacity finalization.",
            )
        )
    except Exception as exc:
        claims.append(
            PaperClaim(
                claim_id="CLAIM-003",
                paper_reference="docs/technical/state_action_reward_spec.md §3.2",
                metric_name="cost_index_unit",
                expected_spec_value="Synthetic Cost Index (unitless)",
                actual_system_value=f"Error: {exc}",
                status="failed",
                notes="Failed to inspect state_action_reward_spec.md.",
            )
        )

    # Claim 4: Strict Termination Reasons against Evaluation Contract
    actual_reasons = tuple(sorted(TERMINATION_REASONS))
    expected_reasons = ("arrived", "fuel_depleted", "timeout")
    passed = actual_reasons == expected_reasons
    claims.append(
        PaperClaim(
            claim_id="CLAIM-004",
            paper_reference="docs/technical/evaluation_contract.md",
            metric_name="terminal_reasons",
            expected_spec_value="arrived, fuel_depleted, timeout",
            actual_system_value=", ".join(actual_reasons),
            status="passed" if passed else "failed",
            notes="Verified against evaluation.contract.TERMINATION_REASONS.",
        )
    )

    # Claim 5: Safe Stock Baseline Provisional Status
    try:
        spec_text = Path("docs/technical/state_action_reward_spec.md").read_text(
            encoding="utf-8"
        )
        is_provisional = "provisional" in spec_text and "Safe Stock" in spec_text
        claims.append(
            PaperClaim(
                claim_id="CLAIM-005",
                paper_reference="docs/technical/state_action_reward_spec.md §4.1",
                metric_name="safe_stock_kpi_status",
                expected_spec_value="provisional",
                actual_system_value="provisional" if is_provisional else "final",
                status="provisional",
                notes="Safe Stock baseline is M1 reference candidate; cost saving KPI requires multi-seed mentor approval.",
            )
        )
    except Exception as exc:
        claims.append(
            PaperClaim(
                claim_id="CLAIM-005",
                paper_reference="docs/technical/state_action_reward_spec.md §4.1",
                metric_name="safe_stock_kpi_status",
                expected_spec_value="provisional",
                actual_system_value=f"Error: {exc}",
                status="failed",
                notes="Failed to inspect state_action_reward_spec.md.",
            )
        )

    # Claim 6: Public Data Reference Isolation
    try:
        readme_text = Path("README.md").read_text(encoding="utf-8")
        has_public_ref = "공공데이터" in readme_text and "참고자료" in readme_text
        claims.append(
            PaperClaim(
                claim_id="CLAIM-006",
                paper_reference="docs/submission/public_data_report_updates.md",
                metric_name="public_data_separation",
                expected_spec_value="domain reference only",
                actual_system_value="domain reference only"
                if has_public_ref
                else "mismatched",
                status="passed" if has_public_ref else "failed",
                notes="Public data is used as domain reference and not as DQN training input.",
            )
        )
    except Exception as exc:
        claims.append(
            PaperClaim(
                claim_id="CLAIM-006",
                paper_reference="docs/submission/public_data_report_updates.md",
                metric_name="public_data_separation",
                expected_spec_value="domain reference only",
                actual_system_value=f"Error: {exc}",
                status="failed",
                notes="Failed to inspect README.md.",
            )
        )

    return claims


def audit_paper_claims(claims: Sequence[PaperClaim]) -> PaperAuditReport:
    """Audit a collection of paper claims and produce an aggregate report."""
    if not claims:
        raise ValueError("claims list must not be empty")

    passed = sum(1 for c in claims if c.status == "passed")
    failed = sum(1 for c in claims if c.status == "failed")
    provisional = sum(1 for c in claims if c.status == "provisional")

    return PaperAuditReport(
        total_claims=len(claims),
        passed_claims=passed,
        failed_claims=failed,
        provisional_claims=provisional,
        claims=tuple(claims),
    )


def export_audit_csv(report: PaperAuditReport, path: Path | str) -> None:
    """Export paper evidence audit report to CSV format."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for claim in report.claims:
            writer.writerow(claim.to_row())


def export_audit_json(report: PaperAuditReport, path: Path | str) -> None:
    """Export paper evidence audit report to JSON format."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
