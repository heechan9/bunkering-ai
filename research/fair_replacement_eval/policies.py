"""Candidate planners for the fair comparison.

Information discipline
----------------------
``planner_ops`` reads ONLY the current observation vector plus two environment
constants (``min_safe_fuel`` and ``max_steps``) and the fixed nominal model
constants in criteria.json. It never touches the environment's RNG, future
prices, or any private state. ``tests`` replace the env with a stub exposing only
those two constants to prove that.

Tiers that add information (history, schedule, forecast, oracle) are separate
classes/flags and are never used for a replacement verdict.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Sequence

import numpy as np

from .common import (
    AMOUNT_EPS,
    FX_MEAN,
    SAFETY_TOL,
    allowed_stops,
    decode_observation,
    fuel_step,
)

NOMINAL_CONSUMPTION = 0.05
COST_TIE = 9  # decimals used when comparing normalized costs


def solve_dp(
    fuel: float,
    remaining: int,
    consumption: float,
    forecast: Sequence[float],
    terminal: float,
    reserve: float,
    max_stops: int | None = None,
) -> tuple[bool | None, tuple[float, float, int] | None]:
    """Exact DP over the binary refill action for the remaining legs.

    ``forecast[j]`` is the (normalized) price*fx at which a purchase on leg j is
    valued; ``terminal`` values leftover fuel at arrival. Lexicographic
    objective: min cost, then fewest stops, then max minimum reserve margin,
    then prefer waiting. Returns (buy_now, (cost, margin, stops)) or
    (None, None) when no safe plan exists.
    """
    memo: dict[tuple[int, float, int], tuple[float, float, int] | None] = {}

    def rec(j: int, f: float, left: int) -> tuple[float, float, int] | None:
        if j == remaining:
            return (-terminal * f, f - reserve, 0)
        key = (j, round(f, 9), left)
        if key in memo:
            return memo[key]
        best: tuple[float, float, int] | None = None
        best_key: tuple[float, float, int] | None = None
        for buy in (False, True):
            raw, after, amount = fuel_step(f, buy, consumption)
            if raw < reserve - SAFETY_TOL:
                continue
            stop = int(amount > AMOUNT_EPS)
            if max_stops is not None and stop > left:
                continue
            sub = rec(j + 1, after, left - stop if max_stops is not None else 0)
            if sub is None:
                continue
            cand = (amount * forecast[j] + sub[0], min(raw - reserve, sub[1]), stop + sub[2])
            cand_key = (round(cand[0], COST_TIE), cand[2], -round(cand[1], COST_TIE))
            if best_key is None or cand_key < best_key:
                best, best_key = cand, cand_key
        memo[key] = best
        return best

    start_left = max_stops if max_stops is not None else 0
    best_action: bool | None = None
    best_val: tuple[float, float, int] | None = None
    best_key: tuple[float, float, int] | None = None
    for buy in (False, True):  # wait first: ties keep waiting
        raw, after, amount = fuel_step(fuel, buy, consumption)
        if raw < reserve - SAFETY_TOL:
            continue
        stop = int(amount > AMOUNT_EPS)
        if max_stops is not None and stop > start_left:
            continue
        sub = rec(1, after, start_left - stop if max_stops is not None else 0)
        if sub is None:
            continue
        val = (amount * forecast[0] + sub[0], min(raw - reserve, sub[1]), stop + sub[2])
        key = (round(val[0], COST_TIE), val[2], -round(val[1], COST_TIE))
        if best_key is None or key < best_key:
            best_action, best_val, best_key = buy, val, key
    return best_action, best_val


class PlannerPolicy:
    """Receding-horizon DP planner with configurable information tier.

    forecast:
      * ``persistence`` - current price*fx for every future leg (I_ops).
      * ``noisy`` - true future price*fx times lognormal noise ``sigma`` (I_forecast);
        ``sigma == 0`` is the oracle upper bound (I_oracle). Peeks at a cloned env.
    use_history: estimate consumption from the previous observation (I_ops_hist).
    deadline_stops: stops allowed by the deadline (I_schedule); fallback to the
        unconstrained plan if the constrained one is infeasible (safety first).
    """

    def __init__(
        self,
        name: str = "planner_ops",
        *,
        forecast: str = "persistence",
        sigma: float = 0.0,
        use_history: bool = False,
        deadline_stops: int | None = None,
        consumption: float = NOMINAL_CONSUMPTION,
    ) -> None:
        if forecast not in ("persistence", "noisy"):
            raise ValueError("forecast must be 'persistence' or 'noisy'")
        self.name = name
        self.forecast = forecast
        self.sigma = float(sigma)
        self.use_history = use_history
        self.deadline_stops = deadline_stops
        self.nominal_consumption = float(consumption)
        self._reset()

    def _reset(self) -> None:
        self._prev_fuel: float | None = None
        self._stops_used = 0
        self._c_hat = self.nominal_consumption
        self._episode_key = 0
        self.last_fallback = False

    # -- helpers
    def _true_future(self, env: Any, remaining: int) -> tuple[list[float], float]:
        """I_forecast/I_oracle only: read the true future from a cloned env."""
        clone = copy.deepcopy(env)
        pf = [clone.raw_fuel_price * clone._raw_fx_rate]
        for _ in range(remaining):
            clone.step(0)
            pf.append(clone.raw_fuel_price * clone._raw_fx_rate)
        return pf[:remaining], pf[remaining]

    def select_action(self, env: Any, observation: np.ndarray, step_index: int) -> int:
        legs = int(env.max_steps)
        reserve = float(env.min_safe_fuel)
        obs = decode_observation(observation, legs)
        fuel = round(obs["fuel"], 6)
        if step_index == 0:
            self._reset()
            self._episode_key = int(round(obs["price"] * 1000)) * 1000 + int(round(obs["fx"]))
        elif self._prev_fuel is not None:
            if fuel > self._prev_fuel + 1e-6:
                self._stops_used += 1
            elif self.use_history:
                self._c_hat = max(1e-4, self._prev_fuel - fuel)
        self._prev_fuel = fuel
        remaining = legs - obs["step"]
        if remaining <= 0:
            return 0
        consumption = self._c_hat if self.use_history else self.nominal_consumption

        if self.forecast == "persistence":
            forecast = [1.0] * remaining
            terminal = 1.0
        else:
            pf, term = self._true_future(env, remaining)
            base = pf[0]
            forecast = [v / base for v in pf]
            terminal = term / base
            if self.sigma > 0.0:
                rng = np.random.default_rng([self._episode_key, int(round(self.sigma * 1e6)), step_index])
                noise = np.exp(self.sigma * rng.standard_normal(remaining + 1))
                forecast = [forecast[0]] + [forecast[j] * noise[j] for j in range(1, remaining)]
                terminal *= noise[remaining]

        max_stops = None
        if self.deadline_stops is not None:
            max_stops = max(0, self.deadline_stops - self._stops_used)
        action, _ = solve_dp(fuel, remaining, consumption, forecast, terminal, reserve, max_stops)
        self.last_fallback = False
        if action is None and max_stops is not None:
            action, _ = solve_dp(fuel, remaining, consumption, forecast, terminal, reserve, None)
            self.last_fallback = True
        if action is None:
            # No safe plan under the assumed model: safety first, refill.
            self.last_fallback = True
            return 1
        return int(action)


def make_planners(sigma_grid: Sequence[float], deadline_stops: dict[str, int] | None = None) -> dict[str, PlannerPolicy]:
    """Build the registry of planner variants (names are stable keys in results)."""
    planners: dict[str, PlannerPolicy] = {
        "planner_ops": PlannerPolicy("planner_ops"),
        "planner_ops_hist": PlannerPolicy("planner_ops_hist", use_history=True),
    }
    for sigma in sigma_grid:
        name = "planner_oracle" if sigma == 0 else f"planner_fcst_{sigma:g}"
        planners[name] = PlannerPolicy(name, forecast="noisy", sigma=sigma)
    for label, stops in (deadline_stops or {}).items():
        planners[f"planner_ops_dl_{label}"] = PlannerPolicy(f"planner_ops_dl_{label}", deadline_stops=stops)
    return planners


__all__ = ["PlannerPolicy", "solve_dp", "make_planners", "NOMINAL_CONSUMPTION", "math", "FX_MEAN"]
