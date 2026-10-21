"""Candidate comparison policy. Separate name; the legacy safe_stock is untouched.

Status: pending C01 (reserve before refill) acceptance by 희찬. Not used for any
confirmed result and never run on the already-used 91,000,000 set as new evidence.
"""
import numpy as np

FUEL_INDEX = 3  # envs.bunkering_env.STATE_VARS position of fuel_remaining


class SafeStockPreRefillV1:
    """Bunker when observed fuel <= reserve + consumption, so that fuel - consumption >= reserve.

    Boundary/dtype spec: the threshold is computed in float64 (0.15 + 0.05 == 0.2)
    and then cast to the observation dtype (float32), the same rounding the
    observation went through, exactly as SafeStockStrategy does for its threshold.
    A state already below reserve + consumption still violates the reserve on this
    step; refilling afterwards does not erase that audit record.
    """

    name = "safe_stock_pre_refill_v1"
    version = "v1-candidate-pending-C01"

    def threshold(self, env, observation):
        return np.asarray(env.min_safe_fuel + env.fuel_consumption_per_step, dtype=observation.dtype)

    def select_action(self, env, observation, step_index):
        del step_index
        return 1 if observation[FUEL_INDEX] <= self.threshold(env, observation) else 0
