"""Integrity-checked access to the pinned ONS route-stress release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_METADATA = Path(__file__).parents[1] / "data/route_stress/ons_source.json"


def _metadata(path: str | Path = DEFAULT_METADATA) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def verify_sha256(content: bytes, expected_sha256: str) -> None:
    observed = hashlib.sha256(content).hexdigest()
    if observed != expected_sha256:
        raise ValueError(
            "ONS SHA-256 mismatch; the upstream current release may have changed "
            f"(expected {expected_sha256}, observed {observed})"
        )


def download_verified_ons(
    destination: str | Path,
    *,
    metadata_path: str | Path = DEFAULT_METADATA,
    timeout: int = 30,
) -> Path:
    """Download the ONS CSV and write it only after hash verification."""
    metadata = _metadata(metadata_path)
    request = Request(
        metadata["source_url"],
        headers={"User-Agent": "bunkering-ai-route-stress/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        content = response.read()
    verify_sha256(content, metadata["sha256"])

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination
