"""Config validation, contract merge rules and CLI overwrite guard."""
import contextlib
import copy
import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import cli  # noqa: E402
import config  # noqa: E402
import contracts  # noqa: E402

CFG_PATH = HERE / "config" / "bai_v4_native.json"
CFG = json.loads(CFG_PATH.read_text())
C = HERE / "contracts"
TEMPLATE = C / "input_contract_template.csv"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(map(str, argv)))
    return code, out.getvalue(), err.getvalue()


class ConfigTests(unittest.TestCase):
    def bad(self, edit, pattern):
        cfg = copy.deepcopy(CFG)
        edit(cfg)
        with self.assertRaisesRegex(config.ConfigError, pattern):
            config.validate(cfg)

    def test_shipped_config_valid(self):
        config.validate(copy.deepcopy(CFG))

    def test_wrong_unit(self):
        self.bad(lambda c: c["native_fixed"]["reserve"].update(unit="ton"), "unit must be")

    def test_unknown_key(self):
        self.bad(lambda c: c["integration"].update(reserve_mode={"value": 1}), "unknown keys")

    def test_unknown_enum(self):
        self.bad(lambda c: c["integration"]["reserve_phase"].update(value="whenever"), "not in")

    def test_bool_is_not_ddof(self):
        self.bad(lambda c: c["integration"]["statistics_ddof"].update(value=True), "not in")

    def test_tank_fraction_range(self):
        self.bad(lambda c: c["native_fixed"]["consumption_per_step"].update(value=5), "outside")

    def test_used_seed_range_cannot_be_new_plan(self):
        self.bad(lambda c: c["integration"]["seed_status"].update(value="new_frozen_plan"), "overlaps")

    def test_v1_requires_accepted(self):
        self.bad(lambda c: c.update(contract_version="BAI-CONTRACT-v1.0"), "requires accepted")


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edited(self, name, cid, **changes):
        with TEMPLATE.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["contract_id"] == cid:
                r.update(changes)
        p = self.tmp / name
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=contracts.FIELDS)
            w.writeheader()
            w.writerows(rows)
        return p

    def inputs(self, **override):
        base = {"domain_review": C / "received/domain_review_contract.csv", "data_statistics": C / "received/data_statistics_contract.csv",
                "현수": C / "hyeonsu_contract.csv"}
        base.update(override)
        return base

    def test_current_inputs_merge_as_pending(self):
        merged, issues = contracts.merge(TEMPLATE, self.inputs())
        status = {r["contract_id"]: r["received_status"] for r in merged}
        self.assertEqual(status["C06"], "received_filled")
        self.assertEqual({status[c] for c in ["C01", "C02", "C03", "C04", "C05"]}, {"received_blank"})
        self.assertTrue(all(r["owner_decision"] == "pending" for r in merged))

    def test_non_owner_edit_rejected(self):
        p = self.edited("m.csv", "C03", proposed_value="x")
        with self.assertRaisesRegex(contracts.ContractError, "owned by data_statistics"):
            contracts.merge(TEMPLATE, self.inputs(domain_review=p))

    def test_member_cannot_decide(self):
        p = self.edited("m.csv", "C01", owner_decision="accepted")
        with self.assertRaisesRegex(contracts.ContractError, "희찬 only"):
            contracts.merge(TEMPLATE, self.inputs(domain_review=p))

    def test_version_change_rejected(self):
        p = self.edited("m.csv", "C01", contract_version="BAI-CONTRACT-v0.2")
        with self.assertRaisesRegex(contracts.ContractError, "contract_version"):
            contracts.merge(TEMPLATE, self.inputs(domain_review=p))

    def test_missing_file_is_reported_not_fatal(self):
        merged, issues = contracts.merge(TEMPLATE, self.inputs(data_statistics=None))
        self.assertIn("data_statistics: file not received", issues)
        self.assertEqual(merged[2]["received_status"], "not_received")

    def test_freeze_requires_all_accepted(self):
        merged, _ = contracts.merge(TEMPLATE, self.inputs())
        with self.assertRaisesRegex(contracts.ContractError, "not accepted"):
            contracts.freeze(merged)
        contracts.apply_decisions(merged, {r["contract_id"]: "accepted" for r in merged})
        rows, digest = contracts.freeze(merged)
        self.assertEqual({r["contract_version"] for r in rows}, {"BAI-CONTRACT-v1.0"})
        self.assertEqual(digest, contracts.freeze(merged)[1])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(HERE / "fixtures/smoke_episodes.csv", self.tmp / "episodes.csv")
        shutil.copy(HERE / "fixtures/smoke_steps.csv", self.tmp / "steps.csv")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def ledger(self, out, *extra):
        cfg = copy.deepcopy(CFG)
        cfg["integration"]["seed_range_inclusive"]["value"] = [1, 3]
        path = self.tmp / "smoke_config.json"
        path.write_text(json.dumps(cfg), encoding="utf-8")
        return run("ledger", "--config", path, "--episodes", self.tmp / "episodes.csv",
                   "--steps", self.tmp / "steps.csv", "--out-dir", out, *extra)

    def test_ledger_smoke_reports_accounting_only(self):
        code, out, _ = self.ledger(self.tmp / "out")
        self.assertEqual(code, 3, out)
        self.assertEqual(json.loads(out)["status"], "INCOMPLETE")
        self.assertEqual(json.loads(out)["accounting_status"], "PASS")
        for name in ["ledger.csv", "paired_summary.csv", "policy_summary.csv", "accounting_mismatches.csv",
                     "run_manifest.json", "paired_final_fuel.csv"]:
            self.assertTrue((self.tmp / "out" / name).exists(), name)
        with (self.tmp / "out" / "paired_final_fuel.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        empty = next(r for r in rows if r["baseline"] == "fixed_fueling" and r["subset"] == "common_safe")
        self.assertEqual(empty["n"], "0")
        self.assertEqual(empty["mean_final_fuel_comparator"], "")
        self.assertEqual(empty["mean_final_fuel_baseline"], "")

    def test_refuses_input_folder_even_with_overwrite(self):
        before = (self.tmp / "episodes.csv").read_bytes()
        code, _, err = self.ledger(self.tmp, "--overwrite")
        self.assertEqual(code, 2)
        self.assertIn("contains input", err)
        self.assertEqual((self.tmp / "episodes.csv").read_bytes(), before)

    def test_refuses_nonempty_out_without_overwrite(self):
        self.assertEqual(self.ledger(self.tmp / "out")[0], 3)
        code, _, err = self.ledger(self.tmp / "out")
        self.assertEqual(code, 2)
        self.assertIn("not empty", err)
        self.assertEqual(self.ledger(self.tmp / "out", "--overwrite")[0], 3)

    def test_validate_config_reports_pending(self):
        code, out, _ = run("validate-config", "--config", CFG_PATH)
        self.assertEqual(code, 0)
        self.assertIn("reserve_phase", json.loads(out)["pending"])

    def test_merge_contracts_writes_map(self):
        code, out, _ = run("merge-contracts", "--template", TEMPLATE, "--domain-review", C / "received/domain_review_contract.csv",
                           "--data-statistics", C / "received/data_statistics_contract.csv", "--hyeonsu", C / "hyeonsu_contract.csv",
                           "--out-dir", self.tmp / "m")
        self.assertEqual(code, 0, out)
        with (self.tmp / "m/integration_map.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["contract_id"] for r in rows], ["C01", "C02", "C03", "C04", "C05", "C06"])
        code, _, err = run("merge-contracts", "--template", TEMPLATE, "--hyeonsu", C / "hyeonsu_contract.csv",
                           "--freeze", "--out-dir", self.tmp / "f")
        self.assertEqual(code, 2)
        self.assertIn("not accepted", err)
        self.assertFalse((self.tmp / "f").exists())  # refused runs leave no output folder

    def test_reused_native_sources_match_pinned_commit(self):
        code, out, _ = run("verify-source", "--source-verification", HERE / "fixtures/pinned_source_blobs.json")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
