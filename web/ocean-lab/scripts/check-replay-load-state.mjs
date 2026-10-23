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
 const data=[],failures=[];const context={fetch:fetcher,setData:v=>data.push(v),setFailure:v=>failures.push(v),normalizeReplay:types.normalizeReplay,AbortController};
 const code=ts.transpileModule(`const effect=${effect}; effect;`,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText;
 const cleanup=vm.runInNewContext(code,context)();if(abort)cleanup();
 await new Promise(r=>setTimeout(r,0));return {data,failures};
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
// Every literal translated by this component must have an English entry.
const en=JSON.parse(fs.readFileSync('lib/en.json','utf8'));
for(const match of fs.readFileSync('components/ocean/ReplayLoadNotice.tsx','utf8').matchAll(/t\('([^']+)'\)/g))assert(en[match[1]],match[1]);
