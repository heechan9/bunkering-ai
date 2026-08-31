"""Shared contracts for policy-independent evaluation and paper evidence audit."""

from evaluation.contract import (
    CSV_FIELDS as EVALUATION_CSV_FIELDS,
    TERMINATION_REASONS,
    AggregateResult,
    EpisodeResult,
    EvaluationCase,
    aggregate_results,
    validate_fair_evaluation_plan,
)
from evaluation.paper_audit import (
    AUDIT_STATUSES,
    CSV_FIELDS as AUDIT_CSV_FIELDS,
    PaperAuditReport,
    PaperClaim,
    audit_paper_claims,
    export_audit_csv,
    export_audit_json,
    read_upa_metrics,
    verify_canonical_evidence,
)

# Preserve backward compatibility for evaluation contract CSV_FIELDS
CSV_FIELDS = EVALUATION_CSV_FIELDS

__all__ = [
    "CSV_FIELDS",
    "EVALUATION_CSV_FIELDS",
    "AUDIT_CSV_FIELDS",
    "TERMINATION_REASONS",
    "AUDIT_STATUSES",
    "AggregateResult",
    "EpisodeResult",
    "EvaluationCase",
    "PaperClaim",
    "PaperAuditReport",
    "aggregate_results",
    "validate_fair_evaluation_plan",
    "audit_paper_claims",
    "export_audit_csv",
    "export_audit_json",
    "read_upa_metrics",
    "verify_canonical_evidence",
]
