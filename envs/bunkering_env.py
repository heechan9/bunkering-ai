"""Synthetic vessel bunkering-trading reinforcement-learning environment."""

from __future__ import annotations

from collections import deque

import gymnasium as gym
import numpy as np
from gymnasium import spaces


# Keep this order aligned with docs/technical/state_action_reward_spec.md.
STATE_VARS = [
    "fuel_price",
    "fuel_price_ma30",
    "fx_rate",
    "fuel_remaining",
    "route_remaining",
    "sfc",
]

REWARD_WEIGHTS = {
    "fuel_cost_saving": 1.0,
    "risk_penalty": 0.5,
    "operational_efficiency": 0.3,
    "imo_compliance_bonus": 0.2,
}


class BunkeringEnv(gym.Env):
    """A small synthetic environment for port-level bunkering decisions.

    Action ``0`` means do not bunker; actions ``1..n_ports`` bunker at a port.
    Observations are normalized to the declared ``[-1, 1]`` range.
    """

    metadata = {"render_modes": ["human"]}

    _FUEL_PRICE_MEAN = 500.0
    _FUEL_PRICE_SCALE = 150.0
    _FX_RATE_MEAN = 1300.0
    _FX_RATE_SCALE = 90.0
    _SFC = 0.19
    _FUEL_CONSUMPTION_PER_STEP = 0.05
    _BUNKER_REFILL_AMOUNT = 0.9
    _MAX_REFILLED_FUEL = 0.95
    _BUNKER_AMOUNT_EPSILON = 1e-6
    _PRICE_RANGE = (250.0, 850.0)
    _FX_RANGE = (1000.0, 1600.0)

    def __init__(
        self, n_ports: int = 3, max_steps: int = 30, min_safe_fuel: float = 0.15
    ):
        super().__init__()
        if n_ports < 1:
            raise ValueError("n_ports must be at least 1")
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if not 0.0 <= min_safe_fuel <= 1.0:
            raise ValueError("min_safe_fuel must be between 0 and 1")

        self.n_ports = n_ports
        self.max_steps = max_steps
        self.min_safe_fuel = min_safe_fuel

        # Do not change either declared space: downstream agents depend on them.
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(len(STATE_VARS),), dtype=np.float32
        )
        self.action_space = spaces.Discrete(1 + self.n_ports)

        self._step_count = 0
        self._state: np.ndarray | None = None
        self._raw_fuel_price = self._FUEL_PRICE_MEAN
        self._raw_fx_rate = self._FX_RATE_MEAN
        self._fuel_remaining = 1.0
        self._route_remaining = 1.0
        self._price_history: deque[float] = deque(maxlen=30)
        self._decision_fuel_price = self._FUEL_PRICE_MEAN
        self._decision_price_ma30 = self._FUEL_PRICE_MEAN
        self._decision_fx_rate = self._FX_RATE_MEAN
        self._cumulative_cost_index = 0.0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self._step_count = 0
        self._cumulative_cost_index = 0.0
        self._state = self._init_state()
        # Initialize a fresh decision snapshot so values cannot leak across episodes.
        self._decision_fuel_price = self._raw_fuel_price
        self._decision_price_ma30 = self.raw_price_ma30
        self._decision_fx_rate = self._raw_fx_rate
        return self._state, {"state_vars": STATE_VARS}

    def step(self, action: int):
        assert self.action_space.contains(action), f"invalid action: {action}"
        if self._state is None:
            raise RuntimeError("Call reset() before step().")

        previous_state = self._state
        # Freeze all market inputs before the random-walk transition. Reward and
        # cost accounting for this action must not use post-decision information.
        self._decision_fuel_price = self._raw_fuel_price
        self._decision_price_ma30 = self.raw_price_ma30
        self._decision_fx_rate = self._raw_fx_rate

        self._step_count += 1
        next_state, actual_bunker_amount = self._transition(previous_state, action)
        # Synthetic index on a normalized tank basis, not an actual USD or KRW cost.
        step_cost_index = (
            actual_bunker_amount
            * self._decision_fuel_price
            * self._decision_fx_rate
        )
        self._cumulative_cost_index += step_cost_index
        reward, reward_breakdown = self._compute_reward(
            previous_state,
            action,
            next_state,
            decision_fuel_price=self._decision_fuel_price,
            decision_price_ma30=self._decision_price_ma30,
            actual_bunker_amount=actual_bunker_amount,
        )
        self._state = next_state

        terminated = False
        truncated = False
        end_reason = ""

        # Failure takes precedence if fuel depletion and arrival occur together.
        if self._fuel_remaining <= 0.0:
            terminated = True
            end_reason = "fuel_depleted"
        elif self._route_remaining <= 1e-6:
            terminated = True
            end_reason = "arrived"
        elif self._step_count >= self.max_steps:
            truncated = True
            end_reason = "timeout"

        info = {
            "reward_breakdown": reward_breakdown,
            "end_reason": end_reason,
            "voyage_success": end_reason == "arrived",
            "decision_fuel_price": self._decision_fuel_price,
            "decision_price_ma30": self._decision_price_ma30,
            "decision_fx_rate": self._decision_fx_rate,
            "actual_bunker_amount": actual_bunker_amount,
            "step_cost_index": step_cost_index,
            "cumulative_cost_index": self._cumulative_cost_index,
        }
        return self._state, reward, terminated, truncated, info

    def _init_state(self) -> np.ndarray:
        """Start one synthetic voyage and return its normalized observation."""
        self._raw_fuel_price = float(
            np.clip(
                self.np_random.normal(self._FUEL_PRICE_MEAN, 50.0), *self._PRICE_RANGE
            )
        )
        self._raw_fx_rate = float(
            np.clip(self.np_random.normal(self._FX_RATE_MEAN, 30.0), *self._FX_RANGE)
        )
        self._fuel_remaining = 1.0
        self._route_remaining = 1.0
        self._price_history = deque([self._raw_fuel_price], maxlen=30)
        return self._observation()

    def _transition(self, state: np.ndarray, action: int) -> tuple[np.ndarray, float]:
        """Advance one step and return the observation and actual bunker amount."""
        del state  # Raw simulation state is retained to avoid evolving normalized values.
        self._raw_fuel_price = float(
            np.clip(
                self._raw_fuel_price * (1.0 + self.np_random.normal(0.0, 0.01)),
                *self._PRICE_RANGE,
            )
        )
        self._price_history.append(self._raw_fuel_price)
        self._raw_fx_rate = float(
            np.clip(
                self._raw_fx_rate * (1.0 + self.np_random.normal(0.0, 0.003)),
                *self._FX_RANGE,
            )
        )

        fuel_before_refill = max(
            0.0, self._fuel_remaining - self._FUEL_CONSUMPTION_PER_STEP
        )
        requested_bunker_amount = self._BUNKER_REFILL_AMOUNT if action != 0 else 0.0
        available_capacity = max(
            0.0, self._MAX_REFILLED_FUEL - fuel_before_refill
        )
        actual_bunker_amount = max(
            0.0, min(requested_bunker_amount, available_capacity)
        )
        self._fuel_remaining = min(
            self._MAX_REFILLED_FUEL,
            fuel_before_refill + actual_bunker_amount,
        )
        self._route_remaining = max(0.0, self._route_remaining - 1.0 / self.max_steps)
        return self._observation(), actual_bunker_amount

    def _compute_reward(
        self,
        state: np.ndarray,
        action: int,
        next_state: np.ndarray,
        *,
        decision_fuel_price: float,
        decision_price_ma30: float,
        actual_bunker_amount: float,
    ) -> tuple[float, dict[str, float]]:
        """Calculate the four STEP 02 reward components."""
        del next_state

        # Price advantage proxy, not actual cost saving. Rule-based cost savings
        # require episode-level comparison and are deferred to the evaluation step.
        fuel_cost_saving = (
            max(
                0.0,
                (decision_price_ma30 - decision_fuel_price)
                / decision_price_ma30,
            )
            if (
                action != 0
                and actual_bunker_amount > self._BUNKER_AMOUNT_EPSILON
                and decision_price_ma30 > 0.0
            )
            else 0.0
        )
        risk_penalty = 1.0 if self._fuel_remaining < self.min_safe_fuel else 0.0

        fuel_before_action = float(state[3])
        operational_efficiency = -0.1 if action != 0 and fuel_before_action > 0.8 else 0.0

        # TODO: IMO 규제 로직은 STEP 03 이후 범위
        imo_compliance_bonus = 0.0

        breakdown = {
            "fuel_cost_saving": fuel_cost_saving,
            "risk_penalty": risk_penalty,
            "operational_efficiency": operational_efficiency,
            "imo_compliance_bonus": imo_compliance_bonus,
        }
        reward = (
            REWARD_WEIGHTS["fuel_cost_saving"] * fuel_cost_saving
            - REWARD_WEIGHTS["risk_penalty"] * risk_penalty
            + REWARD_WEIGHTS["operational_efficiency"] * operational_efficiency
            + REWARD_WEIGHTS["imo_compliance_bonus"] * imo_compliance_bonus
        )
        return float(reward), breakdown

    def _observation(self) -> np.ndarray:
        """Normalize raw market values and clip every feature to [-1, 1]."""
        price_ma30 = float(np.mean(self._price_history))
        values = np.array(
            [
                (self._raw_fuel_price - self._FUEL_PRICE_MEAN) / self._FUEL_PRICE_SCALE,
                (price_ma30 - self._FUEL_PRICE_MEAN) / self._FUEL_PRICE_SCALE,
                (self._raw_fx_rate - self._FX_RATE_MEAN) / self._FX_RATE_SCALE,
                self._fuel_remaining,
                self._route_remaining,
                self._SFC,
            ],
            dtype=np.float32,
        )
        return np.clip(values, -1.0, 1.0).astype(np.float32)

    @property
    def raw_fuel_price(self) -> float:
        """Current unnormalized synthetic fuel price (USD/ton)."""
        return self._raw_fuel_price

    @property
    def raw_price_ma30(self) -> float:
        """Current unnormalized fuel-price moving average over up to 30 steps."""
        return float(np.mean(self._price_history))

    def render(self):
        print(f"step={self._step_count} state={self._state}")


if __name__ == "__main__":
    env = BunkeringEnv()
    observation, info = env.reset(seed=42)
    print("initial obs:", observation, info)
    for _ in range(5):
        observation, reward, terminated, truncated, info = env.step(env.action_space.sample())
        print(
            f"reward={reward:.4f} obs={observation} "
            f"done={terminated or truncated}"
        )
        if terminated or truncated:
            break
