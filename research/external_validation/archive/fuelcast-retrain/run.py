from pathlib import Path
import sys,json,random,hashlib,time
import numpy as np,pandas as pd,torch
P=Path(__file__).resolve().parent;R=P.parent
sys.path.insert(0,str(R/'bunkering-restore'))
from envs.bunkering_env import BunkeringEnv
from agents.dqn import DQNAgent,ReplayBuffer
from scripts.baseline import SafeStockStrategy
torch.set_num_threads(1)
CK=R/'integrated-pilot/dqn_final.pt'
assert hashlib.sha256(CK.read_bytes()).hexdigest()=='970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392'

class StrictEnv(BunkeringEnv):
 def __init__(self,demands,horizon):
  self.demands=demands;super().__init__(max_steps=horizon)
 def step(self,action):
  need=float(self.demands[self._step_count]);available=self._fuel_remaining
  self.fuel_consumption_per_step=need
  shortage=max(0.,need-available)
  # Consumption precedes bunkering. On a shortfall no impossible rescue purchase.
  o,_,done,trunc,info=super().step(0 if shortage>1e-9 else action)
  if shortage>1e-9:
   done=True;trunc=False;info['voyage_success']=False;info['end_reason']='pre_refill_shortage'
  info['shortage']=shortage
  reward=-info['step_cost_index']/650000.
  if done or trunc:
   reward+=self._fuel_remaining*self._raw_fuel_price*self._raw_fx_rate/650000.
   if not info['voyage_success']:reward-=50.
  return o,reward,done,trunc,info

def prepare():
 splits={k:[] for k in ['train','validation','test']};meta=[]
 protocol=json.loads((R/'fuelcast-pilot/protocol.json').read_text())
 for rec in protocol['ships']:
  f=R/'feasibility'/f"{rec['ship']}.parquet"
  assert hashlib.sha256(f.read_bytes()).hexdigest()==rec['sha256']
  d=pd.read_parquet(f,columns=['index','Consumer_Total_MomentaryFuel']).dropna(subset=['index']).sort_values('index')
  train=d[d['index'].between(*rec['index_ranges'][0])]
  mean=float(train.Consumer_Total_MomentaryFuel.mean())
  for split,bounds in zip(splits,rec['index_ranges']):
   sub=d[d['index'].between(*bounds)]
   for start in range(0,len(sub)-287,288):
    w=sub.iloc[start:start+288]
    if not np.all(np.diff(w['index'])==1):continue
    demands=.05*w.Consumer_Total_MomentaryFuel.to_numpy()[:43]/mean
    assert np.isfinite(demands).all() and (demands>=0).all()
    splits[split].append((rec['ship'],int(w['index'].iloc[0]),demands))
   meta.append(dict(ship=rec['ship'],split=split,bounds=bounds,train_mean=mean,blocks=sum(x[0]==rec['ship'] for x in splits[split])))
 (P/'splits.json').write_text(json.dumps(meta,indent=2))
 return splits

def evaluate(agent,blocks,seeds,label):
 rows=[]
 for ship,start,demands in blocks:
  for horizon in [30,43]:
   for seed in seeds:
    e=StrictEnv(demands,horizon);o,_=e.reset(seed=seed);initial=e._raw_fuel_price*e._raw_fx_rate
    for step in range(horizon):
     a=agent.greedy_action(o) if agent else SafeStockStrategy().select_action(e,o,step)
     o,_,done,trunc,info=e.step(a)
     if done or trunc:break
    rows.append(dict(policy=label,ship=ship,start=start,horizon=horizon,price_seed=seed,success=info['voyage_success'],steps=step+1,SCI=info['cumulative_cost_index'],adjusted_SCI=info['cumulative_cost_index']-e._fuel_remaining*e._raw_fuel_price*e._raw_fx_rate+initial,end_reason=info['end_reason']))
 return pd.DataFrame(rows)

