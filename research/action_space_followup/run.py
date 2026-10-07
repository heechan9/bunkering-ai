"""Replay archived NTNU candidates, decompose gaps, and paired 5/6-action pilot."""
import argparse, ast, copy, csv, hashlib, itertools, json, random, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'results'

def load_functions(path,names,ns):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)

def oracles(c,quantity):
    # Enumerate every sequence in parallel, under identical inventory and time rules.
    ans=[]
    for n in (5,6):
        acts=np.array(list(itertools.product(range(n),repeat=4)))
        inv=np.full(len(acts),.5);cost=np.zeros(len(acts));hours=np.full(len(acts),c['sailing']);safe=np.ones(len(acts),dtype=bool)
        for i in range(4):
            floor=np.maximum(0,c['d'][i]+.1-inv)
            ceiling=np.maximum(0,min(1,.1+sum(c['d'][i:]))-inv)
            q=np.minimum(np.maximum(0,1-inv),floor+(ceiling-floor)*acts[:,i]/4)
            if n==6:
                j=next((j for j in range(i+1,4) if c['p'][j]<c['p'][i]),4)
                rule=np.maximum(0,min(1,.1+sum(c['d'][i:j]))-inv)
                q=np.where(acts[:,i]==5,rule,q)
            inv+=q-c['d'][i];cost+=q*c['p'][i]
            hours+=np.where(q>1e-9,c['fixed'][i]+q*c['variable'][i],0)
            safe &= (inv>=.1-1e-7)&(inv<=1+1e-7)
        adjusted=(cost+min(c['p'])*(.5-inv))*c['cap']
        objective=adjusted/(c['cap']*.1)+5*np.maximum(0,hours/c['limit']-1)
        ans.append((float(adjusted[safe].min()),float(objective[safe].min())))
    return ans

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);a=ap.parse_args()
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    OUT.mkdir(exist_ok=False)
    old=a.archive; audit=json.loads((old/'results/retraining/audit.json').read_text())
    for name,h in audit['artifact_sha256'].items():
        p=old/name if name=='retrain.py' else old/'results/retraining'/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
    assert hashlib.sha256((old/'inputs/supplementary_materials.zip').read_bytes()).hexdigest()==audit['source_sha256']
    ns=dict(np=np,pd=pd,torch=torch,nn=nn,copy=copy,random=random,json=json,hashlib=hashlib,zipfile=zipfile,HERE=old,OUT=OUT,ETAS=[1.,.5,.4],SOURCE_SHA=audit['source_sha256'],linprog=linprog)
    load_functions(old/'experiment.py',['solve'],ns)
    load_functions(old/'retrain.py',['cases','state','quantity','rollout','train'],ns)
    sets,manifest=ns['cases']()
    assert manifest==json.loads((old/'results/retraining/route_manifest.json').read_text())
    for k in sets:sets[k]=[c for c in sets[k] if c['lp'] is not None]
    cs=sets['test']+sets['external'];baseq=ns['quantity'];rows=[]
    archived=pd.read_csv(old/'results/retraining/episodes.csv').set_index(['id','policy'])
    nets={}
    for seed in [42,43,44]:
        ck=torch.load(old/f'results/retraining/candidate_{seed}.pt',map_location='cpu',weights_only=True)
        net=nn.Sequential(nn.Linear(12,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,5));net.load_state_dict(ck['state_dict']);net.eval();nets[seed]=net
    max_replay=0.
    for index,c in enumerate(cs):
        (five,fiveobj),(six,sixobj)=oracles(c,baseq)
        lp=ns['rollout'](c,rule='lp')['cost']
        assert five>=lp-1e-5 and six>=lp-1e-5 and six<=five+1e-5
        for seed,net in nets.items():
            r=ns['rollout'](c,net);ref=archived.loc[(c['id'],f'dqn_{seed}')]
            delta=abs(r['cost']-ref.cost);max_replay=max(max_replay,delta)
            assert np.isclose(r['cost'],ref.cost,rtol=1e-8,atol=1e-5)
            assert r['safe']==ref.safe and r['feasible']==ref.feasible
            assert r['cost']>=five-1e-5
            obj=r['cost']/(c['cap']*.1)+5*max(0,r['hours']/c['limit']-1)
            rows.append(dict(id=c['id'],split=c['split'],eta=c['eta'],seed=seed,lp=lp,five_oracle=five,six_oracle=six,dqn=r['cost'],action_gap=five-lp,selection_gap=r['cost']-five,objective_gap=obj-fiveobj))
        if index%500==0:print('decomposition',index,flush=True)
    pd.DataFrame(rows).to_csv(OUT/'decomposition.csv',index=False)
    print('archived replay max cost difference',max_replay,flush=True)
    # Same predeclared 2,000-episode pilot for both action spaces; validation-only choice.
    source=(old/'retrain.py').read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='train')
    text=ast.unparse(node).replace('range(1, 6001)','range(1, 2001)').replace('episode / 4500','episode / 1500').replace('episode % 1000','episode % 500').replace('nn.Linear(64, 5)','nn.Linear(64, ACTIONS)').replace('rng.integers(5)','rng.integers(ACTIONS)')
    # Saved architecture metadata must match six-action heads.
    text=text.replace('[12, 64, 64, 5]','[12, 64, 64, ACTIONS]')
    (OUT/'effective_train.py').write_text(text+'\n',encoding='utf-8')
    exec(compile(text,'paired_pilot_train','exec'),ns)
    def q6(c,i,inv,action):
        if action<5:return baseq(c,i,inv,action)
        j=next((j for j in range(i+1,4) if c['p'][j]<c['p'][i]),4)
        return max(0,min(1,.1+sum(c['d'][i:j]))-inv)
    pilot=[];hist=[]
    for actions in [5,6]:
        ns['ACTIONS']=actions;ns['quantity']=baseq if actions==5 else q6
        folder=OUT/f'actions_{actions}';folder.mkdir();ns['OUT']=folder
        for seed in [42,43,44]:
            net,h=ns['train'](sets['train'],sets['validation'],seed)
            hist += [dict(actions=actions,**r) for r in h]
            net.eval()
            for c in cs:
                r=ns['rollout'](c,net);pilot.append(dict(id=c['id'],split=c['split'],eta=c['eta'],actions=actions,seed=seed,**r))
    pd.DataFrame(pilot).to_csv(OUT/'pilot.csv',index=False);pd.DataFrame(hist).to_csv(OUT/'training_history.csv',index=False)
    (OUT/'execution.json').write_text(json.dumps(dict(replay_max_cost_difference=max_replay,cases=len(cs),pilot_episodes=2000,seeds=[42,43,44],torch=torch.__version__,numpy=np.__version__,source_sha256=audit['source_sha256']),indent=2))
    print('COMPLETE',flush=True)
if __name__=='__main__':main()
