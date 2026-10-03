from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent;R=P.parent
sys.path.insert(0,str(R/'fuelcast-retrain'))
from run import StrictEnv,DQNAgent,CK,SafeStockStrategy
agent=DQNAgent.load_checkpoint(CK,device='cpu')
# Approximate visual read of purple PE bars in Figure S7, rounded to integer pp.
cases=dict(zip(['S10','S20','S40','S50','M10','M20','M40','M50','B10','B20'],[15,25,39,43,28,41,59,63,43,63]))
rows=[];inputs=[]
for name,delta in [('smooth',0)]+list(cases.items()):
 for aux in ([0.] if name=='smooth' else [0.,.3,.6]):
  multiplier=1+(1-aux)*delta/100
  inputs.append(dict(case=name,approx_effective_power_increase_pct=delta,auxiliary_share_assumption=aux,fuel_multiplier_assumption=multiplier))
  for horizon in [30,43]:
   for seed in range(42,62):
    for policy in ['original_dqn','safe_stock']:
     e=StrictEnv(np.full(horizon,.05*multiplier),horizon);o,_=e.reset(seed=seed);initial=e._raw_fuel_price*e._raw_fx_rate
     for t in range(horizon):
      a=agent.greedy_action(o) if policy=='original_dqn' else SafeStockStrategy().select_action(e,o,t)
      o,_,done,trunc,info=e.step(a)
      if done or trunc:break
     rows.append(dict(case=name,aux=aux,multiplier=multiplier,horizon=horizon,seed=seed,policy=policy,success=info['voyage_success'],SCI=info['cumulative_cost_index'],adjusted_SCI=info['cumulative_cost_index']-e._fuel_remaining*e._raw_fuel_price*e._raw_fx_rate+initial))
r=pd.DataFrame(rows);r.to_csv(P/'episodes.csv',index=False)
s=r.groupby(['case','aux','multiplier','horizon','policy']).agg(cases=('success','size'),success_rate=('success','mean'),SCI=('SCI','mean'),adjusted_SCI=('adjusted_SCI','mean')).reset_index();s.to_csv(P/'summary.csv',index=False)
pd.DataFrame(inputs).to_csv(P/'scenario_assumptions.csv',index=False)
assert len(r)==2480 and not r.duplicated(['case','aux','horizon','seed','policy']).any()
f=P/'supplement.pdf';meta=json.loads((P/'figshare.json').read_text());assert hashlib.md5(f.read_bytes()).hexdigest()==meta['files'][0]['computed_md5']
(P/'manifest.json').write_text(json.dumps(dict(pdf_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source='https://api.figshare.com/v2/articles/5472880',license='CC BY 4.0',figure='S7, PDF page 7, 180m bulk carrier',extraction='manual approximate purple bar heights rounded to integer percentage points; not exact source data; uncertainty unquantified',mapping='fuel_multiplier = 1 + (1-auxiliary_share)*PE_increase/100; assumes unchanged speed, propulsion efficiency and propulsion SFC; fixed auxiliary load',limitations=['not measured fuel consumption','auxiliary fractions are assumptions, not dataset estimates','one ship figure only','no digitization-uncertainty sweep','synthetic normalized fuel and route horizon','no retraining or official model replacement'],episodes=len(r)),indent=2))
print(s.groupby('policy').success_rate.agg(['min','max']).to_string());print(r.groupby('policy').success.mean())
