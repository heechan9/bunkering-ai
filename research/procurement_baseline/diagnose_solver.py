"""Record both MILP phases without assuming the original bug occurs on every platform."""
import argparse
import json
import platform
from dataclasses import asdict
from pathlib import Path

from research.procurement_baseline import procurement, reference_original
from research.procurement_baseline.benchmark import generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    spec = json.loads(Path(__file__).with_name('spec.json').read_text(encoding='utf-8'))
    case = next(c for _, c in generate(spec) if c.case_id == 'monetary_fees_010')
    report = {'platform': platform.platform(), 'case': asdict(case), 'variants': {}}
    for name, module in [('original', reference_original), ('patched', procurement)]:
        real = module.milp
        trace = []

        def traced(*a, **kw):
            result = real(*a, **kw)
            trace.append({'phase': len(trace) + 1, 'options': kw.get('options'),
                          'status': int(result.status), 'message': result.message,
                          'objective': result.fun})
            return result

        module.milp = traced
        try:
            result = module.solve(module.Case(**asdict(case)))
        finally:
            module.milp = real
        report['variants'][name] = {'result': result, 'milp_calls': trace}
    independent = procurement.enumerate_stops(case)
    report['independent_enumeration'] = independent
    report['historical_failure_reproduced'] = report['variants']['original']['result']['status'] == 'INFEASIBLE'
    patched = report['variants']['patched']['result']
    assert patched['status'] == independent['status'] == 'OPTIMAL'
    assert abs(patched['objective_usd'] - 13000) <= .01
    assert abs(patched['objective_usd'] - independent['best']['objective_usd']) <= .01
    assert patched['audit']['valid']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'original': report['variants']['original']['result']['status'],
                      'patched': patched['status'], 'objective_usd': patched['objective_usd'],
                      'q_t': patched['q_t'], 'historical_failure_reproduced': report['historical_failure_reproduced']}))


if __name__ == '__main__':
    main()
