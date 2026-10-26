# Native v4 first-round import and review — 2026-10-19

Status: **draft review import; not approved for merge or operational use**.
Base: `183ab3a684cc970315112c312cc52953bd02f6e1`.
This record concerns the separate native-v4 package, not the separate cost-time model/ledger work in PRs #128/#131.

## Contributions and dates

- Requirements/Planning: Heechan supplied the v4 assignment and retains contract-adoption responsibility.
- Domain review: the 자료 검토 담당자 supplied [the four-part first-round criteria review](../domain/m1_domain_review_first_round_20261019.md). It discusses action-time planning versus arrival/pre-refill evaluation, consumption uncertainty and port consumption, terminal inventory, and practical bunkering constraints. The original says it was not compared directly with the latest teammate implementation.
- Implementation / AI-assisted editing: the package submitted through Hyeonsu states that Claude executed and wrote the implementation/draft on his Windows PC. Hyeonsu's personal review was still pending. Its patch identifies source commit `b5c1f70fcb0dc892887f41ce47df5148eae2e7bc`, 18 added files / 1,480 lines. These facts do not establish Hyeonsu's direct code-entry or review contribution.
- Codex: inspected the submitted files and original assignments, independently checked the available evidence, imported a privacy-adjusted publication copy, and wrote this integration/attribution record. No substantive repair of the submitted algorithm or validation logic is included here.
- Dates: the domain document states 2026-10-19; the patch timestamp is 2026-10-19 09:17:55 +09:00. The package and domain document were received on 2026-10-19 KST. Reception timestamps are not claimed as working time. Codex's import/review date is 2026-10-19 KST.
- Merge/Integration: review branch only; no main merge, deployment, contract adoption, or manuscript change.

## Publication copy and interface compatibility

The original private files remain preserved separately. This repository does not publish the original ZIP, mail-patch header, contact details, private sharing links, evaluation bundle, weights, or full experiment CSVs.
The 18-file implementation is a **privacy-adjusted derivative**, not a byte-identical patch import:

| Public role identifier | Assignment responsibility | Public CLI flag / CSV |
|---|---|---|
| `domain_review` | 자료 검토 담당자; C01/C02/C05 | `--domain-review`, `received/domain_review_contract.csv` |
| `data_statistics` | 자료·통계 담당자; C03/C04 | `--data-statistics`, `received/data_statistics_contract.csv` |
| `현수` | execution/integration; C06 | `--hyeonsu`, `hyeonsu_contract.csv` (unchanged) |

Personal labels were consistently replaced in the owner fields, owner lookup, CLI arguments, filenames, documentation, and their tests. The CLI owner-label changes are an intentional public-interface difference. **Private original CSVs/CLI commands are not directly interchangeable**: prepare separate role-labeled copies before using this public tool; do not edit the private originals. No automatic mapping to personal identities is published. Contract IDs, values, adoption decisions, and ownership enforcement are unchanged. In particular, the received CSVs are the historical blank inputs from the implementation package; the separate domain Markdown does not fill them or approve C01/C02/C05.

The source `ledger.py`, `config.py`, `policies.py`, configuration values, and synthetic fixtures are unchanged. README import warnings identify the known gaps below without silently fixing them. No new license is assigned; repository visibility is not a license grant.

## What was verified independently

Python 3.12.14 / NumPy 2.3.5 in an isolated cloud workspace:

```bash
BAI_EVAL_ROOT=<preserved original evaluation bundle> PYTHONDONTWRITEBYTECODE=1 \
  python -m unittest discover -s research/native_v4_integration -p 'test_ledger.py' -v
BAI_EVAL_ROOT=<preserved original evaluation bundle> PYTHONDONTWRITEBYTECODE=1 \
  python -m unittest discover -s research/native_v4_integration -p 'test_config_cli.py' -v
python research/native_v4_integration/cli.py verify-source \
  --source-verification research/native_v4_integration/fixtures/pinned_source_blobs.json
python research/native_v4_integration/cli.py ledger \
  --config research/native_v4_integration/config/bai_v4_native.json \
  --episodes <bundle>/results/episodes.csv --steps <bundle>/results/steps.csv \
  --legacy-summary <bundle>/results/summary.json --out-dir <new separate directory>
```

