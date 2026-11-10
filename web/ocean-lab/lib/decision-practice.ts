import {checkU01} from './u01-procurement';
export type Lang='ko'|'en';
export type Text={ko:string;en:string};
export const text=(ko:string,en:string):Text=>({ko,en});
export const source='https://github.com/heechan9/bunkering-ai/blob/18f340e4e849fe9fe99ee4472a793f34119c5028/web/ocean-lab/lib/u01-procurement.ts';
export const concepts=[
 {id:'unit',prerequisites:[],label:text('단가 × 구매량','Unit price × quantity'),explanation:text('USD/t에 t를 곱하면 구매지출 USD입니다.','USD/t multiplied by t gives purchase outlay in USD.'),misconception:'unit-is-total'},
 {id:'cost',prerequisites:['unit'],label:text('총비용의 범위','Cost boundary'),explanation:text('여러 항구의 지출을 합칩니다. 별도 비용이 있다면 포함 여부와 출처를 먼저 정합니다.','Sum outlays across ports. Declare any additional costs and their source before comparing.'),misconception:'cheapest-unit-is-cheapest-plan'},
 {id:'balance',prerequisites:[],label:text('연료 수지','Fuel balance'),explanation:text('U01은 구매 후 소비합니다. 다음 도착 잔량 = 현재 잔량 + 구매 − 구간 소모입니다.','U01 purchases THEN consumes. Next arrival = current inventory + purchase − leg consumption.'),misconception:'purchase-without-balance'},
 {id:'reserve',prerequisites:['balance'],label:text('급유 전 도착 제약','Arrival constraint before refueling'),explanation:text('B 도착 때 10t 미만이면 실패입니다. B에서 사더라도 이전 위반은 사라지지 않습니다.','Arrival at B below 10 t fails. Buying at B cannot erase the earlier violation.'),misconception:'later-refueling-repairs-arrival'},
 {id:'uncertainty',prerequisites:['unit'],label:text('가정과 미래 보장','Assumptions and future guarantees'),explanation:text('U01은 가격을 고정해 아는 예제입니다. 미래 가격을 모르는 경우에는 가격 분기와 판단 기준을 별도로 밝혀야 합니다.','U01 assumes fixed known prices. Unknown future prices require explicit branches and a decision criterion.'),misconception:'forecast-is-guarantee'},
] as const;
export const diagnostics=[
 {concept:'cost',question:text('B의 단가가 더 낮으면 모든 구매안의 총비용도 반드시 낮나요?','Does a lower B unit price guarantee a lower total plan cost?'),options:[text('항상 그렇다','Always'),text('구매량과 포함 비용을 함께 봐야 한다','Check quantities and included costs'),text('단가는 비용과 무관하다','Unit price is irrelevant')],correct:1},
 {concept:'reserve',question:text('B 도착 9t, 급유 후 50t라면 도착 안전잔량 10t를 충족하나요?','Arrival at B is 9 t, then 50 t after refueling. Is the 10 t arrival reserve satisfied?'),options:[text('아니요, 도착 시점에 이미 위반','No, arrival already violated it'),text('급유했으니 충족','Yes, refueling repairs it'),text('총비용에 따라 다름','Depends on total cost')],correct:0},
 {concept:'uncertainty',question:text('내일 가격이 낮아질 것이라는 예측은 무엇인가요?','What is a prediction that tomorrow’s price will fall?'),options:[text('미래 가격 보장','A future price guarantee'),text('실운항 급유 명령','An operational instruction'),text('확인되지 않은 가정','An unconfirmed assumption')],correct:2},
] as const;
export const plans=[{id:'split',quantities:['20','40'],label:text('A에서 20t 구매 → B까지 대기 → B에서 40t','Buy 20 t at A → wait until B → buy 40 t')},{id:'early',quantities:['60','0'],label:text('A에서 60t 구매 → B에서는 대기','Buy 60 t at A → no purchase at B')},{id:'unsafe',quantities:['19','41'],label:text('A에서 19t → B에서 41t','Buy 19 t at A → 41 t at B')}] as const;
export type Plan=typeof plans[number]['id'];
export const reasons=[{id:'cost',label:text('모든 포함 비용을 합산','Sum all included costs')},{id:'reserve',label:text('급유 전 제약 충족을 먼저 확인','Check pre-refueling constraints first')},{id:'worst',label:text('지정된 두 분기의 최대 지출을 최소화','Minimize the maximum outlay across the two stated branches')},{id:'unit',label:text('단가가 더 낮아서','Because its unit price is lower')},{id:'guarantee',label:text('예측이 맞을 것이 보장돼서','Because the forecast is guaranteed')}];
export const scenarios=[
 {id:'fees',concept:'cost',title:text('1. 어느 항구에서 살까?','1. Which port?'),prompt:text('U01에 교육용 가정 추가: B에서 구매하면 고정 작업비 $10,000. 유효한 두 구매안 중 총비용이 낮은 쪽을 고르세요.','Education-only addition to U01: a $10,000 fixed service fee if buying at B. Choose the lower total cost among the two valid plans.'),transfer:text('조건 변경: B 작업비가 $0이면 구매안이 달라지나요?','Transfer: if the B fee becomes $0, does your choice change?'),hint:[text('단가와 구매량을 먼저 곱해보세요.','Multiply each unit price by its purchase quantity.'),text('20×600 + 40×400에 B 작업비를 더하고, 60×600과 비교하세요.','Add the B fee to 20×600 + 40×400, then compare with 60×600.')],explanation:text('기존 계산기 지출은 분할 $28,000, A 집중 $36,000입니다. 교육용 B 비용을 더하면 $38,000 대 $36,000으로 A 집중이 낮습니다.','The existing calculator gives split $28,000 versus early $36,000. Adding the educational B fee gives $38,000 versus $36,000: early is lower.'),best:'early',reason:'cost',transferBest:'split',transferReason:'cost'},
 {id:'safety',concept:'reserve',title:text('2. 싸 보이는 구매안은 유효할까?','2. Is the apparently cheaper plan valid?'),prompt:text('U01 원래 조건, 추가 비용 없음. 유효한 구매안 중 지출이 가장 낮은 것을 고르세요. 도착 제약과 최종 잔량을 먼저 확인하세요.','Original U01, no added fees. Choose the lowest-outlay valid plan. Check arrival constraints and terminal inventory first.'),transfer:text('교육용 조건 변경: B에서 공급 중단. B 구매가 필요한 안을 제외하면 무엇을 선택하나요?','Education-only transfer: B supply is unavailable. Exclude plans needing purchases at B. What do you choose?'),hint:[text('최종 10t만 보면 충분할까요?','Is checking only the final 10 t enough?'),text('19t를 사면 B 도착은 20+19−30=9t입니다.','Buying 19 t gives arrival at B of 20+19−30=9 t.')],explanation:text('19/41은 원지출 $27,800·최종 10t여도 B 도착 9t로 실패해 비교비용이 null입니다. 원래 조건에서는 20/40이 유효하고 $28,000입니다. B 공급 중단은 별도 교육용 조건입니다.','19/41 has raw outlay $27,800 and final 10 t, but fails with 9 t at B; comparable cost is null. Under original conditions, 20/40 is valid at $28,000. B supply loss is a separate educational condition.'),best:'split',reason:'reserve',transferBest:'early',transferReason:'reserve'},
 {id:'future',concept:'uncertainty',title:text('3. 미래 가격이 다르면?','3. What if the future price differs?'),prompt:text('교육용 두 분기: B 단가 $350/t 또는 $800/t, 확률 미제공. 추가 비용 없음. “두 분기 중 최대 지출을 최소화”라는 기준으로 유효한 안을 고르세요. 예측·최적해 보장이 아닙니다.','Educational branches: B price $350/t or $800/t, with no probabilities. No extra fees. Among valid plans, minimize the maximum outlay across the two branches. This is not a forecast or an optimality guarantee.'),transfer:text('상한 분기만 $500/t로 낮아집니다. 같은 최대지출 기준에서 판단이 달라지나요?','Transfer: reduce only the upper branch to $500/t. Does your choice change under the same maximum-outlay criterion?'),hint:[text('한 가격만 맞을 것이라고 가정하지 마세요.','Do not assume only one price can occur.'),text('분할 지출은 $26,000/$44,000, A 집중은 두 분기 모두 $36,000입니다.','Split outlays are $26,000/$44,000; early is $36,000 in both branches.')],explanation:text('최대 지출은 분할 $44,000, A 집중 $36,000이므로 주어진 기준에서는 A 집중입니다. 실제 미래 분포나 시장 예측은 검증하지 않았고, 다른 판단 기준에서는 결론이 달라질 수 있습니다.','Maximum outlay is $44,000 for split and $36,000 for early, so this criterion selects early. No real future distribution or market forecast was validated; another criterion may lead to another choice.'),best:'early',reason:'worst',transferBest:'split',transferReason:'worst'},
] as const;
export function compareScenario(id:string,transfer=false){
 if(!scenarios.some(s=>s.id===id))throw new Error('Unknown synthetic scenario');
 return plans.map(plan=>{
  const ledger=checkU01(plan.quantities);
  const extra=id==='fees'&&!transfer&&Number(plan.quantities[1])>0?10000:0;
  const available=!(id==='safety'&&transfer&&Number(plan.quantities[1])>0);
  const branchPrices=id==='future'?[350,transfer?500:800]:[400];
  const branches=branchPrices.map(price=>({bPrice:price,purchases:ledger.rows.reduce((sum,row,i)=>sum+row.purchase*(i===0?600:price),0)}));
  return {plan:plan.id,ledger,extra,available,branches,total:ledger.feasible&&available?Math.max(...branches.map(b=>b.purchases))+extra:null};
 });
}
export type RecordState='prediction_only'|'revealed'|'checked_changed_condition';
export type LearningRecord={scenario:string;concept:string;prerequisites:string[];evidence:string;misconception:string;source:string;status:RecordState;choice:Plan|null;reason:string|null;transferChoice:Plan|null;transferReason:string|null};
export type Progress={version:1;lang:Lang;diagnosis:(number|null)[];records:LearningRecord[]};
export const storageKey='bunker-decision-practice-v1';
export function freshProgress():Progress{return {version:1,lang:'ko',diagnosis:[null,null,null],records:[]};}
export function recordFor(id:string,status:RecordState,choice:Plan|null,reason:string|null,transferChoice:Plan|null=null,transferReason:string|null=null):LearningRecord{
 const s=scenarios.find(s=>s.id===id);if(!s)throw new Error('Unknown scenario');
 const c=concepts.find(c=>c.id===s.concept)!;
 return {scenario:id,concept:c.id,prerequisites:[...c.prerequisites],evidence:`${id}:U01-ledger+explicit-educational-assumptions-v1`,misconception:c.misconception,source,status,choice,reason,transferChoice,transferReason};
}
// Accept only a bounded allowlist, and reconstruct descriptive fields locally.
export function parseProgress(raw:string|null):Progress|null{
 try{
  if(!raw||raw.length>12000)return null;
  const v=JSON.parse(raw);if(v.version!==1||!['ko','en'].includes(v.lang)||!Array.isArray(v.diagnosis)||v.diagnosis.length!==3||v.diagnosis.some((n:unknown)=>n!==null&&(!Number.isInteger(n)||Number(n)<0||Number(n)>2))||!Array.isArray(v.records)||v.records.length>3)return null;
  const ids=new Set();const records:LearningRecord[]=[];
  for(const r of v.records){
   if(!r||typeof r!=='object'||!scenarios.some(s=>s.id===r.scenario)||ids.has(r.scenario)||!['prediction_only','revealed','checked_changed_condition'].includes(r.status))return null;
   for(const c of [r.choice,r.transferChoice])if(c!==null&&!plans.some(p=>p.id===c))return null;
   for(const reason of [r.reason,r.transferReason])if(reason!==null&&!reasons.some(p=>p.id===reason))return null;
   if(r.status==='checked_changed_condition'&&(!r.transferChoice||!r.transferReason))return null;
   ids.add(r.scenario);records.push(recordFor(r.scenario,r.status,r.choice,r.reason,r.transferChoice,r.transferReason));
  }
  return {version:1,lang:v.lang,diagnosis:v.diagnosis,records};
 }catch{return null;}
}
export function neededConcepts(answers:(number|null)[]){
 const ids=new Set<string>();
 function add(id:string){const c=concepts.find(c=>c.id===id)!;for(const p of c.prerequisites)add(p);ids.add(id);}
 diagnostics.forEach((d,i)=>{if(answers[i]!==d.correct)add(d.concept);});
 return concepts.filter(c=>ids.has(c.id));
}
