# Model boundary and maritime-research gap analysis

## Purpose

This document aligns Bunkering-AI with research themes associated with maritime
transport optimisation, ship energy efficiency, voyage simulation, digital
twins, maritime logistics, decarbonisation, uncertainty, and data-driven
decision support. University of Strathclyde maritime-systems work, including
research directions associated with Mina Tadros and Gerasimos Theotokatos, is
used as a **research-alignment lens only**. It does not imply collaboration,
replication of their vessel models, or validation by the University.

The defensible V1 description is:

> **Economic/operational bunkering decision optimisation under simulated route
> and market conditions.**

## 1. Already implemented

### V1 model boundary

| Layer | Included in V1 | Meaning |
|---|---|---|
| Market observation | Synthetic fuel price, price moving average, FX rate | Bounded simulated market signals |
| Operational observation | Fuel remaining, route remaining, constant SFC feature | Normalized decision state, not telemetry |
| Decision | Wait or select one of three nominal port actions | Port actions are not yet operationally differentiated |
| Transition | Canonical `0.05/step` fuel use and fixed refill rule | Inventory abstraction; V1.5 may vary consumption as a hidden synthetic shock |
| Policies | Three Rule-based strategies and Double DQN | Shared action and environment interface |
| Accounting | Reward, Synthetic Cost Index, success, fuel depletion, bunkering count | SCI is not actual currency cost |
| Evaluation | Common cases, seeds, environment config and accounting | Same-condition computational comparison |
| Robustness | Rule-based repeated seeds, frozen-DQN route stress, multi-training-seed aggregation | Synthetic sensitivity evidence |

The current six observations are `fuel_price`, `fuel_price_ma30`, `fx_rate`,
`fuel_remaining`, `route_remaining`, and `sfc`. The canonical environment
transition defaults to `0.05` fuel consumption per step; V1.5 can change that
normalized transition parameter without changing the observation. The `sfc`
observation is constant and is not a calibrated engine fuel-consumption curve.

### Explicitly outside V1

| Excluded physical or regulatory element | Current status |
|---|---|
| Weather and sea state | Not modelled |
| Vessel speed and voyage time | Not modelled |
| Engine load and operating point | Not modelled |
| Propulsion efficiency and hull resistance | Not modelled |
| Calibrated fuel-consumption curve | Not modelled |
| Vessel type, size, draught and trim | Not modelled |
| Measured nautical-mile route geometry | Not modelled |
| Carbon intensity and verified emissions | Not modelled |
| IMO CII/EEXI and EU ETS cost | Not modelled |
| Alternative-fuel properties and constraints | Not modelled |
| Port price, fee, waiting time and availability differences | Not modelled |
| Live vessel, AIS, engine or port-system telemetry | Not integrated |
| Vessel digital twin or hardware control | Not implemented |

Accordingly, `sfc` must not be presented as proof that ship-energy efficiency,
engine behaviour, or physical fuel use has been validated.

### Existing fairness controls

The evaluation plan gives every policy the same initial-case generation,
evaluation seeds, environment configuration, transition logic, reward and cost
accounting, and episode count. Double DQN is loaded from a checkpoint and used
greedily; route-stress evaluation keeps the weights frozen. Manifest checks,
dimension checks, termination contracts and regression tests reduce accidental
comparison drift.

This is computational fairness, not proof of objective neutrality. Double DQN is
trained against the reward it is later scored on, while Safe Stock is naturally
suited to the fixed-consumption/minimum-stock structure. Therefore reward alone
cannot rank operational quality; success, depletion, SCI and bunkering frequency
must be reported together.

## 2. V1.5 implementation status

After the four-seed result freeze, the low-risk V1.5 robustness extension was
approved. It remains isolated from the canonical evaluation.

1. Freeze the four-training-seed snapshot and report mean, population standard
   deviation, range and paired Normal-to-Suez/Cape degradation.
2. Keep the canonical Rule-based table unchanged and label the four-seed study
   as an optional Double DQN stability extension.
3. **Implemented:** distribution-oriented reporting from existing per-episode logs:
   reward standard deviation/minimum/bottom-5% mean; SCI standard
   deviation/maximum/top-5% mean; bunkering mean/maximum; success, depletion and
   termination reason.
4. Preserve the claim boundary that the 43-step route case changes episode
   horizon only. It does not include route physics.
5. **Implemented:** a versioned fuel-consumption sensitivity harness and a local
   42/43/44-step horizon sensitivity check.

### Implemented low-cost fuel-consumption sensitivity design

The smallest defensible experiment is a **hidden transition shock** at
multipliers `0.9`, `1.0`, `1.1`, and `1.2` relative to the current fixed
`0.05` consumption per step.

- The observation space, action space, reward weights and canonical defaults
  remain unchanged.
- Rule-based policies and frozen Double DQN checkpoints receive the same shock,
  initial cases and evaluation seeds.
- The constant `sfc` observation remains unchanged, so this tests resilience to
  an unobserved consumption disturbance—not adaptation using observed engine
  data.
- Outputs belong to a new experimental namespace and never overwrite official
  or route-stress results.
- Required metrics are success, fuel-depletion, SCI, bunkering count, reward and
  degradation from the `1.0` condition.

