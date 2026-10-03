"""Search allowlisted public evidence; return excerpts, never generated answers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'research/external_validation/DECISIONS.md',
    'docs/technical/safety_accounting.md',
    'docs/technical/reward_diagnostics_results_4seed.md',
    'docs/technical/multiseed_results_4seed.md',
    'docs/technical/web_evidence_guard.md',
    'docs/submission/submission_status.md',
)
# Expand query vocabulary only; every returned excerpt remains literal source text.
ALIASES = {
    '구매비용': ('구매', '비용', 'sci'),
    '재학습': ('학습',),
    '교체': ('교체',),
    '온스': ('ons',),
    '퓨얼캐스트': ('fuelcast',),
    '안전': ('안전', '예비'),
}
STOP = {'왜', '어디', '어떻게', '사용', '사용됐어', '했어', '있어', '알려줘', '더', '높아', '우리', '프로젝트', '모델'}


def terms(query: str) -> set[str]:
    words = re.findall(r'[a-z0-9]+|[가-힣]+', query.lower())
    normalized = set()
    for word in words:
        word = re.sub(r'(은|는|을|를|이|가|에|도|랑)$', '', word) if len(word) > 2 else word
        if len(word) >= 2 and word not in STOP:
            alias = next((key for key in ALIASES if word.startswith(key)), None)
            normalized.update(ALIASES[alias] if alias else (word,))
    return normalized


def search(query: str, root: Path = ROOT, limit: int = 3) -> dict:
    keywords = terms(query)
    if not keywords:
        return {'status': 'no_match', 'query': query, 'results': []}
    matches = []
    root = root.resolve()
    for relative in SOURCES:
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f'Source escapes repository: {relative}')
        if not path.is_file():
            raise FileNotFoundError(f'Missing evidence source: {relative}')
        raw = path.read_bytes()
        lines = raw.decode('utf-8').splitlines()
        digest = hashlib.sha256(raw).hexdigest()
        # Line windows preserve table rows and prevent long paragraphs being discarded.
        for index, line in enumerate(lines):
            if not line.strip() or line.startswith('#'):
                continue
            lowered = line.lower()
            found = {word for word in keywords if (
                re.search(r'(?<![a-z0-9])' + re.escape(word) + r'(?![a-z0-9])', lowered)
                if word.isascii() else word in lowered
            )}
            if len(found) < min(2, len(keywords)):
                continue
            excerpt = line[:900]
            matches.append((len(found) / len(keywords), {
                'path': relative, 'line_start': index + 1, 'line_end': index + 1,
                'sha256': digest, 'excerpt': excerpt,
                'truncated': len(line) > len(excerpt), 'matched_terms': sorted(found),
            }))
    matches.sort(key=lambda item: (-item[0], item[1]['path'], item[1]['line_start']))
    results = [item[1] for item in matches[:limit]]
    return {'status': 'matches' if results else 'no_match', 'query': query,
            'notice': '원문 검색 결과이며 질문에 대한 검증된 답변이나 성능 개선을 뜻하지 않습니다.',
            'results': results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query')
    parser.add_argument('--limit', type=int, default=3, choices=range(1, 11))
    args = parser.parse_args()
    print(json.dumps(search(args.query, limit=args.limit), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
