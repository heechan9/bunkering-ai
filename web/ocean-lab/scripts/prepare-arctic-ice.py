"""Rebuild Jan15 historical ice JSON from preserved CSV/provenance, without network."""
import csv,json,math,pathlib
p=pathlib.Path(__file__).resolve().parents[1]/'public/data/arctic-observations'
meta=json.loads((p/'provenance.json').read_text())
rows=list(csv.DictReader((p/'raw-2026-01-15.csv').open()))[1:]
cells=[]; missing=0; invalid=0
for r in rows:
    v=float(r['cdr_seaice_conc'])
    if not math.isfinite(v):missing+=1;continue
    if not 0<=v<=1:invalid+=1;continue
    assert r['time']=='2026-01-15T00:00:00Z'
    cells.append([float(r['x']),float(r['y']),v])
assert len(cells)==meta['counts']['validCells']==856
assert missing==1272 and invalid==0
meta.update(status='available',url=meta['productUrl'],sampleSpacingKm=200,nativeResolutionKm=25,cells=cells)
(p/'ice.json').write_text(json.dumps(meta,separators=(',',':')))
print('PASS: reproduced',len(cells),'valid cells; preserved metadata and exact date')
