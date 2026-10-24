import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {createRequire} from 'node:module';
const nativeRequire=createRequire(import.meta.url);
const fixture=JSON.parse(fs.readFileSync('public/data/u01-procurement.json','utf8'));
const moduleSource=fs.readFileSync('lib/u01-procurement.ts','utf8');
const output={};
vm.runInNewContext(ts.transpileModule(moduleSource,{compilerOptions:{module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,{exports:output,require:()=>fixture});
const {checkU01,isU01Quantity,u01Step}=output;
assert(isU01Quantity('20'));assert(!isU01Quantity(''));assert(!isU01Quantity('-1'));
const good=checkU01(['20','40']);
assert(good.feasible);assert.equal(good.comparableCost,28000);assert.equal(good.terminal,10);
assert.deepEqual(JSON.parse(JSON.stringify(good.rows.map(r=>r.nextArrival))),[10,10]);
for(const saved of fixture.methods){
 const actual=checkU01(saved.purchases_t.map(String));assert(actual.feasible);
 assert.equal(actual.comparableCost,saved.total_usd);assert.equal(actual.terminal,saved.terminal_t);
 actual.rows.forEach((r,i)=>{const expected=saved.ledger[i];assert.equal(r.arrival,expected.I_before_t);assert.equal(r.departure,expected.D_after_t);assert.equal(r.nextArrival,expected.I_next_t);assert.equal(r.cost,expected.total_usd)});
}
const bad=checkU01(['19','41']);assert(bad.validInput&&!bad.feasible);assert.equal(bad.rows[0].nextArrival,9);assert.equal(bad.terminal,10);assert.equal(bad.rawCost,27800);assert.equal(bad.comparableCost,null);assert(bad.violations.some(v=>v.port==='B'&&v.kind==='reserve'));
for(const text of ['', ' ', '-1', 'NaN','Infinity','1e2','0x14','20x','20,0','20.0001','101','9'.repeat(400)]){
 const r=checkU01([text,'40']);assert(!r.validInput);assert.equal(r.rows.length,0);assert.equal(r.rawCost,null);assert.equal(r.comparableCost,null);assert.equal(u01Step(r,0),null);
}
assert(checkU01(['20.000','40.000']).feasible);
for(const [values,kind] of [[['81','0'],'capacity'],[['20','39'],'terminal'],[['0','60'],'reserve']])assert(checkU01(values).violations.some(v=>v.kind===kind));
assert.equal(u01Step(good,0).spent,0);assert.equal(u01Step(good,1).spent,12000);assert.equal(u01Step(good,2).spent,28000);assert.equal(u01Step(good,2).fuel,10);
for(const step of [-1,3,0.5,NaN])assert.equal(u01Step(good,step),null);
assert(!/purchase-comparison|scenario-review|ocean-types/.test(moduleSource));

// Run the actual component with a minimal hook scheduler: integration of handlers
// and rendered states, not browser keyboard navigation or mobile layout E2E.
const component=fs.readFileSync('app/procurement/page.tsx','utf8');
let lang='ko',state=[],cursor=0;
const componentExports={};
const useState=initial=>{const i=cursor++;if(!(i in state))state[i]=initial;return [state[i],v=>{state[i]=typeof v==='function'?v(state[i]):v}]};
vm.runInNewContext(ts.transpileModule(component,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText,{exports:componentExports,require:p=>{
 if(p==='react')return {useState};
 if(p==='@/lib/locale')return {LocaleProvider:({children})=>children,useLocale:()=>({lang,setLang:v=>{lang=v}})};
 if(p==='@/lib/u01-procurement')return output;
 if(p.endsWith('.css'))return {};
 return nativeRequire(p);
}});
function render(){cursor=0;return componentExports.default().props.children.type()}
function elements(node){if(node==null||typeof node!=='object')return [];if(Array.isArray(node))return node.flatMap(elements);return [node,...elements(node.props?.children)]}
function text(n){if(n==null)return '';if(typeof n!=='object')return String(n);if(Array.isArray(n))return n.map(text).join('');return text(n.props?.children)}
function button(tree,label){const b=elements(tree).find(n=>n.type==='button'&&text(n)===label);assert(b,label);assert.equal(b.props.type,'button');return b}
let tree=render();assert(text(tree).includes('28,000'));assert.equal(elements(tree).filter(n=>n.type==='input').length,2);
assert.equal(button(tree,'이전 단계').props['aria-disabled'],true);assert.equal(button(tree,'이전 단계').props.disabled,undefined);button(tree,'이전 단계').props.onClick();tree=render();assert.equal(state[1],0);
button(tree,'다음 단계').props.onClick();tree=render();assert(text(tree).includes('누적 구매지출: $12,000'));assert(elements(tree).some(n=>n.props?.['aria-current']==='step'&&text(n).includes('B 도착')));
button(tree,'위반 예시 19 / 41').props.onClick();tree=render();assert(text(tree).includes('앞선 위반은 사라지지'));assert(!text(tree).includes('모든 제약 충족.'));
button(tree,'다음 단계').props.onClick();tree=render();button(tree,'다음 단계').props.onClick();tree=render();assert(text(tree).includes('급유 전 도착 잔량 10t 미만'));
assert.equal(button(tree,'다음 단계').props['aria-disabled'],true);assert.equal(button(tree,'다음 단계').props.disabled,undefined);button(tree,'다음 단계').props.onClick();tree=render();assert.equal(state[1],2);
elements(tree).find(n=>n.type==='input').props.onChange({target:{value:''}});tree=render();
let inputs=elements(tree).filter(n=>n.type==='input');assert.equal(inputs[0].props['aria-invalid'],true);assert.equal(inputs[1].props['aria-invalid'],false);assert(inputs[0].props['aria-describedby'].includes('u01-input-error'));assert(!inputs[1].props['aria-describedby'].includes('u01-input-error'));
inputs[0].props.onChange({target:{value:'20'}});tree=render();elements(tree).filter(n=>n.type==='input')[1].props.onChange({target:{value:'NaN'}});tree=render();inputs=elements(tree).filter(n=>n.type==='input');assert.equal(inputs[0].props['aria-invalid'],false);assert.equal(inputs[1].props['aria-invalid'],true);
assert(elements(tree).some(n=>n.props?.role==='alert'));assert(!elements(tree).some(n=>n.type==='table'&&text(n).includes('전체 두 구간')));
button(tree,'U01 초기화').props.onClick();tree=render();assert(text(tree).includes('모든 제약 충족. 총비용 $28,000'));assert.equal(state[1],0);assert.equal(state[0].join(','),'20,40');
button(tree,'English').props.onClick();tree=render();assert(!/[가-힣]/.test(text(tree).replace('한국어','')));assert(text(tree).includes('Illustrative synthetic example'));assert(text(tree).includes('Total $28,000'));
elements(tree).filter(n=>n.type==='input')[1].props.onChange({target:{value:'39'}});tree=render();assert(text(tree).includes('Destination arrival inventory below 10 t'));assert(!text(tree).includes('BEFORE refueling'));
button(tree,'한국어').props.onClick();tree=render();assert(text(tree).includes('종점 도착 잔량 10t 미만'));assert(!text(tree).includes('급유 전 도착 잔량'));
button(tree,'English').props.onClick();tree=render();
const {renderToStaticMarkup}=nativeRequire('react-dom/server');
const enMarkup=renderToStaticMarkup(tree);assert(enMarkup.includes('aria-describedby="u01-input-help"'));assert(enMarkup.includes('scope="col"'));assert(enMarkup.includes('tabindex="0"'));
assert.equal(elements(tree).filter(n=>n.type==='label').length,2);
assert(fs.readFileSync('app/page.tsx','utf8').includes('href="/procurement"'));
const css=fs.readFileSync('app/procurement/procurement.css','utf8');
assert(css.includes('@media(max-width:600px)'));assert(css.includes('overflow-x:auto'));assert(css.includes('min-height:44px'));assert(css.includes('button[aria-disabled=true]'));assert(css.includes(':focus-visible'));
console.log('PASS: four Python fixtures, reserve/terminal/capacity failures, invalid inputs, source isolation, step/change/reset handlers, KO/EN render and native accessible control contracts. Browser/mobile E2E is separate.');
