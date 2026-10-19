"""Copied-fixture regressions for the independent integration review."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

import cli
import config
import ledger
import contracts
from test_ledger import CFG, EP, ST, rewrite


class IntegrationRegressionTests(unittest.TestCase):
    def test_input_proposed_is_received_but_not_adopted(self):
        template = Path(__file__).parent / "contracts/input_contract_template.csv"
        rows = list(contracts.read_rows(template).values())
        row = next(r for r in rows if r["contract_id"] == "C03")
        row.update(proposed_value="synthetic units proposal", domain_status="input_proposed")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data_statistics_contract.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=contracts.FIELDS)
                w.writeheader()
                w.writerows(rows)
            merged, issues = contracts.merge(template, {"data_statistics": path})
            proposal = next(r for r in merged if r["contract_id"] == "C03")
            self.assertEqual(proposal["domain_status"], "input_proposed")
            self.assertEqual(proposal["owner_decision"], "pending")
            self.assertEqual(proposal["received_status"], "received_filled")
            self.assertFalse(any("domain_status" in i for i in issues))
            with self.assertRaises(contracts.ContractError):
                contracts.freeze(merged)

    def test_bad_steps_are_rejected(self):
        episodes = ledger.load_episodes(EP, CFG)
        for field, value in [("step_sci", "NaN"), ("fuel_after", "inf"),
                             ("action", "99"), ("action", "1.5"),
                             ("step", "0"), ("step", "2")]:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as d:
                def edit(rows):
                    rows[0][field] = value
                    return rows
                path = rewrite(ST, Path(d) / "steps.csv", edit)
                with self.assertRaises(ledger.InputError):
                    ledger.audit_steps(path, episodes, CFG)

    def test_post_refill_phase_rejected(self):
        cfg = copy.deepcopy(CFG)
        cfg["integration"]["reserve_phase"]["value"] = "post_refill"
        with self.assertRaises(config.ConfigError):
            config.validate(cfg)

    def test_declared_seed_plan_must_match_records(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = copy.deepcopy(CFG)
            cfg["integration"]["seed_range_inclusive"]["value"] = [92000000, 2**63]
            cfg["integration"]["seed_status"]["value"] = "new_frozen_plan"
            path = Path(d) / "config.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaisesRegex(ledger.InputError, "seeds"):
                cli.cmd_ledger(type("Args", (), dict(config=path, episodes=EP, steps=ST,
                    legacy_summary=None, out_dir=Path(d) / "out", overwrite=False))())
            self.assertFalse((Path(d) / "out").exists())

    def test_overwrite_symlink_preserves_source(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "source.csv"
            source.write_bytes(EP.read_bytes())
            before = source.read_bytes()
            out = Path(d) / "out"
            out.mkdir()
            try:
                (out / "ledger.csv").symlink_to(source)
            except OSError as exc:
                self.skipTest(f"OS cannot create symbolic link: {exc}")
            with self.assertRaises(cli.OutputGuardError):
                cli.check_out_dir(out, [source], True)
            self.assertEqual(source.read_bytes(), before)

    def test_empty_common_safe_remains_null(self):
        rows = ledger.paired_summary(ledger.load_episodes(EP, CFG), 1, "draft")
        empty = [r for r in rows if r["subset"] == "common_strict_safe" and r["n"] == 0]
        self.assertTrue(empty)
        self.assertTrue(all(r["mean_delta"] is None and r["ci95_low"] is None for r in empty))

    def test_final_fuel_has_explicit_comparison_populations(self):
        rows = ledger.policy_summary(ledger.load_episodes(EP, CFG), "draft")
        fixed = next(r for r in rows if r["policy"] == "fixed_fueling")
        self.assertEqual(fixed["final_fuel_subset"], "all_episodes")
        self.assertEqual(fixed["final_fuel_n_all"], 3)
        self.assertEqual(fixed["final_fuel_n_strict_safe"], 0)
        self.assertIsNone(fixed["mean_final_fuel_strict_safe"])
