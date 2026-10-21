"""Episode ledger, step-level accounting audit and paired summary for native results.

The full legacy audit stays in the evaluation bundle (independent_audit/check.py).
This module adds what that script does not provide: arbitrary input paths, the
first failing row instead of a bare assert, and paired_summary.csv with explicit
denominators, null for empty subsets and "not estimable" for n=1 intervals.
"""
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

from config import native

EPISODE_COLUMNS = ["seed", "policy", "steps", "end_reason", "legacy_arrived", "safe_arrival",
                   "pre_refill_shortage_steps", "pre_refill_reserve_violation_steps", "purchase_sci",
                   "initial_inventory_value", "terminal_inventory_value", "final_fuel",
                   "inventory_adjusted_sci"]
STEP_COLUMNS = ["seed", "policy", "step", "action", "fuel_before", "pre_refill_unclipped",
                "decision_price", "decision_fx", "purchase", "fuel_after", "step_sci"]
METRICS = ["purchase_sci", "inventory_adjusted_sci"]
FUEL_TOL = 1e-12
SCI_TOL = 1e-7


class InputError(ValueError):
    pass


def expected_transition(fuel, action, cfg):
    """Contract formula: u=f-c, b=max(0,u), q=max(0,min(0.9*1[a>0],0.95-b)), f'=min(0.95,b+q)."""
    c, cap = native(cfg, "consumption_per_step"), native(cfg, "max_fill")
    u = fuel - c
    b = max(0.0, u)
    q = max(0.0, min(native(cfg, "refill_request") if action > 0 else 0.0, cap - b))
    return u, b, q, min(cap, b + q)


def _bool(value, where):
    if value not in ("True", "False"):
        raise InputError(f"{where}: expected True/False, got {value!r}")
    return value == "True"


def _read(path, columns):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{path}: missing columns {missing}")
        return list(reader)


def _episode_number(row, name, convert, where):
    """Report malformed CSV numbers through the documented input-error path."""
    try:
        return convert(row[name])
    except (ValueError, TypeError, OverflowError) as exc:
        raise InputError(f"{where}.{name}: invalid numeric value {row[name]!r}") from exc


def load_episodes(path, cfg):
    rows = _read(path, EPISODE_COLUMNS)
    if not rows:
        raise InputError(f"{path}: no episodes")
    cap, tol = native(cfg, "max_fill"), native(cfg, "tolerance")
    episodes = {}
    for i, r in enumerate(rows, start=2):
        where = f"{path}:line {i}"
        key = (r["policy"], _episode_number(r, "seed", int, where))
        if key in episodes:
            raise InputError(f"{where}: duplicate policy/seed {key}")
        e = {k: r[k] for k in r}
        e["seed"] = key[1]
        e["steps"] = _episode_number(r, "steps", int, where)
        for k in ["legacy_arrived", "safe_arrival"]:
            e[k] = _bool(r[k], f"{where}.{k}")
        for k in ["pre_refill_shortage_steps", "pre_refill_reserve_violation_steps"]:
            e[k] = _episode_number(r, k, int, where)
            if e[k] < 0:
                raise InputError(f"{where}.{k}: negative count")
        for k in ["purchase_sci", "initial_inventory_value", "terminal_inventory_value",
                  "final_fuel", "inventory_adjusted_sci"]:
            e[k] = _episode_number(r, k, float, where)
            if not math.isfinite(e[k]):
                raise InputError(f"{where}.{k}: not finite")
        if not -tol <= e["final_fuel"] <= cap + tol:
            raise InputError(f"{where}.final_fuel: {e['final_fuel']} outside [0, {cap}] tank fraction")
        episodes[key] = e
    seeds = defaultdict(set)
    for policy, seed in episodes:
        seeds[policy].add(seed)
    reference = next(iter(seeds.values()))
    for policy, s in seeds.items():
        if s != reference:
            raise InputError(f"{path}: policy {policy} seed set differs; pairing requires identical seeds")
    return episodes


