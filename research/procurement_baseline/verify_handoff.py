import json
from pathlib import Path
from zipfile import ZipFile

import argparse
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Compare all 120 reproduced development cases with the frozen reviewed handoff')
parser.add_argument('--input-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
run=args.input_dir.resolve()
if args.output.exists(): raise FileExistsError(args.output)
load=lambda p: json.loads(p.read_text(encoding='utf-8'))
# Expanded handoff files are local-only; the exact reviewed archive is committed.
with ZipFile(root/'provenance/reviewed_bundle.zip') as archived:
    prefix='procurement_baseline_comparison_20261015/'
    original_cases=json.loads(archived.read(prefix+'cases.json'))
    original_results=json.loads(archived.read(prefix+'results.json'))
assert load(run/'cases.json') == original_cases
a=load(run/'results.json');b=original_results
assert len(a)==len(b)==120
max_delta=0.
for actual,expected in zip(a,b):
    assert actual['case_id']==expected['case_id']
    assert actual['reference']['status']==expected['reference']['status']
    assert actual['reference']['status']==actual['independent_stop_enumeration']['status']
    if actual['reference']['status']=='OPTIMAL':
        delta=abs(actual['reference']['objective_usd']-actual['independent_stop_enumeration']['best']['objective_usd'])
        max_delta=max(max_delta,delta)
        assert delta<=.01
        assert abs(actual['reference']['objective_usd']-expected['reference']['objective_usd'])<=.01
    for name,result in actual['policies'].items():
        assert result['status']==expected['policies'][name]['status']
        assert abs(result['audit']['total_usd']-expected['policies'][name]['audit']['total_usd'])<=.01
s=load(run/'summary.json')
assert s['ALL']['reference_status']=={'OPTIMAL':86,'INFEASIBLE':34}
assert s['ALL']['common_feasible_n']==75
assert s['ALL']['policies']['minimum_required']['feasible_n']==75
assert s['ALL']['policies']['next_cheaper']['feasible_n']==79
assert s['ALL']['policies']['departure_concentrated']['feasible_n']==79
for m in s['ALL']['policies'].values(): assert abs(m['common_optimum_total_usd']-1750550)<=.01
assert s['zero_fees_unlimited']['policies']['next_cheaper']['optimal_match_n']==34
out={'status':'PASS','cases':120,'cases_equal_handoff':True,'all_reference_status_and_costs_match_handoff':True,'all_policy_status_and_costs_match_handoff':True,'independent_enumeration_max_absolute_difference_usd':max_delta,'all':s['ALL'],'zero_fees_next_cheaper_optimal_matches':34}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
