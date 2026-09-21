"""Read-only check of the committed Ocean Lab snapshot against research evidence.

Does not execute models, certify rendered UI, or validate real-world performance.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = Path('web/ocean-lab/public/data')
RESEARCH = Path('results/diagnostics/review_4seed')


def audit(root=ROOT):
    root = Path(root)
    raw = (root / WEB / 'replay.json').read_bytes()
    replay = json.loads(raw)
    report = json.loads((root / WEB / 'integration-review.json').read_text())
    if hashlib.sha256(raw).hexdigest() != report['replay_sha256']:
        raise ValueError('Replay hash differs from reviewed snapshot')
    with (root / RESEARCH / 'policy_accounting_comparison.csv').open(newline='') as f:
        reader = csv.DictReader(f)
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError('Duplicate CSV columns')
        expected = list(reader)
    fields = set(expected[0])
    def keyed(rows):
        result = {}
        for row in rows:
            if set(row) != fields:
                raise ValueError('Summary columns differ')
            key = (row['checkpoint'], row['policy'])
            if key in result:
                raise ValueError('Duplicate summary key')
            result[key] = row
        return result
    left, right = keyed(expected), keyed(replay['summary'])
    if left.keys() != right.keys():
        raise ValueError('Summary policy/checkpoint set differs')
    checked = 0
    for key, row in left.items():
        for field in fields - {'checkpoint', 'policy'}:
            a, b = float(row[field]), float(right[key][field])
            if not math.isfinite(a) or not math.isfinite(b) or a != b:
                raise ValueError(f'Summary differs: {key}/{field}')
            checked += 1
    provenance = json.loads((root / RESEARCH / 'provenance.json').read_text())
    hashes = {s['checkpoint']['name']: s['checkpoint']['sha256'] for s in provenance['sources']}
    if replay['checkpointHashes'] != hashes:
        raise ValueError('Checkpoint identity differs')
    cases = [str(i) for i in range(42, 142)]
    runs = replay['runs']
    expected_runs = {'dqn_42', 'dqn_1042', 'dqn_2042', 'dqn_3042',
                     'safe_stock', 'fixed_fueling', 'price_reactive'}
    if set(runs) != expected_runs:
        raise ValueError('Replay policy/checkpoint coverage differs')
    transitions = 0
    for name, run in runs.items():
        if set(run) != set(cases):
            raise ValueError(f'Case coverage differs: {name}')
        for case, trace in run.items():
            if not 1 <= len(trace) <= 30:
                raise ValueError(f'Invalid trace length: {name}/{case}')
            previous = 1.0
            for row in trace:
                if len(row) != 11 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in row):
                    raise ValueError('Invalid transition values')
                fuel, buy, consume, sci, reward, violation, price, fx, pr, sr, op = row
                close = lambda a, b: math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
                if not close(previous + buy - consume, fuel):
                    raise ValueError('Fuel balance differs')
                if not close(buy * price * fx, sci) or not close(pr + sr + op, reward):
                    raise ValueError('Transition accounting differs')
                if violation != int(fuel < 0.15):
                    raise ValueError('Raw safety flag differs')
                previous = fuel
                transitions += 1
    if transitions != report['transitions_verified']:
        raise ValueError('Transition count differs from reviewed snapshot')
    return {'summary_values_checked': checked, 'policy_case_combinations': 700,
            'transitions_checked': transitions, 'model_execution': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.root), indent=2))
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        raise SystemExit(f'FAIL: {exc}') from exc


if __name__ == '__main__':
    main()
