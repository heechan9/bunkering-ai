"""Deterministic route-stress scenarios kept outside the canonical RL state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RouteStressScenario:
    """A versioned scenario input, not a claim about route closure or cost."""

    scenario_id: str
    chokepoint_id: str
    transit_baseline_ratio: float
    disruption_level: str
    route_available: bool = True
    detour_distance_nm: float | None = None
    detour_duration_hours: float | None = None
    estimated_extra_fuel: float | None = None
    evidence_scope: str = "scenario_fixture"

    def __post_init__(self) -> None:
        if self.transit_baseline_ratio < 0:
            raise ValueError("transit_baseline_ratio must be non-negative")
        if self.disruption_level not in {"normal", "moderate", "severe"}:
            raise ValueError("unsupported disruption_level")
        derived = (
            self.detour_distance_nm,
            self.detour_duration_hours,
            self.estimated_extra_fuel,
        )
        if any(value is not None and value < 0 for value in derived):
            raise ValueError("detour and fuel assumptions must be non-negative")


SCENARIOS = {
    "normal": RouteStressScenario(
        scenario_id="normal",
        chokepoint_id="none",
        transit_baseline_ratio=1.0,
        disruption_level="normal",
    ),
    "suez_contraction": RouteStressScenario(
        scenario_id="suez_contraction",
        chokepoint_id="suez_canal",
        transit_baseline_ratio=0.34,
        disruption_level="severe",
    ),
    "hormuz_contraction": RouteStressScenario(
        scenario_id="hormuz_contraction",
        chokepoint_id="strait_of_hormuz",
        transit_baseline_ratio=0.77,
        disruption_level="moderate",
    ),
    "cape_detour_assumption": RouteStressScenario(
        scenario_id="cape_detour_assumption",
        chokepoint_id="cape_of_good_hope",
        transit_baseline_ratio=2.0,
        disruption_level="moderate",
    ),
}


class RouteStressAdapter:
    """Expose immutable scenario metadata without changing state or reward."""

    def get(self, scenario_id: str) -> RouteStressScenario:
        try:
            return SCENARIOS[scenario_id]
        except KeyError as exc:
            raise ValueError(f"unknown route-stress scenario: {scenario_id}") from exc

    def episode_metadata(self, scenario_id: str) -> dict[str, Any]:
        return asdict(self.get(scenario_id))
