"""Copied-fixture regressions for the independent integration review."""
import contextlib
import copy
import csv
import json
import io
import tempfile
import unittest
from pathlib import Path

import cli
import config
import ledger
import contracts
from test_ledger import CFG, EP, ST, rewrite


class IntegrationRegressionTests(unittest.TestCase):
    def test_config_cannot_mislabel_changed_constants_as_native_reproduction(self):
        for key, value in (("max_steps", 31), ("n_ports", 4), ("consumption_per_step", 0.1),
                           ("reserve", 0.2), ("refill_request", 0.8), ("max_fill", 0.9),
                           ("tolerance", 0.0)):
            with self.subTest(key=key):
                cfg = copy.deepcopy(CFG)
                cfg["native_fixed"][key]["value"] = value
                with self.assertRaisesRegex(config.ConfigError, "pinned native"):
                    config.validate(cfg)
        cfg = copy.deepcopy(CFG)
        cfg["policy_version"] = "unimplemented-candidate"
        with self.assertRaisesRegex(config.ConfigError, "unsupported policy_version"):
            config.validate(cfg)

    def test_invalid_native_counts_and_seed_ranges_are_rejected(self):
        for key in ("max_steps", "n_ports"):
            for value in (float("nan"), float("inf"), -1, 0, 1.5, True):
                with self.subTest(key=key, value=value):
                    cfg = copy.deepcopy(CFG)
                    cfg["native_fixed"][key]["value"] = value
                    with self.assertRaises(config.ConfigError):
                        config.validate(cfg)
        for value in ([True, 3], [-1, 3], [1], [1, 2, 3], None, "13"):
            with self.subTest(seed_range=value):
                cfg = copy.deepcopy(CFG)
                cfg["integration"]["seed_range_inclusive"]["value"] = value
                with self.assertRaises(config.ConfigError):
                    config.validate(cfg)

    def test_coordinated_terminal_value_edit_cannot_receive_pass(self):
        # The identity still holds after this corruption. Do not mistake it for
        # independent terminal-market verification, even when steps are supplied.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg = copy.deepcopy(CFG)
            cfg["integration"]["seed_range_inclusive"]["value"] = [1, 3]
            cfg_path = root / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            def edit(rows):
                rows[0]["terminal_inventory_value"] = str(float(rows[0]["terminal_inventory_value"]) + 100)
                rows[0]["inventory_adjusted_sci"] = str(float(rows[0]["inventory_adjusted_sci"]) - 100)
                return rows
            episodes = rewrite(EP, root / "episodes.csv", edit)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = cli.main(["ledger", "--config", str(cfg_path), "--episodes", str(episodes),
                               "--steps", str(ST), "--out-dir", str(root / "out")])
            report = json.loads(stdout.getvalue())
            self.assertEqual(rc, 3)
            self.assertEqual(report["status"], "INCOMPLETE")
            self.assertEqual(report["accounting_status"], "PASS")
            self.assertEqual(report["terminal_valuation_status"], "not_independently_verified")
            self.assertEqual(report["step_audit_status"], "checked")
            self.assertEqual(report["accounting_mismatches"], 0)

    def test_unknown_consumption_information_is_rejected(self):
        cfg = copy.deepcopy(CFG)
        cfg["integration"]["consumption_known_at_decision"]["value"] = False
        with self.assertRaisesRegex(config.ConfigError, "consumption_known_at_decision"):
            config.validate(cfg)

    def test_hardlinked_output_preserves_all_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, steps, cfg_path = root / "episodes.csv", root / "steps.csv", root / "config.json"
            source.write_bytes(EP.read_bytes())
            steps.write_bytes(ST.read_bytes())
            cfg = copy.deepcopy(CFG)
            cfg["integration"]["seed_range_inclusive"]["value"] = [1, 3]
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            out = root / "out"
            out.mkdir()
            try:
                (out / "ledger.csv").hardlink_to(source)
            except OSError as exc:
                self.skipTest(f"OS cannot create hard link: {exc}")
            before = {p: p.read_bytes() for p in (source, steps, cfg_path)}
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = cli.main(["ledger", "--config", str(cfg_path), "--episodes", str(source),
                               "--steps", str(steps), "--out-dir", str(out), "--overwrite"])
            self.assertEqual(rc, 2)
            self.assertIn("hardlinked output target", stderr.getvalue())
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            self.assertFalse((out / "run_manifest.json").exists())

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
