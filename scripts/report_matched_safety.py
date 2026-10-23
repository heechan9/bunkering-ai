"""Read-only source audit; create a new report directory (never overwrite)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.matched_safety import matched_safety_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.episodes, args.manifest)}
    with args.episodes.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    report = matched_safety_report(rows, json.loads(args.manifest.read_text()))
    report['input_sha256'] = inputs
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / 'matched_safety.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'comparisons'}, indent=2))
    for c in report['comparisons']:
        print(json.dumps({k:v for k,v in c.items() if k != 'pairs'}))

if __name__ == '__main__':
    main()
