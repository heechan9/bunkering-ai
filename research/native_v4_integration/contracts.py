"""Merge member contract CSVs into one view without overwriting other owners' rows."""
import csv
import hashlib
from pathlib import Path

FIELDS = ["contract_id", "field", "input_owner", "baseline_proposal_not_approved", "unit",
          "unresolved_question", "contract_version", "proposed_value", "evidence_file_or_url",
          "domain_status", "owner_decision", "checked_by", "checked_at"]
# Columns a member may fill for rows they own; everything else must equal the template.
MEMBER_FIELDS = {"proposed_value", "evidence_file_or_url", "domain_status", "unresolved_question",
                 "checked_by", "checked_at"}
OWNER_FILES = {"domain_review": "domain_review_contract.csv", "data_statistics": "data_statistics_contract.csv", "현수": "hyeonsu_contract.csv"}
DECISIONS = {"pending", "accepted", "rejected"}
# Member review vocabulary from the v4 instructions (domain_review: 적합/부적합/조건부/미확인).
DOMAIN_STATUSES = {"pending", "적합", "부적합", "조건부", "미확인"}
# Contract row -> integration config field, test and code that consume it.
DOMAIN_STATUSES.add("input_proposed")  # Received proposal; owner_decision remains independent.
INTEGRATION = {
    "C01": ("integration.reserve_phase; native_fixed.reserve; native_fixed.tolerance",
            "test_native_fixture.ReserveBoundaryTests", "evaluation/safety_accounting.py (reused); policies.py"),
    "C02": ("integration.consumption_known_at_decision; native_fixed.consumption_per_step",
            "test_native_fixture.TransitionTests", "envs/bunkering_env.py (reused)"),
    "C03": ("native_fixed.refill_request; native_fixed.max_fill",
            "test_ledger.ValidationTests", "ledger.py"),
    "C04": ("integration.statistics_ddof", "test_ledger.StatisticsTests", "ledger.py"),
    "C05": ("integration.terminal_valuation", "test_ledger.LedgerTests", "ledger.py"),
    "C06": ("contract_version; policy_version; integration.seed_status; integration.seed_range_inclusive",
            "test_config_cli", "config.py; cli.py"),
}


class ContractError(ValueError):
    pass


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ContractError(f"{path}: header differs from template")
        rows = list(reader)
    ids = [r["contract_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ContractError(f"{path}: duplicate contract_id")
    return {r["contract_id"]: r for r in rows}


def merge(template_path, inputs):
    """inputs: {owner_name: path or None}. Returns (merged_rows, issues)."""
    template = read_rows(template_path)
    issues = []
    loaded = {}
    for owner, path in inputs.items():
        if path is None or not Path(path).exists():
            issues.append(f"{owner}: file not received")
            continue
        rows = read_rows(path)
        if set(rows) != set(template):
            raise ContractError(f"{path}: contract_id set differs from template (rows added or deleted)")
        for cid, row in rows.items():
            base = template[cid]
            if row["contract_version"] != base["contract_version"]:
                raise ContractError(f"{path}:{cid}: contract_version {row['contract_version']} != template")
            if row["owner_decision"] != base["owner_decision"]:
                raise ContractError(f"{path}:{cid}: owner_decision is decided by 희찬 only")
            for col in FIELDS:
                if row[col] == base[col]:
                    continue
                if base["input_owner"] != owner:
                    raise ContractError(f"{path}:{cid}.{col}: {owner} edited a row owned by {base['input_owner']}")
                if col not in MEMBER_FIELDS:
                    raise ContractError(f"{path}:{cid}.{col}: column is fixed by the template")
        loaded[owner] = rows

    merged = []
    for cid, base in template.items():
        owner = base["input_owner"]
        row = dict(loaded.get(owner, {}).get(cid, base))
        if owner not in loaded:
            status = "not_received"
        elif row["proposed_value"].strip():
            status = "received_filled"
        else:
            status = "received_blank"
            issues.append(f"{cid}: {owner} file received but proposed_value is blank")
        if row["domain_status"] not in DOMAIN_STATUSES:
            issues.append(f"{cid}: domain_status {row['domain_status']!r} not in {sorted(DOMAIN_STATUSES)}")
        row["received_status"] = status
        merged.append(row)
    return merged, issues


def read_decisions(path):
    """Read an owner decision CSV without silently overwriting duplicate IDs."""
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        required = {"contract_id", "owner_decision"}
        if not required.issubset(fields) or len(fields) != len(set(fields)):
            raise ContractError(f"{path}: decisions header needs unique contract_id and owner_decision columns")
        decisions = {}
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ContractError(f"{path}:line {line}: decisions row width differs from header")
            cid, decision = row["contract_id"], row["owner_decision"]
            if not cid.strip():
                raise ContractError(f"{path}:line {line}: blank contract_id")
            if cid in decisions:
                raise ContractError(f"{path}:line {line}: duplicate decision contract_id {cid!r}")
            if decision not in DECISIONS:
                raise ContractError(f"{path}:line {line}: invalid decision {decision!r}")
            decisions[cid] = decision
    return decisions


def apply_decisions(merged, decisions):
    """Validate all supplied owner decisions before changing any merged row."""
    ids = {row["contract_id"] for row in merged}
    unknown = set(decisions) - ids
    if unknown:
        raise ContractError(f"unknown decision contract_id: {sorted(unknown)}")
    pending = []
    for row in merged:
        decision = decisions.get(row["contract_id"], row["owner_decision"])
        if decision not in DECISIONS:
            raise ContractError(f"{row['contract_id']}: invalid decision {decision!r}")
        pending.append(decision)
    for row, decision in zip(merged, pending):
        row["owner_decision"] = decision
    return merged


def integration_map(merged, output_version):
    out = []
    for row in merged:
        config_field, test_name, code_file = INTEGRATION[row["contract_id"]]
        open_issue = "" if row["owner_decision"] == "accepted" else "awaiting 희찬 decision"
        if row["received_status"] != "received_filled":
            open_issue = f"{row['input_owner']} input {row['received_status']}; " + open_issue
        out.append({"contract_id": row["contract_id"], "input_version": row["contract_version"],
                    "input_owner": row["input_owner"], "received_status": row["received_status"],
                    "owner_decision": row["owner_decision"], "config_field": config_field,
                    "test_name": test_name, "code_file": code_file, "output_version": output_version,
                    "open_issue": open_issue.strip("; ")})
    return out


def freeze(merged):
    """Only an all-accepted contract can become v1.0; returns (rows, sha256 of canonical CSV)."""
    blocked = [r["contract_id"] for r in merged if r["owner_decision"] != "accepted"]
    if blocked:
        raise ContractError(f"cannot freeze BAI-CONTRACT-v1.0: not accepted {blocked}")
    rows = [{**{k: r[k] for k in FIELDS}, "contract_version": "BAI-CONTRACT-v1.0"} for r in merged]
    text = ",".join(FIELDS) + "\n" + "".join(",".join(_q(r[k]) for k in FIELDS) + "\n" for r in rows)
    return rows, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _q(value):
    return '"' + value.replace('"', '""') + '"' if any(c in value for c in ',"\n') else value
