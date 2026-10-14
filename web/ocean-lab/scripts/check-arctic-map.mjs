import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import ts from 'typescript';
import {geoArea,geoContains,geoInterpolate} from 'd3-geo';
import * as THREE from 'three';

const nativeRequire=createRequire(import.meta.url),cache=new Map();
function compile(file){
 const absolute=path.resolve(file);
 if(cache.has(absolute))return cache.get(absolute);
 const exports={};cache.set(absolute,exports);
 const require=name=>{
  if(name.startsWith('@/')||name.startsWith('.')){
   const base=name.startsWith('@/')?path.resolve(name.slice(2)):path.resolve(path.dirname(absolute),name);
   for(const candidate of [base,base+'.ts',base+'.tsx'])if(fs.existsSync(candidate)&&fs.statSync(candidate).isFile()){
    return candidate.endsWith('.json')?JSON.parse(fs.readFileSync(candidate,'utf8')):compile(candidate);
   }
  }
  return nativeRequire(name);
 };
 vm.runInNewContext(ts.transpileModule(fs.readFileSync(absolute,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{exports,require,URL,URLSearchParams},{filename:absolute});
 return exports;
}
const {passagePaths,makePassageTraffic,passageSample,arcticMapProject,arcticMapProjection}=compile('components/ocean/PassageTraffic.ts');
const {regions,arcticCoastlinePolygons,groupProjectedRings}=compile('components/ocean/Geography.tsx');
const {readShareState,shareURL}=compile('lib/share-state.ts');
const legacy=['suez','hormuz','taiwan','bab','cape','dover','ulsan'];
assert.deepEqual(Object.keys(regions),[...legacy,'arctic']);
for(const key of legacy)assert(passagePaths[key].length>=2,`${key} route remains available`);
assert(passagePaths.arctic.length>=10);
assert(passagePaths.arctic.some((point,index)=>index>0&&Math.abs(point[0]-passagePaths.arctic[index-1][0])>180),'Route includes the dateline crossing');
const projected=passagePaths.arctic.map(point=>{const [x,y]=arcticMapProject(point);return new THREE.Vector3(x,.45,-y)});
for(let i=1;i<projected.length;i++)assert(projected[i].distanceTo(projected[i-1])<20,'Polar map has no dateline jump');
const land=JSON.parse(fs.readFileSync('public/data/world-land.json','utf8'));
const original=JSON.stringify(land);
const polygons=arcticCoastlinePolygons(land);
assert.equal(JSON.stringify(land),original,'Coastline source remains unchanged');
assert(polygons.length>50,'Polar projection contains real public coastline polygons');
for(const polygon of polygons){
 assert(polygon.length>0&&polygon[0].length>=3);
 for(const [x,y] of polygon.flat())assert(Number.isFinite(x)&&Number.isFinite(y)&&Math.hypot(x,y)<60,'Coastlines stay inside the north-polar clip');
 const shape=new THREE.Shape(polygon[0].map(point=>new THREE.Vector2(...point)));
 polygon.slice(1).forEach(ring=>shape.holes.push(new THREE.Path(ring.map(point=>new THREE.Vector2(...point)))));
 const geometry=new THREE.ShapeGeometry(shape);
 assert([...geometry.attributes.position.array].every(Number.isFinite),'Flat coastline triangulates without invalid positions');
 geometry.dispose();
}
// Assert actual triangle coverage, not merely finite coordinates: a large
// disjoint exterior incorrectly treated as a hole previously passed that test.
const meshes=polygons.map(rings=>{const shape=new THREE.Shape(rings[0].map(p=>new THREE.Vector2(...p)));rings.slice(1).forEach(r=>shape.holes.push(new THREE.Path(r.map(p=>new THREE.Vector2(...p)))));const mesh=new THREE.Mesh(new THREE.ShapeGeometry(shape),new THREE.MeshBasicMaterial({side:THREE.DoubleSide}));mesh.updateMatrixWorld();return mesh});
function filled(point){const [x,y]=arcticMapProject(point);return new THREE.Raycaster(new THREE.Vector3(x,y,10),new THREE.Vector3(0,0,-1)).intersectObjects(meshes).length>0}
for(const [name,point] of [['Siberia',[110,65]],['western Russia',[50,64]],['Chukotka',[175,66]],['Alaska',[-150,66]],['Canada',[-110,65]],['Greenland',[-42,73]],['Norway',[24,69]]])assert(filled(point),name+' must have visible land fill');
for(const [name,point] of [['North Pole',[0,90]],['Barents Sea',[35,78]],['Chukchi Sea',[-170,75]]])assert(!filled(point),name+' must remain water');
const square=(x,y,size)=>[[x,y],[x+size,y],[x+size,y+size],[x,y+size],[x,y]];
const classified=groupProjectedRings([square(20,20,4),square(2,2,3).reverse(),square(0,0,10),square(3,3,1)]);
assert.equal(JSON.stringify(classified.map(p=>p.length)),JSON.stringify([2,1,1]),'Disjoint exteriors, genuine hole and nested island survive arbitrary ordering/winding');
meshes.forEach(m=>{m.geometry.dispose();m.material.dispose()});
land.geometry.coordinates=land.geometry.coordinates.map(rings=>geoArea({type:'Polygon',coordinates:rings})>2*Math.PI?rings.map(ring=>ring.slice().reverse()):rings);
// A visual-geometry regression against a simplified coastline, never a test of
// depth, ice, permits, vessel capability, safety or actual route feasibility.
for(let step=0;step<=1000;step++){
 const sample=passageSample(projected,step/1000);
 const lonLat=arcticMapProjection.invert([sample.position.x,sample.position.z]);
 assert(!geoContains(land,lonLat),'Illustrative line should not visually cross bundled land');
}
for(let index=1;index<passagePaths.arctic.length;index++){
 const interpolate=geoInterpolate(passagePaths.arctic[index-1],passagePaths.arctic[index]);
 for(let step=0;step<=100;step++)assert(!geoContains(land,interpolate(step/100)),'Globe route should not visually cross bundled land');
}
const traffic=makePassageTraffic('arctic',arcticMapProject,true);
assert(traffic.group.getObjectByName('Illustrative_route_arctic'));
let previous=traffic.update(0,0)[0].position;
assert(previous.equals(traffic.start));
for(let step=1;step<=30;step++){
 const position=traffic.update(step/30,0)[0].position;
 assert(position.distanceTo(passageSample(projected,step/30).position)<1e-10,'Vessel stays on the displayed waypoint line');
 assert(position.distanceTo(previous)>0,'Each replay step advances the vessel');previous=position;
}
assert(previous.distanceTo(traffic.destination)<1e-10);
assert.equal(traffic.group.getObjectByName('Illustrative_destination_flag').children[1].material.color.getHexString(),'c6f36c');
traffic.update(0,0);
assert.equal(traffic.group.getObjectByName('Illustrative_destination_flag').children[1].material.color.getHexString(),'dca85f');
traffic.group.traverse(object=>{object.geometry?.dispose();if(object.material)(Array.isArray(object.material)?object.material:[object.material]).forEach(material=>material.dispose())});
const state={policy:'double_dqn',checkpoint:'42',caseSeed:'42',step:17,region:'arctic',tab:'explore',view:'geography',lang:'en',started:true};
assert.equal(JSON.stringify(readShareState(new URL(shareURL('https://example.test','/',state)).search)),JSON.stringify(state));
for(const key of legacy)assert.equal(readShareState('?share=1&region='+key).region,key);
assert.equal(readShareState('?share=1&region=invalid').region,'hormuz');
assert(fs.readFileSync('components/ocean/Globe.tsx','utf8').includes('data-selected-route={region}'));
console.log(`PASS: all 8 regions, ${polygons.length} public polar coastline polygons, dateline continuity, 1,001 illustrative sea-line samples, 30 vessel positions, arrival/reset and Arctic share-state round trip. This is a display regression, not navigation validation.`);
