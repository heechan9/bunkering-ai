"""Generate the public source catalog from reviewed, revision-pinned evidence.

Adapted from FabGuard's reviewed snapshot build pattern. No network or inference.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path('scripts/web_source_catalog.json')
OUTPUT = Path('web/ocean-lab/public/data/source-catalog.json')


def build(root=ROOT):
    root = Path(root).resolve()
    config = json.loads((root / CONFIG).read_text(encoding='utf-8'))
    if config['schema'] != 'bunkering-source-catalog/v1' or config['repository'] != 'heechan9/bunkering-ai':
        raise ValueError('Unexpected source catalog contract')
    if not re.fullmatch('[0-9a-f]{40}', config['revision']):
        raise ValueError('Evidence revision must be an immutable commit')
    seen = set()
    for source in config['sources']:
        if source['id'] in seen:
            raise ValueError('Duplicate source ID')
        seen.add(source['id'])
        path = Path(source['path'])
        if path.is_absolute() or '..' in path.parts or not path.as_posix().startswith('docs/'):
            raise ValueError('Evidence must be a repository documentation path')
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError('Evidence path escapes repository')
        raw = resolved.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError(f'{path}: evidence changed; review metadata and revision together')
        for field in ('title', 'status', 'limits', 'kind', 'unit', 'period', 'scope'):
            if any(not isinstance(source[field].get(lang), str) or not source[field][lang].strip() for lang in ('ko', 'en')):
                raise ValueError(f'Missing localized source metadata: {field}')
        source['bytes'] = len(raw)
        source['url'] = f"https://github.com/{config['repository']}/blob/{config['revision']}/{path.as_posix()}"
    if seen != {'simulation', 'upa', 'maritime_review', 'kmou'}:
        raise ValueError('Source coverage differs')
    return config


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    expected = build()
    if args.check:
        if json.loads((ROOT / OUTPUT).read_text(encoding='utf-8')) != expected:
            raise SystemExit('Source catalog is stale; regenerate after review')
        print('PASS: 4 source records match reviewed evidence')
    else:
        (ROOT / OUTPUT).write_text(json.dumps(expected, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
