import unittest
from research.procurement_baseline.benchmark import Case,policy,POLICIES,solve,need

def case(name,p=(5,5,5),d=(4,4,4),available=(True,True,True),minimum=(0,0,0),reserve=(0,0,0),C=20,I=0,T=2):
    return Case(name,d,p,available,(C,)*len(d),minimum,(0,)*len(d),(0,)*len(d),reserve,C,I,T)
class Tests(unittest.TestCase):
    def test_price_tie(self):
        c=case('price_tie')
        for p in POLICIES:
            r=policy(c,p);self.assertEqual(r['status'],'FEASIBLE');self.assertAlmostEqual(r['audit']['total_usd'],70)
        self.assertEqual(policy(c,'next_cheaper')['q_t'],[14,0,0])
    def test_price_reversal(self):
        c=case('price_reversal',p=(9,1,9));r=policy(c,'next_cheaper')
        self.assertEqual(r['q_t'],[4,10,0]);self.assertAlmostEqual(r['audit']['total_usd'],solve(c)['objective_usd'])
    def test_supply_gap(self):
        c=case('supply_gap',available=(True,False,True));r=policy(c,'minimum_required')
        self.assertEqual(r['q_t'],[8,0,6]);self.assertEqual(r['status'],'FEASIBLE')
    def test_intermediate_reserve(self):
        c=case('intermediate_reserve',available=(True,False,True),reserve=(9,0,0));r=policy(c,'minimum_required')
        self.assertEqual(r['q_t'],[13,0,1]);self.assertEqual(r['status'],'FEASIBLE')
    def test_terminal_caps_purchase(self):
        c=case('terminal_caps_purchase',I=7)
        for p in POLICIES:
            r=policy(c,p);self.assertEqual(r['status'],'FEASIBLE');self.assertAlmostEqual(sum(r['q_t']),7);self.assertAlmostEqual(r['audit']['terminal_t'],2)
    def test_minimum_lift_failure(self):
        c=case('minimum_lift_failure',minimum=(8,8,8));r=policy(c,'minimum_required')
        self.assertEqual(r['status'],'POLICY_FAILURE');self.assertLessEqual(sum(r['q_t']),14);self.assertEqual(solve(c)['status'],'OPTIMAL')
    def test_unavoidable_infeasible(self):
        c=case('unavoidable_infeasible',available=(False,True,True));self.assertEqual(solve(c)['status'],'INFEASIBLE')
        for p in POLICIES:self.assertEqual(policy(c,p)['status'],'POLICY_FAILURE')
    def test_presolve_counterexample_regression(self):
        c=Case('presolve_counterexample',(6,10,12),(980,470,440),(True,)*3,(30,)*3,(0,)*3,(0,500,0),(20,20,0),(2,2,0),30,7,5)
        r=solve(c);self.assertEqual(r['status'],'OPTIMAL');self.assertAlmostEqual(r['objective_usd'],13000);self.assertTrue(r['audit']['valid'])
    def test_zero_purchase(self):
        c=case('zero_purchase',I=14)
        for p in POLICIES:
            r=policy(c,p);self.assertEqual(r['q_t'],[0,0,0]);self.assertEqual(r['status'],'FEASIBLE')
if __name__=='__main__':unittest.main(verbosity=2)
