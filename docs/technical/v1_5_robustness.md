# V1.5 fuel-consumption and horizon robustness

## Purpose

This optional paper-extension experiment measures policy sensitivity to two
small, versioned perturbation families while preserving every canonical result:

1. hidden fuel-consumption multipliers `0.9`, `1.0`, `1.1`, and `1.2` relative
   to the existing normalized `0.05` consumption per step;
2. local horizon sensitivity at `42`, `43`, and `44` steps, with `43` as the
   representative-route reference.

It evaluates Fixed Fueling, Price Reactive, Safe Stock, and a frozen Double DQN
on identical episode seeds and environment settings within each scenario. It
does not retrain the checkpoint.

## Interpretation boundary

The consumption parameter is a normalized inventory transition, not tonnes,
SFC in physical units, an engine load curve, or a propulsion model. The constant
`sfc` observation remains unchanged, so the experiment represents an
**unobserved consumption disturbance**. It tests policy resilience under the
synthetic contract, not adaptation to measured ship-energy data.

The 42/43/44-step family tests sensitivity to integer horizon selection. It does
not represent measured voyage duration or nautical miles and does not add
weather, speed, current, draught, or sea-state physics.

## Compatibility contract

- `BunkeringEnv()` still defaults to exactly `0.05` consumption per step.
- Observation and action spaces, reward weights, random walks and termination
  ordering are unchanged.
- Explicit `fuel_consumption_per_step=0.05` and the omitted default produce the
  same seeded trajectory.
- Outputs are written below `results/robustness/` and never overwrite official
  evaluation or route-stress artifacts.
- Signed reward receives an absolute paired change only; percentage change is
  intentionally omitted.

## Metrics

Each scenario-policy group reports:

- reward mean, population standard deviation, minimum and bottom-5% mean;
- Synthetic Cost Index mean, standard deviation, maximum and top-5% mean;
- SCI per realized step;
- success and fuel-depletion rates;
- bunkering mean, maximum and per-30-step mean.

The empirical 5% tail uses `ceil(0.05 * episodes)`, with at least one episode.
SCI remains a synthetic index and must not be described as money or savings.

## Run one checkpoint

```bat
python -m scripts.robustness.evaluate_v1_5 --episodes 100 --base-seed 42 --checkpoint checkpoints\dqn_seed_42.pt --output-dir results\robustness\v1_5_multiseed\seed_42
```

The run writes `raw.csv`, `summary.csv`, `paired_effects.csv`,
`robustness_comparison.png`, and `manifest.json`.

Repeat with training seeds `1042`, `2042`, and `3042`. Keep evaluation
`--base-seed 42` unchanged so every checkpoint sees the same 100 cases.

## Aggregate independent checkpoints

```bat
python -m scripts.robustness.aggregate_v1_5 --input-root results\robustness\v1_5_multiseed --output-dir results\robustness\v1_5_aggregate
```

The aggregator fails closed when scenario definitions, base seed, episode count,
or manifest schema differs between runs. Double DQN variation is summarized
across independent training seeds. Rule-based rows are repeated only to prove
the same-case contract; they must be identical and are not counted as
independent training seeds.

Aggregate outputs are:

- `per_training_seed.csv`
- `aggregate.csv`
- `paired_effects_per_training_seed.csv`
- `paired_effect_summary.csv`
- `robustness_comparison.png`
- `manifest.json`

Generated artifacts remain git-ignored until a separate result-freeze review.

## Existing-log tail analysis

The existing multi-training-seed aggregator now also reads each checkpoint's
canonical `evaluation_results.csv` and writes:

- `tail_risk_per_training_seed.csv`
- `tail_risk_summary.csv`

This derives new statistics from existing episodes; it does not rerun or change
the four-seed official-normal evaluation.

## Reviewed four-checkpoint result

The four frozen checkpoints have now been evaluated and reviewed. The empirical
values and claim boundary are frozen in
[the V1.5 four-training-seed result snapshot](v1_5_results_4seed.md).

## Allowed paper claim

The reviewed result supports a limited statement about synthetic policy
sensitivity to a hidden normalized fuel-use disturbance and local horizon
choice. It does not support claims about physical fuel consumption, actual
voyage performance, cost savings, or digital-twin validation.
