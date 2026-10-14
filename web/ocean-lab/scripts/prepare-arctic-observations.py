"""Rebuild public observations from the preserved licensed source; never infer fuel."""
import csv,hashlib,io,json,math,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
out=root/'public/data/arctic-observations'
raw=(out/'PS155_10min.tsv').read_bytes()
text=raw.decode('utf-8'); header,body=text.split('*/\n',1)
assert 'CC-BY-4.0' in header
rows=list(csv.DictReader(io.StringIO(body),delimiter='\t'))
points=[]
for r in rows:
    lat,lon=float(r['Latitude']),float(r['Longitude'])
    assert -90<=lat<=90 and -180<=lon<=180
    points.append([r['Date/Time'],lat,lon,float(r['Speed [kn]']) if r['Speed [kn]'] else None,float(r['Course [deg]']) if r['Course [deg]'] else None])
assert len(points)>4000 and all(a[0]<b[0] for a,b in zip(points,points[1:]))
a=6378273.; e=math.sqrt(1-(6356889.449/a)**2); rad=math.pi/180
lat_ts=70*rad
m=math.cos(lat_ts)/math.sqrt(1-e*e*math.sin(lat_ts)**2)
def t(phi):
    return math.tan(math.pi/4-phi/2)/((1-e*math.sin(phi))/(1+e*math.sin(phi)))**(e/2)
def project(lat,lon):
    rho=a*m*t(lat*rad)/t(lat_ts)
    return [round(320+rho*math.sin((lon+45)*rad)*.00007,2),round(320+rho*math.cos((lon+45)*rad)*.00007,2)]
# Coastline outlines only. Discontinuous southern segments are not joined.
land=json.loads((root/'public/data/world-land.json').read_text())
paths=[]
for poly in land['geometry']['coordinates']:
 for ring in poly:
    seg=[]
    for lon,lat in ring:
      if lat>=48:seg.append(project(lat,lon))
      else:
        if len(seg)>1:paths.append(seg)
        seg=[]
    if len(seg)>1:paths.append(seg)
metadata=dict(status='available',id='PS155',citation='Purser, Autun (2026): Master tracks in different resolutions of POLARSTERN cruise PS155, Bremerhaven - Tromsø, 2026-07-04 - 2026-08-03. Alfred Wegener Institute, PANGAEA.',url='https://doi.org/10.1594/PANGAEA.996842',download='https://doi.pangaea.de/10.1594/PANGAEA.996842?format=textfile',license='CC-BY-4.0',licenseUrl='https://creativecommons.org/licenses/by/4.0/',sourceSha256=hashlib.sha256(raw).hexdigest(),rowCount=len(points),start=points[0][0],end=points[-1][0],sourceResolution='10 min; final endpoint may be shorter',timestampNote='Source timestamps preserved without adding an unverified time zone.',columns=['sourceTime','latitude_deg','longitude_deg','calculated10minSpeed_kn','calculated10minCourse_deg'],fuelData=False,commercialNsrTransit=False,points=points)
(out/'track.json').write_text(json.dumps(metadata,ensure_ascii=False,separators=(',',':')))
(out/'coastline.json').write_text(json.dumps(dict(source=land['properties'],projection='EPSG:3411',paths=paths),separators=(',',':')))
print(len(points), points[0], points[-1], 'coastlines',len(paths))
