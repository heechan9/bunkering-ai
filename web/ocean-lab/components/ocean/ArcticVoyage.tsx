'use client';

import {useEffect,useRef,useState,type Dispatch,type ReactNode,type SetStateAction} from 'react';
import {ArrowUpRight,Maximize,Minimize,Pause,Play,RotateCcw,Ship} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useLocale} from '@/lib/locale';
import {ARCTIC_PRESETS,COMMON_FIELDS,arcticPreset,parseArctic,reviewArctic,type ArcticCandidate,type ArcticForm,type ArcticPreset,type ArcticReason,type CommonField,type Supply} from '@/lib/arctic-scenario';
import {MapLabelKey,MapScene} from './Geography';
import styles from './ArcticVoyage.module.css';
import ArcticObservations from './ArcticObservations';

export type ArcticActions=[boolean,boolean];
export type ArcticVoyageProps={
  form:ArcticForm;
  onFormChange:Dispatch<SetStateAction<ArcticForm>>;
  onCompare:()=>void;
  actions?:ArcticActions;
  onActionsChange?:Dispatch<SetStateAction<ArcticActions>>;
};

type VoyageFrame={position:number;fuel:number|null;hours:number|null;leg:number;phase:'decision'|'work'|'travel'|'arrived'|'blocked';bunkering:boolean};
const format=(value:number|null,digits=1)=>value===null?'UNKNOWN':value.toLocaleString('en-US',{maximumFractionDigits:digits});
const clamp=(value:number,min=0,max=1)=>Math.min(max,Math.max(min,value));
const presetLabels:Record<ArcticPreset,[string,string]>={normal:['정상','Normal'],'delay-fuel':['지연 + 소비 증가','Delay + fuel'],'supply-unavailable':['중간 급유 불가','Supply unavailable']};
const commonLabels:Record<CommonField,[string,string]>={
  initialFuel:['시작 연료 (100점 탱크)','Starting fuel (100-point tank)'],price:['고정 합성 가격 지수','Fixed synthetic price index'],fx:['고정 합성 환율 지수','Fixed synthetic FX index'],
  baseConsumption:['기본 구간 소비량 (연료점)','Base consumption per leg (fuel points)'],travelHours:['구간별 기본 이동 (h)','Base travel per leg (h)'],
  bunkerWorkHours:['구매 선택별 작업 (h)','Work per Buy (h)'],arrivalDeadlineHours:['최종 도착 마감 (h)','Final arrival deadline (h)'],
};
const reasonLabels:Record<ArcticReason,[string,string]>={missing_input:['입력이 없어 계산을 보류합니다.','Missing input; calculation is on hold.'],invalid_input:['잘못된 입력을 확인하세요.','Check the invalid inputs.'],unknown_supply:['구매 지점의 공급 여부가 UNKNOWN입니다.','Supply is UNKNOWN at the selected Buy.'],unavailable_supply:['급유 불가 지점에서 구매를 선택했습니다.','Buy selected where supply is unavailable.'],fuel_shortage:['연료 소진 지점에서 이동이 중단됩니다.','Movement stops at the fuel-exhaustion point.'],reserve_breach:['다음 급유 전 도착 여유가 15 미만입니다.','Arrival reserve is below 15 before the next refill.'],arrival_deadline:['최종 도착 마감을 넘습니다.','Final arrival deadline is exceeded.'],arithmetic:['계산 범위를 초과하여 진행을 보류합니다.','Calculation exceeds the supported range.']};

/** Display interpolation only. All purchase, fuel and time endpoints come from reviewArctic. */
export function arcticPlaybackLimit(candidate:ArcticCandidate):number {
  if(candidate.status==='invalid'||candidate.steps.length===0)return 0;
  let limit=0;
  for(const step of candidate.steps){
    const start=(step.leg-1)/2;
    if(step.departureFuel===null||step.consumption===null||step.arrivalFuel===null||step.arrivalHours===null)return start;
    if(step.arrivalFuel<0){
      // Do not animate an exhausted ship to the leg endpoint or to a later refill.
      return Math.min(step.leg/2-Number.EPSILON,start+.1+.4*clamp(step.consumption>0?step.departureFuel/step.consumption:0));
    }
    limit=step.leg/2;
  }
  return limit;
}

