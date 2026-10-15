import json,math,hashlib,sys
from pathlib import Path
from collections import Counter
import argparse
from research.procurement_baseline import benchmark as b
parser=argparse.ArgumentParser(description='Independent sequential ledger and summary audit')
parser.add_argument('--input-dir',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--spec',type=Path,help='Specification when auditing legacy output without spec.json')
args=parser.parse_args()
P=args.input_dir.resolve(); OUT=args.output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=False)
cases=json.load(open(P/'cases.json'));rows=json.load(open(P/'results.json'));summary=json.load(open(P/'summary.json'))
assert len(cases)==len(rows)==120
assert len({x['case']['case_id'] for x in cases})==120
assert Counter(x['block'] for x in cases)==dict.fromkeys(['zero_fees_unlimited','monetary_fees','limited_supply_minimum'],40)
# Deterministic regeneration is exact, with no result-based selection.
from dataclasses import asdict
spec_path=args.spec or P/'spec.json'
assert json.loads(json.dumps([dict(block=k,case=asdict(c)) for k,c in b.generate(json.loads(spec_path.read_text(encoding='utf-8')))]))==cases
checks=Counter();counts={}; issues=[]
for item,r in zip(cases,rows):
 c=item['case'];assert c['case_id']==r['case_id'];B=sum(c['d'])+c['terminal']-c['initial'];tol=max(1e-6,1e-8*c['capacity'])
 for name,s in [('reference',r['reference']),*r['policies'].items()]:
  if 'q_t' not in s: continue
  inv=c['initial'];cost=0;errors=[];q=s['q_t'];z=s['z']
  for i,(qty,stop) in enumerate(zip(q,z)):
   dep=inv+qty;after=dep-c['d'][i]
   if not all(math.isfinite(v) for v in [qty,stop,dep,after]):errors.append('finite')
   if abs(stop-round(stop))>1e-7 or not -1e-7<=stop<=1+1e-7:errors.append('binary')
   if qty < -tol or qty>min(c['supply'][i],c['capacity'])*stop+tol:errors.append('supply')
   if qty<c['minimum'][i]*stop-tol:errors.append('minimum')
   if not c['available'][i] and (qty>tol or stop>1e-7):errors.append('availability')
   if min(inv,dep,after)<-tol or max(inv,dep,after)>c['capacity']+tol:errors.append('inventory')
   if after<c['reserve'][i]-tol:errors.append('reserve')
   if qty<=tol and stop>.5:errors.append('ghost')
   line=qty*(c['p'][i]+c['variable'][i])+stop*c['fixed'][i];cost+=line
   ledger=s['audit']['ledger'][i]
   for key,val in [('I_before_t',inv),('D_after_t',dep),('I_next_t',after),('fuel_cost_usd',qty*c['p'][i]),('variable_fee_usd',qty*c['variable'][i]),('fixed_fee_usd',stop*c['fixed'][i]),('total_usd',line)]:assert abs(ledger[key]-val)<.0001,(c['case_id'],name,key)
   inv=after
  if abs(inv-c['terminal'])>tol:errors.append('terminal')
  assert abs(cost-s['audit']['total_usd'])<.0001
  assert bool(not errors)==s['audit']['valid'],(c['case_id'],name,errors)
  if s['status'] in ['OPTIMAL','FEASIBLE']:
   assert not errors
   assert abs(sum(q)-B)<=tol
   checks[name+'_valid']+=1
  checks['ledgers']+=1
for block in ['ALL']+list(dict.fromkeys(x['block'] for x in rows)):
 subset=[r for r in rows if block=='ALL' or r['block']==block];out=summary[block]
 assert out['n']==len(subset)
 assert out['reference_status']==dict(Counter(r['reference']['status'] for r in subset))
 common=[r for r in subset if r['reference']['status']=='OPTIMAL' and all(v['status']=='FEASIBLE' for v in r['policies'].values())]
 assert out['common_feasible_n']==len(common)
 for policy in b.POLICIES:
  dst=out['policies'][policy];feas=[r for r in subset if r['policies'][policy]['status']=='FEASIBLE'];pair=[r for r in feas if r['reference']['status']=='OPTIMAL']
  a=sum(r['policies'][policy]['audit']['total_usd'] for r in pair);o=sum(r['reference']['audit']['total_usd'] for r in pair)
  assert dst['feasible_n']==len(feas) and dst['failure_n']==len(subset)-len(feas) and dst['pairwise_feasible_n']==len(pair)
  for key,val in [('pairwise_policy_total_usd',a),('pairwise_optimum_total_usd',o),('pairwise_difference_usd',a-o),('pairwise_cost_weighted_difference_pct',100*(a-o)/a),('common_policy_total_usd',sum(r['policies'][policy]['audit']['total_usd'] for r in common)),('common_optimum_total_usd',sum(r['reference']['audit']['total_usd'] for r in common))]:assert abs(dst[key]-val)<1e-6,(block,policy,key)
  assert all(r['policies'][policy]['audit']['total_usd']>=r['reference']['audit']['total_usd']-.01 for r in pair)
# Review policy function itself does not invoke any optimizer.
import ast,inspect
calls=[ast.unparse(n.func) for n in ast.walk(ast.parse(inspect.getsource(b.policy))) if isinstance(n,ast.Call)]
assert not any(any(word in f for word in ['solve','milp','linprog','enumerate']) for f in calls)
report=dict(status='PASS',checks=dict(checks),all=summary['ALL'],policy_calls=calls)
(OUT/'independent_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
