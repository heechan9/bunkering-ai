# Synthetic fixed-route procurement baseline

This isolated research module compares a static LP/MILP purchasing optimum with three prespecified rules. It uses **tonnes (t) and USD**, a fixed route, one fuel grade, identical terminal inventory, per-call supply limits, minimum lifts, and monetary fixed/variable fees. Mass inputs must lie on a 0.001 t grid and tank capacity must be at most 1,000 t; purchase decision variables remain continuous.

It does not replace `research/ntnu_bunkering`, the official normalized SCI environment, DQN models, manuscript, or web UI. This is a 120-case **synthetic development comparison with full static information**, not AI superiority, realized vessel savings, reproduction of the De paper, or an unused holdout evaluation.

## Preserved evidence and solver correction

The reviewed user-downloaded input ZIP is preserved unchanged at `provenance/reviewed_bundle.zip` (258,193 bytes; SHA-256 `863b074677d43e6aae774f13cde77a02eb145f682fb98142732b4a25f5b6d923`). `provenance/integration_manifest.json` records the integration baseline and exact-copy hashes. The full cases/results, preregistration, original solver outputs, first-run records, independent review, and SHA256SUMS.txt are members of that committed ZIP. Only selected supplied reports and summaries are duplicated under `handoff/` in a fresh checkout; the expanded full handoff on the integration laptop is ignored and is not required.

`reference_original.py` is a byte-identical copy of the supplied original solver; `procurement.py` is a byte-identical copy of the reviewed patched solver. The only solver correction relative to the original is `presolve=False` in **both** MILP calls. Objective, constraints, tolerances, and policy rules are unchanged. Read [PATCH_NOTES_KO.md](PATCH_NOTES_KO.md), [ALGORITHMS_KO.md](ALGORITHMS_KO.md), and the [supplied report](handoff/REPORT_KO.md).

The original solver incorrectly declared `monetary_fees_010` infeasible. Its feasible optimum is 13,000 USD with purchases `[1, 10, 15]` t, verified independently by stop-pattern enumeration with explicit inventory LPs and a sequential ledger. The false infeasibility was reproduced on this Windows run. Disabling presolve is an environment-tested workaround; it does not establish the complete internal solver cause or guarantee all other versions/platforms.

## Run from the repository root

Use an isolated Python environment with NumPy, SciPy, and pytest. The supplied run used Python 3.12.14 / NumPy 2.3.5 / SciPy 1.17.0. The local Windows integration uses Python 3.11.16 / NumPy 2.4.6 / SciPy 1.17.0, with actual details in each run's `environment.json`. Existing project dependencies are needed for the whole-suite tests; the procurement solver itself needs only NumPy/SciPy.

```bash
python -m pytest tests/test_procurement_baseline_core.py tests/test_procurement_baseline_policies.py -q --strict-config --strict-markers -W error
python -m research.procurement_baseline.benchmark --output-dir PATH_TO_NEW_RUN
python -m research.procurement_baseline.audit_results --input-dir PATH_TO_NEW_RUN --output-dir PATH_TO_NEW_AUDIT
python -m research.procurement_baseline.verify_handoff --input-dir PATH_TO_NEW_RUN --output PATH_TO_NEW_COMPARISON.json
python -m research.procurement_baseline.diagnose_solver --output PATH_TO_NEW_DIAGNOSTIC.json
python -m research.procurement_baseline.generate_report --input-dir PATH_TO_NEW_RUN --audit PATH_TO_NEW_AUDIT/independent_checks.json
python -m pytest -q --strict-config --strict-markers -W error
```

The benchmark stores the specification and **every generated input before solving**. It runs all cases without exclusion or resampling, saves all policy failures, and checks the optimizer against independent stop-pattern enumeration. Output directories must be new; existing directories are rejected. Diagnostics/report generation reject an existing output file. Archived evidence is never used as the default output location. `audit_results` accepts `--spec research/procurement_baseline/spec.json` when auditing the first integration run, which predates the additional copied-spec output file. These commands use package imports; no cloud filesystem path or `sys.path` mutation is required.

