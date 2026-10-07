"""Report paired policies and separate cost-only decomposition from time objectives."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent/'results'
d=pd.read_csv(P/'decomposition.csv');p=pd.read_csv(P/'pilot.csv')
assert len(d)==3052*3 and len(p)==3052*3*2
assert not d.duplicated(['id','seed']).any() and not p.duplicated(['id','seed','actions']).any()
np.testing.assert_allclose(d.dqn-d.lp,d.action_gap+d.selection_gap,atol=1e-7)
assert (d.action_gap>=-1e-5).all() and (d.selection_gap>=-1e-5).all()
rows=[]
for (split,seed),g in p.groupby(['split','seed']):
 a=g[g.actions==5].set_index('id');b=g[g.actions==6].set_index('id');assert a.index.equals(b.index)
 mask=a.feasible & b.feasible
 lp=d[d.seed==seed].set_index('id').loc[a.index,'lp']
 rows.append(dict(split=split,seed=int(seed),n=len(a),common_feasible=int(mask.sum()),five_success=float(a.feasible.mean()),six_success=float(b.feasible.mean()),five_safe=float(a.safe.mean()),six_safe=float(b.safe.mean()),six_vs_five_common_cost_pct=float(100*(b.loc[mask,'cost'].sum()/a.loc[mask,'cost'].sum()-1)),six_vs_lp_common_cost_pct=float(100*(b.loc[mask,'cost'].sum()/lp.loc[mask].sum()-1)),six_vs_five_all_cost_pct=float(100*(b.cost.sum()/a.cost.sum()-1))))
report=dict(decomposition=dict(cases=3052,action_gap_cases=int((d.drop_duplicates('id').action_gap>1e-5).sum()),action_gap_share_of_pooled_cost_gap=float(d.action_gap.sum()/(d.dqn-d.lp).sum()),maximum_six_vs_lp_abs=float(abs(d.six_oracle-d.lp).max())),paired_pilot=rows)
(P/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
