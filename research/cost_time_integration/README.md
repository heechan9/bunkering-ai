# Synthetic cost / call-time integration (2026-10-16)

Isolated development adapter for four fixed-route purchase opportunities. No training,
model replacement, official result edits, manuscript edits, web changes, push, merge,
or deployment. This is not operational or holdout validation.

## Source and environment

Remote main was checked with git ls-remote and a fresh clone:
`a4634faa261e1a433bbbddbee6106dfac73dd6a5` (PR #127 merged).
PR #126 head: `57de151d19e54ec58248fd1edfe94fb1af9c6520`.
GitHub REST returned open, draft=true, merged=false, mergeable=true.
REST's PR base.sha was 25f89464..., which is not the current remote main ref;
the current remote ref and fresh clone were used for the work base.

Workspace branch: research/cost-time-integration-20261016, based on current main.
The procurement module and its two core/policy tests are unchanged copies from
the PR head, locally available as untracked dependency files. The procurement.py
Git blob hash matches the PR: 7ddaa22fb0ca6602dddf9b2f113820b8cd60f5fd.
The integration patch itself adds only cost_time_integration; applying it to
main requires the procurement dependency from #126 first. No whole-branch merge
was done, so newer voyage_demand work on main remains present.

Original user checkout remains on feat/evidence-fr-routing-20261004,
HEAD aabba356b0ae5527f50dc8934b2938d230b54bc7. Initial untracked files:
.github/bunkering_latest_FR_experiments.zip, its expanded directory, evidence/,
results/robustness/v1_5_aggregate/, results/robustness/v1_5_multiseed/.
No files or Git state in that checkout were changed.

No installation: C:/Users/hc247/anaconda3/python.exe, Python 3.14.6,
NumPy 2.4.6, SciPy 1.18.0, pytest 9.0.3. The existing bunkering_ai environment
lacks SciPy and was left unchanged. Initial sandbox Git access/DNS failures were
resolved by approved read-only external access and a separate workspace clone.

## Method and integration boundary

solver.py imports procurement.Case validation and port_call_time model functions.
It does not use the legacy DQN reward, SCI inventory correction, or the older
time_constrained_planner fixed time as a monetary fee.
All 16 stop patterns are enumerated. Each solves a continuous LP for purchases
and delay epigraphs, with supply, availability, minimum lift, cumulative reserve,
departure capacity, exact terminal inventory, and inclusive deadline constraints.
Existing call delay is max of overlapping work, not their sum. Baseline voyage
time includes sailing plus existing calls exactly once. Missing time propagates
NOT_COMPUTED_UNKNOWN_TIME, never implicit zero.

Pattern LPs use the closed nonnegative purchase bounds; a returned zero purchase
on a selected stop is rejected as a support mismatch. Its smaller support is
also enumerated, with no fee/time for the unused stop. No epsilon lot size or
quantity rounding is introduced. Fees are added only to exact positive supports.
All monetary/time inputs are nonnegative; dropping a zero-purchase stop cannot
increase its objective or delay. Solver failures other than infeasibility raise
instead of being relabeled infeasible. HiGHS LP uses presolve=False and primal/
dual tolerances 1e-9. LP solves are floating point, not rational certificates.

ledger.py independently recomputes sequential inventory, fees, dedicated timing,
and existing-call max timing using Decimal arithmetic. It does not reuse LP
matrices or the project timing functions. Expected objective values and analytical
bounds are parent-provided independent checks, used only by run_validation.py;
they are never solver inputs. Compact numerical fixtures and the contract are
frozen JSON; the supplied proof arguments are summarized separately in
analytical_proofs.json. Input hashes are recorded in validation_results.json.

## Results

17/17 frozen cases matched: 11 feasible optima and 6 infeasible cases; no expected
values were adjusted after solving. Every feasible solution passed the independent
ledger and objective/time comparisons. Every feasible parent witness also passed
the ledger. The nonunique flat-price case does not enforce a purchase vector or
stop count. All per-pattern statuses and ledgers are in validation_results.json.

Key results: base 7200 USD; supply8 8400; supply8 + fee100 8600 (two stops);
fee1500 11100 (one stop); deadline27h consolidates to9600; first two unavailable
10700. Deadline26.32h is feasible,26.31h infeasible. Existing-call full overlap:
24h sailing+3.5h baseline+0h incremental=27.5h,7200 USD. Limiting that zero-delay
port to8t makes the zero-slack case infeasible.

Regression checks: 190 passed for new integration tests plus existing port_call_time;
36 passed for unchanged procurement core/policy tests. New tests cover unknown
time, q=0 fee/time, a genuinely continuous0.0005t purchase (not a0.001t lot),
pre-refill reserve failure, and existing overlap.
First pytest collection failed due to missing new-package __init__.py (fixed).
Next run had163 passed/27 setup errors from sandbox's default temp directory;
using a fresh workspace --basetemp resolved all27. No source expectations were
changed to resolve either failure. The original phase did not run the full suite;
the subsequent full-suite checks and separate additional cases are in FOLLOWUP.md
and the external parent_review_report.txt.

Commands from repository root:

```powershell
& C:\Users\hc247\anaconda3\python.exe -m research.cost_time_integration.run_validation
& C:\Users\hc247\anaconda3\python.exe -m pytest research/cost_time_integration/test_integration.py research/port_call_time -q --strict-config --strict-markers -W error --basetemp=C:\Users\hc247\Documents\Codex\2026-10-16\task-5\pytest-cost-time-20261016
& C:\Users\hc247\anaconda3\python.exe -m pytest tests/test_procurement_baseline_core.py tests/test_procurement_baseline_policies.py -q --strict-config --strict-markers -W error
```

The runner refuses to overwrite its evidence JSON. Use a fresh copy/output design
for a new run. The 17 fixtures do not exercise binding capacity, nonzero detours,
or partial overlap. The small extra continuous-purchase regression is a software
check, not extension to whole-voyage validation. Real schedule feedback, uncertain
inputs, tides, berth resources and dynamic information remain out of scope.
