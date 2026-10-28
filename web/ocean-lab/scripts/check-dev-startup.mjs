// Run from web/ocean-lab. This checks HTTP startup/reload, not browser behavior.
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";
import { stripVTControlCharacters } from "node:util";

const diagnostics = process.argv.includes("--diagnostics");
if (process.argv.slice(2).some((arg) => arg !== "--diagnostics")) {
  throw new Error("Usage: node scripts/check-dev-startup.mjs [--diagnostics]");
}
// Select an unused loopback port, rather than probing an unrelated dev server.
const reservation = createServer();
reservation.listen(0, "127.0.0.1");
await once(reservation, "listening");
const port = reservation.address().port;
await new Promise((resolve, reject) => reservation.close((error) => error ? reject(error) : resolve()));
const started = Date.now();
const interrupted = new AbortController();
const onInterrupt = () => { process.exitCode = 130; interrupted.abort(new Error("Interrupted")); };
const onTerminate = () => { process.exitCode = 143; interrupted.abort(new Error("Terminated")); };
process.once("SIGINT", onInterrupt);
process.once("SIGTERM", onTerminate);
const child = spawn(process.execPath, [
  fileURLToPath(new URL("./run-framework.mjs", import.meta.url)),
  "dev", "--host", "127.0.0.1", "--port", String(port),
], {
  cwd: fileURLToPath(new URL("../", import.meta.url)),
  env: diagnostics ? {
    ...process.env,
    NODE_DEBUG: [process.env.NODE_DEBUG, "@cloudflare:vite-plugin", "net"].filter(Boolean).join(","),
  } : process.env,
  stdio: ["ignore", "pipe", "pipe"],
  detached: process.platform !== "win32",
});
const exited = once(child, "exit");
const closed = once(child, "close").then(() => true, () => true);
let output = "";
let announced = false;
let notifyReady;
const ready = new Promise((resolve) => { notifyReady = resolve; });
child.stdout.on("data", (data) => {
  process.stdout.write(data);
  const combined = output + data.toString();
  output = combined.slice(-8192);
  // Strip after accumulation so ANSI escapes split across chunks are handled.
  if (!announced && stripVTControlCharacters(combined).includes(`http://127.0.0.1:${port}/`)) {
    announced = true;
    notifyReady();
  }
});
child.stderr.on("data", (data) => process.stderr.write(data));
let timer;
try {
  console.log(`START: ${new Date().toISOString()} ${process.platform} ${process.version}; IPv4 port ${port}`);
  await Promise.race([
    ready,
    exited.then(([code, signal]) => { throw new Error(`dev exited before IPv4 readiness: code=${code}, signal=${signal}`); }),
    new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("dev did not announce IPv4 readiness within 120 seconds")), 120_000); }),
    new Promise((_, reject) => interrupted.signal.addEventListener("abort", () => reject(interrupted.signal.reason), { once: true })),
  ]);
  clearTimeout(timer);
  console.log(`READY: ${Date.now() - started} ms`);
  for (let attempt = 1; attempt <= 2; attempt++) {
    const response = await fetch(`http://127.0.0.1:${port}/procurement`, {
      signal: AbortSignal.any([AbortSignal.timeout(60_000), interrupted.signal]),
      redirect: "error",
    });
    const body = await response.text();
    if (response.status !== 200 || !body.includes("<html") ||
        !body.includes('class="u01-page"') || !body.includes("STATIC_KNOWN")) {
      throw new Error(`procurement request ${attempt}: HTTP ${response.status}, missing expected procurement HTML`);
    }
    console.log(`PASS: procurement HTTP request ${attempt}: 200, ${Buffer.byteLength(body)} bytes`);
  }
  console.log("PASS: IPv4 dev startup and repeated HTTP page requests; browser hydration/interactions not tested.");
} catch (error) {
  console.error(`FAIL after ${Date.now() - started} ms:`, error);
  process.exitCode ||= 1;
} finally {
  clearTimeout(timer);
  if (child.pid && child.exitCode === null && child.signalCode === null) {
    // Only terminate this probe's child process (and its workerd child on Windows).
    if (process.platform === "win32") {
      const cleanup = spawnSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
        stdio: "inherit", timeout: 5000,
      });
      if (cleanup.error || cleanup.status !== 0) {
        console.error("FAIL: could not confirm cleanup of the probe's Windows process tree.", cleanup.error ?? cleanup.status);
        process.exitCode ||= 1;
      }
    } else {
      child.kill("SIGTERM");
    }
    async function waitForExit() {
      let deadline;
      const finished = await Promise.race([
        exited.then(() => true, () => true),
        new Promise((resolve) => { deadline = setTimeout(() => resolve(false), 5000); }),
      ]);
      clearTimeout(deadline);
      return finished;
    }
    if (!await waitForExit()) {
      child.kill("SIGKILL");
      if (!await waitForExit()) {
        console.error(`FAIL: probe child PID ${child.pid} did not exit; manual cleanup may be required.`);
        process.exitCode ||= 1;
        child.stdout.destroy();
        child.stderr.destroy();
        child.unref();
      }
    }
  }
  if (child.pid && process.platform !== "win32") {
    // The child is a dedicated process-group leader; clean up any descendants.
    try { process.kill(-child.pid, "SIGKILL"); } catch (error) {
      if (error.code !== "ESRCH") {
        console.error("FAIL: could not confirm cleanup of the probe's process group.", error);
        process.exitCode ||= 1;
      }
    }
  }
  process.removeListener("SIGINT", onInterrupt);
  process.removeListener("SIGTERM", onTerminate);
  // `exit` can precede the last stderr/stdout data. Drain before closing pipes,
  // but bound this wait in case a surviving descendant still holds them open.
  let drainDeadline;
  await Promise.race([
    closed,
    new Promise((resolve) => { drainDeadline = setTimeout(resolve, 2000); }),
  ]);
  clearTimeout(drainDeadline);
  // A descendant retaining inherited pipes must not keep a failed probe alive.
  child.stdout.destroy();
  child.stderr.destroy();
  child.unref();
}
