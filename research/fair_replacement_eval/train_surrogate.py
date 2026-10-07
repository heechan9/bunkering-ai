"""Train a SURROGATE Double DQN for harness validation only.

Uses the repository's own ``scripts.train.train`` and ``configs/dqn.yaml``
unchanged except the episode count and seed (criteria.json: seed 5000000,
3000 episodes; seeds 5000000..5002999 are disjoint from reuse/holdout seeds).
The result is NOT the official model and can never support a replacement
verdict. Checkpoints (*.pt) are gitignored.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research.fair_replacement_eval.common import PROJECT_ROOT, load_criteria


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    crit = load_criteria()
    spec = crit["surrogate_for_synthetic_validation"]

    import yaml

    from scripts.train import train

    config = yaml.safe_load((PROJECT_ROOT / "configs" / "dqn.yaml").read_text(encoding="utf-8"))
    train(config, int(spec["episodes"]), int(spec["train_seed"]), checkpoint_path=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
