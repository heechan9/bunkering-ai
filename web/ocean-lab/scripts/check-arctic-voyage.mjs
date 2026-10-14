import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
// Execute the production calculator and voyage component; map rendering is browser-tested separately.
const root=process.cwd();
const nodeRequire=createRequire(path.join(root,'package.json'));
const ts=nodeRequire('typescript'),React=nodeRequire('react'),{renderToStaticMarkup}=nodeRequire('react-dom/server');
const cache=new Map();let language='en';
function load(filename){
 const absolute=path.resolve(root,filename);if(cache.has(absolute))return cache.get(absolute).exports;
 const loaded={exports:{}};cache.set(absolute,loaded);
 const require=specifier=>{
  if(specifier.endsWith('.module.css'))return {__esModule:true,default:new Proxy({},{get:(_t,name)=>String(name)})};
  if(specifier==='@/lib/locale')return {useLocale:()=>({lang:language})};
  if(specifier==='./Geography')return {MapScene:()=>React.createElement('div',{'data-test-map':true}),MapLabelKey:()=>null};
  if(!specifier.startsWith('.')&&!specifier.startsWith('@/'))return nodeRequire(specifier);
  const resolved=specifier.startsWith('@/')?path.resolve(root,specifier.slice(2)):path.resolve(path.dirname(absolute),specifier);
  return load(path.extname(resolved)?resolved:['.ts','.tsx'].map(ext=>resolved+ext).find(fs.existsSync));
 };
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(absolute,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{module:loaded,exports:loaded.exports,require,structuredClone},{filename:absolute});return loaded.exports;
}
const {arcticPreset,parseArctic,reviewArctic}=load('lib/arctic-scenario.ts');
const {default:Component,arcticPlaybackLimit:limit,arcticVoyageFrame:frame}=load('components/ocean/ArcticVoyage.tsx');
const candidates=f=>reviewArctic(parseArctic(f)).candidates;
const near=(a,b)=>assert(Math.abs(a-b)<1e-8,`${a} != ${b}`);
let checks=0;
for(const preset of ['normal','delay-fuel','supply-unavailable'])for(const c of candidates(arcticPreset(preset))){
 assert.equal(limit(c),1);const start=frame(c,0),end=frame(c,1);near(start.fuel,.3);assert.equal(start.hours,0);near(end.fuel,c.finalFuel);near(end.hours,c.arrivalHours);near(end.position,1);assert.equal(end.phase,'arrived');
 const b=frame(c,.5);near(b.position,.5);near(b.fuel,c.steps[0].arrivalFuel);near(b.hours,c.steps[0].arrivalHours);
 for(const [i,at] of [[0,.1],[1,.6]]){const departure=frame(c,at);near(departure.fuel,c.steps[i].departureFuel);near(departure.hours,c.steps[i].departureHours);}checks++;
}
const finalLegExhaustion=arcticPreset('normal');finalLegExhaustion.common.baseConsumption='20';
const exhaustedCandidate=candidates(finalLegExhaustion).find(c=>c.id==='wait-wait');
const exhaustedFrame=frame(exhaustedCandidate,1);near(exhaustedFrame.hours,18);near(exhaustedFrame.fuel,0);near(exhaustedFrame.position,.75);assert.equal(exhaustedFrame.phase,'blocked');assert.equal(exhaustedCandidate.arrivalHours,null);assert.equal(exhaustedCandidate.finalFuel,null);checks++;
for(const supplyAt of [0,1]){const f=arcticPreset('normal');f.legs[supplyAt].supply='unknown';for(const c of candidates(f)){if(c.actions[supplyAt]){assert.equal(limit(c),supplyAt/2);const end=frame(c,1);assert.equal(end.phase,'blocked');assert.equal(end.position,supplyAt/2);assert(Number.isFinite(end.fuel));}else assert.equal(limit(c),1);checks++;}}
for(const value of ['','NaN','-1']){const f=arcticPreset('normal');f.common.baseConsumption=value;for(const c of candidates(f)){assert.equal(limit(c),0);for(const progress of [0,.3,.6,1]){const now=frame(c,progress);assert.equal(now.fuel,null);assert.equal(now.hours,null);assert.equal(now.position,0);assert.equal(now.phase,'blocked');}checks++;}}
for(const initial of [0,5,10,30])for(const burn of [5,10,20,50,100,1000,1e100]){const f=arcticPreset('normal');f.common.initialFuel=String(initial);f.common.baseConsumption=String(burn);for(const c of candidates(f)){const max=limit(c),end=frame(c,1);if(c.steps.some(s=>s.arrivalFuel<0)){assert(max<1);assert.equal(c.arrivalHours,null);assert.equal(c.finalFuel,null);assert.equal(c.purchaseSCI,null);assert.equal(end.phase,'blocked');assert(end.fuel>=0);assert(end.fuel<1e-8);assert(end.position<1);}for(let n=0;n<=100;n++){const now=frame(c,n/100);assert(now.position>=0&&now.position<=1);assert(now.fuel>=0);assert(now.hours>=0);assert(Number.isFinite(now.fuel));assert(Number.isFinite(now.hours));}checks++;}}
for(const lang of ['ko','en']){language=lang;for(const preset of ['normal','delay-fuel','supply-unavailable']){const html=renderToStaticMarkup(React.createElement(Component,{form:arcticPreset(preset),onFormChange:()=>{},onCompare:()=>{}}));assert(html.includes('data-arctic-voyage'));assert(html.includes('data-arctic-fuel'));assert(html.includes('data-arctic-hours'));assert(html.includes('DQN'));assert(html.includes('UNKNOWN'));assert(html.includes('type="range"'));assert(html.includes('voyage-arctic-leg-1-supply'));
 assert(html.includes('class="workspace '),'Arctic voyage should share the simulator workspace');
 assert(html.includes('class="panel '),'Arctic controls should share the simulator side panel');
 assert(html.indexOf('class="controls"')>html.indexOf('<aside'),'Presets and A/B choices must be in the side panel');
 assert(!/<details\b[^>]*\bopen(?:[ =]|>)/.test(html),'Advanced voyage inputs and caveats must start collapsed');
 assert(html.includes(lang==='en'?'Fullscreen Arctic map':'북극 지도 전체 화면'));
 checks+=6;}}
