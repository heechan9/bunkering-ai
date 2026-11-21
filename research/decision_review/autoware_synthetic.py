"""Frozen synthetic review diagnostics. Not connected to Bunkering runtime."""

from collections import Counter


def coverage(required, entries):
    """Preserve per-source causes; valid subset is not complete evidence."""
    counts = Counter(key for key, _ in entries)
    states = dict(entries)
    return {
        key: ('AMBIGUOUS' if counts[key] > 1 else states.get(key, 'MISSING'))
        for key in required
    }


def corroboration(rows, tolerance):
    """Only pair distinct upstream evidence on the exact same dimension."""
    if len(rows) != 2:
        return 'INSUFFICIENT'
    (origin_a, unit_a, a), (origin_b, unit_b, b) = rows
    if not origin_a or not origin_b or origin_a == origin_b:
        return 'INSUFFICIENT'
    if unit_a != unit_b or unit_a != 't':
        return 'INCOMPARABLE'
    return 'AGREE' if abs(a - b) <= tolerance else 'DISAGREE'


def deadlines(limits, durations):
    """Stage overruns stay visible even when a total fits the total budget."""
    return {stage: ('UNMEASURED' if stage not in durations else
                    'OVERRUN' if durations[stage] > limit else 'WITHIN')
            for stage, limit in limits.items()}


def display_recovery(raw, consecutive_ok):
    """Suppress only premature clearing of display warning; not safety logic."""
    latched, count = False, 0
    displayed = []
    for state in raw:
        if state != 'OK':
            latched, count = True, 0
        elif latched:
            count += 1
            if count >= consecutive_ok:
                latched = False
        displayed.append('RECHECK' if latched and state == 'OK' else state)
    return tuple(displayed)


def alert_window(events, start, end, code):
    """Check time *and reason*, separating missing from wrong-time alerts."""
    events = [time for time, reason in events if reason == code]
    if any(start <= time <= end for time in events):
        return 'ON_TIME'
    if events:
        return 'WRONG_TIME'
    return 'MISSING'


def paired_cases():
    """Known-truth counterexamples; Legacy is a deliberately naive control."""
    expected = ('HOLD', 'INSUFFICIENT', 'OVERRUN', 'RECHECK', 'WRONG_TIME')
    entries = [('port', 'READY'), ('supply', 'STALE')]
    readings = [('same-upstream', 't', 10), ('same-upstream', 't', 10)]
    times = {'capture': 4, 'review': 5}
    sequence = ('HOLD', 'OK', 'HOLD', 'OK', 'OK')
    events = [(1, 'reserve'), (3, 'unrelated')]
    status = coverage(('port', 'supply', 'reserve'), entries)
    reviewed = (
        'COMPLETE' if all(v == 'READY' for v in status.values()) else 'HOLD',
        corroboration(readings, 1),
        deadlines({'capture': 3, 'review': 7}, times)['capture'],
        display_recovery(sequence, 2)[1],
        alert_window(events, 3, 4, 'reserve'),
    )
    naive = (
        'COMPLETE' if any(state == 'READY' for _, state in entries) else 'HOLD',
        'AGREE' if abs(readings[0][2] - readings[1][2]) <= 1 else 'DISAGREE',
        'WITHIN' if sum(times.values()) <= 10 else 'OVERRUN',
        sequence[1],
        'ON_TIME' if any(3 <= time <= 4 for time, _ in events) else 'MISSING',
    )
    return dict(zip(('coverage', 'corroboration', 'watchdog', 'recovery', 'alert_window'),
                    zip(naive, reviewed, expected)))


if __name__ == '__main__':
    import json
    print(json.dumps(paired_cases(), indent=2))
