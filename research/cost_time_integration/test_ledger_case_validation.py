"""Direct-ledger input regression tests; stdlib unittest, no pytest required."""
import copy
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
import unittest
from research.cost_time_integration import ledger

BASE = json.loads((Path(ledger.__file__).parent/'fixtures_compact.json').read_text())['base']
Q = [0, 16, 0, 0]

class LedgerCaseValidation(unittest.TestCase):
    def assert_invalid(self, case, q=Q):
        result = ledger.audit(case, q)
        self.assertIs(result['valid'], False)
        self.assertTrue(result['errors'])
        self.assertIsInstance(result['errors'][0], str)

    def test_valid_baseline_unchanged(self):
        r = ledger.audit(copy.deepcopy(BASE), Q)
        self.assertTrue(r['valid']); self.assertEqual(r['cost_usd'], 7200)
        self.assertAlmostEqual(r['time_hours'],26.32);self.assertEqual(r['terminal_t'],6)

    def test_unavailable_unknown_price_zero_purchase(self):
        c=copy.deepcopy(BASE);c['available'][0]=False;c['prices_usd_per_t'][0]=None
        self.assertTrue(ledger.audit(c,Q)['valid'])

    def test_zero_purchase_no_time(self):
        c=copy.deepcopy(BASE);c['initial_inventory_t']=46;c['deadline_hours']=24
        c['calls'][0]=dict(kind='existing',baseline_departure_hours=1,cargo_end_with_bunkering_hours=100,bunker_ready_hours=0,preparation_hours=1,cleanup_hours=1,transfer_hours_per_t=.1,departure_readiness_hours=1)
        r=ledger.audit(c,[0]*4);self.assertTrue(r['valid']);self.assertEqual(r['time_hours'],24)

    def test_valid_decimal_quantity(self):
        self.assertTrue(ledger.audit(copy.deepcopy(BASE),[0,Decimal('16'),0,0])['valid'])

    def test_valid_numpy_quantity(self):
        import numpy as np
        self.assertTrue(ledger.audit(copy.deepcopy(BASE),np.array(Q,dtype=float))['valid'])

    def test_output_float_overflow_rejected(self):
        c=copy.deepcopy(BASE);c['prices_usd_per_t'][1]=1e308
        self.assert_invalid(c)

    def test_decimal_arithmetic_exception_structured(self):
        c=copy.deepcopy(BASE);c['prices_usd_per_t'][1]=Decimal('1e20')
        with localcontext() as ctx:
            ctx.Emax=10
            self.assert_invalid(c)

    def test_time_float_overflow_rejected(self):
        c=copy.deepcopy(BASE);c['calls'][1]['transfer_hours_per_t']=1e308
        self.assert_invalid(c)

    def test_terminal_float_overflow_rejected(self):
        c=copy.deepcopy(BASE)
        for field in ('capacity_t','initial_inventory_t','terminal_inventory_exact_t'):
            c[field]=Decimal('1e1000')
        self.assert_invalid(c,[0]*4)

    def test_disabled_decimal_traps_fail_closed(self):
        from decimal import Overflow, InvalidOperation
        c=copy.deepcopy(BASE);c['prices_usd_per_t'][1]=Decimal('1e20')
        with localcontext() as ctx:
            ctx.Emax=10;ctx.traps[Overflow]=False;ctx.traps[InvalidOperation]=False
            self.assert_invalid(c)

    def test_quantity_decimal_snan_structured(self):
        self.assert_invalid(copy.deepcopy(BASE),[0,Decimal('sNaN'),0,0])

    def test_quantity_numpy_bool_structured(self):
        import numpy as np
        self.assert_invalid(copy.deepcopy(BASE),[0,np.bool_(True),0,0])

    def test_malformed_numeric_has_empty_ledger(self):
        c=copy.deepcopy(BASE);c['prices_usd_per_t'][1]=float('nan')
        r=ledger.audit(c,Q);self.assertFalse(r['valid']);self.assertEqual(r['ledger'],[])

    def test_quantity_mapping_rejected(self):
        c=copy.deepcopy(BASE);c['deadline_hours']=100
        self.assert_invalid(c,{1:'junk',2:None,3:float('nan'),10:'x'})

    def test_quantity_set_rejected(self):
        c=copy.deepcopy(BASE);c['deadline_hours']=100
        self.assert_invalid(c,{1,2,3,10})

    def test_quantity_frozenset_rejected(self):
        c=copy.deepcopy(BASE);c['deadline_hours']=100
        self.assert_invalid(c,frozenset([1,2,3,10]))

    def test_quantity_text_rejected(self):
        self.assert_invalid(copy.deepcopy(BASE),'0160')

    def test_quantity_bytes_rejected(self):
        c=copy.deepcopy(BASE);c['deadline_hours']=100
        self.assert_invalid(c,bytes([1,2,3,10]))

    def test_quantity_ordered_generator_supported(self):
        self.assertTrue(ledger.audit(copy.deepcopy(BASE),(x for x in Q))['valid'])

    def test_deadline_tolerance_unchanged(self):
        c=copy.deepcopy(BASE);c['deadline_hours']=26.32-5e-7
        self.assertTrue(ledger.audit(c,Q)['valid'])

    def test_initial_reserve_policy_unchanged(self):
        c=copy.deepcopy(BASE);c['initial_inventory_t']=10;c['arrival_reserves_t']=[12,6,6,6];c['deadline_hours']=1000
        r=ledger.audit(c,[12,24,0,0]);self.assertFalse(r['valid']);self.assertIn('initial reserve',r['errors'])

    def test_case_not_dict(self):self.assert_invalid(None)
    def test_missing_case_field(self):
        c=copy.deepcopy(BASE);del c['capacity_t'];self.assert_invalid(c)
    def test_case_vector_none(self):
        c=copy.deepcopy(BASE);c['prices_usd_per_t']=None;self.assert_invalid(c)
    def test_case_vector_short(self):
        c=copy.deepcopy(BASE);c['prices_usd_per_t']=[600];self.assert_invalid(c)
    def test_invalid_call_kind(self):
        c=copy.deepcopy(BASE);c['calls'][0]['kind']='arbitrary';self.assert_invalid(c)
    def test_missing_call_field(self):
        c=copy.deepcopy(BASE);del c['calls'][0]['preparation_hours'];self.assert_invalid(c)
    def test_available_price_none_rejected(self):
        c=copy.deepcopy(BASE);c['prices_usd_per_t'][1]=None;self.assert_invalid(c)
    def test_unavailable_positive_purchase_rejected(self):
        c=copy.deepcopy(BASE);c['available'][1]=False;self.assert_invalid(c)
    def test_below_minimum_positive_rejected(self):
        c=copy.deepcopy(BASE);c['minimum_lift_t'][1]=20;self.assert_invalid(c)