for(const actions of [[false,false],[false,true],[true,false],[true,true]]){
 const html=renderToStaticMarkup(React.createElement(Component,{form:arcticPreset('normal'),onFormChange:()=>{},onCompare:()=>{},actions,onActionsChange:()=>{}}));
 assert(html.includes(`data-arctic-candidate="${actions.map(buy=>buy?'buy':'wait').join('-')}"`));checks++;
}
const Review=load('components/ocean/ArcticScenarioReview.tsx').default;
for(const lang of ['ko','en']){language=lang;const form=arcticPreset('supply-unavailable');form.common.baseConsumption='6';const html=renderToStaticMarkup(React.createElement(Review,{form,onFormChange:()=>{},integrated:true}));assert(html.includes('value="6"'));assert(html.includes(lang==='en'?'Changes carry between voyage and comparison tabs':'변경값은 운항·비교 탭 사이에 유지'));assert(!html.includes(lang==='en'?'Edited values persist within this panel only':'편집값은 이 패널 안에서만 유지'));
 assert(!/<details\b[^>]*\bopen(?:[ =]|>)/.test(html),'Review inputs and caveats must start collapsed');
 assert((html.match(/<details\b/g)??[]).length>=3,'Common inputs, leg inputs, and caveats need distinct disclosures');
 checks+=3;}
console.log(JSON.stringify({checks,passed:checks,coverage:'Calculator-driven voyage frames, preset endpoint sync, UNKNOWN supply, invalid/missing input, exhausted leg stopping, shared simulator layout, collapsed advanced inputs, KO/EN SSR'}));
