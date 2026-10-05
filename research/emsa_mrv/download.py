"""Download pinned public EMSA workbooks and verify the audited originals."""
from pathlib import Path
import hashlib,json
import requests
root=Path(__file__).resolve().parent
for item in json.loads((root/'audit.json').read_text(encoding='utf-8'))['files']:
    p=root/f"{item['year']}-v{item['version']}.xlsx"
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']:
        continue
    r=requests.get(item['download_url'],timeout=120)
    r.raise_for_status()
    if hashlib.sha256(r.content).hexdigest()!=item['sha256']:
        raise ValueError('Source bytes changed; re-audit explicitly instead of overwriting')
    p.write_bytes(r.content)
