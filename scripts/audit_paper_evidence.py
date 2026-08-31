#!/usr/bin/env python3
"""CLI script to run independent paper-evidence audit."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from evaluation.paper_audit import (
    audit_paper_claims,
    export_audit_csv,
    export_audit_json,
    verify_canonical_evidence,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run independent paper-evidence audit for claims and specifications."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/paper_audit"),
        help="Directory where audit CSV and JSON reports will be saved.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root directory.",
    )
    return parser


def main(args: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(args)

    output_dir: Path = options.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    claims = verify_canonical_evidence(repo_root=options.repo_root)
    report = audit_paper_claims(claims)

    csv_path = output_dir / "paper_evidence_summary.csv"
    json_path = output_dir / "paper_evidence_report.json"

    export_audit_csv(report, csv_path)
    export_audit_json(report, json_path)

    print(f"Paper Evidence Audit complete:")
    print(f"  Total claims: {report.total_claims}")
    print(f"  Passed: {report.passed_claims}")
    print(f"  Provisional: {report.provisional_claims}")
    print(f"  Missing evidence: {report.missing_evidence_claims}")
    print(f"  Failed: {report.failed_claims}")
    print(f"  CSV summary saved to: {csv_path}")
    print(f"  JSON report saved to: {json_path}")

    if report.failed_claims > 0 or report.missing_evidence_claims > 0:
        reasons = []
        if report.failed_claims > 0:
            reasons.append(f"{report.failed_claims} claim(s) failed verification")
        if report.missing_evidence_claims > 0:
            reasons.append(f"{report.missing_evidence_claims} required claim(s) missing evidence")
        print(f"AUDIT FAILURE: {', '.join(reasons)}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