def audit_steps(path, episodes, cfg):
    """Recompute every step from the contract formula; return per-episode totals and mismatches."""
    rows = _read(path, STEP_COLUMNS)
    tol, reserve = native(cfg, "tolerance"), native(cfg, "reserve")
    traces = defaultdict(list)
    for r in rows:
        for name in STEP_COLUMNS:
            if name == "policy":
                continue
            try:
                value = float(r[name])
                if not math.isfinite(value):
                    raise ValueError("non-finite")
                if name in {"seed", "step", "action"} and value != int(r[name]):
                    raise ValueError("not an integer")
            except (ValueError, TypeError, OverflowError) as exc:
                raise InputError(f"{path}: invalid {name}: {r[name]!r}") from exc
        if not 0 <= int(r["action"]) <= native(cfg, "n_ports"):
            raise InputError(f"{path}: invalid action {r['action']}")
        if not 0 <= float(r["fuel_before"]) <= 1.0 + tol:
            raise InputError(f"{path}: fuel_before outside tank range")
        if float(r["decision_price"]) <= 0 or float(r["decision_fx"]) <= 0:
            raise InputError(f"{path}: price and FX must be positive")
        traces[(r["policy"], int(r["seed"]))].append(r)
    mismatches, totals, market = [], {}, {}

    def bad(check, key, step, expected, actual):
        mismatches.append({"check": check, "policy": key[0], "seed": key[1], "step": step,
                           "expected": expected, "actual": actual})

    if set(traces) != set(episodes):
        missing = sorted(set(episodes) - set(traces))[:3]
        extra = sorted(set(traces) - set(episodes))[:3]
        raise InputError(f"{path}: step traces do not match episodes (missing {missing}, extra {extra})")
    for key, trace in traces.items():
        trace.sort(key=lambda t: int(t["step"]))
        if [int(t["step"]) for t in trace] != list(range(1, len(trace) + 1)):
            raise InputError(f"{path}: {key}: steps must be consecutive from 1")
        prev_after, cost, short, res = None, 0.0, 0, 0
        for t in trace:
            step = int(t["step"])
            f, a = float(t["fuel_before"]), int(t["action"])
            price, fx = float(t["decision_price"]), float(t["decision_fx"])
            u, _, q, f_next = expected_transition(f, a, cfg)
            if prev_after is not None and abs(f - prev_after) > FUEL_TOL:
                bad("fuel_continuity", key, step, prev_after, f)
            if abs(u - float(t["pre_refill_unclipped"])) > FUEL_TOL:
                bad("pre_refill_unclipped", key, step, u, float(t["pre_refill_unclipped"]))
            if abs(q - float(t["purchase"])) > FUEL_TOL:
                bad("purchase_cap", key, step, q, float(t["purchase"]))
            if abs(f_next - float(t["fuel_after"])) > FUEL_TOL:
                bad("fuel_after", key, step, f_next, float(t["fuel_after"]))
            if abs(q * price * fx - float(t["step_sci"])) > SCI_TOL:
                bad("step_sci", key, step, q * price * fx, float(t["step_sci"]))
            if market.setdefault((key[1], step), (price, fx)) != (price, fx):
                bad("market_tape", key, step, market[(key[1], step)], (price, fx))
            if step == 1 and abs(f * price * fx - episodes[key]["initial_inventory_value"]) > SCI_TOL:
                bad("initial_inventory_value", key, step, f * price * fx, episodes[key]["initial_inventory_value"])
            # Shortage/reserve are judged on u, before the zero clip and before refill.
            short += u < -tol
            res += u < reserve - tol
            cost += float(t["step_sci"])
            prev_after = float(t["fuel_after"])
        e = episodes[key]
        if len(trace) != e["steps"]:
            bad("step_count", key, None, e["steps"], len(trace))
        if abs(prev_after - e["final_fuel"]) > FUEL_TOL:
            bad("final_fuel", key, None, prev_after, e["final_fuel"])
        if abs(cost - e["purchase_sci"]) > SCI_TOL:
            bad("purchase_sci_sum", key, None, cost, e["purchase_sci"])
        if short != e["pre_refill_shortage_steps"]:
            bad("shortage_steps", key, None, short, e["pre_refill_shortage_steps"])
        if res != e["pre_refill_reserve_violation_steps"]:
            bad("reserve_violation_steps", key, None, res, e["pre_refill_reserve_violation_steps"])
        totals[key] = {"step_purchase_sci": cost, "step_shortage": short, "step_reserve": res}
    return totals, mismatches, len(rows)


