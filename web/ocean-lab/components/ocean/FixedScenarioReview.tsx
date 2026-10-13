'use client';
import {useState} from 'react';
import {useLocale} from '@/lib/locale';
import type {DecisionSnapshot} from '@/lib/purchase-comparison';
import {parseTiming, reviewScenario, scenarioExport, scenarioPreset, SOURCE_REVISION, TIME_FIELDS, type Reason, type TimeField, type ReviewSelection} from '@/lib/scenario-review';
import {Button} from '@/components/ui/button';
import {Table,TableHeader,TableHead,TableBody,TableRow,TableCell} from '@/components/ui/table';

const format = (value:number|null, digits=1) => value === null ? '—' : value.toLocaleString('en-US',{maximumFractionDigits:digits});
const fieldLabels: Record<TimeField,[string,string]> = {
  baselineDeparture:['급유 없는 출항','Departure without bunkering'], cargoEnd:['급유 영향 반영 하역 종료','Cargo end including bunker impact'],
  bunkerReady:['급유 준비 가능 시각','Bunker-ready time'], preparation:['급유 준비 시간','Preparation duration'], transfer:['이송 시간','Transfer duration'],
  cleanup:['마무리 시간','Cleanup duration'], departureReadiness:['모든 작업 후 출항 준비','Post-work departure readiness'], deadline:['출항 마감','Departure deadline'],
};
const reasonLabels: Record<Reason,[string,string]> = {
  fuel_shortage:['급유 전 소비량 부족','Consumption shortage before refill'], reserve_breach:['급유 전 안전여유 15 미달','Pre-refill reserve below 15'],
  capacity:['탱크·급유 상한 위반','Tank/refill capacity exceeded'], depleted:['고갈 또는 이후 단계 미실행','Depleted or later step not executed'],
  deadline:['출항 마감 초과','Departure deadline exceeded'], missing_time:['작업·마감 입력 누락','Missing work/deadline inputs'],
  invalid_time:['유효하지 않은 시간 입력','Invalid time input'], arithmetic:['수치 계산 범위 초과','Arithmetic out of range'],
};
export default function FixedScenarioReview({snapshot,replaySelection}:{snapshot:DecisionSnapshot|null;replaySelection?:ReviewSelection}) {
  const {lang}=useLocale(), en=lang==='en';
  const [form,setForm]=useState(()=>scenarioPreset('normal'));
  const [exportStatus,setExportStatus]=useState<'saved'|'failed'|null>(null);
  const review=reviewScenario(snapshot,parseTiming(form));
  const label=(buy:boolean)=>buy?(en?'Buy':'구매'):(en?'Wait':'미구매');
  function download() {
    try {
      const payload=scenarioExport(snapshot,form,new Date().toISOString(),replaySelection);
      const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
      const anchor=document.createElement('a'); anchor.href=url; anchor.download=`bunkering-fixed-review-step-${review.decision??'ended'}.json`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url),1000); setExportStatus('saved');
    } catch {setExportStatus('failed');}
  }
  const statusLabel={feasible:en?'Passes modeled checks':'가정 제약 충족',infeasible:en?'Excluded':'제약 위반 · 제외',incomplete:en?'Incomplete':'입력 부족 · 보류',invalid:en?'Invalid':'입력 오류 · 보류'};
  return <div className="fixed-scenario-review">
    <div className="scenario-heading"><div><span className="scenario-tag">{en?'FIXED SYNTHETIC SCENARIO':'고정 합성 시나리오'}</span><h3>{en?'Fuel, work time and departure review':'연료·작업시간·출항 마감 검토'}</h3></div><Button variant="outline" onClick={download} disabled={!review.candidates.length}>{en?'Export review JSON':'검토 결과 JSON 저장'}</Button></div>
    <p>{en?'Review the next one or two buy/wait choices against explicit assumptions. This is not a real-route optimizer or a replacement for the 30-step policy. Passing these checks does not establish real-world feasibility.':'다음 1~2단계의 구매·미구매 후보를 명시한 가정으로 검토합니다. 실제 항로 최적화나 30단계 정책 대체 기능이 아니며, 검사 통과가 실선 운항 가능성을 뜻하지 않습니다.'}</p>
    <div className="scenario-presets" aria-label={en?'Synthetic presets':'합성 예시 선택'}>
      <Button variant="outline" onClick={()=>{setForm(scenarioPreset('normal'));setExportStatus(null);}}>{en?'Normal example':'정상 예시'}</Button>
      <Button variant="outline" onClick={()=>{setForm(scenarioPreset('deadline'));setExportStatus(null);}}>{en?'Deadline conflict':'마감 충돌 예시'}</Button>
      <Button variant="outline" onClick={()=>{setForm(scenarioPreset('missing'));setExportStatus(null);}}>{en?'Missing inputs':'입력 누락 예시'}</Button>
    </div>
    <details className="scenario-inputs" open><summary>{en?'Time assumptions · editable hours':'시간 가정 · 시간(h) 단위로 수정'}</summary>
      <p className="small-muted">{en?'The same existing-cargo-call template is used at each step. Event times share a local zero; baseline step origins are 0 h and 24 h. Earlier extra delay is added without recovery. Blank means UNKNOWN.':'각 단계에 같은 기존 화물 기항 양식을 적용합니다. 시각은 기항별 같은 기준점 0을 사용하며 기본 단계 시작은 0h·24h입니다. 앞 단계 추가 지연은 회복 없이 더합니다. 빈칸은 UNKNOWN입니다.'}</p>
      <div className="scenario-fields">{TIME_FIELDS.map(field=><label key={field} htmlFor={`scenario-${field}`}><span>{fieldLabels[field][en?1:0]} <small>(h)</small></span><input id={`scenario-${field}`} name={field} type="number" min="0" step="any" inputMode="decimal" placeholder="UNKNOWN" value={form[field]} onChange={event=>{setForm(previous=>({...previous,[field]:event.target.value}));setExportStatus(null);}}/></label>)}</div>
      <p className="small-muted">{en?'Departure without bunkering already includes readiness. Cargo end must include bunker interruptions; bunker-ready includes access/waiting. Preparation → transfer → cleanup are sequential. Readiness starts after BOTH cargo and bunker work, with no overlap or double counting. These are unverified synthetic assumptions.':'급유 없는 출항은 출항 준비를 이미 포함합니다. 하역 종료에는 급유로 인한 중단을, 급유 준비 가능 시각에는 대기·접근 제한을 반영해야 합니다. 급유 준비 → 이송 → 마무리는 순차 작업이며, 출항 준비는 하역·급유가 모두 끝난 뒤에 시작합니다. 중복·병행 시간을 넣지 않는다는 미검증 합성 가정입니다.'}</p>
    </details>
    <p className="scenario-summary" role="status">{!review.candidates.length?(en?'Review unavailable: current record is ended, missing, stale or invalid.':'현재 기록 종료·누락·오래된 관측·입력 오류로 검토할 수 없습니다.'):en?`${review.horizon}-step horizon · ${review.eligibleCount}/${review.candidates.length} candidates pass modeled checks${review.tied?' · Adjusted SCI tied':''}`:`${review.horizon}단계 검토 · ${review.candidates.length}개 중 ${review.eligibleCount}개 가정 제약 충족${review.tied?' · 보정 SCI 동률':''}`}</p>
    {!!review.candidates.length&&<Table><TableHeader><TableRow>{(en?['Choice / checks','Fuel flow · before refill → ending','Departure / deadline (h)','Purchase SCI','Ending fuel','Comparable adjusted SCI']:['선택 / 판정','연료 흐름 · 급유 전 → 종료','출항 / 마감 (h)','구매 SCI','종료 잔량','비교 가능한 보정 SCI']).map(text=><TableHead key={text} scope="col">{text}</TableHead>)}</TableRow></TableHeader><TableBody>{review.candidates.map(candidate=><TableRow key={candidate.id}>
      <TableCell><strong>{candidate.actions.map(label).join(' → ')}</strong><span className={`scenario-status ${candidate.status}`}>{statusLabel[candidate.status]}</span>{candidate.reasons.map(reason=><span className="candidate-flag" key={reason}>{reasonLabels[reason][en?1:0]}</span>)}</TableCell>
      <TableCell><ol className="candidate-flow">{candidate.steps.map(step=><li key={step.decision}>{en?'Step':'단계'} {step.decision}: {format(step.fuelBeforeRefill*100)} → {format(step.fuelAfter*100)}<small>{en?'Refill':'구매'} +{format(step.amount*100)}</small></li>)}</ol>{candidate.steps.length<candidate.actions.length&&<span className="candidate-flag">{en?'Later action not executed or checked':'이후 선택 미실행·미검사'}</span>}</TableCell>
      <TableCell>{candidate.steps.map(step=><div className="scenario-time" key={step.decision}>{en?'Step':'단계'} {step.decision}: {format(step.departureHours)} / {format(step.deadlineHours)}<span className="candidate-flag">{step.onTime===null?(en?'UNKNOWN':'UNKNOWN · 판정 보류'):step.onTime?(en?'Within deadline':'마감 이내'):(en?'Late':'마감 초과')}</span>{[...step.timing.missing,...step.timing.invalid].map(field=><span className="candidate-flag" key={field}>{fieldLabels[field][en?1:0]}</span>)}</div>)}</TableCell>
      <TableCell>{format(candidate.purchaseSCI,2)}</TableCell><TableCell>{format(candidate.finalFuel*100)}</TableCell><TableCell>{format(candidate.comparableSCI,2)}{candidate.rank!==null&&<span className="candidate-flag">{en?`Eligible rank ${candidate.rank}`:`충족 후보 내 ${candidate.rank}위`}</span>}</TableCell>
    </TableRow>)}</TableBody></Table>}
    <p className="small-muted">{en?'Adjusted SCI = purchase SCI + (opening fuel − ending fuel) × current price × current FX, using normalized fuel. Both inventories use the same assumed value. Candidates passing this review horizon therefore tie at fixed prices; lower spending alone is not savings. Excluded or incomplete paths are never ranked. Economic superiority has not been demonstrated.':'보정 SCI = 구매 SCI + (시작 잔량 − 종료 잔량) × 현재 가격 × 현재 환율이며 정규화 연료량으로 계산합니다. 시작·종료 재고에 같은 가치를 적용하므로 이 검토 구간의 제약을 충족한 후보는 고정 가격에서 동률입니다. 적은 지출만으로 절감을 주장하지 않으며, 위반·누락 후보는 순위에서 제외합니다. 경제적 우위는 입증되지 않았습니다.'}</p>
    <p className="small-muted">{en?'Time edits stay in this panel while changing replay steps; returning after leaving the panel resets the example. Selection links do not include these edits. Save the review JSON to retain them.':'재생 단계를 바꿔도 이 패널의 시간 입력은 유지되며, 패널을 벗어났다가 돌아오면 예시가 초기화됩니다. 선택 링크에는 시간 편집값이 포함되지 않습니다. 보관하려면 검토 JSON을 저장하세요.'}</p>
    <details className="scenario-assumptions"><summary>{en?'Calculation rules and limits':'계산 규칙과 한계'}</summary><p className="small-muted">{en?'Legacy flow: consume 5, then request refill 90 with target 95; initial/tank capacity is 100. Actual purchase is clipped to available headroom. Every Buy incurs the full assumed work, even when clipped or zero. Pre-refill fuel must stay ≥15 (tolerance 10⁻⁹); a refill cannot undo an earlier shortage. Consumption stays at 5 per step regardless of elapsed time; work durations stay fixed regardless of purchase quantity.':'기존 흐름은 5 소비 후 90 급유 요청·목표 상한 95이며, 초기량·탱크 용량은 100입니다. 실제 구매량은 남은 공간까지만 채웁니다. 구매량이 줄거나 0이어도 구매 선택에는 전체 가정 작업시간을 적용합니다. 급유 전 잔량 15 이상(허용오차 10⁻⁹)을 검사하며 이후 급유로 앞선 부족을 해소했다고 보지 않습니다. 소비량은 경과시간과 무관하게 단계당 5이며, 작업시간은 구매량과 무관하게 고정입니다.'}</p><p className="small-muted">{en?'Departure = max(no-bunker departure, max(cargo end, bunker-ready + preparation + transfer + cleanup) + readiness). Wait uses no-bunker departure. Deadline checks include all prior extra delay. Port supply, grades, tides, pilot/berth allocation and downstream schedule feedback are not modeled.':'출항 = max(급유 없는 출항, max(하역 종료, 급유 준비 가능 + 준비 + 이송 + 마무리) + 출항 준비). 미구매는 급유 없는 출항을 사용합니다. 마감 판정에는 앞 단계의 추가 지연을 포함합니다. 항만 공급·연료 규격·조석·도선·선석 배정·후속 일정 조정은 미구현입니다.'}</p><a href={`https://github.com/heechan9/bunkering-ai/blob/${SOURCE_REVISION}/research/port_call_time/INTAKE.md`} target="_blank" rel="noreferrer">{en?'Timing input contract ↗':'시간 입력 기준 ↗'}</a>{' · '}<a href={`https://github.com/heechan9/bunkering-ai/blob/${SOURCE_REVISION}/docs/technical/safety_accounting.md`} target="_blank" rel="noreferrer">{en?'Safety and accounting definitions ↗':'안전·회계 기준 ↗'}</a></details>
    {exportStatus&&<p role="status">{exportStatus==='saved'?(en?'Review JSON download started with current inputs and full-precision results.':'현재 입력과 반올림 전 계산값을 담은 검토 JSON 다운로드를 시작했습니다.'):(en?'Download failed. Please try again.':'다운로드에 실패했습니다. 다시 시도해 주세요.')}</p>}
  </div>;
}
