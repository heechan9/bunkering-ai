# Multi-training-seed evaluation

This optional paper-extension experiment trains independent Double DQN
checkpoints while preserving the existing official result and frozen checkpoint.
It is not required for the completed competition artifact.

Use training seeds `42`, `1042`, `2042`, `3042`, and `4042`. Each checkpoint is
trained for 5,000 episodes. Evaluate every checkpoint on the identical 100-case
evaluation contract (base seed 42) and the identical route-stress contract.

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

The aggregator fails closed when the evaluation contracts, training-seed
metadata, or checkpoint SHA-256 values disagree. It reports population standard
deviation across independently trained checkpoints separately from within-run
episode variation. Generated outputs remain git-ignored until a result-freeze
review explicitly approves selected artifacts.

These results measure synthetic training-seed stability. They do not establish
actual-voyage performance, operational savings, or a causal route effect.
