import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ts from 'typescript';

// Load the production TypeScript modules, including their relative imports.
// There is no hand-copied implementation in this test harness.
const modules = new Map();
const nodeRequire = createRequire(import.meta.url);
let renderedLanguage = 'ko';
function loadModule(filename) {
  const absolute = path.resolve(filename);
  if (modules.has(absolute)) return modules.get(absolute).exports;
  const loaded = {exports:{}};
  modules.set(absolute,loaded);
  const source = ts.transpileModule(fs.readFileSync(absolute,'utf8'),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true},
  }).outputText;
  const require = specifier => {
    // Only locale is controlled. React and all rendered components are real.
    if (specifier==='@/lib/locale') return {useLocale:()=>({lang:renderedLanguage})};
    if (!specifier.startsWith('.') && !specifier.startsWith('@/')) return nodeRequire(specifier);
    const resolved = specifier.startsWith('@/')
      ? path.resolve(specifier.slice(2)) : path.resolve(path.dirname(absolute),specifier);
    if (path.extname(resolved)) return loadModule(resolved);
    const file = ['.ts','.tsx'].map(extension=>`${resolved}${extension}`).find(fs.existsSync);
    assert(file,`Cannot resolve production module ${specifier}`);
    return loadModule(file);
  };
  vm.runInNewContext(source,{module:loaded,exports:loaded.exports,require},{filename:absolute});
  return loaded.exports;
}
const {
  callTiming,parseTiming,reviewScenario,scenarioExport,scenarioPreset,
  TIME_FIELDS,FUEL_TOLERANCE,STEP_HOURS,REVIEW_VERSION,SOURCE_REVISION,
} = loadModule('lib/scenario-review.ts');
const {decisionSnapshot,comparePurchases} = loadModule('lib/purchase-comparison.ts');
const plain = value => JSON.parse(JSON.stringify(value));
const near = (actual,expected) => assert(
  Math.abs(actual-expected) <= 1e-9*Math.max(1,Math.abs(expected)),
  `${actual} != ${expected}`,
);
const normal = () => parseTiming(scenarioPreset('normal'));
const input = overrides => ({...normal(),...overrides});
const reading = (value,step=0) => ({value,step,kind:'record',timestamp:null});
function snapshot(fuel=.5,step=0,price=500,fx=1300) {
  return {step,remaining:30-step,fuel:reading(fuel,step),price:reading(price,step),fx:reading(fx,step),
    previousPrice:{value:null,step:null,kind:'missing',timestamp:null}};
}
const candidate = (review,id) => {
  const found = review.candidates.find(item => item.id===id);
  assert(found,`Missing candidate ${id}`);
  return found;
};
const excluded = (item,reason) => {
  assert.notEqual(item.status,'feasible');
  assert(item.reasons.includes(reason),`${item.id} lacks reason ${reason}: ${item.reasons}`);
  assert.equal(item.comparableSCI,null);
  assert.equal(item.rank,null);
};
let checks = 0;
const failures = [];
function check(name,run) {
  checks++;
  try {run();} catch (error) {failures.push({name,error});}
}

check('hand-calculated timing parity, overlap, readiness and departure floor',()=>{
  const cases = [
    [{cargoEnd:13,bunkerReady:0,preparation:0,transfer:10,cleanup:0},15,3],
    [{cargoEnd:10,bunkerReady:14,preparation:0,transfer:0,cleanup:0},16,4],
    [{cargoEnd:15,bunkerReady:8,preparation:1,transfer:6,cleanup:1},18,6],
    [{cargoEnd:10,bunkerReady:0,preparation:1,transfer:7,cleanup:1},12,0],
    [{cargoEnd:11,bunkerReady:0,preparation:1,transfer:7,cleanup:1},13,1],
    [{baselineDeparture:20},20,0],
    [{baselineDeparture:12,cargoEnd:12,departureReadiness:0},12,0],
    [{baselineDeparture:12,cargoEnd:12,bunkerReady:6,departureReadiness:0},16,4],
    [{baselineDeparture:12,cargoEnd:15,transfer:6,departureReadiness:0},15,3],
    [{baselineDeparture:12,cargoEnd:12,bunkerReady:4.5,departureReadiness:0},14.5,2.5],
  ];
  for (const [values,departure,extra] of cases) {
    const result = callTiming(input(values),true);
    assert.equal(result.status,'known');
    near(result.departure,departure); near(result.extraHours,extra);
  }
  const zero = Object.fromEntries(TIME_FIELDS.map(key=>[key,0]));
  const result = callTiming(zero,true);
  assert.equal(result.status,'known'); near(result.departure,0); near(result.extraHours,0);
});

