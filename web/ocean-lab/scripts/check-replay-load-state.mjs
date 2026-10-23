import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
// Integration contract: status must be reachable before replay can be started.
const source=fs.readFileSync('app/page.tsx','utf8');
function assertReachableNotice(candidate){
 const tree=ts.createSourceFile('page.tsx',candidate,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 let notices=0;
 function walk(node){
  if(ts.isJsxSelfClosingElement(node)&&node.tagName.getText(tree)==='ReplayLoadNotice'){
   notices++;
   for(let p=node.parent;p;p=p.parent){
    assert(!ts.isConditionalExpression(p),'Load notice must not be conditionally reachable');
    if(ts.isBinaryExpression(p)) assert(![ts.SyntaxKind.AmpersandAmpersandToken,ts.SyntaxKind.BarBarToken,ts.SyntaxKind.QuestionQuestionToken].includes(p.operatorToken.kind),'Load notice must not depend on a conditional gate');
    if(ts.isJsxElement(p)) assert.notEqual(p.openingElement.tagName.getText(tree),'TabsContent','Load notice must remain outside tab panels');
   }
  }
  ts.forEachChild(node,walk);
 }
 walk(tree);
 assert.equal(notices,1,'One always-reachable replay load notice');
 return tree;
}
const ast=assertReachableNotice(source);
// Mutation regressions: alternate syntax must not restore the original unreachable-state bug.
const noticeMatch=source.match(/<ReplayLoadNotice\b[^]*?\/>/);
assert(noticeMatch,'Actual notice required for mutation regressions');
for(const mutate of [n=>`{started?${n}:null}`,n=>`{!started?null:${n}}`,n=>`{started&&${n}}`,n=>`{tab==='explore'&&${n}}`,n=>`<TabsContent value="explore">${n}</TabsContent>`]){
 assert.throws(()=>assertReachableNotice(source.replace(noticeMatch[0],mutate(noticeMatch[0]))),/Load notice/);
}
assert(source.includes('if(!a.signal.aborted)setData('),'Discard stale success');
assert(source.includes('if(!a.signal.aborted)setFailure(true)'),'Discard stale failure');
assert(source.includes('},[loadAttempt])'),'Language changes must not refetch records');
assert(source.includes('setFailure(false);setLoadAttempt(n=>n+1)'),'Retry clears error before loading');
console.log('PASS: reachable status, retry reset, cancellation guards and locale-independent loading');
// Execute the real presentational component, without a browser/network.
const {createRequire}=await import('node:module');
const vm=await import('node:vm');
const require=createRequire(import.meta.url);
const exports={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('components/ocean/ReplayLoadNotice.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,{exports,require});
const Notice=exports.default;
const t=s=>s;
const loading=Notice({ready:false,failed:false,retry(){},t});
assert.equal(loading.props.role,'status');
assert.match(loading.props.children,/불러오는 중/);
let retried=0;
const failed=Notice({ready:false,failed:true,retry(){retried++},t});
assert.equal(failed.props.role,'alert');
const button=failed.props.children.find(c=>c?.type==='button');
assert.equal(button.props.type,'button');button.props.onClick();assert.equal(retried,1);
assert.equal(Notice({ready:true,failed:false,retry(){},t}),null);
assert.equal(Notice({ready:true,failed:true,retry(){},t}),null);
console.log('PASS: loading status, error alert, retry action and successful dismissal');
// Execute the actual page fetch effect with deterministic HTTP responses.
let effect;
function findEffect(n){if(ts.isCallExpression(n)&&n.expression.getText(ast)==='useEffect'&&n.arguments[1]?.getText(ast)==='[loadAttempt]')effect=n.arguments[0].getText(ast);ts.forEachChild(n,findEffect)}
findEffect(ast);assert(effect);
const raw=JSON.parse(fs.readFileSync('public/data/replay.json','utf8'));
const summary=JSON.parse(fs.readFileSync('public/data/research-summary.json','utf8'));
const types={};vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/ocean-types.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:types});
async function runEffect(fetcher,abort=false){
 const data=[],failures=[];let requests=0;const context={fetch:(...args)=>{requests++;return fetcher(...args)},setData:v=>data.push(v),setFailure:v=>failures.push(v),normalizeReplay:types.normalizeReplay,AbortController};
 const code=ts.transpileModule(`const effect=${effect}; effect;`,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText;
 const cleanup=vm.runInNewContext(code,context)();if(abort)cleanup();
 await new Promise(r=>setTimeout(r,0));return {data,failures,requests};
}
const success=url=>Promise.resolve({ok:true,json:async()=>url.includes('research-summary')?summary:raw});
const ok=await runEffect(success);assert.equal(ok.data.length,1);assert.equal(ok.failures.length,0);assert.equal(ok.data[0].runs,raw.runs);
const http=await runEffect(async()=>({ok:false}));assert.equal(http.failures.length,1);assert.equal(http.data.length,0);
const network=await runEffect(async()=>{throw Error('network')});assert.equal(network.failures.length,1);
const json=await runEffect(async()=>({ok:true,json:async()=>{throw SyntaxError('json')}}));assert.equal(json.failures.length,1);
const cancelled=await runEffect(success,true);assert.equal(cancelled.data.length+cancelled.failures.length,0);
const cancelledError=await runEffect(async()=>{throw Error('late failure')},true);assert.equal(cancelledError.data.length+cancelledError.failures.length,0);
const retry=await runEffect(success);assert.equal(retry.data.length,1);
console.log('PASS: real fetch effect handles success, HTTP/network/JSON errors, retry and cancelled success/error without changing replay data');
// Valid JSON is not necessarily valid replay data. Reject it before setData.
const invalidPayloads = [
 ['missing runs', d=>{delete d.runs}],
 ['missing run', d=>{delete d.runs.dqn_42}],
 ['missing case', d=>{delete d.runs.dqn_42['42']}],
 ['empty trace', d=>{d.runs.dqn_42['42']=[]}],
 ['non-array trace', d=>{d.runs.dqn_42['42']={}}],
 ['short row', d=>{d.runs.dqn_42['42'][0].pop()}],
 ['nonnumeric trace value', d=>{d.runs.dqn_42['42'][0][0]='0.95'}],
 ['null trace value', d=>{d.runs.dqn_42['42'][0][0]=null}],
 ['infinite trace value', d=>{d.runs.dqn_42['42'][0][0]=Infinity}],
 ['wrong column order', d=>{[d.columns[0],d.columns[1]]=[d.columns[1],d.columns[0]]}],
 ['wrong schema', d=>{d.schema='unknown'}],
 ['wrong horizon', d=>{d.maxSteps=31}],
 ['missing caseSeeds', d=>{delete d.caseSeeds}],
 ['duplicate case seed', d=>{d.caseSeeds[0]=43}],
 ['fractional case seed', d=>{d.caseSeeds[0]=42.5}],
 ['missing summary', (_d,s)=>{delete s.summary}],
 ['empty summary', (_d,s)=>{s.summary=[]}],
 ['null summary row', (_d,s)=>{s.summary[0]=null}],
 ['missing metric', (_d,s)=>{delete s.summary[0].episode_sci_mean}],
 ['blank metric', (_d,s)=>{s.summary[0].episode_sci_mean='  '}],
 ['null metric', (_d,s)=>{s.summary[0].episode_sci_mean=null}],
 ['boolean metric', (_d,s)=>{s.summary[0].episode_sci_mean=false}],
 ['array metric', (_d,s)=>{s.summary[0].episode_sci_mean=[]}],
 ['NaN metric', (_d,s)=>{s.summary[0].episode_sci_mean=NaN}],
 ['infinite metric', (_d,s)=>{s.summary[0].episode_sci_mean='1e309'}],
 ['out-of-range rate', (_d,s)=>{s.summary[0].success_rate='1.1'}],
 ['negative cost', (_d,s)=>{s.summary[0].episode_sci_mean=-1}],
 ['missing cases', (_d,s)=>{delete s.summary[0].cases}],
 ['blank cases', (_d,s)=>{s.summary[0].cases=''}],
 ['wrong cases', (_d,s)=>{s.summary[0].cases=99}],
 ['duplicate summary identity', (_d,s)=>{s.summary[1]=structuredClone(s.summary[0])}],
 ['unknown policy', (_d,s)=>{s.summary[0].policy='unknown'}],
 ['missing checkpoint', (_d,s)=>{delete s.summary[0].checkpoint}],
 ['relabeled checkpoint', (_d,s)=>{s.summary[0].policy='dqn_42';s.summary[0].checkpoint='not_applicable'}],
];
for (const [label, mutate] of invalidPayloads) {
 const d=structuredClone(raw),s=structuredClone(summary);mutate(d,s);
 const result=await runEffect(async url=>({ok:true,json:async()=>url.includes('research-summary')?s:d}));
 assert.equal(result.data.length,0,`${label}: must not publish unverified data`);
 assert.equal(result.failures.length,1,`${label}: must reach the existing load error`);
 assert.equal(result.requests,2,`${label}: no automatic retry`);
}
// The current corpus has 20-step early exhaustion, 11 columns and negative rewards.
assert(Object.values(raw.runs).some(run=>Object.values(run).some(trace=>trace.length===20)));
assert(Object.values(raw.runs).some(run=>Object.values(run).some(trace=>trace.some(row=>row[4]<0))));
assert.deepEqual(ok.data[0].runs,raw.runs);
const numericSummary=structuredClone(summary);
for (const row of numericSummary.summary) for (const key of ['cases',...types.metricKeys]) row[key]=Number(row[key]);
const numeric=await runEffect(async url=>({ok:true,json:async()=>url.includes('research-summary')?numericSummary:raw}));
assert.equal(numeric.data.length,1);assert.equal(numeric.failures.length,0);
assert.deepEqual(JSON.parse(JSON.stringify(numeric.data[0].summary)),JSON.parse(JSON.stringify(ok.data[0].summary)));
for (const zero of [0,'0','0.0','0e10']) {
 const s=structuredClone(summary);s.summary.find(row=>row.policy==='fixed_fueling').episode_sci_mean=zero;
 const result=await runEffect(async url=>({ok:true,json:async()=>url.includes('research-summary')?s:raw}));
 assert.equal(result.data.length,1);assert.equal(result.failures.length,0);
 assert.equal(result.data[0].summary.find(row=>row.policy==='fixed_fueling').episode_sci_mean,0);
}
console.log(`PASS: ${invalidPayloads.length} malformed payloads fail closed; real early-stop/negative-reward records and numeric/string summaries are preserved`);
// Every literal translated by this component must have an English entry.
const en=JSON.parse(fs.readFileSync('lib/en.json','utf8'));
for(const match of fs.readFileSync('components/ocean/ReplayLoadNotice.tsx','utf8').matchAll(/t\('([^']+)'\)/g))assert(en[match[1]],match[1]);
