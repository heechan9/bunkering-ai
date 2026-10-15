"""Reproduce all prespecified development cases without overwriting handoff evidence."""
import sys,json,csv,random,hashlib,platform
from pathlib import Path
from dataclasses import asdict
from collections import Counter
ROOT=Path(__file__).resolve().parent
from research.procurement_baseline.procurement import Case,solve,audit,enumerate_stops
POLICIES=('minimum_required','next_cheaper','departure_concentrated')
def usable(c,i): return c.available[i] and c.supply[i]>0 and c.minimum[i]<=min(c.supply[i],c.capacity)
def need(c,i,j):
    used=0.; target=0.
    for k in range(i,j):
        used+=c.d[k]
        target=max(target,used+(c.terminal if k==len(c.d)-1 else c.reserve[k]))
    return target

def policy(c,name):
    c.validate(); inv=c.initial; B=sum(c.d)+c.terminal-c.initial; left=B; q=[]; reasons=[]; first=True
    for i in range(len(c.d)):
        qty=0.
        if usable(c,i) and left>c.mass_tol:
            j=next((j for j in range(i+1,len(c.d)) if usable(c,j)),len(c.d))
            target=need(c,i,j)
            if name=='next_cheaper':
                j=next((j for j in range(i+1,len(c.d)) if usable(c,j) and c.p[j]+c.variable[j]<c.p[i]+c.variable[i]),None)
                target=need(c,i,j) if j is not None else c.capacity
                if target>c.capacity: target=c.capacity
            if name=='departure_concentrated' and first:target=c.capacity
            first=False
            request=max(0.,target-inv)
            if request>c.mass_tol:
                upper=max(0.,min(c.supply[i],c.capacity-inv,left))
                if c.minimum[i]>upper+c.mass_tol:reasons.append(f'{i}:minimum_exceeds_common_upper')
                else:qty=min(max(request,c.minimum[i]),upper)
        q.append(qty);left-=qty;inv+=qty-c.d[i]
    checked=audit(c,q,[int(x>c.mass_tol) for x in q]); residual=sum(q)-B
    if B< -c.mass_tol:reasons.append('negative_total_purchase_requirement')
    if abs(residual)>c.mass_tol:reasons.append('total_purchase_requirement')
    reasons+=checked['errors']
    return dict(status='FEASIBLE' if checked['valid'] and not reasons else 'POLICY_FAILURE',q_t=q,z=[int(x>c.mass_tol) for x in q],audit=checked,reasons=reasons,total_purchase_required_t=B,total_purchase_residual_t=residual)

def generate(spec):
    rng=random.Random(spec['seed']); cases=[]
    for block in spec['blocks']:
        for k in range(spec['random_cases_per_block']):
            n=rng.randint(3,7); C=rng.choice([30,45,60]); I=rng.randint(0,15); T=rng.randint(2,8)
            d=tuple(rng.randint(3,16) for _ in range(n)); reserve=tuple(rng.randint(0,min(2,T)) for _ in range(n))
            avail=tuple(rng.random()>.2 for _ in range(n)); p=tuple(rng.randint(30,100)*10 for _ in range(n))
            U=tuple(rng.randint(0,C) for _ in range(n)) if block=='limited_supply_minimum' else (C,)*n
            m=tuple(rng.choice([0,3,8,15]) for _ in range(n)) if block=='limited_supply_minimum' else (0,)*n
            f=tuple(rng.choice([0,100,500,1500]) for _ in range(n)) if block!='zero_fees_unlimited' else (0,)*n
            v=tuple(rng.choice([0,5,20]) for _ in range(n)) if block!='zero_fees_unlimited' else (0,)*n
            c=Case(f'{block}_{k:03}',d,p,avail,U,m,f,v,reserve,C,I,T);c.validate();cases.append((block,c))
    return cases

