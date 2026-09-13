"""Supplementary accounting trace; never changes the official environment or reward."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from envs.bunkering_env import BunkeringEnv, REWARD_WEIGHTS
from scripts.baseline import FixedFuelingStrategy, PriceReactiveStrategy, SafeStockStrategy


def trace_episode(policy, seed=42, env_config=None):
    """Record realized accounting, including clipping loss; no inferred physical units."""
    env = BunkeringEnv(**(env_config or {}))
    obs, _ = env.reset(seed=seed)
    rows = []
    # Internal raw fuel avoids float32 observation rounding in conservation checks.
    while True:
        fuel_before = env._fuel_remaining
        action = policy.select_action(env, obs, len(rows))
        obs, reward, terminated, truncated, info = env.step(action)
        fuel_after = env._fuel_remaining
        consumed = min(fuel_before, env.fuel_consumption_per_step)
        amount = info["actual_bunker_amount"]
        clipping_loss = fuel_before - consumed + amount - fuel_after
        b = info["reward_breakdown"]
        rows.append(dict(
            policy=policy.name, seed=seed, step=len(rows), action=int(action),
            fuel_before=fuel_before, fuel_after=fuel_after,
            realized_consumption=consumed, clipping_loss=clipping_loss,
            bunker_amount=amount,
            bunker_event=int(amount > env._BUNKER_AMOUNT_EPSILON),
            decision_price=info["decision_fuel_price"],
            decision_ma=info["decision_price_ma30"],
            decision_fx=info["decision_fx_rate"],
            step_sci=info["step_cost_index"], reward=reward,
            price_advantage_reward=REWARD_WEIGHTS["fuel_cost_saving"] * b["fuel_cost_saving"],
            safety_reward=-REWARD_WEIGHTS["risk_penalty"] * b["risk_penalty"],
            operational_reward=REWARD_WEIGHTS["operational_efficiency"] * b["operational_efficiency"],
            imo_reward=REWARD_WEIGHTS["imo_compliance_bonus"] * b["imo_compliance_bonus"],
            # Preserve the official strict comparison, including float boundary effects.
            # Tolerance reclassification is separate postprocessing; see snapshot audit.
            safety_violation=int(fuel_after < env.min_safe_fuel),
        ))
        if terminated or truncated:
            break
    summary = dict(policy=policy.name, seed=seed, steps=len(rows),
                   end_reason=info["end_reason"], initial_fuel=rows[0]["fuel_before"],
                   final_fuel=fuel_after)
    for field in ("bunker_amount", "bunker_event", "realized_consumption", "clipping_loss",
                  "step_sci", "reward", "price_advantage_reward", "safety_reward",
                  "operational_reward", "imo_reward", "safety_violation"):
        summary[field] = sum(r[field] for r in rows)
    summary["fuel_balance_residual"] = (summary["initial_fuel"] + summary["bunker_amount"]
        - summary["realized_consumption"] - summary["clipping_loss"] - fuel_after)
    env.close()
    return rows, summary


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.episodes < 1 or args.base_seed < 0:
        parser.error("episodes must be positive and base-seed nonnegative")
    # Require a fresh directory to avoid mixing runs or overwriting official artifacts.
    if args.output_dir.exists():
        parser.error("output-dir must be a new directory")
    policies = [FixedFuelingStrategy(), PriceReactiveStrategy(), SafeStockStrategy()]
    checkpoint = None
    if args.checkpoint:
        from scripts.evaluate import load_dqn_policy, file_sha256
        policies.append(load_dqn_policy(args.checkpoint, {}))
        checkpoint = {"name": args.checkpoint.name, "sha256": file_sha256(args.checkpoint)}
    rows, summaries = [], []
    for policy in policies:
        for seed in range(args.base_seed, args.base_seed + args.episodes):
            trace, summary = trace_episode(policy, seed)
            rows.extend(trace)
            summaries.append(summary)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_csv(args.output_dir / "steps.csv", rows)
    write_csv(args.output_dir / "episodes.csv", summaries)
    manifest = dict(schema="reward-diagnostics/v1", episodes=args.episodes,
        base_seed=args.base_seed, policies=[p.name for p in policies], checkpoint=checkpoint,
        env_config=dict(n_ports=3, max_steps=30, min_safe_fuel=0.15, fuel_consumption_per_step=0.05),
        reward_weights=REWARD_WEIGHTS, separate_from_official=True, retraining=False,
        source_baseline="97233c1c442a687aaed4a34e2cadca0d98aa2fb9",
        limits="Normalized tank quantities and synthetic cost only. No terminal inventory credit."
    )
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(summaries)} episodes to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
