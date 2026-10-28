import assert from "node:assert/strict";
import { normalizeDevArgs } from "./framework-args.mjs";

for (const managedLinux of [false, true]) {
  const expected = managedLinux ? "--host" : "--hostname";
  for (const host of ["127.0.0.1", "localhost", "::1", "0.0.0.0"]) {
    for (const flag of ["--host", "--hostname", "-H"]) {
      assert.deepEqual(normalizeDevArgs([flag, host, "--port", "5199"], managedLinux),
        [expected, host, "--port", "5199"]);
    }
    for (const flag of ["--host", "--hostname"]) {
      assert.deepEqual(normalizeDevArgs([`${flag}=${host}`], managedLinux), [expected, host]);
    }
  }
  for (const args of [["--host"], ["--host", "--port", "5173"], ["--hostname="], ["-H", ""]]) {
    assert.throws(() => normalizeDevArgs(args, managedLinux), /explicit bind address/);
  }
  assert.deepEqual(normalizeDevArgs(["--port=5199", "--mode", "test"], managedLinux),
    ["--port=5199", "--mode", "test"]);
  assert.deepEqual(normalizeDevArgs([], managedLinux), []);
}
console.log("PASS: explicit host flags survive portable/vinext and managed-linux/Vite dispatch; missing addresses fail closed.");