def summary(records):
    result={}
    for block in ['ALL']+list(dict.fromkeys(r['block'] for r in records)):
        rows=[r for r in records if block=='ALL' or r['block']==block]; n=len(rows)
        ref=Counter(r['reference']['status'] for r in rows)
        common=[r for r in rows if r['reference']['status']=='OPTIMAL' and all(r['policies'][p]['status']=='FEASIBLE' for p in POLICIES)]
        obj={'n':n,'reference_status':dict(ref),'reference_optimal_rate':ref['OPTIMAL']/n,'reference_infeasible_rate':ref['INFEASIBLE']/n,'reference_other_rate':(n-ref['OPTIMAL']-ref['INFEASIBLE'])/n,'common_feasible_n':len(common),'policies':{}}
        for p in POLICIES:
            feasible=[r for r in rows if r['policies'][p]['status']=='FEASIBLE']
            pair=[r for r in feasible if r['reference']['status']=='OPTIMAL']
            total=sum(r['policies'][p]['audit']['total_usd'] for r in pair); opt=sum(r['reference']['audit']['total_usd'] for r in pair)
            diffs=[r['policies'][p]['audit']['total_usd']-r['reference']['audit']['total_usd'] for r in pair]
            obj['policies'][p]=dict(feasible_n=len(feasible),feasible_rate=len(feasible)/n,failure_n=n-len(feasible),failure_rate=(n-len(feasible))/n,policy_failure_on_proven_feasible_n=sum(r['reference']['status']=='OPTIMAL' and r['policies'][p]['status']!='FEASIBLE' for r in rows),failure_on_proven_infeasible_n=sum(r['reference']['status']=='INFEASIBLE' and r['policies'][p]['status']!='FEASIBLE' for r in rows),failure_on_unresolved_reference_n=sum(r['reference']['status'] not in ['OPTIMAL','INFEASIBLE'] and r['policies'][p]['status']!='FEASIBLE' for r in rows),pairwise_feasible_n=len(pair),pairwise_policy_total_usd=total,pairwise_optimum_total_usd=opt,pairwise_difference_usd=total-opt,pairwise_cost_weighted_difference_pct=100*(total-opt)/total if total else None,optimal_match_n=sum(bool(abs(x)<=.01) for x in diffs),negative_difference_n=sum(bool(x<-.01) for x in diffs),common_policy_total_usd=sum(r['policies'][p]['audit']['total_usd'] for r in common),common_optimum_total_usd=sum(r['reference']['audit']['total_usd'] for r in common))
        for metrics in obj['policies'].values():
            metrics['common_difference_usd']=metrics['common_policy_total_usd']-metrics['common_optimum_total_usd']
            metrics['common_cost_weighted_difference_pct']=100*metrics['common_difference_usd']/metrics['common_policy_total_usd'] if metrics['common_policy_total_usd'] else None
        result[block]=obj
    return result

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True,help='New directory for reproduced artifacts; existing files are never overwritten')
    parser.add_argument('--spec',type=Path,default=ROOT/'spec.json')
    args=parser.parse_args()
    output=args.output_dir.resolve()
    output.mkdir(parents=True,exist_ok=False)
    spec=json.loads(args.spec.read_text(encoding='utf-8'));cases=generate(spec)
    (output/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    # Persist EVERY generated input before running any optimizer or policy.
    (output/'cases.json').write_text(json.dumps([dict(block=b,case=asdict(c)) for b,c in cases],indent=2))
    records=[]
    for b,c in cases:
        reference=solve(c); raw_reference=dict(reference)
        verification=enumerate_stops(c)
        conflict=reference['status']!=verification['status'] or (reference['status']=='OPTIMAL' and abs(reference['objective_usd']-verification['best']['objective_usd'])>.01)
        if conflict:
            reference=dict(reference,status='REFERENCE_CONTRADICTION')
        records.append(dict(case_id=c.case_id,block=b,reference=reference,raw_reference=raw_reference,independent_stop_enumeration=verification,policies={p:policy(c,p) for p in POLICIES}))
    (output/'results.json').write_text(json.dumps(records,indent=2));summ=summary(records)
    (output/'summary.json').write_text(json.dumps(summ,indent=2))
    with (output/'results.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['case_id','block','method','status','cost_usd','total_purchase_t','total_purchase_residual_t','reasons'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in records:
            for p,s in [('reference',r['reference'])]+list(r['policies'].items()):
                w.writerow(dict(case_id=r['case_id'],block=r['block'],method=p,status=s['status'],cost_usd=s.get('audit',{}).get('total_usd'),total_purchase_t=sum(s.get('q_t',[])) if 'q_t' in s else None,total_purchase_residual_t=s.get('total_purchase_residual_t'),reasons=';'.join(s.get('reasons',[]))))
    import scipy,numpy
    (output/'environment.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),scipy=scipy.__version__,numpy=numpy.__version__),indent=2))
    print(json.dumps(summ,indent=2))
if __name__=='__main__': main()
