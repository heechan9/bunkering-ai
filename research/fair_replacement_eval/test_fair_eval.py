"""Tests for the fair replacement evaluation harness (no checkpoint needed)."""

from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from envs.bunkering_env import BunkeringEnv  # noqa: E402
from research.fair_replacement_eval import common  # noqa: E402
from research.fair_replacement_eval.decision import (  # noqa: E402
    evaluate_criteria,
    rate_diff,
    relative_cost_diff,
)
from research.fair_replacement_eval.policies import PlannerPolicy, solve_dp  # noqa: E402

CFG = {"n_ports": 3, "max_steps": 30, "min_safe_fuel": 0.15}


class CriteriaTests(unittest.TestCase):
    def test_hash_matches_registered(self):
        crit = common.load_criteria()
        self.assertEqual(crit["status"], "pre_registered_before_any_evaluation")

    def test_changed_criteria_is_rejected(self):
        original = common.CRITERIA_PATH.read_bytes()
        try:
            common.CRITERIA_PATH.write_bytes(original + b" ")
            with self.assertRaises(RuntimeError):
                common.load_criteria()
        finally:
            common.CRITERIA_PATH.write_bytes(original)
        common.load_criteria()

    def test_holdout_seeds_disjoint_from_reuse_and_default_training(self):
        crit = common.load_criteria()
        reuse = crit["evaluation_sets"]["reuse"]
        hold = crit["evaluation_sets"]["holdout"]
        reuse_seeds = set(range(reuse["base_seed"], reuse["base_seed"] + reuse["episodes"]))
        hold_seeds = set(range(hold["base_seed"], hold["base_seed"] + hold["episodes"]))
        self.assertFalse(reuse_seeds & hold_seeds)
        self.assertFalse(hold_seeds & set(range(42, 42 + 5000)))  # default train seed range
        sur = crit["surrogate_for_synthetic_validation"]
        sur_seeds = set(range(sur["train_seed"], sur["train_seed"] + sur["episodes"]))
        self.assertFalse(sur_seeds & (reuse_seeds | hold_seeds))


class DynamicsTests(unittest.TestCase):
    def test_fuel_step_matches_env(self):
        rng = np.random.default_rng(0)
        for consumption in (0.04, 0.05, 0.06):
            env = BunkeringEnv(**CFG, fuel_consumption_per_step=consumption)
            env.reset(seed=3)
            fuel = env._fuel_remaining
            for _ in range(30):
                buy = bool(rng.integers(0, 2))
                raw, after, amount = common.fuel_step(fuel, buy, consumption)
                _, _, term, trunc, info = env.step(1 if buy else 0)
                self.assertAlmostEqual(env._fuel_remaining, after, places=12)
                self.assertAlmostEqual(info["actual_bunker_amount"], amount, places=12)
                fuel = env._fuel_remaining
                if term or trunc:
                    break

    def test_min_safe_stops(self):
        self.assertEqual(common.min_safe_stops(0.05, 30, 0.15), 1)
        self.assertEqual(common.min_safe_stops(0.045, 30, 0.15), 1)
        self.assertEqual(common.min_safe_stops(0.055, 30, 0.15), 2)
        self.assertEqual(common.min_safe_stops(0.06, 30, 0.15), 2)

    def test_deadline_classes(self):
        crit = common.load_criteria()
        ov = crit["time_overlay"]
        needed = common.min_safe_stops(0.05, 30, 0.15)
        got = {
            label: common.classify_deadline(d, 30, ov["leg_hours"], ov["stop_hours"], needed)
            for label, d in ov["deadlines_hours"].items()
        }
        self.assertEqual(got["sailing_exceeds"], "sailing_exceeds_deadline")
        self.assertEqual(got["zero_stop"], "stop_forced_exceeds_deadline")
        self.assertEqual(got["one_stop"], "attainable")
        self.assertEqual(got["slack"], "attainable")
        # Under +20% demand two stops are needed, so one_stop becomes stop-forced.
        needed2 = common.min_safe_stops(0.06, 30, 0.15)
        self.assertEqual(
            common.classify_deadline(ov["deadlines_hours"]["one_stop"], 30, ov["leg_hours"], ov["stop_hours"], needed2),
            "stop_forced_exceeds_deadline",
        )


