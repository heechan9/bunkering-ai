"""Research-only incremental port-call time; hours on one local timeline."""
from dataclasses import dataclass
import math
from numbers import Real


def hours(value, name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{name}: expected a finite nonnegative number or None')
    try:
        value = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f'{name}: invalid hours') from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{name}: invalid hours')
    return value


@dataclass(frozen=True)
class Delay:
    status: str
    extra_hours: float | None
    missing: tuple[str, ...] = ()


def existing_call(*, baseline_departure=None, cargo_end_with_bunkering=None,
                  bunker_ready=None, preparation=None, transfer=None, cleanup=None):
    """All event offsets use the same origin; durations are sequential.

    baseline_departure is the counterfactual departure without bunkering.
    cargo_end_with_bunkering includes any interruption imposed by bunkering.
    bunker_ready includes waits/access restrictions before preparation starts.
    cleanup includes all remaining bunker-related work before departure.
    """
    values = {k: hours(v, k) for k, v in locals().items()}
    missing = tuple(k for k, v in values.items() if v is None)
    if missing:
        return Delay('UNKNOWN', None, missing)
    end = values['bunker_ready'] + values['preparation'] + values['transfer'] + values['cleanup']
    extra = max(values['baseline_departure'], values['cargo_end_with_bunkering'], end) - values['baseline_departure']
    if not math.isfinite(end) or not math.isfinite(extra):
        raise ValueError('time arithmetic overflow')
    return Delay('KNOWN', extra)


def dedicated_call(*, detour=None, port_transit=None, waiting=None,
                   preparation=None, transfer=None, cleanup=None):
    """Disjoint incremental durations vs the route without this call.

    detour excludes port_transit; waiting excludes work intervals. All phases
    are sequential. User must explicitly provide zero for known zero phases.
    """
    values = {k: hours(v, k) for k, v in locals().items()}
    missing = tuple(k for k, v in values.items() if v is None)
    if missing:
        return Delay('UNKNOWN', None, missing)
    extra = sum(values.values())
    if not math.isfinite(extra):
        raise ValueError('time arithmetic overflow')
    return Delay('KNOWN', extra)


def arrival(*, baseline_hours, calls, deadline_hours):
    """Fixed trace audit; baseline excludes all incremental delays above.

    UNKNOWN propagates; never treat missing time as zero. Does not check fuel
    safety, change policy actions, or model downstream schedule feedback.
    """
    baseline = hours(baseline_hours, 'baseline_hours')
    deadline = hours(deadline_hours, 'deadline_hours')
    calls = list(calls)
    if any(not isinstance(c, Delay) for c in calls):
        raise ValueError('calls must contain Delay results')
    for c in calls:
        if c.status not in ('KNOWN', 'UNKNOWN'):
            raise ValueError('invalid delay status')
        if c.status == 'KNOWN' and (hours(c.extra_hours, 'extra_hours') is None or c.missing):
            raise ValueError('inconsistent known delay')
        if c.status == 'UNKNOWN' and c.extra_hours is not None:
            raise ValueError('inconsistent unknown delay')
    if baseline is None or deadline is None or any(c.status == 'UNKNOWN' for c in calls):
        return {'status': 'UNKNOWN', 'arrival_hours': None, 'on_time': None}
    total = baseline + sum(c.extra_hours for c in calls)
    if not math.isfinite(total):
        raise ValueError('time arithmetic overflow')
    return {'status': 'KNOWN', 'arrival_hours': total, 'on_time': total <= deadline}
