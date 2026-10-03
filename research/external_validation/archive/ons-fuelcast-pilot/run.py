from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd,torch
P=Path(__file__).resolve().parent; ROOT=P.parent
sys.path.insert(0,str(ROOT/'bunkering-restore'))
from envs.bunkering_env import BunkeringEnv
from agents.dqn import DQNAgent
from scripts.baseline import FixedFuelingStrategy,PriceReactiveStrategy,SafeStockStrategy
from route_stress.ons import parse_ons_crossings,add_past_only_baseline
from route_stress.impact import get_route_impact
checkpoint=ROOT/'integrated-pilot/dqn_final.pt'
sha=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
assert sha=='970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392'
torch.set_num_threads(2)
agent=DQNAgent.load_checkpoint(checkpoint,device='cpu');agent.policy_net.eval()
class DQN:
 name='double_dqn'
 def select_action(self,env,obs,step):
  with torch.no_grad():return int(agent.policy_net(torch.as_tensor(obs).unsqueeze(0)).argmax(1).item())
source=ROOT/'upload/upload-weeklyshipcrossingsbyshiptypethroughsixglobalmaritimepassages.csv'
ons=add_past_only_baseline(parse_ons_crossings(source))
ons.to_csv(P/'ons_context.csv',index=False)
ons.groupby(['chokepoint_id','vessel_type']).tail(1).to_csv(P/'ons_latest_context.csv',index=False)
rows=[];windows=[]
for f in sorted((ROOT/'fuelcast-pilot').glob('*_test_predictions.csv')):
 d=pd.read_csv(f);ship=f.name.split('_test')[0];mean=float(d.train_mean.iloc[0])
 assert mean>0 and np.isfinite(d.actual).all() and (d.actual>=0).all()
 # Same day blocks as the prior pilot; only first 43 samples used per block.
 for start in range(0,len(d)-287,288):
  w=d.iloc[start:start+288]
  if not np.all(np.diff(w['index'])==1):continue
  windows.append(dict(ship=ship,start_index=int(w['index'].iloc[0]),train_mean_kg_s=mean))
  for scenario in ['normal','suez_cape_representative']:
   horizon=get_route_impact(scenario).scenario_max_steps
   for mode in ['constant_control','fuelcast_actual']:
    demands=np.full(horizon,.05) if mode=='constant_control' else .05*w.actual.to_numpy()[:horizon]/mean
    for seed in [820000,820001,820002,820003,820004]:
     for policy in [FixedFuelingStrategy(),PriceReactiveStrategy(),SafeStockStrategy(),DQN()]:
      e=BunkeringEnv(max_steps=horizon);obs,_=e.reset(seed=seed)
      initial_value=e._raw_fuel_price*e._raw_fx_rate;shortage=0.;buy=0.
      for step,need in enumerate(demands):
       action=policy.select_action(e,obs,step)
       shortage+=max(0.,float(need)-e._fuel_remaining)
       e.fuel_consumption_per_step=float(need)
       obs,_,done,trunc,info=e.step(action);buy+=info['actual_bunker_amount']
       if done or trunc:break
      rows.append(dict(ship=ship,start_index=int(w['index'].iloc[0]),scenario=scenario,horizon=horizon,mode=mode,seed=seed,policy=policy.name,original_success=info['voyage_success'],strict_success=info['voyage_success'] and shortage<1e-9,shortage_tank_fraction=shortage,steps=step+1,purchased=buy,SCI=info['cumulative_cost_index'],adjusted_SCI=info['cumulative_cost_index']-e._fuel_remaining*e._raw_fuel_price*e._raw_fx_rate+initial_value))
r=pd.DataFrame(rows);r.to_csv(P/'episodes.csv',index=False)
s=r.groupby(['ship','scenario','mode','policy']).agg(cases=('strict_success','size'),strict_success_rate=('strict_success','mean'),original_success_rate=('original_success','mean'),mean_shortage=('shortage_tank_fraction','mean')).reset_index()
s.to_csv(P/'summary.csv',index=False)
pairs=[]
for keys,g in r.groupby(['ship','scenario','mode']):
 a=g[g.policy=='safe_stock'].set_index(['start_index','seed']);b=g[g.policy=='double_dqn'].set_index(['start_index','seed']);ok=a.strict_success&b.strict_success
 pairs.append(dict(ship=keys[0],scenario=keys[1],mode=keys[2],paired_success=int(ok.sum()),cases=len(a),raw_cost_change_pct=float(100*(b.loc[ok,'SCI'].mean()/a.loc[ok,'SCI'].mean()-1)) if ok.any() and a.loc[ok,'SCI'].mean()>0 else None,adjusted_cost_change_pct=float(100*(b.loc[ok,'adjusted_SCI'].mean()/a.loc[ok,'adjusted_SCI'].mean()-1)) if ok.any() else None))
pd.DataFrame(pairs).to_csv(P/'paired_costs.csv',index=False)
(P/'manifest.json').write_text(json.dumps(dict(checkpoint_sha256=sha,ons_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),windows=windows,seeds=[820000,820001,820002,820003,820004],assumptions=[get_route_impact(x).to_manifest() for x in ['normal','suez_cape_representative']],mapping='actual kg/s / training-only mean kg/s * 0.05 normalized tank per synthetic step; implied tank = training mean * 300 seconds * 20; not real tank capacity',limitations=['5-minute sample variability replayed on synthetic route steps, not real voyage duration','ONS weekly passage context has no shared ship/date key with FuelCast: no joined causal dataset','30/43 horizons come from existing route assumptions, not an ONS traffic-to-delay estimate','Frozen policy gets no new forecast/weather input; no training performed','Strict success additionally requires no pre-refill unmet demand; original environment clips fuel at zero before refill','Five price seeds are repeated scenarios, not independent demand records','Costs compared only on mutually successful pairs; not actual currency'],episodes=len(r)),indent=2))
print(s.to_string(index=False));print(pd.DataFrame(pairs).to_string(index=False))
