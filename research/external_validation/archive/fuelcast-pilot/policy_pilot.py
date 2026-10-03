from pathlib import Path
import numpy as np,pandas as pd,json
P=Path(__file__).resolve().parent
rng=np.random.default_rng(20261003);rows=[]
# Fixed protocol: 24h episodes, ports every 6h, 24h tank, common 3h reserve.
# Forecast ablation: supplied future operational/weather features, not future fuel labels.
for f in sorted(P.glob('*_test_predictions.csv')):
 d=pd.read_csv(f);ship=f.name.split('_test')[0];rate=float(d.train_mean.iloc[0]);unit=300.;cap=rate*unit*288;reserve=rate*unit*36
 # Only strictly consecutive, disjoint 288-step sequences; omit gaps rather than invent time.
 windows=[]
 for start in range(0,len(d)-287,288):
  w=d.iloc[start:start+288]
  if np.all(np.diff(w['index'])==1):windows.append(w)
 for k,w in enumerate(windows):
  actual=w.actual.to_numpy()*unit
  for scenario in range(20):
   price=np.clip(600*np.exp(rng.normal(0,.12,5)),350,1000)/1000 # synthetic USD/kg
   for model in ['train_mean','speed_only','speed_environment']:
    forecast=w[model].to_numpy()*unit;stock=reserve;cost=0.;unserved=0.;volume=0.
    for t in range(288):
     if t%72==0:
      target=min(cap,float(forecast[t:t+72].sum())+reserve)
      buy=max(0,target-stock);stock+=buy;cost+=buy*price[t//72];volume+=buy
     need=actual[t];unserved+=max(0,need-stock);stock=max(0,stock-need)
    rows.append(dict(ship=ship,window=k,scenario=scenario,model=model,spend=cost,purchased_kg=volume,shortage_kg=unserved,success=unserved<1e-8,end_stock_kg=stock,inventory_adjusted_cost=cost-stock*price[-1]+reserve*price[0]))
 if not windows: print(ship,'NO CONTIGUOUS WINDOWS')
r=pd.DataFrame(rows);r.to_csv(P/'policy_episodes.csv',index=False)
a=r.groupby(['ship','model']).agg(cases=('success','size'),success_rate=('success','mean'),mean_shortage_kg=('shortage_kg','mean'),mean_spend=('spend','mean'),mean_inventory_adjusted_cost=('inventory_adjusted_cost','mean')).reset_index();a.to_csv(P/'policy_summary.csv',index=False)
print(a.to_string(index=False))
# Cost comparisons restricted to identical cases where both policies delivered all demand.
b=[]
for ship,g in r.groupby('ship'):
 for baseline in ['train_mean','speed_only']:
  x=g[g.model==baseline].set_index(['window','scenario']);y=g[g.model=='speed_environment'].set_index(['window','scenario']);ok=x.success&y.success
  b.append(dict(ship=ship,baseline=baseline,total_cases=len(x),paired_success_cases=int(ok.sum()),cost_change_pct=(y.loc[ok,'inventory_adjusted_cost'].mean()/x.loc[ok,'inventory_adjusted_cost'].mean()-1)*100 if ok.any() else None))
(P/'policy_paired_comparison.json').write_text(json.dumps(b,indent=2));print(b)
