'use client';
import {useEffect,useRef} from 'react';
import * as THREE from 'three';
import {SVGRenderer} from 'three/addons/renderers/SVGRenderer.js';
import type {missionFrame} from '@/lib/voyage-mission';
type Frame=NonNullable<ReturnType<typeof missionFrame>>;
export default function MissionScene({frame,en}:{frame:Frame;en:boolean}){
 const root=useRef<HTMLDivElement>(null),mode=useRef<HTMLSpanElement>(null);
 const state=useRef<{ship:THREE.Group;hull:THREE.Mesh;fuel:THREE.Mesh;render:()=>void}|null>(null);
 useEffect(()=>{
  const host=root.current;if(!host)return;
  const scene=new THREE.Scene();scene.background=new THREE.Color('#0a2030');
  const camera=new THREE.PerspectiveCamera(37,1,.1,100);camera.position.set(9,10,15);camera.lookAt(0,0,0);
  let renderer:THREE.WebGLRenderer|SVGRenderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true});if(mode.current)mode.current.textContent='WebGL'}catch{renderer=new SVGRenderer();renderer.setQuality('high');if(mode.current)mode.current.textContent='SVG compatibility'}
  host.appendChild(renderer.domElement);
  const material=(color:string)=>new THREE.MeshBasicMaterial({color});
  const box=(w:number,h:number,d:number,color:string,x:number,y:number,z:number)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material(color));m.position.set(x,y,z);scene.add(m);return m};
  box(13,.08,4.7,'#16465a',0,-.5,0);
  for(let i=0;i<3;i++)box(1.8,.3,1.6,'#5f7480',-5+i*5,-.2,-2.6);
  const ship=new THREE.Group();scene.add(ship);ship.position.set(-5,.15,.6);
  const hull=new THREE.Mesh(new THREE.BoxGeometry(1.8,.42,.7),material('#d2e6ea'));ship.add(hull);
  const bridge=new THREE.Mesh(new THREE.BoxGeometry(.45,.55,.6),material('#f6f2e8'));bridge.position.set(-.55,.48,0);ship.add(bridge);
  const tank=box(1.0,1.5,1.0,'#668591',5.5,.35,3.2);(tank.material as THREE.MeshBasicMaterial).wireframe=true;
  const bow=new THREE.Mesh(new THREE.ConeGeometry(.48,.7,3),material('#8ab9c7'));bow.rotation.z=-Math.PI/2;bow.position.set(1.1,0,0);ship.add(bow);
  const cabin=new THREE.Mesh(new THREE.BoxGeometry(.22,.22,.32),material('#70ddc3'));cabin.position.set(-.55,.85,0);ship.add(cabin);
  const fuel=box(.96,1,.96,'#64ddc1',5.5,0,3.2);
  const resize=()=>{const w=Math.max(1,host.clientWidth),h=Math.max(220,host.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.render(scene,camera)};
  state.current={ship,hull,fuel,render:resize};
  const observer=new ResizeObserver(resize);observer.observe(host);resize();
  return ()=>{state.current=null;observer.disconnect();scene.traverse(o=>{if(o instanceof THREE.Mesh){o.geometry.dispose();const materials=Array.isArray(o.material)?o.material:[o.material];materials.forEach(m=>m.dispose())}});if(renderer instanceof THREE.WebGLRenderer)renderer.dispose();renderer.domElement.remove()};
 },[]);
 useEffect(()=>{const s=state.current;if(!s)return;const h=Math.max(.006,frame.fuel/100*1.5);s.ship.position.x=-5+frame.progress*10;s.fuel.scale.y=h;s.fuel.position.y=-.4+h/2;(s.fuel.material as THREE.MeshBasicMaterial).color.set(frame.fuel<10?'#fa776d':'#64ddc1');(s.hull.material as THREE.MeshBasicMaterial).color.set(frame.alert?'#f5b665':'#d2e6ea');s.render()},[frame.fuel,frame.progress,frame.alert]);
 return <figure className="mission-figure"><div className="mission-canvas" ref={root} aria-hidden="true"/><figcaption>{en?'Illustrative 3D scene':'설명용 3D 장면'} · <span ref={mode}/> · {en?'Position and tank use the current ledger; distance and hull are not a physical model.':'위치·탱크는 현재 원장과 연결됩니다. 거리·선체는 물리 모형이 아닙니다.'}</figcaption></figure>;
}
