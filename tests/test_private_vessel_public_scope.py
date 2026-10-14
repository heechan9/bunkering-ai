"""Public distribution must not contain private vessel case payloads."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PublicScopeTests(unittest.TestCase):
 def test_case_artifacts_are_withheld(self):
  paths=list((ROOT/'results/real_voyage').glob('hanbada*.json'))+list((ROOT/'web/ocean-lab/public/data').glob('hanbada*.json'))+list((ROOT/'research/activity_consumption').glob('hanbada*.json'))+list((ROOT/'research/fuel_source_review/results').glob('hanbada*.json'))
  self.assertEqual(len(paths),9)
  for p in paths:
   with self.subTest(path=p.name):
    d=json.loads(p.read_text());self.assertIn('withheld',json.dumps(d))
    self.assertTrue(set(d).isdisjoint({'source_sha256','voyage_id','opening_rob','closing_rob','windows','density_scenarios'}))
 def test_csv_payloads_are_empty(self):
  for p in (ROOT/'research/activity_consumption').glob('hanbada*.csv'):
   self.assertEqual(len(p.read_text().splitlines()),1)
 def test_public_widget_does_not_fetch_case(self):
  s=(ROOT/'web/ocean-lab/components/ocean/AbLogReview.tsx').read_text()
  self.assertNotIn('fetch(',s);self.assertNotIn('hanbada-review.json',s)
 def test_no_pinned_private_case_source(self):
  for p in ['scripts/web_source_catalog.json','web/ocean-lab/public/data/source-catalog.json']:
   for x in json.loads((ROOT/p).read_text())['sources']:
    self.assertNotIn('hanbada',json.dumps(x).lower());self.assertNotEqual(x['id'],'kmou')
