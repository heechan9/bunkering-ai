import * as THREE from 'three';

// Authored geographic illustrations, not AIS tracks or navigable waypoints.
// All seven paths are presentation-only and never enter the research model.
export const passagePaths: Record<string, number[][]> = {
 suez: [[32.15,31.8],[32.31,31.26],[32.33,30.9],[32.34,30.59],[32.52,30.36],[32.56,30.02],[32.7,29.65],[33.1,28.9],[33.6,28.1]],
 hormuz: [[53.2,26.6],[54.6,26.6],[55.6,26.65],[56.05,26.7],[56.45,26.65],[56.8,26.4],[57.0,26.0],[57.5,25.6],[58.6,25.05],[59.4,24.8]],
 taiwan: [[118.0,21.5],[118.5,22.5],[119.05,23.3],[119.6,24.1],[120.25,25.0],[121.0,25.85],[122.0,26.5]],
 bab: [[41.7,15.0],[42.5,13.8],[43.0,13.1],[43.3,12.6],[43.5,12.3],[44.3,12.0],[45.8,11.7]],
 cape: [[16,-32],[16.5,-33.5],[17.3,-34.8],[18.3,-35.5],[19.6,-35.8],[21,-35.6],[22.5,-35.0],[23.2,-34.6]],
 dover: [[-0.5,50.2],[0.2,50.5],[0.9,50.8],[1.5,51.0],[1.9,51.35],[2.5,51.9],[3.2,52.5]],
 ulsan: [[130.0,34.95],[129.85,35.05],[129.65,35.2],[129.55,35.32],[129.48,35.42],[129.42,35.47]],
};

// Piecewise linear interpolation avoids curves inventing shortcuts across land.
export function passageSample(points: THREE.Vector3[], progress: number) {
 const lengths=points.slice(1).map((p,i)=>p.distanceTo(points[i]));
 let distance=THREE.MathUtils.clamp(progress,0,1)*lengths.reduce((a,b)=>a+b,0);
 for(let i=0;i<lengths.length;i++){
  if(distance<=lengths[i]||i===lengths.length-1){
   return {position:points[i].clone().lerp(points[i+1],distance/lengths[i]), tangent:points[i+1].clone().sub(points[i]).normalize()};
  }
  distance-=lengths[i];
 }
 return {position:points[0].clone(),tangent:new THREE.Vector3(1,0,0)};
}

export function makePassageTraffic(region:string, project:(p:number[])=>number[], singleShip=false) {
 const group=new THREE.Group();group.name='Illustrative_passage_traffic';
 const points=passagePaths[region].map(p=>{const [x,y]=project(p);return new THREE.Vector3(x,.45,-y)});
 const route=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineDashedMaterial({color:'#b5e9e3',dashSize:1.2,gapSize:.75,transparent:true,opacity:.85,depthTest:false}));route.computeLineDistances();route.renderOrder=200;group.add(route);
 // The 1:10m coastline omits the canal. A visibly exaggerated blue ribbon
 // marks the illustrative passage, never a surveyed waterway or depth map.
 if(region==='suez')for(let i=0;i<points.length-1;i++){
  const a=points[i],b=points[i+1],ribbon=new THREE.Mesh(new THREE.PlaneGeometry(.9,a.distanceTo(b)),new THREE.MeshBasicMaterial({color:'#246579',side:THREE.DoubleSide,depthTest:false}));
  ribbon.rotation.set(-Math.PI/2,0,Math.atan2(-(b.x-a.x),-(b.z-a.z)));ribbon.position.copy(a.clone().lerp(b,.5));ribbon.position.y=.3;ribbon.renderOrder=190;group.add(ribbon);
 }
 const ships=Array.from({length:3},(_,index)=>{
  const vessel=new THREE.Group();vessel.name='Illustrative_ship_'+(index+1);
  const hullMat=new THREE.MeshBasicMaterial({color:'#e4ede3',depthTest:false});
  const dark=new THREE.MeshBasicMaterial({color:'#12343d',depthTest:false});
  const white=new THREE.MeshBasicMaterial({color:'#ffffff',depthTest:false});
  const cargo=new THREE.MeshBasicMaterial({color:index===1?'#cd9460':'#548d95',depthTest:false});
  const shape=new THREE.Shape();shape.moveTo(-1.7,-.48);shape.lineTo(1.1,-.48);shape.lineTo(1.9,0);shape.lineTo(1.1,.48);shape.lineTo(-1.7,.48);shape.closePath();
  const hullGeo=new THREE.ExtrudeGeometry(shape,{depth:.35,bevelEnabled:false});hullGeo.rotateX(-Math.PI/2);
  const hull=new THREE.Mesh(hullGeo,hullMat);vessel.add(hull);
  const box=(w:number,h:number,d:number,x:number,y:number,z:number,m:THREE.Material)=>{const b=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);b.position.set(x,y,z);vessel.add(b)};
  box(.65,.5,.8,-1.15,.6,0,white);box(.68,.13,.82,-1.15,.77,0,dark);
  for(let i=0;i<3;i++)box(.58,.36,.7,-.4+i*.64,.55,0,cargo);
  const halo=new THREE.Mesh(new THREE.RingGeometry(2.4,2.5,32),new THREE.MeshBasicMaterial({color:'#c6f36c',side:THREE.DoubleSide,depthTest:false}));halo.rotation.x=-Math.PI/2;halo.position.y=.03;vessel.add(halo);
  const wake=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-4,0,-.7),new THREE.Vector3(-1.7,0,0),new THREE.Vector3(-4,0,.7)]),new THREE.LineBasicMaterial({color:'#a9d5d7',transparent:true,opacity:.55,depthTest:false}));vessel.add(wake);
  vessel.scale.setScalar(1.2);vessel.traverse(o=>{o.renderOrder=220});group.add(vessel);
  return {vessel,hullMat,halo};
 });
 return {group,update:(progress:number,selected:number,bunkering=false)=>{
  return ships.map((s,i)=>{s.vessel.visible=!singleShip||i===0;const p=singleShip?THREE.MathUtils.clamp(progress,0,1):(progress+i/3)%1;const sample=passageSample(points,p);s.vessel.position.copy(sample.position);s.vessel.rotation.y=-Math.atan2(sample.tangent.z,sample.tangent.x);s.hullMat.color.set(i===selected?'#c6f36c':'#e4ede3');s.halo.visible=singleShip?bunkering:i===selected;s.halo.scale.setScalar(singleShip&&bunkering?1.25:1);return {position:sample.position,progress:p};});
 }};
}
