"""Explicit, versioned assumptions translating route evidence to env settings."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass


SCA_ROUTE_SOURCE = (
    "https://www.suezcanal.gov.eg/English/About/Pages/WhySuezCanal.aspx"
)


@dataclass(frozen=True)
class RouteImpactAssumption:
    assumption_id: str
    scenario_id: str
    baseline_distance_nm: int
    scenario_distance_nm: int
    baseline_max_steps: int = 30
    source_url: str | None = None
    operational_effect: bool = True
    scope: str = "synthetic representative-route assumption"

    def __post_init__(self) -> None:
        if min(
            self.baseline_distance_nm,
            self.scenario_distance_nm,
            self.baseline_max_steps,
        ) <= 0:
            raise ValueError("distances and baseline_max_steps must be positive")
        if not self.operational_effect and (
            self.scenario_distance_nm != self.baseline_distance_nm
        ):
            raise ValueError("observation-only scenarios cannot change route distance")

    @property
    def distance_multiplier(self) -> float:
        return self.scenario_distance_nm / self.baseline_distance_nm

    @property
    def extra_distance_nm(self) -> int:
        return self.scenario_distance_nm - self.baseline_distance_nm

    @property
    def scenario_max_steps(self) -> int:
        return math.ceil(self.baseline_max_steps * self.distance_multiplier)

    def env_config(self) -> dict[str, int | float]:
        return {
            "n_ports": 3,
            "max_steps": self.scenario_max_steps,
            "min_safe_fuel": 0.15,
        }

    def to_manifest(self) -> dict:
        return {
            **asdict(self),
            "distance_multiplier": self.distance_multiplier,
            "extra_distance_nm": self.extra_distance_nm,
            "scenario_max_steps": self.scenario_max_steps,
            "claim_boundary": (
                "Synthetic environment scaling only; not measured voyage duration, "
                "fuel consumption, cost, or realized diversion."
            ),
        }


ASSUMPTIONS = {
    "normal": RouteImpactAssumption(
        assumption_id="normal_30_step_reference",
        scenario_id="normal",
        baseline_distance_nm=8288,
        scenario_distance_nm=8288,
        source_url=SCA_ROUTE_SOURCE,
    ),
    "suez_cape_representative": RouteImpactAssumption(
        assumption_id="sca_singapore_rotterdam_cape_distance_v1",
        scenario_id="suez_cape_representative",
        baseline_distance_nm=8288,
        scenario_distance_nm=11755,
        source_url=SCA_ROUTE_SOURCE,
    ),
    "hormuz_observation_only": RouteImpactAssumption(
        assumption_id="hormuz_no_fabricated_sea_detour_v1",
        scenario_id="hormuz_observation_only",
        baseline_distance_nm=8288,
        scenario_distance_nm=8288,
        source_url=None,
        operational_effect=False,
        scope="traffic observation only; no assumed equivalent sea bypass",
    ),
}


def get_route_impact(scenario_id: str) -> RouteImpactAssumption:
    try:
        return ASSUMPTIONS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"unknown route-impact scenario: {scenario_id}") from exc