# Each malformed scalar is a named unittest, so the before/after totals are explicit.
invalid_values={'nan':float('nan'),'inf':float('inf'),'negative':-1,'string':'450','bool':True,'none':None}
paths=[('prices_usd_per_t',1),('fixed_fee_usd',1),('variable_fee_usd_per_t',1),
       ('leg_demands_t',1),('arrival_reserves_t',1),('supply_max_t',1),('minimum_lift_t',1),
       ('capacity_t',),('initial_inventory_t',),('terminal_inventory_exact_t',),
       ('sailing_hours',),('baseline_existing_call_hours',),('deadline_hours',),
       ('calls',1,'preparation_hours'),('calls',1,'cleanup_hours'),('calls',1,'transfer_hours_per_t'),
       ('calls',1,'detour_hours'),('calls',1,'port_transit_hours'),('calls',1,'waiting_hours')]
for path in paths:
    for label,value in invalid_values.items():
        def test(self,path=path,value=value):
            c=copy.deepcopy(BASE);target=c
            for part in path[:-1]:target=target[part]
            target[path[-1]]=value;self.assert_invalid(c)
        setattr(LedgerCaseValidation,'test_bad_'+'_'.join(map(str,path))+'_'+label,test)
for label,value in {'string':'no','int':1,'none':None}.items():
    def test(self,value=value):
        c=copy.deepcopy(BASE);c['available'][1]=value;self.assert_invalid(c)
    setattr(LedgerCaseValidation,'test_bad_available_'+label,test)
for label,value in {'nan':Decimal('NaN'),'snan':Decimal('sNaN'),'inf':Decimal('Infinity')}.items():
    def test(self,value=value):
        c=copy.deepcopy(BASE);c['prices_usd_per_t'][1]=value;self.assert_invalid(c)
    setattr(LedgerCaseValidation,'test_bad_decimal_price_'+label,test)
for label,value in {'nan':float('nan'),'string':'16','bool':True,'negative':-1}.items():
    def test(self,value=value):self.assert_invalid(copy.deepcopy(BASE),[0,value,0,0])
    setattr(LedgerCaseValidation,'test_bad_quantity_'+label,test)

for field in ('baseline_departure_hours','cargo_end_with_bunkering_hours','bunker_ready_hours','departure_readiness_hours'):
    for label,value in invalid_values.items():
        def test(self,field=field,value=value):
            c=copy.deepcopy(BASE)
            c['calls'][1]=dict(kind='existing',baseline_departure_hours=3,cargo_end_with_bunkering_hours=2,bunker_ready_hours=0,preparation_hours=1,cleanup_hours=1,transfer_hours_per_t=.1,departure_readiness_hours=1)
            c['calls'][1][field]=value;self.assert_invalid(c)
        setattr(LedgerCaseValidation,'test_bad_existing_'+field+'_'+label,test)

for field in ('leg_demands_t','arrival_reserves_t','supply_max_t','minimum_lift_t',
              'fixed_fee_usd','variable_fee_usd_per_t','prices_usd_per_t','available','calls'):
    def test(self,field=field):
        c=copy.deepcopy(BASE);c[field]=dict(enumerate(c[field]));self.assert_invalid(c)
    setattr(LedgerCaseValidation,'test_mapping_rejected_'+field,test)

# Generated functions are registered on the TestCase, not standalone pytest tests.
del test

if __name__=='__main__':unittest.main(verbosity=2)
