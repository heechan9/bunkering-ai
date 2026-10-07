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
if __name__=='__main__':unittest.main()
