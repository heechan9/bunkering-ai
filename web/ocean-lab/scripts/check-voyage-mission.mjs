import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),model={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/voyage-mission.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:model});
const {calculateMission:calc,missionFrame:frame,initialMission:base}=model;
const normal=calc(base);assert(normal.feasible);assert.equal(normal.total,28000);assert.equal(normal.terminal,10);assert.equal(frame(normal,2).fuel,10);assert.equal(frame(normal,2).spent,12000);assert.equal(frame(normal,4).spent,28000);assert.equal(frame(normal,4).progress,1);
const upfront=calc({...base,quantities:[60,0]});assert(upfront.feasible);assert.equal(upfront.total,36000);
const spike=calc({...base,prices:[600,900]});assert.equal(spike.total,48000);assert.equal(calc({...base,prices:[600,900],quantities:[60,0]}).total,36000);
const outage=calc({...base,supplyB:false});assert(!outage.feasible);assert.equal(outage.total,12000);assert.equal(outage.rows[1].delivered,0);assert.equal(outage.rows[1].consumed,10);assert.equal(outage.terminal,null);assert.equal(frame(outage,4).progress,.625);assert.equal(frame(outage,4).fuel,0);assert(calc({...base,supplyB:false,quantities:[60,0]}).feasible);
const unsafe=calc({...base,quantities:[19,41]});assert(unsafe.violations.includes('B:reserve'));assert.equal(unsafe.terminal,10);assert.equal(unsafe.comparableCost,null);
const stranded=calc({...base,quantities:[0,100]});assert.equal(stranded.rows[1].delivered,0);assert(stranded.rows[1].skipped);assert.equal(stranded.total,0);assert.equal(stranded.terminal,null);assert.equal(frame(stranded,4).progress,1/3);
const over=calc({...base,quantities:[100,0]});assert.equal(over.rows[0].delivered,80);assert(over.violations.includes('A:capacity'));assert.equal(over.total,48000);
for(const q of [NaN,Infinity,-1,101])assert(!calc({...base,quantities:[q,40]}).valid);
for(const p of [NaN,Infinity,-1,2001])assert(!calc({...base,prices:[600,p]}).valid);
for(const i of [-1,5,.5,NaN])assert.equal(frame(normal,i),null);
let checked=0;
for(const supplyB of [true,false])for(let a=0;a<=100;a++)for(let b=0;b<=100;b++){
 const input={...base,quantities:[a,b],supplyB},r=calc(input);assert.equal(JSON.stringify(r),JSON.stringify(calc(input)));
 let inventory=20,cost=0;
 r.rows.forEach(row=>{assert.equal(row.arrival,inventory);assert.equal(row.arrival+row.delivered-row.consumed,row.nextArrival);assert(row.departure<=100&&row.nextArrival>=0);assert(row.delivered<=row.requested);if(row.skipped)assert.equal(row.delivered+row.consumed+row.cost,0);cost+=row.cost;inventory=row.nextArrival});
 assert.equal(cost,r.total);assert.equal(r.comparableCost,r.feasible?r.total:null);
 if(r.feasible){assert(r.reached);assert.equal(r.terminal,10);assert(r.rows.every(row=>row.nextArrival>=10));}
 for(let stage=0;stage<5;stage++){const f=frame(r,stage);assert(f.fuel>=0&&f.fuel<=100);assert(f.progress>=0&&f.progress<=1);}
 checked++;
}
// Run the real React handlers without browser or WebGL claims.
let state=[],cursor=0,lang='ko';const component={};
const useState=initial=>{const i=cursor++;if(!(i in state))state[i]=initial;return[state[i],v=>state[i]=typeof v==='function'?v(state[i]):v]};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('app/voyage-lab/page.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,{exports:component,require:p=>p==='react'?{useState}:p==='@/lib/locale'?{LocaleProvider:({children})=>children,useLocale:()=>({lang,setLang:v=>lang=v})}:p==='@/lib/voyage-mission'?model:p==='./mission-scene'?{default:()=>null}:p.endsWith('.css')?{}:require(p)});
const elements=n=>n==null||typeof n!=='object'?[]:Array.isArray(n)?n.flatMap(elements):[n,...elements(n.props?.children)];
const text=n=>n==null?'':typeof n!=='object'?String(n):Array.isArray(n)?n.map(text).join(''):text(n.props?.children);
const render=()=>{cursor=0;return component.default().props.children.type()};
const click=(tree,label)=>{const b=elements(tree).find(n=>n.type==='button'&&text(n)===label);assert(b,label);assert.equal(b.props.type,'button');b.props.onClick()};
let tree=render();assert(text(tree).includes('$28,000'));click(tree,'5. C: 도착 확인');tree=render();assert.equal(state[1],4);
click(tree,'B 가격 급등');tree=render();assert.equal(state[1],4);assert(text(tree).includes('$48,000'));assert(text(tree).includes('$36,000'));
click(tree,'B 공급 중단');tree=render();assert(text(tree).includes('실패한 구매안'));assert(text(tree).includes('미도착'));
const apply=elements(tree).filter(n=>n.type==='button'&&text(n)==='이 구매안 적용');apply[1].props.onClick();tree=render();assert(text(tree).includes('모든 제약을 충족하는 구매안'));assert.deepEqual(Array.from(state[0].quantities),[60,0]);
click(tree,'기본');tree=render();elements(tree).find(n=>n.props?.id==='quantity-A').props.onChange({target:{value:'19'}});tree=render();assert(text(tree).includes('도착 안전잔량 10t 미달'));
click(tree,'English');tree=render();assert(!/[가-힣]/.test(text(tree).replace('한국어','')));assert(text(tree).includes('Failed plan'));
click(tree,'Normal');tree=render();assert(text(tree).includes('Plan passes all constraints'));assert(text(tree).includes('$28,000'));
assert.equal(elements(tree).filter(n=>n.type==='input'&&n.props.type==='range').length,4);
assert(fs.readFileSync('app/page.tsx','utf8').includes('href="/voyage-lab"'));
console.log(`PASS: ${checked} deterministic balance cases; normal/spike/outage/reserve/capacity/stranding, invalid inputs, same-object frames, actual UI reset/preset/compare/language handlers. Browser/WebGL verification is separate.`);
