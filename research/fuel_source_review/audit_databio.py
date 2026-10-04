import hashlib,json,zipfile,io
from pathlib import Path
import pandas as pd
import openpyxl
HERE=Path(__file__).resolve().parent
p=HERE/'inputs/DataBioDataset1.zip'
keys=['measurement_time','AE_FO_consumption','ME_FO_consumption','propeller_shaft_output','ship_speed_actual','Ship_SpeedLOG','FO_density']
audit=[]
with zipfile.ZipFile(p) as z:
    doc=openpyxl.load_workbook(io.BytesIO(z.read('documentation.xlsx')),data_only=True)
    units={r[0]:r[1] for r in doc.active.values if r[0]}
    for name in ('ship_1.csv','ship_2.csv','ship_3.csv'):
        with z.open(name) as f:df=pd.read_csv(f,usecols=lambda c:c in keys)
        times=pd.to_datetime(df.measurement_time,errors='coerce');deltas=times.sort_values().diff().dt.total_seconds()
        result=dict(file=name,rows=len(df),first=str(times.min()),last=str(times.max()),duplicate_timestamps=int(times.duplicated().sum()),invalid_timestamps=int(times.isna().sum()),median_interval_seconds=float(deltas.median()),absent_columns=[k for k in keys if k not in df],fields={})
        for k in df.columns:
            if k=='measurement_time':continue
            v=pd.to_numeric(df[k],errors='coerce')
            result['fields'][k]=dict(unit=units.get(k),missing=int(v.isna().sum()),negative=int((v<0).sum()),zero=int((v==0).sum()),min=float(v.min()),max=float(v.max()))
        audit.append(result)
(HERE/'results').mkdir(exist_ok=True)
out=dict(source='https://zenodo.org/records/3563390',md5=hashlib.md5(p.read_bytes()).hexdigest(),md5_matches_publisher=hashlib.md5(p.read_bytes()).hexdigest()=='d733e2cfa450e26580295cf3fc2fd7a0',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ships=audit,unit_issue='Documentation lists main engine l/h, auxiliary kg/h; do not add without justified conversion. Total documented unit kg is ambiguous relative to rate inputs.',status='downloaded_and_audited_not_trained_not_adopted')
(HERE/'results/databio_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