class PlannerTests(unittest.TestCase):
    def test_dp_matches_brute_force(self):
        rng = np.random.default_rng(1)
        remaining = 9
        for _ in range(25):
            fuel = float(rng.uniform(0.3, 0.95))
            forecast = list(rng.uniform(0.9, 1.1, size=remaining))
            terminal = float(rng.uniform(0.9, 1.1))
            c, reserve = 0.05, 0.15
            action, value = solve_dp(fuel, remaining, c, forecast, terminal, reserve)
            best = None
            for plan in itertools.product((False, True), repeat=remaining):
                f, cost, margin, stops, ok = fuel, 0.0, 9.0, 0, True
                for j, buy in enumerate(plan):
                    raw, f_after, amount = common.fuel_step(f, buy, c)
                    if raw < reserve - 1e-9:
                        ok = False
                        break
                    cost += amount * forecast[j]
                    margin = min(margin, raw - reserve)
                    stops += int(amount > common.AMOUNT_EPS)
                    f = f_after
                if not ok:
                    continue
                cost -= terminal * f
                margin = min(margin, f - reserve)
                key = (round(cost, 9), stops, -round(margin, 9))
                if best is None or key < best[0]:
                    best = (key, plan[0])
            if best is None:
                self.assertIsNone(action)
            else:
                self.assertEqual(
                    (round(value[0], 9), value[2], -round(value[1], 9)), best[0]
                )

    def test_planner_ops_uses_only_observation(self):
        """Replace the env by a stub with only the two allowed constants."""
        stub = SimpleNamespace(min_safe_fuel=0.15, max_steps=30)
        real = BunkeringEnv(**CFG)
        obs, _ = real.reset(seed=11)
        a, b = PlannerPolicy(), PlannerPolicy()
        for step in range(30):
            act_real = a.select_action(real, obs, step)
            act_stub = b.select_action(stub, obs, step)
            self.assertEqual(act_real, act_stub)
            obs, _, term, trunc, _ = real.step(act_real)
            if term or trunc:
                break

    def test_planner_ops_safe_on_nominal(self):
        for seed in range(10_000_000, 10_000_020):
            ep = common.run_episode(PlannerPolicy(), seed, CFG, "nominal", timed=False)
            self.assertTrue(ep.safe, seed)
            self.assertEqual(ep.stops, 1, seed)

    def test_oracle_cheaper_than_persistence_on_average(self):
        seeds = range(10_000_000, 10_000_030)
        ops = np.mean([common.run_episode(PlannerPolicy(), s, CFG, "n", timed=False).adjusted_sci for s in seeds])
        orc = np.mean([common.run_episode(PlannerPolicy("o", forecast="noisy", sigma=0.0), s, CFG, "n", timed=False).adjusted_sci for s in seeds])
        self.assertLess(orc, ops)

    def test_deadline_aware_respects_limit(self):
        ep = common.run_episode(PlannerPolicy("dl", deadline_stops=1), 10_000_001, CFG, "n", timed=False)
        self.assertEqual(ep.stops, 1)
        self.assertTrue(ep.safe)

    def test_runner_matches_repo_evaluate_path(self):
        from evaluation.contract import EvaluationCase
        from scripts import baseline
        from scripts.evaluate import run_episode as repo_run

        for strategy in (baseline.FixedFuelingStrategy(), baseline.PriceReactiveStrategy(), baseline.SafeStockStrategy()):
            for seed in (42, 43, 44, 45, 46):
                mine = common.run_episode(strategy, seed, CFG, "n", timed=False)
                ref = repo_run(strategy, EvaluationCase(seed=seed, episode=0, policy=strategy.name, env_config=dict(CFG)))
                self.assertAlmostEqual(mine.cost_index, ref.synthetic_cost_index, places=6)
                self.assertEqual(mine.arrived, ref.success)
                self.assertEqual(mine.stops, ref.bunkering_count)


