"""Acquire documented GFW v3 public data and verify publisher MD5."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests,hashlib,json
HERE=Path(__file__).resolve().parent

def acquire():
 meta=requests.get('https://zenodo.org/api/records/14982712',timeout=45);meta.raise_for_status();j=meta.json()
 names={'mmsi-daily-csvs-10-v3-2017.zip','fishing-vessels-v3.csv','README-mmsi-v3.txt','README-known-issues-v3.txt','README-fishing-vessels-v3.txt'}
 def download(f):
  p=HERE/'inputs'/f['key'];h=hashlib.md5();sha=hashlib.sha256()
  with requests.get(f['links']['self'],stream=True,timeout=(30,90)) as r:
   r.raise_for_status()
   with p.open('wb') as out:
    for b in r.iter_content(1024*1024):out.write(b);h.update(b);sha.update(b)
  assert p.stat().st_size==f['size'] and 'md5:'+h.hexdigest()==f['checksum'],f['key']
  print('verified',f['key'],p.stat().st_size,flush=True)
  return {'file':f['key'],'bytes':p.stat().st_size,'md5':h.hexdigest(),'sha256':sha.hexdigest(),'url':f['links']['self']}
 (HERE/'inputs').mkdir(exist_ok=True);(HERE/'results').mkdir(exist_ok=True)
 with ThreadPoolExecutor(max_workers=3) as pool:manifest=list(pool.map(download,[f for f in j['files'] if f['key'] in names]))
 (HERE/'results/source_manifest.json').write_text(json.dumps({'record':'14982712','license':j['metadata'].get('license'),'files':manifest},indent=2),encoding='utf-8')
if __name__=='__main__':acquire()
