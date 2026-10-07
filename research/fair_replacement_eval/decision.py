"""Apply the pre-registered criteria to episode records. Pure functions, no I/O."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .common import allowed_stops, classify_deadline, min_safe_stops, voyage_hours

Rows = Sequence[Mapping[str, Any]]


def _arr(rows: Rows, key: str) -> np.ndarray:
    return np.asarray([float(r[key]) for r in rows], dtype=float)


def _check_paired(a: Rows, b: Rows) -> None:
    if [r["seed"] for r in a] != [r["seed"] for r in b]:
        raise ValueError("paired comparison requires identical seed order")


def _rng(crit: Mapping[str, Any], salt: str) -> np.random.Generator:
    base = int(crit["statistics"]["bootstrap_rng_seed"])
    return np.random.default_rng([base, *[ord(ch) for ch in salt]])


def rate_diff(
    a: np.ndarray, b: np.ndarray, rng: np.random.Generator, resamples: int, pct: Sequence[float]
) -> dict[str, float]:
    """Paired bootstrap of mean(a) - mean(b) (binary or continuous)."""
    n = len(a)
    idx = rng.integers(0, n, size=(resamples, n))
    diffs = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    return {
        "a": float(a.mean()),
        "b": float(b.mean()),
        "diff": float(a.mean() - b.mean()),
        "lo": float(np.percentile(diffs, pct[0])),
        "hi": float(np.percentile(diffs, pct[1])),
    }


def relative_cost_diff(
    a_cost: np.ndarray,
    b_cost: np.ndarray,
    joint: np.ndarray,
    rng: np.random.Generator,
    resamples: int,
    pct: Sequence[float],
) -> dict[str, Any]:
    """Paired bootstrap of mean(a-b)/mean(b) over joint-safe episodes."""
    n_joint = int(joint.sum())
    if n_joint == 0:
        return {"n_joint_safe": 0, "rel_diff": None, "lo": None, "hi": None}
    a, b = a_cost[joint], b_cost[joint]
    idx = rng.integers(0, n_joint, size=(resamples, n_joint))
    rel = (a[idx].mean(axis=1) - b[idx].mean(axis=1)) / b[idx].mean(axis=1)
    return {
        "n_joint_safe": n_joint,
        "rel_diff": float((a.mean() - b.mean()) / b.mean()),
        "lo": float(np.percentile(rel, pct[0])),
        "hi": float(np.percentile(rel, pct[1])),
    }


def policy_summary(rows: Rows) -> dict[str, Any]:
    safe = _arr(rows, "safe").astype(bool)
    adjusted = _arr(rows, "adjusted_sci")
    return {
        "episodes": len(rows),
        "safe_rate": float(safe.mean()),
        "safe_count": int(safe.sum()),
        "depleted_count": int(_arr(rows, "depleted").sum()),
        "arrived_rate": float(_arr(rows, "arrived").mean()),
        "mean_stops": float(_arr(rows, "stops").mean()),
        "max_stops": int(_arr(rows, "stops").max()),
        "mean_adjusted_sci_safe": float(adjusted[safe].mean()) if safe.any() else None,
        "mean_raw_cost_index": float(_arr(rows, "cost_index").mean()),
    }


def time_table(
    rows_by_policy: Mapping[str, Rows], consumption: float, legs: int, reserve: float, crit: Mapping[str, Any]
) -> dict[str, Any]:
    """Deadline classes (per scenario) and on-time-safe rates (attainable only)."""
    overlay = crit["time_overlay"]
    leg_h, stop_h = float(overlay["leg_hours"]), float(overlay["stop_hours"])
    needed = min_safe_stops(consumption, legs, reserve)
    table: dict[str, Any] = {"min_safe_stops": needed, "deadlines": {}}
    for label, deadline in overlay["deadlines_hours"].items():
        cls = classify_deadline(deadline, legs, leg_h, stop_h, needed)
        entry: dict[str, Any] = {
            "deadline_hours": deadline,
            "class": cls,
            "sailing_hours": legs * leg_h,
            "allowed_stops": allowed_stops(deadline, legs, leg_h, stop_h),
            "policies": {},
        }
        for name, rows in rows_by_policy.items():
            hours = np.asarray([voyage_hours(legs, int(r["stops"]), leg_h, stop_h) for r in rows])
            safe = _arr(rows, "safe").astype(bool)
            entry["policies"][name] = {
                "episodes": len(rows),
                "on_time_safe_rate": (
                    float((safe & (hours <= deadline + 1e-9)).mean()) if cls == "attainable" else None
                ),
                "excluded_from_compliance": cls != "attainable",
                "safe_but_late_rate": float((safe & (hours > deadline + 1e-9)).mean()),
            }
        table["deadlines"][label] = entry
    return table


def compare(
    cand: Rows, inc: Rows, crit: Mapping[str, Any], salt: str
) -> dict[str, Any]:
    """Safety, cost and ``on-time`` pieces of candidate vs incumbent on one scenario."""
    _check_paired(cand, inc)
    res = int(crit["statistics"]["paired_bootstrap_resamples"])
    pct = crit["thresholds"]["ci_percentiles"]
    rng = _rng(crit, salt)
    cs, is_ = _arr(cand, "safe"), _arr(inc, "safe")
    out: dict[str, Any] = {"safety": rate_diff(cs, is_, rng, res, pct)}
    joint = (cs > 0) & (is_ > 0)
    out["cost"] = relative_cost_diff(_arr(cand, "adjusted_sci"), _arr(inc, "adjusted_sci"), joint, rng, res, pct)
    out["cost"]["joint_safe_share"] = float(joint.mean())
    out["candidate_depleted"] = int(_arr(cand, "depleted").sum())
    return out


def evaluate_criteria(
    confirmation: Mapping[str, Mapping[str, Rows]],
    runtime: Mapping[str, Mapping[str, float]],
    gates: Mapping[str, bool],
    incumbent_is_official: bool,
    crit: Mapping[str, Any],
    legs: int,
    reserve: float,
    candidate: str = "planner_ops",
    incumbent: str = "double_dqn",
) -> dict[str, Any]:
    """Return per-criterion results and the verdict. Uses only confirmation-set data.

    Every numeric threshold comes from ``crit["thresholds"]`` (criteria.json)."""
    th = crit["thresholds"]
    pct = th["ci_percentiles"]
    res = int(crit["statistics"]["paired_bootstrap_resamples"])
    scenarios = crit["env_scenarios"]
    out: dict[str, Any] = {"criteria": {}, "gates": dict(gates)}

    nominal = confirmation["nominal"]
    cmp_nom = compare(nominal[candidate], nominal[incumbent], crit, "nominal")
    out["nominal_comparison"] = cmp_nom

    r1 = (
        cmp_nom["safety"]["lo"] >= th["safety_lower_bound"]
        and cmp_nom["candidate_depleted"] <= th["candidate_max_depleted"]
    )
    out["criteria"]["R1_safety"] = {"pass": bool(r1), "lower_bound": cmp_nom["safety"]["lo"], "candidate_depleted": cmp_nom["candidate_depleted"]}

    cost = cmp_nom["cost"]
    r2 = (
        cost["rel_diff"] is not None
        and cost["joint_safe_share"] >= th["min_joint_safe_share"]
        and cost["hi"] <= th["cost_upper_bound"]
    )
    out["criteria"]["R2_cost"] = {
        "pass": bool(r2),
        "rel_diff": cost["rel_diff"],
        "hi": cost["hi"],
        "joint_safe_share": cost["joint_safe_share"],
        "label": None if not r2 else ("cost_superior" if cost["hi"] < 0 else "non_inferior_only"),
    }

    # R3: time compliance, nominal scenario, attainable deadlines only.
    consumption = float(scenarios["nominal"]["fuel_consumption_per_step"])
    tt = time_table({candidate: nominal[candidate], incumbent: nominal[incumbent]}, consumption, legs, reserve, crit)
    leg_h = float(crit["time_overlay"]["leg_hours"])
    stop_h = float(crit["time_overlay"]["stop_hours"])
    per_deadline: dict[str, Any] = {}
    r3 = True
    attainable = 0
    rng = _rng(crit, "time")
    for label, entry in tt["deadlines"].items():
        if entry["class"] != "attainable":
            per_deadline[label] = {"class": entry["class"], "judged": False}
            continue
        attainable += 1
        ok = {}
        for name in (candidate, incumbent):
            rows = nominal[name]
            hours = np.asarray([voyage_hours(legs, int(r["stops"]), leg_h, stop_h) for r in rows])
            ok[name] = (_arr(rows, "safe") > 0) & (hours <= entry["deadline_hours"] + 1e-9)
        d = rate_diff(ok[candidate].astype(float), ok[incumbent].astype(float), rng, res, pct)
        passed = d["lo"] >= th["time_lower_bound"]
        r3 = r3 and passed
        per_deadline[label] = {"class": "attainable", "judged": True, "pass": bool(passed), **d}
    r3 = r3 and attainable >= 1
    out["criteria"]["R3_time"] = {"pass": bool(r3), "per_deadline": per_deadline, "time_table": tt}

    # R4: runtime.
    p99_ms = runtime[candidate]["p99_ms"]
    out["criteria"]["R4_runtime"] = {
        "pass": bool(p99_ms <= th["runtime_p99_ms"]),
        "candidate_p99_ms": p99_ms,
        "incumbent_p99_ms": runtime[incumbent]["p99_ms"],
        "note": "hardware dependent; incumbent ratio informational",
    }

    # R5: demand robustness (required scenarios only), plus report-only ones.
    r5 = True
    r5_detail: dict[str, Any] = {}
    for name, spec in scenarios.items():
        if name in ("nominal", "note"):
            continue
        cmp_s = compare(confirmation[name][candidate], confirmation[name][incumbent], crit, name)
        required = spec["decision_use"] == "required"
        passed = cmp_s["safety"]["lo"] >= th["demand_safety_lower_bound"]
        if required:
            r5 = r5 and passed
        r5_detail[name] = {"required": required, "pass": bool(passed), "comparison": cmp_s,
                           "time_classes": time_table({candidate: confirmation[name][candidate], incumbent: confirmation[name][incumbent]},
                                                      float(spec["fuel_consumption_per_step"]), legs, reserve, crit)}
    out["criteria"]["R5_demand_robustness"] = {"pass": bool(r5), "scenarios": r5_detail}

    all_pass = all(out["criteria"][k]["pass"] for k in ("R1_safety", "R2_cost", "R3_time", "R4_runtime", "R5_demand_robustness"))
    gate_other = all(v for k, v in gates.items() if not k.startswith("G1"))
    if not gates.get("G1_official_incumbent", False) or not incumbent_is_official:
        verdict = "SYNTHETIC_VALIDATION_ONLY"
    elif not gate_other:
        verdict = "NOT_DECIDABLE"
    else:
        verdict = "REPLACEMENT_EVIDENCE_SUFFICIENT" if all_pass else "REPLACEMENT_EVIDENCE_INSUFFICIENT"
    out["verdict"] = verdict
    out["would_pass_all_if_official"] = bool(all_pass and gate_other)
    return out


def forecast_sensitivity(
    nominal: Mapping[str, Rows], sigma_grid: Sequence[float], crit: Mapping[str, Any], base: str = "planner_ops"
) -> dict[str, Any]:
    """Value of information: cost advantage of forecast planners over planner_ops.

    These planners see information the operational DQN never sees; they are NOT
    replacement candidates. sigma* is the smallest grid sigma whose paired 95%
    interval no longer excludes zero advantage (hi >= 0).
    """
    res = int(crit["statistics"]["paired_bootstrap_resamples"])
    pct = crit["thresholds"]["ci_percentiles"]
    table: dict[str, Any] = {}
    sigma_star = None
    for sigma in sigma_grid:
        name = "planner_oracle" if sigma == 0 else f"planner_fcst_{sigma:g}"
        if name not in nominal:
            continue
        a, b = nominal[name], nominal[base]
        _check_paired(a, b)
        rng = _rng(crit, "voi" + name)
        joint = (_arr(a, "safe") > 0) & (_arr(b, "safe") > 0)
        entry = relative_cost_diff(_arr(a, "adjusted_sci"), _arr(b, "adjusted_sci"), joint, rng, res, pct)
        entry["mean_stops"] = float(_arr(a, "stops").mean())
        entry["safe_rate"] = float(_arr(a, "safe").mean())
        table[name] = entry
        if sigma_star is None and entry["hi"] is not None and entry["hi"] >= 0:
            sigma_star = sigma
    return {"vs": base, "sigma_star_first_grid_sigma_without_significant_saving": sigma_star, "table": table}
