"""Canada/Australia monthly/quarterly aggregate scenario sensitivity."""
import csv,hashlib,json,statistics
from pathlib import Path
from experiment import uk,HERE
from deadline_simulator import simulate

def run():
    observations=[]
    ca=HERE/'inputs/vancouver_anchor_monthly.csv'; au=HERE/'inputs/australia_waterline71_original_cells.csv'
    for r in csv.DictReader(ca.open(encoding='utf-8')):
        observations.append(dict(country='Canada',port='Vancouver',period=r['month'],p=int(r['anchor_calls'])/(int(r['anchor_calls'])+int(r['direct_to_berth_calls'])),conditional=float(r['mean_anchor_hours'])))
    for r in csv.DictReader(au.open(encoding='utf-8')):
        observations.append(dict(country='Australia',port=r['port'],period=r['period'],p=float(r['anchor_share_pct'])/100,conditional=float(r['mean_anchor_hours'])))
    assert len(observations)==63
    for seed in range(1000,1200):
        d=uk.scenario(seed,'U3',False)
        for p in ('baseline','price','buffer'):
            for speed in ('fixed','adaptive'):assert simulate(d,p,speed)==uk.simulate(d,p,speed)
    rows=[];episodes=0
    for o in observations:
        assert 0<=o['p']<=1 and o['conditional']>=0
        for case,delay in [('no_anchor_delay',0.),('all_calls_mean_proxy',o['p']*o['conditional']),('anchored_call_mean_stress',o['conditional'])]:
            for slack in (0,12,24,48,96,144):
                fixed=[];adaptive=[]
                for seed in range(1000,1200):
                    d=uk.scenario(seed,'U3',False);d['service'][0]+=delay
                    fixed.append(simulate(d,'buffer','fixed',112+slack));adaptive.append(simulate(d,'buffer','adaptive',112+slack));episodes+=2
                keys=[i for i in range(200) if fixed[i]['safe'] and adaptive[i]['safe']]
                fc=statistics.mean(fixed[i]['consumed'] for i in keys) if keys else None
                ac=statistics.mean(adaptive[i]['consumed'] for i in keys) if keys else None
                for speed,results in [('fixed',fixed),('adaptive',adaptive)]:
                    arrived=[r for r in results if r['arrived']]
                    rows.append(dict(country=o['country'],port=o['port'],period=o['period'],case=case,slack_hours=slack,delay_hours=delay,speed=speed,n=200,safe_rate=statistics.mean(r['safe'] for r in results),late_rate=statistics.mean(r['late'] for r in arrived) if arrived else None,mean_consumed_synthetic_units=statistics.mean(r['consumed'] for r in results),paired_safe_n=len(keys),adaptive_consumed_change_pct=100*(ac/fc-1) if fc else None))
                # Under this deterministic one-call timing model these feasibility bounds must hold.
                assert all(r['late']==(delay>slack+1e-8) for r in fixed if r['arrived'])
                if delay>slack+80-800/12+1e-8: assert all(r['late'] for r in adaptive if r['arrived'])
    out=HERE/'results';out.mkdir(exist_ok=True)
    with (out/'deadline_slack_summary.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'deadline_slack_metadata.json').write_text(json.dumps(dict(episodes=episodes,observations=63,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ca,au,Path(__file__),HERE/'deadline_simulator.py')},validated_default_parity_cases=1200,limitations=['synthetic fuel units; no measured fuel savings','aggregate means, not individual distributions','Australia excludes waits under two hours; proxy sets excluded delay to zero','single port delay; no auxiliary-engine fuel','buffer purchase policy only; no DQN training']),indent=2),encoding='utf-8')
    print('episodes',episodes)
    for country in ('Canada','Australia'):
        for case in ('all_calls_mean_proxy','anchored_call_mean_stress'):
            for slack in (0,12,24,48,96,144):
                a=[r for r in rows if r['country']==country and r['case']==case and r['slack_hours']==slack]
                print(country,case,slack,[(v,round(statistics.mean(r['late_rate'] for r in a if r['speed']==v),3)) for v in ('fixed','adaptive')])
if __name__=='__main__':run()
