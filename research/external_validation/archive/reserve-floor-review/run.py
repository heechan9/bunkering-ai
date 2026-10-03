from pathlib import Path
import sys,json
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent;R=P.parent
sys.path.insert(0,str(R/'fuelcast-retrain'))
from run import StrictEnv,DQNAgent,CK,SafeStockStrategy
agent=DQNAgent.load_checkpoint(CK,device='cpu')
class AdaptiveStock:
 """Causal two-step reserve for a consumption-before-refill environment."""
 def __init__(self,prior):self.prior=float(prior);self.history=[]
 def predict(self):return max([self.prior]+self.history[-3:])
 def action(self,fuel):return int(fuel <= 2*self.predict()+.02+1e-8)
 def observe(self,consumed):self.history.append(float(consumed))

def run_case(group,case,demands,prior,horizon,seed,policy,trace=False):
 e=StrictEnv(demands,horizon);o,_=e.reset(seed=seed);initial=e._raw_fuel_price*e._raw_fx_rate
 adaptive=AdaptiveStock(prior);steps=[]
 for t in range(horizon):
  before=e._fuel_remaining;estimate=adaptive.predict()
  a=agent.greedy_action(o) if policy=='original_dqn' else SafeStockStrategy().select_action(e,o,t) if policy=='safe_stock' else (int(before <= max(.4,2*estimate+.02)+1e-8) if policy=='reserve_floor' else adaptive.action(before))
  o,_,done,trunc,info=e.step(a)
  # Consume only the just-completed interval's telemetry, never demands[t+1].
  adaptive.observe(info['fuel_consumption_per_step'])
  if trace:steps.append(dict(case=case,policy=policy,step=t,fuel_before=before,estimate_from_past=estimate,threshold=max(.4,2*estimate+.02) if policy=='reserve_floor' else 2*estimate+.02,action=a,actual_demand=info['fuel_consumption_per_step'],bought=info['actual_bunker_amount'],fuel_after=e._fuel_remaining,shortage=info['shortage'],end_reason=info['end_reason']))
  if done or trunc:break
 return dict(group=group,case=case,horizon=horizon,seed=seed,policy=policy,success=info['voyage_success'],SCI=info['cumulative_cost_index'],adjusted_SCI=info['cumulative_cost_index']-e._fuel_remaining*e._raw_fuel_price*e._raw_fx_rate+initial,steps=t+1),steps

rows=[];traces=[];priors={}
protocol=json.loads((R/'fuelcast-pilot/protocol.json').read_text())
for rec in protocol['ships']:
 d=pd.read_parquet(R/'feasibility'/f"{rec['ship']}.parquet",columns=['index','Consumer_Total_MomentaryFuel'])
 tr=d[d['index'].between(*rec['index_ranges'][0])].Consumer_Total_MomentaryFuel
 priors[rec['ship']]=float(np.quantile(.05*tr/tr.mean(),.95))
for f in sorted((R/'fuelcast-pilot').glob('*_test_predictions.csv')):
 d=pd.read_csv(f);ship=f.name.split('_test')[0]
 for start in range(0,len(d)-287,288):
  w=d.iloc[start:start+288]
  if not np.all(np.diff(w['index'])==1):continue
  demands=.05*w.actual.to_numpy()[216:259]/float(w.train_mean.iloc[0])
  for horizon in [30,43]:
   for seed in range(840000,840005):
    for policy in ['original_dqn','safe_stock','adaptive_stock','reserve_floor']:
     row,_=run_case(ship,str(int(w['index'].iloc[216])),demands,priors[ship],horizon,seed,policy);rows.append(row)
# Separate synthetic jump stress, not observations from FuelCast.
for jump in [1.5,2.,3.,4.]:
 for onset in [7,12,17]:
  for horizon in [30,43]:
   demands=np.full(horizon,.05);demands[onset:]=.05*jump
   for seed in range(82,102):
    for policy in ['original_dqn','safe_stock','adaptive_stock','reserve_floor']:
     row,trace=run_case('synthetic_jump',f'jump{jump}_onset{onset}',demands,.05,horizon,seed,policy,trace=seed==82)
     rows.append(row);traces.extend(trace)
r=pd.DataFrame(rows);assert len(r)==6720
assert not r.duplicated(['group','case','horizon','seed','policy']).any()
r.to_csv(P/'episodes.csv',index=False);pd.DataFrame(traces).to_csv(P/'failure_trace.csv',index=False)
s=r.groupby(['group','horizon','policy']).agg(cases=('success','size'),success_rate=('success','mean')).reset_index();s.to_csv(P/'summary.csv',index=False)
pairs=[]
for keys,g in r.groupby(['group','horizon']):
 for baseline in ['original_dqn','safe_stock','adaptive_stock']:
  a=g[g.policy==baseline].set_index(['case','seed']);b=g[g.policy=='reserve_floor'].set_index(['case','seed']);ok=a.success&b.success
  pairs.append(dict(group=keys[0],horizon=keys[1],baseline=baseline,cases=len(a),paired_success=int(ok.sum()),raw_change_pct=100*(b.loc[ok,'SCI'].mean()/a.loc[ok,'SCI'].mean()-1),adjusted_change_pct=100*(b.loc[ok,'adjusted_SCI'].mean()/a.loc[ok,'adjusted_SCI'].mean()-1)))
pd.DataFrame(pairs).to_csv(P/'paired_costs.csv',index=False)
# Invariant check: same observed prefix yields same decision despite any future data.
a=AdaptiveStock(.05);b=AdaptiveStock(.05)
for seen in [.06,.08,.07]:a.observe(seen);b.observe(seen)
assert a.action(.17)==b.action(.17)==1
(P/'manifest.json').write_text(json.dumps(dict(rule='reserve floor: stock <= max(0.4,2*max(train95_prior,last3_observed_consumptions)+0.02)+1e-8; floor assumes two intervals each at most0.2',priors=priors,synthetic_prior=.05,reason='consumption occurs before refill; wait must leave room for next interval before next purchase',parameters='fixed .02 margin; no test tuning; no future consumption supplied',limitations=['past-only estimator does not guarantee safety under unseen abrupt jumps','training95 prior requires vessel historical training data','FuelCast test was previously examined, not blind validation','synthetic fouling is graph-derived assumptions, not observed fuel','full capped refill unchanged; policy and environment are research-only'],episodes=len(r),evaluation='unused offset216..258 within each held-out 288-sample block; new price seeds; synthetic persistent jumps1.5/2/3/4x at steps7/12/17'),indent=2))
print(s.to_string(index=False));print(pd.DataFrame(pairs).to_string(index=False))
