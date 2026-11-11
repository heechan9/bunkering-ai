import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const out={};vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/passage-clock.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:out});
const {advancePassageProgress:advance}=out;
for(const fps of [1,2,5,10,30,60])for(const speed of [.5,1,2]){let p=0;for(let i=0;i<12*fps;i++)p=advance(p,1000/fps,speed);assert(Math.abs(p-.25*speed)<1e-10, 'Playback duration must not depend on FPS');}
assert.equal(advance(.25,48000,1),.25);
assert.equal(advance(.75,12000,1),0);
assert.equal(advance(.4,0,1),.4);
assert.equal(advance(.4,NaN,1),.4);
const old=12*2*Math.min(500,100)/48000;assert.equal(old,.05);
const source=fs.readFileSync('components/ocean/Geography.tsx','utf8');assert(source.includes("document.addEventListener('visibilitychange',visibility)"));assert(source.includes("document.removeEventListener('visibilitychange',visibility)"));assert(!source.includes('Math.min(now-last,100)'));
console.log('PASS: 18 FPS/speed combinations, loop, invalid time, visibility cleanup; old 2 FPS clock loses 80% of elapsed time.');
