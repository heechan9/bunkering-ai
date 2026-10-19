"""Load and validate the v4 integration config. Unknown keys or units are errors."""
import hashlib
import json
from pathlib import Path

CONTRACT_IDS = {"C01", "C02", "C03", "C04", "C05", "C06"}
STATUSES = {"pending", "accepted", "rejected"}
NATIVE_UNITS = {
    "consumption_per_step": "tank_fraction_per_step",
    "reserve": "tank_fraction",
    "refill_request": "tank_fraction",
    "max_fill": "tank_fraction",
    "tolerance": "tank_fraction",
    "max_steps": "step",
    "n_ports": "count",
}
INTEGRATION_ENUMS = {
    "reserve_phase": {"pre_refill_unclipped"},
    "consumption_known_at_decision": {True, False},
    "terminal_valuation": {"terminal_mark_to_market"},
    "statistics_ddof": {0, 1},
    "seed_status": {"used_reproduction_set", "new_frozen_plan"},
}
TOP_KEYS = {"contract_version", "policy_version", "native_fixed", "integration", "proposed_pending"}
# Seed ranges already evaluated; a "new_frozen_plan" must not reuse them.
USED_RANGES = [(42, 5041), (0, 60000999), (91000000, 91000999)]


class ConfigError(ValueError):
    pass


def _check_keys(section, data, allowed):
    extra = set(data) - set(allowed) - {"_note"}
    missing = set(allowed) - set(data)
    if extra:
        raise ConfigError(f"{section}: unknown keys {sorted(extra)}")
    if missing:
        raise ConfigError(f"{section}: missing keys {sorted(missing)}")


def validate(cfg):
    if not isinstance(cfg, dict):
        raise ConfigError("config must be a JSON object")
    _check_keys("config", cfg, TOP_KEYS)
    if not str(cfg["contract_version"]).startswith("BAI-CONTRACT-v"):
        raise ConfigError("contract_version must start with BAI-CONTRACT-v")
    frozen = cfg["contract_version"] == "BAI-CONTRACT-v1.0"

    _check_keys("native_fixed", cfg["native_fixed"], NATIVE_UNITS)
    for key, unit in NATIVE_UNITS.items():
        item = cfg["native_fixed"][key]
        if item.get("unit") != unit:
            raise ConfigError(f"native_fixed.{key}: unit must be {unit!r}, got {item.get('unit')!r}")
        if item.get("contract_id") not in CONTRACT_IDS:
            raise ConfigError(f"native_fixed.{key}: unknown contract_id {item.get('contract_id')!r}")
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"native_fixed.{key}: value must be numeric")
        if unit.startswith("tank_fraction") and not 0.0 <= value <= 1.0:
            raise ConfigError(f"native_fixed.{key}: tank fraction {value} outside [0, 1]")

    integ = cfg["integration"]
    _check_keys("integration", integ, set(INTEGRATION_ENUMS) | {"seed_range_inclusive"})
    for key, item in integ.items():
        if item.get("contract_id") not in CONTRACT_IDS:
            raise ConfigError(f"integration.{key}: unknown contract_id {item.get('contract_id')!r}")
        if item.get("status") not in STATUSES:
            raise ConfigError(f"integration.{key}: status must be one of {sorted(STATUSES)}")
        if frozen and item["status"] != "accepted":
            raise ConfigError(f"integration.{key}: v1.0 requires accepted, got {item['status']}")
        allowed = INTEGRATION_ENUMS.get(key)
        # bool is an int subclass, so compare type as well as value.
        if allowed is not None and not any(item["value"] == a and type(item["value"]) is type(a) for a in allowed):
            raise ConfigError(f"integration.{key}: {item['value']!r} not in {sorted(map(str, allowed))}")
    lo, hi = integ["seed_range_inclusive"]["value"]
    if not (isinstance(lo, int) and isinstance(hi, int) and lo <= hi):
        raise ConfigError("integration.seed_range_inclusive: need [low, high] integers")
    if integ["seed_status"]["value"] == "new_frozen_plan" and any(lo <= b and a <= hi for a, b in USED_RANGES):
        raise ConfigError("seed_range overlaps an already used range; it cannot be a new frozen plan")

    for name, item in cfg["proposed_pending"].items():
        if name == "_note":
            continue
        if item.get("status") not in STATUSES or item.get("contract_id") not in CONTRACT_IDS:
            raise ConfigError(f"proposed_pending.{name}: invalid status or contract_id")
    return cfg


def load(path):
    path = Path(path)
    raw = path.read_bytes()
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON ({exc})") from exc
    validate(cfg)
    return cfg, hashlib.sha256(raw).hexdigest()


def native(cfg, key):
    return cfg["native_fixed"][key]["value"]


def setting(cfg, key):
    return cfg["integration"][key]["value"]
