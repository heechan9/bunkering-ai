"""Post-hoc condition audit of frozen candidates; no test-set threshold tuning."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import argparse, hashlib, json, zipfile
import numpy as np
import pandas as pd
import torch, joblib
from scipy.optimize import nnls
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
HERE=Path(__file__).resolve().parent
torch.set_num_threads(2)

def metrics(y,p,b,mask):
 n=int(mask.sum())
 if not n:return {'n':0}
 y,p,b=y[mask],p[mask],b[mask]
 a=float(np.mean(abs(y-p)));base=float(np.mean(abs(y-b)))
 return {'n':n,'mae':a,'baseline_mae':base,'improvement_pct':100*(1-a/base) if base else None,'bias':float(np.mean(p-y)),'p90_absolute_error':float(np.quantile(abs(y-p),.9))}

def support(tr,va,te,features):
 # Every-sixth eligible reference reduces immediate-neighbour optimism; train data only.
 ref=tr.iloc[::6][features];sc=StandardScaler().fit(ref)
 a=sc.transform(ref);nn=NearestNeighbors(n_neighbors=6).fit(a)
 threshold=float(np.quantile(nn.kneighbors(a)[0][:,5],.95))
 lo=tr[features].min().to_numpy();hi=tr[features].max().to_numpy()
 def apply(d):
  x=d[features].to_numpy();inside=((x>=lo)&(x<=hi)).all(axis=1)
  distance=nn.kneighbors(sc.transform(d[features]),n_neighbors=5)[0][:,4]
  return inside&(distance<=threshold),distance
 v,vd=apply(va);t,td=apply(te)
 return v,t,{'reference_rows':len(ref),'distance_threshold':threshold,'min':dict(zip(features,lo)),'max':dict(zip(features,hi))}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--hanbada',type=Path);args=ap.parse_args()
 source=HERE/'inputs/DataBioDataset1.zip'
 assert hashlib.sha256(source.read_bytes()).hexdigest()=='bafd4a5109f55ad4e9c61a1d87e992b4ae156c004871ea9ae077f5c01c08aaf9'
 oldpower=json.loads((HERE/'results/french_mlp_australia_adaptation.json').read_text())
 oldfuel=json.loads((HERE/'results/consumption_training.json').read_text())
 output=[];bins=[];daily=[];hashes={};availability=[]
 for ship in [1,3]:
  with zipfile.ZipFile(source) as z:
   with z.open(f'ship_{ship}.csv') as f:raw=pd.read_csv(f)
  raw.measurement_time=pd.to_datetime(raw.measurement_time);raw=raw.set_index('measurement_time').sort_index()
  availability.append({'ship':ship,'raw_rows':len(raw),'fields':{c:{'nonmissing':int(raw[c].notna().sum()),'unique':int(raw[c].nunique()),'zero':int((raw[c]==0).sum()),'min':float(raw[c].min()),'max':float(raw[c].max())} for c in ['wind_velocity','ship_wind_angle','draught_aft_side','draught_fore_side','Ship_SpeedLOG']}})
  for mode in ['power','fuel']:
   target='propeller_shaft_output' if mode=='power' else 'ME_FO_consumption'
   if mode=='power':
    x=raw[['Ship_SpeedLOG','draught_aft_side','draught_fore_side','wind_velocity','ship_wind_angle',target]].copy()
    rad=np.deg2rad(x.ship_wind_angle);x['wind_head']=x.wind_velocity*np.cos(rad);x['wind_cross']=x.wind_velocity*np.sin(rad);x['draft_mean']=(x.draught_aft_side+x.draught_fore_side)/2
    features=['Ship_SpeedLOG','draft_mean','wind_head','wind_cross'];count=x[['Ship_SpeedLOG',target]].resample('10min').count().min(axis=1)
    d=x[features+[target]].resample('10min').mean();d=d[(count>=48)&d.Ship_SpeedLOG.between(2,25)&(d[target]>0)].dropna()
    d['condition_wind']=np.hypot(d.wind_head,d.wind_cross);d['condition_draft']=d.draft_mean;fractions=(.72,.8)
   else:
    features=['Ship_SpeedLOG','draught_aft_side','draught_fore_side','wind_velocity','ship_wind_angle']
    x=raw[[target]+features].copy();count=x[['Ship_SpeedLOG',target]].resample('10min').count().min(axis=1);d=x.resample('10min').mean();d=d[(count>=48)&d.Ship_SpeedLOG.between(2,25)&(d[target]>0)].copy()
    d['condition_wind']=d.wind_velocity;d['condition_draft']=(d.draught_aft_side+d.draught_fore_side)/2;fractions=(.70,.85)
   span=d.index.max()-d.index.min();a=d.index.min()+span*fractions[0];b=d.index.min()+span*fractions[1];gap=pd.Timedelta('1h')
   tr=d[d.index<a-gap];va=d[(d.index>=a+gap)&(d.index<b-gap)];te=d[d.index>=b+gap]
   assert np.isfinite(tr[features]).all().all() and np.isfinite(va[features]).all().all() and np.isfinite(te[features]).all().all()
   coef=nnls(np.column_stack([np.ones(len(tr)),tr.Ship_SpeedLOG**3]),tr[target])[0]
   base=lambda q:coef[0]+coef[1]*q.Ship_SpeedLOG.to_numpy()**3
   val_support,test_support,domain=support(tr,va,te,features)
   for seed in ([42,43,44] if mode=='power' else [42]):
    modelpath=HERE/'models'/(f'french_basic_adapted_ship{ship}_seed{seed}.pt' if mode=='power' else f'ship_{ship}_candidate.joblib')
    hashes[modelpath.name]=hashlib.sha256(modelpath.read_bytes()).hexdigest()
    if mode=='power':
     ck=torch.load(modelpath,map_location='cpu',weights_only=False) # Locally generated, trusted artifact.
     net=torch.nn.Sequential(torch.nn.Linear(4,512),torch.nn.ReLU(),torch.nn.Linear(512,1));net.load_state_dict(ck['state_dict']);net.eval()
     def predict(q):
      with torch.no_grad():return net(torch.tensor((q[features].to_numpy()-ck['scaler_mean'])/ck['scaler_scale'],dtype=torch.float32)).numpy().ravel()*ck['std']+ck['mean']
     expected=next(s for s in oldpower['ships'] if s['ship']==ship);expected_mae=next(s['mae_kW'] for s in expected['runs'] if s['seed']==seed)
    else:
     ck=joblib.load(modelpath)
     def predict(q):return np.maximum(0,base(q)+ck['residual_model'].predict(q[features]))
     expected=next(s for s in oldfuel['ships'] if s['ship']==ship);expected_mae=expected['metrics']['speed_cubed_residual_ml']['mae_L_h']
    yp=predict(te);yv=predict(va);truth=te[target].to_numpy();vt=va[target].to_numpy();baseline=base(te)
    overall=metrics(truth,yp,baseline,np.ones(len(te),bool));assert abs(overall['mae']-expected_mae)<1e-4,(ship,mode,overall,expected_mae)
    vm=metrics(vt,yv,base(va),val_support)
    # Fixed audit criterion, selected without test labels; research triage only.
    validation_pass=vm['n']>=30 and vm['improvement_pct']>0
    accepted=test_support&validation_pass
    q90=float(np.quantile(abs(vt-yv),.9,method='higher'))
    record={'ship':ship,'mode':mode,'seed':seed,'unit':'kW' if mode=='power' else 'L/h','split_counts':{'train':len(tr),'validation':len(va),'test':len(te)},'overall':overall,'train_domain':domain,'validation_supported':vm,'validation_gate_pass':bool(validation_pass),'test_supported':metrics(truth,yp,baseline,test_support),'test_outside_support':metrics(truth,yp,baseline,~test_support),'accepted':metrics(truth,yp,baseline,accepted),'accepted_fraction':float(accepted.mean()),'validation_abs_error_q90':q90,'test_interval_coverage':float(np.mean(abs(truth-yp)<=q90))};output.append(record)
    for field in ['Ship_SpeedLOG','condition_draft','condition_wind']:
     cuts=np.unique(np.quantile(tr[field],[.25,.5,.75]));labels=np.digitize(te[field],cuts,right=True)
     for n in range(len(cuts)+1):
      m=metrics(truth,yp,baseline,labels==n);bins.append({'ship':ship,'mode':mode,'seed':seed,'condition':field,'bin':n,'lower':float(cuts[n-1]) if n else None,'upper':float(cuts[n]) if n<len(cuts) else None,**m,'small_n':m['n']<20})
    dates=te.index.date
    for date in np.unique(dates):daily.append({'ship':ship,'mode':mode,'seed':seed,'date':str(date),**metrics(truth,yp,baseline,dates==date)})
 result={'status':'posthoc_diagnostic_not_operating_gate','rules':'Training quartiles for condition bins; training min/max plus5-NN distance95th percentile on every-sixth eligible training reference; validation supported n>=30 and MAE better than cubic required. No test thresholds tuned.','data_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'model_sha256':hashes,'models':output,'raw_feature_availability':availability,'limitations':['Both ships wind speed/direction are all zero; this does not establish true calm weather. Ship3 draught is constant. Weather response and ship3 draught response cannot be validated.', 'Same previously examined holdout: exploratory post-hoc audit, not new independent validation.','Autocorrelated10min blocks and few voyage days; no confidence or safety guarantee.','Validation90% absolute-error interval is heuristic, not guaranteed conformal coverage under drift.','Consumption candidate retains original arithmetic mean wind angle; diagnostic does not repair it.','Power wind bins use magnitude of mean wind components; fuel bins use mean wind speed, so bins are not interchangeable.','Nearest-neighbour support thresholds are research heuristics, not a deployment authorization.']}
 if args.hanbada:
  import openpyxl
  assert hashlib.sha256(args.hanbada.read_bytes()).hexdigest()=='eaf7945109e2675ba8dbd6716d357f4babe737c6f36195f3a8f4da8c21af6665'
  s=openpyxl.load_workbook(args.hanbada,data_only=True)['B FOAM'];rows=[]
  for row in range(8,69,2):
   day,h,v,me=[s.cell(row,c).value for c in [1,8,10,20]]
   if all(isinstance(x,(int,float)) for x in [day,h,v,me]) and h==24 and v>0 and me>0 and day!=31:rows.append((day,v,me*1000/h))
  z=np.array(rows);train=z[:4];test=z[4:];low,high=train[:,1].min(),train[:,1].max();inside=(test[:,1]>=low)&(test[:,1]<=high)
  result['hanbada']={'selected_days':len(rows),'train_n':4,'test_n':3,'train_speed_range':[float(low),float(high)],'test_speed_supported_n':int(inside.sum()),'test_speed_outside_n':int((~inside).sum()),'full_feature_gate':'not_evaluable_without_aligned_wind_draught_STW','decision':'seven_daily_rows_insufficient_for_validated_rejection_rule'}
 out=HERE/'results/condition_diagnostics';out.mkdir(exist_ok=True)
 for r in output:
  for field in ['Ship_SpeedLOG','condition_draft','condition_wind']:
   assert sum(x['n'] for x in bins if x['ship']==r['ship'] and x['mode']==r['mode'] and x['seed']==r['seed'] and x['condition']==field)==r['overall']['n']
  assert r['test_supported']['n']+r['test_outside_support']['n']==r['overall']['n']
 (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');pd.DataFrame(bins).to_csv(out/'condition_bins.csv',index=False);pd.DataFrame(daily).to_csv(out/'daily_errors.csv',index=False)
 for r in output:print(r['ship'],r['mode'],r['seed'],'overall',round(r['overall']['improvement_pct'],2),'valpass',r['validation_gate_pass'],'support',r['test_supported']['n'],'accepted',r['accepted'],flush=True)
 print('hanbada',result.get('hanbada'))
if __name__=='__main__':main()
