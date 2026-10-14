'use client';
import {useState,type Dispatch,type SetStateAction} from 'react';
import {useLocale} from '@/lib/locale';
import {Button} from '@/components/ui/button';
import {ARCTIC_PRESETS,COMMON_FIELDS,arcticPreset,parseArctic,reviewArctic,arcticExport,type CommonField,type ArcticForm,type ArcticPreset,type ArcticReason,type Supply} from '@/lib/arctic-scenario';

const format=(value:number|null,digits=2)=>value===null?'UNKNOWN':value.toLocaleString('en-US',{maximumFractionDigits:digits});
const fuel=(value:number|null)=>format(value===null?null:value*100);
const commonLabels:Record<CommonField,[string,string]>={
  initialFuel:['시작 연료 (100점 탱크)','Starting fuel (100-point tank)'],price:['고정 합성 가격 지수','Fixed synthetic price index'],fx:['고정 합성 환율 지수','Fixed synthetic FX index'],
  baseConsumption:['기본 구간 소비량 (연료점)','Base consumption per leg (fuel points)'],travelHours:['구간별 기본 이동 (h)','Base travel per leg (h)'],
  bunkerWorkHours:['구매 선택별 작업 (h)','Work per Buy (h)'],arrivalDeadlineHours:['최종 도착 마감 (h)','Final arrival deadline (h)'],
};
const presetLabels:Record<ArcticPreset,[string,string]>={normal:['정상','Normal'],'delay-fuel':['지연 + 소비 증가','Delay + higher consumption'],'supply-unavailable':['지연 + 중간 급유 불가','Delay + intermediate supply unavailable']};
const reasonLabels:Record<ArcticReason,[string,string]>={missing_input:['공통·구간 입력 누락','Missing common/leg inputs'],invalid_input:['입력 오류','Invalid input'],
  unknown_supply:['구매 지점 공급 여부 불명','Supply unknown at requested Buy'],unavailable_supply:['구매 지점 급유 불가','Supply unavailable at requested Buy'],
  fuel_shortage:['구간 연료 부족 · 후속 진행 중단','Leg fuel shortage; onward execution stopped'],reserve_breach:['급유 전 도착 여유 15 미달','Arrival reserve below 15 before any later refill'],
  arrival_deadline:['최종 도착 마감 초과','Final arrival deadline exceeded'],arithmetic:['수치 계산 범위 초과','Arithmetic out of range']};

export type ArcticScenarioReviewProps = {
  form?: ArcticForm;
  onFormChange?: Dispatch<SetStateAction<ArcticForm>>;
  integrated?: boolean;
};