check('readiness is after all work, never absorbed into bunker cleanup',()=>{
  const base = {baselineDeparture:10,cargoEnd:10,bunkerReady:0,preparation:1,transfer:6};
  near(callTiming(input({...base,cleanup:3,departureReadiness:0}),true).extraHours,0);
  near(callTiming(input({...base,cleanup:1,departureReadiness:2}),true).extraHours,2);
});

check('each missing field remains unknown, including omitted runtime readiness',()=>{
  for (const field of TIME_FIELDS) {
    const result = callTiming(input({[field]:null}),true);
    assert.equal(result.status,'incomplete',field);
    assert(result.missing.includes(field));
    assert.equal(result.departure,null); assert.equal(result.extraHours,null);
  }
  const omitted = normal(); delete omitted.departureReadiness;
  const result = callTiming(omitted,true);
  assert.equal(result.status,'incomplete');
  assert(result.missing.includes('departureReadiness'));
});

check('reject invalid numbers and validate even beside a missing field',()=>{
  for (const field of TIME_FIELDS) {
    for (const bad of [-1,NaN,Infinity,-Infinity,true,false,'2',[],{}]) {
      const result = callTiming(input({[field]:bad}),true);
      assert.equal(result.status,'invalid',`${field} = ${String(bad)}`);
      assert(result.invalid.includes(field));
      assert.equal(result.departure,null);
    }
  }
  assert.equal(callTiming(input({transfer:null,departureReadiness:-1}),true).status,'invalid');
  assert.equal(callTiming(input({bunkerReady:1e308,transfer:1e308}),true).status,'invalid');
  assert.equal(callTiming(input({transfer:1e308,departureReadiness:1e308}),true).status,'invalid');
});

check('form blanks and explicit zero remain distinct; invalid entries do not become zero',()=>{
  for (const blank of ['',' ','\t\n']) {
    const parsed = parseTiming({...scenarioPreset('normal'),transfer:blank});
    assert.equal(parsed.transfer,null);
    assert.equal(callTiming(parsed,true).status,'incomplete');
  }
  const zero = parseTiming({...scenarioPreset('normal'),departureReadiness:'0'});
  assert.equal(zero.departureReadiness,0); assert.equal(callTiming(zero,true).status,'known');
  const omitted = scenarioPreset('normal'); delete omitted.departureReadiness;
  assert.equal(parseTiming(omitted).departureReadiness,null);
  for (const bad of ['-1','not-a-number','Infinity','1e309']) {
    assert.equal(callTiming(parseTiming({...scenarioPreset('normal'),transfer:bad}),true).status,'invalid');
  }
  near(parseTiming({...scenarioPreset('normal'),transfer:' 2.5 '}).transfer,2.5);
});

check('Wait uses the counterfactual baseline, already including readiness',()=>{
  const sparse = Object.fromEntries(TIME_FIELDS.map(key=>[key,null]));
  sparse.baselineDeparture=12; sparse.deadline=14;
  const result=callTiming(sparse,false);
  assert.equal(result.status,'known'); near(result.departure,12); near(result.extraHours,0);
  assert.equal(result.bunkerEnd,null);
  near(callTiming(input({departureReadiness:100}),false).departure,12);
  assert.equal(callTiming({...sparse,baselineDeparture:null},false).status,'incomplete');
  assert.equal(callTiming({...sparse,deadline:null},false).status,'incomplete');
});

