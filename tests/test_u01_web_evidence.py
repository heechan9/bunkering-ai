"""Frozen web example versus unchanged t/USD Python solver, rules and Decimal ledger."""
import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from research.procurement_baseline.procurement import Case, solve, audit, enumerate_stops
from research.procurement_baseline.benchmark import POLICIES, policy

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = json.loads((ROOT / 'web/ocean-lab/public/data/u01-procurement.json').read_text())
CASE = Case('U01', (30., 40.), (600., 400.), (True, True), (100., 100.),
            (0., 0.), (0., 0.), (0., 0.), (10., 10.))


def test_original_contract_and_source():
    assert EVIDENCE['input'] == json.loads(json.dumps(asdict(CASE)))
    assert hashlib.sha256((ROOT / EVIDENCE['source_path']).read_bytes()).hexdigest() == EVIDENCE['source_sha256']
    assert EVIDENCE['ports'] == ['A', 'B', 'C']
    assert len(EVIDENCE['input']['p']) == 2  # no purchase at final arrival


def test_all_saved_methods_match_live_python():
    solutions = {'lp': solve(CASE, 'lp'), **{name: policy(CASE, name) for name in POLICIES}}
    for saved in EVIDENCE['methods']:
        live = solutions[saved['id']]
        assert saved['status'] == live['status']
        assert saved['purchases_t'] == live['q_t']
        assert saved['total_usd'] == live['audit']['total_usd']
        assert saved['terminal_t'] == live['audit']['terminal_t'] == 10
        assert saved['ledger'] == live['audit']['ledger']
        assert live['audit']['valid']


def test_independent_decimal_ledger_and_analytic_minimum():
    # No audit or solver matrix reuse in this exact arithmetic check.
    inv = Decimal(20)
    cost = Decimal(0)
    for purchase, demand, price in [(20, 30, 600), (40, 40, 400)]:
        departure = inv + Decimal(purchase)
        assert departure <= 100
        inv = departure - Decimal(demand)
        assert inv >= 10
        cost += Decimal(purchase) * Decimal(price)
    assert inv == 10 and cost == 28000
    # qA+qB=60 and B arrival>=10 require 20<=qA<=60.
    # J=24000+200*qA is increasing on that complete continuous feasible interval.
    assert Decimal(24000) + Decimal(200) * Decimal(20) == cost
    reference = enumerate_stops(CASE)
    assert EVIDENCE['enumeration'] == reference
    assert reference['best']['objective_usd'] == cost


def test_prior_reserve_failure_survives_next_refill():
    ledger = audit(CASE, [19, 41], [1, 1])
    assert ledger['ledger'][0]['I_next_t'] == 9
    assert ledger['ledger'][1]['I_before_t'] == 9
    assert ledger['terminal_t'] == 10
    assert not ledger['valid'] and ledger['errors'] == ['0:reserve']
    assert EVIDENCE['negative']['errors'] == ledger['errors']


def test_table_is_only_one_synthetic_case():
    assert EVIDENCE['schema'] == 'u01-tonne-usd-v1'
    assert EVIDENCE['input']['data_kind'] == 'synthetic'
    assert EVIDENCE['input']['information_tier'] == 'STATIC_KNOWN'
    assert [x['total_usd'] for x in EVIDENCE['methods']] == [28000, 28000, 28000, 36000]
