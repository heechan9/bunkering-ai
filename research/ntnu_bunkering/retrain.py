"""Separate guarded DQN research model; unknown propulsion efficiency is a scenario."""
from pathlib import Path
import json, zipfile, random, hashlib, copy
import numpy as np
import pandas as pd
import torch
from torch import nn
from experiment import solve, SOURCE_SHA
HERE=Path(__file__).resolve().parent
OUT=HERE/'results/retraining'
ETAS=[1.0,0.5,0.4]

def cases():
    raw=(HERE/'inputs/supplementary_materials.zip').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    with zipfile.ZipFile(HERE/'inputs/supplementary_materials.zip') as z:
        data={n:json.loads(z.read(n)) for n in z.namelist()}
    result={k:[] for k in ['train','validation','test','external']}; manifest=[]
    vessels=data['vessel_fuel_specifications.json']; bt=vessels['bunkering_times']['MGO']
    for name,area in sorted(data.items()):
        if not name.startswith('ports_'):continue
        ports={p['port_id']:p for p in area['ports']}; hub=area['hub_port_id']; others=[p for p in ports if p!=hub]
        # Exclude prior experiments and reversed routes; split on canonical route identity.
        seen={min(tuple(r),tuple(reversed(r))) for r in [random.Random(s).sample(others,3) for s in range(20)]}
        rng=random.Random(20261005); counts={'train':100,'validation':20,'test':30} if 'waf' not in name else {'external':50}
        for split,count in counts.items():
            for ri in range(count):
                while True:
                    r=rng.sample(others,3); sig=min(tuple(r),tuple(reversed(r)))
                    if sig not in seen:seen.add(sig);break
                route=[hub]+r+[hub]; calls=[ports[p] for p in route[:-1]]
                dist=np.array([area['distance_matrix_nm'][ports[a]['name']][ports[b]['name']] for a,b in zip(route,route[1:])])
                prices=np.array([p['bunkering_prices']['MGO']['price_usd_per_kwh'] for p in calls])
                avail=np.array([p['bunkering_prices']['MGO']['available'] and not p['bunkering_prices']['MGO'].get('hypothetical_infrastructure',False) for p in calls])
                assert avail.all(), 'This experiment requires available MGO at every call'
                rid=f'{name}:{ri}:{split}'; manifest.append(dict(id=rid,split=split,route=route,signature=list(sig)))
                for v in vessels['by_fuel']['MGO']:
                    cap=v['tank_capacity_kwh']
                    for eta in ETAS:
                        d=v['energy_consumption']*1000*dist/14/eta/cap
                        kind=['hub' if p['port_type']=='CP' else 'local' for p in calls]
                        c=dict(id=f'{rid}:{v["vessel_teu"]}:{eta}',split=split,area=name,eta=eta,teu=v['vessel_teu'],cap=cap,d=d,p=prices,
                               sailing=float(sum(dist)/14),limit=area['max_route_time_hours'],fixed=np.array([bt['bunkering_fixed_h'][k] for k in kind]),variable=np.array([bt['bunkering_variable_h_per_kwh'][k]*cap for k in kind]))
                        q=solve(prices,d,1,.5,.1,avail);c['lp']=q
                        result[split].append(c)
    return result,manifest

def state(c,i,inv,hours):
    d=np.zeros(4);p=np.zeros(4);d[:4-i]=c['d'][i:];p[:4-i]=c['p'][i:]/.1
    return np.array([inv,i/4,(c['limit']-hours)/c['limit'],c['sailing']/c['limit'],*d,*p],dtype=np.float32)

def quantity(c,i,inv,a):
    floor=max(0,c['d'][i]+.1-inv)
    ceiling=max(0,min(1,.1+sum(c['d'][i:]))-inv)
    return min(max(0,1-inv),floor+(ceiling-floor)*a/4)

def rollout(c,net=None,rule=None):
    inv=.5;cost=0.;h=c['sailing'];safe=True;stops=0
    for i in range(4):
        if rule=='lp':q=c['lp'][i]
        elif rule=='minimum':q=quantity(c,i,inv,0)
        elif rule=='cheaper_port':
            j=next((j for j in range(i+1,4) if c['p'][j]<c['p'][i]),4)
            q=max(0,min(1,.1+sum(c['d'][i:j]))-inv)
        else:
            with torch.no_grad():a=int(net(torch.from_numpy(state(c,i,inv,h))).argmax())
            q=quantity(c,i,inv,a)
        q=float(q);cost+=q*c['p'][i];inv+=q-c['d'][i]
        if q>1e-9:h+=c['fixed'][i]+q*c['variable'][i];stops+=1
        safe &= inv>=.1-1e-7
        assert inv<=1+1e-7
    adjusted=(cost+min(c['p'])*(.5-inv))*c['cap']
    return dict(cost=adjusted,safe=bool(safe),feasible=bool(safe and h<=c['limit']),hours=h,stops=stops)

