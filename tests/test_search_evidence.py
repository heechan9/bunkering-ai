import hashlib
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('search_evidence', Path(__file__).parents[1] / 'scripts/search_evidence.py')
search_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(search_module)


@pytest.mark.parametrize('query,expected', [
    ('ONS는 어디에 사용됐어?', 'ONS'),
    ('FuelCast 모델 교체했어?', 'FuelCast'),
    ('왜 DQN 구매비용이 더 높아?', 'DQN'),
])
def test_real_questions_return_literal_sources(query, expected):
    result = search_module.search(query)
    assert result['status'] == 'matches'
    assert any(expected in row['excerpt'] for row in result['results'])
    for row in result['results']:
        raw = (search_module.ROOT / row['path']).read_bytes()
        line = raw.decode().splitlines()[row['line_start'] - 1]
        assert line.startswith(row['excerpt'])
        assert hashlib.sha256(raw).hexdigest() == row['sha256']


@pytest.mark.parametrize('query', ['', '알려줘', '양자컴퓨터 큐비트 오류정정'])
def test_abstains(query):
    assert search_module.search(query)['status'] == 'no_match'


def test_long_evidence_and_changed_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(search_module, 'SOURCES', ('evidence.md',))
    path = tmp_path / 'evidence.md'
    path.write_text('FuelCast ' + '가' * 1200, encoding='utf-8')
    first = search_module.search('FuelCast', tmp_path)['results'][0]
    assert first['truncated'] and len(first['excerpt']) == 900
    path.write_text(path.read_text(encoding='utf-8') + ' 변경', encoding='utf-8')
    second = search_module.search('FuelCast', tmp_path)['results'][0]
    assert first['sha256'] != second['sha256']


def test_outside_source_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(search_module, 'SOURCES', ('../private.md',))
    with pytest.raises(ValueError, match='escapes'):
        search_module.search('FuelCast', tmp_path)


def test_missing_source_fails_explicitly(tmp_path):
    with pytest.raises(FileNotFoundError, match='Missing evidence'):
        search_module.search('FuelCast', tmp_path)


def test_latin_terms_do_not_match_inside_other_words(tmp_path, monkeypatch):
    monkeypatch.setattr(search_module, 'SOURCES', ('evidence.md',))
    (tmp_path / 'evidence.md').write_text('transitions conditions')
    assert search_module.search('ONS', tmp_path)['status'] == 'no_match'
