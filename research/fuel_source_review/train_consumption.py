"""Exploratory measured main-engine consumption prediction; no savings claim."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import zipfile,json,hashlib,platform
import numpy as np,pandas as pd,joblib,sklearn
from scipy.optimize import nnls
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
HERE=Path(__file__).resolve().parent
(HERE/'models').mkdir(exist_ok=True)
(HERE/'results').mkdir(exist_ok=True)
FEATURES=['Ship_SpeedLOG','draught_aft_side','draught_fore_side','wind_velocity','ship_wind_angle']
summary=[]
with zipfile.ZipFile(HERE/'inputs/DataBioDataset1.zip') as z:
 for ship in (1,3):
  with z.open(f'ship_{ship}.csv') as f:
   raw=pd.read_csv(f,usecols=['measurement_time','ME_FO_consumption']+FEATURES)
  raw['measurement_time']=pd.to_datetime(raw.measurement_time,errors='raise')
  raw=raw.set_index('measurement_time').sort_index()
  for c in raw:raw[c]=pd.to_numeric(raw[c],errors='coerce')
  counts=raw[['ME_FO_consumption','Ship_SpeedLOG']].resample('10min').count().min(axis=1)
  d=raw.resample('10min').mean()
  d=d[(counts>=48)&(d.ME_FO_consumption>0)&(d.Ship_SpeedLOG>=2)&(d.Ship_SpeedLOG<=25)].copy()
  # Chronological wall-clock boundaries; remove adjacent one-hour windows.
  span=d.index.max()-d.index.min();a=d.index.min()+span*.70;b=d.index.min()+span*.85
  gap=pd.Timedelta('1h')
  tr=d[d.index<a-gap];va=d[(d.index>=a+gap)&(d.index<b-gap)];te=d[d.index>=b+gap]
  assert len(tr)>100 and len(va)>20 and len(te)>20
  assert tr.index.max()<va.index.min()<te.index.min()
  def design(x):return np.column_stack([np.ones(len(x)),x.Ship_SpeedLOG.to_numpy()**3])
  coef=nnls(design(tr),tr.ME_FO_consumption.to_numpy())[0]
  def base(x):return design(x)@coef
  # Residual ML uses only speed, draught and wind; no shaft/output/fuel-derived inputs.
  fits=[]
  for leaves in (7,15):
   model=HistGradientBoostingRegressor(max_leaf_nodes=leaves,max_iter=150,learning_rate=.05,min_samples_leaf=30,l2_regularization=10,early_stopping=False,random_state=42)
   model.fit(tr[FEATURES],tr.ME_FO_consumption-base(tr))
   pred=np.maximum(0,base(va)+model.predict(va[FEATURES]))
   fits.append((mean_absolute_error(va.ME_FO_consumption,pred),leaves,model))
  _,leaves,model=min(fits,key=lambda q:q[0])
  predictions={'train_mean':np.repeat(tr.ME_FO_consumption.mean(),len(te)),'nonnegative_speed_cubed':base(te),'speed_cubed_residual_ml':np.maximum(0,base(te)+model.predict(te[FEATURES]))}
  metrics={}
  for name,pred in predictions.items():
   y=te.ME_FO_consumption.to_numpy()
   metrics[name]={'mae_L_h':float(mean_absolute_error(y,pred)),'rmse_L_h':float(np.sqrt(mean_squared_error(y,pred))),'r2':float(r2_score(y,pred)),'predicted_volume_bias_pct':float(100*(pred.sum()/y.sum()-1))}
  result={'ship':ship,'raw_rows':len(raw),'eligible_10min_blocks':len(d),'split_counts':{'train':len(tr),'validation':len(va),'test':len(te)},'split_ranges':{k:[str(v.index.min()),str(v.index.max())] for k,v in [('train',tr),('validation',va),('test',te)]},'features':FEATURES,'target':'ME_FO_consumption L/h','speed':'SpeedLOG water-relative; no cross-ship mixing','cubic_coefficients':coef.tolist(),'chosen_leaves':leaves,'metrics':metrics,'hybrid_mae_improvement_vs_cubic_pct':100*(1-metrics['speed_cubed_residual_ml']['mae_L_h']/metrics['nonnegative_speed_cubed']['mae_L_h'])}
  summary.append(result)
  joblib.dump({'cubic_coefficients':coef,'residual_model':model,'features':FEATURES,'target_unit':'L/h','ship':ship},HERE/f'models/ship_{ship}_candidate.joblib')
  out=te[['ME_FO_consumption']].copy()
  for k,v in predictions.items():out[k]=v
  out.to_csv(HERE/f'results/ship_{ship}_heldout_predictions.csv')
  print(json.dumps(result),flush=True)
metadata={'status':'trained_external_candidates_not_adopted','python':platform.python_version(),'sklearn':sklearn.__version__,'input_sha256':hashlib.sha256((HERE/'inputs/DataBioDataset1.zip').read_bytes()).hexdigest(),'ships':summary,'limitations':['Simplified speed-cubed residual ML is not a reproduction of French CFD/MLP method.','Fishing vessel measured consumption predicts observations, not causal policy savings.','10min blocks require >=48 paired observations; retain positive fuel and >=2kn mean speed, not verified transit.','Hanbada transfer is reviewed separately on seven daily blocks; no vessel-independent transfer validation.','No DQN retraining or operating-model replacement.']}
(HERE/'results/consumption_training.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
