# V1.5 four-training-seed robustness result snapshot

> Subsequent baseline diagnostic correction: the original strict safety comparison
> counts Safe Stock fuel 0.1499999999999997 as below 0.15 and adds a -0.5 penalty.
> All historical values below remain unchanged. This rounding-boundary effect
> must not be presented as substantive safety inferiority. The new audit covers
> baseline 0.05/30-step records, not safety reclassification of every stress condition.
> See [the four-checkpoint accounting review](reward_diagnostics_results_4seed.md).


## Frozen evaluation contract

This reviewed extension uses four independently trained Double DQN checkpoints
(training seeds `42`, `1042`, `2042`, and `3042`). Each frozen checkpoint
was evaluated on the same 100 cases beginning at evaluation seed 42. Fixed
Fueling, Price Reactive, Safe Stock, and Double DQN used identical cases within
each scenario.

The experiment is separate from, and does not replace, the canonical official
comparison. Population standard deviation (ddof=0) below is across the four
independently trained Double DQN checkpoints.

## Hidden normalized consumption disturbance

| Condition vs 0.05/step baseline | DQN success | DQN fuel depletion | SCI/step paired change | Bunkering/30-step paired change |
|---|---:|---:|---:|---:|
| -10% consumption | 100% | 0% | -10.75% ± 0.24% | -6.45% ± 0.76% |
| +10% consumption | 100% | 0% | +11.68% ± 0.87% | +5.88% ± 0.70% |
| +20% consumption | 100% | 0% | +22.59% ± 0.55% | +10.56% ± 1.72% |

The baseline DQN mean was 27,992.11 SCI/step and 4.900 bunkering decisions per
30 steps. Under +20% consumption, these means were 34,316.90 and 5.420,
respectively. All four checkpoints kept 100% synthetic arrival success and zero
fuel-depletion episodes in every consumption condition.

This is evidence of safety stability inside the evaluated synthetic range, while
the rising SCI and bunkering frequency show a clear resource/cost burden. An
increase in signed reward under some stresses is not interpreted as improved
operational performance.

## Local horizon sensitivity

The existing 43-step representative-route condition was compared with 42 and
44 steps.

| Condition vs 43 steps | DQN success | DQN fuel depletion | SCI/step paired change | Bunkering/30-step paired change |
|---|---:|---:|---:|---:|
| 42 steps | 100% | 0% | -0.48% ± 0.25% | -0.70% ± 0.40% |
| 44 steps | 100% | 0% | +0.30% ± 0.30% | +0.64% ± 0.27% |

The 43-step means were 29,418.37 SCI/step and 5.5866 bunkering decisions per 30
steps. The small adjacent-horizon changes support local numerical stability of
the 43-step choice under this synthetic contract. They do not validate nautical
distance, voyage time, weather, currents, or route causality.

## Baseline-policy context

Across these shared cases, Safe Stock retained 100% success and zero depletion.
Fixed Fueling retained 0% success and 100% depletion. Price Reactive remained
low-success (1% to 4%, depending on condition). These results describe the
current policy definitions and reward/environment contract; they are not a
general ranking of maritime bunkering methods.

## Official-normal Double DQN tail risk

These statistics are derived from the existing 100-episode official-normal log
for each checkpoint; no policy was retrained or reevaluated.

| Tail metric | Mean across 4 training seeds | Across-seed std (ddof=0) | Min | Max |
|---|---:|---:|---:|---:|
| Minimum episode reward | -0.01714 | 0.01703 | -0.03639 | 0.00000 |
| Bottom-5% mean reward | -0.00378 | 0.00382 | -0.00862 | 0.00000 |
| Maximum episode SCI | 1,129,718 | 63,282 | 1,081,776 | 1,237,345 |
| Top-5% mean SCI | 1,072,647 | 21,682 | 1,049,879 | 1,108,264 |
| Maximum bunkering count | 16.75 | 1.09 | 15 | 18 |

The upper SCI tail and maximum bunkering count show that mean-only reporting
would hide materially heavier individual synthetic episodes. These are empirical
tails from 100 cases per checkpoint, not fitted extreme-value estimates,
confidence intervals, or evidence of real monetary exposure.

## Claim boundary

The consumption multiplier changes a normalized, unobserved inventory
transition. It is not measured fuel use, tonnes, SFC, engine load, propulsion
efficiency, weather, vessel type, or a digital twin. SCI is not currency or
verified operating cost. The result therefore supports only an exploratory
claim about synthetic policy robustness and local horizon sensitivity, not
actual-voyage savings or real-world deployment performance.
