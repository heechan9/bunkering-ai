# Native-v4 integration validation follow-up

This follow-up is based on Draft PR #132 at `55b461a92ff26f3f0eaa820fbc52fa5108c195fa` and main `183ab3a684cc970315112c312cc52953bd02f6e1`.
The original implementation remains attributed as recorded in #132. These changes are Codex integration/validation edits, not new teammate contributions.

## Changes

- Reject nonfinite step fields, invalid action IDs, nonconsecutive step identifiers and invalid fuel/market domains.
- Require recorded seeds to match the declared inclusive config range.
- Reject post-refill reserve timing because the implemented audit evaluates pre-refill unclipped fuel.
- Reject linked output directories and output files before writes, including overwrite.
- Recognize input_proposed as a proposal, independently of owner_decision; pending proposals cannot freeze.
- Label all-episode final-fuel output and add separate legacy-arrived/strict-safe means and sample counts. Empty subsets remain null.
- Declare seeds 1-3 explicitly in copied smoke configs.

## Source handling and decisions

The actual three first-round submissions were checked against their transfer manifest. Originals remain outside the repository. Private role-labelled contract derivatives and exact source/status provenance are preserved separately; they are not published here. A partial proposal label is normalized only in a derivative, with its exact original retained in provenance. The domain Markdown does not supply adopted C01/C02/C05 rows.

The original implementation patch was not reapplied: its ledger/config/policies sources match the #132 base. The data-statistics submission's 12 paired rows match independent reconstruction. Its final-fuel print statement mixed a common-safe comparator population with an all-seed baseline population. A separate corrected derivative uses the same population on both sides; original submitted statistics and source remain unchanged.

All C01-C06 owner decisions and personal reviews remain pending. No contract adoption, new evaluation, training, model replay, manuscript change, main merge or deployment is included.

## Recorded verification before isolated CI-environment follow-up

Existing Windows Python 3.11 environment:

- Native discovery: 56 passed, 1 skipped; actual symbolic-link creation was unavailable (Windows privilege error 1314).
- Targeted environment/baseline/safety-accounting regression: 48 passed.
- Copied synthetic smoke: PASS, 9 episodes / 27 steps.
- Existing recorded ledger: PASS, 4,000 episodes / 100,520 steps, zero accounting and legacy-summary mismatches.
- All-policy common strict-safe n=0/1,000. Common-safe costs remain null. No savings or superiority claim follows.

The initial full regression could not collect three procurement modules because SciPy was absent. A separate incomplete run is not reported as passing. Isolated-environment follow-up results and exact commands belong in the new Draft PR validation section.

## Handoff

Isolated strict regression follow-up: Windows Python 3.12.15, NumPy 2.5.3, pandas 2.2.3, SciPy 1.17.0, Gymnasium 1.4.0, Torch 2.14.1+cpu and pytest 9.1.1; pip check passed. A separate test checkout preserved registered LF/Git-blob bytes without changing frozen inputs in the publication checkout. All seven follow-up files matched after newline normalization. Full repository pytest with CI strict options completed: **946 passed, 5 skipped, 38 subtests passed in 320.84s**. Four skips require POSIX named-pipe/device behavior and one requires Windows symbolic-link privilege. The private-bundle legacy-summary test passed. Existing package environment versions remained unchanged. Linux PR CI must be checked separately after publication.

Compare this seven-file follow-up with the implementation owner's second-round work before applying it; do not reimport or overwrite his work. Source/config/ledger changes are intentionally limited. Other previously identified terminal-valuation/completeness gaps remain outside this repair and require further review. A green test run does not resolve those gaps, personal reviews or pending owner decisions.

Original ZIPs, private source identities, evaluation datasets, weights, contact details and local machine paths are excluded from this publication. Full private evidence and reproducibility records remain in the separately delivered local bundle.
