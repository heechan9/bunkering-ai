"""Crop Natural Earth GeoJSON for an explanatory map; stdlib only.

Usage: python scripts/prepare-coastlines.py /path/to/ne_10m_land.geojson
Input source: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson
Natural Earth: public domain. No DEM, bathymetry, navigation or experiment inputs.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

BOUNDS = {'suez': [29, 27, 35.5, 33.5], 'hormuz': [52.5, 22.5, 60.5, 29.5], 'taiwan': [116, 20.5, 124, 27.5], 'bab': [40.5, 10, 46.5, 16], 'cape': [14, -38, 24, -30], 'dover': [-1, 49, 4, 53], 'ulsan': [128.7, 34.8, 130.1, 36.1]}

def clip_ring(ring, bounds):
    points = ring[:-1] if ring[0] == ring[-1] else ring
    for axis, edge, lower in [(0, bounds[0], True), (0, bounds[2], False), (1, bounds[1], True), (1, bounds[3], False)]:
        result = []
        if not points:
            return []
        prev = points[-1]
        inside = lambda p: p[axis] >= edge if lower else p[axis] <= edge
        for curr in points:
            a, b = inside(prev), inside(curr)
            if a != b:
                t = (edge - prev[axis]) / (curr[axis] - prev[axis])
                result.append([prev[0] + t * (curr[0] - prev[0]), prev[1] + t * (curr[1] - prev[1])])
            if b:
                result.append(curr[:2])
            prev = curr
        points = result
    if len(points) < 3:
        return []
    return points + [points[0]]

def area(ring):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:])))/2

def simplify(points, epsilon=.003):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0]-a[0], b[1]-a[1]
    norm = math.hypot(dx,dy)
    dist = [abs(dx*(p[1]-a[1])-dy*(p[0]-a[0]))/norm if norm else math.dist(a,p) for p in points[1:-1]]
    maximum = max(dist,default=0)
    if maximum <= epsilon:
        return [a,b]
    at = dist.index(maximum)+1
    return simplify(points[:at+1],epsilon)[:-1]+simplify(points[at:],epsilon)

def prepare(source):
    raw = Path(source).read_bytes()
    data = json.loads(raw)
    polygons = []
    for feature in data['features']:
        g = feature['geometry']
        polygons.extend(g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']])
    result = {'source': {
        'name':'Natural Earth 1:10m land polygons',
        'url':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson',
        'documentation':'https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/',
        'license':'Public domain', 'sha256':hashlib.sha256(raw).hexdigest(),
        'processing':'Rectangular Sutherland–Hodgman clipping; Douglas–Peucker 0.003 degree simplification; 5 decimal places. Visual map, not a navigation chart.',
        'elevation':'Uniform illustrative extrusion; no elevation data.'}, 'regions':{}}
    for name,bounds in BOUNDS.items():
        output=[]
        for poly in polygons:
            outer=clip_ring(poly[0],bounds)
            if not outer or area(outer)<.00008:
                continue
            rings=[outer]+[c for r in poly[1:] if (c:=clip_ring(r,bounds)) and area(c)>.00008]
            rings=[[[round(x,5),round(y,5)] for x,y in simplify(r)] for r in rings]
            if any(len(r)<4 for r in rings):
                continue
            output.append(rings)
        assert output
        for poly in output:
            for ring in poly:
                assert ring[0]==ring[-1]
                assert all(bounds[0]-1e-5<=x<=bounds[2]+1e-5 and bounds[1]-1e-5<=y<=bounds[3]+1e-5 for x,y in ring)
        result['regions'][name]={'bounds':bounds,'polygons':output}
    target=Path(__file__).resolve().parents[1]/'public/data/coastlines.json'
    target.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({k:{'polygons':len(v['polygons']),'vertices':sum(len(r) for p in v['polygons'] for r in p)} for k,v in result['regions'].items()}))
    print('wrote',target.stat().st_size,'bytes')

if __name__=='__main__':
    prepare(sys.argv[1])
