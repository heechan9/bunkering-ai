# Native market round-2 integration review — 2026-10-26

**Separate review candidate on #144. No merge, deployment, submission or adoption.**

## Immutable inputs and provenance

The user-supplied second-round ZIP SHA-256 is
`733a0584282e8c9d04d2960adeaca857f248a0d3aa61d74944e27acce9c1daf2`.
It matches the received bytes; all 72 entries in FILE_MANIFEST.json match their
registered sizes/hashes. The uploaded ZIP and extracted source evidence remain
unchanged. These integrity checks do not certify that every claimed run occurred.

Direct remote checks found:

- main `34e1e82ce10309ba737572fdae24625e4bc722a7` (unchanged).
- #144 open Draft, head `805ff96f83862a9ce1181752cf1812fa92dd2f7f`,
  based on #136 `40100e398efb15f44cf9a032bf000cf519a6fa87` (unchanged).
- Submitted round2_changes.patch is an uncommitted seven-file delta against
  `40100e3`, not a main patch or an existing integration commit.

The patch was first materialized on a separate #136 copy, then the code changes
were applied with three-way context onto a new #144 worktree. The README was
reconciled manually to retain #144's cohort/draft guidance, remove an obsolete
unconditional INCOMPLETE statement and identify Windows results as submitted
logs. A personal name in a synthetic UTF-8 test note was replaced with a role-neutral
note. Codex added one coherent forged-price/FX regression (two parameter cases).

Submitted implementation, environment setup and submitted runs are attributed by
the package to **Claude Code, submitted through Hyeonsu**, with personal review
still blank. Integration, additional regression and direct checks here: **Codex**.
This record is not Claude's separate logic audit or a teammate's personal approval.

## Preserved #144 work and contract state

The following remain byte-identical to #144: ledger.py (including paired_final_fuel
and the shared cohort generator), contracts.py, native config, domain input draft,
and the earlier C01–C06 reflection document. The CLI retains paired_final_fuel.csv.
No historical received contract, model, official evaluation result or manuscript
is replaced. No private CSV/model/original ZIP/raw PC log is published.

The [earlier reflection table](native_contract_integration_20261026.md) records the
pre-receipt evidence state. This new document updates only the evidence available
for the round-2 code: the ZIP/patch and submitted logs now exist. It does not turn
C06 into accepted, nor confirm C01/C02/C05 physical inputs or C03/C04 personal review.
All C01–C06 decisions remain pending; the contract version remains draft.
Original human_review.md checkboxes and independent_review.md not-run fields are
not edited. Codex results belong in this separate dated record, not in those
original blank author confirmation fields.

## Regenerated stream and indexing

market_tape.regenerate builds a tape from **seed and fixed algorithm/constants**:
NumPy Generator(PCG64(SeedSequence(seed))); initial independent price/FX normal
draws, then price followed by FX at every transition, with pinned clipping bounds.
It does not load recorded price/FX values or import the environment to obtain its
expected values. Config validation permits only pinned native constants and
native-legacy-v3; new/misspelled nested fields are rejected. This is numerical
reproduction of the pinned synthetic generator, not a real-market price oracle.

| Point | Tape index | Independently regenerated comparison |
|---|---|---|
| Reset / initial stock | 0 | initial value = 1.0 × P0 × FX0 |
| Step k purchase snapshot | k−1 | decision_price and decision_fx; q × P(k−1) × FX(k−1) checked by step audit |
| End of episode after T transitions | T | terminal value = final_fuel × PT × FXT |

The environment advances price/FX inside the transition, but purchase cost uses
its pre-transition frozen decision snapshot. End value uses the post-transition
market even when that transition ends the episode. Independent step accounting
checks fuel transitions and recorded final fuel; the tape check alone does not.
The four reused-source pins match. This fixed native consume-before-refill
contract is separate from U01 tonnes/dollars/purchase-before-consumption.

PASS/0 requires both `--steps` and `--regenerate-market`, with clean accounting,
regenerated markets and any supplied legacy-summary comparison. Without the flag,
clean accounting stays INCOMPLETE/3. With regeneration but no steps it also stays
INCOMPLETE/3 because purchases/fuel traces have not been checked. Mismatches produce
FAIL/1, and handled input/config errors produce exit 2. Contract adoption is always
`not_established_by_ledger`. PASS is recorded numerical/accounting verification,
not policy superiority, real-vessel safety, cost savings, member approval or C05
methodological adoption.

## Negative cases, separate from original recorded runs

Direct tests cover:

- Terminal value +100 and inventory-adjusted SCI −100: identity-only accounting
  remains clean; regeneration reports regenerated_terminal_value and FAIL.
- Balanced initial-value/SCI shift: regenerated initial value detects the edit.
- Same foreign price for every policy: cross-policy agreement alone is
  insufficient; the regenerated decision market detects it.
- Added integration test: scale only decision price, or only FX, and coherently
  scale all affected episode purchase/initial/terminal/adjusted values. The older
  step/accounting checks remain PASS (overall INCOMPLETE/3), but regenerated
  initial/terminal/decision checks fail (FAIL/1). This demonstrates that the new
  stream check is not merely accepting coherent recorded values as its oracle.
- Existing and submitted config regressions reject altered native constants,
  wrong units, wrong seed declarations and nested unknown/missing keys.
- #144 paired-final-fuel tests retain equal seed cohorts and both null at n=0.

All mutations were made in temporary synthetic copies, never original data.

