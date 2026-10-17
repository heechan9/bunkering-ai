"""Preparation utilities only: no vessel records, fitted models or performance claims."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite, sqrt
from statistics import mean


def timestamp(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('A timezone-aware timestamp is required')
    return value.astimezone(timezone.utc)


def number(value, *, positive=False):
    if isinstance(value, bool) or value is None:
        raise ValueError('Missing or invalid numeric input')
    value = float(value)
    if not isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError('A finite nonnegative value is required')
    return value


def available_feature(field, purchase_at):
    """Fail closed on unknown provenance, timing, or post-decision measurements."""
    required = ('name', 'unit', 'source', 'kind', 'issued_at', 'target_at',
                'received_at', 'latency_seconds', 'missing_policy', 'available_at_purchase')
    if any(key not in field or field[key] is None or field[key] == '' for key in required):
        raise ValueError('Incomplete feature dictionary')
    decision = timestamp(purchase_at)
    issued, target, received = (timestamp(field[key]) for key in
                                ('issued_at', 'target_at', 'received_at'))
    latency = number(field['latency_seconds'])
    if received < issued or received < issued + timedelta(seconds=latency):
        raise ValueError('Inconsistent receipt latency')
    if field['available_at_purchase'] is not True or received > decision or issued > decision:
        raise ValueError('Feature unavailable at purchase')
    if field['kind'] not in ('observation', 'forecast', 'plan', 'static'):
        raise ValueError('Unknown feature kind')
    if field['kind'] == 'observation' and target > decision:
        raise ValueError('Future observations are not planning inputs')
    if field.get('post_voyage_aggregate', False):
        raise ValueError('Post-voyage aggregates are excluded')
    return True


@dataclass(frozen=True)
class Voyage:
    key: str
    start: datetime
    end: datetime


def chronological_split(voyages, *, calibration_count=1, test_count=1):
    """Whole non-overlapping voyages only; fewer than three cannot support three sets."""
    if calibration_count < 1 or test_count < 1:
        raise ValueError('Calibration and test require complete voyages')
    ordered = sorted(voyages, key=lambda v: timestamp(v.start))
    if len({v.key for v in ordered}) != len(ordered):
        raise ValueError('Duplicate voyage key')
    for i, voyage in enumerate(ordered):
        if timestamp(voyage.end) <= timestamp(voyage.start):
            raise ValueError('Invalid voyage interval')
        if i and timestamp(ordered[i-1].end) >= timestamp(voyage.start):
            raise ValueError('Voyages overlap or share boundary observations')
    if len(ordered) < calibration_count + test_count + 1:
        raise ValueError('Insufficient independent voyages; pipeline checks only')
    cutoff = len(ordered) - calibration_count - test_count
    return {'train': ordered[:cutoff], 'calibration': ordered[cutoff:-test_count],
            'test': ordered[-test_count:]}


def require_window_inside(voyage, window_start, window_end):
    if not (timestamp(voyage.start) <= timestamp(window_start) < timestamp(window_end)
            <= timestamp(voyage.end)):
        raise ValueError('Window crosses a voyage boundary')


def fit_training_preprocessor(rows, *, train_keys, fitted_before):
    """Example scalar centering only; no imputation, feature selection or model fit."""
    if not rows or not train_keys:
        raise ValueError('Training rows and partition membership required')
    cutoff = timestamp(fitted_before)
    values = []
    for row in rows:
        if row['voyage_key'] not in train_keys or timestamp(row['received_at']) >= cutoff:
            raise ValueError('Preprocessing must use available training rows only')
        if timestamp(row['target_at']) >= cutoff:
            raise ValueError('Future observation in preprocessing')
        values.append(number(row['value']))
    center = mean(values)
    scale = sqrt(mean((v-center)**2 for v in values)) or 1.0
    return {'mean': center, 'scale': scale, 'n_training': len(values)}


def integrate_rate(intervals, *, start, end, density_kg_l, density_basis,
                   expected_interval_hours):
    """Left-constant interval mean L/h, explicit contiguous intervals; no resampling."""
    density = number(density_kg_l, positive=True)
    step = number(expected_interval_hours, positive=True)
    if not density_basis:
        raise ValueError('Fuel density reference conditions/source required')
    cursor, finish = timestamp(start), timestamp(end)
    if finish <= cursor or not intervals:
        raise ValueError('Empty or reversed integration period')
    tonnes = 0.0
    for interval in intervals:
        left, right = timestamp(interval['start']), timestamp(interval['end'])
        hours = (right - left).total_seconds() / 3600
        if left != cursor or hours <= 0 or abs(hours-step) > 1e-9 or right > finish:
            raise ValueError('Duplicate, overlapping, missing or irregular interval')
        if interval['unit'] != 'L/h':
            raise ValueError('Mixed or unsupported rate unit')
        tonnes += number(interval['rate']) * hours * density / 1000
        cursor = right
    if cursor != finish:
        raise ValueError('Incomplete period coverage')
    return tonnes


def baseline_tonnes(training, *, fitted_before, purchase_at, planned_hours,
                    density_kg_l, density_basis):
    """Duration-weighted historical mean rate, fitted using training intervals only."""
    cutoff, decision = timestamp(fitted_before), timestamp(purchase_at)
    if cutoff > decision or not training or not density_basis:
        raise ValueError('Missing training evidence or invalid fitting cutoff')
    litres = hours = 0.0
    previous_end = None
    for row in training:
        if timestamp(row['end']) >= cutoff or timestamp(row['received_at']) > cutoff:
            raise ValueError('Training data not available before fitting cutoff')
        if timestamp(row['received_at']) < timestamp(row['end']):
            raise ValueError('Interval average cannot be observed before interval end')
        if previous_end is not None and timestamp(row['start']) < previous_end:
            raise ValueError('Training intervals duplicated, overlapping or unordered')
        previous_end = timestamp(row['end'])
        if row['unit'] != 'L/h':
            raise ValueError('Training rate unit must be L/h')
        duration = (timestamp(row['end'])-timestamp(row['start'])).total_seconds()/3600
        duration = number(duration, positive=True)
        litres += number(row['rate']) * duration
        hours += duration
    return litres/hours * number(planned_hours, positive=True) * number(density_kg_l, positive=True)/1000


def consumption_metrics(actual_t, predicted_t):
    if not actual_t or len(actual_t) != len(predicted_t):
        raise ValueError('Require aligned port-to-port totals')
    errors = [number(p)-number(a) for a, p in zip(actual_t, predicted_t)]
    return {'n': len(errors), 'mae_t': mean(abs(e) for e in errors),
            'rmse_t': sqrt(mean(e*e for e in errors)), 'bias_t': mean(errors),
            'underprediction_frequency': mean(e < 0 for e in errors),
            'shortfall_total_t': sum(max(0, -e) for e in errors)}


def rob_residual(*, opening, supplied, consumed, closing, unit):
    if unit != 't':
        raise ValueError('ROB conservation requires explicit common tonne units')
    return number(opening) + number(supplied) - number(consumed) - number(closing)
