import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('uk',Path(__file__).resolve().parents[1]/'research/uk_bunkering/experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_ablations_keep_unaffected_draws():
    a=m.scenario(1001,'U3',1)
    assert a['prices']==m.scenario(1001,'U1',0)['prices']
    assert a['fuel']==m.scenario(1001,'U2',0)['fuel']
    assert a['service']==m.scenario(1001,'U0',1)['service']

def test_mass_balance_and_bounds():
    for p in ('baseline','price','buffer'):
        r=m.simulate(m.scenario(1002,'U3',1),p,'adaptive')
        assert m.INITIAL+r['purchase']-r['consumed']==pytest.approx(r['remaining'])
        assert all(0<=x['remaining']<=m.CAPACITY for x in r['trace'])

def test_deterministic_reference():
    r=m.simulate(m.scenario(0,'U0',0),'baseline','fixed')
    assert r['safe'] and r['hours']==112 and r['purchase']==125 and r['adjusted_cost']==16000

def test_future_changes_do_not_change_first_action():
    a=m.scenario(1000,'U3',1); b={k:list(v) for k,v in a.items()}
    for k in b:b[k][-1]*=2
    assert m.simulate(a,'buffer','adaptive')['trace'][0]==m.simulate(b,'buffer','adaptive')['trace'][0]

def test_buffer_safe_over_bounded_evaluation():
    for seed in range(1000,1200):
        assert m.simulate(m.scenario(seed,'U3',1),'buffer','adaptive')['safe']


def test_shortage_terminates_and_excludes_lateness():
    data=m.scenario(0,'U0',0)
    data['fuel'][0]=200
    r=m.simulate(data,'baseline','fixed')
    assert not r['arrived'] and r['shortage'] and r['late'] is None
    assert len(r['trace'])==1 and r['remaining']==0
    assert m.INITIAL+r['purchase']==r['consumed']
