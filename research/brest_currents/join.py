"""Retrospective nearest-cell AIS/current join; no fuel or policy evaluation."""
from pathlib import Path
import csv, io, json, hashlib, urllib.request, zipfile
import numpy as np
import xarray as xr

OUT = Path(__file__).parent / 'results'
SOURCE = 'https://zenodo.org/records/6402160/files/Maritime%20Routes%20and%20Tracklets.zip?download=1'
EXPECTED = 'c1bf2bfe52777be68864ff0ce771bac34956f96772249abd78fa12b8864d55b0'
CURRENT = 'https://s3.waw3-1.cloudferro.com/mdl-arco-geo-032/arco/IBI_MULTIYEAR_PHY_005_002/cmems_mod_ibi_phy-cur_my_0.027deg_PT1H-m_202511/geoChunked.zarr'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = urllib.request.urlopen(SOURCE, timeout=30).read()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    z = zipfile.ZipFile(io.BytesIO(raw))
    rows = list(csv.DictReader(io.StringIO(z.read('Maritime Routes and Tracklets/tracklets.csv').decode()), delimiter='|'))
    points = []
    for r in rows:
        times = [float(r[f'ts{i}']) for i in range(1, 6)]
        valid = all(a < b for a, b in zip(times, times[1:]))
        valid = valid and len({r[f'mmsi{i}'] for i in range(1, 6)}) == 1
        for i in range(1, 6):
            points.append(dict(tracklet=r['idtracklet'], point=i, lon=float(r[f'lon{i}']), lat=float(r[f'lat{i}']), timestamp=times[i-1], tracklet_time_valid=valid))
    ds = xr.open_zarr(CURRENT, consolidated=True, zarr_format=2, storage_options={'client_kwargs': {'trust_env': True}})
    ids = [i for i, p in enumerate(points) if p['tracklet_time_valid']]
    def arr(key): return xr.DataArray([points[i][key] for i in ids], dims='sample')
    time = xr.DataArray(np.array([points[i]['timestamp'] for i in ids]).astype('datetime64[s]'), dims='sample')
    selected = ds[['uo','vo']].sel(longitude=arr('lon'), latitude=arr('lat'), time=time, method='nearest')
    print('Loading',len(ids),'point matches',flush=True)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    groups = {}
    for j in range(len(ids)):
        lon=float(selected.longitude[j]); lat=float(selected.latitude[j])
        key=(round((lon-float(ds.longitude[0]))/float(ds.longitude[1]-ds.longitude[0]))//4, round((lat-float(ds.latitude[0]))/float(ds.latitude[1]-ds.latitude[0]))//4, int((selected.time[j].values-ds.time[0].values)/np.timedelta64(1,'h'))//38760)
        groups.setdefault(key,[]).append(j)
    values = np.full((len(ids),2),np.nan)
    failures = set()
    def fetch(js):
        try:
            batch=ds[['uo','vo']].sel(longitude=arr('lon').isel(sample=js), latitude=arr('lat').isel(sample=js), time=time.isel(sample=js), method='nearest').compute(scheduler='single-threaded')
            return js,batch,None
        except Exception as e:
            return js,None,str(e)[:400]
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(fetch,js) for js in groups.values()]
        for n,job in enumerate(as_completed(jobs)):
            js,batch,error=job.result()
            if error:
                failures.update(js)
                print('group access failure',n,error,flush=True)
            else:
                values[js,0]=batch.uo.values;values[js,1]=batch.vo.values
            if n%10==0: print('groups',n+1,'/',len(groups),flush=True)
    print('Loaded',flush=True)
    for j, i in enumerate(ids):
        p = points[i]
        p.update(grid_lon=float(selected.longitude[j]), grid_lat=float(selected.latitude[j]), time_offset_seconds=float(abs((selected.time[j].values-time[j].values)/np.timedelta64(1,'s'))), uo=float(values[j,0]), vo=float(values[j,1]))
        p['status'] = 'held_access_error' if j in failures else ('matched' if np.isfinite(p['uo']) and np.isfinite(p['vo']) and p['time_offset_seconds'] <= 1800 else 'held_current_missing_or_time')
    for p in points:
        if not p['tracklet_time_valid']: p['status']='held_tracklet_time'
    fields = list(dict.fromkeys(k for p in points for k in p))
    with (OUT/'point_matches.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(points)
    counts = {s:sum(p['status']==s for p in points) for s in sorted({p['status'] for p in points})}
    complete = sum(all(p['status']=='matched' for p in points[n:n+5]) for n in range(0,len(points),5))
    report=dict(retrospective=True, fuel_validation=False, source_sha256=EXPECTED, current_dataset='cmems_mod_ibi_phy-cur_my_0.027deg_PT1H-m', version='202511', units={v:ds[v].attrs.get('units') for v in ('uo','vo')}, timestamp_assumption='AIS ts interpreted as Unix seconds UTC; source documentation confirmation pending', tracklets=len(rows), points=len(points), complete_tracklets=complete, status_counts=counts, method='nearest grid and hour; missing coastal cell held; no replacement; no extrapolation intended', script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()
