import copy
import unittest
from research.voyage_demand.comparison_contract import compare_contexts
from test_voyage_comparison_contract import fixture
class TypeRegression(unittest.TestCase):
 def check_pair(self,key,x,y):
  a=fixture();b=copy.deepcopy(a)
  a['features'][0][key]=x;b['features'][0][key]=y
  before=copy.deepcopy((a,b));r=compare_contexts(a,b)
  self.assertEqual(r['status'],'HOLD');self.assertEqual(r['differences'],['features'])
  self.assertNotEqual(r['left_context_sha256'],r['right_context_sha256'])
  self.assertFalse(r['operational_approval']);self.assertEqual((a,b),before)
 def test_latency_int_float(self):self.check_pair('latency_seconds',0,0.0)
 def test_extra_zero_bool(self):self.check_pair('extra',0,False)
 def test_extra_one_bool(self):self.check_pair('extra',1,True)
 def test_value_zero_bool(self):self.check_pair('value',0,False)
 def test_nested_type(self):self.check_pair('extra',{'x':[0]},{'x':[False]})
 def test_float_signed_zero(self):self.check_pair('value',0.0,-0.0)
 def test_identical_type_and_normalization_match_hash(self):
  for value in (0,False,1,True,0.0,-0.0,{'x':[False]}):
   with self.subTest(value=repr(value)):
    a=fixture();a['features'][0]['extra']=value;b=copy.deepcopy(a)
    b['decision_at']='2020-01-01T09:00:00+09:00'
    r=compare_contexts(a,b)
    self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
    self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
if __name__=='__main__':unittest.main()
