import unittest,copy
from datetime import datetime,timezone
from research.voyage_demand.comparison_contract import compare_contexts
from test_voyage_comparison_contract import fixture
class R3Independent(unittest.TestCase):
 def reject_extra(self,x):
  a=fixture();a['features'][0]['extra']=x
  with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_self_cycles(self):
  a=[];a.append(a);self.reject_extra(a)
  b={};b['x']=b;self.reject_extra(b)
 def test_indirect_cycle(self):
  a=[];b={'x':a};a.append(b);self.reject_extra(a)
 def test_shared_noncycle(self):
  x={'v':[1,False,None]};a=fixture();a['features'][0]['extra']=[x,x]
  before=copy.deepcopy(a);b=copy.deepcopy(a);r=compare_contexts(a,b)
  self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH');self.assertEqual(r['left_context_sha256'],r['right_context_sha256']);self.assertEqual(a,before)
 def test_datetime_objects_rejected(self):
  for k in ('decision_at','departure_at','arrival_deadline'):
   a=fixture();a[k]=datetime(2020,1,1,tzinfo=timezone.utc)
   with self.assertRaises(ValueError):compare_contexts(a,a)
  for k in ('issued_at','target_at','received_at'):
   a=fixture();a['features'][0][k]=datetime(2020,1,1,tzinfo=timezone.utc)
   with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_nonstr_json_dates_rejected(self):
  for v in (0,False,None,{},[],20200101):
   a=fixture();a['decision_at']=v
   with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_nonjson_leaf_types(self):
  from decimal import Decimal
  for v in (b'a',set(),frozenset(),Decimal('0'),complex(0,1)):
   self.reject_extra(v)
 def test_subclasses(self):
  class I(int):pass
  class S(str):pass
  class D(dict):pass
  class L(list):pass
  for v in (I(0),S('s'),D(),L()):self.reject_extra(v)
 def test_cross_date_offset(self):
  a=fixture();b=fixture();b['decision_at']='2019-12-31T19:00:00-05:00'
  r=compare_contexts(a,b);self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH');self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
if __name__=='__main__':unittest.main()
