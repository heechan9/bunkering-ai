import copy
import json
from pathlib import Path
import pytest
from .solver import solve, timing
from .ledger import audit

def base():
    return json.loads((Path(__file__).parent/'fixtures_compact.json').read_text())['base']

def test_missing_time_is_not_zero():
    c = base(); del c['calls'][1]['preparation_hours']
    assert solve(c)['status'] == 'NOT_COMPUTED_UNKNOWN_TIME'

def test_zero_purchase_has_no_fee_or_time():
    c = base(); c['initial_inventory_t'] = 46
    c['fixed_fee_usd'] = [1000]*4; c['deadline_hours'] = 24
    r = solve(c)
    assert r['purchases_t'] == [0]*4
    assert r['cost_usd'] == 0 and r['time_hours'] == 24

def test_continuous_purchase_is_not_input_grid_lot():
    c = base(); c['deadline_hours'] = 39.9995
    for call in c['calls']:
        call['preparation_hours'] = call['cleanup_hours'] = 0
    c['calls'][0]['transfer_hours_per_t'] = 0
    c['calls'][1]['transfer_hours_per_t'] = 1
    r = solve(c)
    assert r['purchases_t'][0] == pytest.approx(.0005, abs=1e-9)
    assert r['purchases_t'][1] == pytest.approx(15.9995, abs=1e-9)
    assert audit(c, r['purchases_t'])['valid']

def test_ledger_rejects_refill_repair_of_earlier_reserve():
    c = base()
    assert not audit(c, [0, 0, 0, 16])['valid']

def test_existing_overlap_uses_project_timing():
    f = json.loads((Path(__file__).parent/'fixtures_compact.json').read_text())
    c = copy.deepcopy(f['base']); c.update(f['cases'][15]['overrides'])
    assert timing(c['calls'][1], 16) == 0
    assert solve(c)['time_hours'] == 27.5
