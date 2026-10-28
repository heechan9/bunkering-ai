"""Native env counterexamples. Expected values come from the C01/C02 formula, not policy win rates.

Already covered by the bundle's test_consistency.py and not repeated here:
action 1/2/3 equivalence, consume-before-refill at f=0.8, shortage before clip at
f=0.02, legacy safe_stock threshold dtype, negative initial shortage not safe.
"""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
from envs.bunkering_env import BunkeringEnv  # noqa: E402
from evaluation.safety_accounting import VoyageAudit  # noqa: E402
from ledger import expected_transition  # noqa: E402
from policies import SafeStockPreRefillV1  # noqa: E402
from scripts.baseline import SafeStockStrategy  # noqa: E402

CFG = json.loads((HERE / "config" / "bai_v4_native.json").read_text())
R, C, TOL = 0.15, 0.05, 1e-9


def env_at(fuel):
    e = BunkeringEnv(n_ports=3, max_steps=30, min_safe_fuel=R, fuel_consumption_per_step=C)
    e.reset(seed=42)
    e._fuel_remaining = fuel
    e._state = e._observation()
    return e


def audited_step(fuel, action):
    e = env_at(fuel)
    audit = VoyageAudit(fuel, 1.0, R)
    audit.observe(e._fuel_remaining, e.fuel_consumption_per_step)
    _, _, term, trunc, info = e.step(action)
    return e, audit, term, info


class ConfigMatchesNativeTests(unittest.TestCase):
    def test_native_constants_match_env(self):
        e = BunkeringEnv()
        n = {k: v["value"] for k, v in CFG["native_fixed"].items() if k != "_note"}
        self.assertEqual(n["consumption_per_step"], e.fuel_consumption_per_step)
        self.assertEqual(n["reserve"], e.min_safe_fuel)
        self.assertEqual(n["refill_request"], BunkeringEnv._BUNKER_REFILL_AMOUNT)
        self.assertEqual(n["max_fill"], BunkeringEnv._MAX_REFILLED_FUEL)
        self.assertEqual(n["max_steps"], e.max_steps)
        self.assertEqual(n["n_ports"] + 1, e.action_space.n)


class ReserveBoundaryTests(unittest.TestCase):
    def test_f020_pre_refill_is_reserve_no_violation(self):
        _, audit, _, _ = audited_step(0.20, 1)
        self.assertAlmostEqual(audit.minimum_pre_refill, 0.15)
        self.assertEqual(audit.reserve_violation_steps, 0)

    def test_f015_pre_refill_010_violation(self):
        e, audit, _, info = audited_step(0.15, 1)
        self.assertAlmostEqual(audit.minimum_pre_refill, 0.10)
        self.assertEqual(audit.reserve_violation_steps, 1)
        self.assertAlmostEqual(e._fuel_remaining, 0.95)  # refill does not erase the violation

    def test_f002_shortage_hidden_by_clip_is_kept(self):
        e, audit, term, info = audited_step(0.02, 1)
        self.assertAlmostEqual(audit.minimum_pre_refill, -0.03)
        self.assertEqual(audit.shortage_steps, 1)
        self.assertAlmostEqual(info["actual_bunker_amount"], 0.9)
        self.assertFalse(term)
        self.assertFalse(audit.finish(True, 0.0, e._fuel_remaining, 1.0)["safe_arrival"])

    def test_tolerance_edges(self):
        cases = [(R - 0.5 * TOL, 0, 0), (R - 2 * TOL, 0, 1), (-0.5 * TOL, 0, 1), (-2 * TOL, 1, 1)]
        for remaining, shortage, reserve in cases:
            a = VoyageAudit(remaining, 1.0, R)
            a.observe(remaining, 0.0)
            self.assertEqual((a.shortage_steps, a.reserve_violation_steps), (shortage, reserve), remaining)


