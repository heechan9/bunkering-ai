# Recorded voyage load recovery

Scope: existing replay page, before playback starts. No new API, screen, model run,
scientific claim, deployment or dependency. Baseline: main
`0c14adb15d09437894fd6ff0a3c870fdc90e148a`.

## Observed failure
The page disabled replay-start controls while `data` was null, but placed both
loading and failure messages inside the `started` branch. On an initial failed
fetch, users could not start playback to reach the message. There was no in-page
retry. The fetch depended on translated `t`, so language changes fetched data again.

## Acceptance conditions and changes
- Pending: one accessible status is visible before playback, outside tab panels.
- Failed HTTP, network or JSON load: an alert and retry button are reachable.
- Retry: clear the error and start a new request; retain selected policy and case.
- Ready: remove the notice; preserve the original recorded runs and summary conversion.
- Cancelled/unmounted requests: neither success nor error updates state.
- Language switch: translate the notice without fetching the same files again.

`app/page.tsx` connects request state and cancellation guards to
`components/ocean/ReplayLoadNotice.tsx`. English copy is in `lib/en.json`.
`scripts/check-replay-load-state.mjs` is included in `check:regressions`.

## Applied learning method
The 20260829 frontend mentoring slides describe making loading, empty and error
states explicit before styling, using the real existing screen/data flow.
The 260929 SDD/TDD slides describe a small acceptance contract, a failing test
before implementation, and intentional failure checks. This change applies those
methods only to the unreachable replay loading/error state. No lecture text is
republished, and lecture deployment instructions are not authorization to deploy.

## Verification and limits
The initial new integration test failed on the baseline (zero reachable notices).
After implementation, the same check passed. Further checks execute the real
notice and the page's actual fetch effect with deterministic HTTP/network/JSON
success and failure responses, cancelled results and successful retry. These are
component/effect and source-contract tests, not full browser or mobile E2E.

Run `node scripts/check-replay-load-state.mjs` from `web/ocean-lab`.
Changed-file ESLint passed. Initial reused dependencies lacked d3-geo/types;
baseline and patch had the same five diagnostics. An isolated official-registry
`pnpm install --frozen-lockfile --ignore-scripts` restored the locked dependency tree
without changing package.json or pnpm-lock.yaml. Full typecheck and the complete
check:regressions command now pass, including localization and Arctic-map checks.
All 12 check-*.mjs scripts also pass individually.
Cloud Chromium launch was blocked by socket() Operation not permitted before
page navigation; browser/mobile behavior remains unverified. No access expansion
or alternate browser route was attempted. Build/hosted CI were not run.

Out of scope: payload schema/empty-dataset validation, the comparison screen's
pre-load placeholder figures, browser layout at 390px, fresh hosted CI, and
publication. Scientific artifacts and submitted-paper files are unchanged.
