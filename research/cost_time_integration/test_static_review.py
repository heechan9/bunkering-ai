"""Reproductions from independent static review; expectations precede fixes."""
from types import SimpleNamespace
import numpy as np
import pytest
from .test_integration import base
from . import solver
from .ledger import audit


@pytest.mark.parametrize('key,value', [
    ('price_unit','KRW/t'), ('mass_unit','kg'), ('currency','KRW'),
    ('time_unit','minutes'), ('information_tier','FORECAST'),
    ('data_kind','observed'), ('decision_lot_t',1),
    ('terminal_inventory_min_t',6), ('fuel_grades',['MGO','HFO'])])
def test_rejects_unsupported_contract(key,value):
    c=base(); c[key]=value
    with pytest.raises(ValueError): solver.solve(c)


def test_rejects_unmodeled_call_field():
    c=base(); c['calls'][0]['tide_window_hours']=2
    with pytest.raises(ValueError): solver.solve(c)


def test_unavailable_none_prices_are_normalized():
    c=base(); c['available']=[False,False,True,True]
    c['prices_usd_per_t']=[None,None,700,650]
    r=solver.solve(c)
    assert r['status']=='FEASIBLE_OPTIMAL'
    assert r['cost_usd']==pytest.approx(10700)
    assert audit(c,r['purchases_t'])['valid']


@pytest.mark.parametrize('q', [[0], [0]*5, [False,16,0,0], [0,True,0,0],
    [0,float('nan'),0,0], [0,float('inf'),0,0], [0,-float('inf'),0,0],
    [0,-.001,0,16.001], [0,'16',0,0]])
def test_ledger_invalid_quantities_return_invalid(q):
    c=base(); c['initial_inventory_t']=16
    r=audit(c,q)
    assert r['valid'] is False


@pytest.mark.parametrize('kind', ['terminal','supply','reserve','capacity','deadline'])
def test_finite_fake_solver_success_is_not_feasible(monkeypatch,kind):
    c=base(); q=[0,16,0,0]
    if kind=='terminal': q=[0,17,0,0]
    if kind=='supply': c['supply_max_t'][1]=8
    if kind=='reserve': q=[0,0,0,16]
    if kind=='capacity': c['capacity_t']=30
    if kind=='deadline': c['deadline_hours']=26.31
    fake=np.array(q+[0]*4,dtype=float)
    monkeypatch.setattr(solver,'linprog',lambda *a,**k: SimpleNamespace(status=0,success=True,x=fake))
    with pytest.raises(RuntimeError,match='audit'):
        solver.solve(c)