check('normal, conflicting-deadline and missing-input presets are reproducible',()=>{
  const normalReview=reviewScenario(snapshot(),normal());
  assert.equal(normalReview.eligibleCount,4); assert.equal(normalReview.tied,true);
  for(const item of normalReview.candidates) {
    assert.equal(item.status,'feasible'); assert.equal(item.rank,1);
    assert(item.steps.every(step=>step.onTime===true));
  }
  const tight=reviewScenario(snapshot(),parseTiming(scenarioPreset('deadline')));
  assert.equal(tight.eligibleCount,1); assert.equal(candidate(tight,'wait-wait').status,'feasible');
  for(const id of ['wait-buy','buy-wait','buy-buy']) excluded(candidate(tight,id),'deadline');
  const missing=reviewScenario(snapshot(),parseTiming(scenarioPreset('missing')));
  assert.equal(missing.eligibleCount,1);
  for(const id of ['wait-buy','buy-wait','buy-buy']) {
    const item=candidate(missing,id); excluded(item,'missing_time'); assert.equal(item.status,'incomplete');
  }
  const a=scenarioPreset('normal'); a.transfer='999';
  assert.equal(scenarioPreset('normal').transfer,'8');
});

check('every step deadline is inclusive and accumulated delay cannot disappear',()=>{
  const late=input({cargoEnd:13,preparation:0,transfer:10,cleanup:0,deadline:15});
  const review=reviewScenario(snapshot(),late);
  const buyWait=candidate(review,'buy-wait');
  assert.equal(buyWait.status,'feasible');
  near(buyWait.steps[0].departureHours,15); near(buyWait.steps[0].deadlineHours,15);
  near(buyWait.steps[1].departureHours,39); near(buyWait.steps[1].deadlineHours,39);
  assert(buyWait.steps.every(step=>step.onTime));
  const buyBuy=candidate(review,'buy-buy'); excluded(buyBuy,'deadline');
  near(buyBuy.steps[1].departureHours,42);
  assert.equal(buyBuy.steps[0].onTime,true); assert.equal(buyBuy.steps[1].onTime,false);
  const missed=reviewScenario(snapshot(),{...late,deadline:14});
  const lateThenWait=candidate(missed,'buy-wait'); excluded(lateThenWait,'deadline');
  assert.equal(lateThenWait.steps[0].onTime,false); assert.equal(lateThenWait.steps[1].onTime,false);
  const zero=input(Object.fromEntries(TIME_FIELDS.map(key=>[key,0])));
  assert.equal(reviewScenario(snapshot(),zero).eligibleCount,4);
});

check('unknown earlier delay propagates through a later Wait',()=>{
  const item=candidate(reviewScenario(snapshot(),input({transfer:null})),'buy-wait');
  excluded(item,'missing_time'); assert.equal(item.steps[0].onTime,null);
  assert.equal(item.steps[1].timing.status,'known');
  assert.equal(item.steps[1].departureHours,null); assert.equal(item.steps[1].onTime,null);
  assert.equal(item.steps[1].deadlineHours,38);
  const invalid=reviewScenario(snapshot(),input({transfer:-1}));
  excluded(candidate(invalid,'buy-buy'),'invalid_time');
  assert.equal(candidate(invalid,'wait-wait').status,'feasible');
});

