import copy,unittest
from test_voyage_comparison_contract import fixture
from research.voyage_demand.comparison_contract import compare_contexts
class Independent(unittest.TestCase):
 def test_all_timezones(self):
  a=fixture();b=fixture()
  for k in ('decision_at','departure_at','arrival_deadline'):
   from research.voyage_demand.validation import timestamp
   from datetime import timezone,timedelta
   b[k]=timestamp(b[k]).astimezone(timezone(timedelta(hours=9))).isoformat()
  for k in ('issued_at','target_at','received_at'):
   b['features'][0][k]=timestamp(b['features'][0][k]).astimezone(timezone(timedelta(hours=-5))).isoformat()
  self.assertEqual(compare_contexts(a,b)['status'],'DECLARED_CONTEXTS_MATCH')
 def test_decision_equals_departure(self):
  a=fixture();a['departure_at']=a['decision_at'];self.assertEqual(compare_contexts(a,a)['status'],'DECLARED_CONTEXTS_MATCH')
 def test_departure_equals_arrival(self):
  a=fixture();a['arrival_deadline']=a['departure_at']
  with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_one_microsecond_late(self):
  a=fixture();a['features'][0]['received_at']='2020-01-01T00:00:00.000001Z'
  with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_nonfinite(self):
  for v in (float('nan'),float('inf'),-1,True):
   a=fixture();a['features'][0]['latency_seconds']=v
   with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_nested_nonfinite(self):
  a=fixture();a['features'][0]['extra']={'a':[float('nan')]}
  with self.assertRaises(ValueError):compare_contexts(a,a)
 def test_bool_must_not_equal_number(self):
  a=fixture();b=fixture();a['features'][0]['value']=0;b['features'][0]['value']=False
  self.assertEqual(compare_contexts(a,b)['status'],'HOLD')
 def test_match_has_same_canonical_hash(self):
  a=fixture();b=fixture();b['features'][0]['latency_seconds']=0.0
  r=compare_contexts(a,b)
  if r['status']=='DECLARED_CONTEXTS_MATCH':self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
if __name__=='__main__':unittest.main()
