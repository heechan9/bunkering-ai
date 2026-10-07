"""A checkpoint path that is not a regular file must be a recorded preflight failure, never a hang.

Hashing a named pipe or a device such as /dev/zero never reaches end-of-file, so before this check the
evaluation hung without writing any record. The CLI runs in a subprocess here so a regression shows up as
a timeout failure instead of freezing the test run. (The shadow CLI has the same test in test_shadow_timeout.py.)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes need a POSIX platform")


def run_cli(module: str, checkpoint: Path, out: Path, *extra: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", f"research.fair_replacement_eval.{module}", "--checkpoint", str(checkpoint), "--out", str(out), *extra]
    return subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=90)


def make_special(kind: str, tmp_path: Path) -> Path:
    if kind == "fifo":
        path = tmp_path / "checkpoint.pt"
        os.mkfifo(path)
        return path
    return Path("/dev/zero")


@pytest.mark.parametrize("kind", ["fifo", "device"])
def test_evaluate_records_a_non_regular_checkpoint_and_stops_before_any_worker(kind, tmp_path):
    if kind == "device" and not Path("/dev/zero").exists():
        pytest.skip("no /dev/zero")
    out = tmp_path / "out"
    proc = run_cli("evaluate", make_special(kind, tmp_path), out, "--smoke", "--workers", "1")
    assert proc.returncode == 3, proc.stderr
    record = json.loads((out / "preflight.json").read_text(encoding="utf-8"))
    check = next(c for c in record["checks"] if c["id"] == "checkpoint_file")
    assert record["overall"] == "fail" and check["status"] == "fail" and "not a regular file" in " ".join(check["reasons"])
    assert not (out / "episodes").exists() and not (out / "summary.json").exists()


def test_directories_still_fail_with_the_original_error_name(tmp_path):
    from research.fair_replacement_eval import evaluate

    directory = tmp_path / "dir"
    directory.mkdir()
    evaluate.ensure_hashable_checkpoint(directory)  # allowed through: open() reports IsADirectoryError, as #108 tests expect
    with pytest.raises(FileNotFoundError):
        evaluate.ensure_hashable_checkpoint(tmp_path / "missing")
