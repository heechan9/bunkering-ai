"""Frozen-policy transfer diagnostic, not NTNU paper replication or field evidence."""
from pathlib import Path
import sys,json,zipfile,hashlib,random
from types import SimpleNamespace
import numpy as np
import pandas as pd
from scipy.optimize import linprog
import torch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from agents.dqn import DQNAgent
from scripts.baseline import FixedFuelingStrategy,PriceReactiveStrategy,SafeStockStrategy
HERE=Path(__file__).resolve().parent
SOURCE_SHA='aa751f28705336cbca379b1499021cb17b299709a7563f398ef066aa75c6381f'
MODEL_SHA='970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392'

def solve(prices,demands,cap,initial,reserve,available):
    # Energy in kWh. Purchase before leg; reserve after leg; no cargo optimization.
    n=len(prices);lower=np.tril(np.ones((n,n)));prior=np.r_[0,np.cumsum(demands)[:-1]]
    ans=linprog(np.array(prices)-min(prices),A_ub=np.r_[lower,-lower],
        b_ub=np.r_[cap-initial+prior,initial-np.cumsum(demands)-reserve],
        bounds=[(0,None if a else 0) for a in available],method='highs')
    return ans.x if ans.success else None

def run():
    torch.set_num_threads(1)
    source=HERE/'inputs/supplementary_materials.zip';model=HERE/'inputs/dqn_final.pt'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
    assert hashlib.sha256(model.read_bytes()).hexdigest()==MODEL_SHA
    agent=DQNAgent.load_checkpoint(model,device='cpu');agent.policy_net.eval()
    with zipfile.ZipFile(source) as z:data={n:json.loads(z.read(n)) for n in z.namelist()}
    vessels=data['vessel_fuel_specifications.json'];settings=data['global_parameters.json']
    rules={p.name:p for p in [FixedFuelingStrategy(),PriceReactiveStrategy(),SafeStockStrategy()]}
    policies=list(rules)+['frozen_dqn','guarded_dqn','minimum_next_leg','inventory_lp']
    rows=[];audit=[]
    for name,area in sorted(data.items()):
        if not name.startswith('ports_'):continue
        ports={p['port_id']:p for p in area['ports']};hub=area['hub_port_id']
        audit.append({'instance':area['instance'],'ports':len(ports),'mgo_hypothetical':sum(bool(p['bunkering_prices']['MGO'].get('hypothetical_infrastructure')) for p in ports.values())})
        for seed in range(20):
            route=[hub]+random.Random(seed).sample([i for i in ports if i!=hub],3)+[hub]
            calls=[ports[i] for i in route[:-1]]
            distances=np.array([area['distance_matrix_nm'][ports[a]['name']][ports[b]['name']] for a,b in zip(route,route[1:])])
            assert np.all(distances>0)
            available=[p['bunkering_prices']['MGO']['available'] and not p['bunkering_prices']['MGO'].get('hypothetical_infrastructure',False) for p in calls]
            # All sampled MGO ports must have published finite prices.
            prices=np.array([p['bunkering_prices']['MGO']['price_usd_per_kwh'] for p in calls]);assert np.all(np.isfinite(prices))
            for vessel in vessels['by_fuel']['MGO']:
                cap=vessel['tank_capacity_kwh'];reserve=cap*settings['gamma_min_tank_fraction'];initial=cap*.5
                for speed in [10,14,18]:
                    # Explicit sensitivity assumption: power proportional to speed cubed.
                    demands=vessel['energy_consumption']*1000*(speed/14)**3*distances/speed
                    optimal=solve(prices,demands,cap,initial,reserve,available)
                    for policy in policies:
                        inv=initial;cost=0.;hours=0.;bought=0.;used=0.;safe=True;arrived=True;stops=0;overrides=0;clipped=0;history=[];min_inv=initial
                        if policy=='inventory_lp' and optimal is None:
                            rows.append(dict(instance=area['instance'],seed=seed,teu=vessel['vessel_teu'],speed=speed,policy=policy,arrived=False,safe=False,on_time=False,feasible=False,cost_usd=None,adjusted_cost_usd=None,hours=None,stops=0,overrides=0,clipped_steps=0,lp_feasible=False));continue
                        for i,(price,demand,port,avail) in enumerate(zip(prices,demands,calls,available)):
                            usd_t=price*vessel['energy_density_kwh_per_kg']*1000;history.append(usd_t)
                            raw=np.array([(usd_t-500)/150,(np.mean(history[-30:])-500)/150,0,inv/cap,sum(distances[i:])/sum(distances),.19],dtype=np.float32)
                            clipped+=int(np.any(abs(raw)>1));obs=np.clip(raw,-1,1)
                            env=SimpleNamespace(raw_fuel_price=usd_t,raw_price_ma30=np.mean(history[-30:]),min_safe_fuel=.15)
                            if policy in rules:action=rules[policy].select_action(env,obs,i)
                            elif policy in ['frozen_dqn','guarded_dqn']:action=agent.greedy_action(obs)
                            else:action=0
                            q=min(.9*cap,max(0,.95*cap-inv)) if action else 0.
                            if policy=='minimum_next_leg':q=max(0,reserve+demand-inv)
                            elif policy=='inventory_lp':q=max(0,float(optimal[i]))
                            elif policy=='guarded_dqn':
                                floor=max(0,reserve+demand-inv);overrides+=int(floor>q+1e-6);q=max(q,floor)
                            q=min(q,max(0,cap-inv)) if avail else 0.
                            before=inv;inv+=q;bought+=q;cost+=q*price
                            if q>1e-6:
                                stops+=1;k='hub' if port['port_type']=='CP' else 'local';bt=vessels['bunkering_times']['MGO'];hours+=bt['bunkering_fixed_h'][k]+q*bt['bunkering_variable_h_per_kwh'][k]
                            actual=min(inv,demand);used+=actual;inv-=actual;hours+=distances[i]/speed;min_inv=min(min_inv,inv)
                            safe &= inv>=reserve-1e-5
                            assert abs(initial+bought-used-inv)<1e-4 and inv<=cap+1e-5 and inv>=-1e-5
                            if actual<demand-1e-5:arrived=False;safe=False;break
                        ontime=arrived and hours<=area['max_route_time_hours']
                        rows.append(dict(instance=area['instance'],seed=seed,teu=vessel['vessel_teu'],speed=speed,policy=policy,arrived=arrived,safe=bool(safe),on_time=bool(ontime),feasible=bool(safe and ontime),cost_usd=cost,adjusted_cost_usd=cost+min(prices)*(initial-inv),hours=hours,stops=stops,overrides=overrides,clipped_steps=clipped,lp_feasible=optimal is not None))
    df=pd.DataFrame(rows);out=HERE/'results';out.mkdir(exist_ok=True)
    df.to_csv(out/'episodes.csv',index=False)
    summary=df.groupby('policy').agg(n=('safe','size'),arrival_rate=('arrived','mean'),safe_rate=('safe','mean'),feasible_rate=('feasible','mean'),mean_overrides=('overrides','mean'),clipped_steps=('clipped_steps','sum')).reset_index()
    summary.to_csv(out/'summary.csv',index=False)
    df.groupby(['speed','policy']).agg(n=('safe','size'),safe_rate=('safe','mean'),feasible_rate=('feasible','mean')).to_csv(out/'by_speed.csv')
    pair=[];keys=['instance','seed','teu','speed']
    for policy in policies[:-1]:
        a=df[df.policy==policy].set_index(keys);b=df[df.policy=='inventory_lp'].set_index(keys);mask=a.feasible&b.feasible
        assert (a.loc[mask,'adjusted_cost_usd']>=b.loc[mask,'adjusted_cost_usd']-1e-4).all()
        pair.append({'policy':policy,'common_feasible_n':int(mask.sum()),'total_cost_gap_pct':float(100*(a.loc[mask,'adjusted_cost_usd'].sum()/b.loc[mask,'adjusted_cost_usd'].sum()-1)) if mask.any() else None})
    report={'source_sha256':SOURCE_SHA,'checkpoint_sha256':MODEL_SHA,'network_files':len(audit),'audit':audit,'scenarios':len(df)//len(policies),'episodes':len(df),'paired_to_inventory_lp':pair,'limitations':['Not NTNU full network design replication; five network files vs six advertised instances.','20 seeded three-call round trips per network, six vessel sizes, speeds10/14/18; routes are constructed, not observed voyages.','14kn consumption uses source;10/18kn use assumed cubic power, not measured response.','Initial tank50%;NTNU reserve10%;legacy safe-stock trigger15%,refill90% capped95%.','Frozen DQN six-state mapping; FX1300,SFC0.19 constants; port actions collapsed to refuel here; purchase-before-leg differs from original environment.','MA30 uses up to30 visited-port prices, NOT30daily market observations. No USDA prices used.','All prices are static published scenario inputs, not future realized market prices.','Guarded DQN adds next-leg reserve logic; gains cannot be attributed to DQN learning.','Inventory LP optimal for fixed route/speed energy cost with terminal inventory valued at minimum route price; no fixed-stop time constraint in solver. Feasibility checked afterwards.','Time includes sailing and bunkering only; cargo handling, queues,full cargo network constraints omitted.','Source labels energy_consumption as propulsion energy; conversion efficiency is not supplied here. Energy balance treats it as stored-energy demand proxy, not verified fuel burn.','No training, deployed model changes, real savings or independent vessel replication.']}
    (out/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(summary.to_string(index=False));print(json.dumps(pair,indent=2));print('episodes',len(df))
if __name__=='__main__':run()
