import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import * as THREE from 'three';
const out={};vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/map-camera.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{exports:out});
const {mapCameraFit,mapCameraTarget}=out;
let cases=0;
for(const [w,h] of [[320,420],[360,420],[390,420],[430,420],[560,300],[805,1069],[1280,720]])for(const depth of [100,126,136,160])for(const yaw of [0,Math.PI/4,Math.PI/2,Math.PI,Math.PI*1.5]){
 const fit=mapCameraFit(w,h,136,depth),cam=new THREE.PerspectiveCamera(38,fit.aspect,.1,4000);
 cam.position.set(18,110,125).normalize().multiplyScalar(fit.distance).applyAxisAngle(new THREE.Vector3(0,1,0),yaw);cam.lookAt(0,0,0);cam.updateMatrixWorld();
 for(const x of [-68,68])for(const z of [-depth/2,depth/2])for(const y of [0,12]){const p=new THREE.Vector3(x,y,z).project(cam);assert(Math.abs(p.x)<.94&&Math.abs(p.y)<.94,'Fit keeps all map bounds within the viewport');}
 assert(fit.minDistance<fit.distance*.12&&fit.maxDistance>fit.distance);cases++;
}
// Reproduce the previous portrait cropping, then verify the fitted camera.
const previous=new THREE.PerspectiveCamera(38,390/560,.1,700);previous.position.set(18,110,125);previous.lookAt(0,0,0);previous.updateMatrixWorld();
const oldCorners=[[-63,-62],[-63,62],[63,-62],[63,62]].map(([x,z])=>new THREE.Vector3(x,0,z).project(previous));assert(oldCorners.some(p=>Math.abs(p.x)>1),'Old camera crops a normal map in portrait');
const source=fs.readFileSync('components/ocean/Geography.tsx','utf8');assert(source.includes('controls.enablePan=true'));assert(source.includes('controls.screenSpacePanning=false'));assert(source.includes('THREE.TOUCH.DOLLY_PAN'));assert(source.includes("cameraModeRef.current==='pan'?THREE.TOUCH.PAN:THREE.TOUCH.ROTATE"));assert(source.includes('boundTarget();dirty=true'));assert(source.includes("useState<'pan'|'rotate'>('pan')"));assert(source.includes('cameraAction.current=action=>'));assert(source.includes("action==='fit'"));assert(source.includes('dataset.cameraPosition'));
const css=fs.readFileSync('app/globals.css','utf8');assert(css.includes('height:clamp(300px,60svh,420px)'));assert(css.includes('.map-camera-controls button{min-width:44px;min-height:44px'));
for(const x of [-10000,-80,-63,0,63,80,10000])for(const z of [-10000,-68,0,68,10000]){const target=mapCameraTarget(x,z,126,136);assert(Math.abs(target.x)<=63&&Math.abs(target.z)<=68&&target.y===0);}
console.log(`PASS: reproduced old portrait crop; ${cases} viewport/map-size/orbit fits, bounded pan, deeper zoom and direct camera recovery controls. Not a physical-phone touch test.`);

// Unit-level synthetic touch events through the actual installed OrbitControls.
// This is not browser/device touch emulation.
const {OrbitControls}=await import('three/examples/jsm/controls/OrbitControls.js');
class Surface extends EventTarget{
 style={};clientWidth=390;clientHeight=420;ownerDocument=this;
 getRootNode(){return this}setPointerCapture(){}releasePointerCapture(){}
 getBoundingClientRect(){return {left:0,top:0,width:390,height:420}}
}
const surface=new Surface(),camera=new THREE.PerspectiveCamera(38,390/420,.1,4000),controls=new OrbitControls(camera,surface);
controls.enablePan=true;controls.screenSpacePanning=false;controls.panSpeed=.8;
controls.touches.ONE=THREE.TOUCH.PAN;controls.touches.TWO=THREE.TOUCH.DOLLY_PAN;
controls.minPolarAngle=.12;controls.maxPolarAngle=Math.PI*.42;
const fit=mapCameraFit(390,420,126,136);controls.minDistance=fit.minDistance;controls.maxDistance=fit.maxDistance;
const center=()=>{controls.target.set(0,0,0);camera.position.set(18,110,125).normalize().multiplyScalar(fit.distance);camera.lookAt(0,0,0);controls.update();};
controls.addEventListener('change',()=>{const b=mapCameraTarget(controls.target.x,controls.target.z,126,136);const delta=new THREE.Vector3(b.x,b.y,b.z).sub(controls.target);controls.target.add(delta);camera.position.add(delta)});
function touch(type,id,x,y){const event=new Event(type);Object.assign(event,{pointerId:id,pointerType:'touch',pageX:x,pageY:y,clientX:x,clientY:y});surface.dispatchEvent(event);}
center();const initialOffset=camera.position.clone().sub(controls.target);
touch('pointerdown',1,190,210);touch('pointermove',1,250,210);touch('pointerup',1,250,210);
assert(controls.target.length()>5,'One finger pans in Move mode');assert(camera.position.clone().sub(controls.target).distanceTo(initialOffset)<1e-8,'Pan preserves orientation/distance');
center();touch('pointerdown',1,150,210);touch('pointerdown',2,250,210);touch('pointermove',1,180,210);touch('pointermove',2,280,210);touch('pointerup',2,280,210);touch('pointerup',1,180,210);assert(controls.target.length()>3,'Two-finger translation pans');
center();touch('pointerdown',1,150,210);touch('pointerdown',2,250,210);touch('pointermove',1,100,210);touch('pointermove',2,300,210);touch('pointerup',2,300,210);touch('pointerup',1,100,210);assert(camera.position.distanceTo(controls.target)<fit.distance*.6,'Pinch spread zooms in');
center();controls.touches.ONE=THREE.TOUCH.ROTATE;touch('pointerdown',1,190,210);touch('pointermove',1,250,210);touch('pointerup',1,250,210);assert(controls.target.length()<1e-8,'Rotate mode keeps target');assert(camera.position.clone().sub(controls.target).distanceTo(initialOffset)>5,'One finger rotates in Rotate mode');
center();controls.touches.ONE=THREE.TOUCH.PAN;touch('pointerdown',1,190,210);for(let i=0;i<20;i++)touch('pointermove',1,1000+i*1000,1000+i*1000);touch('pointerup',1,20000,20000);assert(Math.abs(controls.target.x)<=63&&Math.abs(controls.target.z)<=68&&controls.target.y===0,'Repeated extreme pan stays bounded');assert(camera.position.clone().sub(controls.target).distanceTo(initialOffset)<1e-8);
controls.enableDamping=true;center();touch('pointerdown',1,190,210);touch('pointermove',1,4000,4000);touch('pointerup',1,4000,4000);for(let i=0;i<60;i++)controls.update();assert(Math.abs(controls.target.x)<=63&&Math.abs(controls.target.z)<=68);controls.enableDamping=false;controls.update();
center();assert(controls.target.length()===0&&Math.abs(camera.position.length()-fit.distance)<1e-8,'Reset restores centered fit');controls.dispose();
console.log('PASS: actual OrbitControls synthetic one-touch pan/rotate, two-touch pan/pinch, extreme-pan bounds, offset preservation and reset. Not a physical-device test.');
