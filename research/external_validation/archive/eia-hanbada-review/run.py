from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd,torch
P=Path(__file__).resolve().parent;R=P.parent;sys.path.insert(0,str(R/'bunkering-restore'))
from envs.bunkering_env import BunkeringEnv
from agents.dqn import DQNAgent
from scripts.baseline import SafeStockStrategy,FixedFuelingStrategy,PriceReactiveStrategy
torch.set_num_threads(1)
ck=R/'integrated-pilot/dqn_final.pt';sha=hashlib.sha256(ck.read_bytes()).hexdigest()
assert sha=='970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392'
agent=DQNAgent.load_checkpoint(ck,device='cpu')
class DQN:
 name='double_dqn'
 def select_action(self,env,obs,step):return agent.greedy_action(obs)
class Replay(BunkeringEnv):
 def __init__(self,path):self.path=path;super().__init__(max_steps=len(path)-1)
 def reset(self,**kw):
  _,info=super().reset(**kw);self._raw_fuel_price=float(self.path[0]);self._price_history.clear();self._price_history.append(self._raw_fuel_price);self._raw_fx_rate=1300.;self._state=self._observation();return self._state,info
 def _transition(self,state,action):
  obs,amount=super()._transition(state,action)
  self._price_history.pop();self._raw_fuel_price=float(self.path[self._step_count]);self._price_history.append(self._raw_fuel_price);self._raw_fx_rate=1300.
  return self._observation(),amount
d=pd.read_csv(R/'country-pilot/eia_monthly.csv');d['month']=pd.to_datetime(d.date).dt.to_period('M');prices=d.set_index('month').price_usd_gallon
rows=[];paths=[]
for year in range(1984,2011):
 for month in [1,4,7,10]:
  start=pd.Timestamp(year,month,15)
  for horizon in [30,43]:
   dates=pd.date_range(start,periods=horizon+1,freq='D')
   for lag in [0,1,2,3]:
    # lag=0 is a constant control, not contemporaneous monthly information.
    if lag==0:mapped=np.full(horizon+1,500.)
    else:
     observed=dates.to_period('M')-lag
     assert (observed<dates.to_period('M')).all()
     values=prices.loc[observed].to_numpy();mapped=500*values/values[0]
    path=np.clip(mapped,250,850)
    paths.append(dict(start=str(start.date()),horizon=horizon,lag=lag,clipped=int((mapped!=path).sum()),points=len(path),updates=int((np.diff(path)!=0).sum())))
    for policy in [DQN(),SafeStockStrategy(),FixedFuelingStrategy(),PriceReactiveStrategy()]:
     e=Replay(path);o,_=e.reset(seed=820000);shortage=0.
     for t in range(horizon):
      a=policy.select_action(e,o,t);shortage+=max(0.,e.fuel_consumption_per_step-e._fuel_remaining)
      o,_,done,trunc,info=e.step(a)
      if done or trunc:break
     rows.append(dict(start=str(start.date()),year=year,horizon=horizon,lag=lag,policy=policy.name,success=info['voyage_success'] and shortage<1e-9,SCI=info['cumulative_cost_index'],adjusted_SCI=info['cumulative_cost_index']-e._fuel_remaining*e._raw_fuel_price*1300+650000))
result=pd.DataFrame(rows);result.to_csv(P/'eia_episodes.csv',index=False)
summary=result.groupby(['lag','horizon','policy']).agg(cases=('success','size'),success_rate=('success','mean'),SCI=('SCI','mean')).reset_index();summary.to_csv(P/'eia_summary.csv',index=False)
pairs=[];annual=[]
for (lag,horizon),g in result.groupby(['lag','horizon']):
 a=g[g.policy=='safe_stock'].set_index('start');b=g[g.policy=='double_dqn'].set_index('start');ok=a.success&b.success
 pairs.append(dict(lag=lag,horizon=horizon,paired_cases=int(ok.sum()),raw_change_pct=100*(b.loc[ok,'SCI'].mean()/a.loc[ok,'SCI'].mean()-1),adjusted_change_pct=100*(b.loc[ok,'adjusted_SCI'].mean()/a.loc[ok,'adjusted_SCI'].mean()-1)))
 for year in range(1984,2011):
  keep=ok & (a.year==year)
  annual.append(dict(lag=lag,horizon=horizon,year=year,adjusted_change_pct=100*(b.loc[keep,'adjusted_SCI'].mean()/a.loc[keep,'adjusted_SCI'].mean()-1)))
pd.DataFrame(pairs).to_csv(P/'eia_paired.csv',index=False);pd.DataFrame(annual).to_csv(P/'eia_annual.csv',index=False);pd.DataFrame(paths).to_csv(P/'eia_paths.csv',index=False)
# Identifiability check, not invented daily demand or a new training dataset.
h=json.loads((R/'bunkering-restore/results/real_voyage/hanbada_comparison_inputs.json').read_text());checks=[]
mass=float(h['consumption'])
for w in h['windows']:
 volumes={k:float(v['sum']) for k,v in w['engines'].items()};total=sum(volumes.values());rho=mass/total
 for engine,volume in volumes.items():
  target=float(h['summary_engines'][engine]['sum'])
  checks.append(dict(window=w['id'],engine=engine,volume_kl=volume,summary_mass_t=target,total_matching_factor=rho,factor_implied_by_engine=target/volume,residual_t_at_total_matching_factor=volume*rho-target))
pd.DataFrame(checks).to_csv(P/'hanbada_identifiability.csv',index=False)
assert len(result)==3456 and not result.duplicated(['start','horizon','lag','policy']).any()
assert abs(float(h['opening_rob'])-float(h['closing_rob'])-mass)<1e-9
(P/'manifest.json').write_text(json.dumps(dict(checkpoint_sha256=sha,eia_source_sha256=hashlib.sha256((R/'country-pilot/eia_monthly.csv').read_bytes()).hexdigest(),hanbada_original_sha256=h['source_sha256'],episodes=len(result),time_contract='one synthetic step per calendar day; monthly values held until next monthly bucket; assumed lags 1/2/3 months, NOT verified publication vintages',normalization='500 * lagged monthly price / first lagged price; clip250..850; FX1300; constant fuel .05',limitations=['Historical US residual fuel oil retail price, not port-specific bunker quote','Lagged values are proxy scenarios, not executable historical daily prices','Current downloaded historical vintage may include revisions','No future-month interpolation, but true historical release availability not established','Calendar mapping does not calibrate physical daily fuel or route duration','Quarterly windows may share price history; annual sensitivity is descriptive','Hanbada aggregate matching cannot identify density, reference conditions or period alignment'],training='none'),indent=2))
print(pd.DataFrame(pairs).to_string(index=False));print(pd.DataFrame(checks).to_string(index=False))