def main():
 splits=prepare();logs=[];vals=[];selected=[]
 # Regression checks: shortage must fail before refill; sufficient fuel may refill.
 e=StrictEnv(np.full(43,.2),30);e.reset(seed=1);e._fuel_remaining=.1;e._state=e._observation()
 _,_,done,_,info=e.step(1);assert done and not info['voyage_success'] and info['actual_bunker_amount']==0
 e=StrictEnv(np.full(43,.05),30);e.reset(seed=1);e._fuel_remaining=.1;e._state=e._observation()
 _,_,done,_,info=e.step(1);assert not done and info['actual_bunker_amount']>0
 # Predeclared: three seeds, 1500 episodes, validation every 500, no test selection.
 for seed in [41,42,43]:
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  agent=DQNAgent.load_checkpoint(CK,device='cpu')
  agent.optimizer=torch.optim.Adam(agent.policy_net.parameters(),lr=1e-4)
  buffer=ReplayBuffer(100000);step_count=0;best=None
  rng=np.random.default_rng(seed)
  ships=sorted(set(x[0] for x in splits['train']))
  groups={s:[x for x in splits['train'] if x[0]==s] for s in ships}
  for ep in range(1,1501):
   ship=ships[int(rng.integers(len(ships)))];group=groups[ship];_,_,demands=group[int(rng.integers(len(group)))]
   horizon=int(rng.choice([30,43]));e=StrictEnv(demands,horizon);o,_=e.reset(seed=seed*100000+ep);total=0.
   for t in range(horizon):
    eps=max(.05,.5-.45*step_count/40000);a=agent.select_action(o,eps)
    nxt,reward,done,trunc,info=e.step(a);buffer.push(o,a,reward,nxt,terminated=done)
    step_count+=1
    if len(buffer)>=256 and step_count%4==0:
     loss=agent.update(buffer.sample(64));assert np.isfinite(loss)
    if step_count%500==0:agent.sync_target_network()
    o=nxt;total+=reward
    if done or trunc:break
   logs.append(dict(seed=seed,episode=ep,steps=step_count,reward=total,success=info['voyage_success']))
   if ep%500==0:
    v=evaluate(agent,splits['validation'],[720000,720001],f'seed{seed}_ep{ep}')
    # Equal ship weighting. Failures first; cost only among successful validation cases.
    rate=float(v.groupby('ship').success.mean().mean());cost=float(v[v.success].groupby('ship').adjusted_SCI.mean().mean()) if v.success.any() else float('inf')
    score=(rate,-cost);vals.append(dict(seed=seed,episode=ep,macro_success=rate,successful_adjusted_cost=cost))
    if best is None or score>best:
     best=score;agent.save_checkpoint(P/f'retrained_seed{seed}.pt',metadata=dict(seed=seed,episode=ep,selection='validation macro success then successful adjusted SCI',experimental=True))
    print(f'seed={seed} episode={ep} validation_success={rate:.4f} adjusted_cost={cost:.1f}',flush=True)
  selected.append(DQNAgent.load_checkpoint(P/f'retrained_seed{seed}.pt',device='cpu'))
 pd.DataFrame(logs).to_csv(P/'training_log.csv',index=False);pd.DataFrame(vals).to_csv(P/'validation.csv',index=False)
 # Test seen in earlier pilot: reused holdout, not a new untouched external validation.
 frames=[evaluate(DQNAgent.load_checkpoint(CK,device='cpu'),splits['test'],list(range(820000,820005)),'original_dqn'),evaluate(None,splits['test'],list(range(820000,820005)),'safe_stock')]
 for seed,agent in zip([41,42,43],selected):frames.append(evaluate(agent,splits['test'],list(range(820000,820005)),f'retrained_seed{seed}'))
 result=pd.concat(frames,ignore_index=True);result.to_csv(P/'test_episodes.csv',index=False)
 summary=result.groupby(['policy','ship','horizon']).agg(cases=('success','size'),success_rate=('success','mean')).reset_index();summary.to_csv(P/'summary.csv',index=False)
 pairs=[]
 for policy in result.policy.unique():
  if policy=='original_dqn':continue
  for horizon in [30,43]:
   a=result[(result.policy=='original_dqn')&(result.horizon==horizon)].set_index(['ship','start','price_seed'])
   b=result[(result.policy==policy)&(result.horizon==horizon)].set_index(['ship','start','price_seed']);ok=a.success&b.success
   pairs.append(dict(policy=policy,horizon=horizon,paired_success=int(ok.sum()),cases=len(a),raw_cost_change_pct=100*(b.loc[ok,'SCI'].mean()/a.loc[ok,'SCI'].mean()-1),adjusted_cost_change_pct=100*(b.loc[ok,'adjusted_SCI'].mean()/a.loc[ok,'adjusted_SCI'].mean()-1)))
 pd.DataFrame(pairs).to_csv(P/'paired_vs_original.csv',index=False)
 (P/'manifest.json').write_text(json.dumps(dict(training='warm-start original weights; fresh Adam; 3 seeds; 1500 episodes each; 4-step updates; 500-step target sync; 6 original observations; uniform ship sampling',reward='-purchase SCI/650000; terminal stock credit/650000; failure penalty -50',selection=vals,original_sha256=hashlib.sha256(CK.read_bytes()).hexdigest(),limitations=['synthetic tank and route steps','reward and termination changed together with training data; no data-only causal ablation','ONS contextual only; not learned input','reused holdout previously examined; new blind validation required before official adoption','price seeds not independent fuel traces'],versions=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,pandas=pd.__version__)),indent=2))
 print(summary.to_string(index=False));print(pd.DataFrame(pairs).to_string(index=False))
if __name__=='__main__':main()