class TransitionTests(unittest.TestCase):
    def test_env_matches_contract_formula_on_grid(self):
        for fuel in [0.0, 0.02, 0.04, 0.05, 0.1, 0.15, 0.2, 0.45, 0.5, 0.8, 0.9, 0.95, 1.0]:
            for action in range(4):
                e = env_at(fuel)
                info = e.step(action)[4]
                _, _, q, f_next = expected_transition(fuel, action, CFG)
                self.assertAlmostEqual(info["actual_bunker_amount"], q, places=12, msg=(fuel, action))
                self.assertAlmostEqual(e._fuel_remaining, f_next, places=12, msg=(fuel, action))

    def test_cap_and_actual_purchase(self):
        # Full tank: requested 0.9 but actual 0; this is why fixed_fueling's cost is ~0.
        self.assertEqual(expected_transition(1.0, 1, CFG)[2], 0.0)
        self.assertAlmostEqual(expected_transition(0.5, 1, CFG)[2], 0.5)  # capped by 0.95 - 0.45
        self.assertAlmostEqual(expected_transition(0.02, 1, CFG)[2], 0.9)  # request binds, b=0

    def test_purchase_cost_uses_decision_snapshot(self):
        e = env_at(0.5)
        price, fx = e.raw_fuel_price, e._raw_fx_rate
        info = e.step(1)[4]
        self.assertAlmostEqual(info["step_cost_index"], info["actual_bunker_amount"] * price * fx)
        self.assertNotEqual(e.raw_fuel_price, price)  # post-step price moved; cost did not use it

    def test_early_termination(self):
        e, audit, term, info = audited_step(0.05, 0)
        self.assertTrue(term)
        self.assertEqual(info["end_reason"], "fuel_depleted")
        self.assertEqual(audit.shortage_steps, 0)  # u == 0 exactly is not a shortage
        self.assertEqual(audit.reserve_violation_steps, 1)


class PreRefillPolicyTests(unittest.TestCase):
    def test_threshold_is_float32_of_reserve_plus_consumption(self):
        e = env_at(0.2)
        t = SafeStockPreRefillV1().threshold(e, e._state)
        self.assertEqual(t.dtype, np.float32)
        self.assertEqual(t, np.float32(0.2))

    def test_boundary_in_observation_dtype(self):
        p = SafeStockPreRefillV1()
        above = float(np.nextafter(np.float32(0.2), np.float32(1.0)))
        for fuel, action in [(0.2, 1), (0.19, 1), (above, 0), (0.25, 0)]:
            e = env_at(fuel)
            self.assertEqual(p.select_action(e, e._state, 0), action, fuel)

    def test_refill_at_threshold_keeps_reserve_next_step(self):
        p = SafeStockPreRefillV1()
        e = env_at(0.2)
        audit = VoyageAudit(0.2, 1.0, R)
        for _ in range(30):
            a = p.select_action(e, e._state, 0)
            audit.observe(e._fuel_remaining, e.fuel_consumption_per_step)
            _, _, term, trunc, _ = e.step(a)
            if term or trunc:
                break
        self.assertEqual((audit.shortage_steps, audit.reserve_violation_steps), (0, 0))

    def test_already_below_threshold_is_not_retroactively_safe(self):
        p = SafeStockPreRefillV1()
        e = env_at(0.18)
        audit = VoyageAudit(0.18, 1.0, R)
        self.assertEqual(p.select_action(e, e._state, 0), 1)
        audit.observe(e._fuel_remaining, e.fuel_consumption_per_step)
        e.step(1)
        self.assertEqual(audit.reserve_violation_steps, 1)
        self.assertAlmostEqual(e._fuel_remaining, 0.95)

    def test_legacy_safe_stock_unchanged(self):
        # Legacy rule still waits until 0.15, so its pre-refill fuel is 0.10.
        e = env_at(0.2)
        self.assertEqual(SafeStockStrategy().select_action(e, e._state, 0), 0)
        self.assertEqual(SafeStockStrategy.name, "safe_stock")
        self.assertNotEqual(SafeStockPreRefillV1.name, SafeStockStrategy.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