def train(train,val,seed):
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    net=nn.Sequential(nn.Linear(12,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,5));target=copy.deepcopy(net)
    opt=torch.optim.Adam(net.parameters(),lr=.001);buffer=[];best=float('inf');saved=None;history=[]
    # Online replay: discount1 and terminal salvage align rewards with adjusted energy cost.
    for episode in range(1,6001):
        c=train[int(rng.integers(len(train)))];inv=.5;h=c['sailing']
        for i in range(4):
            s=state(c,i,inv,h);epsilon=max(.05,1-episode/4500)
            with torch.no_grad():a=int(rng.integers(5)) if rng.random()<epsilon else int(net(torch.from_numpy(s)).argmax())
            q=quantity(c,i,inv,a);inv+=q-c['d'][i]
            if q>1e-9:h+=c['fixed'][i]+q*c['variable'][i]
            reward=-q*c['p'][i]/.1;done=i==3
            if done:reward+=min(c['p'])*inv/.1;reward-=5*max(0,h/c['limit']-1)
            ns=state(c,min(i+1,4),inv,h)
            buffer.append((s,a,reward,ns,float(done)))
            if len(buffer)>30000:buffer.pop(0)
            if len(buffer)>=128:
                batch=[buffer[j] for j in rng.integers(len(buffer),size=128)]
                ss,aa,rr,nnn,dd=zip(*batch);ss=torch.tensor(np.array(ss));nsb=torch.tensor(np.array(nnn));aa=torch.tensor(aa);rr=torch.tensor(rr);dd=torch.tensor(dd)
                with torch.no_grad():y=rr+(1-dd)*target(nsb).gather(1,net(nsb).argmax(1)[:,None]).squeeze(1)
                loss=nn.functional.smooth_l1_loss(net(ss).gather(1,aa[:,None]).squeeze(1),y)
                opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),10);opt.step()
        if episode%100==0:target.load_state_dict(net.state_dict())
        if episode%1000==0:
            outputs=[rollout(c,net) for c in val];score=np.mean([r['cost']/(c['cap']*.1)+5*max(0,r['hours']/c['limit']-1) for c,r in zip(val,outputs)])
            history.append(dict(seed=seed,episode=episode,validation_score=float(score)))
            if score<best:best=score;saved=copy.deepcopy(net.state_dict())
            print(seed,episode,round(score,6),flush=True)
    net.load_state_dict(saved);torch.save({'state_dict':saved,'seed':seed,'architecture':[12,64,64,5],'source_sha256':SOURCE_SHA,'efficiency_scenarios':ETAS},OUT/f'candidate_{seed}.pt')
    return net,history

def main():
    torch.set_num_threads(1);OUT.mkdir(parents=True,exist_ok=True)
    sets,manifest=cases();(OUT/'route_manifest.json').write_text(json.dumps(manifest,indent=2))
    audit={'source_sha256':SOURCE_SHA,'efficiencies':ETAS,'counts':{},'production_model_changed':False}
    for split,cs in sets.items():
        audit['counts'][split]={'all':len(cs),'capacity_feasible':sum(c['lp'] is not None for c in cs)}
        sets[split]=[c for c in cs if c['lp'] is not None]
    rows=[];history=[]
    for split in ['test','external']:
        for c in sets[split]:
            for rule in ['minimum','cheaper_port','lp']:
                rows.append(dict(id=c['id'],split=split,eta=c['eta'],policy=rule,**rollout(c,rule=rule)))
    for seed in [42,43,44]:
        net,h=train(sets['train'],sets['validation'],seed);history+=h
        for split in ['test','external']:
            for c in sets[split]:rows.append(dict(id=c['id'],split=split,eta=c['eta'],policy=f'dqn_{seed}',**rollout(c,net)))
    df=pd.DataFrame(rows);df.to_csv(OUT/'episodes.csv',index=False);pd.DataFrame(history).to_csv(OUT/'training_history.csv',index=False)
    summary=[]
    for (split,eta),g in df.groupby(['split','eta']):
        feasible=g.pivot(index='id',columns='policy',values='feasible').all(axis=1);ids=feasible[feasible].index
        costs=g[g.id.isin(ids)].groupby('policy').cost.sum()
        for p,a in g.groupby('policy'):
            summary.append(dict(split=split,eta=eta,policy=p,n=len(a),safe_rate=a.safe.mean(),feasible_rate=a.feasible.mean(),common_feasible_n=len(ids),gap_lp_pct=100*(costs[p]/costs['lp']-1),gap_minimum_pct=100*(costs[p]/costs['minimum']-1),gap_cheaper_pct=100*(costs[p]/costs['cheaper_port']-1)))
    pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False)
    assert all(r['gap_lp_pct']>=-1e-5 for r in summary)
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2))
    print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':main()
