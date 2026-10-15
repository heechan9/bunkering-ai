import unittest
from dataclasses import replace, asdict
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from research.procurement_baseline.procurement import Case,solve,audit,enumerate_stops,price_to_usd_t,solver_status

BASE=Case('base',(30.,40.),(600.,400.),(True,True),(100.,100.),(0.,0.),(0.,0.),(0.,0.),(10.,10.))
class ProcurementTests(unittest.TestCase):
    def optimal(self,c=BASE,cost=28000,q=None,mode='auto'):
        r=solve(c,mode);self.assertEqual(r['status'],'OPTIMAL',r)
        self.assertTrue(r['audit']['valid']);self.assertAlmostEqual(r['objective_usd'],cost,places=4)
        if q is not None:np.testing.assert_allclose(r['q_t'],q,atol=1e-6)
        return r
    def test_U01(self):self.optimal(q=[20,40])
    def test_U02(self):self.optimal(replace(BASE,p=(400,600)),24000,[60,0])
    def test_U03(self):self.optimal(replace(BASE,p=(500,500)),30000)
    def test_U04(self):self.optimal(replace(BASE,fixed=(0,10000)),36000,[60,0])
    def test_U05(self):self.optimal(replace(BASE,available=(True,False),p=(600,None)),36000,[60,0])
    def test_U06(self):self.optimal(replace(BASE,minimum=(0,50)),36000,[60,0])
    def test_U07(self):
        c=Case('impossible',(95,),(500,),(True,),(100,),(0,),(0,),(0,),(10,))
        self.assertEqual(solve(c)['status'],'INFEASIBLE')
    def test_U08(self):self.assertEqual(solve(replace(BASE,terminal=5))['status'],'INVALID_INPUT')
    def test_U09(self):self.assertEqual(solve(replace(BASE,initial=90,d=(10,10)))['status'],'INFEASIBLE')
    def test_U10_price_conversion(self):
        self.optimal(replace(BASE,p=(price_to_usd_t(.6,'currency/kg'),400)))
        self.assertEqual(price_to_usd_t(600,'currency/t'),600)
        self.assertAlmostEqual(price_to_usd_t(500,'currency/t',1.2),600)
        for unit,direction in [('currency/L','USD/source'),('currency/t','source/USD')]:
            with self.assertRaises(ValueError):price_to_usd_t(1,unit,1,direction)
    def test_U11(self):self.assertEqual(solve(replace(BASE,supply=(19,100)))['status'],'INFEASIBLE')
    def test_U12(self):self.assertEqual(solve(replace(BASE,p=(600,400,100)))['status'],'INVALID_INPUT')
    def test_U13_unknown_price(self):self.assertEqual(solve(replace(BASE,p=(600,None)))['status'],'NOT_READY')
    def test_U14(self):
        c=replace(BASE,p=(400,600));a=self.optimal(c,24000,mode='lp');b=self.optimal(c,24000,mode='milp')
        np.testing.assert_allclose(b['z'],[1,0],atol=1e-7)
        self.assertEqual(a['objective_usd'],b['objective_usd'])
    def test_U15_enumeration(self):
        rng=np.random.default_rng(20261015)
        for n in (2,3,4):
            for j in range(12):
                c=Case(f'enumeration-{n}-{j}',tuple(rng.integers(5,65,n)),tuple(rng.integers(100,900,n)),tuple(bool(x) for x in rng.integers(0,2,n)),tuple(rng.integers(15,101,n)),tuple(rng.integers(0,31,n)),tuple(rng.integers(0,10001,n)),tuple(rng.integers(0,51,n)),tuple([10]*n))
                a=solve(c,'milp');b=enumerate_stops(c)
                self.assertEqual(a['status'],b['status'],(asdict(c),a,b))
                if a['status']=='OPTIMAL':self.assertAlmostEqual(a['objective_usd'],b['best']['objective_usd'],places=4)
    def test_U16_mass_boundaries(self):
        c=replace(BASE,minimum=(20,40),supply=(20,40))
        self.optimal(c)
        self.assertEqual(solve(replace(c,supply=(19.999,40)))['status'],'INFEASIBLE')
        self.assertFalse(audit(c,[20,39.999],[1,1])['valid'])
    def test_U17_statuses(self):
        for status,expected in [(1,'LIMIT_REACHED'),(2,'INFEASIBLE'),(4,'SOLVER_ERROR')]:
            for mode,func in [('lp','linprog'),('milp','milp')]:
                with patch('research.procurement_baseline.procurement.'+func,return_value=SimpleNamespace(status=status,message='mock')):
                    self.assertEqual(solve(BASE,mode)['status'],expected)
        with patch('research.procurement_baseline.procurement.linprog',side_effect=RuntimeError('mock numeric failure')):
            self.assertEqual(solve(BASE)['status'],'SOLVER_ERROR')
    def test_reject_bool_nan_inf_unknown(self):
        for value in (True,np.bool_(False),float('nan'),float('inf'),-float('inf'),-1,'3'):
            for field in ('capacity','initial','terminal'):
                self.assertEqual(solve(replace(BASE,**{field:value}))['status'],'INVALID_INPUT',(field,value))
            for field in ('d','p','supply','minimum','fixed','variable','reserve'):
                self.assertEqual(solve(replace(BASE,**{field:(value,40)}))['status'],'INVALID_INPUT',(field,value))
        for value in (None,'unknown',''):
            self.assertEqual(solve(replace(BASE,p=(value,400)))['status'],'NOT_READY')
    def test_availability_unknown_not_false(self):
        self.assertEqual(solve(replace(BASE,available=(None,True)))['status'],'NOT_READY')
        self.assertEqual(solve(replace(BASE,available=(1,True)))['status'],'INVALID_INPUT')
    def test_unit_scope_rejection(self):
        for field,value in [('mass_unit','kg'),('currency','EUR'),('data_kind','observational'),('information_tier','CAUSAL_CURRENT')]:
            self.assertEqual(solve(replace(BASE,**{field:value}))['status'],'INVALID_INPUT')
    def test_variable_fees(self):self.optimal(replace(BASE,variable=(0,300)),36000,[60,0])
    def test_no_silent_lp_relaxation(self):self.assertEqual(solve(replace(BASE,fixed=(1,0)),'lp')['status'],'INVALID_INPUT')
    def test_auditor_tamper(self):
        for q,z,obj in [([19,41],[1,1],None),([20,41],[1,1],None),([20,40],[1,1],1),([60,0],[1,1],None),([float('nan'),40],[1,1],None),([20,40],[.5,1],None)]:
            self.assertFalse(audit(BASE,q,z,obj)['valid'])
    def test_zero_price_and_no_purchase(self):
        self.optimal(replace(BASE,p=(0,0)),0,mode='milp')
        r=self.optimal(replace(BASE,initial=80),0,[0,0],mode='milp');self.assertEqual(r['z'],[0,0])
    def test_minimum_above_supply(self):self.optimal(replace(BASE,minimum=(0,101)),36000,[60,0])
    def test_subprecision_fixed_fee_rejected(self):
        c=Case('tiny-fee',(1,),(600,),(True,),(100,),(1e-7,),(1,),(0,),(0,),initial=1-1e-7,terminal=0)
        self.assertEqual(solve(c)['status'],'INVALID_INPUT')
        self.assertEqual(solve(replace(c,minimum=(0,)))['status'],'INVALID_INPUT')
        self.assertEqual(solve(replace(BASE,capacity=1001))['status'],'INVALID_INPUT')
        self.assertEqual(solve(replace(BASE,mass_input_precision_t=.000001))['status'],'INVALID_INPUT')
        # Smallest supported shortage still triggers actual fixed fee.
        c=replace(c,initial=.999,minimum=(.001,))
        self.optimal(c,1.6,[.001])
    def test_one_leg_exact_capacity(self):
        c=Case('boundary',(90,),(500,),(True,),(100,),(80,),(10,),(2,),(10,))
        self.optimal(c,40170,[80])

if __name__=='__main__':unittest.main(verbosity=2)
