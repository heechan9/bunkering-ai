"""Synthetic sensitivity study inspired by UK literature, NOT paper replication."""
import csv
import hashlib
import json
import random
from pathlib import Path

N = 8
INITIAL, CAPACITY, RESERVE = 50., 120., 15.


def scenario(seed, uncertainty, variable_time):
    # Separate streams ensure ablations share all unaffected random quantities.
    price_rng, fuel_rng, time_rng = (random.Random(seed+i) for i in (0,100000,200000))
    return dict(prices=[100*price_rng.uniform(.75,1.25) if uncertainty in ('U1','U3') else 100. for _ in range(N)],
                fuel=[20*fuel_rng.uniform(.7,1.3) if uncertainty in ('U2','U3') else 20. for _ in range(N)],
                service=[time_rng.uniform(0,8) if variable_time else 4. for _ in range(N)])


def simulate(data, policy, speed_policy):
    fuel, clock, cost, bought, consumed = INITIAL, 0., 0., 0., 0.
    shortage, reserve_violation, stops = False, False, 0
    trace = []
    for i in range(N):
        clock += data['service'][i]  # observed only after port service finishes
        # All policies have speeds 10/12. Adaptive uses observed elapsed time only.
        speed = 12. if speed_policy == 'adaptive' and clock+10*(N-i)+4*(N-i-1)>112 else 10.
        expected = 20*(speed/10)**2
        floor = RESERVE + expected*(1.3 if policy == 'buffer' else 1.)
        target = floor if policy == 'baseline' else (CAPACITY if data['prices'][i]<100 else floor)
        amount = max(0., min(CAPACITY,target)-fuel)
        fuel += amount; bought += amount; cost += amount*data['prices'][i]; stops += amount>1e-9
        demand = data['fuel'][i]*(speed/10)**2
        before = fuel
        if demand>fuel:
            shortage=True
            consumed+=fuel; fuel=0.
            trace.append(dict(leg=i,inventory=before,purchase=amount,demand=demand,remaining=fuel,speed=speed))
            break
        fuel-=demand; consumed+=demand; clock+=100/speed
        reserve_violation |= fuel<RESERVE-1e-9
        trace.append(dict(leg=i,inventory=before,purchase=amount,demand=demand,remaining=fuel,speed=speed))
    return dict(arrived=not shortage, safe=not(shortage or reserve_violation), shortage=shortage,
                reserve_violation=reserve_violation, purchase=bought, consumed=consumed,
                remaining=fuel, cost=cost, adjusted_cost=cost+100*(INITIAL-fuel),
                purchase_cost_per_consumed_unit=cost/consumed if consumed else None, stops=stops, hours=clock,
                late=(clock>112) if not shortage else None,
                late_hours=max(0.,clock-112) if not shortage else None, trace=trace)


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for u in ('U0','U1','U2','U3'):
        for t in (0,1):
            for seed in range(1000,1200):
                data=scenario(seed,u,t)
                for policy in ('baseline','price','buffer'):
                    for speed in ('fixed','adaptive'):
                        result=simulate(data,policy,speed); result.pop('trace')
                        rows.append(dict(uncertainty=u,time_case='T'+str(t),seed=seed,policy=policy,speed=speed,**result))
    with (out/'episodes.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=[]
    for u in ('U0','U1','U2','U3'):
        for t in ('T0','T1'):
            subset=[r for r in rows if r['uncertainty']==u and r['time_case']==t]
            common={seed for seed in range(1000,1200) if all(r['safe'] for r in subset if r['seed']==seed)}
            for p in ('baseline','price','buffer'):
                for v in ('fixed','adaptive'):
                    a=[r for r in subset if r['policy']==p and r['speed']==v]
                    b=[r for r in a if r['seed'] in common]
                    summary.append(dict(u=u,t=t,policy=p,speed=v,n=len(a),
                        arrival_rate=sum(r['arrived'] for r in a)/len(a),safe_rate=sum(r['safe'] for r in a)/len(a),
                        late_rate=sum(r['late'] is True for r in a)/sum(r['arrived'] for r in a) if any(r['arrived'] for r in a) else None,
                        mean_cost=sum(r['cost'] for r in a)/len(a),common_safe_n=len(b),
                        common_safe_adjusted_cost=sum(r['adjusted_cost'] for r in b)/len(b) if b else None))
    pairs=[]
    for u in ('U0','U1','U2','U3'):
        for t in ('T0','T1'):
            for v in ('fixed','adaptive'):
                group=[r for r in rows if r['uncertainty']==u and r['time_case']==t and r['speed']==v]
                for left,right in (('baseline','price'),('price','buffer')):
                    a={r['seed']:r for r in group if r['policy']==left}
                    b={r['seed']:r for r in group if r['policy']==right}
                    keys=[k for k in a if a[k]['safe'] and b[k]['safe']]
                    ac=sum(a[k]['adjusted_cost'] for k in keys)/len(keys) if keys else None
                    bc=sum(b[k]['adjusted_cost'] for k in keys)/len(keys) if keys else None
                    pairs.append(dict(u=u,t=t,speed=v,left=left,right=right,paired_safe_n=len(keys),
                                      left_adjusted_cost=ac,right_adjusted_cost=bc,
                                      change_pct=100*(bc/ac-1) if ac else None))
    (out/'paired_safe.json').write_text(json.dumps(pairs,indent=2)+'\n',encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(dict(synthetic=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),episodes=len(rows),summary=summary),indent=2)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    run(Path(__file__).parent/'results')
