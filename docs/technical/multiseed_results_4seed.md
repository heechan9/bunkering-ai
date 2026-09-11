# Four-training-seed Double DQN result snapshot

## Status and provenance

This optional extension evaluates four independently trained Double DQN
checkpoints. It does **not** replace the canonical single-checkpoint official
comparison or the fixed Rule-based results.

- training seeds: `42`, `1042`, `2042`, `3042`
- training episodes: 5,000 per checkpoint
- evaluation cases: 100 per checkpoint, shared base seed `42`
- route-stress cases: 100 per checkpoint, shared base seed `42`
- environment and accounting contract: unchanged
- aggregation command: `python -m scripts.multiseed.aggregate`
- execution date: 2026-09-11
- repository tests before execution: 167 passed

Generated checkpoints and result directories remain git-ignored. The values
below are a reviewed documentation snapshot transcribed from the aggregator
output; they are not new canonical result files.

## Normal-condition stability

| Metric | Mean across training seeds | Population std | Minimum | Maximum |
|---|---:|---:|---:|---:|
| Reward | 0.043921 | 0.001596 | 0.041753 | 0.045650 |
| Synthetic Cost Index | 839,763.41 | 8,193.64 | 826,282.11 | 846,347.87 |
| Success rate | 100% | 0 pp | 100% | 100% |
| Fuel-depletion rate | 0% | 0 pp | 0% | 0% |
| Mean bunkering count | 4.900 | 0.298 | 4.420 | 5.220 |
| SCI per step | 27,992.11 | 273.12 | 27,542.74 | 28,211.60 |

All four trained checkpoints reached the destination in every shared evaluation
case without fuel depletion. This supports stability within the tested synthetic
contract, not actual-voyage reliability.

## Paired Normal-to-Suez/Cape effect

Each checkpoint is compared with itself under Normal and the 43-step
Suez/Cape representative condition.

| Normalized metric | Normal mean | Stress mean | Mean change | Change std | Range across checkpoints |
|---|---:|---:|---:|---:|---:|
| SCI per step | 27,992.11 | 29,418.37 | +5.097% | 0.349 pp | +4.503% to +5.402% |
| Bunkering per 30 steps | 4.900 | 5.587 | +13.969% | 1.630 pp | +12.543% to +16.740% |

Success remained 100% and fuel depletion remained 0% in both conditions.
The paired direction is consistent across the four checkpoints.

## Claim boundary

The result supports the limited statement that, within the current synthetic
environment, extending the episode horizon from 30 to 43 steps increased
normalized SCI exposure and normalized bunkering frequency for all four frozen
Double DQN checkpoints tested.

It does not establish:

- actual fuel consumption, voyage duration, distance-normalized cost, or savings;
- a causal effect of a real Suez closure or Cape diversion;
- weather, current, speed, engine-load, or propulsion effects;
- superiority of Double DQN over Safe Stock;
- generalization to unseen vessel types, routes, markets, or real operations.

Reward is reported for completeness. Its increase under the longer scenario
must not be described as improved operational performance because reward is
defined by the current synthetic objective and the exposure length changes.

## Reproduction

Use the procedure in [Multi-training-seed evaluation](multiseed_evaluation.md).
The fifth proposed seed (`4042`) was not required for this competition snapshot.
Future paper work may add further independent training seeds without modifying
or relabelling these four-seed results.
