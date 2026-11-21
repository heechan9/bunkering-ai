from types import SimpleNamespace
import numpy as np
import pytest
from . import solver
from .test_integration import base

@pytest.mark.parametrize('status', [1, 3, 4])
def test_solver_limit_unbounded_error_not_infeasible(monkeypatch, status):
    monkeypatch.setattr(solver, 'linprog', lambda *a, **k: SimpleNamespace(status=status,success=False,message='injected failure'))
    with pytest.raises(RuntimeError, match='injected failure'):
        solver.solve(base())

def test_missing_time_status_distinct_from_infeasibility():
    c = base(); c['deadline_hours'] = None
    assert solver.solve(c)['status'] == 'NOT_COMPUTED_UNKNOWN_TIME'
    c['deadline_hours'] = 23
    assert solver.solve(c)['status'] == 'INFEASIBLE'

def test_boolean_transfer_rate_is_invalid():
    c = base(); c['calls'][1]['transfer_hours_per_t'] = True
    with pytest.raises(ValueError): solver.solve(c)

def test_nonfinite_lp_answer_is_solver_error(monkeypatch):
    monkeypatch.setattr(solver, 'linprog', lambda *a, **k: SimpleNamespace(status=0,success=True,x=np.full(8, float('nan'))))
    with pytest.raises(RuntimeError): solver.solve(base())