## Evidence levels: submitted logs versus direct execution

| Evidence | What it establishes here | What it does not establish |
|---|---|---|
| Submitted native logs | 78 passed, 90 pytest subtests, BAI_EVAL_ROOT set, no skips reported | Codex rerun or personal Hyeonsu review |
| Submitted UTF-8 full-suite log | 966 passed, 6 skips, 122 subtests | Current candidate full-suite execution |
| Submitted locale full-suite log | 962 passed, 4 cp949 failures, 6 skips | A same-environment full-suite comparison against unchanged base |
| Submitted 91M logs/manifests | Original/replayed 4,000 episodes / 100,520 steps reported PASS/0 | Codex rerun of those raw CSVs or model inference |
| Submitted 60M logs/manifests | Development 4,000 episodes / 100,470 steps reported PASS/0 | New frozen/unseen evaluation or Codex raw-record replay |

The six submitted full-suite skips are four Windows POSIX special-file tests and
two missing-BAI_EVAL_ROOT comparisons. Native-only submission runs did set that
variable. These scopes are not interchangeable. The old chat count of 77 is
superseded by these dated package logs, without converting them into independent
execution.

Both submitted JUnit XMLs are not well-formed: privacy placeholders such as
`<scratch>` were inserted unescaped into text nodes. Originals remain unchanged.
Escaping only those known placeholders in memory allows a derived parse of the
reported four failures/six skips; that derivative is not the original valid XML.
Text log footers corroborate the reported counts. The locale/UTF-8 modified-code
pair supports an encoding trigger for those four submitted failures, but the ZIP
has no equivalent unchanged-base full-suite log. Do not claim that comparison was
provided or proved here.

## Direct Codex results

Direct commands use one task-local environment; no repository dependency pin was
changed. BAI_EVAL_ROOT was **unset** throughout this integration. The raw original
45-file evaluation bundle/model and raw 60M episode/step CSVs are absent from the
submission and were not obtained from the inspected project folders. No full
neural-network replay or original raw-record 91M/60M audit is claimed.

1. Native pytest, before full-suite environment setup: **81 passed / 2 skipped /
   92 subtests**. The two skips require the original BAI_EVAL_ROOT: legacy summary
   and regenerated-market raw-bundle comparison. All synthetic market tests run.
2. Fixed source equivalence: **2,000 seeds, 60,000 transitions** across the 91M and
   60M ranges; regenerated P/FX exactly equals the environment stream at reset
   and every index with varied actions. This is synthetic source equivalence,
   not raw recorded data or model evaluation.
3. A separate check used the previously submitted first-round 4,000-row ledger
   converted explicitly into derived episode input, not recovered raw episodes.
   Regenerated initial/terminal values matched 1,000 seeds with zero mismatches.
   With no steps, the CLI correctly returned **INCOMPLETE/3**, steps_checked=0.
4. Initial same-environment full suites used PYTHONPATH-only dependencies: base
   #144 **961 passed / 4 failed / 1 skipped / 110 subtests**; candidate **971 passed /
   4 failed / 2 skipped / 124 subtests**. All four identical failures were in the
   POSIX special-file subprocess tests: those tests replace PYTHONPATH, leaving
   their child interpreter unable to import task-local gymnasium. This is a
   directly observed base/candidate environment limitation, distinct from the
   submitted Windows cp949 problem. A task-local venv with a dependency .pth
   makes the same dependencies visible to child interpreters; all four focused
   checks then passed, with no repository change.
5. Final same-environment full suites after the environment-only correction:
   base #144 **965 passed / 1 skipped / 110 subtests** (104.51 s);
   candidate **975 passed / 2 skipped / 124 subtests** (106.24 s), zero failures.
   Python 3.12.14, NumPy 2.5.4, PyTorch 2.14.1+cpu, Gymnasium 1.4.0,
   pytest 9.1.1, UTF-8. Both candidate skips are missing BAI_EVAL_ROOT; the base
   has only the pre-existing summary comparison skip. These local versions are
   recorded rather than represented as an exact reproduction of the submitted
   Windows environment or every hosted CI pin.
6. All **five #144 data CSVs**, including paired_final_fuel.csv, are byte-identical
   on the derived first-round input before/after integration. Four reused-source
   pins and git diff whitespace checks pass. Uploaded ZIP hash remains unchanged.

```bash
# From each checkout; PY is the same task-local venv interpreter.
PYTHONUTF8=1 MPLBACKEND=Agg PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$PY" -m pytest -q --strict-config --strict-markers -W error \
  -p no:cacheprovider --junitxml=<separate-results.xml>
"$PY" research/native_v4_integration/cli.py verify-source \
  --source-verification research/native_v4_integration/fixtures/pinned_source_blobs.json
git diff --check
```

## Numerical impact and remaining conditions

Legacy ledger, SCI pair summaries and per-policy summaries are not recalculated
under new physical settings. #144 final-fuel means and null conventions remain
unchanged. All-policy common strict-safe **0/1000** and DDQN–Price Reactive pair
common-safe **33/1000** refer to different intersections. The latter's final-fuel
mean about 0.632 is a tank fraction, not savings. No performance claim follows.

Still needed: raw evaluation inputs for independent original 91M/60M validation;
Hyeonsu's explicit personal review; the separate logic audit; missing domain and
statistics-owner confirmations; Heechan's individual C01–C06 adoption decisions;
publication/hosted CI review. No C01 candidate policy, native constant, model,
new seed contract or report approval is adopted by this change.
