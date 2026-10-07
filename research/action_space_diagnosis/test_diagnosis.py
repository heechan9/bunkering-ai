import unittest
import numpy as np
from run import evaluate, oracle, solve

class DiagnosisTests(unittest.TestCase):
    def test_analytic_lp(self):
        q=solve([1.,2.],[.4,.4],1.,.1,.1,[True,True])
        np.testing.assert_allclose(q,[.8,0.],atol=1e-8)

    def test_flat_price_identity(self):
        d=[.2,.3,.2,.2]
        for actions in [(0,0,0,0),(4,4,4,4),(2,1,3,0)]:
            value,trace=evaluate(d,[1.]*4,actions)
            self.assertAlmostEqual(value,sum(d))
            self.assertAlmostEqual(.5+sum(t['purchase'] for t in trace)-sum(d),trace[-1]['closing'])

    def test_impossible_leg(self):
        self.assertIsNone(solve([1.],[1.],1.,.5,.1,[True]))
        self.assertEqual(evaluate([1.,.1,.1,.1],[1.]*4,[4]*4)[0],float('inf'))

    def test_discrete_counterexample(self):
        d=[.24,.29,.13,.24];p=[1.13,.90,1.27,.72]
        old,_,_=oracle(d,p);new,_,_=oracle(d,p,True)
        # Hand solution: buy .26 at port 1 and .24 at port 3.
        expected=.26*.90+.24*.72+.72*(.5-.1)
        self.assertAlmostEqual(new,expected)
        self.assertGreater(old,new+1e-5)
        self.assertAlmostEqual(evaluate(d,p,[5]*4,True)[0],expected)

if __name__=='__main__':unittest.main()
