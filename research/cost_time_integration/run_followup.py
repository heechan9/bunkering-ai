"""Additional frozen development cases, separate from the original seventeen."""
import copy
import hashlib
import json
from pathlib import Path
import platform
import numpy
import scipy
from .solver import solve
from .ledger import audit


def main():
    root = Path(__file__).parent
    original = json.loads((root/'fixtures_compact.json').read_text())
    followup = json.loads((root/'followup_fixtures.json').read_text())
    results = []
    for case in followup['cases']:
        c = copy.deepcopy(original['base']); c.update(case['overrides'])
        for key, update in case.get('call_updates', {}).items(): c['calls'][int(key)].update(update)
        if case.get('existing_port2'):
            c['calls'][1] = dict(kind='existing', baseline_departure_hours=3.5,
                cargo_end_with_bunkering_hours=3, bunker_ready_hours=0,
                preparation_hours=1, cleanup_hours=1, transfer_hours_per_t=.1,
                departure_readiness_hours=.5)
        expected = case['expected']; result = solve(c)
        checks = [result['status'] == expected['status']]
        if result['status'] == 'FEASIBLE_OPTIMAL':
            ledger = audit(c, result['purchases_t']); witness = audit(c, expected['q'])
            checks += [ledger['valid'], witness['valid'],
                       abs(result['cost_usd']-expected['cost_usd']) <= .0001,
                       abs(result['cost_usd']-ledger['cost_usd']) <= .0001,
                       abs(result['time_hours']-ledger['time_hours']) <= .000001]
            result['independent_ledger'] = ledger
        results.append(dict(id=case['id'], input=c, expected=expected, result=result, passed=all(checks)))
    groups = []
    by_id = {r['id']:r for r in results}
    for group in followup['monotonicity_groups']:
        costs = [by_id[key]['result']['cost_usd'] for key in group]
        groups.append(dict(cases=group, costs_usd=costs, passed=all(a >= b-.0001 for a,b in zip(costs,costs[1:]))))
    original_checks = []
    for case in original['cases']:
        c = copy.deepcopy(original['base']); c.update(case['overrides'])
        result = solve(c); expected = case['expected']
        passed = result['status'] == expected['status']
        if result['status'] == 'FEASIBLE_OPTIMAL':
            passed &= audit(c,result['purchases_t'])['valid'] and abs(result['cost_usd']-expected['optimal_cost_usd']) <= .0001
        original_checks.append(dict(id=case['id'],passed=bool(passed)))
    out = dict(environment=dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__),
               input_sha256=hashlib.sha256((root/'followup_fixtures.json').read_bytes()).hexdigest(),
               cases=results, monotonicity=groups, original_17_recheck=original_checks)
    path=root/'followup_results.json'
    if path.exists(): raise FileExistsError(path)
    path.write_text(json.dumps(out,indent=2)+'\n')
    for row in results: print(row['id'],row['result']['status'],row['result'].get('cost_usd'),row['result'].get('time_hours'),row['passed'])
    print('Additional cases:',sum(r['passed'] for r in results),'/',len(results))
    print('Monotonicity:',groups)
    print('Original cases after fixes:',sum(r['passed'] for r in original_checks),'/ 17')
    if not all(r['passed'] for r in results+groups+original_checks): raise SystemExit(1)


if __name__ == '__main__': main()
