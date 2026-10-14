import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const files=[];
function walk(dir){if(!fs.existsSync(dir))return;for(const f of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,f.name);if(f.isDirectory())walk(p);else files.push(p);}}
for(const dir of ['app','components','lib','public'])walk(dir);
const forbidden=/한바다|hanbada/i;
for(const file of files){
 const text=fs.readFileSync(file,'utf8');assert(!forbidden.test(text),`Public vessel identifier in ${file}`);
 // Public Polarstern course angles can independently equal a previously withheld fuel figure.
 if(!file.includes('/arctic-observations/'))assert(!/(?<![\d.])(?:670\.3|475\.1|195\.2)(?![\d.])/.test(text),`Withheld value pattern in ${file}`);
}
for(const name of ['hanbada-review.json','hanbada-comparison.json']){const stub=JSON.parse(fs.readFileSync('public/data/'+name));assert(stub.withheld===true||stub.status==='withheld');assert(!('opening_rob' in stub));assert(!('windows' in stub));}
const ab=fs.readFileSync('components/ocean/AbLogReview.tsx','utf8');assert(!ab.includes('fetch('));
assert.equal(JSON.parse(fs.readFileSync('public/data/source-catalog.json')).sources.length,3);
console.log(`PASS: ${files.length} public/bundled source files scanned; detail stubs, no detail fetch, no vessel-specific catalogue card.`);
