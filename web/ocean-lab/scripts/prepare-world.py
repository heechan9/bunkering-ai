"""Prepare simplified Natural Earth land for the interactive globe (no elevation)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('coasts',root/'scripts/prepare-coastlines.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=Path(sys.argv[1]).read_bytes();raw=json.loads(b);polys=[]
for f in raw['features']:
    g=f['geometry']
    source=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    for poly in source:
        if m.area(poly[0])<.025:continue
        rings=[]
        for ring in poly:
            r=[[round(x,3),round(y,3)] for x,y in m.simplify(ring,.12)]
            if len(r)>=4:rings.append(r)
        if rings:polys.append(rings)
out={'type':'Feature','properties':{'source':'Natural Earth 1:10m land','source_url':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson','license':'Public domain','source_sha256':hashlib.sha256(b).hexdigest(),'simplification_degrees':.12,'elevation':'none'},'geometry':{'type':'MultiPolygon','coordinates':polys}}
target=root/'public/data/world-land.json';target.write_text(json.dumps(out,separators=(',',':'))+'\n')
print('world polygons',len(polys),'bytes',target.stat().st_size)
