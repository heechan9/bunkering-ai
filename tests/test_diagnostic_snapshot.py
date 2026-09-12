"""Regression checks for strict-vs-tolerant interpretation, not a new environment."""
import copy
import pytest
from scripts.audit_diagnostic_snapshot import inspect_steps, main
from scripts.diagnose_reward import trace_episode
from scripts.baseline import SafeStockStrategy, FixedFuelingStrategy, PriceReactiveStrategy


def test_boundary_is_reclassified_without_rewriting_reward():
    rows, _ = trace_episode(SafeStockStrategy(), 42)
    original = copy.deepcopy(rows)
    result = inspect_steps(rows)
    assert result['raw_violation'] == 1
    assert result['tolerance_violation'] == 0
    assert result['safety_reward'] == pytest.approx(-0.5)
    assert result['price_advantage_reward'] >= 0
    assert rows == original


@pytest.mark.parametrize('strategy', [SafeStockStrategy, FixedFuelingStrategy, PriceReactiveStrategy])
def test_existing_baseline_records_are_accepted(strategy):
    for seed in (42, 57, 141):
        rows, original = trace_episode(strategy(), seed)
        result = inspect_steps(rows)
        assert result['step_sci'] == pytest.approx(original['step_sci'])
        assert result['reward'] == pytest.approx(original['reward'])


@pytest.mark.parametrize('field,value', [('safety_reward',0.007202), ('step_sci',12345),
    ('fuel_after',0.99), ('step',999), ('reward',float('nan'))])
def test_rejects_altered_record(field, value):
    rows, _ = trace_episode(SafeStockStrategy(), 42)
    rows[16][field] = value
    with pytest.raises(ValueError):
        inspect_steps(rows)


def test_output_protection(tmp_path):
    output=tmp_path/'existing.json'
    output.write_text('preserve')
    with pytest.raises(SystemExit):
        main(['--bundle',str(tmp_path),'--output',str(output)])
    assert output.read_text() == 'preserve'
