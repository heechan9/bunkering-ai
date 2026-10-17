"""Four-call synthetic continuous procurement/time integration; no training."""
from itertools import product
import math
import numpy as np
from scipy.optimize import linprog
from research.procurement_baseline.procurement import Case
from research.port_call_time.model import existing_call, dedicated_call, hours
from .ledger import audit


def validate_contract(c):
    """Accept only this adapter's explicit synthetic, static t/USD/hour schema."""
    if not isinstance(c, dict):
        raise ValueError('case must be a dictionary')
    required = {'data_kind', 'information_tier', 'capacity_t', 'initial_inventory_t',
                'terminal_inventory_exact_t', 'leg_demands_t', 'arrival_reserves_t',
                'prices_usd_per_t', 'supply_max_t', 'minimum_lift_t', 'available',
                'fixed_fee_usd', 'variable_fee_usd_per_t', 'calls'}
    units = {'price_unit': 'USD/t', 'mass_unit': 't', 'currency': 'USD', 'time_unit': 'h'}
    allowed = required | set(units) | {'sailing_hours', 'baseline_existing_call_hours', 'deadline_hours'}
    if set(c)-allowed or required-set(c):
        raise ValueError(f'unsupported/missing case fields: {sorted(set(c)-allowed)}, {sorted(required-set(c))}')
    if c['data_kind'] != 'synthetic_assumption' or c['information_tier'] != 'STATIC_KNOWN':
        raise ValueError('Only synthetic_assumption STATIC_KNOWN inputs supported')
    for key, expected in units.items():
        if key in c and c[key] != expected:
            raise ValueError(f'{key}: only {expected} supported; no implicit conversion')
    if not isinstance(c['calls'], (list, tuple)) or len(c['calls']) != 4:
        raise ValueError('four call records required')
    common = {'kind', 'preparation_hours', 'cleanup_hours', 'transfer_hours_per_t'}
    for call in c['calls']:
        if not isinstance(call, dict) or call.get('kind') not in ('existing', 'dedicated'):
            raise ValueError('unsupported call kind')
        phases = ({'baseline_departure_hours', 'cargo_end_with_bunkering_hours',
                   'bunker_ready_hours', 'departure_readiness_hours'} if call['kind']=='existing'
                  else {'detour_hours', 'port_transit_hours', 'waiting_hours'})
        if set(call)-(common | phases):
            raise ValueError('unsupported call fields: '+str(sorted(set(call)-(common | phases))))


def procurement_case(c):
    validate_contract(c)
    return Case('integration', tuple(c['leg_demands_t']), tuple(c['prices_usd_per_t']),
                tuple(c['available']), tuple(c['supply_max_t']), tuple(c['minimum_lift_t']),
                tuple(c['fixed_fee_usd']), tuple(c['variable_fee_usd_per_t']),
                tuple(c['arrival_reserves_t']), c['capacity_t'], c['initial_inventory_t'],
                c['terminal_inventory_exact_t']).validate()


def timing(c, q):
    if q == 0:
        return 0.0
    common = {k: c.get(k+'_hours') for k in ('preparation', 'cleanup')}
    rate = hours(c.get('transfer_hours_per_t'), 'transfer_hours_per_t')
    common['transfer'] = None if rate is None else rate*q
    if c['kind'] == 'existing':
        result = existing_call(**common, **{k: c.get(k+'_hours') for k in
            ('baseline_departure', 'cargo_end_with_bunkering', 'bunker_ready', 'departure_readiness')})
    elif c['kind'] == 'dedicated':
        result = dedicated_call(**common, **{k: c.get(k+'_hours') for k in ('detour', 'port_transit', 'waiting')})
    else:
        raise ValueError('unsupported call kind')
    return result.extra_hours


