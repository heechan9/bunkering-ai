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
saving is inferred. Hormuz contraction remains observation-only because an
equivalent sea bypass is not established; with identical seeds its policy rows
must exactly match the normal synthetic environment. Output under
`results/route_stress/rulebased_100seed/` is git-ignored and explicitly separate
from the canonical four-policy comparison.
