"""Check artifact integrity and sequential accounting, not solver optimality proofs."""
import argparse
import copy
import ast
from collections import Counter
from dataclasses import asdict
import inspect
import json
import math
from pathlib import Path

from research.procurement_baseline import benchmark as b


class AuditError(ValueError):
    """An artifact is incomplete or inconsistent with independently checked evidence."""


def require(condition, context):
    if not condition:
        raise AuditError(context)


def number(value, context):
    require(type(value) in (int, float) and math.isfinite(value), context + ': finite number required')
    return value


def compare(actual, expected, context, tolerance=1e-6):
    """Compare the entire schema; Python's bool/int equality is not evidence."""
    if isinstance(expected, dict):
        require(type(actual) is dict and actual.keys() == expected.keys(), context + ': fields')
        for key, value in expected.items():
            compare(actual[key], value, context + '.' + key, tolerance)
    elif isinstance(expected, list):
        require(type(actual) is list and len(actual) == len(expected), context + ': length')
        for i, value in enumerate(expected):
            compare(actual[i], value, f'{context}[{i}]', tolerance)
    elif type(expected) is bool or expected is None or isinstance(expected, str):
        require(type(actual) is type(expected) and actual == expected, context + ': value/type')
    elif type(expected) is int:
        require(type(actual) is int and actual == expected, context + ': integer')
    else:
        number(actual, context)
        require(abs(actual - expected) <= tolerance, context + ': numeric mismatch')


def check_result(c, result, name, checks):
    require(type(result) is dict, name + ': result object')
    status = result.get('status')
    policy = name in b.POLICIES
    allowed = {'FEASIBLE', 'POLICY_FAILURE'} if policy else {
        'OPTIMAL', 'INFEASIBLE', 'LIMIT_REACHED', 'UNBOUNDED', 'SOLVER_ERROR',
        'NOT_READY', 'INVALID_INPUT', 'LEXICOGRAPHIC_FAILED', 'AUDIT_FAILED',
        'REFERENCE_CONTRADICTION'}
    require(type(status) is str and status in allowed, name + ': status')
    solution_fields = {'q_t', 'z', 'audit'}
    has_solution = bool(solution_fields.intersection(result))
    require(not (policy or status in {'OPTIMAL', 'AUDIT_FAILED'}) or has_solution,
            name + ': missing solution')
    if not has_solution:
        require(type(result.get('message')) is str, name + ': missing failure message')
        return
    require(policy or status in {'OPTIMAL', 'AUDIT_FAILED', 'REFERENCE_CONTRADICTION'},
            name + ': status cannot carry a solution')
    require(solution_fields <= result.keys(), name + ': incomplete solution')
    n = len(c['d'])
    q, z = result['q_t'], result['z']
    require(type(q) is list and type(z) is list and len(q) == len(z) == n, name + ': vector length')
    for value in q + z:
        number(value, name + ': vector')
    inv = float(c['initial'])
    cost = 0.
    errors, ledger = [], []
    tol = max(1e-6, 1e-8 * c['capacity'])
    for i in range(n):
        qty, stop = q[i], z[i]
        dep = inv + qty
        after = dep - c['d'][i]
        if min(abs(stop), abs(stop - 1)) > 1e-7: errors.append(f'{i}:binary')
        if qty < -tol or qty > min(c['supply'][i], c['capacity']) * stop + tol: errors.append(f'{i}:supply/link')
        if not c['available'][i] and (qty > tol or stop > 1e-7): errors.append(f'{i}:unavailable')
        if qty < c['minimum'][i] * stop - tol: errors.append(f'{i}:minimum')
        if qty <= tol and stop > .5: errors.append(f'{i}:ghost stop')
        if min(inv, dep, after) < -tol or max(inv, dep, after) > c['capacity'] + tol: errors.append(f'{i}:inventory')
        if after < c['reserve'][i] - tol: errors.append(f'{i}:reserve')
        fuel = qty * (c['p'][i] if c['available'][i] else 0.)
        variable, fixed = qty * c['variable'][i], stop * c['fixed'][i]
        line = fuel + variable + fixed
        cost += line
        ledger.append(dict(call_index=i, I_before_t=float(inv), q_t=float(qty), D_after_t=float(dep),
                           consumption_t=float(c['d'][i]), I_next_t=float(after), reserve_t=float(c['reserve'][i]),
                           z=float(stop), fuel_cost_usd=float(fuel), variable_fee_usd=float(variable),
                           fixed_fee_usd=float(fixed), total_usd=float(line)))
        inv = after
    if abs(inv - c['terminal']) > tol: errors.append('terminal')
    residual = c['initial'] + sum(q) - sum(c['d']) - inv
    if abs(residual) > tol: errors.append('mass balance')
    if not policy:
        objective = number(result.get('objective_usd'), name + ': objective_usd')
        if abs(cost - objective) > max(.01, 1e-8 * max(1, abs(cost))): errors.append('objective')
        for key in ('mip_gap', 'mip_dual_bound'):
            if result.get(key) is not None:
                number(result[key], name + ': ' + key)
    expected = dict(valid=not errors, errors=errors, ledger=ledger, total_usd=float(cost),
                    terminal_t=float(inv), mass_residual_t=float(residual))
    compare(result['audit'], expected, name + '.audit', tolerance=.0001)
    require(status != 'AUDIT_FAILED' or bool(errors), name + ': AUDIT_FAILED without errors')
    purchase = sum(c['d']) + c['terminal'] - c['initial']
    if policy:
        # Policy-specific explanatory reasons are text, not feasibility evidence.
        require(type(result.get('reasons')) is list and all(type(x) is str for x in result['reasons']), name + ': reasons')
        for key, value in [('total_purchase_required_t', purchase), ('total_purchase_residual_t', sum(q) - purchase)]:
            number(result.get(key), name + ': ' + key)
            require(abs(result[key] - value) <= tol, name + ': ' + key)
        require((status == 'FEASIBLE') == (not errors and not result['reasons']), name + ': policy status')
    if status in {'OPTIMAL', 'FEASIBLE'}:
        require(not errors and abs(sum(q) - purchase) <= tol, name + ': invalid feasible result')
        checks[name + '_valid'] += 1
    checks['ledgers'] += 1
    return expected


