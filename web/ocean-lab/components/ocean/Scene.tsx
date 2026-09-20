'use client';
import {useLocale} from '@/lib/locale';
import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {GLTFExporter} from 'three/examples/jsm/exporters/GLTFExporter.js';
import {SVGRenderer} from 'three/examples/jsm/renderers/SVGRenderer.js';

import type {ExportVessel} from '@/lib/ocean-types';
import {disposeScene} from '@/lib/dispose-scene';
type SceneProps={progress:number;fuel:number;bunkering:boolean;view:string;resetCamera:number;onExportReady:(exporter:ExportVessel)=>void};
export default function OceanScene({progress,fuel,bunkering,view,resetCamera,onExportReady}:SceneProps){ const {t,lang}=useLocale();
 const host=useRef<HTMLDivElement>(null),state=useRef({progress,fuel,bunkering,view,resetCamera}),[error,setError]=useState('');
 useEffect(()=>{state.current={progress,fuel,bunkering,view,resetCamera}},[progress,fuel,bunkering,view,resetCamera]);
 useEffect(()=>{
  if(!host.current)return;
  let renderer: THREE.WebGLRenderer | SVGRenderer;let software=false;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});}catch{renderer=new SVGRenderer();renderer.setQuality('low');software=true;}
  const el=host.current;if(renderer instanceof THREE.WebGLRenderer){renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.75));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;}el.appendChild(renderer.domElement);renderer.domElement.style.touchAction='none';renderer.domElement.setAttribute('aria-label',t("드래그와 확대가 가능한 합성 선박 3D 공간"));renderer.domElement.setAttribute('role','img');renderer.domElement.dataset.renderer=software?'compatible-3d':'webgl';
  const scene=new THREE.Scene();scene.background=new THREE.Color('#9cbec0');scene.fog=new THREE.FogExp2('#9cbec0',.0065);
  const camera=new THREE.PerspectiveCamera(40,1,.1,1200);camera.position.set(29,25,35);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.07;controls.minDistance=9;controls.maxDistance=130;controls.maxPolarAngle=Math.PI*.485;controls.target.set(0,2,0);controls.enablePan=true;
  scene.add(new THREE.HemisphereLight('#dbffff','#24434e',2.2));
  scene.add(new THREE.AmbientLight('#c4dedd',software?1.6:.3));
  const sun=new THREE.DirectionalLight('#ffe6b5',3.5);sun.position.set(-35,55,10);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-60;sun.shadow.camera.right=60;sun.shadow.camera.top=60;sun.shadow.camera.bottom=-60;sun.shadow.normalBias=.15;scene.add(sun);
  const mat=(color:THREE.ColorRepresentation,roughness=.55,metalness=.08)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
  const materials={hull:mat('#163b49',.4,.35),red:mat('#913d37'),deck:mat('#d1d7c5'),white:mat('#edf0dc'),window:mat('#1d4d5c',.18,.65),rail:mat('#c8ddd4',.35,.4),lime:mat('#c9e881'),orange:mat('#cc7e4b'),teal:mat('#42737a'),dark:mat('#2a4d53'),concrete:mat('#788a87'),ground:mat('#778f80'),metal:mat('#b5c8bb')};
  function box(g:THREE.Object3D,w:number,h:number,d:number,x:number,y:number,z:number,m:THREE.Material){const o=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;g.add(o);return o}
  function cylinder(g:THREE.Object3D,r:number,h:number,x:number,y:number,z:number,m:THREE.Material){const o=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,software?5:16),m);o.position.set(x,y,z);o.castShadow=true;g.add(o);return o}
  function line(g:THREE.Object3D,points:[number,number,number][],color:THREE.ColorRepresentation,width=1){const geom=new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p)));const o=new THREE.Line(geom,new THREE.LineBasicMaterial({color,linewidth:width}));g.add(o);return o}
  const waterGeo=new THREE.PlaneGeometry(900,900,120,120);waterGeo.rotateX(-Math.PI/2);
  const waterMat=new THREE.ShaderMaterial({uniforms:{time:{value:0}},vertexShader:`uniform float time; varying vec3 p;void main(){p=position;p.y+=sin(p.x*.25+time*.35)*.07+cos(p.z*.19+time*.3)*.05;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);}`,fragmentShader:`uniform float time;varying vec3 p;void main(){float w=sin(p.x*.5+p.z*.4+time*.6)*sin(p.z*.61-p.x*.3-time*.4);float gl=pow(max(0.,w),18.);float d=clamp(length(p.xz)/180.,0.,1.);vec3 c=mix(vec3(.08,.28,.32),vec3(.36,.56,.57),d);c+=gl*vec3(.17,.22,.18);float stripe=pow(max(0.,sin(p.x*2.+p.z*3.+time)),40.);c+=stripe*.018;gl_FragColor=vec4(c,1.);}`});
  const fallbackWaterGeo=new THREE.PlaneGeometry(900,900);fallbackWaterGeo.rotateX(-Math.PI/2);
  const water=new THREE.Mesh(software?fallbackWaterGeo:waterGeo,software?new THREE.MeshBasicMaterial({color:'#366b75'}):waterMat);water.position.y=-.65;water.renderOrder=-1000;scene.add(water);
  const grid=new THREE.GridHelper(230,46,'#4f8588','#396a71');grid.position.y=-.42;grid.material.transparent=true;grid.material.opacity=.18;grid.renderOrder=-999;scene.add(grid);
  const vessel=new THREE.Group();vessel.name='Bunkering_AI_Concept_Vessel';scene.add(vessel);
  const shape=new THREE.Shape();shape.moveTo(-8.5,-2.35);shape.lineTo(5.6,-2.35);shape.quadraticCurveTo(9.1,-1.7,10,0);shape.quadraticCurveTo(9.1,1.7,5.6,2.35);shape.lineTo(-8.5,2.35);shape.closePath();
  const hullGeo=new THREE.ExtrudeGeometry(shape,{depth:2,bevelEnabled:true,bevelSize:.25,bevelThickness:.3,bevelSegments:2,steps:1,curveSegments:12});hullGeo.rotateX(Math.PI/2);const hull=new THREE.Mesh(hullGeo,materials.hull);hull.position.y=1.25;hull.castShadow=true;hull.receiveShadow=true;vessel.add(hull);
  const deckGeo=new THREE.ShapeGeometry(shape);deckGeo.rotateX(Math.PI/2);const deck=new THREE.Mesh(deckGeo,materials.deck);deck.rotation.x=Math.PI;deck.position.y=1.6;vessel.add(deck);
  box(vessel,16,.18,4.1,-.7,1.65,0,materials.deck);
  // Fixed decorative dimensions; no naval architecture or propulsion model.
  const cargo=new THREE.Group();cargo.name='Illustrative_cargo';vessel.add(cargo);
  for(let ix=0;ix<4;ix++)for(let iz=0;iz<3;iz++)for(let level=0;level<2+(ix===1?1:0);level++){
   const m=[materials.lime,materials.teal,materials.orange,materials.white,materials.dark][(ix*3+iz+level*2)%5];
   const x=-2.7+ix*2.45,y=2.15+level*.94,z=(iz-1)*1.25;
   box(cargo,2.3,.85,1.14,x,y,z,m);
   for(let c=0;c<(software?0:7);c++)box(cargo,.025,.77,.02,x-1+c*.32,y,z+.58,materials.rail);
  }
  box(vessel,3.1,3.8,4.0,-6.5,3.55,0,materials.white);box(vessel,3.7,.65,4.65,-6.2,5.6,0,materials.white);
  for(let i=0;i<6;i++){box(vessel,.37,.37,.035,-7.65+i*.58,5.64,2.345,materials.window);box(vessel,.37,.37,.035,-7.65+i*.58,5.64,-2.345,materials.window)}
  box(vessel,.035,.38,3.6,-4.33,5.65,0,materials.window);box(vessel,1.2,1.6,1.3,-7.1,6.15,0,materials.dark);box(vessel,1.26,.22,1.34,-7.1,6.94,0,materials.lime);
  cylinder(vessel,.065,2.3,-5.5,7.0,0,materials.white);box(vessel,.09,.08,2.5,-5.5,7.2,0,materials.white);
  cylinder(vessel,.36,.35,7.2,1.97,0,materials.dark);cylinder(vessel,.28,.35,8,1.94,.9,materials.dark);
  for(const side of [-1,1]){
   for(let i=0;i<24;i++)cylinder(vessel,.023,.6,-8+i*.66,1.95,side*2.31,materials.rail);
   line(vessel,[[-8,2.25,side*2.31],[7.15,2.25,side*2.31]],'#d5e3d9');
   box(vessel,1.5,.3,.4,-5,3.0,side*2.2,materials.orange);
  }
  const tankGroup=new THREE.Group();tankGroup.name='Normalized_fuel_indicator';vessel.add(tankGroup);
  const glass=new THREE.MeshPhysicalMaterial({color:'#d5ffff',transparent:true,opacity:.13,roughness:.1,metalness:0,depthWrite:false,side:THREE.DoubleSide});
  box(tankGroup,10,3.3,3.9,.9,3.2,0,glass);const fuelMesh=box(tankGroup,9.8,3,3.7,.9,3.1,0,new THREE.MeshStandardMaterial({color:'#c4f66d',emissive:'#44681b',emissiveIntensity:.22,transparent:true,opacity:.82}));
  const edges=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(10,3.3,3.9)),new THREE.LineBasicMaterial({color:'#d7f9ed',transparent:true,opacity:.6}));edges.position.set(.9,3.2,0);tankGroup.add(edges);
  line(tankGroup,[[-4,2.0,-2],[5.8,2.0,-2],[5.8,2.0,2],[-4,2.0,2],[-4,2.0,-2]],'#ffbd66');
  tankGroup.visible=false;
  const route=new THREE.CatmullRomCurve3([new THREE.Vector3(-27,-.15,-9),new THREE.Vector3(-10,-.15,0),new THREE.Vector3(8,-.15,3),new THREE.Vector3(25,-.15,-5),new THREE.Vector3(38,-.15,-18)]);
  const routeLine=new THREE.Line(new THREE.BufferGeometry().setFromPoints(route.getPoints(180)),new THREE.LineDashedMaterial({color:'#c5f47b',dashSize:1.1,gapSize:.75,transparent:true,opacity:.65}));routeLine.computeLineDistances();scene.add(routeLine);
  for(let i=0;i<=30;i++){const p=route.getPoint(i/30);const b=new THREE.Mesh(new THREE.SphereGeometry(i%5===0?.18:.08,8,6),materials.lime);b.position.copy(p);scene.add(b)}
  function harbor(x:number,z:number,rotation:number){const g=new THREE.Group();g.position.set(x,-.1,z);g.rotation.y=rotation;scene.add(g);
   box(g,23,1.2,12,0,-.4,-5,materials.ground);box(g,26,1,4,0,.05,2,materials.concrete);
   for(let i=0;i<9;i++)box(g,1.25,.08,.25,-10+i*2.4,.59,3.85,materials.lime);
   for(let i=0;i<3;i++){box(g,4.5,2.5,4.5,-7+i*6,1.6,-6,materials.dark);box(g,4.8,.23,4.8,-7+i*6,2.94,-6,materials.metal)}
   for(let i=0;i<2;i++){const x=-5+i*10;box(g,.45,9,.5,x,5,0,materials.orange);box(g,.45,9,.5,x+2.7,5,0,materials.orange);box(g,3.5,.5,11,x+1.35,9.1,2.5,materials.orange);line(g,[[x+1.3,9.3,6],[x+1.3,5.5,6]],'#dddace');box(g,3.5,.2,.7,x+1.3,5.4,6,materials.dark)}
   for(let i=0;i<12;i++)box(g,2.3,.85,1.1,-10+(i%6)*3.6,1.08+Math.floor(i/6)*.9,-1.5,materials[i%2?'teal':'lime']);
  }
  harbor(-36,-23,.2);harbor(47,-32,-.5);
  for(let i=0;i<8;i++){const rock=new THREE.Mesh(new THREE.DodecahedronGeometry(5+i%3,0),materials.ground);rock.scale.set(1,.55,1.5);rock.position.set(-60+i*17,-1,-61-Math.sin(i)*12);rock.castShadow=true;scene.add(rock)}
  const glow=new THREE.Mesh(new THREE.TorusGeometry(5,.035,8,90),new THREE.MeshBasicMaterial({color:'#caf76f',transparent:true,opacity:.85}));glow.rotation.x=Math.PI/2;glow.position.y=.03;scene.add(glow);
  const wake=new THREE.Group();vessel.add(wake);for(let i=0;i<12;i++){const l=line(wake,[[-8-i*.8,-.5,-.9-i*.15],[-9-i*.8,-.5,-1.25-i*.17]],'#b9ebe4');l.material.transparent=true;l.material.opacity=.48-i*.025;const r=l.clone();r.scale.z=-1;wake.add(r)}
  let dirty=true,lastProgress=-1,lastFuel=-1;controls.addEventListener('change',()=>{dirty=true});
  let lastView='',lastReset=-1,first=true,raf=0,lastDraw=0;const lastPos=new THREE.Vector3();const targetPos=new THREE.Vector3();const clock=new THREE.Clock();
  const onResize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()};const ro=new ResizeObserver(onResize);ro.observe(el);onResize();
  function animate(){raf=requestAnimationFrame(animate);if(document.hidden)return;const t=clock.getElapsedTime();const s=state.current;if(software){controls.update();if(t-lastDraw<.18)return;if(!dirty&&lastProgress===s.progress&&lastFuel===s.fuel&&lastView===s.view)return;}lastDraw=t;lastProgress=s.progress;lastFuel=s.fuel;const p=route.getPoint(Math.max(0,Math.min(1,s.progress)));targetPos.copy(p);vessel.position.lerp(targetPos,first||software?1:.08);vessel.position.y=software?0:Math.sin(t*.65)*.045;const tangent=route.getTangent(s.progress);vessel.rotation.y=-Math.atan2(tangent.z,tangent.x);vessel.rotation.z=software?0:Math.sin(t*.5)*.004;
   if(s.view!==lastView||s.resetCamera!==lastReset){const pos=vessel.position;controls.target.copy(s.view==='route'?new THREE.Vector3(5,0,-6):pos.clone().add(new THREE.Vector3(0,2,0)));camera.position.copy(s.view==='route'?new THREE.Vector3(55,67,72):pos.clone().add(s.view==='tank'?new THREE.Vector3(19,16,22):new THREE.Vector3(25,20,30)));lastView=s.view;lastReset=s.resetCamera;dirty=true;}
   if(!first&&s.view!=='route'){const delta=vessel.position.clone().sub(lastPos);camera.position.add(delta);controls.target.add(delta)}lastPos.copy(vessel.position);first=false;
   waterMat.uniforms.time.value=t;cargo.visible=s.view!=='tank';tankGroup.visible=s.view==='tank';fuelMesh.scale.y=Math.max(.005,s.fuel);fuelMesh.position.y=1.6+1.5*Math.max(.005,s.fuel);glow.position.set(vessel.position.x,0,vessel.position.z);glow.visible=s.bunkering;glow.scale.setScalar(1+.035*Math.sin(t*3));controls.update();renderer.render(scene,camera);dirty=false;
  }
  animate();
  onExportReady?.(()=>new Promise<boolean>((resolve,reject)=>{new GLTFExporter().parse(vessel,(result)=>{if(!(result instanceof ArrayBuffer)){reject(new Error("Expected binary GLB"));return}const url=URL.createObjectURL(new Blob([result],{type:'model/gltf-binary'}));const a=document.createElement('a');a.href=url;a.download='Bunkering_Concept_Vessel.glb';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);resolve(true)},reject,{binary:true,onlyVisible:true});}));
  const lost=(e:Event)=>{e.preventDefault();setError(t("3D 연결이 중단됐어요. 페이지를 새로고침하면 다시 시도합니다. 데이터 비교는 계속 이용할 수 있습니다."))};renderer.domElement.addEventListener('webglcontextlost',lost);
  return()=>{cancelAnimationFrame(raf);ro.disconnect();controls.dispose();onExportReady?.(null);disposeScene(scene);if(renderer instanceof THREE.WebGLRenderer)renderer.dispose();renderer.domElement.remove();};
 },[lang,t,onExportReady]);
 return <div className="scene-canvas" ref={host}>{error&&<div role="alert" className="webgl-error">{error}</div>}</div>
}
