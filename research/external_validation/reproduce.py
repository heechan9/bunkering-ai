"""Stage historical research scripts in an explicit, private workspace."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def stage(workspace: Path) -> dict[str, str]:
    hashes = json.loads((ROOT / 'archive_sha256.json').read_text())
    workspace.mkdir(parents=True, exist_ok=True)
    link = workspace / 'bunkering-restore'
    if link.exists() and link.resolve() != REPO.resolve():
        raise ValueError('workspace/bunkering-restore already points to another repository')
    if not link.exists():
        link.symlink_to(REPO, target_is_directory=True)
    # Preflight all collisions before copying; never replace user research code.
    for name, expected in hashes.items():
        source = ROOT / 'archive' / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f'archive hash mismatch: {name}')
        dest = workspace / name
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            raise ValueError(f'existing script differs: {dest}; use a fresh workspace')
    for name in hashes:
        dest = workspace / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'archive' / name, dest)
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--experiment', help='archived relative path, e.g. reserve-floor-review/run.py')
    parser.add_argument('--allow-output-replace', action='store_true',
                        help='allow the chosen script to replace its prior generated outputs')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace == REPO or REPO in workspace.parents:
        parser.error('use a workspace outside the git checkout for private inputs and outputs')
    hashes = stage(workspace)
    if not args.experiment:
        print('Staged scripts. Supply inputs described in README.md, then select --experiment.')
        return
    if args.experiment not in hashes:
        parser.error('unknown archived experiment')
    output = workspace / args.experiment.split('/')[0]
    markers = {
        'fuelcast-pilot/run.py': ['metrics.csv'],
        'fuelcast-pilot/policy_pilot.py': ['policy_episodes.csv'],
        'country-pilot/run_experiments.py': ['results.json'],
        'fuelcast-retrain/run.py': ['test_episodes.csv', 'training_log.csv'],
        'eia-hanbada-review/run.py': ['eia_episodes.csv'],
        'strathclyde-appendix/uncertainty.py': ['local_uncertainty.csv'],
    }.get(args.experiment, ['episodes.csv'])
    if not args.allow_output_replace and any((output / name).exists() for name in markers):
        parser.error('generated outputs already exist; choose another workspace or --allow-output-replace')
    subprocess.run([sys.executable, str(workspace / args.experiment)], cwd=workspace, check=True)


if __name__ == '__main__':
    main()
