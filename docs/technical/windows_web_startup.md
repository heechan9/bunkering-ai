# Windows web startup: host dispatch and unresolved reset

## Evidence and scope

The supplied Windows logs used commit `5f0dd23eeda5094d8da47332a6bb59eafd0079fa`
(Claude's TSV raw-byte/EOL fix on `130e7c02`). Installation and all eleven existing
regression scripts passed. Two dev runs failed before HTTP readiness, after
roughly 54–58 seconds, with `read ECONNRESET`; `/procurement` was not requested.
The logs do not identify the peer socket or establish that workerd crashed.
The JSON-import/config-loader warning is not a demonstrated cause.

One independent startup defect is confirmed in the pinned vinext
`1.0.0-beta.9`: its CLI accepts `--hostname` / `-H`, not Vite's `--host`.
The old wrapper passed `--host 127.0.0.1` unchanged, silently leaving vinext's
default `localhost`. The wrapper now translates the flag for the selected
execution profile. Dependency versions, lockfile, Cloudflare runtime, authentication,
security controls, data and TSV attributes are unchanged.

**This fixes ignored bind-address arguments. It does not establish or claim a
fix for the Windows ECONNRESET.** Linux success is not Windows verification.
The Cloudflare plugin initializes Miniflare and RSC/SSR module runners before
the HTTP listener; optimizer log ordering alone cannot locate the reset within
that startup sequence.

## Verify on the affected Windows checkout

The earlier hostfix-only checks used a separate clone of the supplied EOL bundle.
For the current combined native-v4/EOL/hostfix candidate, use an isolated copy
matching its manifest and full patch, and record the exact candidate tree tested.
Keep the earlier standalone logs separate; they do not validate the combined tree.
Stop an existing dev process normally before running the probe; do not kill an unrelated PID.

From `web/ocean-lab`, in PowerShell:

```powershell
corepack pnpm install --frozen-lockfile
corepack pnpm check:framework
corepack pnpm check:regressions
node scripts/check-dev-startup.mjs *> startup-check.log
$result = $LASTEXITCODE
Get-Content startup-check.log
"exit=$result"
```

The probe requires an announced **IPv4** URL, followed by two HTTP 200 HTML
responses from `/procurement`. Redirects are rejected, and each response must
contain `<html`, `class="u01-page"`, and `STATIC_KNOWN`; HTTP 200 alone is insufficient.
It waits up to 120 seconds for startup and up to
60 seconds per response. It selects an available loopback port and waits for its
own child's matching URL; port availability can race between selection and binding.
On Windows it attempts to terminate its own process tree while the direct child
is still running, and reports cleanup errors as nonzero results. This branch does
not guarantee descendant cleanup after the direct child has already exited.
The exit code is captured directly, avoiding a Tee-Object pipeline masking it.

If it still fails, preserve that log and run once with phase/socket diagnostics:

```powershell
node scripts/check-dev-startup.mjs --diagnostics *> startup-diagnostics.log
$result = $LASTEXITCODE
"exit=$result"
```

Diagnostics enable the pinned Cloudflare plugin's startup messages and Node's
`net` debug channel for that child only. Review logs for local paths, hostnames
or other private information before sharing. Do not disable antivirus/firewall,
TLS checks, authentication or the Cloudflare plugin, and do not upgrade the
whole dependency tree as a speculative fix.

Needed to resolve the remaining reset: last Cloudflare initialization phase,
failing socket endpoint, and any workerd crash/exit message on the affected
Windows machine. If startup succeeds, separately open `/procurement` in the
user's chosen browser and refresh; HTTP success alone is not browser verification.
