"""Build bounded display DEMs; no experiment inputs are modified.

Terrarium RGB decoded to metres, bilinearly sampled onto a north-to-south
WGS84 grid. Natural Earth supplies a separate land mask. Sea/below-zero
render heights are clamped to zero; original sampled elevations are retained.
"""
import concurrent.futures
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import urllib.request
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public/data/terrain'
CACHE = Path(tempfile.gettempdir()) / 'ocean-terrain-tiles'
OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(exist_ok=True)
COAST = json.loads((ROOT / 'public/data/coastlines.json').read_text())
N = 257

def pixels(lon, lat, z):
    return ((lon + 180) / 360 * 256 * 2**z,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 256 * 2**z)

def tile(item):
    z, x, y = item
    url = f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
    p = CACHE / f'{z}-{x}-{y}.png'
    if not p.exists():
        with urllib.request.urlopen(url, timeout=45) as response:
            raw = response.read()
        image = Image.open(io.BytesIO(raw))
        assert image.size == (256, 256)
        p.write_bytes(raw)
    raw = p.read_bytes()
    rgb = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'), dtype=float)
    elevation = rgb[:,:,0] * 256 + rgb[:,:,1] + rgb[:,:,2] / 256 - 32768
    return item, elevation, {'url': url, 'sha256': hashlib.sha256(raw).hexdigest()}

for key, region in COAST['regions'].items():
    west, south, east, north = region['bounds']
    z = 10 if key == 'ulsan' else 8
    px0, py0 = pixels(west, north, z)
    px1, py1 = pixels(east, south, z)
    x0, y0 = int(px0)//256, int(py0)//256
    x1, y1 = int(px1)//256, int(py1)//256
    items = [(z,x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]
    mosaic = np.empty(((y1-y0+1)*256,(x1-x0+1)*256))
    provenance = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for (_,x,y), values, proof in pool.map(tile, items):
            mosaic[(y-y0)*256:(y-y0+1)*256,(x-x0)*256:(x-x0+1)*256] = values
            provenance.append(proof)
    xx = np.linspace(px0, px1, N) - x0*256 - .5
    yy = np.array([pixels(west,lat,z)[1] for lat in np.linspace(north,south,N)]) - y0*256 - .5
    xx = np.clip(xx,0,mosaic.shape[1]-1.001)
    yy = np.clip(yy,0,mosaic.shape[0]-1.001)
    xi, yi = np.floor(xx).astype(int), np.floor(yy).astype(int)
    dx, dy = xx-xi, yy-yi
    a = mosaic[yi[:,None],xi[None,:]]*(1-dx)+mosaic[yi[:,None],xi[None,:]+1]*dx
    b = mosaic[yi[:,None]+1,xi[None,:]]*(1-dx)+mosaic[yi[:,None]+1,xi[None,:]+1]*dx
    heights = np.round(a*(1-dy[:,None])+b*dy[:,None]).astype(int)
    assert np.isfinite(heights).all() and heights.min()>-12000 and heights.max()<9000
    mask = Image.new('L',(N,N),0)
    draw = ImageDraw.Draw(mask)
    for polygon in region['polygons']:
        for i, ring in enumerate(polygon):
            draw.polygon([((lon-west)/(east-west)*(N-1),(north-lat)/(north-south)*(N-1)) for lon,lat in ring], fill=255 if i==0 else 0)
    land = np.asarray(mask)>0
    result = {'schema':'ocean-display-dem/v1','region':key,'bounds':region['bounds'],
              'width':N,'height':N,'row_order':'north_to_south','elevation_unit':'metre',
              'elevations':heights.flatten().tolist(),'land':land.astype(int).flatten().tolist(),
              'land_elevation_range_m':[int(heights[land].min()),int(heights[land].max())],
              'source':'Mapzen / AWS Terrain Tiles','zoom':z,'sampling':'bilinear, rounded to 1 metre; display grid, not native DEM resolution',
              'attribution_url':'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
              'coastline':'Natural Earth 1:10m, simplified','tiles':provenance,
              'usage':'Display only. No bathymetry or navigation. No experiment coupling.'}
    (OUT/f'{key}.json').write_text(json.dumps(result,separators=(',',':')))
    print(key,len(items),'tiles',result['land_elevation_range_m'],flush=True)