- 36 tests passed (16 ledger + 20 config/CLI/contracts), zero skips, on the imported public copy. This includes the renamed ownership paths, rejection of another owner's edits, pending/freeze behavior, and four reused-source blob checks.
- The four reused native source files match the pinned versions on the current main base.
- The original 45-file evaluation bundle remained hash-identical before/after the private inspection.
- Ledger reconstruction checked 4,000 recorded episodes / 100,520 recorded steps, with zero reported accounting or legacy-summary mismatches. The four generated CSV outputs matched the submitted ledger outputs byte-for-byte; the public role renaming does not affect those outputs.
- An independently written recorded-data checker verified price/FX draws, step order/action validity, fuel and cost transitions, initial/terminal valuation and paired summaries for the available records. This is recorded-data verification, not rerunning neural-network inference.
- Not run here: 14 `test_native_fixture.py` tests and five original consistency tests (Gymnasium absent); full native policy/model replay (Gymnasium and PyTorch absent). Hyeonsu's submitted report of 50 new tests + five original tests is separate from Codex's 36 directly executed tests. His reported Python 3.11.9/Windows environment also differs from the assignment's Python 3.12/WSL-or-Linux target.

## Known merge blockers / second-round work

1. **Input validation and ledger completeness.** Controlled copies with NaN step SCI, invalid action IDs, or shifted step identifiers could still receive a PASS. Modified terminal valuations with compensating SCI also escaped the current checks. Require finite/domain/range checks, sequence checks and independent valuation consistency, with regression tests. The available original records passed the separate independent checker; the defects concern the validator's acceptance of future invalid inputs.
2. **Configuration-to-data agreement.** A declared new 92M seed plan accepted the actual reused 91M records; `reserve_phase=post_refill` was accepted while the audit remained pre-refill. Check actual seed/episode coverage and supported phase semantics, or reject unsupported settings. Do not label reused evidence as new evaluation.
3. **Output protection.** With `--overwrite`, an existing output-file symlink could point to an input and permit overwriting it. This was reproduced only on disposable local copies. Reject linked/unsafe output targets before any writes; test that every input remains unchanged after failures. This is a guard defect in a trusted local research CLI, not evidence of an external compromise.

Hyeonsu's own review, these repairs, and the omitted dependency-based tests remain open before treating the implementation as ready. The draft PR preserves the first-round contribution rather than silently completing the repairs.

## Assignment-specific domain follow-up

The requested first round included C01/C02/C05 rows, `domain_limits.csv`, a one-page summary and 3–5 revised claim phrases. The submitted criteria review is a substantive partial contribution, while the structured rows/limits and explicit native boundary-case/SCI comparison remain unfinished.
Known native cases to compare include f=0.20 → u=0.15, f=0.15 → u=0.10, and f=0.02 → u=-0.03 before clipping/refill; native consumption is 0.05. Existing inventory-adjusted SCI already includes initial value minus terminal mark-to-market. Suggestions about zero terminal valuation therefore require implementation comparison, not an assumed existing defect.
Real capacity, unusable fuel, MOQ/barge fees, consumption distribution, and discount values may remain **unknown with reasons**. No measurement, new external research, or invented calibration is required just to fill an honest status. Final adoption belongs to Heechan. New seeds and an upstream PR were optional in Hyeonsu's original assignment.

## Result boundaries

91,000,000–91,000,999 is a reused reproduction set. The reconstructed strict-safe counts are DDQN 1,000, legacy safe-stock 0, price-reactive 33, fixed-interval 0; legacy-arrival success is a separate measure. All-policy common strict-safe n=0. DDQN minus safe-stock inventory-adjusted SCI is +647.65 with descriptive interval [-106.42, 1401.73]; common-safe cost comparison is null. No savings, superiority, equivalence, real-world validation, or currency claim follows.
`safe_stock_pre_refill_v1` is an unevaluated candidate pending C01 adoption and a separate evaluation plan. C01–C06 remain `BAI-CONTRACT-v0.1-draft` / pending.