export function arcticVoyageFrame(candidate:ArcticCandidate,cursor:number):VoyageFrame {
  const limit=arcticPlaybackLimit(candidate),progress=clamp(cursor,0,limit);
  const empty:VoyageFrame={position:0,fuel:null,hours:null,leg:1,phase:'blocked',bunkering:false};
  if(candidate.status==='invalid'||!candidate.steps.length)return empty;
  if(progress===1){
    return {position:1,fuel:candidate.finalFuel,hours:candidate.arrivalHours,leg:2,phase:'arrived',bunkering:false};
  }
  const legIndex=progress>=.5?1:0,step=candidate.steps[legIndex];
  if(!step){
    const prior=candidate.steps.at(-1)!;
    return {...empty,position:legIndex/2,fuel:prior.arrivalFuel===null?null:Math.max(0,prior.arrivalFuel),hours:prior.arrivalHours,leg:legIndex+1};
  }
  const start=legIndex/2,local=progress-start;
  const previousArrival=legIndex===0?0:candidate.steps[legIndex-1].arrivalHours;
  if(step.departureFuel===null||step.departureHours===null||step.workHours===null||step.arrivalFuel===null||step.arrivalHours===null||step.consumption===null){
    return {...empty,position:start,fuel:step.openingFuel,hours:previousArrival,leg:step.leg};
  }
  if(local<.1-8*Number.EPSILON&&!(progress>=limit&&limit<1)){
    return {position:start,fuel:step.openingFuel,hours:(previousArrival??0)+step.workHours*clamp(local/.1),leg:step.leg,
      phase:step.buy?'work':'decision',bunkering:step.buy&&step.supply==='available'&&progress>0};
  }
  const stopped=progress>=limit&&limit<1;
  const exhausted=stopped&&step.arrivalFuel<0;
  const fraction=exhausted?clamp(step.consumption>0?step.departureFuel/step.consumption:0):clamp((local-.1)/.4);
  return {position:start+fraction/2,fuel:exhausted?0:Math.max(0,step.departureFuel-step.consumption*fraction),
    hours:step.departureHours+(step.arrivalHours-step.departureHours)*fraction,leg:step.leg,phase:stopped?'blocked':'travel',bunkering:false};
}

