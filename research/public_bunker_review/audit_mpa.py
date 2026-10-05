"""Audit pinned MPA workbook; requires pandas/xlrd. No automatic updates."""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('workbook',type=Path);a=p.parse_args()
h=hashlib.sha256(a.workbook.read_bytes()).hexdigest()
if h!='55da8965284620774373593e4d4942c6537532e5fae108af95e40340cfbc603e':raise ValueError('Source version changed; review before recalculating')
x=pd.read_excel(a.workbook,header=None)
r={'unit':'1000 tonnes','2025_annual':float(x.iloc[16,1]),'2025_month_sum':float(pd.to_numeric(x.iloc[19:31,1]).sum()),'2026_aug_preliminary_tonnes':float(x.iloc[41,1])*1000,'2026_jul_tonnes':float(x.iloc[40,1])*1000,'sha256':h}
r['aug_mom_pct']=(r['2026_aug_preliminary_tonnes']/r['2026_jul_tonnes']-1)*100
print(json.dumps(r,indent=2))
