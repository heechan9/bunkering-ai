# Research: incremental port-call time

Separate timing model; no import or modification of fair_replacement_eval criteria,
policies, official results, checkpoints or operational environment.

## Contract

All units are hours. Inputs must be finite nonnegative real numbers; bool, strings,
negative values and nonfinite numbers are errors. None means UNKNOWN, never zero.
Zero must be supplied explicitly. Arithmetic overflow raises ValueError.

`existing_call`: events share one local time origin. Departure without bunkering
is the counterfactual baseline. The cargo completion time WITH bunkering must
include any interruption caused by bunkering. The bunker-ready offset includes
waiting and access restrictions before sequential preparation, transfer and
cleanup. Cleanup includes all bunker-related remaining work before departure.
Extra delay = max(baseline departure, cargo end with bunkering, bunker completion)
minus baseline departure. This prevents negative delay and avoids adding overlapping
cargo and fuel work twice. It assumes any other departure constraints are captured
in these inputs; it is not a full berth or resource scheduler.

`dedicated_call`: sum disjoint incremental detour, port transit, waiting,
preparation, transfer, cleanup. Detour excludes port transit. No implicit phases.
The caller must supply a route-without-call baseline and avoid duplicate durations.

`arrival`: baseline voyage already includes existing cargo calls, excludes the
incremental delays above. Sums fixed local call results; equality with deadline is
on-time. Unknown calls propagate UNKNOWN. Fuel safety is NOT measured. Earlier
arrival changes, tides, congestion and subsequent schedule feedback are not modeled.

## Run

From repository root:

```sh
python -m research.port_call_time.sensitivity > /tmp/port-time-sensitivity.csv
python -m pytest research/port_call_time -q
```

The supplied `sensitivity.csv` has 63 entirely synthetic cases, no real ship traces.
Existing-call grid: cargo 8/12/16h, bunker ready 0/4h, work 8/10/14h,
deadline 728/736/760h (54 cases). Dedicated grid: work8/10/14h and same deadlines
(9 cases), detour2h, port transit1h, wait1h. Each uses prep1h, cleanup1h and
transfer=work−2. These choices are scenario assumptions, not calibrated observations.
Existing-call baseline is720+cargo; dedicated-call baseline720. Thus this is NOT
a drop-in rerun of the legacy720+8×stops model or an official replacement decision.
No seed or learned policy is used. Do not interpret this as policy superiority.

## Domestic evidence and next step

UPA DAYTONA (2026-02-23–24, 1375t, reported10h) and BPA VISBY
(2024-08-08,270t,08–22h) describe simultaneous cargo/bunker work. Their time
boundaries and counterfactual departure times are missing; neither calibrates the
extra delay. Do not feed their reported duration directly into this model as a
measured incremental delay. The 24h/8h official synthetic assumptions stay unchanged.

- https://www.upa.or.kr/portal/board/post/view.do?bcIdx=671&idx=16112&mid=0501010000
- https://busanpa.com/board/view.do?boardId=BBS_0000031&dataSid=32526&menuCd=DOM_000000105002001000&paging=ok&startPage=1

Later policy comparison requires action-dependent visit schedules, fuel decisions,
explicit missing-data handling, schedule feedback assumptions, and preregistered
scenario/deadline sets. This module does not yet provide that integration.

Validation (Codex, 2026-10-08): 19 targeted pytest cases passed. Includes overlap,
late start, cargo interruption, dedicated phases, missing values, invalid numbers,
overflow, inclusive deadlines, multiple calls, and monotonicity over the63 cases.
Full repository suite on main `54b0ad1` plus this module: 533 passed + 23 subtests
(Codex, 2026-10-08, 43.85s). Initial local run failed four subprocess imports
because the dependency path was not inherited; rerun used an isolated venv with
the dependency path installed via .pth. GitHub CI is separate evidence.

Domestic source inventory: [PR #113](https://github.com/heechan9/bunkering-ai/pull/113).
Module review: [PR #114](https://github.com/heechan9/bunkering-ai/pull/114).
Independent reviewer baseline remains `f5e50b0`; no code change in this follow-up.

## Data intake and validation (separate tool)

`intake.py` checks timing records before they reach this model: explicit UNKNOWN (never 0), units, time zones,
time order, provenance per value (`observed` / `stakeholder_statement` / `estimate` / `synthetic_assumption`) and
disclosure scope. It calls `existing_call` / `dedicated_call` only when the inputs are complete and the
double-counting confirmations are given; otherwise it prints the missing fields. It does not change this model's rules
and does not read a reported work duration as extra delay. Details, field meanings and hand-calculated examples:
[INTAKE.md](INTAKE.md).

```sh
python -m research.port_call_time.intake template --call-type existing_cargo_call > my_case.json  # 1) blank form
python -m research.port_call_time.intake validate my_case.json                                    # 2) validate only
python -m research.port_call_time.intake compute my_case.json                                     # 3) validate + compute
python -m research.port_call_time.intake compute research/port_call_time/examples/*.json          # synthetic examples
python -m pytest research/port_call_time -q
```

Real or non-public inputs belong under `research/port_call_time/private/` (git-ignored). Examples are synthetic only.

Limits: the personal-data check is an auxiliary warning, 완전한 탐지가 아니다. `private/` + `.gitignore` do not protect
files that are 이미 추적 중이거나 `git add -f`로 추가된 경우; review `git status` and the diff before committing. The
confirmations are 사용자 확인 (self-attestation) that 코드가 검증하지 않는다. Bunkering may 겹칠 수 있다 with cargo work and
start before berthing (묘박지/STS), so no order is enforced between `bunker_ready` and the cargo events, nor between the counterfactual `baseline_departure` and the actual berth/cargo events. Only `research/port_call_time/private/` is git-ignored; the `--out` guard accepts any folder named `private`. Delays that bunkering causes to berthing or cargo work must be entered by the submitter in the berth/cargo times; the code does not estimate or adjust for them automatically (see INTAKE.md).
