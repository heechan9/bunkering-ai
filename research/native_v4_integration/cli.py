"""v4 integration CLI. Writes only into a new --out-dir and never over its inputs.

    python research/native_v4_integration/cli.py validate-config --config CONFIG
    python research/native_v4_integration/cli.py verify-source --source-verification JSON
    python research/native_v4_integration/cli.py merge-contracts --template CSV --domain-review CSV --data-statistics CSV --hyeonsu CSV --out-dir DIR
    python research/native_v4_integration/cli.py ledger --config CONFIG --episodes CSV [--steps CSV] [--legacy-summary JSON] --out-dir DIR
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(REPO)]

import config as config_mod  # noqa: E402
import contracts  # noqa: E402
import ledger  # noqa: E402

REUSED_SOURCES = ["envs/bunkering_env.py", "scripts/baseline.py", "evaluation/safety_accounting.py", "agents/dqn.py"]


class OutputGuardError(RuntimeError):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_out_dir(out_dir, inputs, overwrite):
    """Refuse unsafe targets before any work; the folder is created only when writing."""
    raw_out = Path(out_dir).absolute()
    for target in (raw_out, *raw_out.parents):
        if target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction()):
            raise OutputGuardError(f"linked output directory: {target}")
    out = raw_out.resolve()
    if out.exists():
        for target in out.iterdir():
            if target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction()):
                raise OutputGuardError(f"linked output target: {target}")
            if target.is_file() and target.stat().st_nlink > 1:
                raise OutputGuardError(f"hardlinked output target: {target}")
    for p in inputs:
        p = Path(p).resolve()
        # Inputs and their folders (e.g. a bundle's results/) are never write targets, even with --overwrite.
        if out == p.parent or out == p or p.is_relative_to(out):
            raise OutputGuardError(f"--out-dir {out} contains input {p}; choose a separate folder")
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise OutputGuardError(f"--out-dir {out} is not empty; pass --overwrite to replace previous tool outputs")
    return out


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: "" if r.get(k) is None else r[k] for k in fields})


def write_manifest(out, args, inputs, extra):
    import numpy
    manifest = {"command": sys.argv, "subcommand": args.cmd,
                "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "python": sys.version, "numpy": numpy.__version__, "platform": platform.platform(),
                "inputs_sha256": {str(p): sha256(p) for p in inputs}, **extra}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8", newline="\n")


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def cmd_validate_config(args):
    cfg, digest = config_mod.load(args.config)
    print(json.dumps({"status": "valid", "config_sha256": digest, "contract_version": cfg["contract_version"],
                      "policy_version": cfg["policy_version"],
                      "pending": sorted(k for k, v in cfg["integration"].items() if v["status"] != "accepted")}, indent=2))
    return 0


def cmd_verify_source(args):
    pinned = {e["path"]: e["git_blob_sha1"] for e in json.loads(Path(args.source_verification).read_text())}
    result, ok = {}, True
    for rel in REUSED_SOURCES:
        data = (REPO / rel).read_bytes()
        raw, lf = git_blob_sha1(data), git_blob_sha1(data.replace(b"\r\n", b"\n"))
        # A Windows checkout with core.autocrlf=true has CRLF on disk; git stores LF blobs.
        basis = "raw_bytes" if raw == pinned.get(rel) else "crlf_normalized" if lf == pinned.get(rel) else None
        ok &= basis is not None
        result[rel] = {"pinned": pinned.get(rel), "repo_raw": raw, "repo_lf": lf, "match": basis is not None,
                       "basis": basis}
    print(json.dumps({"status": "PASS" if ok else "FAIL", "files": result}, indent=2))
    return 0 if ok else 1


def cmd_merge_contracts(args):
    inputs = {"domain_review": args.domain_review, "data_statistics": args.data_statistics, "현수": args.hyeonsu}
    given = [args.template] + [p for p in inputs.values() if p] + ([args.decisions] if args.decisions else [])
    out = check_out_dir(args.out_dir, given, args.overwrite)
    merged, issues = contracts.merge(args.template, inputs)
    if args.decisions:
        with Path(args.decisions).open(encoding="utf-8-sig", newline="") as f:
            decisions = {r["contract_id"]: r["owner_decision"] for r in csv.DictReader(f)}
        contracts.apply_decisions(merged, decisions)
    version = merged[0]["contract_version"]
    extra = {"issues": issues}
    frozen = None
    if args.freeze:
        frozen, digest = contracts.freeze(merged)
        version, extra["frozen_sha256"] = "BAI-CONTRACT-v1.0", digest
    write_csv(out / "merged_contract.csv", merged, contracts.FIELDS + ["received_status"])
    if frozen:
        write_csv(out / "BAI-CONTRACT-v1.0.csv", frozen, contracts.FIELDS)
    write_csv(out / "integration_map.csv", contracts.integration_map(merged, version))
    write_manifest(out, args, given, extra)
    print(json.dumps({"status": "merged", "output_version": version, "issues": issues}, indent=2, ensure_ascii=False))
    return 0


def cmd_ledger(args):
    cfg, cfg_sha = config_mod.load(args.config)
    given = [args.config, args.episodes] + [p for p in (args.steps, args.legacy_summary) if p]
    out = check_out_dir(args.out_dir, given, args.overwrite)
    version = cfg["contract_version"]
    episodes = ledger.load_episodes(args.episodes, cfg)
    lo, hi = config_mod.setting(cfg, "seed_range_inclusive")
    seeds = {s for _, s in episodes}
    if len(seeds) != hi - lo + 1 or min(seeds) != lo or max(seeds) != hi:
        raise ledger.InputError("episode seeds do not match config.seed_range_inclusive")
    rows, mismatches = ledger.build_ledger(episodes, version)
    steps_checked = 0
    if args.steps:
        _, step_mismatches, steps_checked = ledger.audit_steps(args.steps, episodes, cfg)
        mismatches += step_mismatches
    legacy = json.loads(Path(args.legacy_summary).read_text()) if args.legacy_summary else None
    paired = ledger.paired_summary(episodes, config_mod.setting(cfg, "statistics_ddof"), version, legacy=legacy)
    common, total = ledger.all_policy_common_safe(episodes)
    write_csv(out / "ledger.csv", rows)
    write_csv(out / "paired_summary.csv", paired)
    write_csv(out / "policy_summary.csv", ledger.policy_summary(episodes, version))
    write_csv(out / "accounting_mismatches.csv", mismatches,
              ["check", "policy", "seed", "step", "expected", "actual"])
    legacy_bad = [r for r in paired if r["legacy_match"].startswith("MISMATCH")]
    status = "PASS" if not mismatches and not legacy_bad else "FAIL"
    report = {"status": status, "contract_version": version, "policy_version": cfg["policy_version"],
              "config_sha256": cfg_sha, "episodes_checked": len(rows), "steps_checked": steps_checked,
              "accounting_mismatches": len(mismatches), "first_mismatch": mismatches[0] if mismatches else None,
              "legacy_summary_mismatches": len(legacy_bad),
              "all_policy_common_strict_safe": {"n": common, "of": total},
              "interpretation": "SCI is a synthetic index, not currency; intervals are descriptive."}
    write_manifest(out, args, given, {"report": report})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # Korean owner names on a cp949 Windows console
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("validate-config")
    s.add_argument("--config", required=True)
    s = sub.add_parser("verify-source")
    s.add_argument("--source-verification", required=True)
    s = sub.add_parser("merge-contracts")
    s.add_argument("--template", required=True)
    for name in ["domain-review", "data-statistics", "hyeonsu"]:
        s.add_argument(f"--{name}")
    s.add_argument("--decisions", help="CSV contract_id,owner_decision supplied by 희찬")
    s.add_argument("--freeze", action="store_true", help="write BAI-CONTRACT-v1.0 (all rows must be accepted)")
    s.add_argument("--out-dir", required=True)
    s.add_argument("--overwrite", action="store_true")
    s = sub.add_parser("ledger")
    s.add_argument("--config", required=True)
    s.add_argument("--episodes", required=True)
    s.add_argument("--steps")
    s.add_argument("--legacy-summary")
    s.add_argument("--out-dir", required=True)
    s.add_argument("--overwrite", action="store_true")
    args = p.parse_args(argv)
    handlers = {"validate-config": cmd_validate_config, "verify-source": cmd_verify_source,
                "merge-contracts": cmd_merge_contracts, "ledger": cmd_ledger}
    try:
        return handlers[args.cmd](args)
    except (config_mod.ConfigError, contracts.ContractError, ledger.InputError, OutputGuardError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