check('pre-refill shortage and reserve failures cannot be repaired by a Buy',()=>{
  const shortage=candidate(reviewScenario(snapshot(.03),normal()),'buy-buy');
  excluded(shortage,'fuel_shortage'); excluded(shortage,'reserve_breach');
  near(shortage.steps[0].fuelBeforeRefill,-.02); near(shortage.steps[0].fuelAfter,.9);
  const reserve=candidate(reviewScenario(snapshot(.10),normal()),'buy-buy');
  excluded(reserve,'reserve_breach'); near(reserve.steps[0].fuelBeforeRefill,.05);
  near(reserve.steps[0].fuelAfter,.95);
  const boundary=reviewScenario(snapshot(.20),normal());
  assert.equal(candidate(boundary,'buy-wait').status,'feasible');
  excluded(candidate(boundary,'wait-buy'),'reserve_breach');
  near(candidate(boundary,'wait-buy').steps[1].fuelBeforeRefill,.10);
  assert.equal(candidate(reviewScenario(snapshot(.25),normal()),'wait-wait').status,'feasible');
  assert.equal(candidate(reviewScenario(snapshot(.25-FUEL_TOLERANCE/2),normal()),'wait-wait').status,'feasible');
  excluded(candidate(reviewScenario(snapshot(.25-2*FUEL_TOLERANCE),normal()),'wait-wait'),'reserve_breach');
  const exactEmpty=candidate(reviewScenario(snapshot(.05),normal()),'buy-buy');
  assert(!exactEmpty.reasons.includes('fuel_shortage')); excluded(exactEmpty,'reserve_breach');
});

check('initial capacity one, refill target .95 and requested .9 are preserved',()=>{
  for(const fuel of [0,.03,.2,.5,.95,1]) {
    const review=reviewScenario(snapshot(fuel),normal());
    for(const item of review.candidates) for(const step of item.steps) {
      assert(step.amount>=0 && step.amount<=.9+FUEL_TOLERANCE);
      assert(step.fuelAfter<=.95+FUEL_TOLERANCE);
      assert(!item.reasons.includes('capacity'));
    }
  }
  const full=candidate(reviewScenario(snapshot(1),normal()),'buy-buy');
  near(full.steps[0].amount,0); near(full.steps[0].fuelAfter,.95); near(full.steps[1].amount,.05);
  assert.equal(full.status,'feasible');
  const zeroBuy=candidate(reviewScenario(snapshot(1),parseTiming(scenarioPreset('deadline'))),'buy-wait');
  near(zeroBuy.steps[0].amount,0); near(zeroBuy.steps[0].timing.extraHours,8);
  excluded(zeroBuy,'deadline');
  assert.equal(reviewScenario(snapshot(1.01),normal()).status,'unavailable');
});

check('depleted legacy paths retain diagnostics, never ranks or unexecuted checks',()=>{
  const review=reviewScenario(snapshot(0),normal());
  for(const id of ['wait-wait','wait-buy']) {
    const item=candidate(review,id); excluded(item,'depleted');
    assert.equal(item.steps.length,1); assert.equal(item.actions.length,2);
    near(item.finalFuel,0);
  }
  assert.equal(review.eligibleCount,0);
  for(const item of review.candidates) {assert.equal(item.comparableSCI,null); assert.equal(item.rank,null);}
  assert.equal(candidate(review,'buy-buy').steps.length,2,'Legacy refill survives for diagnostics');
});

check('fair adjusted SCI cancels inventory differences at the same current market',()=>{
  const review=reviewScenario(snapshot(.5),normal());
  assert.equal(review.unitValue,650000);
  assert.equal(candidate(review,'wait-wait').purchaseSCI,0);
  near(candidate(review,'buy-wait').purchaseSCI,325000);
  near(candidate(review,'wait-wait').finalFuel,.4);
  near(candidate(review,'buy-wait').finalFuel,.9);
  for(const item of review.candidates) {
    near(item.inventoryAdjustedSCI,65000); near(item.comparableSCI,65000); assert.equal(item.rank,1);
  }
  const one=reviewScenario(snapshot(.5,29),normal());
  assert.equal(one.horizon,1); assert.equal(one.candidates.length,2);
  for(const item of one.candidates) {
    near(item.comparableSCI,32500); assert.equal(item.steps.length,1); assert.equal(item.steps[0].decision,30);
  }
  assert.equal(reviewScenario(null,normal()).status,'unavailable');
});

