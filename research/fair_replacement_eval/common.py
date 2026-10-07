"""Shared pieces for the fair DQN-vs-planner replacement evaluation.

Nothing here modifies the environment, the DQN, or research/time_constrained_planner.
The episode driver mirrors ``scripts.evaluate.run_episode`` (same env, same
``VoyageAudit``) and adds latency timing, the voyage-time overlay and deadline
classification.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from envs.bunkering_env import BunkeringEnv  # noqa: E402
from evaluation.safety_accounting import VoyageAudit  # noqa: E402

CRITERIA_PATH = HERE / "criteria.json"
CRITERIA_HASH_PATH = HERE / "criteria.sha256"

# Dynamics constants are read from the environment class so they cannot drift.
REFILL = BunkeringEnv._BUNKER_REFILL_AMOUNT
CAP = BunkeringEnv._MAX_REFILLED_FUEL
AMOUNT_EPS = BunkeringEnv._BUNKER_AMOUNT_EPSILON
PRICE_MEAN = BunkeringEnv._FUEL_PRICE_MEAN
PRICE_SCALE = BunkeringEnv._FUEL_PRICE_SCALE
FX_MEAN = BunkeringEnv._FX_RATE_MEAN
FX_SCALE = BunkeringEnv._FX_RATE_SCALE
SAFETY_TOL = 1e-9


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_criteria(*, verify_hash: bool = True) -> dict[str, Any]:
    """Load the pre-registered criteria; fail loudly if the file was changed."""
    if verify_hash:
        expected = CRITERIA_HASH_PATH.read_text(encoding="utf-8").split()[0]
        actual = file_sha256(CRITERIA_PATH)
        if actual != expected:
            raise RuntimeError(
                f"criteria.json hash {actual} differs from registered {expected}; "
                "criteria must be fixed before evaluation"
            )
    return json.loads(CRITERIA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- dynamics
def fuel_step(fuel: float, buy: bool, consumption: float) -> tuple[float, float, float]:
    """One env step on fuel only. Returns (pre_refill_raw, fuel_after, amount).

    ``pre_refill_raw`` is the quantity ``VoyageAudit.observe`` checks (before
    clipping at zero and before refilling).
    """
    raw = fuel - consumption
    before = max(0.0, raw)
    requested = REFILL if buy else 0.0
    amount = max(0.0, min(requested, max(0.0, CAP - before)))
    return raw, min(CAP, before + amount), amount


def min_safe_stops(consumption: float, legs: int, reserve: float, initial_fuel: float = 1.0) -> int | None:
    """Fewest stops of any plan that is safe under VoyageAudit (None if none exists)."""
    layer = {round(initial_fuel, 12): 0}
    for _ in range(legs):
        nxt: dict[float, int] = {}
        for fuel, stops in layer.items():
            for buy in (False, True):
                raw, after, amount = fuel_step(fuel, buy, consumption)
                if raw < reserve - SAFETY_TOL:
                    continue
                added = int(amount > AMOUNT_EPS)
                key = round(after, 12)
                best = stops + added
                if key not in nxt or best < nxt[key]:
                    nxt[key] = best
        layer = nxt
        if not layer:
            return None
    return min(layer.values())


# ------------------------------------------------------------ time overlay
def voyage_hours(legs: int, stops: int, leg_hours: float, stop_hours: float) -> float:
    return legs * leg_hours + stops * stop_hours


def allowed_stops(deadline: float, legs: int, leg_hours: float, stop_hours: float) -> int:
    """Stops that fit under the deadline; negative if sailing alone misses it."""
    slack = deadline - legs * leg_hours
    if slack < -1e-9:
        return -1
    return int((slack + 1e-9) // stop_hours)


def classify_deadline(deadline: float, legs: int, leg_hours: float, stop_hours: float, needed: int | None) -> str:
    """Return one of the three classes defined in criteria.json."""
    allowed = allowed_stops(deadline, legs, leg_hours, stop_hours)
    if allowed < 0:
        return "sailing_exceeds_deadline"
    if needed is None or allowed < needed:
        return "stop_forced_exceeds_deadline"
    return "attainable"


# ------------------------------------------------------------ episode driver
def decode_observation(observation: Any, max_steps: int) -> dict[str, float]:
    """Invert the env's normalization. Clipping to [-1, 1] makes extremes lossy."""
    return {
        "price": float(observation[0]) * PRICE_SCALE + PRICE_MEAN,
        "ma30": float(observation[1]) * PRICE_SCALE + PRICE_MEAN,
        "fx": float(observation[2]) * FX_SCALE + FX_MEAN,
        "fuel": float(observation[3]),
        "route_remaining": float(observation[4]),
        "step": int(round((1.0 - float(observation[4])) * max_steps)),
    }