The generated report derives every count and policy metric from the supplied summary. Without `--audit`, it explicitly marks verification as UNVERIFIED. A supplied audit must report PASS and contain the exact complete summary; missing, failed, stale, or mismatched evidence is rejected before writing. The report does not independently certify enumeration agreement. The default report filename remains `REPORT_KO.md` for CLI compatibility; newly generated reports use English, while supplied Korean evidence is preserved unchanged.

## Reproduced results and boundaries

`verify_handoff` reads the committed reviewed ZIP directly, so no expanded local-only handoff files are required in a fresh checkout.

The seed 20261015 generates three blocks of 40 cases each. Reference status: **86 optimal, 34 infeasible, no unresolved/error/contradiction results**. Policy feasible counts: minimum required 75, next cheaper 79, departure concentrated 79. Among the 86 proven feasible cases, policy failure counts are 11/7/7; failure on an infeasible problem is reported separately.

All-policy common feasible denominator: **75 cases**, optimum total **1,750,550 USD**.

| Rule | Rule total on common 75 (USD) | Optimum total (USD) | Cost-weighted difference |
|---|---:|---:|---:|
| Minimum required | 2,294,200 | 1,750,550 | 23.6967% |
| Next cheaper | 1,755,430 | 1,750,550 | 0.2780% |
| Departure concentrated | 2,148,450 | 1,750,550 | 18.5203% |

Difference = `sum(rule cost − optimum cost) / sum(rule cost) × 100`. The separate pairwise denominators are 75/79/79; their rates must not be used interchangeably with the common-75 rates. In the fee-free, unlimited-supply block, next-cheaper matched the optimum on all 34 feasible cases. A constrained mathematical optimum being no worse than feasible rules is expected by construction and is not evidence of AI benefit. Failed policies are not repaired by the solver, and failed-ledger costs do not enter feasible-cost aggregates.

`validation/windows_20261015/` is an ignored, local-only integration output directory, absent from a fresh checkout. Committed validation summaries are in WINDOWS_COMPATIBILITY.md, WINDOWS_STRICT_RESULT.txt, and verification_summary.json; full reviewed source evidence is in the ZIP. The handoff and development cases have already been used to identify and fix the solver counterexample; they are not independent future confirmation data. No real prices, operational records, private identifiers, forecasts, route optimization, multi-grade contracts, quality/tax/credit constraints, or causal realized-savings evaluation are included.

See [LOCAL_INTEGRATION.md](LOCAL_INTEGRATION.md) for the initial local integration checks, failed baseline attempts, and environment differences. The subsequent approved Windows fixes and current validation status are recorded in [WINDOWS_COMPATIBILITY.md](WINDOWS_COMPATIBILITY.md). This branch is prepared for Draft PR review; no model replacement, merge, or web deployment is included.

## Admission gate for a future fixed-route rule / optimizer / RL comparison

2026-10-30: **research protocol only**, not a new benchmark, RL implementation or
result. The user-supplied Europe semiconductor career lecture (19 pages, pp. 5,
9 and 12) motivates attention to collaboration, efficiency and field outcomes.
The following comparison design is our proposal, not validation by that lecture;
none of its industrial savings figures is a Bunkering result. Preserve the
official submission baseline, manuscript/HWP, checkpoints and archived results.

Fixed route does not by itself make methods comparable. Reuse the existing
[specification](spec.json), [rule definitions](ALGORITHMS_KO.md) and
[same-information evaluation design](../fair_replacement_eval/README.md), rather
than introducing a second set of thresholds or a new result table.

