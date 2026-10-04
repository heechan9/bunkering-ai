"""Predetermined input-range gate and +20% demand buffer; research only."""
from experiment import HERE,SOURCE_SHA,MODEL_SHA,DQNAgent
import hashlib,json,zipfile,random
import numpy as np
import pandas as pd
import torch

def run():
 torch.set_num_threads(1)
 p=HERE/'inputs';assert hashlib.sha256((p/'supplementary_materials.zip').read_bytes()).hexdigest()==SOURCE_SHA
 assert hashlib.sha256((p/'dqn_final.pt').read_bytes()).hexdigest()==MODEL_SHA
 a=DQNAgent.load_checkpoint(p/'dqn_final.pt',device='cpu');a.policy_net.eval()
 with zipfile.ZipFile(p/'supplementary_materials.zip') as z:d={n:json.loads(z.read(n)) for n in z.namelist()}
 rows=[]
 for n,area in sorted(d.items()):
  if not n.startswith('ports_'):continue
  ports={x['port_id']:x for x in area['ports']};hub=area['hub_port_id']
  for seed in range(20):
   route=[hub]+random.Random(seed).sample([i for i in ports if i!=hub],3)+[hub]
   calls=[ports[i] for i in route[:-1]];dist=np.array([area['distance_matrix_nm'][ports[x]['name']][ports[y]['name']] for x,y in zip(route,route[1:])])
   prices=np.array([x['bunkering_prices']['MGO']['price_usd_per_kwh'] for x in calls])
   for v in d['vessel_fuel_specifications.json']['by_fuel']['MGO']:
    cap=v['tank_capacity_kwh'];reserve=.1*cap;pred=v['energy_consumption']*1000*dist/14
    for error in [0,.1,.2]:
     for policy in ['frozen','range_gate','range_gate_buffer20','minimum_buffer20']:
      inv=.5*cap;cost=0.;hours=0.;safe=True;arrived=True;gates=0;clips=0;interventions=0;history=[];used=0.;bought=0.
      for i,(port,price,need) in enumerate(zip(calls,prices,pred)):
       price_t=price*v['energy_density_kwh_per_kg']*1000;history.append(price_t)
       raw=np.array([(price_t-500)/150,(np.mean(history)-500)/150,0,inv/cap,sum(dist[i:])/sum(dist),.19],dtype=np.float32)
       outside=bool(np.any(abs(raw)>1));clips+=outside
       action=a.greedy_action(np.clip(raw,-1,1));q=min(.9*cap,max(0,.95*cap-inv)) if action else 0
       margin=1.2 if 'buffer20' in policy else 1.
       if policy!='frozen':
        floor=max(0,reserve+need*margin-inv)
        if outside or policy=='minimum_buffer20':q=floor;gates+=outside
        else:
         # Bound learned overbuy by estimated remaining voyage demand plus reserve.
         ceiling=max(0,reserve+sum(pred[i:])*margin-inv);q=max(floor,min(q,ceiling))
        interventions+=int(q>0)
       fuel=port['bunkering_prices']['MGO'];available=fuel['available'] and not fuel.get('hypothetical_infrastructure',False)
       q=min(q,max(0,cap-inv)) if available else 0
       inv+=q;bought+=q;cost+=q*price
       if q>1e-6:
        k='hub' if port['port_type']=='CP' else 'local';bt=d['vessel_fuel_specifications.json']['bunkering_times']['MGO'];hours+=bt['bunkering_fixed_h'][k]+q*bt['bunkering_variable_h_per_kwh'][k]
       actual=need*(1+error);burn=min(inv,actual);used+=burn;inv-=burn;hours+=dist[i]/14;safe &= inv>=reserve-1e-5
       assert abs(.5*cap+bought-used-inv)<1e-4 and 0<=inv<=cap+1e-5
       if burn<actual-1e-5:arrived=False;safe=False;break
      rows.append(dict(instance=area['instance'],seed=seed,teu=v['vessel_teu'],demand_error=error,policy=policy,safe=bool(safe),feasible=bool(safe and arrived and hours<=area['max_route_time_hours']),adjusted_cost=cost+min(prices)*(.5*cap-inv),range_gate_steps=gates,clipped_steps=clips))
 df=pd.DataFrame(rows);out=HERE/'results/guard_followup';out.mkdir(exist_ok=True)
 df.to_csv(out/'episodes.csv',index=False)
 s=df.groupby(['demand_error','policy']).agg(n=('safe','size'),safe_rate=('safe','mean'),feasible_rate=('feasible','mean'),gated_steps=('range_gate_steps','sum')).reset_index();s.to_csv(out/'summary.csv',index=False)
 pairs=[]
 for error in [0,.1,.2]:
  a=df[(df.policy=='frozen')&(df.demand_error==error)].set_index(['instance','seed','teu'])
  for policy in ['range_gate','range_gate_buffer20','minimum_buffer20']:
   b=df[(df.policy==policy)&(df.demand_error==error)].set_index(['instance','seed','teu']);m=a.feasible&b.feasible
   pairs.append(dict(error=error,policy=policy,common_feasible_n=int(m.sum()),cost_change_pct=100*(b.loc[m,'adjusted_cost'].sum()/a.loc[m,'adjusted_cost'].sum()-1)))
 (out/'paired.json').write_text(json.dumps(pairs,indent=2));print(s.to_string(index=False));print(json.dumps(pairs,indent=2))
if __name__=='__main__':run()
