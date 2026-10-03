from pathlib import Path
import sys
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'fuelcast-retrain'))
from run import StrictEnv,DQNAgent,CK,SafeStockStrategy
agent=DQNAgent.load_checkpoint(CK,device='cpu');rows=[]
for pct in [58,59,60]:
 for horizon in [30,43]:
  for seed in range(42,62):
   for policy in ['original_dqn','safe_stock']:
    e=StrictEnv(np.full(horizon,.05*(1+pct/100)),horizon);o,_=e.reset(seed=seed)
    for step in range(horizon):
     a=agent.greedy_action(o) if policy=='original_dqn' else SafeStockStrategy().select_action(e,o,step)
     o,_,done,trunc,info=e.step(a)
     if done or trunc:break
    rows.append(dict(power_increase_pct=pct,horizon=horizon,seed=seed,policy=policy,success=info['voyage_success']))
r=pd.DataFrame(rows);r.to_csv(P/'local_uncertainty.csv',index=False);print(r.groupby(['power_increase_pct','policy']).success.mean())
