"""Prove the read-only web guard rejects stale and inconsistent evidence."""
import hashlib
import json
import shutil
from pathlib import Path

import unittest
import tempfile
from contextlib import contextmanager
from scripts.audit_web_evidence import ROOT, WEB, RESEARCH, audit


def snapshot(tmp_path):
    for name in [WEB / 'replay.json', WEB / 'integration-review.json',
                 RESEARCH / 'policy_accounting_comparison.csv', RESEARCH / 'provenance.json']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


def test_current_snapshot():
    assert audit()['transitions_checked'] == 19030


def mutate_and_check(snapshot, change):
    path = snapshot / WEB / 'replay.json'
    data = json.loads(path.read_text())
    row = data['runs']['dqn_42']['42'][0]
    if change == 'summary':
        data['summary'][0]['episode_sci_mean'] = '1'
    elif change == 'checkpoint':
        data['checkpointHashes']['dqn_seed_42.pt'] = '0' * 64
    elif change == 'case':
        del data['runs']['dqn_42']['42']
    else:
        row[{'fuel': 0, 'sci': 3, 'reward': 4, 'flag': 5}[change]] += 1
    path.write_text(json.dumps(data))
    report = snapshot / WEB / 'integration-review.json'
    metadata = json.loads(report.read_text())
    metadata['replay_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    report.write_text(json.dumps(metadata))
    with unittest.TestCase().assertRaises(ValueError):
        audit(snapshot)


def stale_hash(snapshot):
    path = snapshot / WEB / 'replay.json'
    path.write_bytes(path.read_bytes() + b' ')
    with unittest.TestCase().assertRaisesRegex(ValueError, 'hash'):
        audit(snapshot)


def canonical_csv_changed(snapshot):
    path = snapshot / RESEARCH / 'policy_accounting_comparison.csv'
    path.write_text(path.read_text().replace('840076.6038216761', '1'))
    with unittest.TestCase().assertRaisesRegex(ValueError, 'Summary differs'):
        audit(snapshot)

class WebEvidenceTests(unittest.TestCase):
    def test_current(self):
        test_current_snapshot()

    def test_mutations(self):
        for change in ['summary', 'checkpoint', 'case', 'fuel', 'sci', 'reward', 'flag']:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                mutate_and_check(snapshot(Path(directory)), change)

    def test_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            stale_hash(snapshot(Path(directory)))

    def test_canonical(self):
        with tempfile.TemporaryDirectory() as directory:
            canonical_csv_changed(snapshot(Path(directory)))
