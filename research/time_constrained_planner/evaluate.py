"""Aggregate-only evaluation; archive path is supplied explicitly."""
import argparse,sys,json,time,zipfile,hashlib,random
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from planner import plan
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'action_space_followup'))
from run import load_functions

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);a=ap.parse_args()
    audit=json.loads((a.archive/'results/retraining/audit.json').read_text())
    for name,h in audit['artifact_sha256'].items():
        source=a.archive/name if name=='retrain.py' else a.archive/'results/retraining'/name
        assert hashlib.sha256(source.read_bytes()).hexdigest()==h,name
    ns=dict(np=np,pd=pd,random=random,json=json,zipfile=zipfile,hashlib=hashlib,HERE=a.archive,ETAS=[1.,.5,.4],SOURCE_SHA=audit['source_sha256'],linprog=linprog)
    load_functions(a.archive/'experiment.py',['solve'],ns);load_functions(a.archive/'retrain.py',['cases'],ns)
    sets,manifest=ns['cases']();assert manifest==json.loads((a.archive/'results/retraining/route_manifest.json').read_text())
    old=pd.read_csv(a.archive/'results/retraining/episodes.csv')
    summaries=[];runtimes=[];infeasibility={}
    for split in ['test','external']:
        cs=[c for c in sets[split] if c['lp'] is not None];records=[]
        for i,c in enumerate(cs):
            start=time.perf_counter();r=plan(c);runtimes.append(time.perf_counter()-start)
            records.append(dict(id=c['id'],planner_feasible=r is not None,planner_cost=r['cost'] if r else np.nan))
            if i%500==0:print(split,i,flush=True)
        frame=pd.DataFrame(records)
        infeasibility[split]=dict(planner_infeasible=int((~frame.planner_feasible).sum()),sailing_alone_over_limit=sum(c['sailing']>c['limit'] for c in cs))
        for policy,g in old[old.split==split].groupby('policy'):
            joined=g.merge(frame,on='id',validate='one_to_one');common=joined.feasible & joined.planner_feasible
            assert not (joined.feasible & ~joined.planner_feasible).any()
            assert (joined.loc[common,'planner_cost']<=joined.loc[common,'cost']+1e-5).all()
            summaries.append(dict(split=split,policy=policy,n=len(joined),baseline_feasible=int(joined.feasible.sum()),planner_feasible=int(joined.planner_feasible.sum()),rescued=int((~joined.feasible & joined.planner_feasible).sum()),common_n=int(common.sum()),planner_cost_change_pct=float(100*(joined.loc[common,'planner_cost'].sum()/joined.loc[common,'cost'].sum()-1))))
    out=dict(infeasibility=infeasibility,source_sha256=audit['source_sha256'],comparisons=summaries,runtime_seconds=dict(median=float(np.median(runtimes)),p95=float(np.quantile(runtimes,.95)),max=float(max(runtimes))),scope='Existing reused synthetic NTNU routes; not independent holdout or production evaluation')
    (Path(__file__).parent/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