def build_ledger(episodes, contract_version):
    rows, mismatches = [], []
    for (policy, seed), e in sorted(episodes.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        strict = e["legacy_arrived"] and e["pre_refill_shortage_steps"] == 0 and e["pre_refill_reserve_violation_steps"] == 0
        residual = e["purchase_sci"] + e["initial_inventory_value"] - e["terminal_inventory_value"] - e["inventory_adjusted_sci"]
        if strict != e["safe_arrival"]:
            mismatches.append({"check": "strict_safe_arrival", "policy": policy, "seed": seed, "step": None,
                               "expected": strict, "actual": e["safe_arrival"]})
        if abs(residual) > SCI_TOL:
            mismatches.append({"check": "inventory_identity", "policy": policy, "seed": seed, "step": None,
                               "expected": 0.0, "actual": residual})
        rows.append({"contract_version": contract_version, "seed": seed, "policy": policy,
                     "steps": e["steps"], "end_reason": e["end_reason"], "legacy_arrived": e["legacy_arrived"],
                     "strict_safe_arrival": strict,
                     "pre_refill_shortage_steps": e["pre_refill_shortage_steps"],
                     "pre_refill_reserve_violation_steps": e["pre_refill_reserve_violation_steps"],
                     "purchase_sci": e["purchase_sci"], "initial_inventory_value": e["initial_inventory_value"],
                     "terminal_inventory_value": e["terminal_inventory_value"], "final_fuel": e["final_fuel"],
                     "inventory_adjusted_sci": e["inventory_adjusted_sci"], "inventory_identity_residual": residual,
                     "sci_unit": "synthetic_index_not_currency"})
    return rows, mismatches


def describe(values, ddof):
    """Mean and 1.96*sd/sqrt(n) interval. n=0 -> all null; n=1 -> interval not estimable."""
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "sd_ddof0": None, "ci95_low": None, "ci95_high": None,
                "status": "empty_subset_null"}
    mean = math.fsum(values) / n
    ss = math.fsum((v - mean) ** 2 for v in values)
    sd0 = math.sqrt(ss / n)
    if n == 1 or n - ddof <= 0:
        return {"n": n, "mean": mean, "sd": None, "sd_ddof0": sd0, "ci95_low": None, "ci95_high": None,
                "status": "ci_not_estimable_n1"}
    sd = math.sqrt(ss / (n - ddof))
    half = 1.96 * sd / math.sqrt(n)
    return {"n": n, "mean": mean, "sd": sd, "sd_ddof0": sd0, "ci95_low": mean - half, "ci95_high": mean + half,
            "status": "ok"}


def _strict(e):
    return e["legacy_arrived"] and e["pre_refill_shortage_steps"] == 0 and e["pre_refill_reserve_violation_steps"] == 0


def paired_summary(episodes, ddof, contract_version, comparator="double_dqn", legacy=None):
    policies = sorted({p for p, _ in episodes})
    if comparator not in policies:
        raise InputError(f"comparator {comparator} not in episodes")
    seeds = sorted({s for _, s in episodes})
    rows = []
    for base in [p for p in policies if p != comparator]:
        safe = [s for s in seeds if _strict(episodes[comparator, s]) and _strict(episodes[base, s])]
        for subset, ss in [("all", seeds), ("common_strict_safe", safe)]:
            for metric in METRICS:
                d = [episodes[comparator, s][metric] - episodes[base, s][metric] for s in ss]
                st = describe(d, ddof)
                row = {"contract_version": contract_version, "comparator": comparator, "baseline": base,
                       "delta": f"{comparator}_minus_baseline", "metric": metric, "subset": subset,
                       "n_all": len(seeds), "n_common_safe": len(safe), "n_excluded": len(seeds) - len(safe),
                       "n": st["n"], "mean_delta": st["mean"], "sd_delta": st["sd"], "ddof": ddof,
                       "sd_delta_ddof0": st["sd_ddof0"], "ci95_low": st["ci95_low"], "ci95_high": st["ci95_high"],
                       "ci_method": "mean +/- 1.96*sd/sqrt(n), descriptive, not a superiority test",
                       "status": st["status"], "sci_unit": "synthetic_index_not_currency"}
                row.update(_legacy_compare(legacy, base, subset, metric, st))
                rows.append(row)
    return rows


