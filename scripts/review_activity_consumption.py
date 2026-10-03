"""Describe consumption by documented activity; no ship-to-ship calibration."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

FIELDS = ['record_id', 'activity', 'duration_hours', 'consumption', 'unit', 'evidence']
ACTIVITIES = {'berthed', 'transit', 'operation', 'mixed', 'unknown'}


def number(value, positive=False):
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError('Invalid nonnegative consumption or positive duration')
    return result


def review(path: Path):
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if reader.fieldnames != FIELDS:
        raise ValueError(f'Expected columns: {FIELDS}')
    groups, seen, issues = {}, set(), []
    for line, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f'Malformed row {line}')
        row = {k: v.strip() for k, v in row.items()}
        identifier = row['record_id']
        if not identifier or identifier in seen:
            raise ValueError(f'Missing or duplicate record_id at row {line}')
        seen.add(identifier)
        if row['activity'] not in ACTIVITIES or row['unit'] not in {'t', 'kL'}:
            raise ValueError(f'Unsupported activity or unit at row {line}')
        if not row['evidence']:
            raise ValueError(f'Missing source evidence at row {line}')
        consumption = number(row['consumption']) if row['consumption'] else None
        hours = number(row['duration_hours'], positive=True) if row['duration_hours'] else None
        key = (row['activity'], row['unit'])
        group = groups.setdefault(key, {'activity': key[0], 'unit': key[1], 'records': 0,
            'known_consumption_total': 0., 'missing_consumption_records': 0,
            'rate_eligible_hours': 0., 'rate_eligible_consumption': 0., 'evidence': []})
        group['records'] += 1
        group['evidence'].append({'record_id': identifier, 'source': row['evidence'], 'csv_line': line})
        if consumption is None:
            group['missing_consumption_records'] += 1
            issues.append({'record_id': identifier, 'reason': 'missing_consumption'})
        else:
            group['known_consumption_total'] += consumption
        if hours is None:
            issues.append({'record_id': identifier, 'reason': 'unconfirmed_duration'})
        if key[0] in {'mixed', 'unknown'}:
            issues.append({'record_id': identifier, 'reason': 'activity_not_separable'})
        elif hours is not None and consumption is not None:
            group['rate_eligible_hours'] += hours
            group['rate_eligible_consumption'] += consumption
    if not seen:
        raise ValueError('No records')
    for group in groups.values():
        hours = group['rate_eligible_hours']
        group['consumption_per_hour'] = group['rate_eligible_consumption'] / hours if hours else None
    return {'source_sha256': hashlib.sha256(raw).hexdigest(),
            'scope': 'descriptive_only; rates use only documented single-activity paired consumption-duration records',
            'groups': list(groups.values()), 'issues': issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = review(args.csv)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
