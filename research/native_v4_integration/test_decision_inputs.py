"""Owner-decision input validation without changing freeze policy."""
import copy
import tempfile
import unittest
from pathlib import Path

import contracts
from test_config_cli import TEMPLATE, run


class DecisionInputTests(unittest.TestCase):
    def rows(self):
        return contracts.merge(TEMPLATE, {})[0]

    def test_unknown_ids_do_not_mutate_rows(self):
        rows = self.rows()
        before = copy.deepcopy(rows)
        with self.assertRaisesRegex(contracts.ContractError, 'unknown decision'):
            contracts.apply_decisions(rows, {'C01': 'accepted', 'C99': 'accepted'})
        self.assertEqual(rows, before)

    def test_later_invalid_value_does_not_partially_apply(self):
        rows = self.rows()
        before = copy.deepcopy(rows)
        with self.assertRaises(contracts.ContractError):
            contracts.apply_decisions(rows, {'C01': 'accepted', 'C06': 'typo'})
        self.assertEqual(rows, before)

    def test_cli_rejects_malformed_decisions_before_output(self):
        cases = [
            ('missing header', 'contract_id\nC01\n'),
            ('missing id header', 'owner_decision\naccepted\n'),
            ('empty file', ''),
            ('duplicate header', 'contract_id,owner_decision,owner_decision\nC01,accepted,rejected\n'),
            ('unknown id', 'contract_id,owner_decision\nC99,accepted\n'),
            ('duplicate id', 'contract_id,owner_decision\nC01,accepted\nC01,rejected\n'),
            ('blank id', 'contract_id,owner_decision\n,accepted\n'),
            ('missing cell', 'contract_id,owner_decision\nC01\n'),
            ('extra cell', 'contract_id,owner_decision\nC01,accepted,x\n'),
            ('blank decision', 'contract_id,owner_decision\nC01,\n'),
            ('invalid decision', 'contract_id,owner_decision\nC01,typo\n'),
        ]
        for label, text in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                decision_path = root/'decisions.csv'
                decision_path.write_text(text, encoding='utf-8')
                before = decision_path.read_bytes()
                code, out, err = run('merge-contracts', '--template', TEMPLATE,
                                     '--decisions', decision_path, '--out-dir', root/'out')
                self.assertEqual(code, 2, (out, err))
                self.assertIn('ERROR:', err)
                self.assertFalse((root/'out').exists())
                self.assertEqual(decision_path.read_bytes(), before)

    def test_valid_partial_decisions_and_extra_metadata_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'decisions.csv'
            p.write_text('\ufeffowner_decision,contract_id,note\naccepted,C01,owner choice\n', encoding='utf-8')
            decisions = contracts.read_decisions(p)
        rows = contracts.apply_decisions(self.rows(), decisions)
        self.assertEqual(rows[0]['owner_decision'], 'accepted')
        self.assertTrue(all(r['owner_decision'] == 'pending' for r in rows[1:]))

    def test_all_explicitly_accepted_blank_pending_freeze_is_unchanged(self):
        # Existing repository contract permits this; do not invent stricter adoption policy.
        rows = self.rows()
        contracts.apply_decisions(rows, {r['contract_id']: 'accepted' for r in rows})
        frozen, digest = contracts.freeze(rows)
        self.assertEqual(len(frozen), 6)
        self.assertTrue(all(r['proposed_value'] == '' and r['domain_status'] == 'pending' for r in frozen))
        self.assertEqual({r['contract_version'] for r in frozen}, {'BAI-CONTRACT-v1.0'})
        self.assertEqual(len(digest), 64)
