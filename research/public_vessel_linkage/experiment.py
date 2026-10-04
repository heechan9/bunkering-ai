"""Test exact public MMSI joins; refuse anonymous DataBio identity inference."""
from pathlib import Path
import json,zipfile,hashlib
import pandas as pd
HERE=Path(__file__).resolve().parent

def run():
 registry=pd.read_csv(HERE/'inputs/fishing-vessels-v3.csv',dtype={'mmsi':str},low_memory=False)
 r=registry[registry.year==2017].copy();duplicate=r.mmsi.duplicated(keep=False)
 unique=r[~duplicate];keys=set(unique.mmsi)
 selected=[]
 with zipfile.ZipFile(HERE/'inputs/mmsi-daily-csvs-10-v3-2017.zip') as z:
  for name in z.namelist():
   if not name.endswith('.csv'):continue
   date=name.rsplit('-v3-',1)[-1].removesuffix('.csv')
   if '2017-09-30'<=date<='2017-10-30':
    with z.open(name) as f:d=pd.read_csv(f,dtype={'mmsi':str})
    d['source_file']=name;selected.append(d)
 assert len(selected)==31,len(selected)
 d=pd.concat(selected,ignore_index=True)
 valid=(d.cell_ll_lat.between(-90,90)&d.cell_ll_lon.between(-180,180)&(d.hours>=0)&(d.fishing_hours>=0)&(d.fishing_hours<=d.hours+1e-8))
 d['registry_unique_match']=d.mmsi.isin(keys)
 matched=d[d.registry_unique_match].merge(unique,on='mmsi',validate='many_to_one',suffixes=('','_registry'))
 assert len(matched)==int(d.registry_unique_match.sum())
 day=d.groupby(['date','mmsi'],as_index=False)[['hours','fishing_hours']].sum()
 perday=d.groupby('date').agg(cell_rows=('mmsi','size'),unique_mmsi=('mmsi','nunique'),registry_matched_rows=('registry_unique_match','sum')).reset_index()
 with zipfile.ZipFile(HERE.parent/'fuel_source_review/inputs/DataBioDataset1.zip') as z:
  with z.open('ship_1.csv') as f:cols=pd.read_csv(f,nrows=0).columns.tolist()
 required=['mmsi','imo','latitude','longitude','vessel_name']
 present=[x for x in required if x.lower() in {c.lower() for c in cols}]
 assert present==[],present
 # No candidate may be declared a DataBio match solely because dates or engine power overlap.
 report={'source':'https://zenodo.org/records/14982712','scope':'2017-09-30 through 2017-10-30 inclusive; daily calendar grid aggregation; exact timezone alignment with DataBio unconfirmed','registry_2017_rows':len(r),'registry_2017_unique_mmsi':r.mmsi.nunique(),'registry_duplicate_key_rows_held':int(duplicate.sum()),'selected_days':len(selected),'selected_cell_rows':len(d),'selected_unique_mmsi':d.mmsi.nunique(),'valid_geometry_and_hours_rows':int(valid.sum()),'invalid_geometry_or_hours_rows':int((~valid).sum()),'exact_registry_join_rows':len(matched),'exact_registry_join_fraction':len(matched)/len(d),'vessel_days_hours_above24':int((day.hours>24+1e-6).sum()),'databio_identity_columns_present':present,'accepted_databio_ship1_matches':0,'decision':'public_registry_join_passed_databio_identity_link_blocked','limitations':['MMSI can be reused or spoofed; exact key is not conclusive physical identity.','No IMO/name in this GFW table; vessel properties may be inferred, not measured.','Daily 0.1-degree lower-left grid locations are not AIS point tracks or port arrival timestamps.','No common identifier or positions in DataBio; ship1 match must not be guessed.','No fuel savings, operating adoption, or causal energy policy validation.','GFW date bins and unconfirmed DataBio timezone prevent exact interval certification.']}
 report.update(vessel_day_count=len(day), vessel_day_hours_quantiles={str(k):float(x) for k,x in day.hours.quantile([0,.5,.9,.99,1]).items()}, vessel_days_above_24_01h=int((day.hours>24.01).sum()), vessel_days_above25h=int((day.hours>25).sum()), vessel_days_above48h=int((day.hours>48).sum()), duplicate_date_mmsi_grid_rows=int(d.duplicated(['date','mmsi','cell_ll_lat','cell_ll_lon']).sum()), invalid_nine_digit_mmsi_rows=int((~d.mmsi.str.fullmatch(r'[1-9][0-9]{8}')).sum()))
 report['decision']='registry_key_join_passed_daily_hours_quality_review_and_databio_identity_link_held'
 report['limitations'].append('Daily hours above24 are diagnostics and must not be silently capped or interpreted as exact port waiting; distinguish small boundary differences from material overcounting.')
 (HERE/'results/linkage_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');perday.to_csv(HERE/'results/daily_join_summary.csv',index=False)
 unique.to_csv(HERE/'inputs/registry_2017.csv',index=False);d.to_csv(HERE/'inputs/gfw_20170930_20171030.csv',index=False)
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':run()
