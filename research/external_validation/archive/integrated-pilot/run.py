from pathlib import Path
import sys,hashlib,json
import numpy as np,pandas as pd,torch
P=Path(__file__).resolve().parent;R=P.parent/'bunkering-restore';sys.path.insert(0,str(R))
from envs.bunkering_env import BunkeringEnv
from scripts.baseline import FixedFuelingStrategy,PriceReactiveStrategy,SafeStockStrategy
from agents.dqn import DQNAgent
checkpoint=P/'dqn_final.pt';h=hashlib.sha256(checkpoint.read_bytes()).hexdigest();assert h=='970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392'
torch.set_num_threads(2);agent=DQNAgent.load_checkpoint(checkpoint,device='cpu');agent.policy_net.eval()
class DQN:
 name='double_dqn'
 def select_action(self,env,obs,step):
  with torch.no_grad():return int(agent.policy_net(torch.as_tensor(obs).unsqueeze(0)).argmax(1).item())
class Replay(BunkeringEnv):
 def __init__(self,path,**kw):self.path=path;super().__init__(**kw)
 def reset(self,**kw):
  _,info=super().reset(**kw)
  self._raw_fuel_price=float(self.path[0]);self._price_history.clear();self._price_history.append(self._raw_fuel_price);self._raw_fx_rate=1300.;self._state=self._observation();return self._state,info
 def _transition(self,state,action):
  # Delegate inventory, action and route transition to original implementation.
  obs,amount=super()._transition(state,action)
  self._price_history.pop();self._raw_fuel_price=float(self.path[self._step_count]);self._price_history.append(self._raw_fuel_price);self._raw_fx_rate=1300.
  return self._observation(),amount
prices=pd.read_csv(P.parent/'country-pilot/eia_monthly.csv');nom=pd.read_csv(P.parent/'country-pilot/brest/Maritime Routes and Tracklets/nomen.csv',sep='|');median=float(nom.length.median())
settings=[('original_30',30)]+[(x.route,int(np.ceil(30*x.length/median))) for x in nom.itertuples()]
rows=[];clip=[]
for route,n in settings:
 for start in [0,60,120,180,240]:
  source=prices.price_usd_gallon.iloc[start:start+n+1].to_numpy();assert len(source)==n+1
  mapped=500*source/source[0];path=np.clip(mapped,250,850);clip.append(dict(route=route,start=start,clipped=int((path!=mapped).sum()),count=len(path)))
  for kind in ['synthetic','eia_replay']:
   for policy in [FixedFuelingStrategy(),PriceReactiveStrategy(),SafeStockStrategy(),DQN()]:
    e=Replay(path,max_steps=n) if kind=='eia_replay' else BunkeringEnv(max_steps=n)
    o,_=e.reset(seed=820000+start);buy=0.;step=0;first=e._raw_fuel_price*e._raw_fx_rate
    while True:
     a=policy.select_action(e,o,step);o,r,done,trunc,info=e.step(a);buy+=info['actual_bunker_amount'];step+=1
     if done or trunc:break
    final=e._fuel_remaining;cost=info['cumulative_cost_index'];ok=info['voyage_success']
    rows.append(dict(route=route,max_steps=n,start=start,market=kind,policy=policy.name,success=ok,steps=step,purchased=buy,end_fuel=final,SCI=cost,adjusted_SCI=cost-final*e._raw_fuel_price*e._raw_fx_rate+first))
r=pd.DataFrame(rows);r.to_csv(P/'episodes.csv',index=False)
s=r.groupby(['market','policy']).agg(cases=('success','size'),success_rate=('success','mean'),SCI=('SCI','mean')).reset_index();s.to_csv(P/'summary.csv',index=False)
# Compare only matched successful episodes. Raw failed costs are not savings.
pairs=[]
for market,g in r.groupby('market'):
 a=g[g.policy=='safe_stock'].set_index(['route','start']);b=g[g.policy=='double_dqn'].set_index(['route','start']);ok=a.success&b.success
 pairs.append(dict(market=market,paired_success=int(ok.sum()),DQN_vs_safe_adjusted_change_pct=float((b.loc[ok,'adjusted_SCI'].mean()/a.loc[ok,'adjusted_SCI'].mean()-1)*100)))
(P/'manifest.json').write_text(json.dumps(dict(checkpoint_sha256=h,route_length_reference=median,settings=settings,starts=[0,60,120,180,240],price_mapping='500 * monthly_price / first_price, clipped 250..850; FX=1300 fixed on replay',limitations='monthly observations replayed on synthetic steps; route length ratio scales synthetic horizon, NOT real voyage clock or calibrated fuel consumption',pairs=pairs,clipping=clip),indent=2))
print(s.to_string(index=False));print(pairs)
