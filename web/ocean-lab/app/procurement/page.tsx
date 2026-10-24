'use client';
import {useState} from 'react';
import Link from 'next/link';
import {LocaleProvider,useLocale} from '@/lib/locale';
import {checkU01,defaultQuantities,isU01Quantity,u01,u01Step} from '@/lib/u01-procurement';
import './procurement.css';

const fmt=(n:number)=>n.toLocaleString('en-US',{maximumFractionDigits:3});
const root=`https://github.com/heechan9/bunkering-ai/blob/${u01.source_commit}`;

function ProcurementExample(){
 const {lang,setLang}=useLocale(),en=lang==='en';
 const [values,setValues]=useState<string[]>([...defaultQuantities]);
 const [step,setStep]=useState(0);
 const result=checkU01(values),current=u01Step(result,step);
 const methodNames:Record<string,string>={lp:en?'LP optimum':'LP 최적화 기준선',minimum_required:en?'Minimum required':'최소 필요량 규칙',next_cheaper:en?'Next cheaper':'다음 저가항 규칙',departure_concentrated:en?'Departure concentrated':'출항 집중 구매 규칙'};
 const steps=en?['Start at A','Buy at A → arrive B','Buy at B → arrive C']:['A항 출발 전','A에서 구매 → B 도착','B에서 구매 → C 도착'];
 const inputError=en?'Enter two quantities from 0 to 100 t, with up to 3 decimal places. Blank, negative and non-finite values are invalid.':'두 구매량을 0~100t, 소수 셋째 자리까지 입력하세요. 빈칸·음수·비유한 값은 허용하지 않습니다.';
 const reset=()=>{setValues([...defaultQuantities]);setStep(0)};
 return <main className="u01-page">
  <header className="u01-header"><Link href="/">← {en?'Ocean Lab replay':'Ocean Lab 기록 재생'}</Link><div className="language-switch" role="group" aria-label="Language / 언어"><button type="button" aria-pressed={!en} onClick={()=>setLang('ko')}>한국어</button><button type="button" aria-pressed={en} onClick={()=>setLang('en')}>English</button></div></header>
  <p className="u01-kicker">U01 · t / USD · STATIC_KNOWN</p>
  <h1>{en?'Three ports. One fuel balance.':'항구 세 곳, 하나의 연료 수지'}</h1>
  <p className="u01-boundary">{en?'Illustrative synthetic example. Purchase THEN consume. Separate from normalized fuel/SCI, recorded replay and PR141’s 400-row safety accounting. This is not an RL improvement or real-vessel cost-saving result.':'설명용 합성 예제입니다. 구매 후 소비하며, 정규화 연료·SCI, 기존 리플레이, PR141의 400행 안전회계와 분리됩니다. 강화학습 개선이나 실제 선박 비용 절감 결과가 아닙니다.'}</p>

  <section aria-labelledby="u01-inputs"><h2 id="u01-inputs">{en?'1. Shared inputs and constraints':'1. 같은 입력과 제약'}</h2>
   <div className="u01-ports">{u01.ports.map((port,i)=><article key={port}><h3>{port}</h3><p>{en?'Price':'가격'}: {i<2?u01.input.p[i]:u01.terminal_reference_price_usd_t} USD/t</p><p>{i<2?`${en?'Next-leg consumption':'다음 구간 소모'}: ${u01.input.d[i]} t`:en?'Destination: no further leg or purchase. Price is reference only.':'종점: 이후 구간·급유 없음. 가격은 참고만 합니다.'}</p></article>)}</div>
   <p>{en?'One fuel grade · capacity 100 t · initial inventory 20 t · minimum ARRIVAL reserve 10 t · final inventory exactly 10 t. Supply at A/B: 100 t each; no minimum lift or fees. All methods see the same fixed prices and consumption.':'유종 하나 · 용량 100t · 초기 잔량 20t · 도착 시 안전잔량 10t · 최종 잔량 정확히 10t. A/B 공급한도 각각 100t, 최소급유량·수수료 없음. 모든 방법은 같은 고정 가격·소모량을 봅니다.'}</p>
   <p className="u01-equation">{en?'Departure = arrival + purchase; next arrival = departure − consumption.':'출항 잔량 = 도착 잔량 + 구매량; 다음 도착 잔량 = 출항 잔량 − 소모량.'}<br/><code>D_i = I_i + q_i; I_next = D_i - d_i; D_i ≤ 100; I_next ≥ 10; I_C = 10</code></p>
  </section>

  <section aria-labelledby="u01-walkthrough"><h2 id="u01-walkthrough">{en?'2. Follow the purchase ledger':'2. 구매와 잔량을 따라가기'}</h2>
   <p>{en?'The initial quantities are the saved Python LP solution. Editing quantities checks a proposed ledger only; the browser does not run an optimizer or a model.':'초기 구매량은 저장된 Python LP 해입니다. 구매량 편집은 제안한 원장만 검산하며 브라우저에서 최적화나 모델을 실행하지 않습니다.'}</p>
   <div className="u01-input-row">{['A','B'].map((port,i)=><label key={port} htmlFor={`u01-q-${port}`}>{en?`Purchase at ${port} (t)`:`${port}항 구매량 (t)`}<input id={`u01-q-${port}`} type="text" inputMode="decimal" value={values[i]} aria-invalid={!isU01Quantity(values[i])} aria-describedby={!isU01Quantity(values[i])?'u01-input-help u01-input-error':'u01-input-help'} onChange={e=>{const next=[...values];next[i]=e.target.value;setValues(next);setStep(0)}}/></label>)}</div>
   <p id="u01-input-help">{en?'Use 20 / 40 to inspect U01. Try 19 / 41 to see the reserve failure.':'20 / 40으로 U01을 확인하고, 19 / 41로 안전잔량 위반을 확인해보세요.'}</p>
   <div className="u01-actions"><button type="button" onClick={reset}>{en?'Reset U01':'U01 초기화'}</button><button type="button" onClick={()=>{setValues(['19','41']);setStep(0)}}>{en?'Load unsafe 19 / 41':'위반 예시 19 / 41'}</button></div>
   {!result.validInput?<p id="u01-input-error" className="u01-error" role="alert">{inputError}</p>:<>
    <nav className="u01-step-nav" aria-label={en?'U01 voyage steps':'U01 항차 단계'}>{steps.map((label,i)=><button type="button" key={label} aria-current={step===i?'step':undefined} onClick={()=>setStep(i)}>{i+1}. {label}</button>)}</nav>
    <div className="u01-step-state" aria-live="polite" aria-atomic="true"><h3>{steps[step]}</h3><p>{en?'Arrival inventory':'도착 잔량'}: <strong>{fmt(current!.fuel)} t</strong> · {en?'Cumulative purchase outlay':'누적 구매지출'}: <strong>${fmt(current!.spent)}</strong></p>
     {step===0?<p>{en?'Start with 20 t. The first leg consumes 30 t, so at least 20 t must be purchased at A to arrive at B with 10 t.':'20t로 시작합니다. 첫 구간에서 30t를 소비하므로 B에 10t로 도착하려면 A에서 적어도 20t를 사야 합니다.'}</p>:<p>{result.rows[step-1].arrival} + {result.rows[step-1].purchase} − {result.rows[step-1].consumption} = {fmt(result.rows[step-1].nextArrival)} t · ${fmt(result.rows[step-1].cost)} {en?'at this purchase':'이번 구매비'}</p>}
    </div>
    <div className="u01-actions"><button type="button" aria-disabled={step===0} onClick={()=>{if(step>0)setStep(step-1)}}>{en?'Previous step':'이전 단계'}</button><button type="button" aria-disabled={step===2} onClick={()=>{if(step<2)setStep(step+1)}}>{en?'Next step':'다음 단계'}</button></div>
    <div className="u01-table-scroll" role="region" aria-label={en?'Purchase ledger, scroll horizontally if needed':'구매 원장, 필요 시 가로 스크롤'} tabIndex={0}><table><caption>{en?'Complete two-leg ledger (t / USD)':'전체 두 구간 원장 (t / USD)'}</caption><thead><tr>{(en?['Port','Arrival t','Buy t','Depart t','Burn t','Next arrival t','Cost USD']:['항구','도착 t','구매 t','출항 t','소모 t','다음 도착 t','비용 USD']).map(h=><th scope="col" key={h}>{h}</th>)}</tr></thead><tbody>{result.rows.map(r=><tr key={r.port}><th scope="row">{r.port}</th>{[r.arrival,r.purchase,r.departure,r.consumption,r.nextArrival,r.cost].map((v,i)=><td key={i}>{fmt(v)}</td>)}</tr>)}</tbody></table></div>
    <p role="status" className={result.feasible?'u01-success':'u01-error'}>{result.feasible?(en?`All constraints satisfied. Total $${fmt(result.comparableCost!)} · final inventory ${fmt(result.terminal!)} t.`:`모든 제약 충족. 총비용 $${fmt(result.comparableCost!)} · 최종 잔량 ${fmt(result.terminal!)}t.`):(en?`Failed plan. Raw outlay $${fmt(result.rawCost!)} is excluded from valid cost comparisons. Final inventory ${fmt(result.terminal!)} t does not erase an earlier violation.`:`실패한 구매안입니다. 원지출 $${fmt(result.rawCost!)}는 유효 비용 비교에서 제외합니다. 최종 잔량 ${fmt(result.terminal!)}t여도 앞선 위반은 사라지지 않습니다.`)}</p>
    {result.violations.length>0&&<ul className="u01-error">{result.violations.map((v,i)=><li key={i}>{v.port}: {({reserve:v.port==='C'?(en?'Destination arrival inventory below 10 t. No purchase is allowed at C.':'종점 도착 잔량 10t 미만. C에서는 급유하지 않습니다.'):(en?'Arrival reserve below 10 t BEFORE refueling; later purchases cannot repair it.':'급유 전 도착 잔량 10t 미만. 이후 구매로 복구 처리하지 않습니다.'),capacity:en?'Departure inventory exceeds capacity.':'출항 잔량이 용량을 초과합니다.',supply:en?'Purchase exceeds supply.':'공급한도를 초과합니다.',terminal:en?'Final inventory is not 10 t.':'최종 잔량이 10t가 아닙니다.'})[v.kind]}</li>)}</ul>}
   </>}
  </section>

  <section aria-labelledby="u01-methods"><h2 id="u01-methods">{en?'3. Same contract, four saved methods':'3. 같은 계약, 저장된 네 방법'}</h2>
   <p>{en?'This table always describes the original U01 inputs, independent of the editable candidate above. It is one reused development/unit-test case, not a new holdout. LP is a mathematical optimum, not AI; the two simple rules also reach it here.':'이 표는 위 편집 후보와 별개로 원본 U01 입력의 결과를 유지합니다. 재사용한 개발·단위검사 사례 하나이며 새 확인집합이 아닙니다. LP는 수학적 최적해이며 AI가 아닙니다. 이 사례에서는 두 간단한 규칙도 같은 최적해에 도달합니다.'}</p>
   <div className="u01-table-scroll" role="region" aria-label={en?'Original U01 method comparison':'원본 U01 방법 비교'} tabIndex={0}><table><caption>{en?'Shared capacity, reserves, prices and final inventory':'동일 용량·안전잔량·가격·최종재고'}</caption><thead><tr>{(en?['Method','A buy t','B buy t','Cost USD','Final t']:['방법','A 구매 t','B 구매 t','비용 USD','최종 t']).map(h=><th scope="col" key={h}>{h}</th>)}</tr></thead><tbody>{u01.methods.map(m=><tr key={m.id}><th scope="row">{methodNames[m.id]}</th><td>{fmt(m.purchases_t[0])}</td><td>{fmt(m.purchases_t[1])}</td><td>{fmt(m.total_usd)}</td><td>{fmt(m.terminal_t)}</td></tr>)}</tbody></table></div>
  </section>

  <section aria-labelledby="u01-evidence"><h2 id="u01-evidence">{en?'4. Evidence and remaining work':'4. 재현 근거와 남은 일'}</h2>
   <p>{en?'Implemented: fixed U01 walkthrough and a separate t/USD candidate ledger. Verified evidence: recorded Python LP, three rules, stop-pattern enumeration and an independent decimal/algebra check. Source version:':'구현: 고정 U01 단계 설명과 별도 t/USD 후보 원장. 검증 근거: Python LP·규칙 세 종류·정차조합 열거 실행, 별도 십진 계산·일차식 검산. 소스 버전:'} <code>{u01.source_commit.slice(0,7)}</code>.</p>
   <p>{en?'Not completed: matched RL evaluation under this contract, unseen confirmation data, external model replication or real-voyage validation. PR141 safety accounting is a separate unmerged study and is not used here.':'미완료: 이 계약의 동등조건 강화학습 평가, 미사용 확인자료, 외부 모델 재현, 실항차 검증. PR141 안전회계는 별도 미병합 연구이며 여기서 사용하지 않습니다.'}</p>
   <ul><li><a href={`${root}/research/procurement_baseline/README.md`}>{en?'Formulation, results and reproduction commands (English)':'모형·결과·재현 명령 (영문)'}</a></li><li><a href={`${root}/tests/test_procurement_baseline_core.py`}>{en?'Original U01 test and reserve-failure check':'원본 U01 검사와 안전선 반례'}</a></li><li><a href={`${root}/${u01.source_path}`}>{en?'Pinned Python solver and audit':'고정 버전 Python 최적화·검산 코드'}</a></li><li><a href="https://drive.google.com/file/d/1IK8BbXnQHb52_pOSMKRqAEJK0C2e47nl/view">{en?'One-page English research overview':'영문 연구 소개 1쪽'}</a></li></ul>
  </section>
 </main>;
}
export default function ProcurementPage(){return <LocaleProvider><ProcurementExample/></LocaleProvider>}
