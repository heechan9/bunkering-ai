# Native-v4 validation follow-up, 2026-10-20

This change is stacked on Draft PR #133 at `0f96511b4b277a8d69236b3d7d4cce888cced882`, which includes Draft PR #132 at `55b461a92ff26f3f0eaa820fbc52fa5108c195fa`. Checked main remains `183ab3a684cc970315112c312cc52953bd02f6e1`. The follow-up does not reimport the native-v4 implementation or merge either parent PR.

## Behavior

- Reject nonfinite, fractional or nonpositive max_steps/n_ports; reject malformed, boolean or negative seed bounds.
- Reject unsupported policy versions and changed constants mislabeled as pinned native-legacy-v3 reproduction. Alternative domain assumptions need a separately versioned implementation.
- Clean ledger accounting returns `status=INCOMPLETE`, exit 3, with `accounting_status=PASS` and explicit step/terminal/adoption scope. An accounting mismatch remains FAIL/1; invalid input/output protection remains exit 2. Other subcommands retain their exit codes.
- Terminal market price/FX is not independently established by a balanced accounting identity or a matching legacy aggregate. A copied episode with terminal value +100 and adjusted SCI -100 cannot receive overall PASS. This limits the validator's claim; it does not implement independent terminal valuation.

## Direct validation

Existing Windows Python 3.11.16, NumPy 2.4.6, Torch 2.13.0+cpu, Gymnasium 1.3.0 and pytest 9.1.1; no installation. `pip check` passed.

`python -m pytest research/native_v4_integration -q -rs --strict-config --strict-markers -W error` with separate temporary/output paths and the existing private bundle: **61 passed, 1 skipped, 31 subtests passed**. The skip is actual Windows symlink creation being unavailable (privilege error 1314). Hardlink input preservation and the private legacy-summary comparison passed. Full repository regression and model inference replay were not performed in this follow-up; hosted CI must be checked separately.

- Synthetic smoke: 9 episodes / 27 steps; zero accounting mismatches; overall INCOMPLETE/3.
- Existing recorded ledger: 4,000 episodes / 100,520 steps; zero accounting or legacy-summary mismatches; overall INCOMPLETE/3. This is recorded-data checking, not inference replay or a new ML evaluation.
- All-policy common strict-safe n=0/1,000; empty costs remain null. No savings/superiority claim follows.
- Original 45-file bundle matched its registered hashes and remained unchanged before/after; four pinned source blobs passed verification with checkout newline handling.
- Pending contracts merged as pending and freeze was refused. No C01-C06 input or owner decision was invented.
- Direct before/after probes showed n_ports=Inf, max_steps=1.5, n_ports=4 and reserve=0.2 were accepted by the parent config and rejected by this follow-up.

## Attribution and remaining work

Requirements/Planning: user-authorized v4 integration and validation scope. Implementation/AI-assisted editing: Codex authored this follow-up. Review: direct local regression, copied-fixture counterexamples and recorded-data checks above. Original draft attribution remains as recorded in #132. No additional teammate review or personal code entry is inferred. Merge/Integration: review branch only; no main merge or deployment.

Independent terminal market evidence/reconstruction design, C01-C06 structured inputs/adoption and personal reviews remain pending. Actual symlink verification requires an environment already permitting links. No new evaluation/training, model/data/manuscript edit, HTML report implementation or operational approval is included. Private originals, local paths, machine identity and full logs are excluded from this document.
