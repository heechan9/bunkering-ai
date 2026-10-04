"""Leave-one-leg-out diagnostics and explicitly assumed slowdown scenarios."""
from pathlib import Path
import hashlib,json
import numpy as np,openpyxl
from scipy.optimize import nnls
from sklearn.metrics import mean_absolute_error
HERE=Path(__file__).resolve().parent
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workbook', type=Path, required=True, help='Authorized private Hanbada workbook; never commit this input')
source=parser.parse_args().workbook
assert hashlib.sha256(source.read_bytes()).hexdigest()=='eaf7945109e2675ba8dbd6716d357f4babe737c6f36195f3a8f4da8c21af6665'
s=openpyxl.load_workbook(source,data_only=True)['B FOAM'];rows=[]
for r in range(8,69,2):
 day,h,dist,v,me,ge,bo=[s.cell(r,c).value for c in [1,8,9,10,20,21,22]]
 if all(isinstance(x,(int,float)) for x in [h,dist,v,me,ge,bo]) and h==24 and day!=31:
  leg=1 if day<=9 else 2 if day<=16 else 3 if day<=25 else 4
  rows.append(dict(day=int(day),leg=leg,h=h,dist=dist,v=v,me=me,ge=ge,bo=bo))
v=np.array([r['v'] for r in rows]);y=np.array([r['me']*1000/r['h'] for r in rows]);X=np.column_stack([np.ones(len(v)),v**3]);legs=np.array([r['leg'] for r in rows]);folds=[];pred=np.empty(len(y));models=[]
for leg in sorted(set(legs)):
 tr=legs!=leg;te=~tr;c=nnls(X[tr],y[tr])[0];models.append(c);pred[te]=X[te]@c
 folds.append({'held_out_leg':int(leg),'train_count':int(tr.sum()),'test_count':int(te.sum()),'coefficients':c.tolist(),'mae_L_h':float(mean_absolute_error(y[te],pred[te])),'volume_bias_pct':float(100*(pred[te].sum()/y[te].sum()-1)),'test_speed_outside_train_range':int(((v[te]<v[tr].min())|(v[te]>v[tr].max())).sum())})
full=nnls(X,y)[0];models.append(full)
scenarios=[]
# Discrete amount of assumed deadline slack; never claim actual schedule known.
for reduction in [0,.02,.05,.10]:
 vals=[]
 for c in models:
  baseline=sum((c[0]+c[1]*r['v']**3)*r['h']/1000+r['ge']+r['bo'] for r in rows)
  candidate=0;extra=0
  for r in rows:
   speed=r['v']*(1-reduction);new_h=r['h']/(1-reduction)
   candidate+=(c[0]+c[1]*speed**3)*new_h/1000+(r['ge']+r['bo'])*new_h/24
   extra+=new_h-r['h']
  vals.append(100*(baseline-candidate)/baseline)
 scenarios.append({'speed_reduction_pct':100*reduction,'extra_time_total_selected_blocks_h':extra,'extra_time_per_24h_block_h':24/(1-reduction)-24,'estimated_volume_saving_pct_full_fit':vals[-1],'fold_coefficient_sensitivity_range_pct':[min(vals),max(vals)],'minimum_scenario_speed_kn':float(v.min()*(1-reduction)),'below_selected_observed_speed_range_blocks':int((v*(1-reduction)<v.min()).sum()),'deadline_checks':[{'assumed_slack_h':slack,'selected_blocks_time_budget_feasible':bool(extra<=slack+1e-9)} for slack in [0,6,12,24]]})
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'selected_blocks':len(rows),'selected_hours':sum(r['h'] for r in rows),'selected_observed_me_kL':sum(r['me'] for r in rows),'selected_observed_aux_boiler_kL':sum(r['ge']+r['bo'] for r in rows),'leave_one_leg_out':folds,'out_of_fold_mae_L_h':float(mean_absolute_error(y,pred)),'out_of_fold_volume_bias_pct':float(100*(pred.sum()/y.sum()-1)),'full_fit_coefficients':full.tolist(),'scenarios':scenarios,'actual_deadline':'not present; port event timestamps are actual events, not planned deadlines','decision':'exploratory_only_no_operating_adoption_no_measured_savings','assumptions':['Only7 selected24h records represent parts of4 legs, not complete voyage.','Observed daily ME kL divided by underway hours is a proxy with unverified exact interval.','Each daily average speed treated constant; ignore intra-day speed variance.','Fixed recorded distance approximated by original speed times hours, not charted route change.','G/E+boiler rate held fixed at recorded kL/24h; hotel load/weather effects unknown.','Counterfactual consumes modelled ME; baseline also modelled ME, observed auxiliaries.','Coefficient ranges are sensitivity, not confidence intervals.','Added-time budget applies only selected blocks; no actual voyage deadline certification.','Sea/wind/draught/current/engine constraints and safety-stock initial-condition units unresolved.','Slower speeds outside observed subset are extrapolation; not deployable recommendations.']}
(HERE/'results/hanbada_policy_review.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
