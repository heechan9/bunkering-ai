import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {createRequire} from 'node:module';
const loadModule=createRequire(import.meta.url);
const translations=JSON.parse(fs.readFileSync('lib/en.json','utf8'));
function compile(file){const exports={};vm.runInNewContext(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{exports,require:p=>p==='./en.json'?translations:loadModule(p)});return exports;}
const {translate}=compile('lib/locale.tsx');
for(const [ko,en]of Object.entries(translations)){assert(en.length>0);assert(!/[가-힣]/.test(en));assert.deepEqual((ko.match(/\{\d+\}/g)||[]).sort(),(en.match(/\{\d+\}/g)||[]).sort());assert.equal(translate('ko',ko),ko.replace(/\{\d+\}/g,''));}
assert.equal(translate('en','{0}/30 단계 · 연료 {1}{2}',17,'65.0',''),'17/30 steps · Fuel 65.0');
assert.equal(translate('ko','{0}/30 단계 · 연료 {1}{2}',17,'65.0',''),'17/30 단계 · 연료 65.0');
for(const file of ['app/page.tsx','components/ocean/Geography.tsx','components/ocean/Globe.tsx','components/ocean/Scene.tsx']){const sf=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);function walk(n){if(ts.isCallExpression(n)&&n.expression.getText(sf)==='t'&&ts.isStringLiteral(n.arguments[0]))assert(Object.hasOwn(translations,n.arguments[0].text.trim()),'Missing translation: '+n.arguments[0].text);ts.forEachChild(n,walk)}walk(sf)}
const {makePassageTraffic,passagePaths}=compile('components/ocean/PassageTraffic.ts');
for(const region of Object.keys(passagePaths)){const traffic=makePassageTraffic(region,p=>p,true);const first=traffic.update(0,0)[0],middle=traffic.update(20/30,0)[0];assert(first.position.equals(traffic.start));assert(!middle.position.equals(traffic.destination));const flag=traffic.group.getObjectByName('Illustrative_destination_flag').children[1];assert.equal(flag.material.color.getHexString(),'dca85f');assert(traffic.update(1,0)[0].position.distanceTo(traffic.destination)<1e-10);assert.equal(flag.material.color.getHexString(),'c6f36c');traffic.update(0,0);assert.equal(flag.material.color.getHexString(),'dca85f');traffic.group.traverse(o=>{o.geometry?.dispose();if(o.material)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.dispose())});}
console.log(`PASS: ${Object.keys(translations).length} translation entries, numerical placeholders, 7 destination markers, early-stop and reset states.`);

const {normalizeReplay,isReplaySelection,metricKeys}=compile('lib/ocean-types.ts');
const raw=JSON.parse(fs.readFileSync('public/data/replay.json','utf8'));
const normalized=normalizeReplay(raw);
assert.equal(normalized.runs,raw.runs,'Recorded voyage data must remain unchanged');
normalized.summary.forEach((row,i)=>{for(const key of metricKeys){assert(Number.isFinite(row[key]));assert.equal(row[key],Number(raw.summary[i][key]))}});
const selection={policy:'double_dqn',checkpoint:'42',caseSeed:42,step:10};
assert(isReplaySelection(selection));
for(const bad of [null,{}, {...selection,policy:'unknown'},{...selection,checkpoint:'0'},{...selection,caseSeed:141.5},{...selection,step:31},{...selection,step:-1},{...selection,step:'10'}])assert.equal(isReplaySelection(bad),false);
const row=normalized.runs.dqn_42['42'][9];
assert(Math.abs(row[0]-.95)<1e-12);
const totals=normalized.runs.dqn_42['42'].slice(0,10).reduce((a,r)=>[a[0]+r[1],a[1]+r[2]],[0,0]);
assert(Math.abs(totals[0]-.45)<1e-12);assert(Math.abs(totals[1]-.5)<1e-12);
console.log('PASS: replay summaries preserve numeric values; invalid replay selections rejected; reference voyage unchanged.');
