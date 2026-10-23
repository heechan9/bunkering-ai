"""Read-only source audit; create a new report directory (never overwrite)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.matched_safety import BOOL_FIELDS, COUNT_FIELDS, NUM_FIELDS, matched_safety_report


REQUIRED_COLUMNS = frozenset(('seed', 'episode', 'policy', 'safe_arrival_adjusted_sci',
                              *BOOL_FIELDS, *COUNT_FIELDS, *NUM_FIELDS))


def read_safety_csv(path: Path) -> list[dict[str, str]]:
    """Reject ambiguous headers and malformed records before interpreting values."""
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.reader(handle, strict=True)
        try:
            header = next(reader, None)
            if not header:
                raise ValueError('CSV header is missing')
            if len(header) != len(set(header)):
                raise ValueError('CSV header contains duplicate column names')
            if set(header) != REQUIRED_COLUMNS:
                raise ValueError('CSV header must contain exactly the safety-audit columns')
            rows = []
            for cells in reader:
                if len(cells) != len(header):
                    raise ValueError(f'CSV record at line {reader.line_num} has {len(cells)} cells; expected {len(header)}')
                rows.append(dict(zip(header, cells)))
        except csv.Error as exc:
            raise ValueError(f'Malformed CSV at line {reader.line_num}: {exc}') from exc
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.episodes, args.manifest)}
    rows = read_safety_csv(args.episodes)
    report = matched_safety_report(rows, json.loads(args.manifest.read_text()))
    report['input_sha256'] = inputs
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / 'matched_safety.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'comparisons'}, indent=2))
    for c in report['comparisons']:
        print(json.dumps({k:v for k,v in c.items() if k != 'pairs'}))

if __name__ == '__main__':
    main()
