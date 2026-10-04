"""Monthly aggregate delay sensitivity; not measured fuel-saving validation."""
import csv, hashlib, importlib.util, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('uk',ROOT/'research/uk_bunkering/experiment.py')
uk=importlib.util.module_from_spec(spec);spec.loader.exec_module(uk)
HERE=Path(__file__).resolve().parent

def run():
    source=HERE/'inputs/vancouver_anchor_monthly.csv'
    months=list(csv.DictReader(source.open(encoding='utf-8')))
    assert len(months)==13 and len({m['month'] for m in months})==13
    rows=[]
    for m in months:
        direct,anchor=int(m['direct_to_berth_calls']),int(m['anchor_calls'])
        probability=anchor/(direct+anchor)
        conditional=float(m['mean_anchor_hours'])
        assert abs(conditional-24*float(m['mean_anchor_days']))<1e-8
        # Deterministic aggregate and conditional stress cases; no invented distribution.
        for case,delay in [('no_anchor_delay',0.),('all_calls_mean_proxy',probability*conditional),('anchored_call_mean_stress',conditional)]:
            for seed in range(1000,1200):
                data=uk.scenario(seed,'U3',False)
                data['service'][0]+=delay  # One Vancouver call; separate from synthetic 4h service.
                for policy in ('baseline','price','buffer'):
                    for speed in ('fixed','adaptive'):
                        result=uk.simulate(data,policy,speed);result.pop('trace')
                        rows.append(dict(month=m['month'],case=case,anchor_probability=probability,delay_hours=delay,seed=seed,policy=policy,speed=speed,**result))
    out=HERE/'results';out.mkdir(exist_ok=True)
    with (out/'episodes.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=[];pairs=[]
    for month in months:
        for case in ('no_anchor_delay','all_calls_mean_proxy','anchored_call_mean_stress'):
            group=[r for r in rows if r['month']==month['month'] and r['case']==case]
            for policy in ('baseline','price','buffer'):
                a={r['seed']:r for r in group if r['policy']==policy and r['speed']=='fixed'}
                b={r['seed']:r for r in group if r['policy']==policy and r['speed']=='adaptive'}
                keys=[k for k in a if a[k]['safe'] and b[k]['safe']]
                pairs.append(dict(month=month['month'],case=case,policy=policy,common_safe_n=len(keys),adaptive_consumed_change_pct=100*(statistics.mean(b[k]['consumed'] for k in keys)/statistics.mean(a[k]['consumed'] for k in keys)-1) if keys else None))
                for speed in ('fixed','adaptive'):
                    v=[r for r in group if r['policy']==policy and r['speed']==speed]
                    arrived=[r for r in v if r['arrived']]
                    summary.append(dict(month=month['month'],case=case,policy=policy,speed=speed,n=len(v),delay_hours=v[0]['delay_hours'],safe_rate=statistics.mean(r['safe'] for r in v),arrival_rate=len(arrived)/len(v),late_rate=sum(r['late'] for r in arrived)/len(arrived) if arrived else None,mean_consumed_synthetic_units=statistics.mean(r['consumed'] for r in v)))
    report=dict(status='connected_to_research_experiment_only',episodes=len(rows),source_url='https://www.portvancouver.com/media/dashboard-documents/container-vessel-line',source_document_date='2026-09-29',input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),uk_simulator_sha256=hashlib.sha256((ROOT/'research/uk_bunkering/experiment.py').read_bytes()).hexdigest(),summary=summary,paired_safe=pairs)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert len(rows)==46800
    print('episodes:',len(rows))
    for case in ('no_anchor_delay','all_calls_mean_proxy','anchored_call_mean_stress'):
        for speed in ('fixed','adaptive'):
            s=[r for r in summary if r['case']==case and r['policy']=='buffer' and r['speed']==speed]
            print(case,speed,'safe',statistics.mean(r['safe_rate'] for r in s),'late',statistics.mean(r['late_rate'] for r in s),'delay_range',min(r['delay_hours'] for r in s),max(r['delay_hours'] for r in s))
if __name__=='__main__':run()
