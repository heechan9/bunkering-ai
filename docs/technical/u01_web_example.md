# U01 three-port web walkthrough

Baseline: main `fcf3c38d5606285626734d1f8cc8bfc14408b300`.
Draft source change only; no merge, deployed release, model replacement or research
performance claim. Requirements/planning: Heechan; implementation, fixtures,
checks and this record: Codex. Human review remains pending.

## Existing screen versus this change

The public Ocean Lab was opened in the cloud browser on 2026-10-24. It presents
normalized fuel/SCI replay, geographic exhibits and policy comparisons. Main
contained no U01 tonne/USD walkthrough. The new `/procurement` page has a link
from the existing home page. It does not modify the existing replay calculators,
data, models, manuscript or PR141's separate 400-row safety accounting work.

## Contract

Illustrative synthetic A → B → C, one fuel grade. Fixed A/B prices are 600/400
USD/t; leg consumptions 30/40 t; capacity 100 t; initial fuel 20 t; arrival reserve
10 t at both arrivals; terminal inventory exactly 10 t. Supply limits at A/B are
100 t each, minimum lifts and fixed/variable fees zero. C's 550 USD/t is a
reference price only: C is the final arrival and purchasing there is forbidden.
The Python source's two decisions correspond to two legs, not three purchases.

Every policy sees the same complete static information, physical constraints and
terminal target. The saved Python LP and three unchanged rules give:

| Method | A purchase t | B purchase t | Cost USD | Final t |
|---|---:|---:|---:|---:|
| LP | 20 | 40 | 28,000 | 10 |
| Minimum required | 20 | 40 | 28,000 | 10 |
| Next cheaper | 20 | 40 | 28,000 | 10 |
| Departure concentrated | 60 | 0 | 36,000 | 10 |

This is the reused U01 unit example, not an unseen evaluation. The table is
recorded Python evidence; browser edits check only a separate candidate ledger,
never rerun an optimizer or a model. The comparison table stays on original U01
even if a visitor changes their candidate. No general savings percentage or
reinforcement-learning advantage is inferred from this one case.

`lib/u01-procurement.ts` deliberately imports no existing purchase-comparison,
scenario-review or replay/SCI helpers. Purchases precede consumption and each next
arrival is checked before another purchase. For [19,41], B arrival is 9 t, C
arrival is 10 t, and the candidate remains failed: later refueling cannot erase
the B violation. Its raw outlay 27,800 USD is displayed as failed-plan expenditure
and `comparableCost` is null. Missing/malformed/negative/non-finite/over-precision
inputs produce no candidate ledger or stale successful result. The fixed UI input
range is 0–100 t with at most three decimal places; these are not editable market
or ship assumptions. Capacity, reserves and terminal equality are independently
checked for numeric candidates. Source tolerances remain explicit.

## External review assignment and candidate separation

Heechan confirmed the external review scope: fresh-environment README/test
execution, invalid-input rejection, and CSV/CLI clarity. Report generation is
not this assignment. U01 is reviewed on PR142; the separate native CSV/CLI
candidate is PR136 at `40100e398efb15f44cf9a032bf000cf519a6fa87`.
The old introduction's `0f96511b4b277a8d69236b3d7d4cce888cced882` is for
practice/historical reproduction, not the current review candidate.
Do not merge candidates or mix normalized SCI with U01 tonnes/USD.
The frozen commands and acceptance criteria are in PR142 comment 6384844796.
No report generator, original dataset, model or native CSV/CLI source is changed.

## Accessibility follow-up after Claude review

The user relayed Claude's browser review of `ae2170e`: calculation passed;
real devices, screen readers and full regression were not covered by that review.
Boundary navigation retains native focusable buttons with `aria-disabled` and
explicit no-op guards instead of disabling the focused button. Each input uses
the same strict quantity parser independently for `aria-invalid`; only the
invalid input references the error message. C reserve errors say destination
arrival inventory and explicitly state that C has no purchasing.
These changes require fresh actual browser keyboard/layout verification;
component checks do not certify focus behavior in a browser.

## Reproduction and checks directly executed

From the repository root (isolated Python environment with existing NumPy/SciPy,
pytest 9.1.1 and pytest-subtests 0.15.0):

```bash
python -m pytest tests/test_u01_web_evidence.py tests/test_procurement_baseline_core.py tests/test_procurement_baseline_policies.py -q --strict-config --strict-markers -W error
```

41 passed. The five new tests compare the exact input/source hash and every saved
method/ledger with existing Python, independently check Decimal arithmetic and
the continuous optimum `J=24000+200*qA` for `20<=qA<=60`, enumerate stops with the
existing independent formulation, and preserve the 19/41 reserve failure. The
enumeration shares SciPy, so it is not external independent reproduction.

From `web/ocean-lab`:

```bash
node scripts/check-u01-procurement.mjs
pnpm typecheck
pnpm exec eslint app/page.tsx app/procurement/page.tsx lib/u01-procurement.ts
pnpm check:regressions
pnpm build
```

The U01 script executes the real TS ledger and React handlers for all four saved
methods, invalid inputs, capacity/reserve/terminal failures, navigation, unsafe
preset, edited quantities resetting the step, invalid input hiding stale results,
reset and Korean/English output. Native buttons, associated input labels, table
headers, live announcements and focusable scroll regions are checked. These are
component/source contracts, not actual keyboard navigation or screen-reader tests.
All 11 regression scripts and TypeScript checks passed. The build includes the
new route; existing Vite config-loader, large-chunk and route-classification
warnings remain. Dependencies were installed from the frozen lockfile without
changing the lockfile or adding packages.

## Remaining UI verification

- Responsive implementation: one-column ports/inputs and stacked step controls
  below 600px, minimum 44px button targets, contained table scrolling, visible
  focus styles, no new 3D dependency on this page.
- Actual 360/390px browser geometry, keyboard Tab/Enter/Space flows, real phones,
  iOS Safari and screen readers: **not yet verified**.
- The cloud browser could inspect the live public site but could not connect to
  the local candidate server (`ERR_CONNECTION_REFUSED`). A local HTTP request
  also could not reach the nominal dev listener. No preview was published to
  work around this, and no new hosted/deployed UI is claimed.
- Before review approval, open `/procurement` locally: inspect widths 360/390/1280,
  tab through every control/table/link, step forward/back, reset at C, load 19/41,
  try blank/negative/NaN inputs, recover with reset, switch language, and confirm
  both languages retain units, boundaries and the same numerical results.

Keep Draft until those UI checks and human review are complete. GitHub CI (if
subsequently run) does not by itself resolve these browser-verification limits.
