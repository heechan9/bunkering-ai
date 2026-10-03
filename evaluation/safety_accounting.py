"""Additive audit of legacy trajectories; does not alter actions or termination."""
from dataclasses import dataclass

@dataclass
class VoyageAudit:
    initial_fuel: float
    initial_unit_value: float
    reserve: float
    tolerance: float = 1e-9
    minimum_pre_refill: float = float("inf")
    shortage_steps: int = 0
    reserve_violation_steps: int = 0

    def observe(self, fuel: float, consumption: float) -> None:
        remaining = fuel - consumption  # Deliberately before clipping and refill.
        self.minimum_pre_refill = min(self.minimum_pre_refill, remaining)
        self.shortage_steps += int(remaining < -self.tolerance)
        self.reserve_violation_steps += int(remaining < self.reserve - self.tolerance)

    def finish(self, arrived: bool, purchase: float, final_fuel: float, terminal_unit_value: float) -> dict:
        feasible = arrived and self.shortage_steps == 0
        safe = feasible and self.reserve_violation_steps == 0
        adjusted = purchase + self.initial_fuel * self.initial_unit_value - final_fuel * terminal_unit_value
        return {
            "legacy_arrived": arrived,
            "arrived_without_pre_refill_shortage": feasible,
            "safe_arrival": safe,
            "pre_refill_shortage_steps": self.shortage_steps,
            "pre_refill_reserve_violation_steps": self.reserve_violation_steps,
            "minimum_pre_refill_fuel": self.minimum_pre_refill,
            "purchase_sci": purchase,
            "initial_inventory_value": self.initial_fuel * self.initial_unit_value,
            "terminal_inventory_value": final_fuel * terminal_unit_value,
            "final_fuel": final_fuel,
            "inventory_adjusted_sci": adjusted,
            "safe_arrival_adjusted_sci": adjusted if safe else None,
        }
