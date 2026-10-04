"""Private workbook inspection; publish aggregate diagnostics only."""
from pathlib import Path
import hashlib,json
import numpy as np,openpyxl
from scipy.optimize import nnls
from sklearn.metrics import mean_absolute_error,r2_score
HERE=Path(__file__).resolve().parent
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workbook', type=Path, required=True, help='Authorized private Hanbada workbook; never commit this input')
SOURCE=parser.parse_args().workbook
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='eaf7945109e2675ba8dbd6716d357f4babe737c6f36195f3a8f4da8c21af6665'
w=openpyxl.load_workbook(SOURCE,data_only=True);s=w['B FOAM'];f=openpyxl.load_workbook(SOURCE,data_only=False)['B FOAM']
rows=[]
for r in range(8,69,2):
 day,h,dist,speed,me=[s.cell(r,c).value for c in [1,8,9,10,20]]
 if all(isinstance(v,(int,float)) for v in [h,dist,speed,me]) and h>0 and speed>0 and me>0:
  assert not any(f.cell(r,c).data_type=='f' for c in [8,9,10,20])
  rows.append(dict(day=int(day),hours=h,distance=dist,speed=speed,me_kL=me,rate_L_h=me*1000/h,kinematic_error_pct=100*(dist/(h*speed)-1)))
# Full 24h recorded rows, excluding ambiguous arrival/noon boundary 31.
q=[x for x in rows if x['hours']==24 and x['day']!=31]
v=np.array([x['speed'] for x in q]);y=np.array([x['rate_L_h'] for x in q])
training=json.loads((HERE/'results/consumption_training.json').read_text())
external=[]
for ship in training['ships']:
 a,b=ship['cubic_coefficients'];pred=a+b*v**3
 external.append({'ship':ship['ship'],'mae_L_h':float(mean_absolute_error(y,pred)),'r2':float(r2_score(y,pred)),'volume_bias_pct':float(100*(pred.sum()/y.sum()-1)),'scope':'unadjusted average-speed proxy; DataBio STW vs Hanbada distance/time speed not interchangeable'})
# Target-ship exploratory fit on earliest 4, test latest3; no adjustment from test.
X=np.column_stack([np.ones(len(v)),v**3]);coef=nnls(X[:4],y[:4])[0];p=X[4:]@coef
result={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'year':2026,'paired_rows':len(rows),'recorded_hours_range':[min(x['hours'] for x in rows),max(x['hours'] for x in rows)],'max_abs_distance_speed_time_error_pct':max(abs(x['kinematic_error_pct']) for x in rows),'eligible_24h_rows_excluding31':len(q),'external_cubic_transfer':external,'hanbada_exploratory_fit':{'train_count':4,'test_count':len(q)-4,'train_days':[x['day'] for x in q[:4]],'test_days':[x['day'] for x in q[4:]],'coefficients':coef.tolist(),'test_mae_L_h':float(mean_absolute_error(y[4:],p)),'test_r2':float(r2_score(y[4:],p)),'test_volume_bias_pct':float(100*(p.sum()/y[4:].sum()-1))},'limitations':['Daily recorded consumption, metering method not independently verified.','M/E volume divided by recorded underway hours is a proxy; same-interval alignment not independently established.','Mean-speed cubed differs from mean cubed speed; no within-day speed trajectories.','25h row retained in paired audit but excluded from24h subset; timezone interval unknown.','Partial days/port events excluded; day31 boundary interpretation tentative.','Hanbada draught and wind are not same-granularity compatible with DataBio residual features; residual model not applied.','Only seven selected day rows, no independent voyage; no statistical generalization or fuel-saving estimate.']}
(HERE/'results/hanbada_consumption_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
