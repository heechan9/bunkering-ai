"""Data-free structural diagnosis; exhaustive action oracle is NOT a trained policy."""
import ast
import csv
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'results'

def source_function(relative, name, namespace):
    """Execute only the actual pure function AST, avoiding training imports."""
    path = ROOT / relative
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]

quantity = source_function('research/ntnu_bunkering/retrain.py', 'quantity', {})
solve = source_function('research/ntnu_bunkering/experiment.py', 'solve', {'np': np, 'linprog': linprog})

def cheaper(d, p, i, inv):
    j = next((j for j in range(i + 1, 4) if p[j] < p[i]), 4)
    return max(0., min(1., .1 + sum(d[i:j])) - inv)

def evaluate(d, p, actions, extra=False):
    inv, spend, trace = .5, 0., []
    for i, a in enumerate(actions):
        q = cheaper(d, p, i, inv) if extra and a == 5 else quantity({'d': d}, i, inv, a)
        before = inv
        inv += q - d[i]
        if inv < .1 - 1e-9 or inv > 1 + 1e-9:
            return float('inf'), trace
        spend += q * p[i]
        trace.append({'step': i, 'action': a, 'opening': before, 'purchase': q, 'demand': d[i], 'closing': inv, 'price': p[i]})
    return spend + min(p) * (.5 - inv), trace

def oracle(d, p, extra=False):
    best = (float('inf'), None, None)
    for a in itertools.product(range(6 if extra else 5), repeat=4):
        cost, trace = evaluate(d, p, a, extra)
        if cost < best[0]:
            best = cost, a, trace
    return best

def run():
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(20261007)
    cases = [([.2,.3,.2,.2], [1.,2.,1.5,2.5])]
    cases += [(rng.uniform(.12,.42,4).tolist(), rng.uniform(.7,1.4,4).tolist()) for _ in range(119)]
    rows, worst = [], None
    for k, (d,p) in enumerate(cases):
        q = solve(p,d,1.,.5,.1,[True]*4)
        assert q is not None
        terminal = .5 + sum(q) - sum(d)
        lp = float(np.dot(q,p) + min(p)*(.5-terminal))
        old, old_a, trace = oracle(d,p)
        new, new_a, _ = oracle(d,p,True)
        rule, _ = evaluate(d,p,[5]*4,True)
        assert old >= lp - 1e-8
        assert new <= old + 1e-8
        assert abs(new-lp) < 1e-8 and abs(rule-lp) < 1e-8
        row = {'case':k,'lp':lp,'five_action_oracle':old,'six_action_oracle':new,'cheaper_rule':rule,'unavoidable_gap':old-lp,'gap_pct':100*(old/lp-1)}
        rows.append(row)
        if worst is None or row['gap_pct'] > worst['result']['gap_pct']:
            worst = {'demand':d,'price':p,'result':row,'five_actions':old_a,'five_trace':trace,'lp_purchases':q.tolist(),'six_actions':new_a}
    with (OUT/'cases.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    report={'seed':20261007,'cases':len(rows),'old_sequences_per_case':625,'new_sequences_per_case':1296,
        'five_action_strict_gap_cases':sum(r['unavoidable_gap']>1e-8 for r in rows),
        'five_action_total_gap_pct':100*(sum(r['five_action_oracle'] for r in rows)/sum(r['lp'] for r in rows)-1),
        'max_gap_pct':max(r['gap_pct'] for r in rows),
        'six_action_max_abs_gap':max(abs(r['six_action_oracle']-r['lp']) for r in rows),
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['research/ntnu_bunkering/retrain.py','research/ntnu_bunkering/experiment.py']},
        'limitations':['Synthetic four-leg cases, not NTNU original-case replay.','Exhaustive oracle, not DQN training or achieved learned performance.','Static known prices, all ports available, no stop-time constraint.','No attribution of historical DQN errors without checkpoint replay.','Sixth action is a rule candidate; gains are not learned gains.']}
    (OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (OUT/'worst_case.json').write_text(json.dumps(worst,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    run()
