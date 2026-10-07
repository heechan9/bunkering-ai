import itertools
import unittest
import numpy as np
from scipy.optimize import linprog
from planner import plan

class PlannerTests(unittest.TestCase):
    def test_matches_independent_stop_enumeration(self):
        rng=np.random.default_rng(672)
        for _ in range(30):
            d=rng.uniform(.12,.4,4);p=rng.uniform(.07,.14,4);f=rng.uniform(1,5,4);v=rng.uniform(1,4,4)
            c=dict(d=d,p=p,fixed=f,variable=v,sailing=10,limit=float(rng.uniform(12,30)),cap=100)
            candidates=[];L=np.tril(np.ones((4,4)))
            for z in itertools.product([0,1],repeat=4):
                r=linprog(p-min(p),A_ub=np.vstack([L,-L,v]),b_ub=np.r_[.5+np.r_[0,np.cumsum(d)[:-1]],.4-np.cumsum(d),c['limit']-10-f@z],bounds=[(0,x) for x in z],method='highs')
                if r.success:candidates.append(float((r.fun+min(p)*sum(d))*100))
            got=plan(c)
            if candidates:self.assertAlmostEqual(got['cost'],min(candidates),places=6)
            else:self.assertIsNone(got)
    def test_impossible_leg_and_sailing(self):
        c=dict(d=[.91],p=[.1],fixed=[1],variable=[1],sailing=1,limit=10,cap=1)
        self.assertIsNone(plan(c));c.update(d=[.1],sailing=11)
        self.assertIsNone(plan(c))
    def test_consolidates_stops_to_meet_deadline(self):
        c=dict(d=[.3]*4,p=[.1,.11,.09,.12],fixed=[5]*4,variable=[1]*4,sailing=10,limit=16,cap=100)
        r=plan(c)
        self.assertIsNotNone(r)
        self.assertLessEqual(r['hours'],16)
        self.assertEqual(int((r['q']>1e-9).sum()),1)
        self.assertAlmostEqual(r['q'][1],.8)
    def test_invalid(self):
        with self.assertRaises(ValueError):plan(dict(d=[float('nan')],p=[.1],fixed=[1],variable=[1],sailing=1,limit=10,cap=1))
        with self.assertRaises(ValueError):plan("not a dict")
        with self.assertRaises(ValueError):plan(dict(d=.1,p=[.1],fixed=[1],variable=[1],sailing=1,limit=10,cap=1))
        with self.assertRaises(ValueError):plan(dict(d=[.1],p=[.1],fixed=[1],variable=[1],sailing=1,limit=10))
        with self.assertRaises(ValueError):plan(dict(d=[[0.1]],p=[[0.1]],fixed=[[1]],variable=[[1]],sailing=1,limit=10,cap=1))

    def test_numerical_noise_cleaning(self):
        # Test controlled solver mock returning q_0 = 1e-10 slack
        # Without q[q < 1e-8] = 0.0, post-processing falsely adds fixed port time (5.0h)
        # causing total hours (15.0h) to exceed limit (12.0h) and fail assertion.
        import sys
        from unittest.mock import patch
        from scipy.optimize import OptimizeResult
        c = dict(d=[0.1], p=[100.0], fixed=[5.0], variable=[1.0], sailing=10.0, limit=12.0, cap=100.0)
        mock_res = OptimizeResult(x=np.array([1e-10, 0.0]), status=0, success=True)
        planner_mod = sys.modules[plan.__module__]
        with patch.object(planner_mod, 'milp', return_value=mock_res):
            res = plan(c)
            self.assertIsNotNone(res)
            self.assertEqual(res['q'][0], 0.0)
            self.assertEqual(res['hours'], 10.0)

    def test_boundary_exact_limits(self):
        # Demand 0.6 requires q >= 0.2 to maintain safe stock 0.1 (initial 0.5 + 0.2 - 0.6 = 0.1)
        # Bunkering time = fixed 2.0 + variable 1.0 * 0.2 = 2.2 hours
        # Total hours = 10.0 + 2.2 = 12.2, matching exact limit 12.2
        c = dict(d=[0.6], p=[100.0], fixed=[2.0], variable=[1.0], sailing=10.0, limit=12.2, cap=100.0)
        res = plan(c)
        self.assertIsNotNone(res)
        self.assertAlmostEqual(res['hours'], 12.2, places=5)

    def test_solver_failure_or_timeout(self):
        # Test solver failure or time limit error (status != 2 and success == False)
        import sys
        from unittest.mock import patch
        from scipy.optimize import OptimizeResult
        c = dict(d=[0.1], p=[100.0], fixed=[1.0], variable=[1.0], sailing=10.0, limit=20.0, cap=100.0)
        mock_failure = OptimizeResult(x=None, status=1, success=False, message="Time limit reached")
        planner_mod = sys.modules[plan.__module__]
        with patch.object(planner_mod, 'milp', return_value=mock_failure):
            with self.assertRaises(RuntimeError) as ctx:
                plan(c)
            self.assertIn("Time limit reached", str(ctx.exception))

if __name__=='__main__':unittest.main()
