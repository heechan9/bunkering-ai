# Purchase comparison validation — 2026-09-24

Scope: explanatory purchase choices and input provenance. No DQN/model changes, learned history, MCTS, new paper results or savings claims. Existing paper files and baseline replay/summary JSON are unchanged.

## Behavior

Open 02 Voyage replay, select/open a record and move the timeline. Below the replay, the current pre-action price/FX and current fuel produce four two-decision paths (wait/wait, wait/buy, buy/wait, buy/buy). At step 29 there are only two one-decision paths; at recorded termination there is no comparison. Paths stop at depletion.

The next price and FX are explicitly held constant; future recorded prices and actions are never read by the projection. This is deterministic conditional accounting, not a policy recommendation, probability, forecast or real port optimization. Actions 1–3 in the canonical environment have equivalent accounting, so the UI compares buy/wait. Canonical consume-then-refill behavior, cap 0.95, refill request 0.9 and consumption 0.05 are retained. Pre-refill consumption shortage is separately flagged. Ending inventory is displayed alongside cost.

Current and previous synthetic record readings have simulation-step provenance (age 0 and 1); unavailable history is missing, not zero. Wall-clock observation timestamps are absent and labeled as unavailable. Current required readings must be finite, valid and current-step records; missing/stale values hold comparison. There is no live data source or LSTM forecast.

## Verification

- `python scripts/check-purchase-reference.py --env-source <canonical source directory>` generates 548 action-path fixtures from unmodified `envs/bunkering_env.py` at `66ae9dec2f8ea13a8f4e11b656bc0a011f238929`. The fixture records the source SHA-256. Boundary, empty tank, full tank, random fuel/price/FX and depletion cases are included.
- `node scripts/check-purchase-comparison.mjs` passes: all fixture transitions and aggregate paths match; 19,030 bundled replay decisions match original fuel/quantity/cost; a proxy rejects any future-row access; missing/stale/nonfinite/invalid values hold; zero remains a value; early-stop and last-step handling pass; replay JSON remains unchanged.
- TypeScript typecheck, existing localization/marker/replay regression checks, CSV review checks and production build pass.
- Browser checks: existing compare tab values; open record; jump to step 10; candidate numbers and history age; Korean/English; keyboard move to termination and back to step 29; SafeStock boundary link and risk rows. New comparison is HTML and works independently of WebGL.
- Browser runtime cannot create a WebGL context; existing 3D rendering and physical-device behavior are not newly certified. No claim of a full device/3D audit. Preview initially reported a transient module load error then recovered; functional checks ran on the loaded page.

## Preserved surface and limits

Only the comparison module/component, a page insertion, scoped CSS, fixtures and validation scripts/document are added. Existing policy comparisons, CSV review, share logic, locale data and replay values are not rewritten. The site source's pre-edit page/CSS hashes matched GitHub main before integration. No dependency/lockfile changes.

Known limits: two-decision constant-market assumption; no variable order sizes, port-specific prices/supply, service times or specification constraints; no terminal-inventory economic adjustment in the UI. The interface labels these limits and does not rank low-cost failing or low-inventory paths as better.