def _legacy_compare(legacy, base, subset, metric, st):
    if legacy is None:
        return {"legacy_mean": None, "legacy_ci95_low": None, "legacy_ci95_high": None, "legacy_match": "not_compared"}
    label = "all" if subset == "all" else "common_safe"
    ref = legacy["paired"][base][f"{label}_{metric}_ddqn_minus_baseline"]
    out = {"legacy_mean": ref["mean"], "legacy_ci95_low": ref["ci95_low"], "legacy_ci95_high": ref["ci95_high"]}
    if ref["n"] != st["n"]:
        out["legacy_match"] = "MISMATCH_n"
    elif st["n"] == 0:
        out["legacy_match"] = "match_null" if ref["mean"] is None else "MISMATCH_expected_null"
    elif abs(ref["mean"] - st["mean"]) > SCI_TOL:
        out["legacy_match"] = "MISMATCH_mean"
    elif st["n"] == 1:
        # Legacy run_evaluation used se=0 for n=1; the v4 tool contract reports the interval as not estimable.
        out["legacy_match"] = "mean_match_ci_contract_differs_n1"
    elif abs(ref["ci95_low"] - st["ci95_low"]) > SCI_TOL or abs(ref["ci95_high"] - st["ci95_high"]) > SCI_TOL:
        out["legacy_match"] = "MISMATCH_ci"
    else:
        out["legacy_match"] = "match"
    return out


def policy_summary(episodes, contract_version):
    rows = []
    for policy in sorted({p for p, _ in episodes}):
        es = [e for (p, _), e in episodes.items() if p == policy]
        n = len(es)
        arrived = [e for e in es if e["legacy_arrived"]]
        strict = [e for e in es if _strict(e)]
        reasons = Counter(e["end_reason"] for e in es)
        rows.append({"contract_version": contract_version, "policy": policy, "episodes": n,
                     "legacy_arrivals": sum(e["legacy_arrived"] for e in es),
                     "strict_safe_arrivals": sum(_strict(e) for e in es),
                     "shortage_episodes": sum(e["pre_refill_shortage_steps"] > 0 for e in es),
                     "reserve_violation_episodes": sum(e["pre_refill_reserve_violation_steps"] > 0 for e in es),
                     "end_reasons": ";".join(f"{k}={v}" for k, v in sorted(reasons.items())),
                     "mean_purchase_sci": math.fsum(e["purchase_sci"] for e in es) / n,
                     "mean_inventory_adjusted_sci": math.fsum(e["inventory_adjusted_sci"] for e in es) / n,
                     "mean_final_fuel": math.fsum(e["final_fuel"] for e in es) / n,
                     "final_fuel_subset": "all_episodes",
                     "final_fuel_n_all": n,
                     "final_fuel_n_legacy_arrived": len(arrived),
                     "final_fuel_n_strict_safe": len(strict),
                     "mean_final_fuel_legacy_arrived": (math.fsum(e["final_fuel"] for e in arrived) / len(arrived)
                                                        if arrived else None),
                     "mean_final_fuel_strict_safe": (math.fsum(e["final_fuel"] for e in strict) / len(strict)
                                                     if strict else None),
                     "mean_steps": sum(e["steps"] for e in es) / n})
    return rows


def all_policy_common_safe(episodes):
    seeds = sorted({s for _, s in episodes})
    policies = sorted({p for p, _ in episodes})
    return sum(all(_strict(episodes[p, s]) for p in policies) for s in seeds), len(seeds)
