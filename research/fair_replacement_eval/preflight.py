"""Pre-evaluation validation, run once before any episode.

Checks, without running an episode:

* checkpoint file, sha256, format version, tensor dimensions;
* ``metadata.env_config`` against the evaluation environment configuration;
* ``metadata.train_seed`` / ``metadata.n_episodes`` presence and validity;
* criteria hash;
* seed ranges (confirmation vs training range, reuse, already-used ranges).

Every check returns ``status`` in {``pass``, ``fail``, ``undecidable``, ``info``} plus
human-readable ``reasons``. A missing or invalid training-seed field is
``undecidable`` (never treated as 0), and the training-seed overlap check then
does not pass. ``info`` entries never affect ``overall``.

Nothing here reads or changes criteria, planner, seeds or results.
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

PASS, FAIL, UNDECIDABLE, INFO = "pass", "fail", "undecidable", "info"
CHECKPOINT_FORMAT_VERSION = 1  # mirrors agents.dqn.CHECKPOINT_FORMAT_VERSION; verified by a test


def _check(check_id: str, status: str, reasons: Sequence[str] = (), **detail: Any) -> dict[str, Any]:
    return {"id": check_id, "status": status, "reasons": list(reasons), **detail}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# --------------------------------------------------------------------------- seeds


def used_ranges(crit: Mapping[str, Any]) -> list[tuple[int, int]]:
    """Inclusive seed ranges that earlier work already used (reuse, development, diagnostics, surrogate)."""
    sets = crit["evaluation_sets"]
    ranges = [(int(r["range"][0]), int(r["range"][1])) for r in sets["seed_ranges_already_used"]]
    for key in ("reuse", "development_holdout"):
        cfg = sets[key]
        ranges.append((int(cfg["base_seed"]), int(cfg["base_seed"]) + int(cfg["episodes"]) - 1))
    return ranges


def hits_used_ranges(seeds: Sequence[int], crit: Mapping[str, Any]) -> bool:
    lo, hi = min(seeds), max(seeds)
    return any(not (hi < a or lo > b) for a, b in used_ranges(crit))


def training_seed_range(metadata: Mapping[str, Any] | None) -> tuple[tuple[int, int] | None, list[str]]:
    """Return ``((first, last_inclusive), [])`` or ``(None, reasons)``.

    Training episode ``e`` uses seed ``train_seed + e`` (scripts/train.py), so the range is
    ``[train_seed, train_seed + n_episodes)``. Missing or invalid fields yield reasons instead
    of a default: ``n_episodes`` is never assumed to be 0.
    """
    reasons: list[str] = []
    if not isinstance(metadata, Mapping):
        return None, ["metadata missing: training seed range cannot be determined"]
    for key, minimum in (("train_seed", 0), ("n_episodes", 1)):
        if key not in metadata or metadata[key] is None:
            reasons.append(f"metadata.{key} missing: training seed range cannot be determined")
        elif not _is_int(metadata[key]):
            reasons.append(f"metadata.{key}={metadata[key]!r} is not an integer")
        elif metadata[key] < minimum:
            reasons.append(f"metadata.{key}={metadata[key]!r} is below the minimum {minimum}")
    if reasons:
        return None, reasons
    start = int(metadata["train_seed"])
    return (start, start + int(metadata["n_episodes"]) - 1), []


def check_training_seed_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    rng, reasons = training_seed_range(metadata)
    if rng is None:
        return _check("training_seed_metadata", UNDECIDABLE, reasons, training_range=None)
    return _check("training_seed_metadata", PASS, training_range=list(rng))


def _overlap(seeds: Sequence[int], rng: tuple[int, int] | None) -> bool | None:
    if rng is None:
        return None
    return any(rng[0] <= s <= rng[1] for s in seeds)


def check_seed_ranges(
    crit: Mapping[str, Any],
    metadata: Mapping[str, Any] | None,
    confirmation_seeds: Sequence[int],
    reuse_seeds: Sequence[int],
) -> dict[str, Any]:
    """Confirmation seeds must be disjoint from the training range and from every used range.

    Reuse seeds may overlap the training range (they only test consistency); that is recorded.
    """
    reasons: list[str] = []
    for name, seeds in (("confirmation", confirmation_seeds), ("reuse", reuse_seeds)):
        if len(seeds) == 0:
            return _check("seed_ranges", FAIL, [f"{name} seed list is empty"])
        if not all(_is_int(s) and s >= 0 for s in seeds):
            return _check("seed_ranges", FAIL, [f"{name} seeds must be non-negative integers"])
    if set(confirmation_seeds) & set(reuse_seeds):
        reasons.append("confirmation seeds intersect reuse seeds")
    if hits_used_ranges(confirmation_seeds, crit):
        reasons.append("confirmation seeds intersect a range already used (reuse, development, diagnostic or surrogate)")

    rng, meta_reasons = training_seed_range(metadata)
    conf_overlap, reuse_overlap = _overlap(confirmation_seeds, rng), _overlap(reuse_seeds, rng)
    detail = {
        "confirmation_range": [min(confirmation_seeds), max(confirmation_seeds)],
        "reuse_range": [min(reuse_seeds), max(reuse_seeds)],
        "training_range": None if rng is None else list(rng),
        "confirmation_overlaps_training_seeds": conf_overlap,
        "reuse_overlaps_training_seeds": reuse_overlap,
    }
    if conf_overlap:
        reasons.append(f"confirmation seeds intersect the training seed range {list(rng)}")
    if reasons:
        return _check("seed_ranges", FAIL, reasons, **detail)
    if rng is None:
        return _check("seed_ranges", UNDECIDABLE, meta_reasons + ["training-seed overlap cannot be checked"], **detail)
    return _check("seed_ranges", PASS, **detail)


# --------------------------------------------------------------------- environment


def _env_defaults() -> dict[str, Any]:
    from envs.bunkering_env import BunkeringEnv

    params = inspect.signature(BunkeringEnv.__init__).parameters
    return {k: p.default for k, p in params.items() if k != "self" and p.default is not inspect.Parameter.empty}


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def check_env_config(metadata: Mapping[str, Any] | None, eval_env_config: Mapping[str, Any]) -> dict[str, Any]:
    """Field-by-field comparison; a key absent on one side resolves to the BunkeringEnv default.

    ``eval_env_config`` is the nominal evaluation configuration. Stress scenarios deliberately
    change ``fuel_consumption_per_step`` and are not compared here.
    """
    trained = None if not isinstance(metadata, Mapping) else metadata.get("env_config")
    if not isinstance(trained, Mapping):
        return _check("env_config", UNDECIDABLE, ["metadata.env_config missing: training environment unknown"], mismatches=[])
    defaults = _env_defaults()
    unknown = sorted((set(trained) | set(eval_env_config)) - set(defaults))
    mismatches = []
    for key in sorted(set(defaults) & (set(trained) | set(eval_env_config))):
        t, e = trained.get(key, defaults[key]), eval_env_config.get(key, defaults[key])
        if not _same(t, e):
            mismatches.append({"field": key, "checkpoint": t, "evaluation": e})
    reasons = [f"{m['field']}: checkpoint={m['checkpoint']!r} evaluation={m['evaluation']!r}" for m in mismatches]
    reasons += [f"unknown env field {k!r}" for k in unknown]
    return _check("env_config", FAIL if reasons else PASS, reasons, mismatches=mismatches, unknown_fields=unknown)


# -------------------------------------------------------------------- checkpoint


def load_payload(path: Path) -> dict[str, Any]:
    import torch

    return torch.load(path, map_location="cpu", weights_only=True)


def check_checkpoint(
    payload: Mapping[str, Any] | None,
    sha256: str | None,
    official_sha256: str,
    eval_env_config: Mapping[str, Any],
    load_error: str | None = None,
) -> list[dict[str, Any]]:
    """Hash (informational), format version and dimensions. Does not run any episode."""
    checks = [
        _check(
            "checkpoint_sha256",
            INFO,
            [] if sha256 == official_sha256 else ["not the official checkpoint: verdict can only be SYNTHETIC_VALIDATION_ONLY"],
            sha256=sha256,
            official=bool(sha256 is not None and sha256 == official_sha256),
            expected_official_sha256=official_sha256,
        )
    ]
    if payload is None:
        checks.append(_check("checkpoint_format", FAIL, [load_error or "checkpoint could not be read"]))
        return checks
    version = payload.get("format_version")
    fmt_reasons = []
    if version != CHECKPOINT_FORMAT_VERSION:
        fmt_reasons.append(f"format_version={version!r}, expected {CHECKPOINT_FORMAT_VERSION}")
    fmt_reasons += [f"missing key {k!r}" for k in ("config", "policy_net", "target_net", "state_dim", "action_dim") if k not in payload]
    checks.append(_check("checkpoint_format", FAIL if fmt_reasons else PASS, fmt_reasons, format_version=version))

    from envs.bunkering_env import BunkeringEnv

    env = BunkeringEnv(**dict(eval_env_config))
    want = (int(env.observation_space.shape[0]), int(env.action_space.n))
    got = (payload.get("state_dim"), payload.get("action_dim"))
    dim_reasons = []
    if not (_is_int(got[0]) and _is_int(got[1])):
        dim_reasons.append(f"state_dim/action_dim not integers: {got!r}")
    elif got != want:
        dim_reasons.append(f"checkpoint (state_dim, action_dim)={got}, evaluation environment needs {want}")
    checks.append(_check("checkpoint_dimensions", FAIL if dim_reasons else PASS, dim_reasons, checkpoint=list(got), expected=list(want)))
    return checks


# ------------------------------------------------------------------------ driver


def check_criteria_hash(load_criteria_fn: Any) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    try:
        crit = load_criteria_fn()
    except Exception as exc:  # hash mismatch or unreadable file
        return _check("criteria_hash", FAIL, [f"{type(exc).__name__}: {exc}"]), None
    return _check("criteria_hash", PASS), crit


def overall_status(checks: Sequence[Mapping[str, Any]]) -> str:
    statuses = {c["status"] for c in checks if c["status"] != INFO}
    if FAIL in statuses:
        return FAIL
    if UNDECIDABLE in statuses:
        return UNDECIDABLE
    return PASS


def run_preflight(
    checkpoint_path: Path,
    crit: Mapping[str, Any],
    eval_env_config: Mapping[str, Any],
    confirmation_seeds: Sequence[int],
    reuse_seeds: Sequence[int],
    *,
    sha256: str | None = None,
    payload: Mapping[str, Any] | None = None,
    criteria_check: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run every check once and return the record written to ``preflight.json``.

    ``payload`` may be injected (tests); otherwise the file is read with ``weights_only=True``.
    ``crit`` is expected to come from ``load_criteria()`` (hash already verified); pass
    ``criteria_check`` from :func:`check_criteria_hash` to record that result.
    """
    from research.fair_replacement_eval.common import file_sha256

    load_error = None
    if payload is None:
        try:
            payload = load_payload(Path(checkpoint_path))
        except Exception as exc:
            load_error = f"{type(exc).__name__}: {exc}"
    if sha256 is None and Path(checkpoint_path).is_file():
        sha256 = file_sha256(Path(checkpoint_path))

    metadata = None if payload is None else payload.get("metadata")
    checks: list[dict[str, Any]] = [dict(criteria_check) if criteria_check else _check("criteria_hash", PASS)]
    checks += check_checkpoint(payload, sha256, str(crit["incumbent"]["official_checkpoint_sha256"]), eval_env_config, load_error)
    checks.append(check_env_config(metadata, eval_env_config))
    checks.append(check_training_seed_metadata(metadata))
    checks.append(check_seed_ranges(crit, metadata, confirmation_seeds, reuse_seeds))
    return {
        "overall": overall_status(checks),
        "checks": checks,
        "note": "No episode was run. fail = evaluation must not start; undecidable = decision gates stay closed (verdict NOT_DECIDABLE).",
    }


def gate_values(preflight: Mapping[str, Any]) -> dict[str, bool]:
    """Map pre-flight results onto decision gates. Only an explicit pass opens a gate."""
    by_id = {c["id"]: c["status"] for c in preflight["checks"]}
    return {
        "G2_holdout_disjoint": by_id.get("seed_ranges") == PASS and by_id.get("training_seed_metadata") == PASS,
        "G3_criteria_hash": by_id.get("criteria_hash") == PASS,
        "G0_preflight": preflight["overall"] == PASS,
    }
