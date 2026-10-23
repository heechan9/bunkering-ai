# Confirmed static-review fixes (2026-10-16)

This phase follows the prior28-case and full-suite records. The previous full
run remains779 passed,1 timing failure,4 skipped,32 subtests passed; it was not
rerun after these fixes and is not evidence of a green final full suite.
All existing evidence, expected fixture values and acceptance thresholds remain
unchanged. Changes are limited to this isolated research module.

Before changes, test_static_review.py had21 failed,4 passed (4.09s). Failures
confirmed all four review categories: ignored unit/tier/unsupported fields;
unavailable ports with price=None; unsafe ledger quantity vectors; and finite
fake LP successes that violated physical constraints. Some malformed vectors
were already rejected, explaining the4 initial passes. An exception instead
of a structured invalid ledger also counts as a failed input-validation test.
The initial16/terminal6/four10t legs/q=[0] counterexample was explicitly included.

Fixes:

- validate_contract checks synthetic_assumption/STATIC_KNOWN, supported top-level
  fields and per-kind call fields. Optional unit declarations must exactly equal
  USD/t,t,USD,h. Unsupported conversion, information tiers, extra fuel grades,
  lot sizes, terminal-minimum fields and tide-window fields raise ValueError.
  Missing time still returns NOT_COMPUTED_UNKNOWN_TIME; no implicit zero.
- Objective coefficients and purchase costing use procurement Case.prices,
  which normalizes unavailable-port None prices to0. Independent ledger costing
  avoids evaluating a price for q=0; positive unknown-price purchases are invalid.
- audit first requires a four-element vector matching the route/case vectors,
  numeric scalar quantities excluding booleans/strings, finite values and strict
  nonnegativity. Invalid vectors return valid=False without partial-voyage audit.
- Every support-matching LP candidate is checked by the independent sequential
  ledger before entering the candidate list. Physical invalidity, cost mismatch
  >1e-4USD, or time mismatch >1e-6h raises RuntimeError with audit classification.
  Shape/finiteness/negative-q LP guards remain in place. Injected finite successes
  cover terminal,supply,reserve,capacity and deadline violations.

After fixes, the original11 integration checks plus25 reproduction checks had
36 passed (1.42s). Then the unchanged28 frozen scenarios were made explicit
pytest regressions in test_frozen_cases.py, with one canonical-unit acceptance
check. Final targeted run:286 passed (5.34s):65 integration tests (11 previous,
25 reproductions,28 frozen cases,1 canonical-unit check),185 port_call_time tests,
36 unchanged procurement core/policy tests. No skip or warning filter was added.
This differs from the prior full suite, where the28 scenario loop ran separately.

Commands (existing Python3.11.16/SciPy1.17.0 venv, no installation):

```powershell
# cwd: task-5/bunkering-cost-time
python -m pytest research/cost_time_integration/test_static_review.py -q --strict-config --strict-markers -W error --tb=short --basetemp=../pytest-static-review-before --junitxml=../static-review-before.xml
python -m pytest research/cost_time_integration -q --strict-config --strict-markers -W error --tb=short --basetemp=../pytest-static-review-after --junitxml=../static-review-after.xml
python -m pytest research/cost_time_integration research/port_call_time tests/test_procurement_baseline_core.py tests/test_procurement_baseline_policies.py -q --strict-config --strict-markers -W error --tb=short --basetemp=../pytest-static-review-final --junitxml=../static-review-final.xml
```

Full interpreter path, environment, output, final source excerpts and raw-byte
SHA256 values are in the external static_review_report.txt. Earlier parent review
report and patches are preserved. No push, merge, deployment, research training,
original user-checkout write, or new whole-suite run was performed in this phase.