function ArcticPlayback({candidate,form,onCompare,controls}:{candidate:ArcticCandidate;form:ArcticForm;onCompare:()=>void;controls:ReactNode}){
  const {lang}=useLocale(),en=lang==='en';
  const [cursor,setCursor]=useState(0),[playing,setPlaying]=useState(false),[cameraReset,setCameraReset]=useState(0);
  const mapColumnRef=useRef<HTMLDivElement>(null);
  const [fullscreen,setFullscreen]=useState(false),[fullscreenFailed,setFullscreenFailed]=useState(false);
  useEffect(()=>{
    const syncFullscreen=()=>setFullscreen(document.fullscreenElement===mapColumnRef.current);
    document.addEventListener('fullscreenchange',syncFullscreen);
    return()=>document.removeEventListener('fullscreenchange',syncFullscreen);
  },[]);
  async function toggleFullscreen(){
    setFullscreenFailed(false);
    try{
      if(document.fullscreenElement===mapColumnRef.current)await document.exitFullscreen();
      else if(mapColumnRef.current?.requestFullscreen)await mapColumnRef.current.requestFullscreen();
      else setFullscreenFailed(true);
    }catch{setFullscreenFailed(true);}
  }
  const limit=arcticPlaybackLimit(candidate),frame=arcticVoyageFrame(candidate,cursor),ended=cursor>=limit;
  const destinationReachable=limit===1;
  const active=playing&&!ended;
  useEffect(()=>{
    if(!active)return;
    let raf=0,last=0;
    const advance=(now:number)=>{
      if(last&&!document.hidden)setCursor(previous=>Math.min(limit,previous+Math.min(now-last,100)/24000));
      last=now;raf=requestAnimationFrame(advance);
    };
    raf=requestAnimationFrame(advance);return()=>cancelAnimationFrame(raf);
  },[active,limit]);
  const stop=frame.leg===1?'A':'B';
  const phaseLabel=frame.phase==='arrived'?(en?'Destination reached':'설명용 목적지 도착'):frame.phase==='blocked'?(en?'Progress on hold':'진행 보류'):frame.phase==='work'?(en?`Buy at ${stop} · work time`:`${stop} 구매 · 작업 시간`):frame.phase==='decision'?(en?`Wait at ${stop} · no purchase`:`${stop} 미구매 · 구매 없음`):(en?`Leg ${frame.leg} · sailing illustration`:`${frame.leg}구간 · 이동 설명`);
  const statusLabel={feasible:en?'Passes synthetic checks':'합성 제약 충족',infeasible:en?'Excluded by synthetic checks':'합성 제약 위반 · 제외',incomplete:en?'Incomplete assumptions':'입력 부족 · 보류',invalid:en?'Invalid assumptions':'입력 오류 · 보류'}[candidate.status];
  const playLabel=active?(en?'Pause':'일시정지'):ended&&limit>0?(en?'Replay voyage':'다시 체험'):(en?'Play voyage':'운항 체험 시작');
  return <div className={`workspace ${styles.workspace}`}>
    <div className={styles.mapColumn} ref={mapColumnRef}>
      <header className={styles.mapHeading}>
        <div className={styles.mapCaption}><span>{en?'ARCTIC ROUTE · SYNTHETIC VOYAGE':'북극 항로 · 합성 운항 체험'}</span><h2>{en?'A ship along the selected route':'선택한 항로를 지나는 배'}</h2><p>A → B → {en?'Destination · two illustrative legs':'도착 · 설명용 두 구간'}</p></div>
        <div className={`scene-tools ${styles.mapTools}`}>
          <Button size="icon" variant="outline" aria-label={en?'Reset Arctic map camera':'북극 지도 시점 초기화'} title={en?'Reset camera':'시점 초기화'} onClick={()=>setCameraReset(previous=>previous+1)}><RotateCcw size={17}/></Button>
          <Button size="icon" variant="outline" aria-label={fullscreen?(en?'Exit fullscreen':'전체 화면 닫기'):(en?'Fullscreen Arctic map':'북극 지도 전체 화면')} title={fullscreen?(en?'Exit fullscreen':'전체 화면 닫기'):(en?'Fullscreen':'전체 화면')} onClick={toggleFullscreen}>{fullscreen?<Minimize size={17}/>:<Maximize size={17}/>}</Button>
        </div>
      </header>
      <div className={styles.voyageState}><Ship size={15}/><strong>{phaseLabel}</strong><span>{format(frame.hours)} h</span></div>
      {fullscreenFailed&&<p className={styles.small} role="status">{en?'Fullscreen is unavailable in this browser. You can keep using the map here.':'이 브라우저에서는 전체 화면을 열 수 없습니다. 현재 화면에서 지도를 계속 사용할 수 있습니다.'}</p>}
      <div className={styles.map}>
        <MapScene region="arctic" reset={cameraReset} exaggeration={1} trafficProgress={frame.position} selectedShip={0} singleShip bunkering={frame.bunkering} replayLabel={`${phaseLabel} · ${en?'Fuel':'연료'} ${format(frame.fuel===null?null:frame.fuel*100)}`}/>
      </div>
      <div className={styles.playback}>
        <Button className={styles.playButton} size="icon" disabled={limit===0} aria-label={playLabel} title={playLabel} onClick={()=>{if(ended)setCursor(0);setPlaying(!active)}}>{active?<Pause size={17}/>:<Play size={17}/>}</Button>
        <div className={styles.timelineTrack}>
          <div className={styles.playbackTop}><label htmlFor="arctic-voyage-progress">{en?'Voyage progress · synthetic illustration':'운항 진행 · 합성 이동 설명'}</label><span>{Math.round(cursor*100)}%</span></div>
          <input id="arctic-voyage-progress" className={styles.slider} type="range" min="0" max="1000" step="1" value={Math.round(cursor*1000)} disabled={limit===0} onChange={event=>{setPlaying(false);setCursor(Math.min(limit,Number(event.target.value)/1000))}} aria-valuetext={`${phaseLabel}, ${format(frame.hours)} h`}/>
          <div className={styles.stops} aria-hidden="true"><span>A</span><span>B</span><span>{en?'Destination':'도착'}</span></div>
        </div>
        <Button className={styles.resetPosition} size="icon" variant="ghost" aria-label={en?'Reset position':'이동 초기화'} title={en?'Reset position':'이동 초기화'} onClick={()=>{setCursor(0);setPlaying(false)}}><RotateCcw size={17}/></Button>
      </div>
      <div className={styles.mapNotes}>
        <MapLabelKey region="arctic"/>
        <details className={styles.disclosure}><summary>{en?'Synthetic voyage · assumptions and limits':'합성 운항 · 가정과 한계'}</summary>
          <p>{en?'Illustration only: the authored map line and abstract A/B stops are not validated navigation or real bunkering ports. All delay, consumption and supply assumptions are synthetic. No ice measurements, ship-class or icebreaker capability, safety, Polar Code compliance, savings or DQN performance is established.':'설명용 체험입니다. 직접 구성한 지도 선과 추상 A/B 지점은 검증된 항로·실제 급유항이 아닙니다. 지연·소비·공급은 모두 합성 가정이며, 빙해 실측·선급·쇄빙능력·안전·Polar Code 준수·절감·DQN 성능을 입증하지 않습니다.'}</p>
          <p>{en?'Work holds the ship at A or B. Travel uses interpolated calculation endpoints; map distance does not determine fuel or hours. Playback resets when assumptions or choices change.':'작업 중 선박은 A 또는 B에 머뭅니다. 이동 중 수치는 계산된 구간 양 끝값 사이의 설명용 보간이며, 지도 거리가 연료·시간을 결정하지 않습니다. 가정·선택을 바꾸면 이동이 초기화됩니다.'}</p>
          <p>{en?'Status checks cover the entire candidate, including later legs. Stopped paths have no completed arrival; a completed illustration can still be excluded.':'상태 검사는 이후 구간을 포함한 전체 후보에 적용됩니다. 중단된 경로의 최종 도착은 미정이며, 설명용 이동을 마쳐도 제약 위반으로 제외될 수 있습니다.'}</p>
        </details>
      </div>
      <p className={styles.mapFootnote}>{en?'Synthetic fuel and time illustration · not validated for navigation':'합성 연료·시간 이동 설명 · 실제 항해용으로 검증되지 않음'}</p>
    </div>
    <aside className={`panel ${styles.readings}`} aria-label={en?'Selected Arctic voyage results':'선택한 북극 운항 결과'}>
      <div className={styles.panelTitle}><span>{en?'VOYAGE CONDITIONS':'운항 조건 선택'}</span><span>{en?'Arctic route':'북극 항로'}</span></div>
      {controls}
      <div className={styles.selectedChoice}><span>{en?'Selected choices':'선택한 구매 조합'}</span><strong>{candidate.actions.map((buy,i)=>`${i===0?'A':'B'}: ${buy?(en?'Buy':'구매'):(en?'Wait':'미구매')}`).join(' → ')}</strong></div>
      <p className={styles.status} data-status={candidate.status} role="status">{statusLabel}</p>
      <dl className={styles.liveMetrics} aria-label={en?'Current illustration readings':'현재 설명 위치 수치'}>
        <div><dt>{en?'Current fuel · points':'현재 연료 · 점'}</dt><dd data-arctic-fuel data-unknown={frame.fuel===null}>{format(frame.fuel===null?null:frame.fuel*100)}<small>/ 100</small></dd></div>
        <div><dt>{en?'Elapsed synthetic time':'합성 경과 시간'}</dt><dd data-arctic-hours data-unknown={frame.hours===null}>{format(frame.hours)}<small>h</small></dd></div>
      </dl>
      <div className={styles.fuelTrack} aria-hidden="true"><span style={{width:`${clamp(frame.fuel??0)*100}%`}}/></div>
      <p className={styles.reserve}>{en?'Minimum arrival reserve: 15 points, before any later refill.':'다음 급유 전 도착 최소 여유: 15점.'}</p>
      <dl className={styles.resultMetrics}>
        <div><dt>{en?'Calculated final arrival':'계산된 최종 도착'}</dt><dd>{format(destinationReachable?candidate.arrivalHours:null)} h</dd></div>
        <div><dt>{en?'Arrival deadline':'도착 마감'}</dt><dd>{form.common.arrivalDeadlineHours||'UNKNOWN'} h</dd></div>
        <div><dt>{en?'Calculated ending fuel':'계산된 종료 연료'}</dt><dd>{format(!destinationReachable||candidate.finalFuel===null?null:candidate.finalFuel*100)}</dd></div>
        <div><dt>{en?'Purchase SCI · not currency':'구매 SCI · 실제 통화 아님'}</dt><dd>{format(candidate.purchaseSCI,0)}</dd></div>
      </dl>
      {candidate.reasons.length>0&&<ul className={styles.reasons}>{candidate.reasons.map(reason=><li key={reason}>{reasonLabels[reason][en?1:0]}</li>)}</ul>}
      <Button variant="outline" onClick={onCompare}>{en?'Compare all four choices':'네 가지 선택 비교'}<ArrowUpRight size={16}/></Button>
    </aside>
  </div>;
}