| Gate before ranking methods | Required record / stop condition |
|---|---|
| Same task and inputs | Pin ordered port/leg IDs, demand, prices, availability, supply, minimum lift, fees, reserve, capacity, initial/terminal inventory, units and input hashes. Keep route and speed assumptions fixed; do not credit route optimization that is absent. |
| Same information and actions | This module gives rules and LP/MILP full static information and continuous purchase quantities. It has no RL policy. Do not rank these results against the native discrete-action DQN with different action semantics. A future RL adapter needs a separately reviewed contract with the same available information, observation timing and feasible actions. An oracle or extra forecast is an information-bound experiment, not a same-information winner. |
| Same safety clock | Identify inventory before purchase, after purchase and after leg consumption; record which state each reserve constraint checks. This module purchases before the leg, whereas native reproduction consumes before refilling. Do not silently relabel phases or let a later purchase erase an earlier reserve violation. |
| Same terminal treatment | Keep this module's exact terminal inventory equality for every method. Native inventory-adjusted SCI uses terminal valuation instead; equal-target USD costs and mark-to-market SCI cannot be pooled. Any changed terminal target/valuation needs its own version, not relabelled historical results. |
| Same constraints and failure accounting | Apply supply, minimum-lift, capacity, intermediate reserve and terminal constraints to every policy. Keep the prespecified clipping rules; do not repair a failed policy with an optimizer. New guards are separate policies. Missing time/queue/quality constraints are unmodelled, not zero or satisfied. |
| Same evidence budget | Freeze scenario roles, development/confirmation history, seeds and evaluation criteria before a new run. Record training/search effort separately from decision runtime and use the same runtime measurement environment. This protocol schedules no training or evaluation. |

### Failure-first review, using existing cases

Report all cases and status counts before jointly feasible cost differences.
Retain pairwise and all-policy common denominators separately. A cheap failed
voyage is not efficient; an empty eligible cohort is undefined, not zero savings.
An optimal reference is a mathematical comparator, not evidence of realized
cost reduction, safer vessels or RL benefit.

| Review question | Existing regression evidence to reuse |
|---|---|
| Are unknown inputs distinct from impossible routes? | [Core tests](../../tests/test_procurement_baseline_core.py): `test_U13_unknown_price` (`NOT_READY`), `test_unit_scope_rejection` (`INVALID_INPUT`), `test_U07` / `test_U11` (`INFEASIBLE`). |
| Is a solver time/iteration limit being called infeasible? | Same file: `test_U17_statuses` distinguishes `LIMIT_REACHED`, `INFEASIBLE` and `SOLVER_ERROR`. Preserve unresolved/audit/lexicographic failures; do not force them into success or infeasibility. |
| Does a feasible problem expose a policy limitation? | [Policy tests](../../tests/test_procurement_baseline_policies.py): `test_minimum_lift_failure` retains `POLICY_FAILURE` while the reference is `OPTIMAL`; `test_unavoidable_infeasible` is a different case. |
| Are supply gaps, intermediate reserve and terminal inventory respected? | Same file: `test_supply_gap`, `test_intermediate_reserve`, `test_terminal_caps_purchase` and `test_zero_purchase`. Preserve the first violated constraint and the complete ledger, not cost alone. |
| Does the reference itself need independent checking? | `test_presolve_counterexample_regression` and core `test_U15_enumeration`; use the existing audit rather than treating a solver label as sufficient proof. |

These are existing synthetic regression cases, not newly executed performance
experiments. A file/test name is not proof of execution. For a small reproducible
code check without model weights or the full benchmark, run from the repo root:

```bash
python -m unittest -v tests.test_procurement_baseline_core tests.test_procurement_baseline_policies
```

### English handoff: add only the comparison-specific fields

Reuse the [English reproduction/review receipt](../../docs/technical/DATA_ANALYSIS_REVIEW_CHECKLIST.md#english-reproduction--review-receipt)
for code SHA, input hashes, environment, seeds, command, log, exit code and human
review. Add the fields below; blank/unexecuted fields remain pending. Do not
publish private paths or data. A receiving reviewer should be able to identify
the same inputs, outputs and expected failure without guessing the model scope.

```text
Comparison scope: static t/USD procurement | native normalized SCI | other (separate)
Route/leg order / information tier / action contract / reserve-check phase:
Terminal inventory target or valuation rule / unmodelled operational constraints:
Input artifacts and hashes -> output files, units and eligible-cohort definition:
Known-failure case ID / expected input-reference-policy statuses / actual result:
Reproduction status: not run | regression only | saved-result audit | new evaluation
Implementation author / execution author / independent reviewer / unresolved question:
```

Acceptance is a reviewable protocol and an accurately scoped receipt, not a
cost-only ranking. Any later execution or claim change needs separate approval;
this documentation does not adopt native C01-C06 or change `spec.json`.
