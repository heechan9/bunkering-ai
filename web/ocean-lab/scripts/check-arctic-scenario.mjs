import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ts from 'typescript';

// Execute production modules, not a copied implementation.
const modules=new Map(),nodeRequire=createRequire(import.meta.url);
let language='ko';
function load(filename) {
  const absolute=path.resolve(filename);
  if(modules.has(absolute))return modules.get(absolute).exports;
  const loaded={exports:{}};modules.set(absolute,loaded);
  const require=specifier=>{
    if(specifier==='@/lib/locale')return {useLocale:()=>({lang:language})};
    if(!specifier.startsWith('.')&&!specifier.startsWith('@/'))return nodeRequire(specifier);
    const resolved=specifier.startsWith('@/')?path.resolve(specifier.slice(2)):path.resolve(path.dirname(absolute),specifier);
    return load(path.extname(resolved)?resolved:['.ts','.tsx'].map(ext=>resolved+ext).find(fs.existsSync));
  };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(absolute,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{module:loaded,exports:loaded.exports,require,structuredClone},{filename:absolute});
  return loaded.exports;
}
const {arcticPreset,parseArctic,reviewArctic,arcticExport,ARCTIC_VERSION,ARCTIC_BASE_REVISION,COMMON_FIELDS}=load('lib/arctic-scenario.ts');
const component=load('components/ocean/ArcticScenarioReview.tsx').default;
const plain=value=>JSON.parse(JSON.stringify(value));
const near=(a,b)=>assert(Math.abs(a-b)<=1e-9*Math.max(1,Math.abs(b)),`${a} != ${b}`);
const candidate=(r,id)=>r.candidates.find(c=>c.id===id);
const calculate=form=>reviewArctic(parseArctic(form));
let checks=0,randomizedCandidates=0;const failures=[];
function check(name,run){checks++;try{run();}catch(error){failures.push({name,error});}}
const excluded=(c,reason)=>{assert.notEqual(c.status,'feasible');assert(c.reasons.includes(reason),`${c.id}: ${c.reasons}`);assert.equal(c.comparableSCI,null);assert.equal(c.rank,null);};

