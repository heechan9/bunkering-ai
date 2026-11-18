"""Synthetic contract counterexamples, not vessel measurements."""
from datetime import datetime, timedelta, timezone
import pytest
from research.voyage_demand.validation import available_feature
T = datetime(2030, 1, 1, tzinfo=timezone.utc)
def feature(**changes):
    return dict(name='speed', unit='kn', source='synthetic fixture', kind='observation',
                issued_at=T, target_at=T, received_at=T, latency_seconds=0,
                missing_policy='reject', available_at_purchase=True) | changes
@pytest.mark.parametrize('key', ['name', 'unit', 'source', 'missing_policy'])
@pytest.mark.parametrize('value', ['  ', '\t\n', 123, True, [], {}])
def test_metadata_requires_text(key, value):
    with pytest.raises(ValueError):
        available_feature(feature(**{key:value}), T)
@pytest.mark.parametrize('received', [T, T+timedelta(minutes=30)])
def test_observation_not_received_before_measured(received):
    with pytest.raises(ValueError):
        available_feature(feature(target_at=T+timedelta(hours=1), received_at=received),
                          T+timedelta(hours=3))
@pytest.mark.parametrize('kind', ['forecast','plan'])
def test_future_target_allowed_for_plan_and_forecast(kind):
    assert available_feature(feature(kind=kind, target_at=T+timedelta(days=1)), T)
def test_observation_at_issue_and_later_receipt_allowed():
    assert available_feature(feature(received_at=T+timedelta(seconds=1)),
                             T+timedelta(seconds=1))

def test_early_issue_late_receipt_allowed():
    assert available_feature(feature(target_at=T+timedelta(hours=1), received_at=T+timedelta(hours=2)), T+timedelta(hours=3))

@pytest.mark.parametrize('latency', [[], {}, 1e15, 10**400])
def test_invalid_receipt_latency_is_value_error(latency):
    with pytest.raises(ValueError, match='Invalid receipt latency'):
        available_feature(feature(latency_seconds=latency), T)

def test_datetime_latency_overflow_is_value_error():
    end = datetime.max.replace(tzinfo=timezone.utc)
    with pytest.raises(ValueError, match='Invalid receipt latency'):
        available_feature(feature(issued_at=end, target_at=end, received_at=end,
                                  latency_seconds=1), end)
