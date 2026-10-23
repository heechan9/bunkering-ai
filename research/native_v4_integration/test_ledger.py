"""Ledger, accounting identities and paired statistics on the synthetic smoke fixture."""
import csv
import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import ledger  # noqa: E402

CFG = json.loads((HERE / "config" / "bai_v4_native.json").read_text())
FIX = HERE / "fixtures"
EP, ST = FIX / "smoke_episodes.csv", FIX / "smoke_steps.csv"


def rewrite(src, dst, edit):
    with src.open(newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    rows = edit(rows)
    with dst.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return dst


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)


class StatisticsTests(unittest.TestCase):
    def test_empty_is_null_not_zero(self):
        st = ledger.describe([], 1)
        self.assertEqual(st["n"], 0)
        self.assertIsNone(st["mean"])
        self.assertIsNone(st["ci95_low"])
        self.assertEqual(st["status"], "empty_subset_null")

    def test_n1_interval_not_estimable_for_any_ddof(self):
        for ddof in (0, 1):
            st = ledger.describe([5.0], ddof)
            self.assertEqual(st["mean"], 5.0)
            self.assertIsNone(st["ci95_low"])
            self.assertEqual(st["status"], "ci_not_estimable_n1")

    def test_ddof1_and_ddof0_relation(self):
        x = [1.0, 2.0, 4.0, 7.0]
        s1, s0 = ledger.describe(x, 1), ledger.describe(x, 0)
        m = sum(x) / 4
        ss = sum((v - m) ** 2 for v in x)
        self.assertAlmostEqual(s1["sd"], math.sqrt(ss / 3))
        self.assertAlmostEqual(s0["sd"], math.sqrt(ss / 4))
        self.assertAlmostEqual(s1["sd"], s1["sd_ddof0"] * math.sqrt(4 / 3))
        self.assertAlmostEqual(s1["ci95_high"] - m, 1.96 * s1["sd"] / 2)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.ep = ledger.load_episodes(EP, CFG)

    def test_fixture_step_audit_is_clean(self):
        _, mismatches, n = ledger.audit_steps(ST, self.ep, CFG)
        self.assertEqual(mismatches, [])
        self.assertEqual(n, 27)

    def test_ledger_keeps_all_failures(self):
        rows, mismatches = ledger.build_ledger(self.ep, "v")
        self.assertEqual(mismatches, [])
        self.assertEqual(len(rows), 9)
        ff = [r for r in rows if r["policy"] == "fixed_fueling"]
        self.assertTrue(all(r["end_reason"] == "fuel_depleted" and r["pre_refill_shortage_steps"] == 1 for r in ff))
        self.assertTrue(all(r["final_fuel"] == 0.0 for r in ff))

    def test_strict_safe_refill_does_not_recover(self):
        e = self.ep["safe_stock", 2]
        self.assertTrue(e["legacy_arrived"])
        self.assertEqual(e["pre_refill_reserve_violation_steps"], 1)
        self.assertFalse(e["safe_arrival"])

    def test_paired_denominators_and_null(self):
        rows = ledger.paired_summary(self.ep, 1, "v")
        get = {(r["baseline"], r["subset"], r["metric"]): r for r in rows}
        ss = get["safe_stock", "common_strict_safe", "inventory_adjusted_sci"]
        self.assertEqual((ss["n_all"], ss["n_common_safe"], ss["n_excluded"], ss["n"]), (3, 1, 2, 1))
        self.assertEqual(ss["status"], "ci_not_estimable_n1")
        ff = get["fixed_fueling", "common_strict_safe", "purchase_sci"]
        self.assertEqual((ff["n"], ff["mean_delta"], ff["status"]), (0, None, "empty_subset_null"))
        allr = get["safe_stock", "all", "purchase_sci"]
        d = [self.ep["double_dqn", s]["purchase_sci"] - self.ep["safe_stock", s]["purchase_sci"] for s in (1, 2, 3)]
        self.assertAlmostEqual(allr["mean_delta"], sum(d) / 3)
        self.assertEqual(ledger.all_policy_common_safe(self.ep), (0, 3))

    def test_inventory_identity_uses_initial_and_terminal_value(self):
        e = self.ep["double_dqn", 1]
        self.assertAlmostEqual(e["inventory_adjusted_sci"],
                               e["purchase_sci"] + e["initial_inventory_value"] - e["terminal_inventory_value"])


