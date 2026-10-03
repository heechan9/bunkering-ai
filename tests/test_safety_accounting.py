import pytest
from evaluation.safety_accounting import VoyageAudit

def test_refill_cannot_hide_shortage():
    audit = VoyageAudit(1, 100, .15)
    audit.observe(.04, .05)
    result = audit.finish(True, 90, .9, 100)
    assert result["legacy_arrived"]
    assert not result["arrived_without_pre_refill_shortage"]
    assert result["safe_arrival_adjusted_sci"] is None
    assert result["minimum_pre_refill_fuel"] == pytest.approx(-.01)

def test_reserve_and_arrival_are_distinct_and_boundary_tolerant():
    audit = VoyageAudit(1, 100, .15)
    audit.observe(.2 - 1e-15, .05)
    assert audit.finish(True, 50, .4, 120)["safe_arrival"]
    audit.observe(.1, .05)
    result = audit.finish(True, 50, .4, 120)
    assert result["arrived_without_pre_refill_shortage"]
    assert not result["safe_arrival"]
    assert result["inventory_adjusted_sci"] == pytest.approx(102)

def test_equal_demand_purchase_only_advantage_can_disappear():
    a = VoyageAudit(1, 100, .15); a.observe(1, .05)
    b = VoyageAudit(1, 100, .15); b.observe(1, .05)
    assert a.finish(True, 40, .4, 100)["inventory_adjusted_sci"] == b.finish(True, 70, .7, 100)["inventory_adjusted_sci"]
    assert not a.finish(False, 40, .4, 100)["safe_arrival"]