check('invalid or stale current observations pause review; absent history does not',()=>{
  for(const key of ['fuel','price','fx']) for(const value of [null,NaN,Infinity,-1]) {
    const s=snapshot(); s[key]={...s[key],value};
    assert.equal(reviewScenario(s,normal()).status,'unavailable',`${key}: ${value}`);
  }
  for(const key of ['fuel','price','fx']) for(const override of [{step:1},{kind:'missing'},{kind:'assumption'}]) {
    const s=snapshot(); s[key]={...s[key],...override};
    assert.equal(reviewScenario(s,normal()).candidates.length,0);
  }
  for(const key of ['price','fx']) {
    const s=snapshot(); s[key]={...s[key],value:0};
    assert.equal(reviewScenario(s,normal()).status,'unavailable');
  }
  for(const override of [{step:-1},{step:30},{step:.5},{remaining:29},{remaining:1.5}]) {
    assert.equal(reviewScenario({...snapshot(),...override},normal()).status,'unavailable');
  }
  assert.equal(reviewScenario(snapshot(.5,0,1e308,1e308),normal()).status,'unavailable');
  assert.equal(reviewScenario(snapshot(),normal()).eligibleCount,4);
});

check('overflow in accumulated call delays excludes candidates',()=>{
  const huge=input({baselineDeparture:0,cargoEnd:0,bunkerReady:0,preparation:0,transfer:9e307,cleanup:0,departureReadiness:0,deadline:1e308});
  const item=candidate(reviewScenario(snapshot(),huge),'buy-buy');
  excluded(item,'arithmetic'); assert.equal(item.status,'invalid');
  assert.equal(item.steps[1].onTime,null); assert.equal(item.steps[1].departureHours,null);
});

check('export captures current edited inputs, provenance and full precision results',()=>{
  const s=snapshot(.53456789,7,503.123456,1297.987654);
  const form={...scenarioPreset('normal'),transfer:'7.123456789',departureReadiness:'0'};
  const generatedAt='2026-10-13T00:00:00.000Z';
  const selection={policy:'double_dqn',checkpoint:'dqn_42',caseSeed:57};
  const exported=scenarioExport(s,form,generatedAt,selection);
  assert.equal(exported.schemaVersion,1); assert.equal(exported.reviewVersion,REVIEW_VERSION);
  assert.equal(exported.sourceRevision,SOURCE_REVISION); assert.equal(exported.generatedAt,generatedAt);
  assert.equal(exported.rawTimingInputs.transfer,'7.123456789');
  assert.equal(exported.timingInputs.transfer,7.123456789);
  assert.equal(exported.assumptions.stepHours,STEP_HOURS);
  assert.equal(exported.assumptions.fuelTolerance,FUEL_TOLERANCE);
  assert.deepEqual(plain(exported.replaySelection),selection);
  selection.caseSeed=99;
  assert.equal(exported.replaySelection.caseSeed,57,'Earlier exports retain their record selection');
  assert.match(exported.units.cost,/SCI.*not currency/);
  assert.match(exported.provenance.timeInputs,/synthetic_assumption/);
  assert.deepEqual(plain(exported.result),plain(reviewScenario(s,parseTiming(form))));
  assert.deepEqual(plain(JSON.parse(JSON.stringify(exported)).result),plain(exported.result));
  const edited=scenarioExport(s,{...form,transfer:''},generatedAt);
  assert.equal(edited.timingInputs.transfer,null);
  excluded(candidate(edited.result,'buy-buy'),'missing_time');
  assert.equal(exported.rawTimingInputs.transfer,'7.123456789','Earlier exports must retain earlier form values');
  const ended=scenarioExport(null,form,generatedAt);
  assert.equal(ended.result.status,'unavailable'); assert.equal(ended.snapshot,null);
  assert.equal(ended.replaySelection,null);
});

