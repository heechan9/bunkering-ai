import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {createRequire} from 'node:module';
const load=createRequire(import.meta.url);
const React=load('react');
const {renderToStaticMarkup}=load('react-dom/server');
const summary=JSON.parse(fs.readFileSync('lib/matched-safety-report.json','utf8'));
const full=JSON.parse(fs.readFileSync('public/data/matched-safety-report.json','utf8'));
assert.equal(summary.row_count,400);
assert.equal(summary.matched_cases_per_policy,100);
assert.equal(summary.training_seed_recorded,42);
assert.equal(summary.confidence_interval,null);
assert.equal(summary.p_value,null);
assert.equal(full.comparisons.length,6);
for(let i=0;i<full.comparisons.length;i++){
 const {pairs,...rest}=full.comparisons[i];
 assert.deepEqual(rest,summary.comparisons[i]);
 assert.equal(pairs.length,100);
 assert.equal(Object.values(rest.safety_counts).reduce((a,b)=>a+b,0),100);
 assert.equal(pairs.filter(p=>p.inventory_adjusted_sci_difference_b_minus_a!==null).length,rest.safety_counts.both_safe);
 if(rest.safety_counts.both_safe===0)assert.equal(rest.cost_difference_b_minus_a,null);
}
const code=ts.transpileModule(fs.readFileSync('components/ocean/MatchedSafetyAudit.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
for(const lang of ['ko','en']){
 const exports={};
 vm.runInNewContext(code,{exports,require:p=>p==='@/lib/locale'?{useLocale:()=>({lang})}:p==='@/lib/matched-safety-report.json'?summary:load(p)});
 const html=renderToStaticMarkup(React.createElement(exports.default));
 assert(html.includes('400'));
 assert(html.includes('700'));
 assert(html.includes('null'));
 assert(html.includes('matched-safety-heading'));
 assert.equal((html.match(/<li /g)||[]).length,6);
 assert(html.includes('/data/matched-safety-report.json'));
 assert(html.includes(lang==='en'?'Post-policy':'정책 결과로'));
}
assert(fs.readFileSync('app/page.tsx','utf8').includes('<MatchedSafetyAudit/>'));
console.log('PASS: 6 matched comparisons, all 600 pair records, null guards, archive/replay scope and both localized rendered panels.');