@dataclass
class Episode:
    seed: int
    policy: str
    scenario: str
    cost_index: float
    adjusted_sci: float
    safe: bool
    arrived: bool
    depleted: bool
    stops: int
    end_reason: str
    shortage_steps: int
    reserve_violation_steps: int
    final_fuel: float
    decision_ns: list[int]
    wall_ns: int

    def row(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "policy": self.policy,
            "scenario": self.scenario,
            "cost_index": self.cost_index,
            "adjusted_sci": self.adjusted_sci,
            "safe": int(self.safe),
            "arrived": int(self.arrived),
            "depleted": int(self.depleted),
            "stops": self.stops,
            "end_reason": self.end_reason,
            "shortage_steps": self.shortage_steps,
            "reserve_violation_steps": self.reserve_violation_steps,
            "final_fuel": self.final_fuel,
            "decision_ns_mean": sum(self.decision_ns) / max(1, len(self.decision_ns)),
            "decision_ns_max": max(self.decision_ns) if self.decision_ns else 0,
            "wall_ns": self.wall_ns,
        }


def run_episode(policy: Any, seed: int, env_config: Mapping[str, Any], scenario: str, *, timed: bool = True) -> Episode:
    """Same loop as ``scripts.evaluate.run_episode`` plus timing, audit fields."""
    env = BunkeringEnv(**dict(env_config))
    observation, _ = env.reset(seed=seed)
    audit = VoyageAudit(env._fuel_remaining, env.raw_fuel_price * env._raw_fx_rate, env.min_safe_fuel)
    stops = 0
    step_index = 0
    decision_ns: list[int] = []
    start = time.perf_counter_ns()
    while True:
        t0 = time.perf_counter_ns()
        action = policy.select_action(env, observation, step_index)
        if timed:
            decision_ns.append(time.perf_counter_ns() - t0)
        audit.observe(env._fuel_remaining, env.fuel_consumption_per_step)
        observation, _reward, terminated, truncated, info = env.step(action)
        stops += int(info["actual_bunker_amount"] > env._BUNKER_AMOUNT_EPSILON)
        step_index += 1
        if terminated or truncated:
            break
    wall = time.perf_counter_ns() - start
    end_reason = info["end_reason"]
    final = audit.finish(
        end_reason == "arrived",
        info["cumulative_cost_index"],
        env._fuel_remaining,
        env.raw_fuel_price * env._raw_fx_rate,
    )
    return Episode(
        seed=seed,
        policy=getattr(policy, "name", type(policy).__name__),
        scenario=scenario,
        cost_index=float(info["cumulative_cost_index"]),
        adjusted_sci=float(final["inventory_adjusted_sci"]),
        safe=bool(final["safe_arrival"]),
        arrived=end_reason == "arrived",
        depleted=end_reason == "fuel_depleted",
        stops=stops,
        end_reason=end_reason,
        shortage_steps=int(final["pre_refill_shortage_steps"]),
        reserve_violation_steps=int(final["pre_refill_reserve_violation_steps"]),
        final_fuel=float(final["final_fuel"]),
        decision_ns=decision_ns,
        wall_ns=wall,
    )