check('repeated review, preset changes and export leave current input objects untouched',()=>{
  const s=snapshot();
  for(const value of Object.values(s)) if(value && typeof value==='object') Object.freeze(value);
  Object.freeze(s);
  const form=Object.freeze(scenarioPreset('normal'));
  const parsed=Object.freeze(parseTiming(form));
  const before=JSON.stringify({s,form,parsed});
  const expected=plain(reviewScenario(s,parsed));
  for(let i=0;i<10;i++) {
    assert.deepEqual(plain(reviewScenario(s,parsed)),expected);
    reviewScenario(s,parseTiming(scenarioPreset('deadline')));
    reviewScenario(s,parseTiming(scenarioPreset('missing')));
    scenarioExport(s,form,'2026-10-13T00:00:00.000Z');
  }
  assert.equal(JSON.stringify({s,form,parsed}),before);
});

// This is server-side markup inspection only. It does not simulate browser
// interaction, exercise event handlers/download delivery, or verify appearance.
const FixedScenarioReview = loadModule('components/ocean/FixedScenarioReview.tsx').default;
const PurchaseComparison = loadModule('components/ocean/PurchaseComparison.tsx').default;
const render = (component,props) => renderToStaticMarkup(createElement(component,props));
const inputTags = html => html.match(/<input\b[^>]*>/g) ?? [];
const bodyRows = html => (html.match(/<tbody\b[^>]*>([\s\S]*?)<\/tbody>/)?.[1].match(/<tr\b/g) ?? []).length;
const jsonButton = (html,language) => {
  const label=language==='en' ? 'Export review JSON' : '검토 결과 JSON 저장';
  const button=(html.match(/<button\b[^>]*>[\s\S]*?<\/button>/g) ?? []).find(tag=>tag.includes(label));
  assert(button,`Missing ${language} JSON export button`);
  return button;
};
const labels={
  en:['Departure without bunkering','Cargo end including bunker impact','Bunker-ready time','Preparation duration',
    'Transfer duration','Cleanup duration','Post-work departure readiness','Departure deadline'],
  ko:['급유 없는 출항','급유 영향 반영 하역 종료','급유 준비 가능 시각','급유 준비 시간',
    '이송 시간','마무리 시간','모든 작업 후 출항 준비','출항 마감'],
};
for(const language of ['ko','en']) {
  check(`${language} static markup has eight associated labels, normal rows and tied summary`,()=>{
    renderedLanguage=language;
    const html=render(FixedScenarioReview,{snapshot:snapshot()});
    const inputs=inputTags(html);
    assert.equal(inputs.length,8);
    const ids=inputs.map(tag=>tag.match(/\bid="([^"]+)"/)?.[1]);
    assert.equal(new Set(ids).size,8,'Each input must have a unique id');
    for(const [index,field] of TIME_FIELDS.entries()) {
      const tag=inputs.find(item=>item.includes(`id="scenario-${field}"`));
      assert(tag,`Missing ${language} input for ${field}`);
      assert(tag.includes(`name="${field}"`));
      assert(tag.includes('type="number"')); assert(tag.includes('min="0"')); assert(tag.includes('step="any"'));
      assert(tag.includes('placeholder="UNKNOWN"'));
      assert(tag.includes(`value="${scenarioPreset('normal')[field]}"`));
      const label=html.match(new RegExp(`<label\\b[^>]*for="scenario-${field}"[^>]*>([\\s\\S]*?)<\\/label>`));
      assert(label,`No associated label for ${field}`);
      assert(label[1].includes(labels[language][index]),`Wrong ${language} label for ${field}`);
    }
    assert.equal(bodyRows(html),4);
    assert.equal((html.match(/class="scenario-status feasible"/g) ?? []).length,4);
    assert.equal((html.match(new RegExp(language==='en' ? 'Eligible rank 1' : '충족 후보 내 1위','g')) ?? []).length,4);
    assert(html.includes(language==='en' ? '4/4 candidates pass modeled checks' : '4개 중 4개 가정 제약 충족'));
    assert(html.includes(language==='en' ? 'Adjusted SCI tied' : '보정 SCI 동률'));
    assert(!/\sdisabled(?:="[^"]*")?(?=\s|>)/.test(jsonButton(html,language)));
    assert(html.includes('65,000'));
  });

  check(`${language} static markup distinguishes one-step, unavailable and ended records`,()=>{
    renderedLanguage=language;
    const one=render(FixedScenarioReview,{snapshot:snapshot(.5,29)});
    assert.equal(bodyRows(one),2);
    assert(one.includes(language==='en' ? '1-step horizon' : '1단계 검토'));
    for(const missing of [null,{...snapshot(),price:{...reading(null),kind:'missing'}}]) {
      const unavailable=render(FixedScenarioReview,{snapshot:missing});
      assert.equal(bodyRows(unavailable),0);
      assert(unavailable.includes(language==='en' ? 'Review unavailable:' : '검토할 수 없습니다.'));
      assert(/\sdisabled(?:="[^"]*")?(?=\s|>)/.test(jsonButton(unavailable,language)));
      assert.equal(inputTags(unavailable).length,8);
    }
    const trace=[[.95,0,.05,0,0,0,500,1300]];
    const active=render(PurchaseComparison,{trace,index:0});
    assert.equal(inputTags(active).length,8); assert.equal(bodyRows(active),4);
    const ended=render(PurchaseComparison,{trace,index:trace.length});
    assert(ended.includes(language==='en' ? 'This recorded voyage has ended.' : '선택한 항차 기록이 종료됐습니다.'));
    assert.equal(inputTags(ended).length,0); assert.equal(bodyRows(ended),0);
    assert(!ended.includes(language==='en' ? 'Export review JSON' : '검토 결과 JSON 저장'));
  });
}

let replayDecisions=0;
check('bundled replay stays unchanged, legacy transitions preserved, future rows inaccessible',()=>{
  const replay=JSON.parse(fs.readFileSync('public/data/replay.json','utf8'));
  const before=JSON.stringify(replay);
  for(const traces of Object.values(replay.runs)) for(const trace of Object.values(traces)) {
    for(let i=0;i<trace.length;i++) {
      const guarded=new Proxy(trace,{get(target,key){
        if(/^\d+$/.test(String(key)) && Number(key)>i) throw new Error('Future row accessed');
        return target[key];
      }});
      const s=decisionSnapshot(guarded,i);
      const review=reviewScenario(s,normal());
      const legacy=comparePurchases(s);
      assert.equal(review.candidates.length,legacy.length);
      for(let j=0;j<legacy.length;j++) {
        const actual=review.candidates[j],expected=legacy[j];
        near(actual.purchaseSCI,expected.cost); near(actual.finalFuel,expected.finalFuel);
        near(actual.purchasedFuel,expected.amount); assert.equal(actual.steps.length,expected.steps.length);
        for(let k=0;k<expected.steps.length;k++) {
          near(actual.steps[k].fuelAfter,expected.steps[k].fuelAfter);
          near(actual.steps[k].amount,expected.steps[k].amount);
        }
        if(actual.status==='feasible') {
          near(actual.comparableSCI,.05*expected.steps.length*review.unitValue);
          assert.equal(actual.rank,1);
        } else {assert.equal(actual.comparableSCI,null); assert.equal(actual.rank,null);}
      }
      replayDecisions++;
    }
    assert.equal(reviewScenario(decisionSnapshot(trace,trace.length),normal()).status,'unavailable');
  }
  assert.equal(JSON.stringify(replay),before);
});

if(failures.length) {
  for(const {name,error} of failures) console.error(`FAIL: ${name}\n${error.stack}`);
  console.error(JSON.stringify({checks,passed:checks-failures.length,failed:failures.length,replayDecisions}));
  process.exitCode=1;
} else {
  console.log(JSON.stringify({checks,replayDecisions,timingParity:'passed',safetyAndCapacity:'passed',deadlineAndUnknown:'passed',
    inventoryAdjustedSCI:'tied at fixed current price and FX',exportsAndRepeatedUse:'passed',futureRows:'blocked',legacyReplay:'unchanged',
    staticMarkup:'Korean/English passed; no browser interaction or visual verification'}));
}
