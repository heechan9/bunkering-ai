'use client';
import {useLocale} from '@/lib/locale';
import {comparePurchases,decisionSnapshot,readingAge} from '@/lib/purchase-comparison';
import {Table,TableHeader,TableHead,TableBody,TableRow,TableCell} from '@/components/ui/table';
const format=(n:number|null,d=1)=>n===null?'—':n.toLocaleString('en-US',{maximumFractionDigits:d});
export default function PurchaseComparison({trace,index}:{trace:readonly (readonly number[])[];index:number}){
 const {lang}=useLocale(),en=lang==='en',s=decisionSnapshot(trace,index);
 const label=(buy:boolean)=>buy?(en?'Buy':'구매'):(en?'Wait':'미구매');
 const candidates=s?comparePurchases(s):[];
 return <section className="purchase-comparison voyage-review" aria-labelledby="purchase-title">
  <h2 id="purchase-title">{en?'Compare choices at this step':'현재 단계의 구매안 비교'}</h2>
  {!s?<p role="status">{en?'This recorded voyage has ended. Move to an earlier step to compare choices.':'선택한 항차 기록이 종료됐습니다. 이전 단계로 이동하면 구매안을 비교할 수 있습니다.'}</p>:<>
   <p>{en?`After ${index} completed steps · decision ${index+1}. Recorded inputs below; candidate outcomes are calculated separately.`:`${index}단계 완료 후 · ${index+1}번째 선택 시점. 아래 기록값을 입력으로 후보 결과를 별도 계산합니다.`}</p>
   <p>{en?'Assumption: price and FX stay at their current values for the next step; consumption is 5 per step. No future recorded prices are used. This does not change the selected policy or replay.':'가정: 다음 단계 가격·환율은 현재값 유지, 단계당 소비량은 5입니다. 미래 기록 가격을 사용하지 않으며 선택한 정책과 재생 기록은 바뀌지 않습니다.'}</p>
   <div className="purchase-readings">
    {([{label:en?'Current fuel':'현재 잔량',r:s.fuel,scale:100},{label:en?'Current price':'현재 합성 가격',r:s.price,scale:1},{label:en?'Current FX':'현재 합성 환율',r:s.fx,scale:1},{label:en?'Previous price':'이전 합성 가격',r:s.previousPrice,scale:1}]).map(({label,r,scale})=><div key={label}><strong>{label}: {format(r.value===null?null:r.value*scale)}</strong><span>{r.kind==='missing'?(en?'Missing · not zero':'누락 · 0으로 대체하지 않음'):(en?`Synthetic record · ${readingAge(r,index)} steps old`:`합성 관측 기록 · ${readingAge(r,index)}단계 경과`)}</span></div>)}
   </div>
   <p className="small-muted">{en?'Observation timestamps are not provided. Age is measured in simulation steps, not real time. The next-step market is an explicit assumption, not an LSTM forecast. Fuel units: initial inventory = 100. SCI is a synthetic index, not currency.':'관측 시각은 미제공입니다. 정보 경과시간은 실제 시간이 아닌 시뮬레이션 단계로 표시합니다. 다음 시장값은 명시적 가정이며 LSTM 예측이 아닙니다. 연료 단위는 초기 잔량=100, SCI는 실제 금액이 아닌 합성 지표입니다.'}</p>
   {!candidates.length?<p role="status">{en?'Comparison paused: current fuel, price or FX is missing, stale or invalid.':'현재 잔량·가격·환율이 누락됐거나 오래됐거나 유효하지 않아 비교를 보류합니다.'}</p>:<>
   <Table><TableHeader><TableRow>{(en?['Choice sequence','Calculated flow · fuel after each step','Total purchase','Scenario SCI','Ending fuel','Checks']:['선택 순서','계산된 흐름 · 단계 후 잔량','총 구매량','가정 SCI','종료 잔량','기준 확인']).map(h=><TableHead key={h} scope="col">{h}</TableHead>)}</TableRow></TableHeader><TableBody>
   {candidates.map((c,i)=>{const risk=c.steps.some(r=>r.reserveViolation),short=c.steps.some(r=>r.unmet>1e-12),boundary=c.steps.some(r=>r.rawViolation&&!r.reserveViolation);return <TableRow key={i}><TableCell>{c.actions.map(label).join(' → ')}</TableCell><TableCell><ol className="candidate-flow">{c.steps.map((r,j)=><li key={j}>{en?`Step ${index+j+1}`:`${index+j+1}단계`}: {label(r.buy)} {format(r.amount*100)} → {format(r.fuelAfter*100)}</li>)}</ol>{c.stopped&&<strong>{en?'Stopped: fuel depleted; later action not executed':'고갈 종료 · 이후 선택 실행 불가'}</strong>}</TableCell><TableCell>{format(c.amount*100)}</TableCell><TableCell>{format(c.cost,0)}</TableCell><TableCell>{format(c.finalFuel*100)}</TableCell><TableCell>{c.stopped?(en?'Depleted':'고갈'):risk?(en?'Below reserve 15':'최소잔량 15 미달'):(en?'Reserve 15 met':'최소잔량 15 충족')}{short&&<span className="candidate-flag">{en?'Consumption shortage before refill':'급유 전 소비량 부족'}</span>}{boundary&&<span className="candidate-flag">{en?'Floating-point boundary':'부동소수점 경계'}</span>}</TableCell></TableRow>})}
   </TableBody></Table>
   <p className="small-muted">{en?'Flow follows the existing consume-then-refill model (requested refill 90, cap 95). Reserve checks allow numerical tolerance 10⁻¹². Port supply, fuel grades and service time are not modeled. Lower spending with less ending fuel or early failure is not a savings claim. No candidate is ranked as a recommendation.':'기존 소비 후 급유 모델(요청량 90, 상한 95)의 흐름입니다. 잔량 판정은 수치 허용오차 10⁻¹²를 적용합니다. 항만 공급·연료 규격·작업시간은 미구현입니다. 종료 잔량 감소나 조기 실패로 낮아진 지출을 절감으로 해석하지 않으며 후보를 추천 순위로 표시하지 않습니다.'}</p>
   </>}
  </>}
 </section>;
}
