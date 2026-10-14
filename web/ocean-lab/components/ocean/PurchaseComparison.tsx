'use client';
import {useLocale} from '@/lib/locale';
import {decisionSnapshot,readingAge} from '@/lib/purchase-comparison';
import type {ReviewSelection} from '@/lib/scenario-review';
import FixedScenarioReview from './FixedScenarioReview';
import ArcticScenarioReview from './ArcticScenarioReview';
const format=(n:number|null,d=1)=>n===null?'—':n.toLocaleString('en-US',{maximumFractionDigits:d});
export default function PurchaseComparison({trace,index,replaySelection}:{trace:readonly (readonly number[])[];index:number;replaySelection?:ReviewSelection}){
 const {lang}=useLocale(),en=lang==='en',s=decisionSnapshot(trace,index);
 return <section className="purchase-comparison voyage-review" aria-labelledby="purchase-title">
  <h2 id="purchase-title">{en?'Compare choices at this step':'현재 단계의 구매안 비교'}</h2>
  {!s?<p role="status">{en?'This recorded voyage has ended. Move to an earlier step to compare choices.':'선택한 항차 기록이 종료됐습니다. 이전 단계로 이동하면 구매안을 비교할 수 있습니다.'}</p>:<>
   <p>{en?`After ${index} completed steps · decision ${index+1}. Recorded inputs below; candidate outcomes are calculated separately.`:`${index}단계 완료 후 · ${index+1}번째 선택 시점. 아래 기록값을 입력으로 후보 결과를 별도 계산합니다.`}</p>
   <p>{en?'Assumption: price and FX stay at their current values for the next step; consumption is 5 per step. No future recorded prices are used. This does not change the selected policy or replay.':'가정: 다음 단계 가격·환율은 현재값 유지, 단계당 소비량은 5입니다. 미래 기록 가격을 사용하지 않으며 선택한 정책과 재생 기록은 바뀌지 않습니다.'}</p>
   <div className="purchase-readings">
    {([{label:en?'Current fuel':'현재 잔량',r:s.fuel,scale:100},{label:en?'Current price':'현재 합성 가격',r:s.price,scale:1},{label:en?'Current FX':'현재 합성 환율',r:s.fx,scale:1},{label:en?'Previous price':'이전 합성 가격',r:s.previousPrice,scale:1}]).map(({label,r,scale})=><div key={label}><strong>{label}: {format(r.value===null?null:r.value*scale)}</strong><span>{r.kind==='missing'?(en?'Missing · not zero':'누락 · 0으로 대체하지 않음'):(en?`Synthetic record · ${readingAge(r,index)} steps old`:`합성 관측 기록 · ${readingAge(r,index)}단계 경과`)}</span></div>)}
   </div>
   <p className="small-muted">{en?'Observation timestamps are not provided. Age is measured in simulation steps, not real time. The next-step market is an explicit assumption, not an LSTM forecast. Fuel units: initial inventory = 100. SCI is a synthetic index, not currency.':'관측 시각은 미제공입니다. 정보 경과시간은 실제 시간이 아닌 시뮬레이션 단계로 표시합니다. 다음 시장값은 명시적 가정이며 LSTM 예측이 아닙니다. 연료 단위는 초기 잔량=100, SCI는 실제 금액이 아닌 합성 지표입니다.'}</p>
   <FixedScenarioReview snapshot={s} replaySelection={replaySelection}/>
  </>}
  <ArcticScenarioReview/>
 </section>;
}
