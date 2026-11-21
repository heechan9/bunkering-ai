import copy,json,sys,platform,hashlib
from pathlib import Path
import numpy,scipy
from research.cost_time_integration import solver
from research.cost_time_integration.ledger import audit
root=Path(solver.__file__).parent
original=json.loads((root/'fixtures_compact.json').read_text()); follow=json.loads((root/'followup_fixtures.json').read_text())
rows=[]
for phase,data in [('original',original),('followup',follow)]:
 for case in data['cases']:
  c=copy.deepcopy(original['base']);c.update(case['overrides'])
  for key,update in case.get('call_updates',{}).items():c['calls'][int(key)].update(update)
  if case.get('existing_port2'):c['calls'][1]=dict(kind='existing',baseline_departure_hours=3.5,cargo_end_with_bunkering_hours=3,bunker_ready_hours=0,preparation_hours=1,cleanup_hours=1,transfer_hours_per_t=.1,departure_readiness_hours=.5)
  r=solver.solve(c);e=case['expected'];assert r['status']==e['status']
  if r['status']=='FEASIBLE_OPTIMAL':
   cost=e['optimal_cost_usd'] if phase=='original' else e['cost_usd'];w=e['witness_purchases_t'] if phase=='original' else e['q']
   a=audit(c,r['purchases_t']);assert a['valid'] and audit(c,w)['valid'];assert abs(r['cost_usd']-cost)<=1e-4;assert abs(r['time_hours']-a['time_hours'])<=1e-6
   if e.get('optimal_positive_purchase_count') is not None:assert r['positive_purchase_count']==e['optimal_positive_purchase_count']
  rows.append({'phase':phase,'id':case['id'],'status':r['status'],'cost':r.get('cost_usd'),'time':r.get('time_hours')})
result={'environment':{'python':sys.version,'platform':platform.platform(),'numpy':numpy.__version__,'scipy':scipy.__version__},'source_hashes':{str(p.relative_to(root.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'solver.py',root/'ledger.py',root.parent/'port_call_time/model.py']},'frozen_cases_passed':len(rows),'cases':rows}
print(json.dumps(result,indent=2))
