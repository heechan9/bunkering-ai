"""Deterministic fee sensitivity; not a tariff calculator or DQN evaluation."""
from itertools import product
from pathlib import Path
import csv,json,math

def fee(hours, hourly_fee, eligible, approved):
    if not all(math.isfinite(x) and x >= 0 for x in (hours,hourly_fee)):
        raise ValueError('finite nonnegative hours and assumed fee required')
    gross=hours*hourly_fee
    discount=min(hours,12)*hourly_fee if eligible and approved else 0
    return gross,discount,gross-discount

def run():
    rows=[]
    # Equal purchase quantity/terminal inventory. No consumption or safety difference assumed.
    # Monetary values are hypothetical KRW, NOT UPA published tariff or actual quotations.
    for qty,premium,hours,rate,time_cost in product([100,500],[0,1000,5000],[4,12,18],[10000,50000],[0,100000]):
        fuel=qty*800000
        gross,discount,net=fee(hours,rate,True,True)
        simultaneous=fuel+qty*premium  # assumed no incremental facility/time cost
        no_discount=fuel+gross+hours*time_cost
        discounted=fuel+net+hours*time_cost
        choice=lambda a,b:'tie' if a==b else ('separate' if a<b else 'simultaneous')
        rows.append(dict(quantity_t_assumed=qty,premium_KRW_t_assumed=premium,hours_assumed=hours,
          hourly_facility_fee_KRW_assumed=rate,hourly_time_cost_KRW_assumed=time_cost,
          discount_KRW=discount,separate_without_discount_KRW=no_discount,
          separate_with_discount_KRW=discounted,simultaneous_KRW=simultaneous,
          choice_without=choice(no_discount,simultaneous),choice_with=choice(discounted,simultaneous),
          break_even_premium_without_KRW_t=(gross+hours*time_cost)/qty,
          break_even_premium_with_KRW_t=(net+hours*time_cost)/qty))
    out=Path(__file__).parent/'results';out.mkdir(exist_ok=True)
    with (out/'scenarios.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    summary={'scenario_count':len(rows),'choice_changed_including_ties':sum(r['choice_without']!=r['choice_with'] for r in rows),
      'strict_switch_simultaneous_to_separate':sum(r['choice_without']=='simultaneous' and r['choice_with']=='separate' for r in rows),
      'maximum_assumed_discount_KRW':max(r['discount_KRW'] for r in rows),
      'official_model_changed':False,'actual_savings_estimated':False,
      'scope':'conditional incentive sensitivity; all prices, amounts, hours and linear fee rates are assumptions'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':run()
