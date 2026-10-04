"""French basic MLP architecture adapted to DataBio; no CFD reproduction."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import zipfile,json,copy,hashlib
import numpy as np,pandas as pd,torch
from scipy.optimize import nnls
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error,r2_score
HERE=Path(__file__).resolve().parent;torch.set_num_threads(2)
assert hashlib.sha256((HERE/'inputs/DataBioDataset1.zip').read_bytes()).hexdigest() == 'bafd4a5109f55ad4e9c61a1d87e992b4ae156c004871ea9ae077f5c01c08aaf9'
(HERE/'models').mkdir(exist_ok=True)
(HERE/'results').mkdir(exist_ok=True)
results=[];scenarios=[]
au=pd.read_csv(HERE.parent/'canada_anchorage/inputs/australia_waterline71_original_cells.csv');print(au.columns.tolist(),flush=True)
for ship in (1,3):
 with zipfile.ZipFile(HERE/'inputs/DataBioDataset1.zip') as z:
  with z.open(f'ship_{ship}.csv') as f:d=pd.read_csv(f,usecols=['measurement_time','Ship_SpeedLOG','draught_aft_side','draught_fore_side','wind_velocity','ship_wind_angle','propeller_shaft_output'])
 d['measurement_time']=pd.to_datetime(d.measurement_time);d=d.set_index('measurement_time').sort_index()
 count=d[['Ship_SpeedLOG','propeller_shaft_output']].resample('10min').count().min(axis=1)
 # Circular direction handled before averaging.
 rad=np.deg2rad(d.ship_wind_angle);d['wind_head']=d.wind_velocity*np.cos(rad);d['wind_cross']=d.wind_velocity*np.sin(rad)
 d['draft_mean']=(d.draught_aft_side+d.draught_fore_side)/2
 features=['Ship_SpeedLOG','draft_mean','wind_head','wind_cross'];d=d[features+['propeller_shaft_output']].resample('10min').mean()
 d=d[(count>=48)&(d.Ship_SpeedLOG>=2)&(d.Ship_SpeedLOG<=25)&(d.propeller_shaft_output>0)].dropna()
 span=d.index.max()-d.index.min();a=d.index.min()+span*.72;b=d.index.min()+span*.8;gap=pd.Timedelta('1h')
 tr=d[d.index<a-gap];va=d[(d.index>=a+gap)&(d.index<b-gap)];te=d[d.index>=b+gap]
 assert tr.index.max()<va.index.min()<te.index.min()
 scaler=StandardScaler().fit(tr[features]);mean=tr.propeller_shaft_output.mean();std=tr.propeller_shaft_output.std()
 xt=torch.tensor(scaler.transform(tr[features]),dtype=torch.float32);yt=torch.tensor(((tr.propeller_shaft_output-mean)/std).to_numpy(),dtype=torch.float32)[:,None]
 xv=torch.tensor(scaler.transform(va[features]),dtype=torch.float32);yv=torch.tensor(((va.propeller_shaft_output-mean)/std).to_numpy(),dtype=torch.float32)[:,None]
 coef=nnls(np.column_stack([np.ones(len(tr)),tr.Ship_SpeedLOG**3]),tr.propeller_shaft_output)[0]
 base=lambda x:coef[0]+coef[1]*x.Ship_SpeedLOG.to_numpy()**3
 models=[];runs=[]
 for seed in (42,43,44):
  torch.manual_seed(seed);np.random.seed(seed)
  net=torch.nn.Sequential(torch.nn.Linear(4,512),torch.nn.ReLU(),torch.nn.Linear(512,1))
  opt=torch.optim.Adam(net.parameters(),lr=.001,weight_decay=.0001);scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=150)
  best=float('inf');state=None;bad=0;bestepoch=0
  for epoch in range(150):
   net.train();order=torch.randperm(len(xt))
   for ids in order.split(256):
    opt.zero_grad();loss=((net(xt[ids])-yt[ids])**2).mean();loss.backward();opt.step()
   scheduler.step();net.eval()
   with torch.no_grad():vl=((net(xv)-yv)**2).mean().item()
   if vl<best:best=vl;state=copy.deepcopy(net.state_dict());bad=0;bestepoch=epoch+1
   else:bad+=1
   if bad>=20:break
  net.load_state_dict(state);net.eval()
  def predict(x):
   with torch.no_grad():return net(torch.tensor(scaler.transform(x[features]),dtype=torch.float32)).numpy().ravel()*std+mean
  yp=predict(te);truth=te.propeller_shaft_output.to_numpy()
  run={'seed':seed,'epochs_run':epoch+1,'best_epoch':bestepoch,'validation_mse_standardized':best,'mae_kW':float(mean_absolute_error(truth,yp)),'r2':float(r2_score(truth,yp)),'negative_test_predictions':int((yp<0).sum()),'mae_improvement_vs_cubic_pct':float(100*(1-mean_absolute_error(truth,yp)/mean_absolute_error(truth,base(te))))};runs.append(run)
  torch.save({'state_dict':state,'features':features,'mean':mean,'std':std,'scaler_mean':scaler.mean_,'scaler_scale':scaler.scale_},HERE/f'models/french_basic_adapted_ship{ship}_seed{seed}.pt')
  # Hypothetical Australian delay + speed recovery. No geographic mapping to DataBio ship.
  context=tr[features].median().to_dict()
  def power(v):
   x=pd.DataFrame([{**context,'Ship_SpeedLOG':v}]);return float(predict(x)[0])
  p10=power(10);p12=power(12)
  delays=au.anchor_share_pct/100*au.mean_anchor_hours
  for slack in [0,12,24,48]:
   for hotel_fraction in [0,.1,.3]:
    vals=[];late=0;invalid=0
    for delay in delays:
     deadline=100+slack;remaining=deadline-delay
     speed=10 if remaining>=100 else min(12,1000/max(remaining,1e-9))
     hours=1000/speed;late+=int(hours+delay>deadline+1e-9)
     power_value=power(speed);invalid+=int(power_value<=0 or p10<=0)
     if power_value>0 and p10>0:
      # Both alternatives have same waiting delay; constant hotel load throughout.
      fixed=p10*100+hotel_fraction*p10*(100+delay)
      adaptive=power_value*hours+hotel_fraction*p10*(hours+delay)
      vals.append(100*(adaptive/fixed-1))
    scenarios.append({'ship':ship,'seed':seed,'slack_h':slack,'assumed_hotel_fraction_of_P10':hotel_fraction,'macro_mean_energy_change_pct':float(np.mean(vals)) if vals else None,'late_cases':late,'cases':len(delays),'invalid_power_cases':invalid,'P12_over_P10':p12/p10,'speed10_12_within_train_range':bool(tr.Ship_SpeedLOG.min()<=10 and tr.Ship_SpeedLOG.max()>=12)})
  models.append(net)
 out={'ship':ship,'eligible_blocks':len(d),'split_counts':{'train':len(tr),'validation':len(va),'test':len(te)},'features':features,'target':'measured propeller_shaft_output kW','cubic_baseline_mae_kW':float(mean_absolute_error(te.propeller_shaft_output,base(te))),'cubic_baseline_r2':float(r2_score(te.propeller_shaft_output,base(te))),'runs':runs};results.append(out);print(out,flush=True)
metadata={'status':'adapted_architecture_experiment_not_original_reproduction','source_paper':'SSRN7232001 section4.1.1 and4.4.2','architecture':'4 ->512 ReLU ->1 linear; no dropout or batchnorm','protocol':'Adam lr.001 wd.0001 cosine150 batch256 patience20; three seeds; chronological72/8/20 and1h boundary gaps','deviations':['Paper features resistance/STW/efficiency/draught replaced with STW/draught/wind components; no CFD coefficients.','Direct shaft-power MLP, not original serial physics hybrid.','DataBio fishing vessels, not9 dual-fuel container sister ships.','Train-only standardization and complete-case filtering; not full paper preprocessing.'],'ships':results,'australia_scenarios':scenarios,'scenario_limitations':['Synthetic1000nm voyage speeds10..12; no real vessel/port mapping.','Australia50 aggregate port-quarter delays: share*conditional mean proxy sets waitsunder2h zero.','Hotel fractions0/.1/.3 are analyst assumptions, not measured generator load.','Mechanical shaft energy plus assumed hotel energy is a proxy, not fuel or CO2.','No DQN training, actual deadline certification, Hanbada savings or operating adoption.']}
(HERE/'results/french_mlp_australia_adaptation.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
