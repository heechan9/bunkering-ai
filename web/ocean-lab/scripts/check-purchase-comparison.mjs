import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const exports={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/purchase-comparison.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports});
const {purchaseTransition,comparePurchases,decisionSnapshot,readingAge}=exports;
const near=(a,b)=>assert(Math.abs(a-b)<=1e-9*Math.max(1,Math.abs(b)),`${a} != ${b}`);
const fixtures=JSON.parse(fs.readFileSync('scripts/fixtures/purchase-reference.json','utf8'));
for(const c of fixtures.cases){let f=c.fuel;for(let j=0;j<c.steps.length;j++){const got=purchaseTransition(f,c.price,c.fx,!!c.actions[j]);for(const k of ['fuelAfter','amount','cost','unmet'])near(got[k],c.steps[j][k]);assert.equal(got.depleted,c.steps[j].depleted);f=got.fuelAfter;}}
for(const c of fixtures.cases){
 const r=v=>({value:v,step:0,kind:'record',timestamp:null});
 const s={step:0,remaining:30,fuel:r(c.fuel),price:r(c.price),fx:r(c.fx),previousPrice:r(c.price)};
 const got=comparePurchases(s).find(x=>JSON.stringify(x.actions.map(Number))===JSON.stringify(c.actions));
 assert.equal(got.steps.length,c.steps.length);
 near(got.cost,c.steps.reduce((a,r)=>a+r.cost,0));near(got.amount,c.steps.reduce((a,r)=>a+r.amount,0));near(got.finalFuel,c.steps.at(-1).fuelAfter);
}
const replay=JSON.parse(fs.readFileSync('public/data/replay.json','utf8'));let decisions=0;
const before=JSON.stringify(replay);
for(const traces of Object.values(replay.runs))for(const trace of Object.values(traces)){
 for(let i=0;i<trace.length;i++){
  const snapshot=decisionSnapshot(trace,i),candidates=comparePurchases(snapshot);assert.equal(candidates.length,i===29?2:4);
  // Replay accounting checks are independent of the candidate implementation.
  const actual=trace[i],got=purchaseTransition(i?trace[i-1][0]:1,actual[6],actual[7],actual[1]>1e-6);
  near(got.fuelAfter,actual[0]);near(got.amount,actual[1]);near(got.cost,actual[3]);
  const guarded=new Proxy(trace,{get(target,k){if(/^\d+$/.test(String(k))&&Number(k)>i)throw Error('Future row accessed');return target[k]}});
  assert.equal(JSON.stringify(decisionSnapshot(guarded,i)),JSON.stringify(snapshot));
  assert(candidates.every(c=>c.steps.length<=Math.min(2,30-i)));decisions++;
 }
 assert.equal(decisionSnapshot(trace,trace.length),null);
}
assert.equal(before,JSON.stringify(replay));
const trace=replay.runs.dqn_42['42'];const s=decisionSnapshot(trace,10);
for(const value of [null,NaN,Infinity,-1]){const bad={...s,price:{...s.price,value}};assert.equal(comparePurchases(bad).length,0)}
assert.equal(comparePurchases({...s,price:{...s.price,value:0}}).length,0);
assert.equal(comparePurchases({...s,price:{...s.price,step:9}}).length,0);
assert.equal(readingAge(s.previousPrice,10),1);
const missing=decisionSnapshot([[.95,0,.05,0,0]],0);assert.equal(missing.price.kind,'missing');assert.equal(comparePurchases(missing).length,0);
const zero={...s,fuel:{...s.fuel,value:0}};assert.notEqual(comparePurchases(zero).length,0,'Zero is a value, not missing');
const stopped=comparePurchases(zero)[1];assert.equal(stopped.steps.length,1);assert(stopped.stopped);
const boundary=purchaseTransition(.2,500,1300,false);assert.equal(boundary.reserveViolation,false);
assert.throws(()=>purchaseTransition(2,500,1300,false));
console.log(JSON.stringify({reference_paths:fixtures.cases.length,replay_decisions_checked:decisions,future_row_access:'blocked',missing_stale_invalid_inputs:'held',zero:'preserved',early_stop:'checked',baseline_data:'unchanged'}));
