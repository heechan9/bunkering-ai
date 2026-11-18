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

class TimestampPrecision(unittest.TestCase):
 def test_context_fraction_loss_rejected(self):
  for key in ('decision_at','departure_at','arrival_deadline'):
   for tail in ('0000001','0000002','1234567'):
    a=fixture();a[key]=a[key].replace('Z','.'+tail+'Z')
    with self.subTest(key=key,tail=tail):
     with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_feature_fraction_loss_rejected(self):
  for key in ('issued_at','target_at','received_at'):
   a=fixture();a['features'][0][key]=a['features'][0][key].replace('Z','.0000001Z')
   with self.subTest(key=key):
    with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_representable_fraction_and_offset_preserved(self):
  a=fixture();b=fixture()
  a['decision_at']='2020-01-01T00:00:00.123456Z'
  b['decision_at']='2020-01-01T09:00:00.123456000+09:00'
  r=compare_contexts(a,b);self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
  self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
 def test_extra_zero_fraction_accepted(self):
  a=fixture();b=fixture()
  for k in ('decision_at','departure_at','arrival_deadline'):b[k]=b[k].replace('Z','.000000000Z')
  for k in ('issued_at','target_at','received_at'):b['features'][0][k]=b['features'][0][k].replace('Z',',000000000Z')
  r=compare_contexts(a,b);self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
  self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])

class TimezoneOffsetContract(unittest.TestCase):
 def test_seconds_and_fractional_offsets_rejected_in_all_fields(self):
  for key in ('decision_at','departure_at','arrival_deadline','issued_at','target_at','received_at'):
   for offset in ('+00:00:00.000001','-00:00:00.000001','+09:00:30','+00:00:00','+090000','+09:00.5','+0900','+09'):
    a=fixture();row=a if key in a else a['features'][0]
    row[key]=row[key].replace('Z',offset)
    with self.subTest(key=key,offset=offset):
     with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_whole_minute_offsets_all_fields(self):
  from datetime import timezone,timedelta
  from research.voyage_demand.validation import timestamp
  a=fixture()
  for minutes in (0,330,345,540,-210,-300):
   b=copy.deepcopy(a)
   for key in ('decision_at','departure_at','arrival_deadline'):
    b[key]=timestamp(b[key]).astimezone(timezone(timedelta(minutes=minutes))).isoformat()
   for key in ('issued_at','target_at','received_at'):
    b['features'][0][key]=timestamp(b['features'][0][key]).astimezone(timezone(timedelta(minutes=minutes))).isoformat()
   with self.subTest(minutes=minutes):
    r=compare_contexts(a,b);self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
    self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
 def test_valid_nonzero_offset_and_microseconds(self):
  a=fixture();b=fixture();a['decision_at']='2020-01-01T00:00:00.123456Z'
  b['decision_at']='2020-01-01T05:45:00.123456000+05:45'
  r=compare_contexts(a,b);self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH')
  self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
 def test_invalid_offsets_rejected(self):
  for offset in ('+24:00','+99:00','+09:60','-00:99','Zgarbage',''):
   a=fixture();a['decision_at']=a['decision_at'].replace('Z',offset)
   with self.subTest(offset=offset):
    with self.assertRaises(ValueError):compare_contexts(a,fixture())
