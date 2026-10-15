# Synthetic fixed-route procurement baseline

This isolated research module compares a static LP/MILP purchasing optimum with three prespecified rules. It uses **tonnes (t) and USD**, a fixed route, one fuel grade, identical terminal inventory, per-call supply limits, minimum lifts, and monetary fixed/variable fees. Mass inputs must lie on a 0.001 t grid and tank capacity must be at most 1,000 t; purchase decision variables remain continuous.

It does not replace `research/ntnu_bunkering`, the official normalized SCI environment, DQN models, manuscript, or web UI. This is a 120-case **synthetic development comparison with full static information**, not AI superiority, realized vessel savings, reproduction of the De paper, or an unused holdout evaluation.

## Preserved evidence and solver correction

The reviewed user-downloaded input ZIP is preserved unchanged at `provenance/reviewed_bundle.zip` (258,193 bytes; SHA-256 `863b074677d43e6aae774f13cde77a02eb145f682fb98142732b4a25f5b6d923`). `provenance/integration_manifest.json` records the integration baseline and exact-copy hashes. `handoff/` retains the supplied reports, all 120 cases/results, preregistration records, original solver outputs, first-run results, and independent review. Its `SHA256SUMS.txt` describes the original ZIP members; the full archive includes the source/test members that are not duplicated in `handoff/`.

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
python -m research.procurement_baseline.generate_report --input-dir PATH_TO_NEW_RUN
python -m pytest -q --strict-config --strict-markers -W error
```

The benchmark stores the specification and **every generated input before solving**. It runs all cases without exclusion or resampling, saves all policy failures, and checks the optimizer against independent stop-pattern enumeration. Output directories must be new; existing directories are rejected. Diagnostics/report generation reject an existing output file. Archived evidence is never used as the default output location. `audit_results` accepts `--spec research/procurement_baseline/spec.json` when auditing the first integration run, which predates the additional copied-spec output file. These commands use package imports; no cloud filesystem path or `sys.path` mutation is required.

## Reproduced results and boundaries

The seed 20261015 generates three blocks of 40 cases each. Reference status: **86 optimal, 34 infeasible, no unresolved/error/contradiction results**. Policy feasible counts: minimum required 75, next cheaper 79, departure concentrated 79. Among the 86 proven feasible cases, policy failure counts are 11/7/7; failure on an infeasible problem is reported separately.

All-policy common feasible denominator: **75 cases**, optimum total **1,750,550 USD**.

| Rule | Rule total on common 75 (USD) | Optimum total (USD) | Cost-weighted difference |
|---|---:|---:|---:|
| Minimum required | 2,294,200 | 1,750,550 | 23.6967% |
| Next cheaper | 1,755,430 | 1,750,550 | 0.2780% |
| Departure concentrated | 2,148,450 | 1,750,550 | 18.5203% |

Difference = `sum(rule cost − optimum cost) / sum(rule cost) × 100`. The separate pairwise denominators are 75/79/79; their rates must not be used interchangeably with the common-75 rates. In the fee-free, unlimited-supply block, next-cheaper matched the optimum on all 34 feasible cases. A constrained mathematical optimum being no worse than feasible rules is expected by construction and is not evidence of AI benefit. Failed policies are not repaired by the solver, and failed-ledger costs do not enter feasible-cost aggregates.

Results in [validation/windows_20261015](validation/windows_20261015/) are local integration evidence. The handoff and development cases have already been used to identify and fix the solver counterexample; they are not independent future confirmation data. No real prices, operational records, private identifiers, forecasts, route optimization, multi-grade contracts, quality/tax/credit constraints, or causal realized-savings evaluation are included.

See [LOCAL_INTEGRATION.md](LOCAL_INTEGRATION.md) for the initial local integration checks, failed baseline attempts, and environment differences. The subsequent approved Windows fixes and current validation status are recorded in [WINDOWS_COMPATIBILITY.md](WINDOWS_COMPATIBILITY.md). This branch is prepared for Draft PR review; no model replacement, merge, or web deployment is included.
