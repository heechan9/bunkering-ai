import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const loadedModule={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/map-label-layout.ts','utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020},
}).outputText,{module:loadedModule,exports:loadedModule.exports});
const {layoutMapLabels}=loadedModule.exports;
let cases=0;
// Effective CSS widths cover desktop zoom and 390/360 px; density covers camera zoom.
for(const width of [360,390,475,633,760,950,1280])for(const density of [0,12,40,120])for(const language of ['ko','en']){
  const boxes=Array.from({length:10},(_,id)=>({id,x:width/2+(id%3-1)*density,y:210+(Math.floor(id/3)-1)*density,
    width:id===0?(language==='en'?240:210):language==='en'?160:110,height:id===0?44:28,priority:id===0?100:90-id*10}));
  const result=layoutMapLabels(boxes,width,420),visible=result.filter(label=>label.visible);
  assert.equal(result.length,boxes.length);
  assert(visible.some(label=>label.id===0),'Vessel gets priority in a dense cluster');
  for(const label of visible){
    const box=boxes[label.id];
    assert(label.x-box.width/2>=12&&label.x+box.width/2<=width-12);
    assert(label.y-box.height/2>=12&&label.y+box.height/2<=408);
    for(const other of visible.filter(other=>other.id>label.id)){
      const otherBox=boxes[other.id];
      assert(Math.abs(label.x-other.x)>=(box.width+otherBox.width)/2+6||Math.abs(label.y-other.y)>=(box.height+otherBox.height)/2+6,'Visible labels must not overlap');
    }
  }
  assert.equal(JSON.stringify(layoutMapLabels(boxes,width,420)),JSON.stringify(result),'Repeated layout is stable');
  cases++;
}
const edge=layoutMapLabels([{id:0,x:1,y:1,width:220,height:28,priority:100}],360,420)[0];
assert.equal(edge.visible,true);assert.equal(edge.x,122);assert.equal(edge.y,26);
for(const width of [NaN,10])assert.equal(layoutMapLabels([{id:0,x:50,y:50,width:200,height:28,priority:100}],width,420)[0].visible,false);
const crowded=[{id:0,x:180,y:210,width:240,height:44,priority:100},{id:1,x:180,y:210,width:240,height:44,priority:20}];
assert.equal(layoutMapLabels(crowded,360,420).filter(label=>label.visible).length,1);
console.log(`PASS: ${cases} Korean/English screen-width and camera-density combinations; bounded, stable, non-overlapping labels and vessel priority. No browser visual verification.`);

// Source-level layout contract: normal-flow replay rows must size their workspace.
// This intentionally does not claim browser geometry/visual coverage.
const css=fs.readFileSync('app/globals.css','utf8');
const page=fs.readFileSync('app/page.tsx','utf8');
assert.match(page,/<section className="workspace"><div className=\{"ocean replay-layout /,
  'The replay grid is a direct child of the workspace targeted by the height override');
assert.match(page,/<\/aside><\/section>\{started&&<PurchaseComparison/,
  'The comparison remains after the replay workspace in normal document flow');
const workspaceOverride=/\.workspace:has\(>\s*\.replay-layout\)\s*\{([^}]+)\}/.exec(css);
assert(workspaceOverride,'Replay workspaces must override the legacy viewport-height constraint');
assert.match(workspaceOverride[1],/(?:^|;)\s*height\s*:\s*auto\s*(?:;|$)/);
assert(workspaceOverride.index>css.indexOf('height:calc(100svh - 202px)'),
  'The content-height rule follows the legacy fixed-height desktop rule');
const replayRule=/\.workspace \.ocean\.replay-layout\{([^}]+)\}/.exec(css)[1];
assert.match(replayRule,/height:auto/);
for(const row of ['map','controls','timeline','key','footnote'])
  assert(replayRule.includes(`"${row} ${row}"`),`${row} keeps its own normal-flow grid row`);
console.log('PASS: replay workspace content-height and following-comparison source contracts. Browser geometry is not covered.');
