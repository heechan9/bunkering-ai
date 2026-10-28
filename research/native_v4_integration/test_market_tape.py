"""Seed-regenerated market tape: equality with the pinned env and terminal-valuation counterexamples."""
import copy
import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
from envs.bunkering_env import BunkeringEnv  # noqa: E402
from evaluation.safety_accounting import VoyageAudit  # noqa: E402
import ledger  # noqa: E402
import market_tape  # noqa: E402
from test_config_cli import CFG, run  # noqa: E402

SEEDS = [1, 2, 3]
# Fixed action plans stand in for policies (paired_summary needs a "double_dqn" comparator);
# the tape must not depend on them.
PLANS = {"never": lambda n: 0, "every_third": lambda n: 1 if n % 3 == 0 else 0,
         "double_dqn": lambda n: 3 if n % 4 == 0 else 0}


def env_episode(seed, name, plan, traces):
    """Mirror the bundle's run_evaluation.episode for a fixed action plan."""
    env = BunkeringEnv(n_ports=3, max_steps=30, min_safe_fuel=0.15, fuel_consumption_per_step=0.05)
    env.reset(seed=seed)
    audit = VoyageAudit(env._fuel_remaining, env.raw_fuel_price * env._raw_fx_rate, env.min_safe_fuel)
    n = 0
    while True:
        a, before = plan(n), env._fuel_remaining
        price, fx = env.raw_fuel_price, env._raw_fx_rate
        audit.observe(before, env.fuel_consumption_per_step)
        _, _, term, trunc, info = env.step(a)
        n += 1
        traces.append({"seed": seed, "policy": name, "step": n, "action": a, "fuel_before": before,
                       "pre_refill_unclipped": before - env.fuel_consumption_per_step,
                       "decision_price": price, "decision_fx": fx, "purchase": info["actual_bunker_amount"],
                       "fuel_after": env._fuel_remaining, "step_sci": info["step_cost_index"]})
        if term or trunc:
            break
    return {"seed": seed, "policy": name, "steps": n, "end_reason": info["end_reason"],
            **audit.finish(info["voyage_success"], info["cumulative_cost_index"], env._fuel_remaining,
                           env.raw_fuel_price * env._raw_fx_rate)}


def write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class RegenerateTests(unittest.TestCase):
    def test_constants_match_pinned_env(self):
        self.assertEqual(market_tape.PRICE_RANGE, BunkeringEnv._PRICE_RANGE)
        self.assertEqual(market_tape.FX_RANGE, BunkeringEnv._FX_RANGE)
        self.assertEqual(market_tape.PRICE_INIT[0], BunkeringEnv._FUEL_PRICE_MEAN)
        self.assertEqual(market_tape.FX_INIT[0], BunkeringEnv._FX_RATE_MEAN)

    def test_tape_equals_env_stream_for_any_actions(self):
        for seed in [0, 42, 91000000, 2**40 + 7]:
            tape = market_tape.regenerate(seed, 30)
            for name, plan in PLANS.items():
                env = BunkeringEnv(n_ports=3, max_steps=30)
                env.reset(seed=seed)
                seen = [(env.raw_fuel_price, env._raw_fx_rate)]
                for n in range(30):
                    env.step(plan(n))
                    seen.append((env.raw_fuel_price, env._raw_fx_rate))
                with self.subTest(seed=seed, plan=name):
                    self.assertEqual(seen, tape)  # exact, not approximate


