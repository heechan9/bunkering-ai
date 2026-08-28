"""Policy-independent evaluation records, aggregation, and fairness checks.

This module deliberately performs no environment runs and writes no files.  Callers
must supply observations produced by their own rule-based or learned policy runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import fmean, pstdev
from typing import Any, Iterable, Mapping

TERMINATION_REASONS = frozenset({"arrived", "fuel_depleted", "timeout"})
CSV_FIELDS = (
    "seed",
    "episode",
    "policy",
    "reward",
    "Synthetic Cost Index",
    "success",
    "fuel_depletion",
    "bunkering_count",
    "termination_reason",
)


def _require_plain_int(name: str, value: int, *, minimum: int = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")


def _require_finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")


@dataclass(frozen=True)
class EpisodeResult:
    """The canonical result of one completed policy episode."""

    seed: int
    episode: int
    policy: str
    reward: float
    synthetic_cost_index: float
    success: bool
    fuel_depletion: bool
    bunkering_count: int
    termination_reason: str

    def __post_init__(self) -> None:
        _require_plain_int("seed", self.seed)
        _require_plain_int("episode", self.episode)
        if not isinstance(self.policy, str) or not self.policy.strip():
            raise ValueError("policy must be a non-empty string")
        _require_finite("reward", self.reward)
        _require_finite("synthetic_cost_index", self.synthetic_cost_index)
        if self.synthetic_cost_index < 0:
            raise ValueError("synthetic_cost_index must be nonnegative")
        if type(self.success) is not bool or type(self.fuel_depletion) is not bool:
            raise ValueError("success and fuel_depletion must be booleans")
        _require_plain_int("bunkering_count", self.bunkering_count)
        if self.termination_reason not in TERMINATION_REASONS:
            raise ValueError(
                "termination_reason must be one of "
                f"{sorted(TERMINATION_REASONS)}"
            )
        if self.success != (self.termination_reason == "arrived"):
            raise ValueError("success must be true exactly when termination_reason is arrived")
        if self.fuel_depletion != (self.termination_reason == "fuel_depleted"):
            raise ValueError(
                "fuel_depletion must be true exactly when termination_reason is fuel_depleted"
            )

    def to_row(self) -> dict[str, int | str | float | bool]:
        """Return a stable, human-facing row suitable for a caller-owned CSV."""
        return {
            "seed": self.seed,
            "episode": self.episode,
            "policy": self.policy,
            "reward": float(self.reward),
            "Synthetic Cost Index": float(self.synthetic_cost_index),
            "success": self.success,
            "fuel_depletion": self.fuel_depletion,
            "bunkering_count": self.bunkering_count,
            "termination_reason": self.termination_reason,
        }


@dataclass(frozen=True)
class EvaluationCase:
    """One planned run, including the environment settings used for fairness."""

    seed: int
    episode: int
    policy: str
    env_config: Mapping[str, Any]

    def __post_init__(self) -> None:
        _require_plain_int("seed", self.seed)
        _require_plain_int("episode", self.episode)
        if not isinstance(self.policy, str) or not self.policy.strip():
            raise ValueError("policy must be a non-empty string")
        if not isinstance(self.env_config, Mapping):
            raise ValueError("env_config must be a mapping")


def _freeze_config(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze_config(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_config(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze_config(item) for item in value))
    return value


def validate_fair_evaluation_plan(
    cases: Iterable[EvaluationCase], expected_policies: Iterable[str]
) -> None:
    """Reject a plan unless every policy has identical episode/seed/config cases."""
    case_list = list(cases)
    policies = tuple(expected_policies)
    if not case_list:
        raise ValueError("evaluation plan must contain at least one case")
    if not policies or len(set(policies)) != len(policies) or any(not p for p in policies):
        raise ValueError("expected_policies must contain unique non-empty names")

    actual_policies = {case.policy for case in case_list}
    if actual_policies != set(policies):
        raise ValueError("evaluation plan policies do not match expected_policies")

    signatures_by_policy: dict[str, set[tuple[Any, ...]]] = {p: set() for p in policies}
    for case in case_list:
        signature = (case.episode, case.seed, _freeze_config(case.env_config))
        signatures = signatures_by_policy[case.policy]
        if signature in signatures:
            raise ValueError(f"duplicate evaluation case for policy {case.policy!r}")
        signatures.add(signature)

    reference = signatures_by_policy[policies[0]]
    if any(signatures != reference for signatures in signatures_by_policy.values()):
        raise ValueError("all policies must use identical episode, seed, and env_config cases")


@dataclass(frozen=True)
class AggregateResult:
    """Population statistics for completed episodes of one policy."""

    policy: str
    episodes: int
    reward_mean: float
    reward_std: float
    synthetic_cost_index_mean: float
    synthetic_cost_index_std: float
    success_mean: float
    success_std: float
    fuel_depletion_mean: float
    fuel_depletion_std: float
    bunkering_count_mean: float
    bunkering_count_std: float


def aggregate_results(results: Iterable[EpisodeResult]) -> list[AggregateResult]:
    """Calculate per-policy population mean/std from supplied results only."""
    grouped: dict[str, list[EpisodeResult]] = {}
    for result in results:
        if not isinstance(result, EpisodeResult):
            raise TypeError("results must contain only EpisodeResult instances")
        grouped.setdefault(result.policy, []).append(result)
    if not grouped:
        raise ValueError("cannot aggregate an empty result collection")

    aggregates: list[AggregateResult] = []
    for policy, records in sorted(grouped.items()):
        metric_values = {
            "reward": [float(record.reward) for record in records],
            "synthetic_cost_index": [float(record.synthetic_cost_index) for record in records],
            "success": [float(record.success) for record in records],
            "fuel_depletion": [float(record.fuel_depletion) for record in records],
            "bunkering_count": [float(record.bunkering_count) for record in records],
        }
        values: dict[str, float | str | int] = {"policy": policy, "episodes": len(records)}
        for name, samples in metric_values.items():
            values[f"{name}_mean"] = fmean(samples)
            values[f"{name}_std"] = pstdev(samples)
        aggregates.append(AggregateResult(**values))
    return aggregates
