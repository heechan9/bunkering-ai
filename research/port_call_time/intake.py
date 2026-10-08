"""Intake, validation and calculation hand-off for port-call timing records (research only).

Reads a JSON case file, validates every value, and calls ``model.existing_call`` /
``model.dedicated_call`` only when the inputs are complete. It never imports or changes the
calculation code's rules, never fills a missing value with zero, never uploads or publishes
anything (no network code), and never treats a reported work duration as extra voyage delay.

    python -m research.port_call_time.intake template --call-type existing_cargo_call
    python -m research.port_call_time.intake validate FILE [FILE ...]
    python -m research.port_call_time.intake compute  FILE [FILE ...] [--out PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

from . import model

SCHEMA_VERSION = 1
UNITS = {"hours": 1.0, "minutes": 1.0 / 60.0}
BASES = ("observed", "stakeholder_statement", "estimate", "synthetic_assumption")
_RANK = {b: i for i, b in enumerate(BASES)}  # higher index = weaker evidence
SCOPES = ("public_ok", "project_internal", "private_do_not_publish", "unknown")
CALL_TYPES = ("existing_cargo_call", "dedicated_bunker_call")
TIME_MODES = ("offset", "absolute")

EXISTING_EVENTS = ("baseline_departure", "cargo_end_with_bunkering", "bunker_ready")
EXISTING_DURATIONS = ("preparation", "transfer", "cleanup")
EXISTING_OPTIONAL_EVENTS = ("berth_arrival", "cargo_start")  # only used for time-order checks
DEDICATED_DURATIONS = ("detour", "port_transit", "waiting", "preparation", "transfer", "cleanup")
CONFIRMATIONS = {
    "existing_cargo_call": (
        "baseline_departure_is_departure_without_bunkering",
        "cargo_end_includes_bunkering_interruption",
        "bunker_ready_includes_waiting_and_access_restrictions",
        "cleanup_includes_all_remaining_bunker_work",
    ),
    "dedicated_bunker_call": (
        "baseline_is_route_without_this_call",
        "detour_excludes_port_transit",
        "waiting_excludes_work_phases",
        "no_phase_counted_twice",
    ),
}
CASE_KEYS = {"case_id", "call_type", "unit", "time_mode", "reference_time", "source", "disclosure",
             "confirmations", "values", "notes"}
VALUE_KEYS = {"value", "at", "basis", "unit", "note"}
DELAY_LIKE = {"extra_delay", "extra_delay_hours", "delay", "delay_hours", "departure_delay", "reported_duration",
              "reported_work_hours", "work_hours", "total_work_hours", "duration", "total_hours"}
LARGE_DURATION_HOURS = 72.0
CODE_VERIFIED_CHECKS = (
    "every used number is finite and >= 0 (no bool or text)",
    "one declared unit per case, no mixed units",
    "every provided value has a declared basis",
    "order of the actual berth/cargo events that were provided (berth_arrival <= cargo_start <= cargo_end_with_bunkering)",
)
PRIVACY_NOTICE = ("The personal-data check is an auxiliary warning, not complete detection, and the disclosure fields are the "
                  "submitter's own statement. A private/ directory and .gitignore do not protect files that are already tracked "
                  "by git or that are added with 'git add -f'. Review 'git status' and the diff before every commit and keep real "
                  "data outside the repository when in doubt.")

def _member(item, collection):
    """Membership test that never raises on unhashable JSON values (lists, objects)."""
    return isinstance(item, str) and item in collection


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_PHONE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")


class IntakeError(Exception):
    """The file itself cannot be read as an intake file."""


def _err(code, field, message):
    return {"code": code, "field": field, "message": message}


# ------------------------------------------------------------------ loading

def _no_constant(name):
    raise ValueError(f"non-finite JSON constant {name} is not allowed")


def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def load_file(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_no_duplicates)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise IntakeError(f"{path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("cases"), list):
        raise IntakeError(f"{path}: expected an object with schema_version {SCHEMA_VERSION} and a cases list")
    return data


# ------------------------------------------------------------------ validation helpers

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(T[\d:.+Zz-]*)?")


def _personal_data(text):
    """Conservative: flags e-mail addresses and phone-like digit runs (ISO dates are removed first)."""
    if not isinstance(text, str):
        return False
    if _EMAIL.search(text):
        return True
    stripped = _ISO_DATE.sub(" ", text)
    return any(sum(c.isdigit() for c in m.group()) >= 9 for m in _PHONE.finditer(stripped))


def _check_text(errors, field, value, required=False):
    if value is None or value == "":
        if required:
            errors.append(_err("missing_text", field, "required text is missing"))
        return None
    if not isinstance(value, str):
        errors.append(_err("bad_text", field, "expected text"))
        return None
    if _personal_data(value):
        errors.append(_err("personal_data", field, "looks like an email address or phone number (heuristic warning); remove personal contact details"))
    return value


def _parse_instant(text, field, errors):
    if not isinstance(text, str):
        errors.append(_err("bad_time", field, "expected an ISO-8601 timestamp with an explicit UTC offset"))
        return None
    try:
        instant = dt.datetime.fromisoformat(text)
    except ValueError:
        errors.append(_err("bad_time", field, f"cannot parse {text!r} as an ISO-8601 timestamp"))
        return None
    if instant.tzinfo is None or instant.utcoffset() is None:
        errors.append(_err("naive_time", field, "timestamp has no time zone; write an explicit offset such as +09:00 or Z"))
        return None
    return instant


def _read_value(spec, field, case_unit, factor, is_event, mode, reference, errors):
    """Return (hours | None, basis | None). None hours means UNKNOWN."""
    if spec is None or (isinstance(spec, str) and spec.strip().upper() == "UNKNOWN"):
        return None, None
    if not isinstance(spec, dict):
        errors.append(_err("bare_value", field, "wrap the value as an object with value/at and basis; a bare number has no provenance"))
        return None, None
    extra = set(spec) - VALUE_KEYS
    if extra:
        errors.append(_err("unknown_key", field, f"unknown keys {sorted(extra)}"))
    _check_text(errors, f"{field}.note", spec.get("note"))
    unit = spec.get("unit")
    if unit is not None and unit != case_unit:
        errors.append(_err("mixed_units", field, f"value unit {unit!r} differs from the case unit {case_unit!r}; convert before entering"))
    use_at = is_event and mode == "absolute"
    key, other = ("at", "value") if use_at else ("value", "at")
    if other in spec:
        errors.append(_err("wrong_value_key", field, f"use '{key}' here (time_mode is {mode!r} for events, durations always use 'value')"))
        return None, None
    raw = spec.get(key)
    basis = spec.get("basis")
    if raw is None or (isinstance(raw, str) and raw.strip().upper() == "UNKNOWN"):
        return None, basis if _member(basis, BASES) else None
    if not _member(basis, BASES):
        errors.append(_err("bad_basis", field, f"basis must be one of {list(BASES)}"))
        return None, None
    if use_at:
        instant = _parse_instant(raw, field, errors)
        if instant is None:
            return None, basis
        if reference is None:
            errors.append(_err("missing_reference", field, "an absolute time needs a reference_time (timestamp with explicit offset) on the case"))
            return None, basis
        hours = (instant - reference).total_seconds() / 3600.0
        if hours < 0:
            errors.append(_err("before_reference", field, "event is earlier than reference_time; choose an earlier reference_time"))
            return None, basis
        return hours, basis
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        errors.append(_err("bad_number", field, "expected a number; use null or \"UNKNOWN\" for a missing value, never blank text"))
        return None, basis
    try:
        number = float(raw) * factor
    except OverflowError:
        number = math.inf
    if not math.isfinite(number) or raw < 0:
        errors.append(_err("bad_number", field, "must be a finite number >= 0 (too large values are rejected)"))
        return None, basis
    return number, basis


def validate_case(case, index=0):
    """Return (errors, normalized). normalized is None when errors exist."""
    errors = []
    where = f"cases[{index}]"
    if not isinstance(case, dict):
        return [_err("bad_case", where, "case must be an object")], None
    unknown = set(case) - CASE_KEYS
    if unknown:
        errors.append(_err("unknown_key", where, f"unknown keys {sorted(unknown)}"))
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not _ID.fullmatch(case_id):
        errors.append(_err("bad_case_id", f"{where}.case_id", "use 1-64 letters, digits, '_', '.', '-' (no names, e-mail or paths)"))
        case_id = None
    label = case_id or where
    call_type = case.get("call_type")
    if not _member(call_type, CALL_TYPES):
        errors.append(_err("bad_call_type", f"{label}.call_type", f"must be one of {list(CALL_TYPES)}"))
    unit = case.get("unit")
    if not _member(unit, UNITS):
        errors.append(_err("bad_unit", f"{label}.unit", f"must be one of {list(UNITS)}; units are never mixed inside a case"))
    factor = UNITS[unit] if _member(unit, UNITS) else 1.0

    source = case.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("kind"), str) or not source.get("kind"):
        errors.append(_err("bad_source", f"{label}.source", "source.kind is required (e.g. 'synthetic', 'operator_log', 'interview')"))
    else:
        for key in ("kind", "reference", "description"):
            _check_text(errors, f"{label}.source.{key}", source.get(key))
        obtained = source.get("obtained_on")
        if obtained not in (None, ""):
            try:
                dt.date.fromisoformat(obtained)
            except (TypeError, ValueError):
                errors.append(_err("bad_date", f"{label}.source.obtained_on", "use a calendar date such as 2026-10-08"))
        extra = set(source) - {"kind", "reference", "description", "obtained_on"}
        if extra:
            errors.append(_err("unknown_key", f"{label}.source", f"unknown keys {sorted(extra)}"))
    disclosure = case.get("disclosure")
    scope, permission = "unknown", None
    if disclosure is not None:
        if not isinstance(disclosure, dict) or not _member(disclosure.get("scope"), SCOPES):
            errors.append(_err("bad_disclosure", f"{label}.disclosure", f"disclosure.scope must be one of {list(SCOPES)}"))
        else:
            scope = disclosure["scope"]
            permission = _check_text(errors, f"{label}.disclosure.permission_basis", disclosure.get("permission_basis"))
            if scope == "public_ok" and not permission:
                errors.append(_err("no_permission_basis", f"{label}.disclosure", "scope public_ok needs a permission_basis text"))
    _check_text(errors, f"{label}.notes", case.get("notes"))

    confirmations = case.get("confirmations")
    if confirmations is None:
        confirmations = {}
    required_conf = CONFIRMATIONS.get(call_type, ()) if _member(call_type, CONFIRMATIONS) else ()
    if not isinstance(confirmations, dict) or set(confirmations) - set(required_conf) or any(not isinstance(v, bool) for v in confirmations.values()):
        errors.append(_err("bad_confirmations", f"{label}.confirmations", f"only these true/false keys are allowed: {list(required_conf)}"))
        confirmations = {}

    values = case.get("values")
    if not isinstance(values, dict):
        errors.append(_err("bad_values", f"{label}.values", "values must be an object"))
        values = {}
    existing = call_type == "existing_cargo_call"
    dedicated = call_type == "dedicated_bunker_call"
    durations = EXISTING_DURATIONS if existing else DEDICATED_DURATIONS if dedicated else ()
    events = EXISTING_EVENTS + EXISTING_OPTIONAL_EVENTS if existing else ()
    allowed = set(durations) | set(events)
    for name in values:
        if name not in allowed:
            hint = (" Work durations and reported times are not extra departure delay; enter the phase durations and event times instead."
                    if name in DELAY_LIKE else "")
            errors.append(_err("unknown_field", f"{label}.values.{name}", f"not an input of {call_type}.{hint}"))

    mode, reference = None, None
    if existing:
        mode = case.get("time_mode")
        if not _member(mode, TIME_MODES):
            errors.append(_err("bad_time_mode", f"{label}.time_mode", f"must be one of {list(TIME_MODES)}"))
        if mode == "absolute":
            if case.get("reference_time") not in (None, ""):
                reference = _parse_instant(case.get("reference_time"), f"{label}.reference_time", errors)
        elif case.get("reference_time") is not None:
            errors.append(_err("unexpected_reference", f"{label}.reference_time", "reference_time is only used with time_mode 'absolute'"))
    elif dedicated and (case.get("time_mode") is not None or case.get("reference_time") is not None):
        errors.append(_err("unexpected_field", label, "dedicated_bunker_call has no event times; remove time_mode/reference_time"))

    hours, basis = {}, {}
    for name in durations:
        hours[name], basis[name] = _read_value(values.get(name), f"{label}.values.{name}", unit, factor, False, mode, reference, errors)
    for name in events:
        hours[name], basis[name] = _read_value(values.get(name), f"{label}.values.{name}", unit, factor, True, mode, reference, errors)

    if existing:  # physical time order, checked only for values that were given
        # Only the cargo/berth timeline is ordered. Bunkering may overlap cargo work, start before or after it, start
        # before berthing (anchorage / STS) or after cargo has finished, so bunker_ready is deliberately not ordered here.
        # baseline_departure is a counterfactual (departure without bunkering) while the other events are the actual,
        # bunkering-affected ones, so it is deliberately not ordered against them either.
        order = (("berth_arrival", "cargo_start"), ("cargo_start", "cargo_end_with_bunkering"),
                 ("berth_arrival", "cargo_end_with_bunkering"))
        for early, late in order:
            if hours.get(early) is not None and hours.get(late) is not None and hours[early] > hours[late]:
                errors.append(_err("time_order", f"{label}.values", f"{early} must not be later than {late}"))

    if errors:
        return errors, None
    return [], {"case_id": case_id, "call_type": call_type, "unit": unit, "time_mode": mode, "hours": hours, "basis": basis,
                "confirmations": {k: bool(confirmations.get(k, False)) for k in required_conf},
                "scope": scope, "permission_basis": permission, "durations": durations,
                "required": EXISTING_EVENTS + EXISTING_DURATIONS if existing else DEDICATED_DURATIONS}


# ------------------------------------------------------------------ calculation hand-off

def evaluate(norm):
    """Compute only when every required input is known and the confirmations are given."""
    result = {"case_id": norm["case_id"], "call_type": norm["call_type"], "status": None, "extra_delay_hours": None,
              "missing_fields": [], "reasons": [], "warnings": [], "unit_entered": norm["unit"], "result_unit": "hours",
              "evidence_level": None, "input_basis": {}, "disclosure_scope": norm["scope"],
              "publication_allowed": norm["scope"] == "public_ok" and bool(norm["permission_basis"]),
              "interpretation": "extra_delay_hours is the delay of departure relative to the stated no-bunkering baseline; "
                                "a reported work duration is not used as delay"}
    result["confirmations"] = {"kind": "user_attested", "verified_by_code": False, "items": dict(norm["confirmations"])}
    result["not_verified_by_code"] = ("the meaning of every confirmation (counterfactual departure, interruption included, no phase counted twice, ...) "
                                      "and whether the values are true; evidence_level only reflects the declared basis")
    hours = norm["hours"]
    required = norm["required"]
    missing = [name for name in required if hours.get(name) is None]
    unconfirmed = [k for k, v in norm["confirmations"].items() if not v]
    result["code_verified_checks"] = (list(CODE_VERIFIED_CHECKS)
                                      + (["timestamps carry explicit UTC offsets"] if norm["time_mode"] == "absolute" else [])
                                      + ([] if missing else ["all required inputs are present (UNKNOWN is never replaced by 0)"]))
    if missing:
        result["missing_fields"] = missing
        result["reasons"].append("missing required inputs: " + ", ".join(missing) + " (UNKNOWN is never replaced by 0)")
    if unconfirmed:
        result["reasons"].append("confirmations not given (set true only after checking): " + ", ".join(unconfirmed))
    if not result["publication_allowed"]:
        result["warnings"].append("disclosure scope does not allow publication; keep this record and its result out of public repositories")
    used = {name: norm["basis"].get(name) for name in required if hours.get(name) is not None}
    result["input_basis"] = used
    if used:
        result["evidence_level"] = max(used.values(), key=lambda b: _RANK.get(b, 0))
    if any(hours.get(n) is not None and hours[n] > LARGE_DURATION_HOURS for n in norm["durations"]):
        result["warnings"].append(f"a duration exceeds {LARGE_DURATION_HOURS:g} h; check that the unit is correct")
    base_basis = norm["basis"].get("baseline_departure")
    if norm["call_type"] == "existing_cargo_call" and base_basis not in (None, "observed"):
        text = {"estimate": "baseline_departure is an ESTIMATE, so the extra delay depends on that estimate",
                "stakeholder_statement": "baseline_departure comes from a stakeholder statement, not an observation",
                "synthetic_assumption": "baseline_departure is a synthetic assumption"}[base_basis]
        result["warnings"].append(text)
    if missing or unconfirmed:
        result["status"] = "NOT_COMPUTED"
        return result
    if norm["call_type"] == "existing_cargo_call":
        delay = model.existing_call(**{n: hours[n] for n in model_inputs("existing_cargo_call")})
        ready_end = hours["bunker_ready"] + hours["preparation"] + hours["transfer"] + hours["cleanup"]
        parts = {"baseline_departure": hours["baseline_departure"], "cargo_end_with_bunkering": hours["cargo_end_with_bunkering"],
                 "bunker_completion": ready_end}
        result["breakdown_hours"] = parts
        result["binding_constraint"] = max(parts, key=parts.get) if delay.extra_hours else "baseline_departure"
    else:
        delay = model.dedicated_call(**{n: hours[n] for n in model_inputs("dedicated_bunker_call")})
    result["status"] = "COMPUTED"
    result["extra_delay_hours"] = delay.extra_hours
    return result


def model_inputs(call_type):
    return EXISTING_EVENTS + EXISTING_DURATIONS if call_type == "existing_cargo_call" else DEDICATED_DURATIONS


def process(paths, compute):
    results, seen = [], set()
    for path in paths:
        data = load_file(path)
        for i, case in enumerate(data["cases"]):
            try:
                errors, norm = validate_case(case, i)
            except Exception as exc:  # safety net: one malformed case must not stop the run
                errors, norm = [_err("internal_error", f"cases[{i}]", f"could not be validated ({type(exc).__name__}); fix the input shape")], None
            case_id = case.get("case_id") if isinstance(case, dict) else None
            if norm is not None and norm["case_id"] in seen:
                errors, norm = [_err("duplicate_case_id", norm["case_id"], "case_id appears more than once in this run")], None
            if norm is None:
                results.append({"case_id": case_id if isinstance(case_id, str) else None, "source_file": Path(path).name,
                                "status": "INVALID", "errors": errors})
                continue
            seen.add(norm["case_id"])
            try:
                result = evaluate(norm) if compute else {"case_id": norm["case_id"], "status": "VALID"}
                if compute and result.get("extra_delay_hours") is not None and not math.isfinite(result["extra_delay_hours"]):
                    raise OverflowError("non-finite result")
            except (ArithmeticError, ValueError) as exc:  # e.g. individually valid but astronomically large values
                results.append({"case_id": norm["case_id"], "source_file": Path(path).name, "status": "INVALID",
                                "errors": [_err("calculation_error", norm["case_id"],
                                                f"the calculation failed ({type(exc).__name__}: {exc}); the values are too large to be plausible")]})
                continue
            if not compute:
                result["missing_fields"] = [n for n in norm["required"] if norm["hours"].get(n) is None]
            result["source_file"] = Path(path).name
            results.append(result)
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"schema_version": SCHEMA_VERSION, "summary": counts, "notice": PRIVACY_NOTICE,
            "publication_allowed": bool(results) and all(r.get("publication_allowed") for r in results),
            "results": results}


# ------------------------------------------------------------------ template + CLI

def template(call_type, time_mode="offset", unit="hours"):
    existing = call_type == "existing_cargo_call"
    event = {"at": None, "basis": None} if time_mode == "absolute" else {"value": None, "basis": None}
    values = {}
    if existing:
        for name in EXISTING_EVENTS + EXISTING_OPTIONAL_EVENTS:
            values[name] = dict(event)
        for name in EXISTING_DURATIONS:
            values[name] = {"value": None, "basis": None}
    else:
        for name in DEDICATED_DURATIONS:
            values[name] = {"value": None, "basis": None}
    case = {"case_id": "CHANGE-ME", "call_type": call_type, "unit": unit}
    if existing:
        case["time_mode"] = time_mode
        if time_mode == "absolute":
            case["reference_time"] = None
    case.update({"source": {"kind": "CHANGE-ME", "reference": "", "obtained_on": ""},
                 "disclosure": {"scope": "unknown", "permission_basis": ""},
                 "confirmations": {k: False for k in CONFIRMATIONS[call_type]}, "values": values, "notes": ""})
    return {"schema_version": SCHEMA_VERSION, "cases": [case]}


def _writable(out_path, report):
    if report["publication_allowed"]:
        return True
    return "private" in Path(out_path).resolve().parts


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m research.port_call_time.intake", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("template", help="print a blank case file (all values UNKNOWN)")
    t.add_argument("--call-type", choices=CALL_TYPES, required=True)
    t.add_argument("--time-mode", choices=TIME_MODES, default="offset")
    t.add_argument("--unit", choices=tuple(UNITS), default="hours")
    for name, text in (("validate", "check files; no calculation"), ("compute", "validate, then calculate complete cases")):
        p = sub.add_parser(name, help=text)
        p.add_argument("files", nargs="+")
        if name == "compute":
            p.add_argument("--out", help="write the JSON report here (non-public data only under a directory named 'private')")
    args = parser.parse_args(argv)
    if args.command == "template":
        print(json.dumps(template(args.call_type, args.time_mode, args.unit), indent=2, ensure_ascii=False))
        return 0
    try:
        report = process(args.files, compute=args.command == "compute")
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2, ensure_ascii=False)
    out = getattr(args, "out", None)
    if out:
        if not _writable(out, report):
            print("error: some cases are not cleared for publication; non-public results may only be written under a "
                  "directory named 'private/'. Only research/port_call_time/private/ is git-ignored, any other 'private/' folder is not, "
                  "and git-ignore never protects already-tracked files. Writing nothing.", file=sys.stderr)
            return 2
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 2 if report["summary"].get("INVALID") else 0


if __name__ == "__main__":
    sys.exit(main())