check('hand-calculated three presets, timing, eligibility and honest ties',()=>{
  const expected=[['normal',4,[24,28,28,32],65000],['delay-fuel',2,[36,40,40,44],130000],['supply-unavailable',1,[36,40,40,44],130000]];
  for(const [preset,count,times,sci] of expected){
    const review=calculate(arcticPreset(preset));assert.equal(review.eligibleCount,count);assert.equal(review.tied,count>1);
    review.candidates.forEach((c,i)=>{assert.equal(c.arrivalHours,times[i]);if(c.status==='feasible'){near(c.comparableSCI,sci);assert.equal(c.rank,1);}else{assert.equal(c.rank,null);assert.equal(c.comparableSCI,null);}});
  }
  const stress=calculate(arcticPreset('delay-fuel'));
  excluded(candidate(stress,'wait-wait'),'reserve_breach');excluded(candidate(stress,'buy-buy'),'arrival_deadline');
  assert.equal(candidate(stress,'buy-wait').status,'feasible');assert.equal(candidate(stress,'wait-buy').status,'feasible');
  const absent=calculate(arcticPreset('supply-unavailable'));
  assert.equal(candidate(absent,'buy-wait').status,'feasible');
  excluded(candidate(absent,'wait-buy'),'unavailable_supply');excluded(candidate(absent,'buy-buy'),'unavailable_supply');
});
check('Buy precedes consumption and supply is at origin/intermediate, never destination',()=>{
  const c=candidate(calculate(arcticPreset('normal')),'buy-wait');
  near(c.steps[0].openingFuel,.3);near(c.steps[0].amount,.65);near(c.steps[0].departureFuel,.95);near(c.steps[0].arrivalFuel,.90);
  near(c.steps[1].openingFuel,.90);near(c.steps[1].amount,0);near(c.finalFuel,.85);
  near(c.steps[0].departureHours,4);near(c.steps[0].arrivalHours,16);near(c.steps[1].arrivalHours,28);
});
check('same starting fuel and unit valuation for every candidate; cash outlay is not savings',()=>{
  const review=calculate(arcticPreset('normal'));
  assert(new Set(review.candidates.map(c=>c.purchaseSCI)).size>1);
  for(const c of review.candidates){near(c.steps[0].openingFuel,.3);near(c.inventoryAdjustedSCI,65000);near(c.purchaseSCI+(.3-c.finalFuel)*650000,c.inventoryAdjustedSCI);near(.3+c.purchasedFuel-c.consumedFuel,c.finalFuel);}
});
check('reserve failure cannot be repaired at the intermediate stop',()=>{
  const form=arcticPreset('normal');form.common.initialFuel='18';
  const c=candidate(calculate(form),'wait-buy');excluded(c,'reserve_breach');near(c.steps[0].arrivalFuel,.13);assert(c.finalFuel>.8);
});
check('negative fuel stops before a later purchase; no clamping or fabricated totals',()=>{
  const form=arcticPreset('normal');form.common.initialFuel='3';
  const c=candidate(calculate(form),'wait-buy');excluded(c,'fuel_shortage');assert.equal(c.steps.length,1);near(c.steps[0].arrivalFuel,-.02);
  for(const key of ['finalFuel','arrivalHours','purchaseSCI','purchasedFuel','consumedFuel','inventoryAdjustedSCI'])assert.equal(c[key],null);
});
check('final-leg exhaustion has no completed arrival, inventory or cost totals in review and JSON',()=>{
  const form=arcticPreset('normal');form.common.baseConsumption='20';
  const c=candidate(calculate(form),'wait-wait');excluded(c,'fuel_shortage');assert.equal(c.status,'infeasible');assert.equal(c.steps.length,2);
  near(c.steps[0].arrivalFuel,.1);near(c.steps[1].arrivalFuel,-.1);near(c.steps[1].arrivalHours,24);
  for(const key of ['finalFuel','arrivalHours','purchaseSCI','purchasedFuel','consumedFuel','inventoryAdjustedSCI','comparableSCI','rank'])assert.equal(c[key],null);
  const exported=candidate(arcticExport(form,'fixed').result,'wait-wait');
  for(const key of ['finalFuel','arrivalHours','purchaseSCI','purchasedFuel','consumedFuel','inventoryAdjustedSCI','comparableSCI','rank'])assert.equal(exported[key],null);
  for(const lang of ['ko','en']){
    language=lang;const html=renderToStaticMarkup(createElement(component,{form,onFormChange:()=>{},integrated:true}));
    const candidateHtml=html.match(/data-candidate="wait-wait"[\s\S]*?<\/article>/)[0];
    assert(candidateHtml.includes(lang==='en'?'Projected endpoint, not reached':'미도달 예상 끝점'));
    assert(candidateHtml.includes(lang==='en'?'projected endpoint (not reached)':'예상 끝점 (미도달)'));
    assert(candidateHtml.includes(lang==='en'?'Full-horizon totals remain UNKNOWN':'전체 구간 합계는 UNKNOWN'));
  }
});
check('reserve boundary is inclusive with normalized tolerance; no false winner',()=>{
  const form=arcticPreset('delay-fuel');form.common.initialFuel='35';
  assert.equal(candidate(calculate(form),'wait-wait').status,'feasible');
  form.common.initialFuel=String(35-1e-6);excluded(candidate(calculate(form),'wait-wait'),'reserve_breach');
});
check('arrival deadline includes all work and delay, exact boundary allowed',()=>{
  const form=arcticPreset('delay-fuel');let review=calculate(form);
  assert.equal(candidate(review,'buy-wait').arrivalHours,40);assert.equal(candidate(review,'buy-wait').status,'feasible');
  form.common.arrivalDeadlineHours='39.999999';review=calculate(form);
  excluded(candidate(review,'buy-wait'),'arrival_deadline');excluded(candidate(review,'wait-buy'),'arrival_deadline');assert.equal(review.eligibleCount,0);
});
check('decimal deadline equality allows roundoff only, never a meaningful grace period',()=>{
  const form=arcticPreset('normal');form.common.travelHours='0.1';form.common.bunkerWorkHours='0';form.common.arrivalDeadlineHours='0.6';form.legs.forEach(leg=>leg.delayHours='0.2');
  assert.equal(calculate(form).eligibleCount,4);form.common.arrivalDeadlineHours='0.599999999999';assert.equal(calculate(form).eligibleCount,0);
});
check('initial fuel above refill target is preserved, zero delivery still requires work',()=>{
  const form=arcticPreset('normal');form.common.initialFuel='100';
  const c=candidate(calculate(form),'buy-wait');near(c.steps[0].amount,0);near(c.steps[0].departureFuel,1);near(c.steps[0].arrivalFuel,.95);near(c.arrivalHours,28);
});
check('unavailable supply means zero delivery and exclusion, even for zero requested delivery',()=>{
  const form=arcticPreset('normal');form.common.initialFuel='100';form.legs[0].supply='unavailable';
  const review=calculate(form);const c=candidate(review,'buy-wait');excluded(c,'unavailable_supply');near(c.steps[0].amount,0);near(c.steps[0].workHours,4);
  assert.equal(candidate(review,'wait-wait').status,'feasible');
});
check('unknown supply is not false or zero; only attempted Buy becomes incomplete',()=>{
  for(const position of [0,1]){
    const form=arcticPreset('normal');form.legs[position].supply='unknown';
    for(const c of calculate(form).candidates){if(c.actions[position]){excluded(c,'unknown_supply');assert.equal(c.status,'incomplete');assert.equal(c.finalFuel,null);assert.equal(c.steps.at(-1).amount,null);assert.equal(c.steps.at(-1).arrivalFuel,null);}else assert.equal(c.status,'feasible');}
  }
  const form=arcticPreset('normal');form.common.initialFuel='100';form.legs[0].supply='unknown';excluded(candidate(calculate(form),'buy-wait'),'unknown_supply');
});
check('blank and omitted common inputs remain UNKNOWN, explicit zero remains a number',()=>{
  for(const field of COMMON_FIELDS)for(const blank of ['','  ','\t']){
    const form=arcticPreset('normal');form.common[field]=blank;const input=parseArctic(form),r=reviewArctic(input);
    assert.equal(input.common[field],null);assert.equal(r.inputStatus,'incomplete');assert(r.missing.includes(field));assert.equal(r.eligibleCount,0);
    for(const c of r.candidates){excluded(c,'missing_input');assert.equal(c.steps.length,0);assert.equal(c.finalFuel,null);}
  }
  const form=arcticPreset('normal');delete form.common.travelHours;assert.equal(calculate(form).inputStatus,'incomplete');
  const zero=arcticPreset('normal');zero.common.baseConsumption='0';zero.common.travelHours='0';zero.common.bunkerWorkHours='0';zero.common.arrivalDeadlineHours='0';
  for(const c of calculate(zero).candidates){assert.equal(c.status,'feasible');near(c.comparableSCI,0);}
});
check('leg multiplier and delay blanks hold all candidates; no silent zero',()=>{
  for(const field of ['consumptionMultiplier','delayHours'])for(const i of [0,1]){
    const form=arcticPreset('normal');form.legs[i][field]='';const r=calculate(form);assert.equal(r.inputStatus,'incomplete');assert.equal(r.eligibleCount,0);assert(r.missing.includes(`leg${i+1}.${field}`));
  }
});
check('invalid numeric and runtime values are excluded, even next to missing inputs',()=>{
  for(const field of COMMON_FIELDS)for(const bad of ['-1','NaN','Infinity','1e309']){
    const form=arcticPreset('normal');form.common[field]=bad;const r=calculate(form);assert.equal(r.inputStatus,'invalid');for(const c of r.candidates)excluded(c,'invalid_input');
  }
  for(const field of ['price','fx']){const f=arcticPreset('normal');f.common[field]='0';assert.equal(calculate(f).inputStatus,'invalid');}
  const out=arcticPreset('normal');out.common.initialFuel='100.01';assert.equal(calculate(out).inputStatus,'invalid');
  for(const bad of [true,false,'2',[],{}]){const input=parseArctic(arcticPreset('normal'));input.common.travelHours=bad;assert.equal(reviewArctic(input).inputStatus,'invalid');}
  const mixed=arcticPreset('normal');mixed.common.travelHours='';mixed.common.price='-1';assert.equal(calculate(mixed).inputStatus,'invalid');
  const input=parseArctic(arcticPreset('normal'));input.legs[0].supply='garbage';assert.equal(reviewArctic(input).inputStatus,'invalid');
});
check('derived arithmetic overflow is excluded and cannot be ranked',()=>{
  const scenarios=[f=>{f.common.price='1e308';f.common.fx='1e308';},f=>{f.common.travelHours='1e308';},f=>{f.common.baseConsumption='1e308';f.legs[0].consumptionMultiplier='1e308';}];
  for(const mutate of scenarios){const form=arcticPreset('normal');mutate(form);for(const c of calculate(form).candidates)excluded(c,'arithmetic');}
});
check('preset changes preserve common conditions but independently reset the leg assumptions',()=>{
  const a=arcticPreset('normal');a.common.initialFuel='42';a.legs[0].delayHours='99';
  const b=arcticPreset('delay-fuel',a.common);assert.equal(b.common.initialFuel,'42');assert.equal(b.legs[0].delayHours,'6');
  b.common.initialFuel='12';b.legs[0].delayHours='8';assert.equal(a.common.initialFuel,'42');assert.equal(a.legs[0].delayHours,'99');
  assert.equal(arcticPreset('normal').common.initialFuel,'30');
});
check('JSON export snapshots exact raw edits, unknown values, constraints and provenance',()=>{
  const form=arcticPreset('supply-unavailable');form.legs[1].delayHours='';
  const payload=arcticExport(form,'2026-10-13T10:00:00Z'),saved=plain(payload);
  assert.equal(saved.reviewVersion,ARCTIC_VERSION);assert.equal(saved.implementationBaseRevision,ARCTIC_BASE_REVISION);
  assert.equal(saved.provenance.usesSavedReplay,false);assert.equal(saved.provenance.usesDQN,false);assert.equal(saved.provenance.realPortOrIceData,false);
  assert.equal(saved.provenance.modifiedFromDefaultPreset,true);assert.equal(saved.rawInputs.legs[1].delayHours,'');assert.equal(saved.inputs.legs[1].delayHours,null);assert.equal(saved.result.eligibleCount,0);
  form.common.initialFuel='90';assert.equal(payload.rawInputs.common.initialFuel,'30');
  const normal=arcticExport(arcticPreset('normal'),'fixed');assert.equal(normal.provenance.modifiedFromDefaultPreset,false);near(normal.result.candidates[1].inventoryAdjustedSCI,65000);
});
check('deterministic randomized conservation, capacity, feasibility, uniform valuation and immutability',()=>{
  let seed=73;const random=()=>((seed=(1664525*seed+1013904223)>>>0)/2**32);
  for(let n=0;n<2000;n++){
    const form=arcticPreset('normal');form.common.initialFuel=String(random()*100);form.common.baseConsumption=String(random()*20);
    form.common.price=String(1+random()*1000);form.common.fx=String(1+random()*2000);form.common.travelHours=String(random()*24);form.common.bunkerWorkHours=String(random()*8);form.common.arrivalDeadlineHours=String(random()*100);
    for(const leg of form.legs){leg.consumptionMultiplier=String(random()*3);leg.delayHours=String(random()*12);leg.supply=['available','unavailable','unknown'][Math.floor(random()*3)];}
    const input=parseArctic(form),before=JSON.stringify(input),r=reviewArctic(input);assert.equal(JSON.stringify(input),before);
    for(const c of r.candidates){randomizedCandidates++;
      for(const step of c.steps){if(step.amount!==null){assert(step.amount>=0&&step.amount<=.9);assert(step.departureFuel<=1+1e-9);near(step.openingFuel+step.amount,step.departureFuel);near(step.departureFuel-step.consumption,step.arrivalFuel);}}
      if(c.steps.some(step=>step.arrivalFuel!==null&&step.arrivalFuel<0)){for(const key of ['finalFuel','arrivalHours','purchaseSCI','purchasedFuel','consumedFuel','inventoryAdjustedSCI','comparableSCI','rank'])assert.equal(c[key],null);}
      if(c.finalFuel!==null){near(input.common.initialFuel+c.purchasedFuel-c.consumedFuel,c.finalFuel);near(c.purchaseSCI,c.purchasedFuel*r.unitValue);near(c.inventoryAdjustedSCI,c.consumedFuel*r.unitValue);}
      if(c.status==='feasible'){assert.equal(c.steps.length,2);assert(c.steps.every(s=>s.arrivalFuel>=.15-1e-9));assert(c.arrivalHours<=input.common.arrivalDeadlineHours);assert.equal(c.reasons.length,0);assert.equal(c.rank,1);}
      else {assert.equal(c.rank,null);assert.equal(c.comparableSCI,null);}
    }
  }
});
for(const lang of ['ko','en'])check(`${lang} real React static markup, accessible fields, independent synthetic warnings`,()=>{
  language=lang;const html=renderToStaticMarkup(createElement(component));
  assert.equal((html.match(/data-candidate=/g)||[]).length,4);assert.equal((html.match(/<input /g)||[]).length,11);assert.equal((html.match(/<select /g)||[]).length,2);
  for(const field of COMMON_FIELDS)assert(html.includes(`for="arctic-${field}"`));
  assert(html.includes(lang==='en'?'4/4 candidates pass':'4개 후보 중 4개'));assert(html.includes('65,000'));assert(html.includes('DQN'));assert(html.includes('Polar Code'));
  assert(html.includes(lang==='en'?'No actual Arctic ports':'실제 북극 항만'));assert(html.includes(lang==='en'?'Export Arctic scenario JSON':'북극 합성 검토 JSON 저장'));
});
if(failures.length){for(const {name,error}of failures)console.error(`FAIL: ${name}\n${error.stack}`);process.exitCode=1;}
console.log(JSON.stringify({checks,passed:checks-failures.length,failed:failures.length,randomizedCandidates,defaultEligibility:[4,2,1],staticMarkup:'KO/EN; not browser interaction'}));
