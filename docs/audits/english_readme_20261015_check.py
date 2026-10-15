"""Check this English README update against its fixed Korean source revision.

Run from any directory with Python and Pillow installed. No model dependencies.
"""
from pathlib import Path
import re
import subprocess
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = '8ea74a952c9d0fd60875bde152c5196e81d3b8da'

def original(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)

ko = original('README.md').decode('utf-8')
en = (ROOT / 'README.en.md').read_text(encoding='utf-8')
tables = lambda s: re.findall(r'(?:^\|.*\n)+', s, re.M)
links = lambda s: re.findall(r'\]\(([^)]+)\)', s)
kt, et = tables(ko), tables(en)
assert len(kt) == len(et) == 13
rows = [len(t.splitlines()) - 2 for t in kt]
assert rows == [len(t.splitlines()) - 2 for t in et]
assert sum(rows) == 105
assert [links(t) for t in kt] == [links(t) for t in et]
for i in [2, 3, 4, 5, 6]:
    cells = lambda t: [r.split('|')[2:-1] for r in t.splitlines()[2:]]
    numbers = lambda s: re.findall(r'(?<![A-Za-z])[-+]?\d[\d,.]*(?:/\d[\d,.]*)*', s.replace('−', '-'))
    assert [[numbers(c) for c in row] for row in cells(kt[i])] == [[numbers(c) for c in row] for row in cells(et[i])], f'table {i + 1} numbers differ'
refs = links(en) + re.findall(r'<img[^>]*src="([^"]+)"', en)
local_refs = [r for r in refs if not r.startswith(('https://', 'http://', '#'))]
assert all((ROOT / r.split('#')[0]).exists() for r in local_refs)
assert not re.search(r'PENDING|WORKING DRAFT|<!-- (?:QUICK_START|RESEARCH_BOUNDARIES|CONTRIBUTING)', en)
old = original('README.en.md').decode('utf-8')
for title, end in [('Quick start', 'Evidence and results'), ('Research boundaries', 'Repository map')]:
    assert old.split('## ' + title)[1].split('## ' + end)[0].strip() in en
assert old.split('## Contributing and reuse')[1].strip() in en
originals = ['README.md', 'docs/assets/bunkering-project-hero.png', 'docs/assets/bunkering-ai-decision-system-hero-v2.jpg', 'docs/assets/international-evidence-pipeline.jpg', 'docs/assets/international-evidence-flow-ko.png', 'results/evaluation/comparison.png']
for path in originals:
    committed, working = original(path), (ROOT / path).read_bytes()
    if path.endswith('.md'):
        committed, working = committed.replace(b'\r\n', b'\n'), working.replace(b'\r\n', b'\n')
    assert committed == working, path + ' changed'
images = []
for p in sorted((ROOT / 'docs/assets').glob('*en*.png')):
    with Image.open(p) as im:
        im.verify()
    with Image.open(p) as im:
        images.append({'path': p.relative_to(ROOT).as_posix(), 'size': list(im.size), 'mode': im.mode, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'source_revision': BASE, 'tables': len(et), 'data_rows': sum(rows), 'rows_per_table': rows, 'table_source_links': sum(len(links(t)) for t in et), 'local_references': len(local_refs), 'originals_preserved': len(originals), 'quick_start_boundaries_reuse_preserved': True, 'images': images}, indent=2))