The implementation uses a default-compatible, validated environment parameter,
separate outputs, frozen inference and a cross-checkpoint aggregator. Empirical
claims remain pending until the real checkpoint runs are reviewed.

### Other low-cost scenario priorities

| Candidate | Recommendation | Reason |
|---|---|---|
| Local horizon 42/43/44 | Implemented | Measures sensitivity to the ceiling choice without claiming route realism |
| Fuel-price shock | Later, with pinned evidence | Decision-relevant and implementable, but magnitude and time profile need provenance |
| FX shock | Later, with pinned evidence | Decision-relevant; needs an explicit shock process and provenance |
| Unexpected consumption increase | Implemented | Direct safety and inventory relevance |
| Route delay | Do not add separately in V1 | Currently collapses to horizon extension |
| Port availability constraint | Defer | Nominal port actions currently lack differentiated economics and operations |

## 3. Do not add for this competition

- propulsion, engine-load, resistance, weather-routing or sea-state models;
- a “digital twin” label or real-time vessel-control claim;
- IMO/EU ETS cost logic or carbon-intensity claims;
- alternative-fuel selection;
- AIS/live sensor integration;
- fabricated distance, duration, consumption, emissions or monetary savings;
- many weak scenarios added only to increase feature count;
- any change to the canonical Rule-based figures or official result files.

These additions require new data contracts, calibration, validation and usually
retraining. Adding them late would increase scientific and regression risk more
than evidential value.

## 4. Paper and V2+ roadmap

| Version | Research scope | Validation threshold |
|---|---|---|
| V1 | Market/inventory/route-progress bunkering decisions | Reproducible synthetic evaluation |
| V1.5 | Multi-seed and versioned price/FX/consumption/horizon stresses | Paired robustness and tail-risk analysis |
| V2 | Vessel type, speed, engine load and calibrated consumption coupling | Published curves or measured operational data |
| V3 | Weather, current, route-time and voyage uncertainty | Hindcast/replay against traceable voyage data |
| V4 | Carbon price, verified emission factors and alternative fuels | Versioned IMO/EU rules and fuel-property evidence |
| V5 | Real-world replay, shadow decision support or digital-twin validation | Prospective vessel/port data and domain review |

The strongest connection to the cited maritime research directions is a staged
coupling: Bunkering-AI supplies the economic decision layer; future vessel-energy
and voyage models supply physically grounded demand and uncertainty. Until that
coupling exists, the project must remain described as a simulation-based
decision-support experiment.

## 5. Implementation map

| Change | Code | Tests | Documentation |
|---|---|---|---|
| Model boundary and roadmap | None | Existing suite | This document and README |
| Existing-log tail analysis | `scripts/multiseed/aggregate.py` | `tests/test_multiseed_aggregate.py` | Multi-seed protocol/results; implemented |
| Consumption parameter | `envs/bunkering_env.py` | Environment default/validation/determinism tests | State/action/reward specification; implemented |
| Consumption/horizon stress harness | `scripts/robustness/` | Same-case fairness, frozen-weight, output-contract tests | Dedicated protocol and limitations; implemented |
| Price/FX shocks | Environment/scenario adapter | Default regression and provenance tests | Versioned evidence note |
| V2 energy coupling | New versioned environment and training config | New contract suite | Model card and calibration report |

## 6. Regression risk to existing results

| Risk | Level | Control |
|---|---|---|
| Documentation-only boundary/results snapshot | Low | Do not edit canonical CSV/JSON or policy code |
| Tail metrics derived from existing logs | Low–Medium | Deterministic fixtures and frozen column definitions |
| Default-compatible consumption parameter | Medium | Default must reproduce current transitions exactly |
| New shock adapter/harness | Medium | Separate output path and common-case contract |
| Coupling SFC to transition or changing observations | High | New environment/checkpoint version and retraining |
| Carbon, alternative fuel or physical voyage model | High | Defer to V2+ with independent validation |

The current 183-test baseline is the regression gate. A future feature is not
acceptable if default behaviour changes, old checkpoints become ambiguous, or
official results are overwritten.

## 7. Estimated effort

| Work item | Estimate |
|---|---:|
| Boundary, roadmap and four-seed documentation | 0.5 day |
| Existing-log tail-risk report | 0.5–1 day |
| Fuel-consumption stress protocol only | 0.5 day |
| Default-compatible consumption parameter | 1 day |
| Stress harness and outputs | 0.5–1 day |
| Regression/fairness tests | 0.5–1 day |
| V2 vessel-energy coupling | 2–4 weeks after data selection |
| V3–V5 operational expansion | Multi-month research programme |

## Decision

The isolated V1.5 tail analysis, hidden fuel-consumption shock, and local horizon
sensitivity are implemented without changing canonical defaults. Freeze further
V1 functionality after the real-checkpoint V1.5 result review. Treat physically coupled fuel consumption,
weather/voyage uncertainty, decarbonisation and digital-twin validation as
versioned V2+ research rather than V1 claims.

## Research-direction references

- [University of Strathclyde, Naval Architecture, Ocean and Marine Engineering](https://www.strath.ac.uk/engineering/navalarchitectureoceanmarineengineering/)
- [University of Strathclyde research portal](https://pureportal.strath.ac.uk/)

These links establish the external research context only; all Bunkering-AI
implementation and validation claims must be supported by this repository.
