# Multi-training-seed evaluation

This optional paper-extension experiment trains independent Double DQN
checkpoints while preserving the existing official result and frozen checkpoint.
It is not required for the completed competition artifact.

The reusable protocol can evaluate any number of independent checkpoints. The
competition snapshot completed training seeds `42`, `1042`, `2042`, and `3042`,
each trained for 5,000 episodes. A fifth proposed seed (`4042`) remains optional
future paper work and is not included in the frozen four-seed claim. Evaluate
every completed checkpoint on the identical 100-case evaluation contract (base
seed 42) and the identical route-stress contract.

On Windows, run one training seed at a time:

```bat
python scripts\train.py --episodes 5000 --seed 42 --checkpoint checkpoints\dqn_seed_42.pt
python scripts\evaluate.py --episodes 100 --seed 42 --checkpoint checkpoints\dqn_seed_42.pt --output-dir results\multiseed\seed_42
python -m scripts.route_stress.evaluate_frozen_dqn --seeds 100 --base-seed 42 --checkpoint checkpoints\dqn_seed_42.pt --output-dir results\route_stress\multiseed\seed_42
```

Repeat after replacing `42` in the checkpoint and output directory with each
remaining training seed. Do not change the evaluation `--seed 42` or route
`--base-seed 42`; those are deliberately shared test cases, not training seeds.

After every run completes:

```bat
python -m scripts.multiseed.aggregate
```

The command writes both audit-oriented tables and publication-oriented outputs:

- `per_training_seed.csv` and `aggregate.csv`: raw long-form and overall summaries
- `tail_risk_per_training_seed.csv` and `tail_risk_summary.csv`: reward lower-tail,
  SCI upper-tail, and maximum bunkering statistics derived from existing episodes
- `route_stress_effects.csv`: paired Normal-to-Suez/Cape changes per checkpoint
- `route_stress_effect_summary.csv`: mean and population standard deviation across training seeds
- `summary.md`: ready-to-review Markdown table with the claim boundary
- `route_stress_comparison.png`: general-audience Normal vs Suez/Cape figure

The seed count is discovered from completed, paired result directories; rerunning the
same command safely regenerates the report after another seed finishes.

The aggregator fails closed when the evaluation contracts, training-seed
metadata, or checkpoint SHA-256 values disagree. It reports population standard
deviation across independently trained checkpoints separately from within-run
episode variation. Generated outputs remain git-ignored until a result-freeze
review explicitly approves selected artifacts.

These results measure synthetic training-seed stability. They do not establish
actual-voyage performance, operational savings, or a causal route effect.

The reviewed four-checkpoint values and their interpretation boundary are frozen
in [Four-training-seed Double DQN result snapshot](multiseed_results_4seed.md).
Tail outputs are derived from each run's existing `evaluation_results.csv`; they
do not modify or rerun the canonical evaluation.
