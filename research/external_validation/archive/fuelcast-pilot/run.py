from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
from threadpoolctl import threadpool_limits
OUT=Path(__file__).resolve().parent
speed=['Ship_SpeedOverGround']
full=speed+['Environment_SeaFloorDepth','Weather_Temperature2M','Weather_WindSpeed10M','Weather_WindDirection10M','Weather_WaveHeight','Weather_WaveDirection','Weather_WavePeriod','Weather_OceanCurrentVelocity','Weather_OceanCurrentDirection']
rows=[];protocol=[]
with threadpool_limits(limits=2):
 for p in sorted((OUT.parent/'feasibility').glob('*.parquet')):
  raw=pd.read_parquet(p); excluded_index=int(raw['index'].isna().sum())
  d=raw.dropna(subset=['index']).sort_values('index').reset_index(drop=True)
  assert d['index'].notna().all() and not d['index'].duplicated().any()
  n=len(d);a=int(n*.6);b=int(n*.8)
  # A 24h embargo in the documented 5-minute index units at each boundary.
  tr=d.iloc[:a];va=d.iloc[a:b];te=d.iloc[b:]
  tr=tr[tr['index']<d.iloc[a]['index']-288];va=va[va['index']<d.iloc[b]['index']-288]
  target='Consumer_Total_MomentaryFuel'
  assert not d[target].isna().any()
  y=tr[target];preds={'train_mean':np.full(len(te),y.mean())}
  protocol.append(dict(ship=p.stem,excluded_missing_index=excluded_index,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),train=len(tr),validation=len(va),test=len(te),index_ranges=[[float(x['index'].min()),float(x['index'].max())] for x in [tr,va,te]]))
  for name,cols in [('speed_only',speed),('speed_environment',full)]:
   best=None
   for leaves in [7,15]:
    m=HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=leaves,learning_rate=.08,l2_regularization=1,early_stopping=False,random_state=42)
    m.fit(tr[cols],y);loss=mean_absolute_error(va[target],np.maximum(0,m.predict(va[cols])))
    if best is None or loss<best[0]:best=(loss,m,leaves)
   preds[name]=np.maximum(0,best[1].predict(te[cols]))
  table=pd.DataFrame({'index':te['index'].values,'actual':te[target].values,**preds});table.to_csv(OUT/(p.stem+'_test_predictions.csv'),index=False)
  for name,pred in preds.items():
   rows.append(dict(ship=p.stem,model=name,test_n=len(te),MAE_kg_s=mean_absolute_error(te[target],pred),RMSE_kg_s=mean_squared_error(te[target],pred)**.5))
  print(p.stem,rows[-3:],flush=True)
pd.DataFrame(rows).to_csv(OUT/'metrics.csv',index=False)
(OUT/'protocol.json').write_text(json.dumps(dict(split='ordered index 60/20/20; 288 index-unit embargo; train-only fitting; validation selects 7 or 15 leaves; fixed test',features=full,ships=protocol),indent=2))
