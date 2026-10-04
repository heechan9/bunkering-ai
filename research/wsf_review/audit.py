"""Visually transcribed FY2025 WSF tables; aggregate accounting, not vessel logs."""
from pathlib import Path
import pandas as pd,json,hashlib
HERE=Path(__file__).resolve().parent
budget=[1690049,1692186,1588412,1523259,1462816,1502750,1450269,1306792,1460914,1463730,1527537,1563348]
actual=[1278797,1241484,1206993,1295424,1279796,1337691,1313231,1140758,1292811,1257884,1298113,1283011]
contracted=[756000,756000,756000,756000,1050000,756000,756000,756000,756000,840000,1218000,1134000]
settlement=[-78246,-210470,-346777,-196787,-171570,-204422,-14364,-45662,-192704,-211798,-246443,-33718]
if __name__=='__main__':
 out=HERE/'results';out.mkdir(exist_ok=True)
 df=pd.DataFrame(dict(month=pd.date_range('2024-07-01',periods=12,freq='MS').strftime('%Y-%m'),budget_gallons=budget,consumed_gallons=actual,swap_notional_gallons=contracted,swap_net_cash_usd=settlement))
 df.to_csv(out/'monthly_2025.csv',index=False)
 r={'scope':'WSF fleet monthly aggregates; no vessel_id,ROB,physical delivery date or port-level purchase price','pages':'FY2025 report printed pp8-10; visually transcribed image tables','budget_sum':sum(budget),'budget_report':18232062,'consumption_sum':sum(actual),'consumption_report':15225993,'notional_sum':sum(contracted),'notional_report':10290000,'monthly_settlement_sum':sum(settlement),'settlement_report':-1952962,'budget_minus_actual_pct':100*(sum(budget)-sum(actual))/sum(budget),'issues':['Executive summary describes86533 received; this equals swap6 alone. Appendix B total is negative1952962; do not claim net hedging gain.','Some headings say FY2024 in FY2025 tables; Attachment A B5-inclusive prices differ from Appendix B swap strike prices; not interchangeable.','Monthly rounded cash amounts differ from reported total by1USD. Preserve both.','Budget underspend is not causal fuel saving: service changes and vessel availability confound it.','FY2021 consumption differs across reports:15391626 in FY2025 hedging text vs15415327 in FY2024 performance table. Do not silently join.'],'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (HERE/'inputs').glob('*.pdf')}}
 assert abs(sum(budget)-18232062)<=2 and abs(sum(actual)-15225993)<=2 and sum(contracted)==10290000
 (out/'audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,indent=2))
