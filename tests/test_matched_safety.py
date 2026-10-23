import copy
import pytest
from evaluation.matched_safety import matched_safety_report


def fixture():
    rows, cases = [], []
    for episode in range(4):
        for policy in ['a', 'b']:
            safe = episode == 0 or episode == (1 if policy == 'a' else 2)
            cases.append(dict(seed=42, episode=episode, policy=policy, env_config={'reserve': .15}))
            rows.append(dict(seed='42', episode=str(episode), policy=policy,
                legacy_arrived='true', arrived_without_pre_refill_shortage='true',
                safe_arrival=str(safe), pre_refill_shortage_steps='0',
                pre_refill_reserve_violation_steps='0' if safe else '1', minimum_pre_refill_fuel='.2' if safe else '.1',
                purchase_sci='10' if policy == 'a' else '15', initial_inventory_value='100',
                terminal_inventory_value='40' if policy == 'a' else '45', final_fuel='.4',
                inventory_adjusted_sci='70', safe_arrival_adjusted_sci='70' if safe else ''))
    return rows, dict(policies=['a', 'b'], cases=cases, n_episodes=4,
        safety_accounting={'mode':'observational_audit_not_strict_termination', 'tolerance':1e-9})


def test_matching_safe_conditioning_and_repeated_seed_not_independent():
    rows, manifest = fixture()
    report = matched_safety_report(rows[::-1], manifest)
    c = report['comparisons'][0]
    assert c['safety_counts'] == dict(both_safe=1, a_only_safe=1, b_only_safe=1, neither_safe=1)
    assert c['cost_difference_b_minus_a']['mean'] == 0
    assert c['both_safe_coverage'] == .25
    assert report['distinct_evaluation_seeds'] == 1
    assert report['confidence_interval'] is None and report['p_value'] is None
    assert [p['inventory_adjusted_sci_difference_b_minus_a'] for p in c['pairs']] == [0, None, None, None]


def test_no_safe_pairs_is_null_not_zero():
    rows, m = fixture()
    for r in rows:
        r.update(safe_arrival='false', pre_refill_reserve_violation_steps='1', safe_arrival_adjusted_sci='')
    assert matched_safety_report(rows, m)['comparisons'][0]['cost_difference_b_minus_a'] is None


@pytest.mark.parametrize('field,value', [('seed', '1.0'), ('seed', True), ('policy', ''),
    ('purchase_sci', ''), ('purchase_sci', 'nan'), ('purchase_sci', 'inf'), ('purchase_sci', '-1'),
    ('safe_arrival', ''), ('safe_arrival', '1'), ('safe_arrival_adjusted_sci', ''),
    ('inventory_adjusted_sci', '80'), ('safe_arrival', 'false'), ('pre_refill_shortage_steps', '2')])
def test_invalid_observation_fails_closed(field, value):
    rows, m = fixture(); rows[0][field] = value
    with pytest.raises(ValueError): matched_safety_report(rows, m)


@pytest.mark.parametrize('mutation', ['missing','extra','duplicate','config','ambiguous','episodes','mode','negative_tolerance'])
def test_plan_integrity(mutation):
    rows,m=fixture()
    if mutation=='missing': rows.pop()
    if mutation=='extra':
        r=copy.deepcopy(rows[0]); r['episode']='999'; rows.append(r)
    if mutation=='duplicate': rows.append(copy.deepcopy(rows[0]))
    if mutation=='config': m['cases'][0]['env_config']['reserve']=.2
    if mutation=='ambiguous':
        for c in list(m['cases']):
            d=copy.deepcopy(c); d['env_config']['reserve']=.2; m['cases'].append(d)
    if mutation=='episodes': m['n_episodes']=99
    if mutation=='mode': m['safety_accounting']['mode']='strict'
    if mutation=='negative_tolerance': m['safety_accounting']['tolerance']=-1
    with pytest.raises(ValueError): matched_safety_report(rows,m)


def test_unsafe_cost_not_imputed():
    rows,m=fixture(); rows[-1]['safe_arrival_adjusted_sci']='0'
    with pytest.raises(ValueError, match='unsafe cost'): matched_safety_report(rows,m)


def test_inputs_not_mutated():
    rows,m=fixture(); before=copy.deepcopy((rows,m)); matched_safety_report(rows,m)
    assert (rows,m)==before
