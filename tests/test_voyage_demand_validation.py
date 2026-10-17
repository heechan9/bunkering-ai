"""Entirely synthetic fixtures; these tests measure no vessel performance."""
from datetime import datetime, timedelta, timezone
import pytest
from research.voyage_demand.validation import (
    Voyage, available_feature, baseline_tonnes, chronological_split,
    consumption_metrics, fit_training_preprocessor, integrate_rate, require_window_inside, rob_residual,
)

T = datetime(2030, 1, 1, tzinfo=timezone.utc)


def feature(**changes):
    row = dict(name='planned_speed', unit='kn', source='synthetic plan', kind='plan',
               issued_at=T, target_at=T+timedelta(days=1), received_at=T,
               latency_seconds=0, missing_policy='reject', available_at_purchase=True)
    return row | changes


def interval(start=0, end=1, rate=1000, unit='L/h'):
    return dict(start=T+timedelta(hours=start), end=T+timedelta(hours=end), rate=rate, unit=unit)


def integrate(rows, **changes):
    return integrate_rate(rows, **(dict(start=T, end=T+timedelta(hours=2),
                          density_kg_l=0.8, density_basis='synthetic kg/L at 15 C',
                          expected_interval_hours=1) | changes))


def test_plan_and_forecast_available_before_purchase():
    assert available_feature(feature(), T)
    assert available_feature(feature(kind='forecast'), T)


@pytest.mark.parametrize('changes', [dict(kind='observation'), dict(post_voyage_aggregate=True),
    dict(received_at=T+timedelta(seconds=1)), dict(issued_at=T+timedelta(seconds=1)),
    dict(source=None), dict(latency_seconds=1), dict(available_at_purchase=False),
    dict(kind='unknown'), dict(target_at=datetime(2030, 1, 1))])
def test_unavailable_or_undocumented_feature_rejected(changes):
    with pytest.raises(ValueError):
        available_feature(feature(**changes), T)


def voyages(n=4):
    return [Voyage(str(i), T+timedelta(days=2*i), T+timedelta(days=2*i+1)) for i in range(n)]


def test_whole_voyage_order_and_no_window_overlap():
    split = chronological_split(list(reversed(voyages())))
    assert [v.key for v in split['train']] == ['0', '1']
    assert [v.key for v in split['calibration']] == ['2']
    assert [v.key for v in split['test']] == ['3']
    require_window_inside(voyages()[0], T, T+timedelta(hours=2))
    with pytest.raises(ValueError):
        require_window_inside(voyages()[0], T, T+timedelta(days=2))


@pytest.mark.parametrize('rows', [voyages(1), voyages(2), [voyages()[0], voyages()[0]],
    [Voyage('a', T, T+timedelta(days=3)), *voyages()[1:]]])
def test_insufficient_duplicate_and_overlapping_voyages(rows):
    with pytest.raises(ValueError):
        chronological_split(rows)


def test_explicit_density_and_duration_conversion():
    assert integrate([interval(), interval(1, 2, 2000)]) == pytest.approx(2.4)
    assert integrate([interval(rate=0), interval(1, 2, 0)]) == 0


@pytest.mark.parametrize('rows', [[], [interval()], [interval(), interval()],
    [interval(), interval(1.5, 2)], [interval(0, 0.5), interval(0.5, 2)],
    [interval(unit='kL/h'), interval(1, 2)], [interval(rate=None), interval(1, 2)],
    [interval(rate=float('nan')), interval(1, 2)]])
def test_missing_duplicate_irregular_and_mixed_units_rejected(rows):
    with pytest.raises(ValueError):
        integrate(rows)


@pytest.mark.parametrize('changes', [dict(density_kg_l=None), dict(density_kg_l=0),
    dict(density_basis=''), dict(expected_interval_hours=0)])
def test_conversion_metadata_required(changes):
    with pytest.raises(ValueError):
        integrate([interval(), interval(1, 2)], **changes)


def test_weighted_training_baseline_and_future_training_rejection():
    training = [interval(0, 1, 1000) | {'received_at': T+timedelta(hours=1)},
                interval(1, 3, 2000) | {'received_at': T+timedelta(hours=3)}]
    kwargs = dict(fitted_before=T+timedelta(hours=4), purchase_at=T+timedelta(hours=5),
                  planned_hours=6, density_kg_l=0.8, density_basis='synthetic 15 C')
    assert baseline_tonnes(training, **kwargs) == pytest.approx(8)
    with pytest.raises(ValueError):
        baseline_tonnes(training, **(kwargs | {'fitted_before': T+timedelta(hours=2)}))


def test_total_consumption_metrics_and_rob_conservation():
    metrics = consumption_metrics([2, 4], [1, 5])
    assert metrics == dict(n=2, mae_t=1, rmse_t=1, bias_t=0,
                           underprediction_frequency=0.5, shortfall_total_t=1)
    assert rob_residual(opening=10, supplied=2, consumed=3, closing=9, unit='t') == 0
    with pytest.raises(ValueError):
        rob_residual(opening=10, supplied=None, consumed=3, closing=7, unit='t')
    with pytest.raises(ValueError):
        rob_residual(opening=10, supplied=0, consumed=3, closing=7, unit='kL')


def test_preprocessing_fit_rejects_calibration_test_and_future_data():
    rows = [dict(voyage_key='train', target_at=T, received_at=T, value=v) for v in [1, 3]]
    kwargs = dict(train_keys={'train'}, fitted_before=T+timedelta(days=1))
    assert fit_training_preprocessor(rows, **kwargs) == dict(mean=2, scale=1, n_training=2)
    for extra in [rows[0] | {'voyage_key': 'test', 'value': 1000},
                  rows[0] | {'target_at': T+timedelta(days=2)},
                  rows[0] | {'received_at': T+timedelta(days=2)}, rows[0] | {'value': None}]:
        with pytest.raises(ValueError):
            fit_training_preprocessor(rows+[extra], **kwargs)


def test_elapsed_hours_use_absolute_time_across_offset_change():
    assert integrate_rate([dict(start='2030-03-31T00:00:00+01:00',
        end='2030-04-01T00:00:00+02:00', rate=1000, unit='L/h')],
        start='2030-03-31T00:00:00+01:00', end='2030-04-01T00:00:00+02:00',
        density_kg_l=0.8, density_basis='synthetic 15 C', expected_interval_hours=23
        ) == pytest.approx(18.4)


def test_baseline_rejects_duplicate_training_intervals():
    row = interval() | {'received_at': T+timedelta(hours=1)}
    with pytest.raises(ValueError, match='duplicated'):
        baseline_tonnes([row, row], fitted_before=T+timedelta(hours=2),
            purchase_at=T+timedelta(hours=3), planned_hours=1,
            density_kg_l=0.8, density_basis='synthetic 15 C')
