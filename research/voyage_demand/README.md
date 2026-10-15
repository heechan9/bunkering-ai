# Voyage fuel-demand validation preparation

Status: preparation and synthetic pipeline tests only. No vessel prediction experiment,
paper reproduction, measured savings, or operating recommendation has been completed.
This branch starts at main `25f89464db42b8e71b4f56ba51d05198e5d3921e`.
The separate procurement Draft PR is unchanged. Official SCI, manuscripts and deployed
models are outside this module.

## Existing implementation and available evidence

The repository already has `scripts/review_ab_log.py`, `scripts/compare_ab_log.py`,
unit/ROB checks, and fuel-source review documentation. Public vessel-analysis entry
points are deliberately disabled; corresponding public CSVs contain headers only.
The existing fuel-source README says older vessel folds can include later periods
when holding out earlier legs. Those diagnostics do not establish prospective performance.

On 2026-10-15 an authorized private workbook was inspected read-only.
Only structural evidence is described here. No original rows, identifiers, source
hashes, dates, fuel totals, routes or private links are included. The downloaded copy
and structural notes remain under git-ignored `private/`; source bytes were unchanged.

| Inspected structure | Finding | Consequence |
|---|---|---|
| Workbook | Monthly summary, daily records and separate worksheet | File count is not independent voyage count |
| Summary sheet | Time-of, date, distance, speed (Kts), RPM, mass-consumption (M/T), ROB labels | Summary consumption is not an independent measurement if derived from ROB |
| Daily sheet | Date, Hours, Speed, RPM, Temp, generator (KW), M/E, G/E, Boiler Consumption | Observed operating conditions are not automatically planning inputs |
| Daily rows | Record counts and values withheld from public diff | Daily records do not establish independent voyage counts |
| Time metadata | No explicit timezone on inspected daily date cells; receipt/issue times and complete port-to-port boundaries unverified | No aligned chronological voyage experiment yet |
| Units | Summary explicitly labels M/T; earlier provider-review documentation corrects daily quantities to kL | Daily kL is not L/h; do not reinterpret it as a rate |
| Density | Source, temperature/reference conditions and period applicability unverified | Volume-to-tonne comparison held |
| Third sheet | Existing provider-review documentation excludes it as unrelated | Do not borrow its conversion factor |

The workbook has a summary voyage identifier, but complete independent voyage boundaries
and the number of qualifying voyages have **not** been established. Even if one voyage
is confirmed, only within-voyage chronological pipeline checks are possible. At least
three temporally distinct, complete voyages are needed for nonempty training,
calibration and test sets; that minimum alone does not establish statistical reliability.

## Input contract and data dictionary

These are proposed canonical fields, **not a claim that the workbook contains them**.
Each actual source column must be mapped privately and verified before use. For each
variable record: name, unit, source/reference, observation or forecast issue time,
target time, receipt time, receipt latency, purchase-time availability, and missing-data
policy. Use timezone-aware times; retain original source/reference conditions.

| Canonical field | Unit / type | Evidence required | Missing handling |
|---|---|---|---|
| voyage_key, port-to-port start/end | Private key, aware timestamps | Confirmed complete voyage boundaries | Hold experiment |
| purchase_at | Aware timestamp | Actual decision cutoff | Hold planning evaluation |
| planned_hours | h | Plan issued and received before purchase, with target period | Hold baseline |
| rate | L/h | Measured interval-average rate, complete interval coverage | Reject missing; observed zero is retained |
| density_kg_l, density_basis | kg/L, reference/source text | Fuel-specific density and matching temperature/reference conditions | Hold tonne conversion; no default density |
| future weather/speed | Explicit unit, forecast/plan | Forecast issue/receipt before cutoff; target may be later | Reject undocumented availability |
| measured power/temperature | kW / verified temperature unit | Observation and receipt times | Future observations excluded from planning |
| opening/supplied/consumed/closing | Common t | Confirmed aligned ROB period and actual supplies | Blank supply is unknown, never zero |

Future measured engine output/temperature and end-of-voyage aggregates are excluded
from pre-purchase planning, even when useful for contemporaneous consumption estimation.
`available_feature` fails closed on missing provenance/timing. Names alone cannot prove
availability: a source owner must attest whether a field is observed, planned or forecast.

## Frozen evaluation protocol

1. Freeze qualifying complete voyages and exclusions before viewing test outcomes.
   Sort whole voyages in time: past voyages train, later voyages calibrate, newest
   voyages test. Never shuffle rows across voyages or let windows cross boundaries.
   Strict interval separation avoids sharing boundary observations. Do not tune split
   dates after seeing test results. With one voyage report pipeline checks only.
2. Fit missing-data policy, scaling, feature selection and all hyperparameters using
   training only. Freeze them before calibration/test. Never backward-fill future
   measurements. The example scalar preprocessor rejects nontraining/future rows;
   it does not provide a fitted real-data model or imputation recipe.
3. Start with duration-weighted historical mean L/h times planned duration. Run only
   with confirmed training rates, their receipt times, purchase cutoff and plan. Rate
   times actual realized duration would be a retrospective comparison, not planning.
4. Integrate explicit interval-average L/h as
   `sum(rate_L_h * duration_h * density_kg_L / 1000)` tonnes. Specify period boundaries,
   interval convention and density conditions. Current utility deliberately rejects
   duplicate, overlapping, missing, mixed-unit and irregular intervals; it does not
   resample. An authorized irregular-interval protocol must be specified separately.
   Already-aggregated kL requires a separate verified volume contract, not this API.
5. Evaluate **port-to-port totals** using MAE, RMSE, signed bias (prediction minus
   actual), underprediction frequency and total shortfall in tonnes. Keep all failures
   and denominators. ROB conservation is a consistency check, not independent truth.
6. Procurement replay is a separate later evaluation requiring prices, decision times,
   supplies, opening ROB, reserve and tank constraints. Report cost, reserve breaches,
   capacity breaches and infeasibility separately, with full counts. No replay is run here.

## Relation to the new paper

DOI `10.1016/j.oceaneng.2026.126205` was supplied in the task. The DOI page could not
be retrieved in this environment. The following are **task-supplied interpretation,
not independently checked paper claims**: separate voyages in time; distinguish a
14-variable observed-condition consumption estimator from a future-voyage predictor;
do not copy the reported eight-voyage mean RMSE of 55.08 L/h as our target/result.
No paper model, dataset or published metric is reproduced by these tests.

## Readiness and checks

Possible now: private structural inspection, unit/time/provenance checks, synthetic
contract/conversion/split/preprocessing/metrics/ROB tests. Blocked: independent voyage
generalization, real planning baseline, density-based aligned mass evaluation and
procurement replay. Needed: complete voyage boundaries and multiple voyages, decision
and issue/receipt timestamps, planned durations, independently measured aligned fuel
targets, density reference conditions, and replay inputs listed above.

```bash
python -m pytest tests/test_voyage_demand_validation.py -q --strict-config --strict-markers -W error
```

All fixtures use invented dates/quantities and measure software behavior only. Tests
must never be described as vessel prediction or fuel-saving performance. Do not run
private exporter CLIs or commit private inputs, row-level predictions or identifying metadata.
