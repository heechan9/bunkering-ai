"""Regenerate the native market tape from a seed and check recorded valuation against it.

The pinned env draws its market from ``env.np_random`` only: two normals at reset,
then one price and one FX normal per step, before fuel is touched. Actions never
draw from that stream, so (seed, step) fixes price and FX for every policy. This
module rebuilds that stream with numpy directly, without importing the env or
reading recorded prices, which gives terminal price/FX a source independent of
the episode CSV. test_market_tape.py checks the constants and the stream against
the pinned env.
"""
import numpy as np

from ledger import SCI_TOL, STEP_COLUMNS, InputError, _read

# Pinned native env a4634faa (envs/bunkering_env.py) market constants.
INITIAL_FUEL = 1.0
PRICE_INIT = (500.0, 50.0)
FX_INIT = (1300.0, 30.0)
PRICE_STEP_SD = 0.01
FX_STEP_SD = 0.003
PRICE_RANGE = (250.0, 850.0)
FX_RANGE = (1000.0, 1600.0)
PRICE_TOL = 1e-9  # price and FX units; CSV floats round-trip exactly


def regenerate(seed, steps):
    """Return [(price, fx)] for t=0..steps; index t is the market after t transitions."""
    # gymnasium.utils.seeding.np_random(seed) is Generator(PCG64(SeedSequence(seed))).
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))
    price = float(np.clip(rng.normal(*PRICE_INIT), *PRICE_RANGE))
    fx = float(np.clip(rng.normal(*FX_INIT), *FX_RANGE))
    tape = [(price, fx)]
    for _ in range(steps):
        # Same draw order as BunkeringEnv._transition: price first, then FX.
        price = float(np.clip(price * (1.0 + rng.normal(0.0, PRICE_STEP_SD)), *PRICE_RANGE))
        fx = float(np.clip(fx * (1.0 + rng.normal(0.0, FX_STEP_SD)), *FX_RANGE))
        tape.append((price, fx))
    return tape


def audit_valuation(episodes, steps_path=None):
    """Compare initial/terminal inventory values, and decision prices if steps are given, with the tape.

    Decision price/FX at step k must equal tape[k-1]. Run after ledger.audit_steps has
    validated the step file. Returns (mismatches, seeds_regenerated).
    """
    traces = {}
    if steps_path:
        for r in _read(steps_path, STEP_COLUMNS):
            traces.setdefault((r["policy"], int(r["seed"])), []).append(r)
    need = {}
    for (policy, seed), e in episodes.items():
        if e["steps"] < 1:
            raise InputError(f"{policy}/{seed}: steps must be at least 1 to value the terminal market")
        last = max([e["steps"]] + [int(t["step"]) for t in traces.get((policy, seed), [])])
        need[seed] = max(need.get(seed, 0), last)
    tapes = {seed: regenerate(seed, n) for seed, n in need.items()}
    mismatches = []

    def bad(check, key, step, expected, actual):
        mismatches.append({"check": check, "policy": key[0], "seed": key[1], "step": step,
                           "expected": expected, "actual": actual})

    for key, e in sorted(episodes.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        tape = tapes[key[1]]
        (p0, fx0), (pt, fxt) = tape[0], tape[e["steps"]]
        initial, terminal = INITIAL_FUEL * p0 * fx0, e["final_fuel"] * pt * fxt
        if abs(initial - e["initial_inventory_value"]) > SCI_TOL:
            bad("regenerated_initial_value", key, None, initial, e["initial_inventory_value"])
        if abs(terminal - e["terminal_inventory_value"]) > SCI_TOL:
            bad("regenerated_terminal_value", key, None, terminal, e["terminal_inventory_value"])
        for t in sorted(traces.get(key, []), key=lambda t: int(t["step"])):
            k = int(t["step"])
            expected, actual = tape[k - 1], (float(t["decision_price"]), float(t["decision_fx"]))
            if abs(expected[0] - actual[0]) > PRICE_TOL or abs(expected[1] - actual[1]) > PRICE_TOL:
                bad("regenerated_decision_market", key, k, expected, actual)
    return mismatches, len(tapes)
