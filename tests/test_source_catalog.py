"""Reject stale evidence, mutable links and missing source descriptions."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.build_source_catalog import ROOT, CONFIG, OUTPUT, build

class SourceCatalogTests(unittest.TestCase):
    def test_committed_catalog_matches(self):
        expected = build()
        self.assertEqual(expected, json.loads((ROOT / OUTPUT).read_text(encoding='utf-8')))
        self.assertTrue(all('/blob/' + expected['revision'] + '/' in s['url'] for s in expected['sources']))

    def test_rejects_changed_evidence_and_invalid_metadata(self):
        for mutation in ('evidence', 'revision', 'duplicate', 'locale', 'path', 'missing'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = json.loads((ROOT / CONFIG).read_text(encoding='utf-8'))
                for s in config['sources']:
                    target = root / s['path']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / s['path'], target)
                if mutation == 'evidence':
                    (root / config['sources'][0]['path']).write_text('changed', encoding='utf-8')
                elif mutation == 'revision': config['revision'] = 'main'
                elif mutation == 'duplicate': config['sources'][1]['id'] = 'simulation'
                elif mutation == 'locale': config['sources'][0]['unit']['en'] = ''
                elif mutation == 'path': config['sources'][0]['path'] = '../private.txt'
                elif mutation == 'missing': config['sources'].pop()
                (root / CONFIG).parent.mkdir(parents=True, exist_ok=True)
                (root / CONFIG).write_text(json.dumps(config), encoding='utf-8')
                with self.assertRaises(ValueError): build(root)