export default function ArcticScenarioReview({form:controlledForm,onFormChange,integrated=false}:ArcticScenarioReviewProps={}) {
  const {lang}=useLocale(),en=lang==='en';
  const [localForm,setLocalForm]=useState(()=>arcticPreset('normal'));
  const form=controlledForm??localForm,setForm=onFormChange??setLocalForm;
  const [lastExport,setLastExport]=useState<{key:string;status:'saved'|'failed'}|null>(null);
  const currentKey=JSON.stringify(form),input=parseArctic(form),review=reviewArctic(input);
  const status={feasible:en?'Passes synthetic checks':'합성 제약 충족',infeasible:en?'Excluded':'제약 위반 · 제외',incomplete:en?'Incomplete':'입력 부족 · 보류',invalid:en?'Invalid':'입력 오류 · 보류'};
  const choice=(buy:boolean)=>buy?(en?'Buy':'구매'):(en?'Wait':'미구매');
  const fieldLabel=(key:string)=>{
    if(COMMON_FIELDS.includes(key as CommonField)) return commonLabels[key as CommonField][en?1:0];
    const match=/^leg(\d)\.(consumptionMultiplier|delayHours|supply)$/.exec(key);
    return match?`${en?'Leg':'구간'} ${match[1]}: ${match[2]==='consumptionMultiplier'?(en?'Consumption multiplier':'소비 배수'):match[2]==='delayHours'?(en?'Extra delay (h)':'추가 지연 (h)'):(en?'Supply':'급유 가능 여부')}`:key;
  };
  function download() {
    try {
      const payload=arcticExport(form,new Date().toISOString());
      const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
      const anchor=document.createElement('a');anchor.href=url;anchor.download=`bunkering-arctic-synthetic-${form.preset}.json`;
      document.body.appendChild(anchor);anchor.click();anchor.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
      setLastExport({key:currentKey,status:'saved'});
    } catch {setLastExport({key:currentKey,status:'failed'});}
  }
  return <section className="arctic-scenario-review" aria-labelledby="arctic-title">
    <div className="scenario-heading"><div><span className="scenario-tag">{en?'ARCTIC-INSPIRED · SYNTHETIC ONLY':'북극항로 착안 · 합성 실험 전용'}</span><h3 id="arctic-title">{en?'Delay, fuel and intermediate supply':'지연·연료·중간 급유 가능성'}</h3></div><Button variant="outline" onClick={download}>{en?'Export Arctic scenario JSON':'북극 합성 검토 JSON 저장'}</Button></div>
    <p>{en?'Compare the four Buy / Wait combinations for A → B → destination.':'A → B → 도착 구간의 구매·미구매 조합 네 가지를 비교합니다.'}</p>
    <p className="arctic-warning">{en?'Synthetic assumptions only · not validated for real navigation or safety.':'합성 가정 전용 · 실제 항해 가능성이나 안전을 검증한 결과가 아닙니다.'}</p>
    <div className="scenario-presets" aria-label={en?'Arctic-inspired synthetic presets':'북극 착안 합성 예시'}>{ARCTIC_PRESETS.map(preset=><Button key={preset} variant="outline" aria-pressed={form.preset===preset} onClick={()=>setForm(previous=>arcticPreset(preset,previous.common))}>{presetLabels[preset][en?1:0]}</Button>)}<Button variant="outline" onClick={()=>setForm(arcticPreset('normal'))}>{en?'Reset all inputs':'전체 입력 초기화'}</Button></div>
    <p className="small-muted">{en?'Preset switches replace only leg delay, consumption multipliers and supply. Shared starting conditions stay unchanged for fair comparison. Manual edits stay unverified. Reset restores every default.':'예시를 바꾸면 구간 지연·소비 배수·공급 여부만 바뀝니다. 공정한 비교를 위해 공통 시작 조건은 유지됩니다. 직접 수정해도 검증된 자료가 되지는 않습니다. 전체 초기화는 모든 기본값을 복원합니다.'}</p>
    <details className="scenario-inputs"><summary>{en?'Common conditions · same for every candidate':'공통 조건 · 모든 후보에 동일 적용'}</summary><div className="scenario-fields">{COMMON_FIELDS.map(field=><label key={field} htmlFor={`arctic-${field}`}><span>{commonLabels[field][en?1:0]}</span><input id={`arctic-${field}`} name={field} type="number" min="0" max={field==='initialFuel'?100:undefined} step="any" inputMode="decimal" placeholder="UNKNOWN" value={form.common[field]} onChange={event=>setForm(previous=>({...previous,common:{...previous.common,[field]:event.target.value}}))}/></label>)}</div><p className="small-muted">{en?'Blank = UNKNOWN. Fuel uses a 100-point tank, refill target 95, request limit 90, minimum arrival reserve 15. SCI is a synthetic index, not currency.':'빈칸은 UNKNOWN입니다. 연료는 100점 탱크, 급유 목표 95·요청 상한 90·도착 최소 여유 15를 사용합니다. SCI는 실제 통화가 아닌 합성 지표입니다.'}</p></details>
    <details className="scenario-inputs"><summary>{en?'Leg assumptions · consumption, delay and supply':'구간 가정 · 소비량·지연·급유 가능성'}</summary><div className="arctic-leg-inputs">{form.legs.map((leg,i)=><fieldset key={i} className="scenario-inputs"><legend>{i===0?(en?'Leg 1 · supply at A':'1구간 · A에서 급유'):(en?'Leg 2 · supply at B':'2구간 · B에서 급유')}</legend><div className="scenario-fields">
      {(['consumptionMultiplier','delayHours'] as const).map(field=><label key={field} htmlFor={`arctic-leg-${i}-${field}`}><span>{field==='consumptionMultiplier'?(en?'Consumption multiplier (×)':'소비 배수 (×)'):(en?'Additional travel delay (h)':'추가 이동 지연 (h)')}</span><input id={`arctic-leg-${i}-${field}`} type="number" min="0" step="any" inputMode="decimal" placeholder="UNKNOWN" value={leg[field]} onChange={event=>setForm(previous=>({...previous,legs:previous.legs.map((item,j)=>i===j?{...item,[field]:event.target.value}:item) as typeof previous.legs}))}/></label>)}
      <label htmlFor={`arctic-leg-${i}-supply`}><span>{en?'Bunkering supply assumption':'급유 가능 여부 가정'}</span><select id={`arctic-leg-${i}-supply`} value={leg.supply} onChange={event=>setForm(previous=>({...previous,legs:previous.legs.map((item,j)=>i===j?{...item,supply:event.target.value as Supply}:item) as typeof previous.legs}))}><option value="available">{en?'Available (assumed)':'가능 (가정)'}</option><option value="unavailable">{en?'Unavailable (assumed)':'불가 (가정)'}</option><option value="unknown">UNKNOWN</option></select></label>
    </div></fieldset>)}</div></details>
    <p className="scenario-summary arctic-summary" role="status">{en?`${review.eligibleCount}/4 candidates pass synthetic checks${review.tied?' · Adjusted SCI tied':''}`:`4개 후보 중 ${review.eligibleCount}개 합성 제약 충족${review.tied?' · 보정 SCI 동률':''}`}</p>
    {[...review.missing,...review.invalid].length>0&&<p role="status">{en?'Check these inputs: ':'입력 확인: '}{[...review.missing,...review.invalid].map(fieldLabel).join(' · ')}</p>}
    <div className="arctic-candidates">{review.candidates.map(candidate=><article key={candidate.id} className="arctic-candidate" data-candidate={candidate.id}>
      <h4>{en?'A':'출발 A'}: {choice(candidate.actions[0])} → {en?'B':'중간 B'}: {choice(candidate.actions[1])}</h4><p className={`scenario-status ${candidate.status}`}>{status[candidate.status]}</p>
      {candidate.reasons.length>0&&<ul className="arctic-reasons">{candidate.reasons.map(reason=><li key={reason}>{reasonLabels[reason][en?1:0]}</li>)}</ul>}
      <dl className="arctic-metrics"><div><dt>{en?'Final arrival / deadline (h)':'최종 도착 / 마감 (h)'}</dt><dd>{format(candidate.arrivalHours)} / {format(input.common.arrivalDeadlineHours)}</dd></div><div><dt>{en?'Ending fuel':'종료 연료'}</dt><dd>{fuel(candidate.finalFuel)}</dd></div><div><dt>{en?'Purchase SCI':'구매 SCI'}</dt><dd>{format(candidate.purchaseSCI)}</dd></div><div><dt>{en?'Eligible adjusted SCI':'비교 가능한 보정 SCI'}</dt><dd>{candidate.comparableSCI===null?'—':format(candidate.comparableSCI)}{candidate.rank!==null&&<small>{en?`${review.tied?'Tied eligible':'Eligible'} rank ${candidate.rank}`:`충족 후보 내 ${review.tied?'공동 ':''}${candidate.rank}위`}</small>}</dd></div></dl>
      <ol className="arctic-flow">{candidate.steps.map(step=>{
        const unreached=step.arrivalFuel!==null&&step.arrivalFuel<0;
        return <li key={step.leg}><strong>{en?'Leg':'구간'} {step.leg}{unreached&&(en?' · Projected endpoint, not reached':' · 미도달 예상 끝점')}</strong><span>{unreached?(en?'Projected fuel balance: ':'예상 연료 수지: '):(en?'Fuel: ':'연료: ')}{fuel(step.openingFuel)} + {fuel(step.amount)} − {fuel(step.consumption)} = {fuel(step.arrivalFuel)}</span><span>{unreached?(en?'Departure → projected endpoint (not reached): ':'출발 → 예상 끝점 (미도달): '):(en?'Departure → arrival: ':'출발 → 도착: ')}{format(step.departureHours)} → {format(step.arrivalHours)} h</span><span>{en?'Work + travel + delay: ':'작업 + 이동 + 지연: '}{format(step.workHours)} + {format(step.travelHours)} + {format(step.delayHours)} h</span></li>;
      })}</ol>
      {(candidate.steps.length<2||candidate.steps.some(step=>step.arrivalFuel===null||step.arrivalFuel<0))&&<p className="small-muted">{en?'The voyage cannot be completed from these inputs. Negative leg endpoints are projections, not achieved arrivals. Full-horizon totals remain UNKNOWN.':'현재 입력으로 전체 항차를 완료할 수 없습니다. 연료가 음수인 구간 끝점은 실제 도착이 아닌 예상 수지입니다. 전체 구간 합계는 UNKNOWN으로 둡니다.'}</p>}
    </article>)}</div>
    <p className="small-muted">{en?'Adjusted SCI = purchase SCI + (starting fuel − ending fuel) × price × FX, using normalized fuel. The same valuation is used for every candidate and both inventories. At fixed prices, completed paths with equal consumption tie; lower cash outlay is not savings. Excluded, invalid or incomplete choices are never ranked.':'보정 SCI = 구매 SCI + (시작 연료 − 종료 연료) × 가격 × 환율이며 정규화 연료로 계산합니다. 모든 후보와 시작·종료 재고에 같은 가치를 적용합니다. 고정 가격에서 소비량이 같은 완료 후보는 동률이며, 지출 감소는 절감이 아닙니다. 위반·오류·입력 부족 후보는 순위에서 제외합니다.'}</p>
    <details className="scenario-assumptions"><summary>{en?'Synthetic calculation rules and limits':'합성 계산 규칙과 한계'}</summary>    <p>{en?'Two abstract legs: origin A → intermediate B → destination. Choose Buy or Wait before each leg. All numbers and supply switches are invented, editable assumptions. No actual Arctic ports, ice or seasonal data are used.':'추상 구간 두 개: 출발 A → 중간 B → 도착. 각 구간 출발 전에 구매·미구매를 선택합니다. 모든 수치와 공급 여부는 수정 가능한 가상 가정이며, 실제 북극 항만·빙해·계절 자료는 사용하지 않습니다.'}</p>
    <p className="arctic-warning">{integrated?(en?'These are the same editable assumptions used in your Arctic voyage. Changes carry between voyage and comparison tabs. This does not establish real navigation, safety, Polar Code compliance, savings or DQN performance; it does not use the saved 30-step policy replay.':'북극 운항 체험과 동일한 편집 가정입니다. 변경값은 운항·비교 탭 사이에 유지됩니다. 실제 항해 가능성·안전·Polar Code 준수·절감·DQN 성능을 입증하지 않으며, 기존 30단계 정책 재생 기록을 사용하지 않습니다.'):(en?'This does not establish real navigation, safety, Polar Code compliance, savings or DQN performance. It is separate from the saved replay and policies; replay controls do not change this panel’s inputs.':'실제 항해 가능성·안전·Polar Code 준수·절감·DQN 성능을 입증하지 않습니다. 기존 재생 기록·정책과 분리된 실험으로, 재생 화면의 선택은 이 패널 입력을 바꾸지 않습니다.')}</p>
<p className="small-muted">{en?'Buy happens BEFORE travel. Reserve checks happen on each arrival before any later refill. Every Buy uses the full fixed work time, including zero/clipped deliveries; unavailable Buy has zero delivery and is excluded. Travel, extra delay and work accumulate without recovery; arrival at the deadline passes (floating roundoff only; no grace period). Consumption = base per-leg fuel × multiplier, independent of time. Extra delay does not separately burn fuel. Unknown supply blocks only a Buy at that stop; missing numeric inputs block all candidates.':'구매 후 이동하며, 매 구간 도착 시 다음 급유 전에 연료 여유를 검사합니다. 급유량이 줄거나 0이어도 구매에는 고정 작업시간을 적용합니다. 급유 불가 지점의 구매는 공급량 0으로 계산하고 제외합니다. 이동·추가 지연·작업시간은 회복 없이 누적하며, 도착 마감과 같은 시각은 통과입니다(부동소수점 오차만 허용, 유예시간 없음). 소비량 = 구간 기본량 × 배수로 시간과 독립적입니다. 지연에 따른 별도 연료 소비는 없습니다. 공급 여부 UNKNOWN은 해당 지점 구매 후보만 보류하며, 숫자 입력 누락은 모든 후보를 보류합니다.'}</p><p className="small-muted">{integrated?(en?'The illustrative map does not enter these calculations. No ice resistance, weather, ship class, icebreaker, actual port supply, fuel grades, regulation or other costs are modeled. Edits carry between the voyage and comparison tabs in this session, but are not saved in share links or after reload. Save JSON before leaving.':'설명용 지도 형상은 계산에 들어가지 않습니다. 빙저항·기상·선급·쇄빙선·실제 항만 공급·유종·규정·기타 비용은 모델링하지 않습니다. 이번 세션의 운항·비교 탭 사이에 편집값이 유지되지만 공유 링크나 새로고침 후에는 보존되지 않습니다. 나가기 전에 JSON으로 보관하세요.'):(en?'No route geometry, ice resistance, weather, ship class, icebreaker, actual port supply, fuel grades, regulation or other costs are modeled. Edited values persist within this panel only; selection links do not preserve them. Save JSON before leaving.':'항로 형상·빙저항·기상·선급·쇄빙선·실제 항만 공급·유종·규정·기타 비용은 모델링하지 않습니다. 편집값은 이 패널 안에서만 유지되고 선택 링크에 저장되지 않습니다. 나가기 전에 JSON으로 보관하세요.')}</p></details>
    {lastExport&&<p role="status" className="arctic-export-status">{lastExport.key!==currentKey?(en?'Inputs changed since the last export. Export again to save the current result.':'마지막 저장 이후 입력이 바뀌었습니다. 현재 결과를 보관하려면 다시 저장하세요.'):lastExport.status==='saved'?(en?'JSON download started with current raw inputs, provenance and full-precision results.':'현재 원본 입력·출처 구분·반올림 전 결과의 JSON 다운로드를 시작했습니다.'):(en?'Download failed. Please try again.':'다운로드에 실패했습니다. 다시 시도해 주세요.')}</p>}
  </section>;
}
