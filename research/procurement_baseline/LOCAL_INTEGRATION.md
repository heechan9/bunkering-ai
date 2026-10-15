# Local integration and verification — 2026-10-15

This preserves the **initial local integration phase** and its six known existing Windows/strict failures. The subsequently authorized fixes and current validation supersede its remaining-blocker status; see [WINDOWS_COMPATIBILITY.md](WINDOWS_COMPATIBILITY.md). Historical failed logs and the clean-main comparison have not been removed.

Branch: `research/procurement-baseline-integration-20261015`.
Baseline: latest fetched main `25f89464db42b8e71b4f56ba51d05198e5d3921e`.
Scope: local preparation only; no remote push, PR, merge, or web deployment.

## Input and preservation

The user-downloaded `procurement_baseline_comparison_20261015_reviewed.zip` was found in Downloads. Its size is 258,193 bytes and SHA-256 is `863b074677d43e6aae774f13cde77a02eb145f682fb98142732b4a25f5b6d923`, exactly matching the requested reviewed input. Every entry in its supplied `SHA256SUMS.txt` was verified before integration. The archive is retained unchanged under `provenance/`; user downloads and the original project checkout were not moved or deleted. Earlier Library transfer failures and browser initialization failures did not supply the input used here.

No applicable `AGENTS.md` or `.agents/skills` directory was present in this checkout or latest tracked tree. Existing related modules were reviewed for duplication: the NTNU and UK studies, normalized SCI environment, official DQN, and port-call-time model remain separate. All previously tracked repository files remain unchanged (`git diff --exit-code` was clean before marking new files for review). The manuscript, original README images, official results, and web source were not edited.

Exact source hashes:

- Original solver (`reference_original.py`): `93c7a81ec8dc8eb8613d720b26f8bd43754b4adcab73d731d9fea013851c7b5b`.
- Reviewed patched solver (`procurement.py`): `e9f08f7cb0467b3681717b512bb4179689d341117a2af169976c17bb6fca9b75`.
- Specification (`spec.json`): `c96df9d8bab519e60da1ec25183b7b300013e8a7245b0c17b78f3918ad95101e`.

Solver copies are byte-identical to their supplied ZIP members. The `usable`, `need`, `policy`, `generate`, and `summary` function ASTs match the reviewed benchmark exactly. Integration changes are package imports, output/spec CLI paths, output-overwrite protection, encoding/newline handling, diagnostics/report adapters, and documentation. The original 27 tests and additional 9 tests use package-qualified imports; no mathematical assertions were removed.

## Environment

A workspace-local `.venv-procurement` uses Python 3.11.16 and inherits the existing `bunkering_ai` environment read-only. SciPy 1.17.0 was installed only into this isolated virtual environment; NumPy is 2.4.6, pytest 9.1.1, torch 2.13.0+cpu, Gymnasium 1.3.0. `pip check` passed. This differs from the supplied Linux Python 3.12.14 / NumPy 2.3.5 environment and current CI's pinned Python 3.12 setup; environment equivalence is not claimed.

Full tests used OMP/MKL threads 1, `PYTHONHASHSEED=0`, `PYTHONUTF8=1`, an explicit workspace temporary directory, and a headless Matplotlib backend. A separate verification checkout at the exact baseline was populated from Git archive bytes to avoid Windows CRLF conversion of registered evidence files. The original working tree was preserved. The verification tree contained the new solver/rules and 36 tests; later CSV/report adapters were checked separately by the final CLI reproductions below.

## Passed checks

| Check | Observed result | Evidence |
|---|---|---|
| Focused tests, strict config/markers, warnings as errors | 36 passed | `validation/windows_20261015/focused_final.log`, `focused_final.xml` |
| Original solver counterexample | Original INFEASIBLE reproduced; patched OPTIMAL 13,000 USD, q = [1, 10, 15] t; valid ledger and independent optimum agree | `validation/windows_20261015/solver_diagnostic.json` |
| Full development benchmark | 120 inputs, 86 OPTIMAL, 34 INFEASIBLE, no unresolved/contradictory result | `validation/windows_20261015/reproduction_portable/` |
| Handoff comparison | All 120 inputs, reference statuses/costs, and policy statuses/costs match the reviewed handoff | `validation/windows_20261015/portable_handoff_comparison.json` |
| Independent stop-pattern LP enumeration | All 120 match; maximum absolute objective difference 7.275957614183426e-12 USD | Same comparison artifact and per-case results |
| Separate physical ledger/summary audit | PASS, 446 ledgers; feasible reference/rules 86 / 75 / 79 / 79 | `validation/windows_20261015/audit_portable/independent_checks.json` |
| Windows CSV and report CLI | 480 parsed data rows, no doubled CRLF; UTF-8 report generated | `reproduction_portable/results.csv`, `validation/windows_20261015/PORTABLE_REPORT_KO.md` |
| Python compilation and dependencies | compileall and pip check passed | Local command results |

