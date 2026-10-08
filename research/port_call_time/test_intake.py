"""Tests for the port-call time intake tool.

Expected values are hand-calculated literals (see INTAKE.md), not recomputed with model.py.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from research.port_call_time import intake

HERE = Path(__file__).parent
EXAMPLES = HERE / "examples"
REPO = HERE.parents[1]
S = "synthetic_assumption"


def val(x, basis=S):
    return {"value": x, "basis": basis}


def existing(values=None, **overrides):
    case = {
        "case_id": "T-1", "call_type": "existing_cargo_call", "unit": "hours", "time_mode": "offset",
        "source": {"kind": "synthetic", "reference": "unit test", "obtained_on": "2026-10-08"},
        "disclosure": {"scope": "public_ok", "permission_basis": "synthetic"},
        "confirmations": {k: True for k in intake.CONFIRMATIONS["existing_cargo_call"]},
        "values": {"baseline_departure": val(12), "cargo_end_with_bunkering": val(12), "bunker_ready": val(0),
                   "preparation": val(1), "transfer": val(8), "cleanup": val(1)},
    }
    if values:
        case["values"].update(values)
    case.update(overrides)
    return case


def dedicated(values=None, **overrides):
    case = {
        "case_id": "T-D", "call_type": "dedicated_bunker_call", "unit": "hours",
        "source": {"kind": "synthetic"}, "disclosure": {"scope": "public_ok", "permission_basis": "synthetic"},
        "confirmations": {k: True for k in intake.CONFIRMATIONS["dedicated_bunker_call"]},
        "values": {"detour": val(2), "port_transit": val(1), "waiting": val(1), "preparation": val(1),
                   "transfer": val(8), "cleanup": val(1)},
    }
    if values:
        case["values"].update(values)
    case.update(overrides)
    return case


def run_case(case):
    errors, norm = intake.validate_case(case)
    return errors, (intake.evaluate(norm) if norm else None)


def codes(errors):
    return {e["code"] for e in errors}


def write(tmp_path, cases, name="in.json", raw=None):
    path = tmp_path / name
    path.write_text(raw if raw is not None else json.dumps({"schema_version": 1, "cases": cases}), encoding="utf-8")
    return path


# ------------------------------------------------------------ hand-calculated examples
# Hand calculation (hours, origin = berth arrival):
#  01 simultaneous : ready 0 + 1 + 8 + 1 = 10 <= 12            -> max(12, 12, 10) - 12 = 0
#  02 late start   : ready 6 + 1 + 8 + 1 = 16                  -> max(12, 12, 16) - 12 = 4
#  03 interrupted  : cargo end 15, fuel end 0+1+6+1 = 8        -> max(12, 15, 8) - 12 = 3
#  04 dedicated    : 2 + 1 + 1 + 1 + 8 + 1                     = 14
#  05 insufficient : transfer, cleanup unknown                 -> not computed
#  06 absolute     : ref 20:00+09:00; ready 2030-03-01T15:30Z = 00:30+09:00 next day = 4.5 h after ref;
#                    departure/cargo end 08:00+09:00 = 12 h after ref; fuel end 4.5+1+8+1 = 14.5 -> 14.5 - 12 = 2.5
HAND = {
    "SYN-01-SIMULTANEOUS": ("COMPUTED", 0.0, "baseline_departure"),
    "SYN-02-LATE-START": ("COMPUTED", 4.0, "bunker_completion"),
    "SYN-03-CARGO-INTERRUPTED": ("COMPUTED", 3.0, "cargo_end_with_bunkering"),
    "SYN-04-DEDICATED": ("COMPUTED", 14.0, None),
    "SYN-05-INSUFFICIENT": ("NOT_COMPUTED", None, None),
    "SYN-06-ABSOLUTE-MIDNIGHT": ("COMPUTED", 2.5, "bunker_completion"),
}


def test_every_example_matches_the_hand_calculation():
    report = intake.process(sorted(EXAMPLES.glob("*.json")), compute=True)
    got = {r["case_id"]: r for r in report["results"]}
    assert set(got) == set(HAND)
    for case_id, (status, extra, binding) in HAND.items():
        r = got[case_id]
        assert r["status"] == status, case_id
        assert r["extra_delay_hours"] == extra, case_id
        assert r.get("binding_constraint") == binding, case_id
    assert got["SYN-05-INSUFFICIENT"]["missing_fields"] == ["transfer", "cleanup"]
    assert report["summary"] == {"COMPUTED": 5, "NOT_COMPUTED": 1}


def test_reported_work_duration_is_not_the_delay():
    # 10 h of fuel work (1 + 8 + 1) inside a 12 h cargo window adds no departure delay.
    _, result = run_case(existing())
    assert result["extra_delay_hours"] == 0.0 and result["breakdown_hours"]["bunker_completion"] == 10.0


def test_examples_are_entirely_synthetic_and_contain_no_personal_data():
    for path in EXAMPLES.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not intake._personal_data(text.replace("2030-03-02T08:00:00+09:00", "")), path.name
        data = json.loads(text)
        for case in data["cases"]:
            assert case["source"]["kind"] == "synthetic" and case["disclosure"]["scope"] == "public_ok"
            bases = {spec["basis"] for spec in case["values"].values() if isinstance(spec, dict) and spec.get("basis")}
            assert bases == {S}, path.name
            assert case["case_id"].startswith("SYN-")


# ------------------------------------------------------------ missing values are UNKNOWN, never 0
@pytest.mark.parametrize("missing", ["transfer", "cleanup", "preparation", "bunker_ready", "baseline_departure", "cargo_end_with_bunkering"])
@pytest.mark.parametrize("how", ["null", "unknown_text", "null_value", "absent"])
def test_missing_existing_input_is_unknown_not_zero(missing, how):
    case = existing()
    if how == "null":
        case["values"][missing] = None
    elif how == "unknown_text":
        case["values"][missing] = "unknown"
    elif how == "null_value":
        case["values"][missing] = {"value": None, "basis": None}
    else:
        del case["values"][missing]
    errors, result = run_case(case)
    assert not errors
    assert result["status"] == "NOT_COMPUTED" and result["extra_delay_hours"] is None
    assert result["missing_fields"] == [missing]


def test_explicit_zero_is_a_value_and_differs_from_missing():
    _, zero = run_case(existing({"bunker_ready": val(0)}))
    assert zero["status"] == "COMPUTED"
    _, none = run_case(existing({"bunker_ready": None}))
    assert none["status"] == "NOT_COMPUTED"


@pytest.mark.parametrize("missing", ["detour", "port_transit", "waiting", "preparation", "transfer", "cleanup"])
def test_dedicated_call_needs_every_phase(missing):
    case = dedicated()
    case["values"][missing] = None
    _, result = run_case(case)
    assert result["status"] == "NOT_COMPUTED" and result["missing_fields"] == [missing]


def test_not_computed_lists_reasons_and_unconfirmed_items():
    case = existing({"transfer": None})
    case["confirmations"]["cleanup_includes_all_remaining_bunker_work"] = False
    _, result = run_case(case)
    assert result["status"] == "NOT_COMPUTED"
    text = " ".join(result["reasons"])
    assert "transfer" in text and "never replaced by 0" in text and "cleanup_includes_all_remaining_bunker_work" in text


def test_double_counting_confirmation_is_required_for_dedicated_calls():
    case = dedicated()
    del case["confirmations"]["no_phase_counted_twice"]
    _, result = run_case(case)
    assert result["status"] == "NOT_COMPUTED" and result["extra_delay_hours"] is None
    assert any("no_phase_counted_twice" in r for r in result["reasons"])


# ------------------------------------------------------------ invalid numbers and units
@pytest.mark.parametrize("bad", [-1, -0.5, True, False, "8", "", [8], {"x": 1}])
def test_bad_numbers_are_rejected(bad):
    errors, _ = intake.validate_case(existing({"transfer": {"value": bad, "basis": S}}))
    assert errors and codes(errors) & {"bad_number"}, bad


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_constants_are_rejected(tmp_path, token):
    raw = json.dumps({"schema_version": 1, "cases": [existing()]}).replace('"transfer": {"value": 8', f'"transfer": {{"value": {token}')
    assert token in raw
    with pytest.raises(intake.IntakeError):
        intake.load_file(write(tmp_path, [], raw=raw))


def test_duplicate_keys_are_rejected(tmp_path):
    with pytest.raises(intake.IntakeError, match="duplicate"):
        intake.load_file(write(tmp_path, [], raw='{"schema_version": 1, "cases": [], "cases": []}'))


def test_bare_numbers_without_basis_are_rejected():
    errors, _ = intake.validate_case(existing({"transfer": 8}))
    assert "bare_value" in codes(errors)


def test_a_value_needs_a_valid_basis():
    for spec in ({"value": 8}, {"value": 8, "basis": "guess"}):
        errors, _ = intake.validate_case(existing({"transfer": spec}))
        assert "bad_basis" in codes(errors)


def test_mixed_units_are_rejected_and_minutes_convert_exactly():
    errors, _ = intake.validate_case(existing({"transfer": {"value": 480, "basis": S, "unit": "minutes"}}))
    assert "mixed_units" in codes(errors)
    # same record as example 01 entered in minutes: 12 h = 720, 1 h = 60, 8 h = 480
    case = existing(unit="minutes", values={"baseline_departure": val(720), "cargo_end_with_bunkering": val(720),
                                            "bunker_ready": val(0), "preparation": val(60), "transfer": val(480), "cleanup": val(60)})
    errors, result = run_case(case)
    assert not errors and result["extra_delay_hours"] == 0.0 and result["unit_entered"] == "minutes"
    case["values"]["bunker_ready"] = val(360)  # late start of example 02 (6 h)
    _, result = run_case(case)
    assert result["extra_delay_hours"] == 4.0 and result["result_unit"] == "hours"


@pytest.mark.parametrize("unit", [None, "days", "h", "HOURS"])
def test_unit_must_be_declared(unit):
    case = existing()
    case["unit"] = unit
    errors, _ = intake.validate_case(case)
    assert "bad_unit" in codes(errors)


def test_a_very_long_duration_triggers_a_unit_check_warning():
    _, result = run_case(existing({"transfer": val(500)}))
    assert any("unit" in w for w in result["warnings"])


# ------------------------------------------------------------ absolute times, zones, midnight, order
def absolute(values, **overrides):
    case = existing(time_mode="absolute", reference_time="2030-03-01T20:00:00+09:00")
    case["values"] = {"preparation": val(1), "transfer": val(8), "cleanup": val(1)}
    case["values"].update(values)
    case.update(overrides)
    return case


def at(text):
    return {"at": text, "basis": S}


def test_naive_timestamps_are_rejected():
    errors, _ = intake.validate_case(absolute({"bunker_ready": at("2030-03-02T00:30:00")}))
    assert "naive_time" in codes(errors)
    errors, _ = intake.validate_case(absolute({}, reference_time="2030-03-01T20:00:00"))
    assert "naive_time" in codes(errors)
    errors, _ = intake.validate_case(absolute({"bunker_ready": at("2030-03-02")}))
    assert codes(errors) & {"bad_time", "naive_time"}


def test_midnight_crossing_and_mixed_time_zones_are_exact():
    # 20:00+09:00 = 11:00Z. Events: 2030-03-02T00:30+09:00 = 15:30Z (4.5 h), 2030-03-02T08:00+09:00 (12 h)
    vals = {"baseline_departure": at("2030-03-01T23:00:00Z"), "cargo_end_with_bunkering": at("2030-03-02T08:00:00+09:00"),
            "bunker_ready": at("2030-03-02T00:30:00+09:00")}
    errors, result = run_case(absolute(vals))
    assert not errors
    assert result["breakdown_hours"] == {"baseline_departure": 12.0, "cargo_end_with_bunkering": 12.0, "bunker_completion": 14.5}
    assert result["extra_delay_hours"] == 2.5


def test_an_absolute_time_needs_a_reference_time_but_unknown_events_do_not():
    case = absolute({"bunker_ready": at("2030-03-02T00:30:00+09:00")}, reference_time=None)
    errors, _ = intake.validate_case(case)
    assert "missing_reference" in codes(errors)
    errors, result = run_case(absolute({}, reference_time=None))  # no absolute value given yet: all UNKNOWN
    assert not errors and result["status"] == "NOT_COMPUTED"


def test_an_event_before_the_reference_time_is_rejected():
    errors, _ = intake.validate_case(absolute({"bunker_ready": at("2030-03-01T19:00:00+09:00")}))
    assert "before_reference" in codes(errors)


def test_time_mode_and_value_keys_must_agree():
    errors, _ = intake.validate_case(absolute({"bunker_ready": val(4.5)}))
    assert "wrong_value_key" in codes(errors)
    errors, _ = intake.validate_case(existing({"bunker_ready": at("2030-03-02T00:30:00+09:00")}))
    assert "wrong_value_key" in codes(errors)
    errors, _ = intake.validate_case(absolute({"transfer": at("2030-03-02T00:30:00+09:00")}))
    assert "wrong_value_key" in codes(errors)  # durations never take timestamps
    errors, _ = intake.validate_case(existing(reference_time="2030-03-01T20:00:00+09:00"))
    assert "unexpected_reference" in codes(errors)


# Each case lists two events whose order is physically impossible (the "late" one is earlier than the "early" one).
WRONG_ORDER = [
    ("berth_arrival", 5, "cargo_start", 3),
    ("berth_arrival", 5, "cargo_end_with_bunkering", 3),
    ("cargo_start", 5, "cargo_end_with_bunkering", 3),
]


@pytest.mark.parametrize("early,early_at,late,late_at", WRONG_ORDER)
def test_wrong_time_order_is_rejected(early, early_at, late, late_at):
    errors, _ = intake.validate_case(existing({early: val(early_at), late: val(late_at)}))
    assert "time_order" in codes(errors), (early, late)
    # the same two events in the right order are accepted
    errors, _ = intake.validate_case(existing({early: val(0), late: val(late_at)}))
    assert "time_order" not in codes(errors)


# Cargo and bunkering may overlap or start in either order. Hand calculation for every row below (hours):
#  fuel end = bunker_ready + preparation + transfer + cleanup; extra = max(baseline_departure, cargo_end, fuel end) - baseline_departure
OVERLAP = [
    # name, values, hand-calculated extra delay
    ("fuel starts before cargo start", {"cargo_start": val(5), "bunker_ready": val(1), "preparation": val(1), "transfer": val(2), "cleanup": val(1)}, 0.0),   # fuel end 5 <= 12
    ("fuel finishes before cargo even starts", {"cargo_start": val(5), "bunker_ready": val(0), "preparation": val(1), "transfer": val(2), "cleanup": val(0)}, 0.0),  # fuel end 3
    ("fuel starts before berthing (anchorage / STS)", {"berth_arrival": val(4), "cargo_start": val(5), "bunker_ready": val(1), "preparation": val(1), "transfer": val(2), "cleanup": val(1)}, 0.0),  # fuel end 5
    ("fuel starts during cargo", {"cargo_start": val(2), "bunker_ready": val(6), "preparation": val(1), "transfer": val(2), "cleanup": val(1)}, 0.0),  # fuel end 10 <= 12
    ("fuel runs past cargo end", {"cargo_start": val(2), "bunker_ready": val(6), "preparation": val(1), "transfer": val(8), "cleanup": val(1)}, 4.0),  # fuel end 16 -> 16 - 12
    ("fuel starts after cargo has ended", {"cargo_start": val(2), "bunker_ready": val(14), "preparation": val(1), "transfer": val(3), "cleanup": val(1)}, 7.0),  # fuel end 19 -> 19 - 12
    ("fuel starts after the no-bunkering departure time", {"cargo_start": val(2), "bunker_ready": val(13), "preparation": val(0), "transfer": val(1), "cleanup": val(0)}, 2.0),  # fuel end 14 -> 14 - 12
]


@pytest.mark.parametrize("name,values,expected", OVERLAP, ids=[o[0] for o in OVERLAP])
def test_cargo_and_bunkering_may_overlap_or_start_in_any_order(name, values, expected):
    errors, result = run_case(existing(values))
    assert not errors, errors
    assert result["status"] == "COMPUTED" and result["extra_delay_hours"] == expected


def test_no_order_is_enforced_between_bunker_ready_and_the_cargo_events():
    from itertools import product
    for ready, start in product((0, 3, 6, 20), (0, 3, 6, 20)):
        errors, _ = intake.validate_case(existing({"cargo_start": val(start), "bunker_ready": val(ready),
                                                   "cargo_end_with_bunkering": val(max(start, 12)), "baseline_departure": val(max(start, 12))}))
        assert not errors, (ready, start)


def test_wrong_order_in_absolute_mode_is_rejected_after_zone_conversion():
    # 01:00+09:00 is 16:00Z the previous day: the cargo start (16:30Z) is LATER than the berth arrival (16:00Z) -> fine;
    # swapping the two violates the order even though the clock digits look ascending.
    ok = absolute({"berth_arrival": at("2030-03-02T01:00:00+09:00"), "cargo_start": at("2030-03-01T16:30:00Z"),
                   "baseline_departure": at("2030-03-02T08:00:00+09:00"), "cargo_end_with_bunkering": at("2030-03-02T08:00:00+09:00"),
                   "bunker_ready": at("2030-03-02T02:00:00+09:00")})
    errors, _ = intake.validate_case(ok)
    assert not errors
    bad = copy.deepcopy(ok)
    bad["values"]["cargo_start"] = at("2030-03-01T15:30:00Z")  # 00:30+09:00, before the 01:00+09:00 arrival
    errors, _ = intake.validate_case(bad)
    assert "time_order" in codes(errors)


def test_optional_order_fields_are_only_checks():
    ok, result = run_case(existing({"berth_arrival": val(0), "cargo_start": val(1)}))
    assert not ok and result["status"] == "COMPUTED" and result["extra_delay_hours"] == 0.0


# ------------------------------------------------------------ schema strictness, hints, hygiene
@pytest.mark.parametrize("name", ["extra_delay_hours", "work_hours", "reported_duration", "delay"])
def test_work_duration_or_delay_fields_are_refused_with_a_hint(name):
    errors, _ = intake.validate_case(existing({name: val(10)}))
    assert "unknown_field" in codes(errors)
    assert any("not extra departure delay" in e["message"] for e in errors)


def test_unknown_keys_and_wrong_fields_for_the_call_type_are_rejected():
    errors, _ = intake.validate_case(existing(surprise=1))
    assert "unknown_key" in codes(errors)
    errors, _ = intake.validate_case(dedicated({"bunker_ready": val(1)}))
    assert "unknown_field" in codes(errors)
    errors, _ = intake.validate_case(dedicated(time_mode="offset"))
    assert "unexpected_field" in codes(errors)
    errors, _ = intake.validate_case(existing(call_type="other"))
    assert "bad_call_type" in codes(errors)


@pytest.mark.parametrize("cid", ["", "a b", "../x", "kim@example.com", "x" * 65, None, 5])
def test_case_ids_cannot_carry_names_paths_or_addresses(cid):
    errors, _ = intake.validate_case(existing(case_id=cid))
    assert "bad_case_id" in codes(errors)


@pytest.mark.parametrize("text", ["contact kim@example.com", "call +82 10 1234 5678", "tel 010-1234-5678", "02-123-4567"])
def test_email_addresses_and_phone_numbers_are_refused_in_free_text(text):
    for place in ("notes", "source", "permission", "value_note"):
        case = existing()
        if place == "notes":
            case["notes"] = text
        elif place == "source":
            case["source"]["description"] = text
        elif place == "permission":
            case["disclosure"]["permission_basis"] = text
        else:
            case["values"]["transfer"]["note"] = text
        errors, _ = intake.validate_case(case)
        assert "personal_data" in codes(errors), (place, text)


def test_iso_dates_and_plain_numbers_are_not_mistaken_for_phone_numbers():
    case = existing(notes="obtained 2026-10-08, durations 8 10 14 hours")
    errors, _ = intake.validate_case(case)
    assert not errors


def test_source_date_must_be_a_calendar_date():
    case = existing()
    case["source"]["obtained_on"] = "yesterday"
    errors, _ = intake.validate_case(case)
    assert "bad_date" in codes(errors)


# ------------------------------------------------------------ evidence level and disclosure
def test_confirmations_are_reported_as_user_attested_and_not_verified_by_code():
    _, result = run_case(existing())
    assert result["confirmations"]["kind"] == "user_attested" and result["confirmations"]["verified_by_code"] is False
    assert set(result["confirmations"]["items"]) == set(intake.CONFIRMATIONS["existing_cargo_call"])
    assert all(result["confirmations"]["items"].values())
    checks = " ".join(result["code_verified_checks"])
    assert "finite" in checks and "unit" in checks and "order" in checks and "UTC offsets" not in checks
    assert "meaning of every confirmation" in result["not_verified_by_code"]
    _, abs_result = run_case(absolute({"baseline_departure": at("2030-03-02T08:00:00+09:00"),
                                       "cargo_end_with_bunkering": at("2030-03-02T08:00:00+09:00"), "bunker_ready": at("2030-03-02T00:30:00+09:00")}))
    assert any("UTC offsets" in c for c in abs_result["code_verified_checks"])
    # also visible for NOT_COMPUTED, where an unchecked box is reported as false
    case = existing({"transfer": None})
    case["confirmations"]["no_such"] = True
    errors, _ = intake.validate_case(case)
    assert "bad_confirmations" in codes(errors)
    case = existing({"transfer": None})
    case["confirmations"]["cleanup_includes_all_remaining_bunker_work"] = False
    _, partial = run_case(case)
    assert partial["status"] == "NOT_COMPUTED" and partial["confirmations"]["items"]["cleanup_includes_all_remaining_bunker_work"] is False


def test_the_report_states_the_limits_of_the_privacy_checks(tmp_path):
    report = intake.process([write(tmp_path, [existing()])], compute=True)
    notice = report["notice"]
    assert "not complete detection" in notice and "already tracked" in notice and "git add -f" in notice


def test_documentation_states_the_limits_and_the_checked_rules():
    text = (HERE / "INTAKE.md").read_text(encoding="utf-8") + (HERE / "README.md").read_text(encoding="utf-8")
    for needle in ("완전한 탐지가 아니", "이미 추적", "git add -f", "사용자 확인", "코드가 검증하지", "겹칠 수", "묘박지"):
        assert needle in text, needle


def test_estimated_baseline_is_flagged_in_the_result():
    case = existing({"baseline_departure": {"value": 12, "basis": "estimate"}})
    _, result = run_case(case)
    assert result["status"] == "COMPUTED" and result["extra_delay_hours"] == 0.0
    assert result["input_basis"]["baseline_departure"] == "estimate"
    assert any("ESTIMATE" in w for w in result["warnings"])
    assert result["evidence_level"] == "synthetic_assumption"  # weakest basis among the inputs


def test_evidence_level_is_the_weakest_basis_and_observed_baseline_has_no_warning():
    values = {k: {"value": v, "basis": "observed"} for k, v in
              dict(baseline_departure=12, cargo_end_with_bunkering=12, bunker_ready=0, preparation=1, transfer=8, cleanup=1).items()}
    _, result = run_case(existing(values))
    assert result["evidence_level"] == "observed" and not result["warnings"]
    values["transfer"] = {"value": 8, "basis": "stakeholder_statement"}
    _, result = run_case(existing(values))
    assert result["evidence_level"] == "stakeholder_statement"
    values["baseline_departure"] = {"value": 12, "basis": "stakeholder_statement"}
    _, result = run_case(existing(values))
    assert any("stakeholder" in w for w in result["warnings"])


@pytest.mark.parametrize("disclosure", [None, {"scope": "unknown"}, {"scope": "private_do_not_publish"}, {"scope": "project_internal"}])
def test_unclear_or_restricted_disclosure_is_never_publishable(disclosure):
    case = existing()
    if disclosure is None:
        del case["disclosure"]
    else:
        case["disclosure"] = disclosure
    errors, result = run_case(case)
    assert not errors and result["publication_allowed"] is False
    assert any("publication" in w for w in result["warnings"])


def test_public_ok_requires_a_permission_basis_and_a_known_scope():
    errors, _ = intake.validate_case(existing(disclosure={"scope": "public_ok"}))
    assert "no_permission_basis" in codes(errors)
    errors, _ = intake.validate_case(existing(disclosure={"scope": "public"}))
    assert "bad_disclosure" in codes(errors)


def test_nothing_in_the_module_can_reach_the_network():
    source = (HERE / "intake.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(socket|urllib|http|requests|ftplib|smtplib|subprocess|webbrowser)\b", source, re.M)


# ------------------------------------------------------------ files, duplicates, templates, CLI
def test_duplicate_case_ids_in_one_run_are_invalid(tmp_path):
    path = write(tmp_path, [existing(), existing()])
    report = intake.process([path], compute=True)
    assert report["summary"] == {"COMPUTED": 1, "INVALID": 1}
    assert report["results"][1]["errors"][0]["code"] == "duplicate_case_id"


def test_invalid_cases_are_not_computed_but_other_cases_still_are(tmp_path):
    bad = existing(case_id="T-BAD")
    bad["values"]["transfer"] = {"value": -1, "basis": S}
    report = intake.process([write(tmp_path, [existing(), bad])], compute=True)
    states = {r["case_id"]: r["status"] for r in report["results"]}
    assert states == {"T-1": "COMPUTED", "T-BAD": "INVALID"}


@pytest.mark.parametrize("call_type,mode", [("existing_cargo_call", "offset"), ("existing_cargo_call", "absolute"), ("dedicated_bunker_call", "offset")])
def test_templates_validate_but_never_compute(tmp_path, call_type, mode):
    tpl = intake.template(call_type, mode)
    report = intake.process([write(tmp_path, [], raw=json.dumps(tpl))], compute=True)
    result = report["results"][0]
    # CHANGE-ME is a legal id; every value is UNKNOWN, so nothing is computed and nothing is zero
    assert result["status"] == "NOT_COMPUTED" and result["extra_delay_hours"] is None
    assert result["missing_fields"] and result["publication_allowed"] is False


def cli(*args, cwd=REPO):
    return subprocess.run([sys.executable, "-m", "research.port_call_time.intake", *map(str, args)], cwd=cwd, capture_output=True, text=True)


def test_cli_template_validate_compute_round_trip(tmp_path):
    tpl = cli("template", "--call-type", "dedicated_bunker_call")
    assert tpl.returncode == 0
    filled = json.loads(tpl.stdout)
    case = filled["cases"][0]
    case.update(case_id="CLI-1", source={"kind": "synthetic", "obtained_on": "2026-10-08"},
                disclosure={"scope": "public_ok", "permission_basis": "synthetic"},
                confirmations={k: True for k in case["confirmations"]})
    for name, hours in dict(detour=2, port_transit=1, waiting=1, preparation=1, transfer=8, cleanup=1).items():
        case["values"][name] = val(hours)
    path = write(tmp_path, [], raw=json.dumps(filled))
    assert cli("validate", path).returncode == 0
    out = cli("compute", path)
    assert out.returncode == 0
    assert json.loads(out.stdout)["results"][0]["extra_delay_hours"] == 14.0


def test_cli_exit_codes(tmp_path):
    bad = existing()
    bad["values"]["transfer"] = {"value": -1, "basis": S}
    assert cli("compute", write(tmp_path, [bad])).returncode == 2
    assert cli("compute", tmp_path / "missing.json").returncode == 2
    assert cli("compute", write(tmp_path, [], raw="{not json", name="x.json")).returncode == 2
    assert cli("compute", *sorted(EXAMPLES.glob("*.json"))).returncode == 0  # NOT_COMPUTED is not an error


def test_cli_refuses_to_write_non_public_results_outside_a_private_directory(tmp_path):
    private_case = existing(disclosure={"scope": "private_do_not_publish"})
    src = write(tmp_path, [private_case])
    refused = cli("compute", src, "--out", tmp_path / "report.json")
    assert refused.returncode == 2 and not (tmp_path / "report.json").exists()
    allowed = cli("compute", src, "--out", tmp_path / "private" / "report.json")
    assert allowed.returncode == 0 and json.loads((tmp_path / "private" / "report.json").read_text())["publication_allowed"] is False
    public_ok = cli("compute", write(tmp_path, [existing()], name="pub.json"), "--out", tmp_path / "pub_report.json")
    assert public_ok.returncode == 0 and (tmp_path / "pub_report.json").exists()


def test_the_private_input_directory_is_git_ignored():
    ignored = subprocess.run(["git", "check-ignore", "-q", "research/port_call_time/private/real_case.json"], cwd=REPO)
    assert ignored.returncode == 0


def test_calculation_code_is_untouched_by_the_intake_layer():
    """intake.py only calls model.existing_call / model.dedicated_call; it must not redefine them."""
    source = (HERE / "intake.py").read_text(encoding="utf-8")
    assert "model.existing_call(" in source and "model.dedicated_call(" in source
    assert not re.search(r"^def (existing_call|dedicated_call|arrival)\b", source, re.M)


def test_case_input_is_not_mutated_by_validation():
    case = existing()
    before = copy.deepcopy(case)
    intake.validate_case(case)
    assert case == before


def test_counterfactual_baseline_is_not_ordered_against_the_actual_events():
    # baseline 12 (no bunkering); bunkering delayed the actual berthing/cargo: berth 18, cargo 19-22, fuel end 8+1+8+1 = 18.
    # hand calculation: max(12, 22, 18) - 12 = 10
    case = existing({"berth_arrival": val(18), "cargo_start": val(19), "cargo_end_with_bunkering": val(22), "bunker_ready": val(8)})
    errors, norm = intake.validate_case(case)
    assert errors == []
    assert intake.evaluate(norm)["extra_delay_hours"] == 10.0


def test_code_verified_checks_reflect_what_was_actually_checked():
    blank = {"schema_version": 1, "cases": [existing({"transfer": None})]}
    _, norm = intake.validate_case(blank["cases"][0])
    incomplete = intake.evaluate(norm)
    assert incomplete["status"] == "NOT_COMPUTED"
    assert not any("all required inputs" in c for c in incomplete["code_verified_checks"])
    _, norm = intake.validate_case(existing())
    assert any("all required inputs" in c for c in intake.evaluate(norm)["code_verified_checks"])


MALFORMED = [
    ("unit_list", {"unit": []}), ("unit_object", {"unit": {}}), ("call_type_list", {"call_type": []}),
    ("time_mode_list", {"time_mode": []}), ("scope_list", {"disclosure": {"scope": []}}),
    ("basis_list", {"values": {"transfer": {"value": 1, "basis": []}}}),
    ("huge_int", {"values": {"transfer": {"value": 10 ** 400, "basis": "synthetic_assumption"}}}),
    ("float_literal_1e400_is_infinity", {"values": {"transfer": {"value": float("inf"), "basis": "synthetic_assumption"}}}),
    ("negative_huge_int", {"values": {"transfer": {"value": -10 ** 400, "basis": "synthetic_assumption"}}}),
]


@pytest.mark.parametrize("name,patch", MALFORMED, ids=[m[0] for m in MALFORMED])
def test_malformed_input_is_invalid_and_the_next_case_is_still_checked(name, patch, tmp_path):
    bad = existing(case_id="BAD")
    for k, v in patch.items():
        if k == "values":
            bad["values"] = {**bad["values"], **v}
        else:
            bad[k] = v
    good = existing(case_id="GOOD")
    path = tmp_path / "in.json"
    path.write_text(json.dumps({"schema_version": 1, "cases": [bad, good]}).replace("Infinity", "1e400"))
    report = intake.process([str(path)], True)
    by_id = {r["case_id"]: r for r in report["results"]}
    assert by_id["BAD"]["status"] == "INVALID" and by_id["BAD"]["errors"]
    assert by_id["GOOD"]["status"] == "COMPUTED"
