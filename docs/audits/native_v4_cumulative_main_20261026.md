# Native-v4 cumulative main-target integration review — 2026-10-26

## Scope and immutable sources

This is a separate Draft review candidate, not a main merge, deployment, final
submission or contract adoption. Original PRs, branches, source packages and
private evidence are preserved. No history rewrite, PR closure or retargeting.

- Latest main: `34e1e82ce10309ba737572fdae24625e4bc722a7`.
- Stack tip #145: `0ac21d636037c02549fb06a49f12ab434e0caa1c`.
- Common ancestor: `183ab3a684cc970315112c312cc52953bd02f6e1`.
- Preserved stack: #132 `55b461a` → #133 `0f96511` → #134 `732b25e`
  → #136 `40100e3` → #144 `805ff96` → #145 `0ac21d6`.

The two heads each contain ten commits after the common ancestor. A local
no-commit integration was conflict-free. The cumulative native stack adds 32
files / 3,079 lines relative to current main; no main files are deleted. Current
main's U01 procurement example, replay-load handling and other web changes remain
unchanged. Native code/constants/models and evaluation source outside the new
native-v4 directory are unchanged. The four reused-source pins pass.

## Necessary integration follow-up

A read-only cumulative review found a genuine additional input-validation gap:
legacy summary NaN mean/CI bypassed `abs(reference - expected) > tolerance`,
reporting `checked_match` and PASS even though the supplied comparison was not
valid. This was reproduced through the CLI with synthetic inputs before editing.
Episode/step finite guards did not cover this separate JSON input.

The new integration-only guard rejects nonfinite or invalid-type legacy values
and invalid counts with InputError/exit 2. It preserves optional summary, normal
comparison, nullable small/empty cohorts and the three legacy_summary_status
states. Two tests add sixteen subcases for NaN/infinities, invalid count/type and
missing required numeric values. No policy, paired cohort, SCI formula or
contract value is changed. Original #145 is untouched.

The project-status header now distinguishes historical INCOMPLETE statements
from current conditional PASS behavior. Dated original audit records remain
unchanged; this document supplements, rather than relabels, their evidence.
In particular, the original round-2 integration task did not obtain raw records;
its "not rerun here" remains true for that task. The new direct checks below are
separate Codex execution on this cumulative candidate, not retroactive evidence
for every historical head. See [historical local scope](../../research/native_v4_integration/LOCAL_INTEGRATION_20261020.md)
and [dated C01-C06 reflection](native_contract_integration_20261026.md).

## Direct validation of this candidate

Commands use a task-local Python 3.12.14 venv with repository requirements-ci.txt
pins (NumPy 2.5.3, Gymnasium 1.4.0, pytest 9.1.1) and torch 2.14.1+cpu.
`pip check` reports no broken requirements. No dependency file was edited.

- Conflict-free initial cumulative tree, before the legacy guard: full suite
  **983 passed / 2 skipped / 124 subtests**, 104.55 seconds.
- Final native suite: **86 passed / 2 skipped / 108 subtests**, 0.58 seconds.
- Final full suite: **985 passed / 2 skipped / 140 subtests**, 111.01 seconds.
  This is the cumulative latest-main tree, not #145-only CI.
- Four fixed source blobs match; whitespace checks pass.
- Both private recorded sets were checked directly on the final local code:
  91M **4,000 episodes / 100,520 steps** and 60M development **4,000 / 100,470**,
  each PASS/0, 1,000 regenerated seeds, zero accounting/legacy mismatches,
  `legacy_summary_status=checked_match`.
- Five data CSVs per recorded set are byte-identical before/after the guard.
  Inputs and outputs remain outside the repository. No model inference or
  checkpoint loading occurred. 60M uses its separate recorded seed-range config;
  91M is used reproduction data, neither is a new unseen evaluation claim.

Full-suite commands leave BAI_EVAL_ROOT unset. The two skipped tests require
private raw bundles; direct CLI recorded-data checks above are reported
separately, not counted as skipped tests executed. Hosted CI results will be
reported on the published immutable head, not preclaimed in this file.

```sh
PYTHONUTF8=1 MPLBACKEND=Agg PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$PY" -m pytest -q --strict-config --strict-markers -W error \
  -p no:cacheprovider --junitxml=<external-evidence>/pytest_final.xml
"$PY" research/native_v4_integration/cli.py verify-source \
  --source-verification research/native_v4_integration/fixtures/pinned_source_blobs.json
```

The 60M config is an external copy of the checked-in native config with only
`integration.seed_range_inclusive.value` changed to `[60000000, 60000999]`;
`seed_status=used_reproduction_set` and all pending decisions are retained.
The following placeholders identify private local inputs, not public uploads:

```sh
"$PY" research/native_v4_integration/cli.py ledger \
  --config research/native_v4_integration/config/bai_v4_native.json \
  --episodes "$PRIVATE_EVAL/results/episodes.csv" \
  --steps "$PRIVATE_EVAL/results/steps.csv" \
  --legacy-summary "$PRIVATE_EVAL/results/summary.json" \
  --regenerate-market --out-dir "$PRIVATE_OUTPUT/final91M"
"$PY" research/native_v4_integration/cli.py ledger \
  --config "$PRIVATE_CONFIG/config60M.json" \
  --episodes "$PRIVATE_EVAL/development_run/results/episodes.csv" \
  --steps "$PRIVATE_EVAL/development_run/results/steps.csv" \
  --legacy-summary "$PRIVATE_EVAL/development_run/results/summary.json" \
  --regenerate-market --out-dir "$PRIVATE_OUTPUT/final60M"
```

## Attribution, privacy and remaining decisions

Requirements/planning: Heechan, including preparation of this cumulative Draft
without merging/deploying. Submitted implementation and submitted execution:
Claude draft/Claude Code through Hyeonsu, as recorded in the original audits;
submission is not personal review. Earlier integration/repairs: original commits
and audit records retain their attribution. This cumulative integration,
independent review, legacy-summary guard/tests and direct local checks: Codex.
Commit Author/Committer must follow CONTRIBUTIONS.md approval before creation.
No human review fields or approvals are fabricated.

C01–C06 remain pending. The prepared domain input draft is not an owner decision.
All-policy common strict-safe 0/1000 and DDQN–PR pair common-safe 33/1000 are
separate cohorts. Final fuel is a tank fraction, SCI is synthetic, and PASS means
recorded numerical checks, not savings, model superiority, real-vessel safety or
C05 methodological adoption. Human review and report acceptance remain separate.

No private raw CSV, model, ZIP, local paths, secrets or raw private logs are added.
New public CSVs in the stack are small synthetic fixtures and contract templates.
The tool is not a general untrusted-file service: some malformed JSON/schema
errors can still raise uncaught exceptions; direct market_tape API assumes
prevalidated input. Existing documentation explains those limits. A finite
legacy comparison does not establish authenticity of its upstream source.