def recompute_summary(rows):
    """Aggregate checked ledgers without calling the producer's summary function."""
    result = {}
    for block in ['ALL'] + list(dict.fromkeys(r['block'] for r in rows)):
        subset = [r for r in rows if block == 'ALL' or r['block'] == block]
        n = len(subset)
        statuses = Counter(r['reference']['status'] for r in subset)
        common = [r for r in subset if r['reference']['status'] == 'OPTIMAL'
                  and all(r['policies'][p]['status'] == 'FEASIBLE' for p in b.POLICIES)]
        out = dict(n=n, reference_status=dict(statuses), reference_optimal_rate=statuses['OPTIMAL']/n,
                   reference_infeasible_rate=statuses['INFEASIBLE']/n,
                   reference_other_rate=(n-statuses['OPTIMAL']-statuses['INFEASIBLE'])/n,
                   common_feasible_n=len(common), policies={})
        for p in b.POLICIES:
            feasible = [r for r in subset if r['policies'][p]['status'] == 'FEASIBLE']
            failures = [r for r in subset if r['policies'][p]['status'] != 'FEASIBLE']
            pairs = [r for r in feasible if r['reference']['status'] == 'OPTIMAL']
            policy_cost = sum(r['policies'][p]['audit']['total_usd'] for r in pairs)
            ref_cost = sum(r['reference']['audit']['total_usd'] for r in pairs)
            diffs = [r['policies'][p]['audit']['total_usd']-r['reference']['audit']['total_usd'] for r in pairs]
            require(all(d >= -.01 for d in diffs), block + '.' + p + ': negative difference')
            common_cost = sum(r['policies'][p]['audit']['total_usd'] for r in common)
            common_ref = sum(r['reference']['audit']['total_usd'] for r in common)
            out['policies'][p] = dict(
                feasible_n=len(feasible), feasible_rate=len(feasible)/n,
                failure_n=len(failures), failure_rate=len(failures)/n,
                policy_failure_on_proven_feasible_n=sum(r['reference']['status']=='OPTIMAL' for r in failures),
                failure_on_proven_infeasible_n=sum(r['reference']['status']=='INFEASIBLE' for r in failures),
                failure_on_unresolved_reference_n=sum(r['reference']['status'] not in {'OPTIMAL','INFEASIBLE'} for r in failures),
                pairwise_feasible_n=len(pairs), pairwise_policy_total_usd=float(policy_cost),
                pairwise_optimum_total_usd=float(ref_cost), pairwise_difference_usd=float(policy_cost-ref_cost),
                pairwise_cost_weighted_difference_pct=100*(policy_cost-ref_cost)/policy_cost if policy_cost else None,
                optimal_match_n=sum(abs(d)<=.01 for d in diffs), negative_difference_n=sum(d<-.01 for d in diffs),
                common_policy_total_usd=float(common_cost), common_optimum_total_usd=float(common_ref),
                common_difference_usd=float(common_cost-common_ref),
                common_cost_weighted_difference_pct=100*(common_cost-common_ref)/common_cost if common_cost else None)
        result[block] = out
    return result


def audit_artifacts(cases, rows, summary, spec):
    require(type(cases) is list and type(rows) is list and len(cases) == len(rows) == 120, 'case/row count')
    regenerated = json.loads(json.dumps([dict(block=k, case=asdict(c)) for k, c in b.generate(spec)]))
    compare(cases, regenerated, 'cases', tolerance=0)
    require(len({x['case']['case_id'] for x in cases}) == 120, 'duplicate cases')
    require(Counter(x['block'] for x in cases) == dict.fromkeys(
        ['zero_fees_unlimited', 'monetary_fees', 'limited_supply_minimum'], 40), 'case blocks')
    checks = Counter()
    checked_rows = copy.deepcopy(rows)
    for item, row in zip(cases, checked_rows):
        require(type(row) is dict, 'row object')
        require(row.get('case_id') == item['case']['case_id'] and row.get('block') == item['block'], 'row membership')
        require(type(row.get('policies')) is dict and set(row['policies']) == set(b.POLICIES), 'policy membership')
        reference_audit = check_result(item['case'], row.get('reference'), 'reference', checks)
        if reference_audit is not None:
            row['reference']['audit'] = reference_audit
        for name in b.POLICIES:
            row['policies'][name]['audit'] = check_result(item['case'], row['policies'][name], name, checks)
    recomputed = recompute_summary(checked_rows)
    compare(summary, recomputed, 'summary')
    calls = [ast.unparse(n.func) for n in ast.walk(ast.parse(inspect.getsource(b.policy))) if isinstance(n, ast.Call)]
    require(not any(any(word in f for word in ['solve', 'milp', 'linprog', 'enumerate']) for f in calls), 'policy optimizer call')
    return dict(status='PASS', checks=dict(checks), all=recomputed['ALL'], summary=recomputed, policy_calls=calls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--spec', type=Path, help='Specification when auditing legacy output without spec.json')
    args = parser.parse_args()
    source, output = args.input_dir.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))
    report = audit_artifacts(read(source/'cases.json'), read(source/'results.json'),
                             read(source/'summary.json'), read(args.spec or source/'spec.json'))
    text = json.dumps(report, indent=2, allow_nan=False)
    (output/'independent_checks.json').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
