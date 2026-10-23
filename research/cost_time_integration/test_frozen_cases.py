"""Make the already-frozen 28 development cases explicit pytest regressions."""
import copy
import json
from pathlib import Path
import pytest
from .solver import solve
from .ledger import audit

ROOT=Path(__file__).parent
ORIGINAL=json.loads((ROOT/'fixtures_compact.json').read_text())
FOLLOWUP=json.loads((ROOT/'followup_fixtures.json').read_text())
CASES=[('original',c) for c in ORIGINAL['cases']]+[('followup',c) for c in FOLLOWUP['cases']]


@pytest.mark.parametrize('phase,case',CASES,ids=[p+'-'+c['id'] for p,c in CASES])
def test_frozen_case_after_static_review(phase,case):
    c=copy.deepcopy(ORIGINAL['base']); c.update(case['overrides'])
    for key,update in case.get('call_updates',{}).items(): c['calls'][int(key)].update(update)
    if case.get('existing_port2'):
        c['calls'][1]=dict(kind='existing',baseline_departure_hours=3.5,
            cargo_end_with_bunkering_hours=3,bunker_ready_hours=0,preparation_hours=1,
            cleanup_hours=1,transfer_hours_per_t=.1,departure_readiness_hours=.5)
    r=solve(c); expected=case['expected']
    assert r['status']==expected['status']
    if r['status']=='FEASIBLE_OPTIMAL':
        cost=expected['optimal_cost_usd'] if phase=='original' else expected['cost_usd']
        witness=expected['witness_purchases_t'] if phase=='original' else expected['q']
        checked=audit(c,r['purchases_t'])
        assert checked['valid'] and audit(c,witness)['valid']
        assert abs(r['cost_usd']-cost)<=.0001
        assert abs(r['cost_usd']-checked['cost_usd'])<=.0001
        assert abs(r['time_hours']-checked['time_hours'])<=.000001
        count=expected.get('optimal_positive_purchase_count')
        if count is not None: assert r['positive_purchase_count']==count


def test_canonical_units_are_accepted_without_conversion():
    c=copy.deepcopy(ORIGINAL['base'])
    c.update(price_unit='USD/t',mass_unit='t',currency='USD',time_unit='h')
    assert solve(c)['cost_usd']==7200
