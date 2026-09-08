"""Build a leakage-safe ONS route-stress analysis artifact."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from route_stress import (
    add_past_only_baseline,
    download_verified_ons,
    parse_ons_crossings,
)


DEFAULT_OUTPUT = Path("results/route_stress/ons_past_only_baseline.csv")


def build_analysis(input_path: Path | None, output_path: Path) -> Path:
    if input_path is None:
        with tempfile.TemporaryDirectory() as directory:
            downloaded = download_verified_ons(Path(directory) / "ons_crossings.csv")
            frame = parse_ons_crossings(downloaded)
    else:
        frame = parse_ons_crossings(input_path)

    result = add_past_only_baseline(frame)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = build_analysis(args.input, args.output)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
