import copy
import unittest
from research.voyage_demand.comparison_contract import compare_contexts

def fixture():
 return dict(schema='paired-context/v1',data_role='synthetic',voyage_id='toy',
 decision_at='2020-01-01T00:00:00Z',departure_at='2020-01-01T01:00:00Z',
 arrival_deadline='2020-01-02T00:00:00Z',origin_id='a',destination_id='b',
 constraints_sha256='a'*64,forecast_snapshot_sha256='b'*64,objective_sha256='c'*64,
 features=[dict(name='wind',unit='m/s',source='synthetic',kind='forecast',
 issued_at='2019-12-31T22:00:00Z',target_at='2020-01-01T12:00:00Z',
 received_at='2019-12-31T23:00:00Z',latency_seconds=0,
 missing_policy='hold',available_at_purchase=True)])
class Tests(unittest.TestCase):
 def test_match_and_immutability(self):
  a=fixture();old=copy.deepcopy(a);r=compare_contexts(a,a)
  self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH');self.assertFalse(r['operational_approval']);self.assertEqual(a,old)
 def test_mismatch_fields(self):
  for key,value in [('voyage_id','other'),('destination_id','c'),('arrival_deadline','2020-01-03T00:00:00Z'),('constraints_sha256','d'*64),('forecast_snapshot_sha256','e'*64),('objective_sha256','f'*64)]:
   with self.subTest(key=key):
    a=fixture();b=copy.deepcopy(a);b[key]=value;self.assertEqual(compare_contexts(a,b)['differences'],[key])
 def test_feature_vintage(self):
  a=fixture();b=copy.deepcopy(a);b['features'][0]['issued_at']='2019-12-31T21:00:00Z'
  self.assertEqual(compare_contexts(a,b)['status'],'HOLD')
 def test_timezone_equivalence(self):
  a=fixture();b=copy.deepcopy(a);b['decision_at']='2020-01-01T09:00:00+09:00'
  self.assertEqual(compare_contexts(a,b)['status'],'DECLARED_CONTEXTS_MATCH')
 def test_invalid_context(self):
  for key,value in [('data_role','real'),('features',[]),('constraints_sha256','bad'),('decision_at','2020-01-01'),('arrival_deadline','2019-01-01T00:00:00Z')]:
   with self.subTest(key=key):
    a=fixture();a[key]=value
    with self.assertRaises(ValueError): compare_contexts(a,fixture())
 def test_missing_extra(self):
  for action in ('missing','extra'):
   a=fixture()
   if action=='missing':del a['voyage_id']
   else:a['unknown']=1
   with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_unavailable_future_observation(self):
  a=fixture();a['features'][0]['kind']='observation'
  with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_late_receipt(self):
  a=fixture();a['features'][0]['received_at']='2020-01-01T01:00:00Z'
  with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_duplicate_feature(self):
  a=fixture();a['features']*=2
  with self.assertRaises(ValueError):compare_contexts(a,fixture())
 def test_feature_order(self):
  a=fixture();f=copy.deepcopy(a['features'][0]);f['name']='current';a['features'].append(f)
  b=copy.deepcopy(a);b['features'].reverse()
  self.assertEqual(compare_contexts(a,b)['status'],'DECLARED_CONTEXTS_MATCH')
if __name__=='__main__':unittest.main()