class ValidationTests(TempDirTest):
    def test_duplicate_seed_rejected(self):
        p = rewrite(EP, self.tmp / "e.csv", lambda rows: rows + [rows[0]])
        with self.assertRaisesRegex(ledger.InputError, "duplicate"):
            ledger.load_episodes(p, CFG)

    def test_unpaired_seed_rejected(self):
        p = rewrite(EP, self.tmp / "e.csv", lambda rows: rows[1:])
        with self.assertRaisesRegex(ledger.InputError, "seed set differs"):
            ledger.load_episodes(p, CFG)

    def test_impossible_fuel_rejected(self):
        def edit(rows):
            rows[0]["final_fuel"] = "1.2"
            return rows
        with self.assertRaisesRegex(ledger.InputError, "outside"):
            ledger.load_episodes(rewrite(EP, self.tmp / "e.csv", edit), CFG)

    def test_missing_column_rejected(self):
        with EP.open() as f:
            text = f.read().replace("final_fuel", "final_fuel_tons", 1)
        p = self.tmp / "e.csv"
        p.write_text(text)
        with self.assertRaisesRegex(ledger.InputError, "missing columns"):
            ledger.load_episodes(p, CFG)

    def test_purchase_error_reports_first_row(self):
        def edit(rows):
            rows[4]["purchase"] = str(float(rows[4]["purchase"]) + 0.01)
            return rows
        p = rewrite(ST, self.tmp / "s.csv", edit)
        ep = ledger.load_episodes(EP, CFG)
        _, mm, _ = ledger.audit_steps(p, ep, CFG)
        self.assertEqual(mm[0]["check"], "purchase_cap")
        self.assertEqual((mm[0]["policy"], mm[0]["seed"], mm[0]["step"]), ("double_dqn", 2, 2))

    def test_market_tape_mismatch_detected(self):
        def edit(rows):
            for r in rows:
                if r["policy"] == "safe_stock" and r["seed"] == "1" and r["step"] == "2":
                    r["decision_price"] = "999.0"
            return rows
        ep = ledger.load_episodes(EP, CFG)
        _, mm, _ = ledger.audit_steps(rewrite(ST, self.tmp / "s.csv", edit), ep, CFG)
        self.assertIn("market_tape", {m["check"] for m in mm})

    def test_safe_flag_inconsistency_detected(self):
        def edit(rows):
            for r in rows:
                if r["policy"] == "safe_stock" and r["seed"] == "2":
                    r["safe_arrival"] = "True"
            return rows
        ep = ledger.load_episodes(rewrite(EP, self.tmp / "e.csv", edit), CFG)
        _, mm = ledger.build_ledger(ep, "v")
        self.assertEqual(mm[0]["check"], "strict_safe_arrival")


@unittest.skipUnless(os.environ.get("BAI_EVAL_ROOT"), "set BAI_EVAL_ROOT to a bunker_disjoint_eval_v3 copy")
class LegacyBundleTests(unittest.TestCase):
    def test_paired_summary_matches_legacy_summary(self):
        root = Path(os.environ["BAI_EVAL_ROOT"])
        ep = ledger.load_episodes(root / "results/episodes.csv", CFG)
        legacy = json.loads((root / "results/summary.json").read_text())
        rows = ledger.paired_summary(ep, 1, "v", legacy=legacy)
        self.assertFalse([r for r in rows if r["legacy_match"].startswith("MISMATCH")])
        ss = [r for r in rows if r["baseline"] == "safe_stock" and r["subset"] == "all"
              and r["metric"] == "inventory_adjusted_sci"][0]
        self.assertAlmostEqual(ss["mean_delta"], 647.652980294044, places=6)
        self.assertEqual(ss["n_common_safe"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