def _rows(seeds, safe, cost, stops=1):
    return [
        {"seed": s, "safe": int(sf), "arrived": int(sf), "depleted": int(not sf), "stops": stops,
         "adjusted_sci": c, "cost_index": c}
        for s, sf, c in zip(seeds, safe, cost)
    ]


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.crit = common.load_criteria()
        seeds = list(range(1000))
        rng = np.random.default_rng(5)
        base_cost = 1000 + rng.normal(0, 20, 1000)
        self.hold = {}
        for sc in ("nominal", "demand_minus_10pct", "demand_plus_10pct", "demand_minus_20pct", "demand_plus_20pct"):
            self.hold[sc] = {
                "planner_ops": _rows(seeds, [True] * 1000, base_cost),
                "double_dqn": _rows(seeds, [True] * 1000, base_cost * 1.01),
            }
        self.runtime = {"planner_ops": {"p99_ms": 5.0}, "double_dqn": {"p99_ms": 0.2}}
        self.gates = {"G1_official_incumbent": True, "G2_holdout_disjoint": True, "G3_criteria_hash": True,
                      "G4_holdout_size": True, "G5_reuse_consistency": True}

    def _eval(self, **overrides):
        gates = {**self.gates, **overrides.get("gates", {})}
        return evaluate_criteria(self.hold, overrides.get("runtime", self.runtime), gates,
                                 overrides.get("official", True), self.crit, 30, 0.15)

    def test_all_pass_official(self):
        out = self._eval()
        self.assertEqual(out["verdict"], "REPLACEMENT_EVIDENCE_SUFFICIENT")
        self.assertEqual(out["criteria"]["R2_cost"]["label"], "cost_superior")

    def test_surrogate_never_sufficient(self):
        out = self._eval(gates={"G1_official_incumbent": False}, official=False)
        self.assertEqual(out["verdict"], "SYNTHETIC_VALIDATION_ONLY")
        self.assertTrue(out["would_pass_all_if_official"])

    def test_other_gate_failure_not_decidable(self):
        self.assertEqual(self._eval(gates={"G4_holdout_size": False})["verdict"], "NOT_DECIDABLE")

    def test_slow_planner_fails_runtime(self):
        out = self._eval(runtime={"planner_ops": {"p99_ms": 80.0}, "double_dqn": {"p99_ms": 0.2}})
        self.assertEqual(out["verdict"], "REPLACEMENT_EVIDENCE_INSUFFICIENT")
        self.assertFalse(out["criteria"]["R4_runtime"]["pass"])

    def test_unsafe_candidate_fails_safety(self):
        seeds = list(range(1000))
        self.hold["nominal"]["planner_ops"] = _rows(seeds, [i >= 5 for i in seeds], [1000.0] * 1000)
        out = self._eval()
        self.assertFalse(out["criteria"]["R1_safety"]["pass"])

    def test_costlier_candidate_fails_cost(self):
        seeds = list(range(1000))
        base = [1000.0 + (i % 7) for i in seeds]
        self.hold["nominal"]["planner_ops"] = _rows(seeds, [True] * 1000, [c * 1.02 for c in base])
        self.hold["nominal"]["double_dqn"] = _rows(seeds, [True] * 1000, base)
        self.assertFalse(self._eval()["criteria"]["R2_cost"]["pass"])

    def test_stop_forced_deadlines_are_not_judged(self):
        out = self._eval()
        judged = out["criteria"]["R3_time"]["per_deadline"]
        self.assertFalse(judged["sailing_exceeds"]["judged"])
        self.assertFalse(judged["zero_stop"]["judged"])
        self.assertTrue(judged["one_stop"]["judged"])

    def test_bootstrap_identity(self):
        rng = np.random.default_rng(0)
        a = np.ones(50)
        d = rate_diff(a, a.copy(), rng, 200)
        self.assertEqual((d["diff"], d["lo"], d["hi"]), (0.0, 0.0, 0.0))
        c = np.linspace(1, 2, 50)
        r = relative_cost_diff(c, c, np.ones(50, dtype=bool), rng, 200)
        self.assertEqual(r["rel_diff"], 0.0)


if __name__ == "__main__":
    unittest.main()