Common feasible denominator: 75 cases, optimum total 1,750,550 USD. Minimum-required, next-cheaper, and departure-concentrated totals are 2,294,200 / 1,755,430 / 2,148,450 USD, giving 23.6967134513% / 0.2779945654% / 18.5203286090%. Pairwise denominators remain separately reported as 75/79/79. Next-cheaper matches the optimum on all 34 feasible fee-free/unlimited-supply cases.

These are reused static-information synthetic development cases. They do not show AI superiority, real-vessel or causal savings, reproduction of the De paper, or unused holdout performance. The presolve workaround does not fully diagnose the internal solver cause or guarantee other platforms.

## Whole-suite strict outcome and remaining failures

Executed from the exact-byte verification checkout:

```bash
python -m pytest -q --strict-config --strict-markers -W error --basetemp=../strict-temp/pytest-exact --junitxml=../bunkering-ai/research/procurement_baseline/validation/windows_20261015/full_strict_exact.xml
```

**728 passed, 32 subtests passed, 5 skipped, 6 failed**, 213.72 seconds. This is not a green whole-suite result. Evidence: `validation/windows_20261015/full_strict_exact.log` and `.xml`.

All six failed nodes were then selected alone, without collecting/importing the new procurement tests, against unchanged committed main code in the exact-byte verification tree. **The same six failed** (`existing_failures.log` / `.xml`):

1. Two parametrizations of `research/fair_replacement_eval/test_preflight.py::test_main_records_checkpoint_read_failure_before_workers` expect `IsADirectoryError`; Windows returns `PermissionError` when the checkpoint path is a directory.
2. Two parametrizations (`sleep`, `spin`) of `research/fair_replacement_eval/test_shadow_timeout.py::test_a_timeout_is_recorded_the_dqn_run_continues_and_the_worker_is_reclaimed` fail with `OSError: [WinError 87]`.
3. `research/fair_replacement_eval/test_shadow_timeout.py::test_close_is_idempotent_and_run_shadow_closes_the_worker_even_if_the_run_fails` fails with the same Windows process error.
4. `research/port_call_time/test_model.py::test_committed_sensitivity_csv_is_regenerated_exactly_with_zero_readiness` emits `PytestUnraisableExceptionWarning` for an unclosed `sensitivity.csv` reader, promoted to an error by `-W error`.

These existing code/test failures were not fixed in this isolated procurement task. Five existing platform-dependent tests were skipped; no new procurement test was skipped. Linux/CI execution of this unposted branch is unperformed, and no remote CI or deployment was triggered.

A second, **clean** checkout `procurement-clean-main` was then created at the same `25f8946` commit with exact Git archive bytes, no procurement module/tests, and empty `git status --porcelain`. Selecting the same six failed nodes in the same Python environment with the same strict options again produced **6 failed in 11.34 seconds**. The clean checkout stayed clean after testing. Evidence: `validation/windows_20261015/clean_main_failures.log` and `.xml`. The six failed node names, error categories, and environment match the integration run. This clean-baseline comparison supports classifying those six failures as pre-existing in this Windows/strict environment, rather than procurement regressions.

The clean-baseline command selects the two `test_main_records_checkpoint_read_failure_before_workers` directory parametrizations, the `sleep`/`spin` timeout parametrizations, `test_close_is_idempotent_and_run_shadow_closes_the_worker_even_if_the_run_fails`, and the sensitivity CSV test listed above, followed by:

```bash
-q --strict-config --strict-markers -W error --basetemp=../strict-temp/clean-main-failures --junitxml=../bunkering-ai/research/procurement_baseline/validation/windows_20261015/clean_main_failures.xml
```

Earlier attempts are retained and are not success evidence: the first sandboxed whole-suite run had temporary-directory permission and CRLF hash failures (42 failed / 537 passed / 5 skipped / 168 setup errors / 19 subtests passed). An intermediate verification attempt was stopped after detecting its checkout baseline/line endings were not the intended exact-byte source. The final complete outcome above supersedes those attempts. The first independent-audit invocation lacked a copied `spec.json`; adding explicit `--spec` support and saving the spec in new benchmark runs resolved it, with the final independent audit passing.

## Reproduce the final module checks

Use the commands in [README.md](README.md) from the repository root and choose **new** output directories/files. The final authoritative local run is `validation/windows_20261015/reproduction_portable`; prior runs are retained for traceability. Existing source and evidence records are never overwritten by benchmark defaults. The six existing strict failures remain the blocker to calling the entire Windows suite green; procurement integration itself passed its focused, counterexample, 120-case, independent-ledger, and handoff-comparison checks.

Verbose local validation and expanded raw handoff files are retained on the laptop but ignored in Git to keep a future review focused. The exact complete reviewed ZIP, concise handoff reports/summaries, integration manifest, executable module, and 36 tests remain visible in the local diff. Module-level attributes preserve copied solver/spec/provenance bytes across future Windows checkouts. No files were deleted by this review packaging step.
