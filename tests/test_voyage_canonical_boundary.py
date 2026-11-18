import copy,unittest
from test_voyage_comparison_contract import fixture
from research.voyage_demand.comparison_contract import compare_contexts
class CanonicalBoundary(unittest.TestCase):
 def pair(self,a,b):
  l=fixture();r=fixture();l['features'][0]['extra']=a;r['features'][0]['extra']=b
  return compare_contexts(l,r)
 def test_tuple_not_silently_normalized(self):
  try:r=self.pair((1,2),[1,2])
  except (TypeError,ValueError):return
  self.assertEqual(r['status'],'HOLD')
 def test_integer_key_not_silently_normalized(self):
  try:r=self.pair({1:'a'},{'1':'a'})
  except (TypeError,ValueError):return
  self.assertEqual(r['status'],'HOLD')
 def test_key_order_identity(self):
  r=self.pair({'a':1,'b':False},{'b':False,'a':1})
  self.assertEqual(r['status'],'DECLARED_CONTEXTS_MATCH');self.assertEqual(r['left_context_sha256'],r['right_context_sha256'])
 def test_unicode_not_implicit_normalized(self):
  self.assertEqual(self.pair('\u00e9','e\u0301')['status'],'HOLD')
 def test_json_scalar_pair_matrix(self):
  values=[None,False,True,0,1,0.0,-0.0,'0',[],{},[0],[False]]
  import json
  for a in values:
   for b in values:
    expected=json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))
    r=self.pair(a,b)
    self.assertEqual(r['status']=='DECLARED_CONTEXTS_MATCH',expected)
    self.assertEqual(r['left_context_sha256']==r['right_context_sha256'],expected)
if __name__=='__main__':unittest.main()
