# Native-v4 contract/code integration review — 2026-10-26

**Review draft. No adoption, freeze, model evaluation, merge or deployment.**
Implementation/review preparation: Codex. Requirements and final adoption: Heechan.
Domain/statistical interpretation is reserved for the separate read-only review.
The first-round packages report AI-assisted preparation; a submission, an AI run,
and a teammate's personal review are different evidence states.

## Git basis and scope

Direct remote checks found main `34e1e82ce10309ba737572fdae24625e4bc722a7`
and #136 `40100e398efb15f44cf9a032bf000cf519a6fa87`, unchanged from the requested basis.
The native-v4 directory is **not in main**. In this document, implemented means
present in the unmerged review stack, not released or domain-approved.

| PR | Head | State / relationship |
|---|---|---|
| [132](https://github.com/heechan9/bunkering-ai/pull/132) | `55b461a` | Open Draft; first-round import on main |
| [133](https://github.com/heechan9/bunkering-ai/pull/133) | `0f96511` | Open Draft; validation follow-up on #132 |
| [134](https://github.com/heechan9/bunkering-ai/pull/134) | `732b25e` | Open Draft; bounded config and INCOMPLETE/3 on #133 |
| [135](https://github.com/heechan9/bunkering-ai/pull/135) | `e3faa05` | Closed unmerged; superseded by #136; do not reimport |
| [136](https://github.com/heechan9/bunkering-ai/pull/136) | `40100e3` | Open Draft; numeric/decision guards on #134 |

Open-PR search also found #143 (U01 audit), #141 (separate 400-row matched-safety
web work), #131/#128 (cost/time model) and #119 (web scenario review).
None is evidence of a native-v4 second-round market-regeneration implementation.
Main contains merged #142 U01. Do not mix U01 tonnes/dollars/purchase-before-consumption,
#141's 400-row dataset, replay records, and this native normalized-fuel/SCI ledger.

This candidate is based on #136, targeting `codex/v4-input-guards-repair-20261021`.
It is a small stacked follow-up; it does not merge or republish its parent patches.

## C01–C06 reflection table

All six `owner_decision` values remain **pending**, and the version remains
`BAI-CONTRACT-v0.1-draft`. Implementation and decision status are separate columns.

| ID / responsibility | Evidence and code connection | Implementation status | Outstanding evidence / decision |
|---|---|---|---|
| C01 / domain review | First-round safety timing proposal; `reserve_phase`, reserve, tolerance → `ledger.expected_transition`, `_strict`, reused `evaluation/safety_accounting.py`; boundary tests at 0.20/0.15/0.02 | Current review code audits consumption-before-refill and retains earlier violations. Departure-planning/real reserve proposals are proposal only. | Second-round structured review, physical reserve/unusable-fuel basis: insufficient evidence. Heechan adoption pending. |
| C02 / domain review | First-round consumption review; `consumption_known_at_decision`, `consumption_per_step` → config guard and reused `envs/bunkering_env.py` | Known constant 0.05 is implemented for reproduction. Uncertainty, port consumption and measured calibration are proposal only. | Vessel/load/weather/information timing unknown; Heechan adoption pending. |
| C03 / data/statistics | Submitted field dictionary (23 rows), contract proposal; refill 0.9/max fill 0.95 → `ledger.load_episodes`, `audit_steps` | Normalized fuel/SCI checks implemented. First-round filled contract is not in historical received CSV, which remains blank. | Four source fields were unknown in that submission; later code/record checks are separate Codex evidence. No tonnes/currency conversion or member approval inferred. Heechan adoption pending. |
| C04 / data/statistics | Statistics checks and corrected second-round recompute source; `statistics_ddof` → `paired_summary` and new `paired_final_fuel` | Existing SCI pairing retained. Candidate adds two final-fuel means on the same pair/subset seeds; n=0 gives both null. | Member personal review pending. This candidate is not yet published/merged. No superiority test or savings claim; Heechan adoption pending. |
| C05 / domain review | First-round terminal/limits review; `terminal_valuation` → `build_ledger`, `audit_steps`, CLI scope | Initial + purchase − terminal mark-to-market already implemented; it is not a zero-terminal-value defect. New terminal targets/discounts/practical limits are proposal only. | Independent terminal price/FX verification and real constraints insufficient; INCOMPLETE/3 retained. Heechan adoption pending. |
| C06 / execution/integration | First-round ZIP implementation/manifest/logs; contract/policy versions, seed status/range → `config.py`, `cli.py`, output guards | Versioning, source pins, coverage/guard repairs implemented in #132–136. | Actual second-round ZIP/PR, `--regenerate-market`, 91M/60M logs and personal review not obtained. Reported PASS/77 tests not independently verified; adoption pending. |

## Domain input draft without changing settings

[Prepared CSV](../../research/native_v4_integration/contracts/drafts/domain_review_draft_20261026.csv)
is a **Codex-prepared draft based on the existing first-round domain document**.
It is not a second-round submission or personal domain-owner review. It is not
loaded by default and does not replace the historical blank received file.
Only C01/C02/C05 member-fillable cells are populated, `domain_status=미확인`,
`checked_by=Codex prepared draft; not domain-owner review`, all decisions pending.
The other owners' rows remain unchanged. Schema/ownership merge was checked and
freeze was rejected. Do not use `--decisions` or `--freeze` for this draft.

No native settings are changed. Real capacity, unusable fuel, reserve basis,
consumption distribution, minimum order, fees, lead time, terminal target and
discount remain unknown. First-round weather percentages and capacity percentages
are illustrations, not measurements or adopted operating requirements.

A later change to reserve timing, known/unknown consumption, terminal valuation or
capacity would change feasibility, policy actions and/or SCI. It needs explicit
assumptions, a new policy/config version, separate results and Heechan's decision.
Existing 91M reproduction results must not be relabeled under a changed contract.

## Owner/status vocabulary and value preservation

The existing public interface uses `domain_review` for C01/C02/C05,
`data_statistics` for C03/C04 and the existing execution-owner label for C06.
Private original personal-owner labels require an explicitly prepared derivative
copy; direct private/public CSV interchange is intentionally unsupported.
A local check of the submitted statistics contract replaced only the two owner
labels and the C03 status alias. All other fields, including proposal text,
evidence, checked-by/date, unresolved questions, version and pending decisions,
were compared and preserved. The original ZIP/CSV was not edited or published.

The C03 raw status `input_proposed(부분: 4필드 unknown)` is not an exact member of
`DOMAIN_STATUSES`; plain C04 `input_proposed` is supported already in #133.
The local review copy explicitly maps the former to `input_proposed`, retaining
its raw qualifier in a separate local mapping record and its unknown fields in
the unchanged proposal. This is not an automatic importer or approval conversion.
`input_proposed` means received proposal; it never means accepted. Current merge
reports unknown vocabulary as an issue rather than silently approving it.
Historical received files remain blank; a successful schema merge does not prove
personal review, source-field completeness, or contract adoption.

## Final-fuel cohorts and numerical impact

`policy_summary.csv` is per-policy descriptive output. Its policy-specific safe
means must not be compared as if they shared a paired safe population.
The new separate `paired_final_fuel.csv` uses the same cohort generator as SCI:

- `all`: identical seeds for both policies; failures remain included.
- `common_safe`: only seeds where both policies satisfy arrival and zero pre-refill
  shortage/reserve violations. This maps explicitly to SCI `common_strict_safe`.
- One n applies to both means; n=0 means both Python/JSON values are null and CSV
  numeric cells are empty. Zero remains a real zero, not a missing-value filler.
- Fuel is tank fraction, not tonnes, sale proceeds, cost savings or improvement.

A new Codex check used **the 4,000-row submitted first-round ledger**, not a new
model run or recovered raw step audit. Results:

| Pair (DDQN / baseline) | Subset | n | DDQN final fuel | Baseline final fuel |
|---|---|---:|---:|---:|
| price_reactive | all | 1000 | 0.823850 | 0.032000 |
| price_reactive | common_safe | 33 | 0.892424 | 0.631818 |
| safe_stock | common_safe | 0 | null | null |
| fixed_fueling | common_safe | 0 | null | null |

All-policy common strict-safe is **0/1000**, independently of the 33 seeds in one
policy pair. Selecting a safe subset after policy outcomes does not establish a
whole-policy causal cost effect. No CI/p-value or savings percentage is added.

The second-round handoff's missing-input statement describes its time of writing.
A later status file records Codex recovering the exact inputs and recomputing saved
records. That work remains attributed to Codex, not the statistics member's own
execution/review. The new check above is explicitly narrower: submitted ledger
verification only. The first-round mixed-cohort final-fuel printout is historical
and not a valid paired estimate; it is not overwritten.

Old/new SCI summaries, policy summaries and ledger objects were compared. Both
CLIs were also run in new output directories with episodes explicitly derived
from the submitted ledger: the four existing CSV outputs were **byte-identical**.
No original evaluation files or original packages were changed. Derived episode
input is not represented as the original raw episode CSV. No full step/model
replay was run in this task.

## Support contributions and missing evidence

The retrieved support start ZIP contains instructions and blank CSV/U01 review
forms, not completed PC execution logs. Its CSV target is #136 `40100e3`; its
U01 target is separate `20dd1c4`. The introduction's `0f96511` is historical
practice material. Instructions, planned checks, prior CI and reported passes
are not a supporter's independently executed result. No attributable execution
artifact for the other proposed support contributor was located in the inspected
project folders/search; this is an evidence limit, not proof of no contribution.

Needed next:

1. Domain reviewer: second-round C01/C02/C05 rows, `domain_limits.csv`, explicit
   comparison with native code; unknown values may stay unknown with reasons.
2. Statistics reviewer: personal review of corrected cohorts/aliases and source
   provenance, actual supplemental results if any; retain Codex attribution.
3. Integration contributor: actual second-round ZIP, immutable commit/PR, hashes,
   `--regenerate-market` source, commands/env and raw 91M/60M logs; distinguish
   old reproduction seeds from new evaluation and terminal verification.
4. Support contributors: completed forms/logs with exact SHA, command, exit code,
   environment and unexecuted scope, not only instructions or verbal reports.
5. Heechan: adopt/reject/defer each C01–C06 input; decide a separate future-domain
   and evaluation contract before changing native constants or freezing v1.0.

## Direct validation of this candidate

Python 3.12.14, NumPy 2.3.5. Gymnasium 1.4.0 installed in a task-local dependency
folder to execute the native boundary tests; no repository dependency file changed.
The initial run lacked Gymnasium and failed importing the native fixture module;
the rerun below completed after that dependency was provided.

```bash
PYTHONPATH=<task-local-gymnasium-dependencies> python -m unittest discover \
  -s research/native_v4_integration -p 'test_*.py' -v
python research/native_v4_integration/cli.py verify-source \
  --source-verification research/native_v4_integration/fixtures/pinned_source_blobs.json
git diff --check
```

- 72 unittest methods: **71 passed, 1 skipped** (private `BAI_EVAL_ROOT` absent).
  Includes all 14 native fixture tests and four new paired-final-fuel tests;
  CLI test checks the new file and blank/null serialization.
- Four reused-source blob pins match. Domain draft schema/ownership checked;
  all pending and freeze rejected. Explicit alias/value-preservation check passed.
- 4,000 submitted-ledger rows checked; existing four CLI CSVs byte-identical.
- Both CLI runs return **INCOMPLETE / exit 3**; step audit not checked and terminal
  valuation not independently verified. Clean accounting is not overall PASS.
- Full repository suite, new model inference/training, browser checks and actual
  second-round market regeneration were not run. Hosted CI awaits publication.

Changed code: `ledger.py`, `cli.py`; tests: `test_ledger.py`, `test_config_cli.py`;
review material: this audit, native README and separate domain draft CSV.
