"""Regenerate the synthetic smoke fixture (3 seeds x 3 policies, 3 steps each).

Hand-chosen fuels/actions/prices, not native results. Designed so that
double_dqn vs safe_stock has 1 common strict-safe seed (n=1 interval not
estimable) and double_dqn vs fixed_fueling has 0 (null).
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from ledger import expected_transition  # noqa: E402

CFG = json.loads((HERE.parent / "config" / "bai_v4_native.json").read_text())
# (initial fuel, actions, legacy_arrived, end_reason)
PLANS = {
    "double_dqn": {s: (1.0, [0, 1, 0], True, "arrived") for s in (1, 2, 3)},
    "safe_stock": {1: (1.0, [0, 0, 0], True, "arrived"), 2: (0.18, [1, 0, 0], True, "arrived"),
                   3: (0.18, [1, 0, 0], True, "arrived")},
    "fixed_fueling": {s: (0.12, [0, 0, 0], False, "fuel_depleted") for s in (1, 2, 3)},
}


def price(seed, step):
    return 600.0 + 10 * seed + step, 1300.0 + seed


def main(out=HERE):
    episodes, steps = [], []
    for policy, plans in PLANS.items():
        for seed, (fuel0, actions, arrived, reason) in plans.items():
            f, cost, short, res, low = fuel0, 0.0, 0, 0, float("inf")
            for k, a in enumerate(actions, start=1):
                p, fx = price(seed, k)
                u, _, q, f_next = expected_transition(f, a, CFG)
                steps.append(dict(seed=seed, policy=policy, step=k, action=a, fuel_before=f,
                                  pre_refill_unclipped=u, decision_price=p, decision_fx=fx,
                                  purchase=q, fuel_after=f_next, step_sci=q * p * fx))
                cost += q * p * fx
                short += u < -1e-9
                res += u < 0.15 - 1e-9
                low = min(low, u)
                f = f_next
            p0, fx0 = price(seed, 1)
            pt, fxt = price(seed, len(actions) + 1)
            init, term = fuel0 * p0 * fx0, f * pt * fxt
            safe = arrived and short == 0 and res == 0
            episodes.append(dict(seed=seed, policy=policy, steps=len(actions), reward=0.0, bunkering_count=sum(
                1 for t in steps if t["policy"] == policy and t["seed"] == seed and t["purchase"] > 1e-6),
                end_reason=reason, legacy_arrived=arrived, arrived_without_pre_refill_shortage=arrived and short == 0,
                safe_arrival=safe, pre_refill_shortage_steps=short, pre_refill_reserve_violation_steps=res,
                minimum_pre_refill_fuel=low, purchase_sci=cost, initial_inventory_value=init,
                terminal_inventory_value=term, final_fuel=f, inventory_adjusted_sci=cost + init - term,
                safe_arrival_adjusted_sci=cost + init - term if safe else None))
    for name, rows in [("smoke_episodes.csv", episodes), ("smoke_steps.csv", steps)]:
        with (Path(out) / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
