#!/usr/bin/env python3
"""CLI script to run independent paper-evidence audit."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from evaluation.paper_audit import (
    PaperClaim,
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
    return parser


def main(args: list[str] | None = None) -> int:
    parser = build_parser()
    options = parser.parse_args(args)

    output_dir: Path = options.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    claims = verify_canonical_evidence()
    report = audit_paper_claims(claims)

    csv_path = output_dir / "paper_evidence_summary.csv"
    json_path = output_dir / "paper_evidence_report.json"

    export_audit_csv(report, csv_path)
    export_audit_json(report, json_path)

    print(f"Paper Evidence Audit complete:")
    print(f"  Total claims: {report.total_claims}")
    print(f"  Passed: {report.passed_claims}")
    print(f"  Provisional: {report.provisional_claims}")
    print(f"  Failed: {report.failed_claims}")
    print(f"  CSV summary saved to: {csv_path}")
    print(f"  JSON report saved to: {json_path}")

    if report.failed_claims > 0:
        print(f"AUDIT FAILURE: {report.failed_claims} claim(s) failed verification.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
