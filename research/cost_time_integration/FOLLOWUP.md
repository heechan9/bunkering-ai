# Follow-up development checks

This phase is separate from the original17 fixtures. followup_fixtures.json was
written with analytical expectations before executing run_followup.py. There are
11 additional cases, two monotonicity sequences, and no fitted parameters.
The input SHA-256 is4125ab73323f8c3af24c535514c977d1de0d7ff8a82cdf7b6ecd6cdfef26811e.

All11 cases matched their frozen expectations. The independent ledger checked
each feasible optimizer result and analytical witness. Original17 cases were
rechecked after the two validation/error-handling fixes and all17 still matched.

| Additional case | Analytical cost USD | Actual result |
| --- | ---: | --- |
| Capacity28t, initial20t | 13300 | q=[0,18,0,8], departure2=28t binds |
| Port2 detour2h, deadline27h | 9600 | Port1 buys16t, time26.32h |
| Existing-call partial overlap | 7200 | Fuel3.6h, readiness0.5h; extra0.6h; time28.1h |
| Same partial overlap, deadline28.09h | infeasible | infeasible |
| Initial46t, fees1000, deadline24h | 0 | q=[0,0,0,0], time24h |
| Supply port2:4 /8 /16t | 9000 /8400 /7200 | same, nonincreasing |
| Deadline27 /28.32 /32h, supply8 | 9600 /8400 /8400 | same, nonincreasing |

Capacity proof: total26t must be purchased. Cumulative purchases through port2
cannot exceed18t because departure2<=28t and inventory there before those
purchases is10t. At least8t is therefore bought at ports3/4, costing>=650/t;
the other18t cost>=450/t. Witness18*450+8*650=13300 attains that bound.
All exact witnesses and proofs are in followup_fixtures.json, not in solver.py.

## Review of stop semantics and tolerances

Every pattern enumerates a closed LP. q=0 selected stops are discarded, not
charged; their smaller support is explicitly enumerated. Dropping such a stop
does not increase objective or delay because all input fees and durations are
nonnegative. No arbitrary positive lower bound or epsilon lot is added. The
continuous0.0005t regression remains positive and is never rounded to zero.
Both zero-volume fees and zero-volume time are exactly0. Timing completeness is
conservatively checked for all four call records, even unused opportunities;
missing records yield UNKNOWN, not implicit zero or a proof of infeasibility.

LP primal/dual tolerance1e-9; acceptance: mass1e-7t, time1e-6h, cost1e-4USD.
These finite-precision checks do not certify exact arithmetic or arbitrary
sub-tolerance physical distinctions. Input mass grid0.001t remains a validation
rule only, never a decision lot. The independent ledger uses Decimal on the
actual serialized quantities; analytical objectives/proofs give independent
bounds for this finite fixture set, not a universal optimum certificate.

HiGHS status2 is infeasible for that pattern. Missing time returns
NOT_COMPUTED_UNKNOWN_TIME. Invalid numeric inputs raise ValueError. Status1
(limit),3 (unbounded),4 (solver failure), unsuccessful solves, nonfinite/wrong
shape solution arrays, and negative purchases raise RuntimeError instead of
being reported as infeasible. Injected-status regressions cover1/3/4. Numeric
noise is not silently rounded away.

Two defects were found before hardening: boolean transfer rates could be treated
as numeric, and nonfinite successful LP arrays lacked an explicit solver-error
guard. test_followup.py failed2 cases before the changes (4 passed). The first
nonfinite test stub also incorrectly used a Python list; correcting it to NumPy
reproduced the missing guard as a downstream ValueError. Both original failure
logs are retained outside this module. The fixed integration tests passed11/11.
The fixes reuse model.hours validation and add explicit shape/finiteness/negative
purchase guards; no objective, fixture expectation, or physical quantity changed.

Existing environment reused read-only:2026-10-15/task-2/.venv-procurement,
Python3.11.16, NumPy2.4.6, SciPy1.17.0, torch2.13.0+cpu,
Gymnasium1.3.0, pytest9.1.1. No dependency installation or research training.

The first whole-suite attempt was interrupted after line-ending conversion
changed registered criteria bytes; it is not a completed test result. Plain
git archive and core.autocrlf=false alone both produced criteria SHA36544d48...
instead of registered1ffad20c.... An isolated archive made with both
core.autocrlf=false and core.eol=lf matched the committed/registered bytes.
Only fresh workspace verification copies were populated; no original user data,
official evidence, or registered hash was edited to bypass the check.

Whole-suite outcome, actual commands, output and per-file SHA-256 are recorded
in the external parent_review_report.txt once the full run finishes. No push,
merge, deployment, new skip, warning suppression or unrelated Windows fix is
included in the integration patch.

After correcting verification-only environment setup, main plus procurement
dependency and integration had773 passed,5 failed,5 skipped,32 subtests passed
(140.96s). All5 failed nodes reproduced on clean main without integration
(5 failed,7.29s): two directory error-classification expectations and three
Windows-incompatible os.kill(pid,0) liveness checks. These existing Windows
fixes are already in PR126, not in this new integration patch. The completed
earlier setup run (24 failed,767 passed,5 skipped,19 subtests passed) and the
interrupted line-ending run are retained rather than reported as passing.

PR126 Windows-compatibility verification variant completed with779 passed,
1 failed,4 skipped,32 subtests passed (146.25s). The one failure was the existing
sleep timeout test: roundtrip397539200ns was below the400000000ns asserted
budget, despite timeout status and worker cleanup. Exactly one targeted rerun
passed (4.50s). That does not erase the full-run failure or establish a root
cause. Platform timer/poll granularity is a hypothesis from the measured early
return and existing Connection.poll path, not a verified diagnosis. No timeout
code, test tolerance or skip was changed. This remaining full-suite timing
failure is outside the new LP adapter and is still reported as unresolved.

The four variant skips are actual FIFO/device tests unsupported on Windows.
Main's fifth skip was the directory test caught by the older module-wide
POSIX marker; PR126 activates it. No skips or warning filters were added.
Final original-checkout status/HEAD matched the initial snapshot. All runs and
their subprocesses finished well before20:00 KST; final evidence generation
and timestamps are in parent_review_report.txt. No background monitoring was
started.
