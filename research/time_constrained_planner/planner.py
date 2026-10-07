"""Exact mixed-integer planner for the fixed-price, known-demand research model."""
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint


def plan(c):
    required_keys = ('d', 'p', 'fixed', 'variable', 'sailing', 'limit', 'cap')
    if not isinstance(c, dict):
        raise ValueError('Input must be a dictionary')
    for k in required_keys:
        if k not in c:
            raise ValueError(f'Missing required key: {k}')
    try:
        d, p, f, v = (np.asarray(c[k], dtype=float) for k in ('d', 'p', 'fixed', 'variable'))
        sailing = float(c['sailing'])
        limit = float(c['limit'])
        cap = float(c['cap'])
    except (ValueError, TypeError) as e:
        raise ValueError(f'Invalid numeric inputs: {e}') from e

    if any(x.ndim != 1 for x in (d, p, f, v)):
        raise ValueError('Equal nonempty 1D vectors required')
    n = len(d)
    if n == 0 or any(x.shape != (n,) for x in (p, f, v)):
        raise ValueError('Equal nonempty 1D vectors required')
    if not all(np.isfinite(x).all() for x in (d, p, f, v)) or any((x < 0).any() for x in (d, p, f, v)):
        raise ValueError('Finite nonnegative inputs required')
    if not all(np.isfinite(x) for x in (sailing, limit, cap)) or cap <= 0 or sailing < 0 or limit <= 0:
        raise ValueError('Invalid capacity or time')

    # q purchases (tank fractions), z binary stop indicators. q <= z.
    lower = np.tril(np.ones((n, n)))
    zero = np.zeros((n, n))
    A = np.vstack([np.c_[lower, zero], np.c_[np.eye(n), -np.eye(n)], np.r_[v, f][None, :]])
    lo = np.r_[np.cumsum(d) + .1 - .5, np.full(n, -np.inf), -np.inf]
    hi = np.r_[1 - .5 + np.r_[0, np.cumsum(d)[:-1]], np.zeros(n), limit - sailing]
    result = milp(np.r_[p - min(p), np.zeros(n)], integrality=np.r_[np.zeros(n), np.ones(n)],
                  bounds=Bounds(np.zeros(2 * n), np.ones(2 * n)), constraints=LinearConstraint(A, lo, hi),
                  options={'mip_rel_gap': 0.0})
    if result.status == 2:
        return None
    if not result.success:
        raise RuntimeError(result.message)

    q = np.maximum(0.0, result.x[:n])
    # Numerical noise cleanup: threshold 1e-8 tank fraction (for a 100,000 MT capacity vessel,
    # 1e-8 corresponds to 0.001 MT / 1 kg), which is well below the solver's primal feasibility tolerance (1e-7).
    # Cleaning near-zero floating point artifacts prevents incorrectly incurring fixed port bunkering time f_i.
    q[q < 1e-8] = 0.0
    inv = .5 + np.cumsum(q - d)
    hours = float(sailing + v @ q + f @ (q > 0.0))
    assert np.all(inv >= .1 - 1e-7) and np.all(inv + d <= 1 + 1e-7)
    assert hours <= limit + 1e-6
    cost = float((q @ p + min(p) * (.5 - inv[-1])) * cap)
    return dict(q=q, cost=cost, hours=hours, safe=True, feasible=True)
