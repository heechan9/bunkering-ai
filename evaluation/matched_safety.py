"""Descriptive, matched safety/cost contrasts of saved simulator observations.

No model fitting, imputation, p-values, confidence intervals, or causal claims.
The recorded plan verifies matching, not actual trajectory provenance or independence.
"""
from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from statistics import fmean, median

from evaluation.contract import EvaluationCase, validate_fair_evaluation_plan

BOOL_FIELDS = ('legacy_arrived', 'arrived_without_pre_refill_shortage', 'safe_arrival')
NUM_FIELDS = ('minimum_pre_refill_fuel', 'purchase_sci', 'initial_inventory_value',
              'terminal_inventory_value', 'final_fuel', 'inventory_adjusted_sci')
COUNT_FIELDS = ('pre_refill_shortage_steps', 'pre_refill_reserve_violation_steps')


def integer(value, name):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    raise ValueError(f'{name}: expected nonnegative integer')


def number(value, name):
    if isinstance(value, bool) or value is None or value == '':
        raise ValueError(f'{name}: missing or invalid number')
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name}: invalid number') from exc
    if not math.isfinite(result):
        raise ValueError(f'{name}: nonfinite number')
    return result


def boolean(value, name):
    if type(value) is bool:
        return value
    if value in ('True', 'true'):
        return True
    if value in ('False', 'false'):
        return False
    raise ValueError(f'{name}: missing or invalid boolean')


def key(row):
    policy = row['policy']
    if not isinstance(policy, str) or not policy.strip():
        raise ValueError('policy: empty or invalid name')
    return integer(row['seed'], 'seed'), integer(row['episode'], 'episode'), policy


def distribution(values):
    """Observed spread, NOT a confidence interval or population uncertainty."""
    if not values:
        return None
    return {'n': len(values), 'mean': fmean(values), 'median': median(values),
            'minimum': min(values), 'maximum': max(values),
            'negative': sum(v < 0 for v in values), 'zero': sum(v == 0 for v in values),
            'positive': sum(v > 0 for v in values)}


def matched_safety_report(rows, manifest):
    policies = manifest['policies']
    cases = [EvaluationCase(**case) for case in manifest['cases']]
    validate_fair_evaluation_plan(cases, policies)
    # The row schema lacks a scenario key. Repeated seed/episode under different
    # configs must not be silently collapsed into one matched case.
    planned = [(c.seed, c.episode, c.policy) for c in cases]
    if len(set(planned)) != len(planned):
        raise ValueError('ambiguous scenario: repeated seed/episode/policy')
    json_config = __import__('json').dumps([c.env_config for c in cases], allow_nan=False)
    del json_config
    if manifest['safety_accounting']['mode'] != 'observational_audit_not_strict_termination':
        raise ValueError('unsupported safety accounting mode')
    tolerance = number(manifest['safety_accounting']['tolerance'], 'tolerance')
    if tolerance < 0:
        raise ValueError('negative tolerance')
    normalized = {}
    for row in rows:
        k = key(row)
        if k in normalized:
            raise ValueError(f'duplicate observed case: {k}')
        r = {f: boolean(row[f], f) for f in BOOL_FIELDS}
        r.update({f: number(row[f], f) for f in NUM_FIELDS})
        r.update({f: integer(row[f], f) for f in COUNT_FIELDS})
        feasible = r['legacy_arrived'] and r['pre_refill_shortage_steps'] == 0
        safe = feasible and r['pre_refill_reserve_violation_steps'] == 0
        if feasible != r['arrived_without_pre_refill_shortage'] or safe != r['safe_arrival']:
            raise ValueError(f'inconsistent safety flags: {k}')
        if r['pre_refill_shortage_steps'] > r['pre_refill_reserve_violation_steps']:
            raise ValueError(f'inconsistent shortage/reserve counts: {k}')
        if r['purchase_sci'] < 0 or r['final_fuel'] < 0:
            raise ValueError(f'negative purchase or inventory: {k}')
        expected = r['purchase_sci'] + r['initial_inventory_value'] - r['terminal_inventory_value']
        if not math.isclose(expected, r['inventory_adjusted_sci'], rel_tol=1e-12, abs_tol=tolerance):
            raise ValueError(f'inconsistent inventory accounting: {k}')
        observed_safe_cost = row['safe_arrival_adjusted_sci']
        if safe:
            if not math.isclose(number(observed_safe_cost, 'safe_arrival_adjusted_sci'), expected,
                                rel_tol=1e-12, abs_tol=tolerance):
                raise ValueError(f'inconsistent safe-arrival cost: {k}')
        elif observed_safe_cost not in ('', None):
            raise ValueError(f'unsafe cost must remain missing: {k}')
        normalized[k] = r
    if set(normalized) != set(planned):
        raise ValueError('observed coverage differs from manifest; no silent dropping or imputation')
    case_keys = sorted({(c.seed, c.episode) for c in cases})
    if 'n_episodes' in manifest and integer(manifest['n_episodes'], 'n_episodes') != len(case_keys):
        raise ValueError('manifest n_episodes differs from matched cases')
    comparisons = []
    for a, b in combinations(policies, 2):
        counts = Counter()
        deltas, pairs = [], []
        for seed, episode in case_keys:
            ra, rb = normalized[seed, episode, a], normalized[seed, episode, b]
            sa, sb = ra['safe_arrival'], rb['safe_arrival']
            category = 'both_safe' if sa and sb else 'a_only_safe' if sa else 'b_only_safe' if sb else 'neither_safe'
            counts[category] += 1
            delta = rb['inventory_adjusted_sci'] - ra['inventory_adjusted_sci'] if sa and sb else None
            if delta is not None:
                deltas.append(delta)
            pairs.append({'seed': seed, 'episode': episode, 'safety_category': category,
                          'inventory_adjusted_sci_difference_b_minus_a': delta})
        comparisons.append({'policy_a': a, 'policy_b': b, 'matched_cases': len(case_keys),
            'safety_counts': {c: counts[c] for c in ('both_safe', 'a_only_safe', 'b_only_safe', 'neither_safe')},
            'safe_arrival_difference_b_minus_a': (counts['b_only_safe']-counts['a_only_safe'])/len(case_keys),
            'both_safe_coverage': counts['both_safe']/len(case_keys),
            'cost_difference_b_minus_a': distribution(deltas), 'pairs': pairs})
    return {'schema_version': 1, 'scope': 'saved_simulator_observations_descriptive_only',
        'row_count': len(normalized), 'matched_cases_per_policy': len(case_keys),
        'distinct_evaluation_seeds': len({s for s, e in case_keys}),
        'checkpoint_sha256_recorded': manifest.get('checkpoint', {}).get('sha256'),
        'training_seed_recorded': manifest.get('checkpoint', {}).get('metadata', {}).get('train_seed'),
        'confidence_interval': None, 'p_value': None,
        'inference_status': 'withheld: independent sampling/training replications not established',
        'limits': ['Same manifest seed/config is a planned match, not proof of identical exogenous trajectories.',
                   'Repeated episodes/time points are not asserted independent.',
                   'Cost is conditional on both policies safe; excluded cases remain in safety denominators.',
                   'Conditioning on post-policy safety can select cases; no overall policy cost effect is estimated.',
                   'Synthetic Cost Index is not currency or real monetary savings.',
                   'Saved audit has observational safety semantics; environment termination is unchanged.',
                   'No model training, fit, imputation, causal inference, or policy performance improvement.'],
        'comparisons': comparisons}
