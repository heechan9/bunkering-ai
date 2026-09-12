"""Read-only diagnostic aggregation; requires matching cases and distinct checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

RULES = {"fixed_fueling", "price_reactive", "safe_stock"}
TOTALS = ["bunker_amount", "bunker_event", "realized_consumption", "clipping_loss",
          "step_sci", "reward", "price_advantage_reward", "safety_reward",
          "operational_reward", "imo_reward", "safety_violation"]


def load_run(path):
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "reward-diagnostics/v1":
        raise ValueError("unsupported diagnostic schema")
    checkpoint = manifest.get("checkpoint") or {}
    digest = checkpoint.get("sha256", "")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("checkpoint SHA-256 required")
    ep = pd.read_csv(path / "episodes.csv")
    st = pd.read_csv(path / "steps.csv")
    keys = ["policy", "seed"]
    if ep.duplicated(keys).any() or st.duplicated(keys + ["step"]).any():
        raise ValueError("duplicate episode or step")
    policies = RULES | {"double_dqn"}
    seeds = set(range(manifest["base_seed"], manifest["base_seed"] + manifest["episodes"]))
    expected = {(p, s) for p in policies for s in seeds}
    if not seeds or set(zip(ep.policy, ep.seed)) != expected:
        raise ValueError("missing or unexpected evaluation cases")
    if set(manifest["policies"]) != policies or set(zip(st.policy, st.seed)) != expected:
        raise ValueError("manifest/trace policies or cases differ")
    for frame in (ep, st):
        for col in frame.columns.difference(["policy", "end_reason"]):
            frame[col] = pd.to_numeric(frame[col], errors="raise")
        if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
            raise ValueError("non-finite diagnostic value")
    ep = ep.sort_values(keys).set_index(keys)
    st = st.sort_values(keys + ["step"])
    grouped = st.groupby(keys, sort=True)
    if not np.allclose(grouped[TOTALS].sum(), ep[TOTALS], rtol=1e-10, atol=1e-10):
        raise ValueError("episode/trace accounting mismatch")
    for key, rows in grouped:
        summary = ep.loc[key]
        if list(rows.step) != list(range(len(rows))) or summary.steps != len(rows):
            raise ValueError("non-contiguous trace")
        if not np.allclose(rows.fuel_before.iloc[1:], rows.fuel_after.iloc[:-1], atol=1e-10, rtol=0):
            raise ValueError("broken fuel trace")
        if not np.allclose([summary.initial_fuel, summary.final_fuel],
                           [rows.fuel_before.iloc[0], rows.fuel_after.iloc[-1]], atol=1e-10, rtol=0):
            raise ValueError("terminal inventory mismatch")
    if not st.safety_violation.isin([0, 1]).all() or not st.bunker_event.isin([0, 1]).all():
        raise ValueError("invalid event flags")
    if not np.array_equal(st.safety_violation, (st.fuel_after < manifest["env_config"]["min_safe_fuel"]).astype(int)):
        raise ValueError("safety flag mismatch")
    if not np.allclose(st.step_sci, st.bunker_amount * st.decision_price * st.decision_fx, rtol=1e-10, atol=1e-10):
        raise ValueError("SCI reconstruction mismatch")
    if not np.allclose(st.reward, st[["price_advantage_reward", "safety_reward", "operational_reward", "imo_reward"]].sum(axis=1), rtol=1e-10, atol=1e-10):
        raise ValueError("reward reconstruction mismatch")
    if not ep.end_reason.isin(["arrived", "fuel_depleted", "timeout"]).all():
        raise ValueError("unknown termination reason")
    balance = ep.initial_fuel + ep.bunker_amount - ep.realized_consumption - ep.clipping_loss - ep.final_fuel
    if not np.allclose(balance, 0, atol=1e-10, rtol=0) or not np.allclose(balance, ep.fuel_balance_residual, atol=1e-10, rtol=0):
        raise ValueError("fuel balance mismatch")
    return manifest, ep.reset_index(), st.reset_index(drop=True)


def summarize(ep, checkpoint):
    rows = []
    for policy, group in ep.groupby("policy", sort=True):
        row = dict(checkpoint=checkpoint if policy == "double_dqn" else "not_applicable",
                   policy=policy, evaluation_cases=len(group),
                   success_rate=float((group.end_reason == "arrived").mean()),
                   violation_episode_rate=float((group.safety_violation > 0).mean()),
                   violation_steps_mean=float(group.safety_violation.mean()),
                   violation_step_fraction=float(group.safety_violation.sum() / group.steps.sum()))
        for col in ["step_sci", "bunker_amount", "bunker_event", "final_fuel", "reward",
                    "price_advantage_reward", "safety_reward", "operational_reward", "imo_reward"]:
            row[col + "_mean"] = float(group[col].mean())
        rows.append(row)
    return rows


def aggregate(paths, output, case_seed=None):
    if output.exists():
        raise ValueError("output-dir must be a new directory")
    runs = [load_run(Path(p)) for p in paths]
    if not runs:
        raise ValueError("at least one run required")
    first, reference, _ = runs[0]
    contract = ["episodes", "base_seed", "env_config", "reward_weights", "source_baseline",
                "separate_from_official", "retraining"]
    hashes, summaries, traces, provenance = set(), [], [], []
    selected = first["base_seed"] if case_seed is None else case_seed
    if selected not in set(reference.seed):
        raise ValueError("case seed absent")
    for index, (manifest, ep, st) in enumerate(runs):
        if any(manifest.get(k) != first.get(k) for k in contract):
            raise ValueError("incompatible evaluation manifests")
        digest = manifest["checkpoint"]["sha256"]
        if digest in hashes:
            raise ValueError("duplicate checkpoint: not an independent model")
        hashes.add(digest)
        for policy in RULES:
            a = reference[reference.policy == policy].reset_index(drop=True)
            b = ep[ep.policy == policy].reset_index(drop=True)
            try:
                pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-10, atol=1e-10)
            except AssertionError as exc:
                raise ValueError("repeated rule results differ") from exc
            try:
                pd.testing.assert_frame_equal(
                    runs[0][2][runs[0][2].policy == policy].reset_index(drop=True),
                    st[st.policy == policy].reset_index(drop=True),
                    check_exact=False, rtol=1e-10, atol=1e-10)
            except AssertionError as exc:
                raise ValueError("repeated rule traces differ") from exc
        keep = ep if index == 0 else ep[ep.policy == "double_dqn"]
        summaries.extend(summarize(keep, digest))
        case = st[(st.seed == selected) & ((st.policy == "double_dqn") | (index == 0))].copy()
        case["checkpoint"] = np.where(case.policy == "double_dqn", digest, "not_applicable")
        traces.append(case)
        provenance.append(dict(path=str(Path(paths[index])), checkpoint=manifest["checkpoint"],
            files={name: hashlib.sha256((Path(paths[index]) / name).read_bytes()).hexdigest()
                   for name in ("manifest.json", "episodes.csv", "steps.csv")}))
    summary = pd.DataFrame(summaries)
    dqn = summary[summary.policy == "double_dqn"]
    metrics = [c for c in summary if c not in ("checkpoint", "policy", "evaluation_cases")]
    across = [dict(metric=c, checkpoint_count=len(dqn), mean=dqn[c].mean(),
                   std_ddof0=dqn[c].std(ddof=0), minimum=dqn[c].min(), maximum=dqn[c].max()) for c in metrics]
    output.mkdir(parents=True, exist_ok=False)
    summary.to_csv(output / "policy_summary.csv", index=False)
    pd.DataFrame(across).to_csv(output / "dqn_checkpoint_summary.csv", index=False)
    pd.concat(traces).to_csv(output / "case_trace.csv", index=False)
    (output / "manifest.json").write_text(json.dumps(dict(
        schema="reward-diagnostics-summary/v1", sources=provenance,
        selected_case_seed=selected, selection="base seed by default; illustrative, not statistically representative",
        checkpoint_count=len(runs), evaluation_cases_per_checkpoint=first["episodes"],
        rule_duplicates_removed=True, std_ddof=0,
        limits="Descriptive checkpoint statistics, not confidence intervals. Synthetic SCI; no terminal inventory credit. No trained-model provenance inferred from filenames."
    ), indent=2), encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case-seed", type=int)
    args = parser.parse_args(argv)
    try:
        result = aggregate(args.inputs, args.output_dir, args.case_seed)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(result.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
