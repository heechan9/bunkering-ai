# Matched archived safety audit

This additive report reanalyses the existing [400 saved simulator audit rows](../../results/diagnostics/safety_accounting/episodes.csv) using their [evaluation manifest](../../results/diagnostics/safety_accounting/manifest.json). It does not run or train a model, modify simulator termination, or change submitted papers. It does not establish paper submission, acceptance, mentor approval, real-vessel validation, or deployment status.

## Reproduce without model weights

From the repository root, using the existing Python test dependencies:

```sh
python scripts/report_matched_safety.py \
  --episodes results/diagnostics/safety_accounting/episodes.csv \
  --manifest results/diagnostics/safety_accounting/manifest.json \
  --output-dir /tmp/new-matched-safety-audit
python -m pytest -q tests/test_matched_safety.py tests/test_matched_safety_csv.py
```

Use a new output directory; existing outputs are not overwritten. CSV headers must contain exactly the safety-audit schema with no duplicates. Every record must have exactly that number of cells. Unknown/missing headers, extra/truncated cells, blank records, and invalid CSV quoting fail before any output directory is created. Header order and an optional UTF-8 BOM are supported. Blank unsafe cost values stay blank; zeros stay zero.

The module additionally checks plan coverage, duplicate cases, matching seed/episode/config, finite numeric values, safety flags, and inventory arithmetic. This is not a revalidation of actual trajectories or termination reasons, which are absent from the input audit schema.

## Scope and results

- Four policies, 100 evaluation cases each, one recorded DQN training seed (42).
- The web panel is a separate archived evaluation, not the current 700-record replay or selected checkpoint.
- All six policy pairs retain the entire matched safety contingency table.
- Cost differences are B minus A, conditional on both policies being safe. DQN versus Safe Stock has zero jointly safe cases, so cost comparison is null, not zero.
- Price Reactive (A) versus DQN (B) has 2/100 jointly safe cases. Their observed mean difference is +17,854.65 SCI. This is not a saving, a causal effect, or an overall policy cost effect. Post-policy outcome selection and potentially different subsets across pairs limit interpretation.
- Confidence intervals and p-values are withheld (null). Same seed/config verifies the plan, not identical exogenous trajectories or independent voyages/training repetitions. SCI is synthetic, not currency.

The [web summary](../../web/ocean-lab/lib/matched-safety-report.json) omits pair-level records; the [downloadable report](../../web/ocean-lab/public/data/matched-safety-report.json) retains them and source SHA-256 values. The Python source-reproduction test compares the computed report with the published JSON. The UI check compares full/summary data and renders Korean and English scope warnings.

## Verification boundaries

The initial implementation had 25 new Python tests plus 26 inherited contract/safety tests passing locally and on independent rerun. PR #141 at `e82da8bfff25cfd39e785879340b7137326f4875` passed both existing GitHub workflows. The subsequent CSV-reader correction has dedicated malformed-record and no-output regression tests; CI must be checked on its own head.

The original UI typecheck, regression scripts, SSR checks, and production build passed locally. The correction does not change UI code or stored evaluation data. Local build/SSR is not hosted-browser, mobile Safari, visual-layout, or deployed-preview verification. Existing CI workflows do not run the Node production build and do not create a preview. No merge or production deployment is performed by this audit.
