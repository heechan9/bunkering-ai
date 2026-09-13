"""Read-only, baseline-only independent check of the four-checkpoint diagnostic snapshot.

This does not rerun a model or change official reward/safety accounting. A tolerance
classification is reported separately from the original strict safety flag.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

RULES = {'fixed_fueling', 'price_reactive', 'safe_stock'}
POLICIES = RULES | {'double_dqn'}
COMPONENTS = ('price_advantage_reward', 'safety_reward', 'operational_reward', 'imo_reward')


def require_close(actual, expected, name):
    if not math.isclose(actual, expected, abs_tol=1e-10, rel_tol=1e-12):
        raise ValueError(f'{name}: {actual} != {expected}')


def inspect_steps(rows):
    """Validate one episode using the fixed V1 baseline transition and reward formulas."""
    if not rows:
        raise ValueError('empty episode')
    previous = 1.0
    max_residual = 0.0
    for index, row in enumerate(rows):
        values = {k: float(v) for k, v in row.items() if k != 'policy'}
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError('non-finite step')
        r = values
        if r['step'] != index or r['action'] not in (0, 1, 2, 3):
            raise ValueError('step/action mismatch')
        require_close(r['fuel_before'], previous, 'fuel continuity')
        consumed = min(previous, 0.05)
        after_consumption = max(previous - 0.05, 0.0)
        amount = min(0.9, max(0.95 - after_consumption, 0.0)) if r['action'] else 0.0
        loss = max(after_consumption + amount - 0.95, 0.0)
        final = after_consumption + amount - loss
        for name, expected in [('realized_consumption', consumed), ('bunker_amount', amount),
                               ('clipping_loss', loss), ('fuel_after', final)]:
            require_close(r[name], expected, name)
        if r['bunker_event'] != int(amount > 1e-6):
            raise ValueError('bunker event mismatch')
        strict = int(r['fuel_after'] < 0.15)
        if r['safety_violation'] != strict:
            raise ValueError('strict safety flag mismatch')
        require_close(r['safety_reward'], -0.5 * strict, 'safety reward')
        price_reward = max((r['decision_ma'] - r['decision_price']) / r['decision_ma'], 0) if amount > 1e-6 and r['decision_ma'] > 0 else 0
        require_close(r['price_advantage_reward'], price_reward, 'price reward')
        observed_fuel = struct.unpack('f', struct.pack('f', r['fuel_before']))[0]
        operating = -0.03 if r['action'] != 0 and observed_fuel > 0.8 else 0.0
        require_close(r['operational_reward'], operating, 'operational reward')
        require_close(r['imo_reward'], 0, 'IMO placeholder')
        require_close(r['reward'], sum(r[k] for k in COMPONENTS), 'reward components')
        require_close(r['step_sci'], amount * r['decision_price'] * r['decision_fx'], 'SCI')
        max_residual = max(max_residual, abs(r['fuel_before'] + amount - consumed - loss - r['fuel_after']))
        previous = r['fuel_after']
    return {
        'steps': len(rows), 'raw_violation': int(any(float(r['fuel_after']) < 0.15 for r in rows)),
        'tolerance_violation': int(any(float(r['fuel_after']) < 0.15 - 1e-12 for r in rows)),
        'max_step_balance_residual': max_residual,
        **{k: sum(float(r[k]) for r in rows) for k in ('step_sci','bunker_amount','realized_consumption','reward', *COMPONENTS)},
        'final_fuel': previous,
    }


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('missing or duplicate CSV columns')
        return list(reader)


def audit(root):
    """Verify supplied bundle hashes, then independently recompute all baseline steps."""
    root = Path(root).resolve()
    hashes = json.loads((root / 'SHA256SUMS.json').read_text())
    for name, digest in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'bundle hash mismatch: {name}')
    paths = sorted((root / 'replayed').glob('seed_*'))
    if len(paths) != 4:
        raise ValueError('expected four checkpoint runs')
    records, model_hashes, baseline_rules, sources = [], set(), {}, {}
    total_steps = 0
    total_episodes = 0
    for path in paths:
        m = json.loads((path / 'manifest.json').read_text())
        if m.get('schema') != 'reward-diagnostics/v1' or m['base_seed'] != 42 or m['episodes'] != 100:
            raise ValueError('unexpected baseline case contract')
        if m['env_config'] != dict(n_ports=3, max_steps=30, min_safe_fuel=0.15, fuel_consumption_per_step=0.05):
            raise ValueError('only V1 normal baseline is supported')
        if m['reward_weights'] != dict(fuel_cost_saving=1.0,risk_penalty=0.5,operational_efficiency=0.3,imo_compliance_bonus=0.2):
            raise ValueError('unexpected reward contract')
        digest = m['checkpoint']['sha256']
        if digest in model_hashes:
            raise ValueError('duplicate checkpoint')
        model_hashes.add(digest)
        sources[path.name] = digest
        grouped = {}
        for r in read_csv(path / 'steps.csv'):
            grouped.setdefault((r['policy'], int(r['seed'])), []).append(r)
        expected = {(p,s) for p in POLICIES for s in range(42,142)}
        if set(grouped) != expected:
            raise ValueError('missing or unexpected cases')
        total_episodes += len(grouped)
        for key, rows in grouped.items():
            result = inspect_steps(rows)
            total_steps += len(rows)
            if key[0] in RULES:
                if key in baseline_rules:
                    if baseline_rules[key] != rows:
                        raise ValueError('repeated rule traces differ')
                    continue
                baseline_rules[key] = rows
            records.append(dict(policy=key[0], checkpoint=digest if key[0]=='double_dqn' else 'not_applicable', seed=key[1], **result))
    summary = {}
    for policy in sorted(POLICIES):
        g = [r for r in records if r['policy']==policy]
        summary[policy] = dict(cases=len(g), **{k: sum(r[k] for r in g)/len(g) for k in
            ('raw_violation','tolerance_violation','step_sci','bunker_amount','realized_consumption','final_fuel','reward',*COMPONENTS)})
    dqn, safe = summary['double_dqn'], summary['safe_stock']
    return dict(schema='diagnostic-snapshot-audit/v1', checked_bundle_files=len(hashes),
        checkpoint_hashes=sources, raw_episodes=total_episodes, raw_steps=total_steps, unique_combinations=len(records),
        shared_market_cases=100, max_step_balance_residual=max(r['max_step_balance_residual'] for r in records),
        policy_summary=summary, dqn_vs_safe=dict(sci_percent_change=100*(dqn['step_sci']/safe['step_sci']-1),
        additional_purchase=dqn['bunker_amount']-safe['bunker_amount'], additional_final_fuel=dqn['final_fuel']-safe['final_fuel']),
        limitations=['Recorded transitions only; not a new model replay.',
        'Tolerance reclassification does not replace the original reward or safety flags.',
        'Baseline only; no stress safety or real-voyage claim.',
        'step_sci in this report is the mean episode total, not SCI per step.',
        'Hashes check bundle integrity, not third-party authenticity.'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args(argv)
    try:
        if a.output.exists():
            raise ValueError('output must be a new file')
        report=audit(a.bundle)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        with a.output.open('x', encoding='utf-8') as f:
            json.dump(report,f,ensure_ascii=False,indent=2)
        print(f'PASS: {report["raw_steps"]} steps; {report["unique_combinations"]} combinations; wrote {a.output}')
    except (ValueError, KeyError, OSError) as exc:
        p.error(str(exc))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
