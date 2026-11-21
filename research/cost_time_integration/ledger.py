"""Independent sequential ledger: no optimizer matrices or project timing calls."""
from collections.abc import Mapping, Set
from decimal import Decimal, DecimalException
import math
from numbers import Real


def _finite_nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise ValueError(name + ': numeric scalar required, not boolean/string')
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError(name + ': finite nonnegative number required')


def _validate_case_numbers(c):
    """Validate direct-ledger inputs without importing the optimizer."""
    if not isinstance(c, dict):
        raise ValueError('case must be a dictionary')
    vectors = ('leg_demands_t', 'arrival_reserves_t', 'supply_max_t',
               'minimum_lift_t', 'fixed_fee_usd', 'variable_fee_usd_per_t')
    for key in vectors + ('prices_usd_per_t', 'available', 'calls'):
        if isinstance(c[key], (Mapping, str, bytes)) or len(c[key]) != 4:
            raise ValueError(key + ': four indexed values required')
    for key in ('capacity_t', 'initial_inventory_t', 'terminal_inventory_exact_t',
                'sailing_hours', 'baseline_existing_call_hours', 'deadline_hours'):
        _finite_nonnegative(c[key], key)
    for key in vectors:
        for i in range(4):
            _finite_nonnegative(c[key][i], f'{key}[{i}]')
    for i in range(4):
        available, price, call = c['available'][i], c['prices_usd_per_t'][i], c['calls'][i]
        if type(available) is not bool:
            raise ValueError(f'available[{i}]: boolean required')
        if price is not None or available:
            _finite_nonnegative(price, f'prices_usd_per_t[{i}]')
        if not isinstance(call, dict) or call.get('kind') not in ('existing', 'dedicated'):
            raise ValueError(f'calls[{i}]: supported call kind required')
        phases = ('preparation_hours', 'cleanup_hours', 'transfer_hours_per_t')
        phases += (('baseline_departure_hours', 'cargo_end_with_bunkering_hours',
                    'bunker_ready_hours', 'departure_readiness_hours')
                   if call['kind'] == 'existing'
                   else ('detour_hours', 'port_transit_hours', 'waiting_hours'))
        for key in phases:
            _finite_nonnegative(call[key], f'calls[{i}].{key}')


def audit(c, q):
    """Fail closed for malformed case inputs or nonfinite arithmetic/results."""
    try:
        if isinstance(q, (Mapping, Set, str, bytes)):
            raise ValueError('quantity must be an ordered numeric iterable, not mapping/set/text')
        _validate_case_numbers(c)
        result = _audit_validated(c, q)
        for key in ('cost_usd', 'time_hours', 'terminal_t'):
            if key in result and not math.isfinite(result[key]):
                raise ValueError(key + ': nonfinite result')
        return result
    except (KeyError, TypeError, ValueError, OverflowError, DecimalException) as exc:
        return dict(valid=False, errors=['invalid ledger input/arithmetic: ' + str(exc)], ledger=[])


def _audit_validated(c, q):
    def invalid(message):
        return dict(valid=False, errors=[message], ledger=[])
    try:
        q = list(q)
    except TypeError:
        return invalid('quantity vector required')
    n = len(c['leg_demands_t'])
    if n != 4 or len(q) != n:
        return invalid('quantity vector length must equal four legs')
    if any(len(c[key]) != n for key in ('calls', 'arrival_reserves_t', 'supply_max_t',
            'available', 'minimum_lift_t', 'prices_usd_per_t', 'fixed_fee_usd', 'variable_fee_usd_per_t')):
        return invalid('case vector shape')
    for raw in q:
        if isinstance(raw, bool) or not isinstance(raw, (Real, Decimal)):
            return invalid('quantity must be a numeric scalar, not boolean/string')
        value = Decimal(str(raw))
        if not value.is_finite() or value < 0:
            return invalid('quantity must be finite and nonnegative')
    D = lambda x: Decimal(str(x))
    tol = D('1e-7'); time_tol = D('1e-6')
    inv = D(c['initial_inventory_t']); cost = D(0)
    total_time = D(c['sailing_hours'])+D(c['baseline_existing_call_hours'])
    rows, errors = [], []
    if inv < D(c['arrival_reserves_t'][0])-tol:
        errors.append('initial reserve')
    for i, raw in enumerate(q):
        qty = D(raw); positive = qty > 0; call = c['calls'][i]
        before = inv; departure = before+qty; inv = departure-D(c['leg_demands_t'][i])
        if qty < 0 or qty > D(c['supply_max_t'][i])+tol: errors.append(f'{i}:supply')
        if positive and not c['available'][i]: errors.append(f'{i}:availability')
        if positive and qty < D(c['minimum_lift_t'][i])-tol: errors.append(f'{i}:minimum')
        if departure > D(c['capacity_t'])+tol: errors.append(f'{i}:capacity')
        if inv < D(c['arrival_reserves_t'][i])-tol: errors.append(f'{i}:arrival reserve')
        # A zero purchase needs no price. Unavailable ports may have price=None.
        subtotal = D(0)
        delay = D(0)
        if positive:
            if c['prices_usd_per_t'][i] is None:
                return invalid(f'{i}:positive purchase requires a known price')
            subtotal = qty*(D(c['prices_usd_per_t'][i])+D(c['variable_fee_usd_per_t'][i]))
            subtotal += D(c['fixed_fee_usd'][i])
            work = D(call['preparation_hours'])+qty*D(call['transfer_hours_per_t'])+D(call['cleanup_hours'])
            if call['kind'] == 'existing':
                finish = max(D(call['cargo_end_with_bunkering_hours']), D(call['bunker_ready_hours'])+work)
                delay = max(D(call['baseline_departure_hours']), finish+D(call['departure_readiness_hours']))-D(call['baseline_departure_hours'])
            else:
                delay = work+sum(D(call[k+'_hours']) for k in ('detour', 'port_transit', 'waiting'))
        cost += subtotal; total_time += delay
        rows.append(dict(before_t=str(before), q_t=str(qty), departure_t=str(departure), arrival_t=str(inv), cost_usd=str(subtotal), extra_hours=str(delay)))
    if abs(inv-D(c['terminal_inventory_exact_t'])) > tol: errors.append('terminal')
    if total_time > D(c['deadline_hours'])+time_tol: errors.append('deadline')
    return dict(valid=not errors, errors=errors, ledger=rows, cost_usd=float(cost), time_hours=float(total_time), terminal_t=float(inv))
