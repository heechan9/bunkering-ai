"""Download publicly available inputs; experiment verifies frozen hashes."""
from pathlib import Path
import requests
p=Path(__file__).resolve().parent/'inputs';p.mkdir(exist_ok=True)
urls={'supplementary_materials.zip':'https://data.mendeley.com/public-files/datasets/c95ph5mfjb/files/9512b905-acd4-4f07-89c5-82bc441deeb1/file_downloaded','dqn_final.pt':'https://github.com/heechan9/bunkering-ai/releases/download/official-eval-2026-09-01/dqn_final.pt'}
if __name__=='__main__':
 for name,url in urls.items():
  r=requests.get(url,timeout=60);r.raise_for_status();(p/name).write_bytes(r.content)
