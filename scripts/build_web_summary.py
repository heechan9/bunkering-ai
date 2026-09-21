"""Generate web comparison summary from reviewed CSV, without replaying models."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from scripts.audit_web_evidence import audit, ROOT, RESEARCH

OUTPUT = Path('web/ocean-lab/public/data/research-summary.json')


def build(root=ROOT):
    # Refuse changed evidence until its full review/reconciliation is complete.
    audit(root)
    source = root / RESEARCH / 'policy_accounting_comparison.csv'
    with source.open(newline='') as f:
        summary = list(csv.DictReader(f))
    return {'schema': 'research-summary/v1', 'source': source.relative_to(root).as_posix(),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'summary': summary}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    expected = build()
    target = ROOT / OUTPUT
    if args.check:
        if json.loads(target.read_text()) != expected:
            raise SystemExit('FAIL: web summary differs; regenerate after evidence review')
        print('PASS: generated web summary matches reviewed CSV')
    else:
        target.write_text(json.dumps(expected, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