export default function ArcticVoyage({form,onFormChange,onCompare,actions:controlledActions,onActionsChange}:ArcticVoyageProps){
  const {lang}=useLocale(),en=lang==='en';
  const [localActions,setLocalActions]=useState<ArcticActions>([true,false]);
  const actions=controlledActions??localActions,setActions=onActionsChange??setLocalActions;
  const input=parseArctic(form),review=reviewArctic(input),candidate=review.candidates.find(item=>item.actions.every((buy,i)=>buy===actions[i]))!;
  return <section className={styles.root} aria-labelledby="arctic-voyage-title" data-arctic-voyage data-arctic-candidate={candidate.id}>
    <header className={`workspace-intro ${styles.heading}`}><div><span className={styles.eyebrow}>{en?'SELECTED REGION · ARCTIC ROUTE':'선택한 지역 · 북극 항로'}</span><h1 id="arctic-voyage-title">{en?'Follow the ship’s movement, fuel and time.':'선택한 항로에서 배의 이동과 연료·시간을 따라갑니다.'}</h1><p>{en?'Choose Buy or Wait at A and B. Synthetic illustration; not validated for navigation.':'A와 B의 구매·미구매를 선택하세요. 합성 설명용 체험이며, 실제 항해용으로 검증되지 않았습니다.'}</p></div><Button variant="outline" onClick={onCompare}>{en?'Compare choices':'연료 구매 비교'}<ArrowUpRight size={16}/></Button></header>
    <ArcticPlayback key={JSON.stringify(form)+candidate.id} candidate={candidate} form={form} onCompare={onCompare} controls={<div className={styles.controls}>
      <div className={styles.presetGroup}><span>{en?'Scenario preset':'시나리오 예시'}</span><div>{ARCTIC_PRESETS.map(preset=><Button key={preset} variant="outline" aria-pressed={form.preset===preset} onClick={()=>onFormChange(previous=>arcticPreset(preset,previous.common))}>{presetLabels[preset][en?1:0]}</Button>)}</div></div>
      <div className={styles.choices}>{actions.map((buy,i)=><fieldset key={i}><legend>{i===0?(en?'A · before leg 1':'A · 1구간 출발 전'):(en?'B · before leg 2':'B · 2구간 출발 전')}</legend><div>{[true,false].map(value=><Button key={String(value)} variant="outline" aria-pressed={buy===value} onClick={()=>setActions(previous=>previous.map((item,j)=>j===i?value:item) as ArcticActions)}>{value?(en?'Buy':'구매'):(en?'Wait':'미구매')}</Button>)}</div></fieldset>)}</div>
    </div>}/>
    <ArcticObservations/>
    <details className={styles.inputs}>
      <summary>{en?'Edit the shared voyage assumptions':'운항·비교 공통 가정 편집'}</summary>
      <p>{en?'Edits persist between voyage and comparison tabs in this session. Presets change only leg assumptions; common inputs stay. Reload and share links do not preserve these edits. Export JSON from the comparison tab to keep them.':'이번 세션의 운항·비교 탭 사이에 편집값이 유지됩니다. 예시는 구간 가정만 바꾸고 공통 입력은 유지합니다. 새로고침·공유 링크에는 편집값이 보존되지 않으므로 비교 탭의 JSON 저장으로 보관하세요.'}</p>
      <div className={styles.fields}>{COMMON_FIELDS.map(field=><label key={field} htmlFor={`voyage-arctic-${field}`}><span>{commonLabels[field][en?1:0]}</span><input id={`voyage-arctic-${field}`} type="number" min="0" max={field==='initialFuel'?100:undefined} step="any" placeholder="UNKNOWN" inputMode="decimal" value={form.common[field]} onChange={event=>onFormChange(previous=>({...previous,common:{...previous.common,[field]:event.target.value}}))}/></label>)}</div>
      <div className={styles.legInputs}>{form.legs.map((leg,i)=><fieldset key={i}><legend>{i===0?(en?'Leg 1 · A → B':'1구간 · A → B'):(en?'Leg 2 · B → destination':'2구간 · B → 도착')}</legend><div className={styles.fields}>
        {(['consumptionMultiplier','delayHours'] as const).map(field=><label key={field} htmlFor={`voyage-arctic-leg-${i}-${field}`}><span>{field==='consumptionMultiplier'?(en?'Consumption multiplier (×)':'소비 배수 (×)'):(en?'Extra travel delay (h)':'추가 이동 지연 (h)')}</span><input id={`voyage-arctic-leg-${i}-${field}`} type="number" min="0" step="any" inputMode="decimal" placeholder="UNKNOWN" value={leg[field]} onChange={event=>onFormChange(previous=>({...previous,legs:previous.legs.map((item,j)=>i===j?{...item,[field]:event.target.value}:item) as ArcticForm['legs']}))}/></label>)}
        <label htmlFor={`voyage-arctic-leg-${i}-supply`}><span>{en?`Supply at ${i===0?'A':'B'}`:`${i===0?'A':'B'} 급유 가능 여부`}</span><select id={`voyage-arctic-leg-${i}-supply`} value={leg.supply} onChange={event=>onFormChange(previous=>({...previous,legs:previous.legs.map((item,j)=>i===j?{...item,supply:event.target.value as Supply}:item) as ArcticForm['legs']}))}><option value="available">{en?'Available (assumed)':'가능 (가정)'}</option><option value="unavailable">{en?'Unavailable (assumed)':'불가 (가정)'}</option><option value="unknown">UNKNOWN</option></select></label>
      </div></fieldset>)}</div>
      <div className={styles.inputFooter}><p>{en?'Blank = UNKNOWN. Consumption = base fuel × leg multiplier. Delay adds time only, with no separate idle fuel burn. Reset restores every default.':'빈칸은 UNKNOWN입니다. 소비량 = 기본 연료 × 구간 배수이며, 지연은 시간만 늘리고 별도 대기 연료를 소모하지 않습니다. 전체 초기화는 모든 기본값을 복원합니다.'}</p><Button variant="outline" onClick={()=>onFormChange(arcticPreset('normal'))}>{en?'Reset all assumptions':'전체 가정 초기화'}</Button></div>
    </details>
  </section>;
}
