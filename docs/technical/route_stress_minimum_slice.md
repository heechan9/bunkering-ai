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

The baseline at week *t* is an expanding mean of weeks strictly before *t*,
separately for each passage and vessel type. The first four observations remain
missing by design. This artifact describes traffic conditions only; it is not a
policy-performance result and is not joined row-by-row to UPA data.
