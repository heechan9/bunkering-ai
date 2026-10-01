import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import {createRequire} from 'node:module';
import {renderToStaticMarkup} from 'react-dom/server';
import React from 'react';
const require=createRequire(import.meta.url);
const catalog=JSON.parse(fs.readFileSync('public/data/source-catalog.json','utf8'));
const code=ts.transpileModule(fs.readFileSync('components/ocean/SourceInventory.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
for(const lang of ['ko','en']){
 const exports={};
 vm.runInNewContext(code,{exports,require:path=>path==='@/lib/locale'?{useLocale:()=>({lang})}:path==='@/public/data/source-catalog.json'?catalog:require(path)});
 const html=renderToStaticMarkup(React.createElement(exports.default));
 assert.equal((html.match(/class="source-catalog-card"/g)||[]).length,4);
 for(const source of catalog.sources){assert(html.includes(source.title[lang]));assert(html.includes(source.url));assert(html.includes(source.sha256));}
 assert(html.includes('download="bunkering-source-catalog.json"'));
 assert(html.includes(lang==='ko'?'남은 확인사항':'Still needed'));
 assert(!html.includes('/blob/main/'));
}
console.log('PASS: Korean/English source cards, pinned links, file identities and download render. Browser layout not covered.');
