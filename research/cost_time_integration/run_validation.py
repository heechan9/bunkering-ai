"""Frozen expectations are comparison-only, never passed into solve."""
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
    fixture = json.loads((root/'fixtures_compact.json').read_text())
    proofs = json.loads((root/'analytical_proofs.json').read_text())
    results = []
    for case in fixture['cases']:
        c = copy.deepcopy(fixture['base']); c.update(case['overrides'])
        answer = solve(c); expected = case['expected']
        checks = [answer['status'] == expected['status']]
        if answer['status'] == 'FEASIBLE_OPTIMAL':
            ledger = audit(c, answer['purchases_t']); answer['independent_audit'] = ledger
            witness = audit(c, expected['witness_purchases_t'])
            checks.extend([ledger['valid'], witness['valid'],
                abs(answer['cost_usd']-expected['optimal_cost_usd']) <= .0001,
                abs(ledger['cost_usd']-answer['cost_usd']) <= .0001,
                abs(ledger['time_hours']-answer['time_hours']) <= .000001])
            if expected['optimal_positive_purchase_count'] is not None:
                checks.append(answer['positive_purchase_count'] == expected['optimal_positive_purchase_count'])
        results.append(dict(id=case['id'], passed=all(checks), result=answer, analytical_proof=proofs[case['id']]))
    output = dict(environment=dict(python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__),
                  input_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('contract.json','fixtures_compact.json','analytical_proofs.json')},
                  passed=sum(r['passed'] for r in results), total=len(results), results=results)
    path = root/'validation_results.json'
    if path.exists(): raise FileExistsError(path)
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(f"{output['passed']}/{output['total']} frozen synthetic cases passed")
    for r in results: print(r['id'], r['result']['status'], r['result'].get('cost_usd'), r['passed'])
    if output['passed'] != output['total']: raise SystemExit(1)

if __name__ == '__main__': main()
