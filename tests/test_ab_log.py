import copy
import unittest
from scripts.review_ab_log import review_cells


def fixture():
    a = {'D4':'HANBADA','S24':'D.O(M/T)','O26':'ROB','O41':'ROB','O42':'CONS','AA6':'CONSUMPTION(M/T)', 'AA8':'M/E','AB8':'G/E','AC8':'BLR','AD8':'M/E','AF8':'G/E','AH8':'BLR','S26':'10','S41':'7','S42':'3','AA10':'3','X4':'2026. 5.31','J4':'test'}
    b = {'T4':'Consumption','T5':'M/E','U5':'G/E','V5':'Boiler','T8':'4'}
    return {k:{p:{'value':v,'formula':False} for p,v in d.items()} for k,d in [('AB-LOG',a),('B FOAM',b)]}

class ReviewTests(unittest.TestCase):
    def test_blank_supply_is_unknown(self):
        r=review_cells(fixture(),'test')
        self.assertIsNone(r['supply'])
        self.assertEqual(r['conditional_balance_status'],'consistent_if_no_supply')
        self.assertEqual(r['status'],'review_pending')
        self.assertEqual(r['daily_comparison_status'],'held_period_unit_and_aggregation_unconfirmed')
    def test_invalid_quantities(self):
        for v in ['', 'NaN','Infinity','-1','abc']:
            with self.subTest(v=v):
                f=fixture(); f['AB-LOG']['S26']['value']=v
                with self.assertRaises(ValueError): review_cells(f,'test')
    def test_formula_not_cached_fact(self):
        f=fixture();f['AB-LOG']['S26']['formula']=True
        with self.assertRaises(ValueError): review_cells(f,'test')
    def test_supply_formula_blocks_conditional_match(self):
        f=fixture();f['AB-LOG']['S27']={'value':'','formula':True}
        self.assertEqual(review_cells(f,'test')['conditional_balance_status'],'review_required')
    def test_discrepancy(self):
        f=fixture();f['AB-LOG']['AA10']['value']='4'
        self.assertEqual(review_cells(f,'test')['summary_status'],'review_required')
    def test_wrong_template(self):
        f=fixture();f['AB-LOG']['S24']['value']='L'
        with self.assertRaises(ValueError): review_cells(f,'test')
    def test_zero_retained(self):
        f=fixture();f['B FOAM']['T8']['value']='0'
        self.assertEqual(review_cells(f,'test')['daily_selected_sum'],'0')
    def test_date_year(self):
        f=fixture();f['AB-LOG']['X4']['value']='2027. 5.31'
        self.assertEqual(review_cells(f,'test')['file_year'],2027)

if __name__=='__main__': unittest.main()