class LegacyEmptySummaryTests(unittest.TestCase):
    def compare(self, ref, values=()):
        legacy = {"paired": {"never": {"all_purchase_sci_ddqn_minus_baseline": ref}}}
        return ledger._legacy_compare(legacy, "never", "all", "purchase_sci", ledger.describe(values, 1))

    def test_empty_mean_and_intervals_are_all_null(self):
        ref = {"n": 0, "mean": None, "ci95_low": None, "ci95_high": None}
        self.assertEqual(self.compare(ref)["legacy_match"], "match_null")

    def test_empty_finite_intervals_are_mismatches(self):
        for low, high in ((123, None), (None, 456), (123, 456), (0, 0)):
            with self.subTest(low=low, high=high):
                ref = {"n": 0, "mean": None, "ci95_low": low, "ci95_high": high}
                self.assertEqual(self.compare(ref)["legacy_match"], "MISMATCH_expected_null")

    def test_empty_nonfinite_fields_remain_input_errors(self):
        for field in ("mean", "ci95_low", "ci95_high"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value):
                    ref = {"n": 0, "mean": None, "ci95_low": None, "ci95_high": None}
                    ref[field] = value
                    with self.assertRaisesRegex(ledger.InputError, "must be finite"):
                        self.compare(ref)

    def test_nonempty_comparisons_keep_existing_interval_contract(self):
        for values, expected in (([5.0], "mean_match_ci_contract_differs_n1"), ([1.0, 3.0], "match")):
            with self.subTest(values=values):
                st = ledger.describe(values, 1)
                ref = {name: st[name] for name in ("n", "mean", "ci95_low", "ci95_high")}
                if len(values) == 1:
                    ref.update(ci95_low=5.0, ci95_high=5.0)
                self.assertEqual(self.compare(ref, values)["legacy_match"], expected)
        ref["ci95_high"] += 10
        self.assertEqual(self.compare(ref, values)["legacy_match"], "MISMATCH_ci")


class ValuationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        traces, eps = [], []
        for seed in SEEDS:
            for name, plan in PLANS.items():
                eps.append(env_episode(seed, name, plan, traces))
        write(self.tmp / "episodes.csv", eps)
        write(self.tmp / "steps.csv", traces)
        cfg = copy.deepcopy(CFG)
        cfg["integration"]["seed_range_inclusive"]["value"] = [SEEDS[0], SEEDS[-1]]
        (self.tmp / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.cfg = cfg

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit_episodes(self, edit):
        path = self.tmp / "episodes.csv"
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        edit(rows[0])
        write(path, rows)
        return rows[0]["policy"], int(rows[0]["seed"])

    def ledger(self, *extra):
        return run("ledger", "--config", self.tmp / "config.json", "--episodes", self.tmp / "episodes.csv",
                   "--steps", self.tmp / "steps.csv", "--out-dir", self.tmp / "out", *extra)

    def test_env_generated_episodes_pass_with_regenerated_market(self):
        ep = ledger.load_episodes(self.tmp / "episodes.csv", self.cfg)
        mm, n = market_tape.audit_valuation(ep, self.tmp / "steps.csv")
        self.assertEqual((mm, n), ([], len(SEEDS)))
        code, out, _ = self.ledger("--regenerate-market")
        report = json.loads(out)
        self.assertEqual((code, report["status"]), (0, "PASS"), out)
        self.assertEqual(report["terminal_valuation_status"], "regenerated_market_tape_match")
        self.assertEqual(report["contract_adoption_status"], "not_established_by_ledger")

    def make_legacy_summary(self, mismatch=False):
        episodes = ledger.load_episodes(self.tmp / "episodes.csv", self.cfg)
        paired = {}
        for row in ledger.paired_summary(episodes, 1, "fixture"):
            subset = "common_safe" if row["subset"] == "common_strict_safe" else "all"
            paired.setdefault(row["baseline"], {})[f"{subset}_{row['metric']}_ddqn_minus_baseline"] = {
                "n": row["n"], "mean": row["mean_delta"],
                "ci95_low": row["ci95_low"], "ci95_high": row["ci95_high"]}
        if mismatch:
            paired["never"]["all_purchase_sci_ddqn_minus_baseline"]["mean"] += 100.0
        path = self.tmp / "legacy.json"
        path.write_text(json.dumps({"paired": paired}), encoding="utf-8")
        return path

    def check_legacy_status(self, expected, exit_code, *extra):
        code, text, _ = self.ledger("--regenerate-market", *extra)
        report = json.loads(text)
        manifest = json.loads((self.tmp / "out" / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(code, exit_code, text)
        self.assertEqual(report["legacy_summary_status"], expected)
        self.assertEqual(manifest["report"]["legacy_summary_status"], expected)
        self.assertEqual(report["legacy_summary_mismatches"], 1 if exit_code == 1 else 0)
        self.assertEqual(report["status"], "FAIL" if exit_code == 1 else "PASS")
        self.assertEqual(report["contract_adoption_status"], "not_established_by_ledger")

    def test_legacy_summary_absent_reports_not_checked(self):
        self.check_legacy_status("not_checked", 0)

    def test_legacy_summary_match_is_recorded_in_manifest(self):
        self.check_legacy_status("checked_match", 0, "--legacy-summary", self.make_legacy_summary())

    def test_legacy_summary_mismatch_is_recorded_in_manifest(self):
        self.check_legacy_status("checked_mismatch", 1, "--legacy-summary", self.make_legacy_summary(mismatch=True))

    def test_empty_legacy_finite_ci_cannot_report_pass(self):
        for low, high in ((123, None), (None, 456), (123, 456)):
            with self.subTest(low=low, high=high):
                path = self.make_legacy_summary()
                data = json.loads(path.read_text(encoding="utf-8"))
                ref = data["paired"]["never"]["common_safe_purchase_sci_ddqn_minus_baseline"]
                self.assertEqual((ref["n"], ref["mean"]), (0, None))
                ref.update(ci95_low=low, ci95_high=high)
                path.write_text(json.dumps(data), encoding="utf-8")
                self.check_legacy_status("checked_mismatch", 1, "--legacy-summary", path, "--overwrite")

    def test_without_flag_stays_incomplete(self):
        code, out, _ = self.ledger()
        self.assertEqual((code, json.loads(out)["status"]), (3, "INCOMPLETE"))

    def test_legacy_nonfinite_values_are_input_errors_not_matches(self):
        for field in ("mean", "ci95_low", "ci95_high"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value):
                    path = self.make_legacy_summary()
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["paired"]["never"]["all_purchase_sci_ddqn_minus_baseline"][field] = value
                    path.write_text(json.dumps(data), encoding="utf-8")
                    code, out, err = self.ledger("--regenerate-market", "--legacy-summary", path)
                    self.assertEqual(code, 2, out)
                    self.assertIn("must be finite", err)
                    self.assertFalse((self.tmp / "out" / "run_manifest.json").exists())

    def test_legacy_count_and_value_types_are_validated(self):
        cases = [("n", True), ("n", 3.0), ("n", -1), ("mean", True),
                 ("mean", "NaN"), ("mean", None), ("ci95_low", None)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                path = self.make_legacy_summary()
                data = json.loads(path.read_text(encoding="utf-8"))
                data["paired"]["never"]["all_purchase_sci_ddqn_minus_baseline"][field] = value
                path.write_text(json.dumps(data), encoding="utf-8")
                code, out, err = self.ledger("--regenerate-market", "--legacy-summary", path)
                self.assertEqual(code, 2, out)
                self.assertIn("legacy-summary:", err)

    def test_regenerated_market_without_steps_stays_incomplete(self):
        code, out, _ = run("ledger", "--config", self.tmp / "config.json", "--episodes", self.tmp / "episodes.csv",
                           "--out-dir", self.tmp / "out", "--regenerate-market")
        report = json.loads(out)
        self.assertEqual((code, report["status"]), (3, "INCOMPLETE"))
        self.assertEqual(report["terminal_valuation_status"], "regenerated_market_tape_match")

    def test_balanced_terminal_shift_is_caught(self):
        # Terminal +100 with adjusted SCI -100 keeps the identity balanced; only the tape catches it.
        def edit(r):
            r["terminal_inventory_value"] = str(float(r["terminal_inventory_value"]) + 100)
            r["inventory_adjusted_sci"] = str(float(r["inventory_adjusted_sci"]) - 100)
        key = self.edit_episodes(edit)
        self.assertEqual(self.ledger()[0], 3)  # identity alone cannot see it
        code, out, _ = run("ledger", "--config", self.tmp / "config.json", "--episodes", self.tmp / "episodes.csv",
                           "--steps", self.tmp / "steps.csv", "--out-dir", self.tmp / "out2", "--regenerate-market")
        report = json.loads(out)
        self.assertEqual((code, report["status"]), (1, "FAIL"))
        self.assertEqual(report["first_mismatch"]["check"], "regenerated_terminal_value")
        self.assertEqual((report["first_mismatch"]["policy"], report["first_mismatch"]["seed"]), key)

    def test_shifted_initial_value_is_caught(self):
        def edit(r):
            r["initial_inventory_value"] = str(float(r["initial_inventory_value"]) + 1)
            r["inventory_adjusted_sci"] = str(float(r["inventory_adjusted_sci"]) + 1)
        self.edit_episodes(edit)
        ep = ledger.load_episodes(self.tmp / "episodes.csv", self.cfg)
        mm, _ = market_tape.audit_valuation(ep)
        self.assertEqual([m["check"] for m in mm], ["regenerated_initial_value"])

    def test_consistent_but_foreign_decision_tape_is_caught(self):
        # Same fake price on every policy keeps the cross-policy tape check green.
        path = self.tmp / "steps.csv"
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["seed"] == "2" and r["step"] == "1":
                r["decision_price"] = str(float(r["decision_price"]) + 1)
                r["step_sci"] = str(float(r["purchase"]) * float(r["decision_price"]) * float(r["decision_fx"]))
        write(path, rows)
        ep = ledger.load_episodes(self.tmp / "episodes.csv", self.cfg)
        _, step_mm, _ = ledger.audit_steps(path, ep, self.cfg)
        self.assertNotIn("market_tape", {m["check"] for m in step_mm})
        mm, _ = market_tape.audit_valuation(ep, path)
        self.assertEqual({(m["check"], m["seed"], m["step"]) for m in mm},
                         {("regenerated_decision_market", 2, 1)})

    def test_coherent_foreign_price_or_fx_passes_old_accounting_but_fails_regeneration(self):
        ep_path, st_path = self.tmp / "episodes.csv", self.tmp / "steps.csv"
        with ep_path.open(encoding="utf-8", newline="") as stream:
            original_ep = list(csv.DictReader(stream))
        with st_path.open(encoding="utf-8", newline="") as stream:
            original_st = list(csv.DictReader(stream))
        for field in ("decision_price", "decision_fx"):
            with self.subTest(field=field):
                eps, traces = copy.deepcopy(original_ep), copy.deepcopy(original_st)
                factor = 1.01
                for row in traces:
                    if row["seed"] == "2":
                        row[field] = str(float(row[field]) * factor)
                        row["step_sci"] = str(float(row["purchase"]) * float(row["decision_price"]) * float(row["decision_fx"]))
                for row in eps:
                    if row["seed"] == "2":
                        for key in ("purchase_sci", "initial_inventory_value", "terminal_inventory_value", "inventory_adjusted_sci"):
                            row[key] = str(float(row[key]) * factor)
                write(ep_path, eps)
                write(st_path, traces)
                out = self.tmp / field
                common = ("ledger", "--config", self.tmp / "config.json", "--episodes", ep_path,
                          "--steps", st_path)
                code, text, _ = run(*common, "--out-dir", out)
                report = json.loads(text)
                self.assertEqual((code, report["accounting_status"]), (3, "PASS"), text)
                code, text, _ = run(*common, "--out-dir", self.tmp / (field + "_regen"), "--regenerate-market")
                report = json.loads(text)
                self.assertEqual((code, report["status"]), (1, "FAIL"), text)
                with (self.tmp / (field + "_regen") / "accounting_mismatches.csv").open(newline="") as stream:
                    checks = {r["check"] for r in csv.DictReader(stream)}
                self.assertTrue({"regenerated_initial_value", "regenerated_terminal_value", "regenerated_decision_market"} <= checks)


@unittest.skipUnless(os.environ.get("BAI_EVAL_ROOT"), "set BAI_EVAL_ROOT to a bunker_disjoint_eval_v3 copy")
class LegacyBundleMarketTests(unittest.TestCase):
    def test_recorded_bundle_matches_regenerated_market(self):
        root = Path(os.environ["BAI_EVAL_ROOT"])
        ep = ledger.load_episodes(root / "results/episodes.csv", CFG)
        mm, n = market_tape.audit_valuation(ep, root / "results/steps.csv")
        self.assertEqual(mm, [])
        self.assertEqual(n, 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
