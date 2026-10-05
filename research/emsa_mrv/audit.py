"""Reproduce the EMSA raw-workbook suitability audit; no savings inference."""
from pathlib import Path
import hashlib,json
import pandas as pd
ROOT=Path(__file__).resolve().parent
FUEL='Total fuel consumption [m tonnes]'
RATE='Fuel consumption per distance [kg / n mile]'
TIME='Time spent at sea [hours]'
output={'source':'https://mrv.emsa.europa.eu/#public/emission-report','files':[],'decision':'annual_ship_reference_only_not_operational_model_validation'}
for year,version in [(2024,246),(2025,59)]:
 p=ROOT/f'{year}-v{version}.xlsx'
 item={'year':year,'version':version,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'download_url':f'https://mrv.emsa.europa.eu/api/public-emission-report/reporting-period-document/binary/{year}/{version}','sheets':[]}
 x=pd.ExcelFile(p)
 for sheet in x.sheet_names:
  d=pd.read_excel(x,sheet_name=sheet,header=2)
  f=pd.to_numeric(d[FUEL],errors='coerce');t=pd.to_numeric(d[TIME],errors='coerce');q=pd.to_numeric(d[RATE],errors='coerce')
  stats={'name':sheet,'rows':len(d),'columns':len(d.columns),'unique_ship_imo':int(d['IMO Number'].nunique()),'duplicate_ship_imo_rows':int(d['IMO Number'].duplicated().sum()),'fuel_missing_or_nonnumeric':int(f.isna().sum()),'fuel_zero':int(f.eq(0).sum()),'fuel_negative':int(f.lt(0).sum()),'distance_intensity_missing_or_nonnumeric':int(q.isna().sum()),'sea_time_zero':int(t.eq(0).sum()),'hanbada_name_matches':int(d['Name'].astype(str).str.contains(r'HAN[\s-]*BADA',case=False,regex=True).sum()),'ship_types':d['Ship type'].value_counts().to_dict()}
  if 'Full' in sheet:
   eligible=d.loc[f.gt(0)&q.gt(0)&t.gt(0),['Ship type']].copy();eligible['fuel_tonnes']=f;eligible['kg_per_nm']=q
   groups=[]
   for typ,g in eligible.groupby('Ship type'):
    groups.append({'ship_type':typ,'eligible_rows':len(g),'median_reported_fuel_tonnes':float(g.fuel_tonnes.median()),'median_reported_kg_per_nm':float(g.kg_per_nm.median())})
   stats['positive_numeric_reference_rows']=len(eligible);stats['reference_by_ship_type']=groups
  item['sheets'].append(stats)
 output['files'].append(item)
output['limitations']=['Full and partial reports are audited separately; never summed together.','Positive numeric screening is not proof of record accuracy.','Annual MRV-scope total fuel in mass units does not match the existing 10-minute main-engine L/h target.','No speed-through-water, draught and wind synchronized series, bunkering event or ROB sequence is provided.','No inferred distance/speed derived from fuel targets is fed back as a predictor.','Hanbada name search is not an IMO-based identity verification.','No model retraining, replacement or causal fuel-saving claim.']
(ROOT/'audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for f in output['files']:
 print(f['year'],[(s['name'],s['rows'],s['fuel_zero'],s.get('positive_numeric_reference_rows'),s['hanbada_name_matches']) for s in f['sheets']])
