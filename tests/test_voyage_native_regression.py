import copy
import unittest
from research.voyage_demand.comparison_contract import compare_contexts
from test_voyage_comparison_contract import fixture
class NativeRegression(unittest.TestCase):
 def reject(self,value):
  a=fixture();a['features'][0]['extra']=value
  with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_surrogate_collision_rejected(self):
  self.reject({'\ud83d\ude00':1,'\U0001f600':2})
 def test_surrogate_values_and_keys_rejected(self):
  for value in ('\ud800','\udfff',{'x':['\ud83d\ude00']},{'\ud800':1}):
   with self.subTest(value=repr(value)):self.reject(value)
 def test_valid_nonbmp_preserved(self):
  a=fixture();a['features'][0]['extra']={'\U0001f600':[1,'\U0001f600']}
  r=compare_contexts(a,copy.deepcopy(a));self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
  self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
 def test_tuple_rejected(self):self.reject((0,1))
 def test_integer_key_rejected(self):self.reject({1:'x'})
 def test_bool_none_float_keys_rejected(self):
  for key in (True,None,1.5):
   with self.subTest(key=key):self.reject({key:'x'})
 def test_nested_tuple_rejected(self):self.reject({'x':[{'y':(1,2)}]})
 def test_bytes_set_object_rejected(self):
  for value in (b'x',{1},object()):
   with self.subTest(kind=type(value)):self.reject(value)
 def test_nonfinite_rejected(self):
  for value in (float('nan'),float('inf'),-float('inf')):self.reject(value)
 def test_subclasses_rejected(self):
  class D(dict):pass
  class L(list):pass
  class I(int):pass
  class S(str):pass
  for value in (D(x=1),L([1]),I(1),S('s')):self.reject(value)
 def test_cycle_rejected(self):
  a=[];a.append(a);self.reject(a)
 def test_shared_noncyclic_native_allowed(self):
  x={'1':[0,True,None,'x',1.5]};a=fixture();a['features'][0]['extra']=[x,x]
  b=copy.deepcopy(a);r=compare_contexts(a,b)
  self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
  self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
 def test_native_list_string_keys_allowed(self):
  a=fixture();a['features'][0]['extra']={'1':[0,1]}
  self.assertEqual(compare_contexts(a,a)['status'],'DECLARED_CONTEXTS_MATCH')
if __name__=='__main__':unittest.main()