def solve(c):
    pc = procurement_case(c)
    if len(pc.d) != 4 or len(c['calls']) != 4:
        raise ValueError('This research adapter requires four calls')
    for key in ('sailing_hours', 'baseline_existing_call_hours', 'deadline_hours'):
        value = c.get(key)
        if value is None:
            return {'status': 'NOT_COMPUTED_UNKNOWN_TIME'}
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(key)
    # Validate even unused call records. Unknown inputs cannot become implicit zero.
    if any(timing(call, 1) is None for call in c['calls']):
        return {'status': 'NOT_COMPUTED_UNKNOWN_TIME'}
    baseline = c['sailing_hours'] + c['baseline_existing_call_hours']
    if pc.initial < pc.reserve[0]:
        return {'status': 'INFEASIBLE', 'patterns_checked': 16}
    candidates, patterns = [], []
    prices = pc.prices  # Case explicitly permits None prices at unavailable ports.
    for z in product((0, 1), repeat=4):
        # Four q and four incremental-delay epigraph variables.
        A, b = [], []
        for i in range(4):
            prefix = [int(j <= i) for j in range(4)] + [0]*4
            A.append([-v for v in prefix]); b.append(pc.initial-sum(pc.d[:i+1])-pc.reserve[i])
            A.append(prefix); b.append(pc.capacity-pc.initial+sum(pc.d[:i]))
            if not z[i]:
                continue
            call = c['calls'][i]
            slope = call['transfer_hours_per_t']
            row = [0.0]*8; row[i] = slope; row[4+i] = -1
            if call['kind'] == 'dedicated':
                intercept = sum(call[k+'_hours'] for k in ('detour', 'port_transit', 'waiting', 'preparation', 'cleanup'))
            else:
                intercept = sum(call[k+'_hours'] for k in ('bunker_ready', 'preparation', 'cleanup', 'departure_readiness')) - call['baseline_departure_hours']
                extra = [0.0]*8; extra[4+i] = -1
                A.append(extra); b.append(call['baseline_departure_hours']-call['cargo_end_with_bunkering_hours']-call['departure_readiness_hours'])
            A.append(row); b.append(-intercept)
        A.append([0]*4+[1]*4); b.append(c['deadline_hours']-baseline)
        bounds = [(pc.minimum[i], min(pc.supply[i], pc.capacity)) if z[i] and pc.available[i] else (0, 0) for i in range(4)]
        if any(lo > hi for lo, hi in bounds):
            patterns.append({'pattern': z, 'status': 'INFEASIBLE_BOUNDS'}); continue
        r = linprog(list(prices+np.array(pc.variable))+[0]*4,
                    A_ub=A, b_ub=b, A_eq=[[1]*4+[0]*4],
                    b_eq=[sum(pc.d)+pc.terminal-pc.initial],
                    bounds=bounds+[(0, None) if on else (0, 0) for on in z],
                    method='highs', options={'presolve': False,
                    'primal_feasibility_tolerance': 1e-9, 'dual_feasibility_tolerance': 1e-9})
        patterns.append({'pattern': z, 'status': int(r.status)})
        if r.status == 2:
            continue
        if not r.success:
            raise RuntimeError(r.message)
        if np.shape(r.x) != (8,) or not np.isfinite(r.x).all():
            raise RuntimeError('SOLVER_ERROR: invalid/nonfinite LP solution')
        q = r.x[:4].tolist()
        if any(qty < 0 for qty in q):
            raise RuntimeError('SOLVER_ERROR: negative purchase; no rounding permitted')
        # No epsilon lot size and no physical-quantity rounding. A closure solution
        # with zero selected purchase belongs to its smaller support, enumerated too.
        if any((qty > 0) != bool(on) for qty, on in zip(q, z)):
            patterns[-1]['discarded'] = 'support mismatch'; continue
        cost = sum(q[i]*(prices[i]+pc.variable[i])+z[i]*pc.fixed[i] for i in range(4))
        delays = [timing(call, qty) for call, qty in zip(c['calls'], q)]
        total_time = baseline+sum(delays)
        checked = audit(c, q)
        if (not checked['valid'] or abs(cost-checked['cost_usd']) > .0001
                or abs(total_time-checked['time_hours']) > .000001):
            raise RuntimeError('SOLVER_ERROR: independent audit rejected LP success: '+str(checked['errors']))
        candidates.append({'status': 'FEASIBLE_OPTIMAL', 'purchases_t': q,
                           'cost_usd': cost, 'time_hours': total_time,
                           'incremental_delays_hours': delays, 'positive_purchase_count': sum(z)})
    if not candidates:
        return {'status': 'INFEASIBLE', 'patterns_checked': 16, 'patterns': patterns}
    answer = min(candidates, key=lambda x: x['cost_usd'])
    answer.update(patterns_checked=16, patterns=patterns)
    return answer
