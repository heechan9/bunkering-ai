# Windows compatibility follow-up

This follow-up was explicitly authorized after the isolated procurement integration and its clean-main comparison. The original failure records remain in `LOCAL_INTEGRATION.md` and local `validation/windows_20261015/` logs. The research model, procurement solver mathematics, policy definitions, manuscript, official results, NTNU module, and web code remain unchanged.

## Root causes and minimal fixes

1. **Two directory preflight failures.** On POSIX, opening a directory raises `IsADirectoryError`; Windows raises `PermissionError`. `research/fair_replacement_eval/common.py::file_sha256` now identifies a directory explicitly and raises `IsADirectoryError` with `EISDIR` before opening it. Missing paths and genuinely unreadable files still use their original errors. Existing evaluate/shadow preflight tests and the now-platform-independent directory test verify the classification.
2. **Three worker-cleanup test failures.** Traces showed the worker was already terminated/joined; the test's `os.kill(pid, 0)` probe failed with Windows `WinError 87`. That POSIX probe is inappropriate on Windows and can send a termination request there. Tests now inspect owned multiprocessing children with `active_children()` and `is_alive()`. Existing sleep/spin/close tests still verify timeout records, worker reclamation, restart behavior, and zero unreaped children. A new regression distinguishes living/dead/unowned child PIDs and fails if the probe calls `os.kill`. Production worker termination/reaping logic did not need changing.
3. **One CSV resource failure.** The existing sensitivity test constructed a reader from an unclosed `open(...)`. With `-W error`, its resource warning became `PytestUnraisableExceptionWarning`. The test now uses a context manager and still checks all 63 original rows exactly. The CSV contents and model are unchanged.

## Strict mode and skips

All verification uses `--strict-config --strict-markers -W error`: invalid pytest configuration/markers and emitted warnings fail the run. No warning filters or additional skips were added. Linux CI now uses those same strict flags.

The original Windows run's five skips were existing POSIX-only checks: evaluate FIFO, evaluate `/dev/zero`, directory preflight (unnecessarily covered by a module-wide POSIX skip), and shadow FIFO/device checks. The POSIX marker is now restricted to actual special-file tests, so the directory test runs on Windows. Four FIFO/device cases remain platform-specific because Windows has neither the tested `os.mkfifo` interface nor `/dev/zero`. Linux CI exercises them when those facilities are available.

## Reproduction and scope

The former six failures plus the new liveness regression and activated directory test passed together: **8 passed** (`validation/windows_20261015/windows_fixed.log`). Procurement tests still pass: **36 passed** (`focused_after_windows_fix.log`). The solver and 120-case/446-ledger evidence remain as recorded in the integration report.

Windows whole-suite verification uses the exact-byte validation checkout, workspace-local temp folders, Python UTF-8 mode, one OMP/MKL thread, and the isolated environment described in the integration report. This preserves registered evidence hashes rather than disabling their checks. Normal Windows CRLF conversion of existing hash-pinned evidence can produce separate failures; the dedicated verification checkout uses Git's committed bytes. No old official evidence file was rewritten in the user's working tree.

The final Windows full strict run passed: **736 passed, 32 subtests passed, 4 skipped**, 193.20 seconds. The flags were `-q --strict-config --strict-markers -W error --basetemp=../strict-temp/pytest-windows-fixed`, with a JUnit output path in the local validation directory. [Captured successful output](WINDOWS_STRICT_RESULT.txt) · [Machine-readable verification summary](verification_summary.json).

Linux validation is provided by the strict PR CI run; it is not inferred from Windows success. Its exact remote head and conclusion are reported with the Draft PR. No merge or deployment is authorized by this Draft review preparation.
