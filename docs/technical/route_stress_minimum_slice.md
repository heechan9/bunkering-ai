# Route-stress minimum slice

This exploratory module keeps overseas chokepoint evidence separate from the
canonical UPA reference data and the official Rule-based/Double-DQN comparison.

The first parser contract targets the fixed ONS release dated 2024-04-24. The
four deterministic fixtures are `normal`, `suez_contraction`,
`hormuz_contraction`, and `cape_detour_assumption`. Their ratios are scenario
inputs derived from the ONS bulletin, not proof of closure, causation, or an
individual vessel's diversion.

No fixture assigns detour distance, duration, extra fuel, insurance cost, fuel
price, or monetary savings. Those values require independent sources or
explicit versioned assumptions. The adapter returns episode metadata only and
does not modify the six-variable observation space, action space, reward, saved
checkpoints, or official result files.

Before adding IMF PortWatch, pin the ArcGIS item/API schema, source revision,
retrieval timestamp, raw SHA-256, and any third-party AIS reuse conditions.
Suez Canal Authority and IMO aggregates remain corroborating evidence in this
minimum slice.

## Reproducible ONS preparation

Run `python -m scripts.route_stress.analyze_ons`. The command downloads the ONS
CSV, refuses to write it when the pinned SHA-256 differs, removes the publisher's
footer rows, and writes `results/route_stress/ons_past_only_baseline.csv`.
The generated CSV is reproducible and intentionally git-ignored; canonical
official evaluation artifacts remain unchanged.

The baseline at week *t* is an expanding mean of weeks strictly before *t*,
separately for each passage and vessel type. The first four observations remain
missing by design. This artifact describes traffic conditions only; it is not a
policy-performance result and is not joined row-by-row to UPA data.

## Representative Rule-based stress evaluation

Run `python -m scripts.route_stress.evaluate_rulebased`. This is a separate
100-seed exploratory evaluation and never writes to the official evaluation or
robustness directories.

For the Suez/Cape scenario, the Suez Canal Authority's Singapore–Rotterdam
comparison is used: 8,288 nautical miles through Suez and 11,755 nautical miles
around the Cape. The 1.4183 distance multiplier scales the synthetic 30-step
route to 43 steps using ceiling rounding. This is a representative route
assumption, not evidence that any specific vessel diverted.

No speed, elapsed time, fuel tonnes, insurance premium, fuel price, or monetary
saving is inferred. Hormuz contraction is a **contextual negative control**, not
a third independent quantitative shock: an equivalent sea bypass is not
established, so no operational effect is applied and, with identical seeds, its
policy rows must exactly match the normal synthetic environment. Output under
`results/route_stress/rulebased_100seed/` is git-ignored and explicitly separate
from the canonical four-policy comparison.

## Frozen Double DQN stress evaluation

Run `python -m scripts.route_stress.evaluate_frozen_dqn` after downloading the
published `dqn_final.pt` checkpoint described in `official_evaluation.md`. The
script loads that exact checkpoint once, switches its policy network to eval
mode, and performs greedy inference only; it never trains or updates weights.

The same evaluation seeds and the same three route-impact assumptions used by
the Rule-based stress run are applied. The 43-step Suez/Cape environment is an
out-of-distribution synthetic sensitivity test for a model trained in the
30-step environment, not evidence of policy generalization or operational
performance. Results are written below
`results/route_stress/frozen_double_dqn_100seed/`, remain git-ignored, and do
not replace or modify the canonical four-policy comparison.

### Observed 100-seed sensitivity result

The published checkpoint (`sha256: 970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392`)
was evaluated over seeds 42–141. Population standard deviation (`ddof=0`) is
reported for reward.

| Scenario | Mean steps | Reward mean ± std | SCI mean | SCI/step | Success | Bunkers mean | Bunkers/30 steps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Normal | 30 | 0.0443 ± 0.0579 | 847,117.9 | 28,237.3 | 100% | 5.31 | 5.31 |
| Hormuz contextual control | 30 | 0.0443 ± 0.0579 | 847,117.9 | 28,237.3 | 100% | 5.31 | 5.31 |
| Suez/Cape representative | 43 | 0.0748 ± 0.0843 | 1,269,622.0 | 29,526.1 | 100% | 8.70 | 6.07 |

Normal and Hormuz rows match exactly by design because the Hormuz fixture does
not invent a bypass effect. In the longer Suez/Cape scenario, the frozen model
still completed every synthetic episode, while both the mean Synthetic Cost
Index and mean bunkering count increased. Much of the cumulative increase is
exposure to 43 rather than 30 steps: SCI per step rises about 4.6%, while
bunkering normalized to 30 steps rises from 5.31 to 6.07 (about 14.3%). These
descriptive differences do not isolate a causal route-stress effect. The higher
reward therefore must not be presented as lower cost or overall superiority.
This is a one-checkpoint sensitivity result; it does not establish robustness
across training seeds.

For Price Reactive, the observed success count changes from 3/100 under Normal
to 1/100 under the representative Suez/Cape condition. These are sparse events;
the document reports counts only and does not claim a statistically established
decline.

ONS traffic observations provide external context and are not joined into the
environment or used as model inputs. Any paper or presentation citing an ONS
value must label it beside the citation as contextual evidence, not a simulation
input.
