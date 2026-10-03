from pathlib import Path
import re,html,json,numpy as np,pandas as pd
P=Path(__file__).resolve().parent;B=P/'brest/Maritime Routes and Tracklets'
p=pd.read_csv(B/'prototypes.csv',sep='|');t=pd.read_csv(B/'tracklets.csv',sep='|')
# Local tangent-plane distance; baseline association, no learned parameters.
def xy(lon,lat):return np.column_stack([np.asarray(lon)*111.32*np.cos(np.deg2rad(48.4)),np.asarray(lat)*111.32])
segments={}
for name,g in p.groupby('route'):
 q=xy(g.sort_values('pointnumber').longitude,g.sort_values('pointnumber').latitude);segments[name]=(q[:-1],q[1:])
r=[]
for _,w in t.iterrows():
 pts=xy([w[f'lon{i}'] for i in range(1,6)],[w[f'lat{i}'] for i in range(1,6)])
 scores={}
 for name,(a,b) in segments.items():
  v=b-a;den=(v*v).sum(1);frac=np.clip(((pts[:,None,:]-a)*v).sum(2)/np.maximum(den,1e-15),0,1)
  dist=np.sqrt(((pts[:,None,:]-(a+frac[:,:,None]*v))**2).sum(2));scores[name]=dist.min(1).mean()
 pred=min(scores,key=scores.get);r.append(dict(tracklet=w.idtracklet,actual=w.route,predicted=pred,distance_km=scores[pred]))
r=pd.DataFrame(r);r.to_csv(P/'route_predictions.csv',index=False);known=r.actual.isin(segments);route=dict(routes=len(segments),tracklets=len(r),labelled_onroute=int(known.sum()),offroute=int((~known).sum()),onroute_accuracy=float((r.loc[known,'actual']==r.loc[known,'predicted']).mean()),offroute_detection='not implemented: nearest route always chooses a route')
# Official monthly series. Do not reinterpret monthly prices as hourly port quotes.
s=(P/'eia.html').read_text();data=[]
for block in re.findall(r'<tr>(.*?)</tr>',s,re.S):
 cells=[html.unescape(re.sub('<[^>]*>','',x)).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',block,re.S)]
 if len(cells)==13 and re.fullmatch(r'\d{4}',cells[0]):
  for month,val in enumerate(cells[1:],1):
   try:data.append(dict(date=f'{cells[0]}-{month:02d}-01',price_usd_gallon=float(val)))
   except ValueError:pass
f=pd.DataFrame(data);f.to_csv(P/'eia_monthly.csv',index=False);f['year']=f.date.str[:4].astype(int)
# Protocol fixed before results: annual blocks, zero initial/final inventory,
# demand=1000gal/month; tank=2000gal; up to 1 month advance buying, no fees.
x=[]
for year,g in f.groupby('year'):
 if len(g)!=12 or year<1984:continue
 pos=f.index[f.year==year][0];prices=g.price_usd_gallon.to_numpy();stock=0.;cost=0.;purchased=0.
 for j,price in enumerate(prices):
  past=f.iloc[max(0,pos+j-3):pos+j].price_usd_gallon
  target=2000. if j<11 and len(past)==3 and price<past.mean() else 1000.
  buy=max(0,target-stock);cost+=buy*price;purchased+=buy;stock+=buy-1000
  assert stock>=-1e-8
 assert abs(stock)<1e-8 and abs(purchased-12000)<1e-8
 base=prices.sum()*1000
 x.append(dict(year=int(year),monthly_purchase_cost=base,past_mean_rule_cost=cost,change_pct=(cost/base-1)*100))
x=pd.DataFrame(x);x.to_csv(P/'price_rule_results.csv',index=False)
result=dict(france_area=route,usa=dict(months=len(f),start=f.date.min(),end=f.date.max(),annual_cases=len(x),mean_annual_change_pct=float(x.change_pct.mean()),best_pct=float(x.change_pct.min()),worst_pct=float(x.change_pct.max()),improved_years=int((x.change_pct<0).sum())),japan=dict(status='not fuel-model executable',reason='JBC is a model-scale hydrodynamic benchmark; official site states no full scale ship exists. No calibrated engine fuel map or operational fuel labels in the acquired files. OCTARVIA access not established.'))
(P/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
