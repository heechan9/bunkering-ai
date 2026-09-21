"""Explicit file baseline and read-only change detection. Never auto-accept changes."""
import argparse
import hashlib
import json
from pathlib import Path


def snapshot(directory):
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError("Source directory does not exist")
    files = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symbolic links are not accepted')
        if path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            files[path.relative_to(directory).as_posix()] = {'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}
    return {'schema': 'source-baseline/v1', 'files': files}


def compare(before, after):
    a, b = before['files'], after['files']
    return {key: sorted(values) for key, values in {
        'added': b.keys() - a.keys(), 'removed': a.keys() - b.keys(),
        'changed': {p for p in a.keys() & b.keys() if a[p] != b[p]},
        'unchanged': {p for p in a.keys() & b.keys() if a[p] == b[p]}}.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('baseline', type=Path)
    p.add_argument('--create', action='store_true')
    args = p.parse_args()
    if args.baseline.resolve().is_relative_to(args.directory.resolve()):
        p.error('Store baseline outside the source directory')
    current = snapshot(args.directory)
    if args.create:
        with args.baseline.open('x', encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        return
    result = compare(json.loads(args.baseline.read_text()), current)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1 if any(result[k] for k in ('added', 'removed', 'changed')) else 0)


if __name__ == '__main__':
    main()
