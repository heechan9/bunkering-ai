'use client';
import {useLocale} from '@/lib/locale';
import {useCallback,useEffect,useRef,useState,useSyncExternalStore} from 'react';
import * as THREE from 'three';
import {geoArea,geoStream} from 'd3-geo';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {SVGRenderer} from 'three/examples/jsm/renderers/SVGRenderer.js';
import {Compass,MapPin,RotateCcw,ArrowUpRight,Info,Ship,Globe2,Play,Pause} from 'lucide-react';
import {Button} from '@/components/ui/button';
import Globe from './Globe';
import {makeTerrain,terrainHeight} from './Terrain';
import {arcticMapProjection,arcticMapProject,makePassageTraffic} from './PassageTraffic';
import {layoutMapLabels} from '@/lib/map-label-layout';

const onsSource='https://www.ons.gov.uk/businessindustryandtrade/internationaltrade/datasets/weeklyshipcrossingsbyshiptypethroughsixglobalmaritimepassages';
const contextNote='ONS 통항량 자료의 대상 지역입니다. 이 지역을 별도 구매·소비·잔량 실험으로 평가하지 않았으며, 통항량을 DQN 학습에 직접 넣지 않았습니다.';
export const regions:Record<string,Region>={
 suez:{title:'수에즈 운하',en:'SUEZ CANAL',badge:'대표 우회 가정',connection:'지중해 ↔ 홍해',description:'수에즈 경유와 희망봉 우회의 거리 차이가 항차 길이 민감도 실험의 출발점입니다.',center:[32.25,30.25],bounds:[29,27,35.5,33.5],labels:[['지중해',31,32.7,'sea'],['홍해',33.8,27.4,'sea'],['이집트',30.5,29.6,'land'],['시나이반도',33.8,29.9,'land'],['포트사이드',32.3,31.26,'port'],['수에즈',32.55,29.97,'port']],focus:[32.38,30.62],source:onsSource,note:'싱가포르–로테르담의 수에즈/희망봉 거리 비교를 참고해 합성 항차를 30→43단계로 늘렸습니다. 실제 운하 통항·선속·기상·소요시간을 계산하지 않습니다.'},
 hormuz:{title:'호르무즈 해협',en:'STRAIT OF HORMUZ',badge:'관찰 대조 조건',connection:'페르시아만 ↔ 오만만',description:'좁은 해협을 통한 공급망 연결을 살펴봅니다. 호르무즈에는 수에즈처럼 가정한 해상 우회로가 없습니다.',center:[56.5,26],bounds:[52.5,22.5,60.5,29.5],labels:[['페르시아만',54.3,26.7,'sea'],['오만만',58.7,24.8,'sea'],['이란',58.7,28.2,'land'],['아랍에미리트',54.7,24,'land'],['오만',57.2,23.5,'land'],['무산담반도',56.25,25.9,'port']],focus:[56.5,26.6],source:onsSource,note:'Hormuz observation-only는 환경을 바꾸지 않은 대조 조건입니다. 동일 seed에서 Normal과 결과가 같으며, 해협 봉쇄·공급 제한·위기 대응 성능을 평가한 것이 아닙니다.'},
 taiwan:{title:'대만해협',en:'TAIWAN STRAIT',badge:'통항량 참고',connection:'동중국해 ↔ 남중국해',description:'아시아 해상 연결을 보여주는 지역입니다. 프로젝트가 참조하는 ONS 6개 통항 지역 중 하나입니다.',center:[120,24],bounds:[116,20.5,124,27.5],labels:[['중국 연안',117.5,25.8,'land'],['대만',121.15,23.7,'land'],['동중국해',122.2,26.5,'sea'],['남중국해',118.5,21.5,'sea']],focus:[119.6,24.1],source:onsSource,note:contextNote},
 bab:{title:'바브엘만데브',en:'BAB-AL MANDAB STRAIT',badge:'통항량 참고',connection:'홍해 ↔ 아덴만',description:'홍해 남쪽 입구의 해협입니다. 수에즈와 같은 홍해 수송 맥락에 있지만 별개의 관측 지역입니다.',center:[43.5,13],bounds:[40.5,10,46.5,16],labels:[['홍해',41.8,15,'sea'],['아덴만',45.4,11.6,'sea'],['예멘',45,14,'land'],['지부티',42.5,11.7,'land'],['에리트레아',41.6,13.8,'land']],focus:[43.35,12.58],source:onsSource,note:contextNote},
 cape:{title:'희망봉',en:'CAPE OF GOOD HOPE',badge:'대표 우회 가정',connection:'아프리카 남부 우회',description:'수에즈를 경유하는 대표 항로와 비교한 우회 지역입니다. 호르무즈의 대체 통로를 뜻하지 않습니다.',center:[19,-34],bounds:[14,-38,24,-30],labels:[['남아프리카공화국',20,-32.4,'land'],['대서양',15.5,-34.8,'sea'],['남부 해역',21.8,-36.8,'sea'],['케이프타운',18.42,-33.92,'port']],focus:[18.5,-34.36],source:onsSource,note:'수에즈와 같은 Suez/Cape 대표 시나리오의 두 경로입니다. 별개의 추가 실험으로 세지 않으며, 우회 항차의 기상·해류·실제 연료소비는 모델링하지 않았습니다.'},
 dover:{title:'도버해협',en:'STRAIT OF DOVER',badge:'통항량 참고',connection:'영국해협 ↔ 북해',description:'영국과 프랑스 사이의 해상 연결입니다. ONS 자료에 포함된 유럽 통항 관측 지역입니다.',center:[1.5,51],bounds:[-1,49,4,53],labels:[['영국',.1,51.8,'land'],['프랑스',2,50,'land'],['영국해협',-.1,50.2,'sea'],['북해',2.8,52,'sea']],focus:[1.5,51],source:onsSource,note:contextNote},
 ulsan:{title:'울산항',en:'ULSAN PORT',badge:'현장 업무 참고',connection:'울산 연안 · 벙커링정박지',description:'울산항만공사 신청현황 6,028건·8개 항목에서 총톤수·벙커량·예정 시간의 구조를 확인했습니다. 벙커량의 단위와 신청량·실공급량 여부는 미확인입니다.',center:[129.4,35.45],bounds:[128.7,34.8,130.1,36.1],labels:[['대한민국',128.95,35.7,'land'],['동해',129.85,35.65,'sea'],['부산',129.07,35.12,'port']],focus:[129.39,35.47],source:'https://www.data.go.kr/data/15132700/fileData.do',note:'신청 자료는 참고 분석용이며 DQN 학습·공식 평가 입력이 아닙니다. 구매가격·소비·최종잔량이 연결된 실항차 자료도 아닙니다. 지도는 울산 연안의 위치 설명이며 실제 정박지 구획을 표시하지 않습니다.'},
 arctic:{title:'북극 항로',en:'ARCTIC ILLUSTRATIVE ROUTE',badge:'합성 북극 실험',connection:'바렌츠해 ↔ 베링해협 · 설명용 경유점',description:'북극의 해양 경유점을 따라 이동하는 선박을 살펴보고, 같은 화면에서 합성 연료·구매 조건을 바꿔봅니다.',center:[100,76],bounds:[-180,56,180,90],labels:[['북극점',0,90,'sea'],['바렌츠해',35,78,'sea'],['추크치해',-170,75,'sea'],['러시아',110,65,'land'],['알래스카',-150,66,'land'],['노르웨이',20,68,'land']],focus:[100,81.5],source:'https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/',note:'해양 경유점을 직접 배치한 설명용 항로입니다. 해빙 관측·수심·운항 가능성·쇄빙 능력·절감 효과를 나타내지 않습니다. 북극 연료 계산에는 사용자가 설정한 합성 가정만 쓰입니다.'}
};

import type {Region,Coordinates,TerrainData,Coastlines,Flight,WorldLand} from '@/lib/ocean-types';
import {disposeScene} from '@/lib/dispose-scene';
function subscribeMotion(callback:()=>void){const mq=matchMedia('(prefers-reduced-motion: reduce)');mq.addEventListener('change',callback);return()=>mq.removeEventListener('change',callback)}
const readMotion=()=>!matchMedia('(prefers-reduced-motion: reduce)').matches;
const serverMotion=()=>false;

// Project the existing public coastline into a north-polar view. This is a flat
// geographic display, not a generated DEM or an ice/route-feasibility layer.
export function arcticCoastlinePolygons(land:WorldLand):Coordinates[][][] {
 const coordinates=land.geometry.coordinates.map(rings=>geoArea({type:'Polygon',coordinates:rings})>2*Math.PI?rings.map(ring=>ring.slice().reverse()):rings);
 const polygons:Coordinates[][][]=[];let polygon:Coordinates[][]=[],ring:Coordinates[]=[];
 geoStream({type:'MultiPolygon',coordinates},arcticMapProjection.stream({
  sphere(){},polygonStart(){polygon=[]},polygonEnd(){if(polygon.length)polygons.push(polygon)},
  lineStart(){ring=[]},lineEnd(){if(ring.length>=3)polygon.push(ring)},point(x,y){ring.push([x,-y])},
 }));
 // Spherical clipping can split one source polygon into several disconnected
 // exterior rings (notably Eurasia at the latitude clip). They must not be
 // passed to Three.js as holes of the first ring. Classify by containment,
 // independent of ring ordering/winding, preserving genuine interior holes.
 return polygons.flatMap(groupProjectedRings);
}

export function groupProjectedRings(rings:Coordinates[][]):Coordinates[][][] {
 const area=(ring:Coordinates[])=>Math.abs(ring.reduce((sum,[x,y],i)=>{const q=ring[(i+1)%ring.length];return sum+x*q[1]-q[0]*y},0));
 const contains=(ring:Coordinates[],[x,y]:Coordinates)=>{let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])inside=!inside}return inside};
 const sorted=rings.map(ring=>({ring,area:area(ring),parent:-1,depth:0})).sort((a,b)=>b.area-a.area);
 const result:Coordinates[][][]=[],outer=new Map<number,Coordinates[][]>();
 sorted.forEach((entry,i)=>{
  for(let j=i-1;j>=0;j--)if(contains(sorted[j].ring,entry.ring[0])){entry.parent=j;entry.depth=sorted[j].depth+1;break}
  if(entry.depth%2===0){const polygon=[entry.ring];result.push(polygon);outer.set(i,polygon)}
  else outer.get(entry.parent)!.push(entry.ring);
 });
 return result;
}

type MapProps={region:string;reset:number;exaggeration:number;trafficProgress:number;selectedShip?:number;singleShip?:boolean;bunkering?:boolean;replayLabel?:string};
export function MapScene({region,reset,exaggeration,trafficProgress,selectedShip=0,singleShip=false,bunkering=false,replayLabel=""}:MapProps){ const {t,lang}=useLocale();
 const arctic=region==='arctic';
 const trafficState=useRef({trafficProgress,selectedShip,bunkering,replayLabel});useEffect(()=>{trafficState.current={trafficProgress,selectedShip,bunkering,replayLabel}});
 const host=useRef<HTMLDivElement>(null),pose=useRef<{key:string;position:THREE.Vector3;target:THREE.Vector3}|null>(null),[data,setData]=useState<Coastlines|null>(null),[terrain,setTerrain]=useState<TerrainData|null>(null),[polarLand,setPolarLand]=useState<WorldLand|null>(null),[failure,setFailure]=useState('');
 useEffect(()=>{if(arctic)return;const a=new AbortController();fetch('/data/coastlines.json',{signal:a.signal}).then(r=>{if(!r.ok)throw Error();return r.json() as Promise<Coastlines>}).then(setData).catch(e=>{if(e.name!=='AbortError')setFailure(t("지도를 불러오지 못했습니다. 새로고침해 주세요."))});return()=>a.abort()},[arctic,t]);
 useEffect(()=>{const a=new AbortController();
  if(region==='arctic')fetch('/data/world-land.json',{signal:a.signal}).then(r=>{if(!r.ok)throw Error();return r.json() as Promise<WorldLand>}).then(d=>{setPolarLand(d);setFailure('')}).catch(e=>{if(e.name!=='AbortError')setFailure(t("지도를 불러오지 못했습니다. 새로고침해 주세요."))});
  else fetch('/data/terrain/'+region+'.json',{signal:a.signal}).then(r=>{if(!r.ok)throw Error();return r.json() as Promise<TerrainData>}).then(d=>{setTerrain(d);setFailure('')}).catch(e=>{if(e.name!=='AbortError')setFailure(t("고도 자료를 불러오지 못했습니다. 새로고침해 주세요."))});
  return()=>a.abort()},[region,t]);
 useEffect(()=>{
  const arctic=region==='arctic';if(!host.current||(arctic?!polarLand:!data||!terrain||terrain.region!==region))return;const el=host.current,cfg=regions[region];let renderer:THREE.WebGLRenderer|SVGRenderer;let software=false;
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.8}catch{renderer=new SVGRenderer();renderer.setQuality('low');software=true}
  renderer.domElement.setAttribute('aria-label',arctic?t("북극 평면 해안선과 설명용 경유점 위 선박 이동. 고도·해빙·수심 미포함."):t("{0} 지형 위 {1}의 설명용 이동, 높이 {2}배",t(cfg.title),singleShip?t("항차 기록 선박"):t("선박 3척"),exaggeration));renderer.domElement.dataset.region=region;renderer.domElement.dataset.terrain=arctic?'none':'dem';renderer.domElement.dataset.cameraStyle='oblique-regional';renderer.domElement.setAttribute('role','img');renderer.domElement.dataset.renderer=software?'compatible-map':'webgl-map';el.appendChild(renderer.domElement);
  const scene=new THREE.Scene();scene.background=new THREE.Color('#0b2533');const camera=new THREE.PerspectiveCamera(38,1,.1,700);camera.position.set(18,singleShip?135:110,singleShip?135:125);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=30;controls.maxDistance=arctic?390:290;controls.maxPolarAngle=Math.PI*.42;controls.target.set(0,0,singleShip?8:0);if(pose.current?.key===region+':'+reset){camera.position.copy(pose.current.position);controls.target.copy(pose.current.target)}
  scene.add(new THREE.AmbientLight('#f1ead4',software?.6:.85));const sun=new THREE.DirectionalLight('#fff5de',software?.85:2.0);sun.position.set(-70,100,-30);scene.add(sun);
  const cosine=Math.cos(cfg.center[1]*Math.PI/180),scale=120/((cfg.bounds[2]-cfg.bounds[0])*cosine);
  const xy=arctic?arcticMapProject:([lon,lat]:number[]):Coordinates=>[(lon-cfg.center[0])*cosine*scale,(lat-cfg.center[1])*scale];const world=(coords:Coordinates)=>{const [x,y]=xy(coords);return new THREE.Vector3(x,.12+(!arctic&&terrain?terrainHeight(terrain,...coords)*scale/111320*exaggeration:0),-y)};
  const polygons=arctic?arcticCoastlinePolygons(polarLand!):data!.regions[region].polygons.map(poly=>poly.map(ring=>ring.map(xy)));
  const top=software?new THREE.MeshBasicMaterial({color:'#83927b',side:THREE.DoubleSide}):new THREE.MeshLambertMaterial({color:'#83927b',side:THREE.DoubleSide}),side=new THREE.MeshLambertMaterial({color:'#526268',side:THREE.DoubleSide});
  polygons.forEach(rings=>{const s=new THREE.Shape(rings[0].map(p=>new THREE.Vector2(...p)));rings.slice(1).forEach(r=>s.holes.push(new THREE.Path(r.map(p=>new THREE.Vector2(...p)))));const g=software?new THREE.ShapeGeometry(s):new THREE.ExtrudeGeometry(s,{depth:.05,bevelEnabled:false,steps:1,curveSegments:1});g.rotateX(-Math.PI/2);const mesh=new THREE.Mesh(g,software?top:[top,side]);if(software){mesh.position.y=.05;mesh.renderOrder=90}scene.add(mesh);
   rings.forEach(r=>{const points=r.map(([x,y])=>new THREE.Vector3(x,.09,-y));const coast=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:'#d4d7b8',transparent:true,opacity:.6}));coast.renderOrder=110;scene.add(coast)})
  });
  if(!arctic&&terrain)scene.add(makeTerrain(terrain,cfg,scale,exaggeration,software));
  const h=(cfg.bounds[3]-cfg.bounds[1])*scale;const sea=new THREE.Mesh(new THREE.PlaneGeometry(arctic?136:126,arctic?136:h+6),new THREE.MeshBasicMaterial({color:'#164457',side:THREE.DoubleSide}));sea.rotation.x=-Math.PI/2;sea.position.y=-.15;sea.renderOrder=-1000;scene.add(sea);
  // Shared oblique map stage and grid across all regions; Arctic has no DEM.
  const grid=new THREE.GridHelper(180,18,'#2c6674','#25525e');grid.position.y=.05;grid.renderOrder=-999;grid.material.transparent=true;grid.material.opacity=.3;scene.add(grid);
  const focus=world(cfg.focus);const ring=new THREE.Mesh(new THREE.RingGeometry(2.3,2.45,48),new THREE.MeshBasicMaterial({color:'#c6f36c',side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.copy(focus);ring.position.y=focus.y+.05;ring.renderOrder=120;scene.add(ring);
  const tick=new THREE.Line(new THREE.BufferGeometry().setFromPoints([focus.clone(),focus.clone().add(new THREE.Vector3(0,7,0))]),new THREE.LineBasicMaterial({color:'#c6f36c'}));tick.renderOrder=120;scene.add(tick);
  const labels:{el:HTMLSpanElement;pos:THREE.Vector3;priority:number}[]=[];const addLabel=(name:string,coords:Coordinates,kind:string)=>{const d=document.createElement('span');d.className='map-label '+kind;d.textContent=t(name);el.appendChild(d);labels.push({el:d,pos:world(coords).add(new THREE.Vector3(0,kind==='focus'?8:1,0)),priority:kind==='focus'?90:kind==='sea'?30:kind==='port'?20:10})};
  cfg.labels.forEach(([name,lon,lat,kind])=>addLabel(name,[lon,lat],kind));addLabel(cfg.title,cfg.focus,'focus');
  const traffic=makePassageTraffic(region,xy,singleShip);scene.add(traffic.group);
  const startLabel=document.createElement('span');startLabel.className='map-label endpoint-label';startLabel.textContent=t('출발 지점');el.appendChild(startLabel);labels.push({el:startLabel,pos:traffic.start.clone().add(new THREE.Vector3(0,2,0)),priority:80});
  const endLabel=document.createElement('span');endLabel.className='map-label endpoint-label destination-label';el.appendChild(endLabel);labels.push({el:endLabel,pos:traffic.destination.clone().add(new THREE.Vector3(0,8,0)),priority:80});
  const shipLabel=document.createElement('span');shipLabel.className='map-label traffic-ship-label';el.appendChild(shipLabel);
  let lastProgress=-1,lastSelected=-1,lastDraw=0,lastLabel='',lastBunkering=false;
  let raf=0,dirty=true;controls.addEventListener('change',()=>dirty=true);const size=()=>{renderer.setSize(el.clientWidth,el.clientHeight);camera.aspect=el.clientWidth/el.clientHeight;if(arctic)camera.zoom=Math.min(1,camera.aspect);camera.updateProjectionMatrix();dirty=true};const ro=new ResizeObserver(size);ro.observe(el);size();
  const draw=(now=0)=>{raf=requestAnimationFrame(draw);if(document.hidden)return;controls.update();const state=trafficState.current;if(lastProgress!==state.trafficProgress||lastSelected!==state.selectedShip||lastLabel!==state.replayLabel||lastBunkering!==state.bunkering)dirty=true;if(!dirty||(software&&now-lastDraw<90))return;lastDraw=now;
   endLabel.textContent=singleShip&&state.trafficProgress>=1?(lang==='en'?'✓ Arrived · illustrative destination':'✓ 도착 · 설명용 목적지'):(lang==='en'?'⚑ Illustrative destination':'⚑ 설명용 목적지');
   const positions=traffic.update(state.trafficProgress,state.selectedShip,state.bunkering);lastProgress=state.trafficProgress;lastSelected=state.selectedShip;
   const selected=positions[state.selectedShip];shipLabel.textContent=singleShip?(state.replayLabel||t("체험 선박")):t("선박 ")+(state.selectedShip+1)+t(" · 설명용");lastLabel=state.replayLabel;lastBunkering=state.bunkering;
   renderer.domElement.dataset.trafficProgress=state.trafficProgress.toFixed(5);renderer.domElement.dataset.selectedShip=String(state.selectedShip+1);renderer.domElement.dataset.shipPosition=selected.position.toArray().map(n=>n.toFixed(5)).join(',');
   renderer.render(scene,camera);
   const currentLabels=[...labels,{el:shipLabel,pos:selected.position.clone().add(new THREE.Vector3(0,4,0)),priority:100}];
   const boxes=currentLabels.flatMap((label,id)=>{
    label.el.style.visibility='hidden';
    const p=label.pos.clone().project(camera);
    return p.z < -1||p.z>1||Math.abs(p.x)>.98||Math.abs(p.y)>.98?[]:[{id,x:(p.x+1)/2*el.clientWidth,y:(1-p.y)/2*el.clientHeight,width:label.el.offsetWidth,height:label.el.offsetHeight,priority:label.priority}];
   });
   const placements=singleShip||arctic?layoutMapLabels(boxes,el.clientWidth,el.clientHeight):boxes.map(box=>({...box,visible:true}));
   for(const placement of placements){
    const label=currentLabels[placement.id].el;
    label.style.left=placement.x+'px';label.style.top=placement.y+'px';label.style.visibility=placement.visible?'visible':'hidden';
   }
   dirty=false};draw();
  return()=>{pose.current={key:region+':'+reset,position:camera.position.clone(),target:controls.target.clone()};cancelAnimationFrame(raf);ro.disconnect();controls.dispose();disposeScene(scene);if(renderer instanceof THREE.WebGLRenderer)renderer.dispose();renderer.domElement.remove();labels.forEach(l=>l.el.remove());shipLabel.remove()}
 },[data,terrain,polarLand,region,reset,exaggeration,singleShip,lang,t]);
 return <div className="geography-canvas" ref={host}>{((region==='arctic'?!polarLand:!data||!terrain||terrain.region!==region)||failure)&&<p className="map-loading" role={failure?'alert':'status'}>{failure||(region==='arctic'?t("북극 해안선을 불러오는 중…"):t("해안선과 고도 자료를 불러오는 중…"))}</p>}</div>
}

export function MapLabelKey({region}:{region:string}){
 const {t}=useLocale(),cfg=regions[region];
 return <details className="map-label-key"><summary>{t('지도 지명과 표시 안내')}</summary><p>{t('확대하거나 화면이 좁아지면 선박과 해협 이름을 우선 표시합니다. 가까운 라벨은 읽기 쉽게 조금 이동하며, 모든 지명은 여기에서 확인할 수 있습니다.')}</p><ul>{[cfg.title,...cfg.labels.map(label=>label[0]),'출발 지점','⚑ 설명용 목적지'].map(name=><li key={name}>{t(name)}</li>)}</ul></details>;
}

export default function Geography({onReplay,region,onRegionChange}:{onReplay:()=>void;region:string;onRegionChange:(region:string)=>void}){ const {t}=useLocale();
 const [reset,setReset]=useState(0),[stage,setStage]=useState("region"),[exaggeration,setExaggeration]=useState(8),[flight,setFlight]=useState<Flight|null>(null);const cfg=regions[region];
 const [playOverride,setTrafficPlaying]=useState<boolean|null>(null),[trafficSpeed,setTrafficSpeed]=useState(1),[trafficProgress,setTrafficProgress]=useState(0),[selectedShip,setSelectedShip]=useState(0);
 const autoPlay=useSyncExternalStore(subscribeMotion,readMotion,serverMotion);const trafficPlaying=playOverride??autoPlay;
 useEffect(()=>{if(!trafficPlaying||stage!=='region')return;let frame=0,last=0;const advance=(now:number)=>{if(last&&!document.hidden)setTrafficProgress(p=>(p+Math.min(now-last,100)/48000*trafficSpeed)%1);last=now;frame=requestAnimationFrame(advance)};frame=requestAnimationFrame(advance);return()=>cancelAnimationFrame(frame)},[trafficPlaying,trafficSpeed,stage]);
 function choose(key:string){setTrafficProgress(0);onRegionChange(key);if(stage==="world")setFlight({region:key})}
 const arrive=useCallback(()=>{setStage("region");setFlight(null)},[]);
 return <section className="regional-exhibit">
 <nav className="region-navigation" aria-label={t("지역 선택")}><div className="region-nav-heading"><Button variant="outline" className="world-back" onClick={()=>{setStage("world");setFlight(null)}}><Globe2 size={16}/>{t("전체 위치 보기")}</Button><strong>{t("우리 연구와 연결된 지역")}</strong><span>{t("해외 통항량 자료 6곳 + 울산항 + 합성 북극 항로")}</span></div><div className="region-buttons">{Object.entries(regions).map(([key,r],i)=><button key={key} type="button" aria-pressed={region===key} onClick={()=>choose(key)}><span className="region-number">{String(i+1).padStart(2,'0')}</span><span><strong>{t(r.title)}</strong><small>{t(r.badge)}</small></span><ArrowUpRight size={16}/></button>)}</div><p>{t("지역을 선택하면 그 지형 위로 배들이 지나갑니다. 이동 경로·선박 크기·통항 수는 설명용이며 실제 교통량이 아닙니다.")}</p></nav>
 {stage==="world"?<Globe regions={regions} region={region} flight={flight} onArrive={arrive} onChoose={choose}/>:<div className="geography-workspace region-arrival"><header className="map-header"><div className="map-heading"><p className="kicker">{cfg.en}</p><h1>{t(cfg.title)}</h1><p>{t(cfg.connection)}</p></div><div className="map-toolbar"><span><Compass size={16}/>{region==='arctic'?t("북극 중심 평면 지도 · 고도·해빙 미포함"):t("입체 지형 · 북쪽 방향은 회전 가능")}</span><Button size="icon" variant="outline" aria-label={t("지도 시점 초기화")} onClick={()=>setReset(n=>n+1)}><RotateCcw/></Button></div></header><div className="map-height-bar">{region==='arctic'?<p className="map-flat-note">{t("평면 해안선 · 직접 배치한 해양 경유점 · 실제 항해에 사용할 수 없습니다.")}</p>:<div className="terrain-controls"><span>{t("지형 높이")}</span>{[1,4,8,12].map(v=><button key={v} aria-pressed={exaggeration===v} onClick={()=>setExaggeration(v)}>{v===1?t("실제 비율"):v+t("× 강조")}</button>)}<small>{t("고도 색상: 저지대 → 산악 · 식생 표현 아님")}</small></div>}</div><div className="geography-map"><MapScene region={region} reset={reset} exaggeration={exaggeration} trafficProgress={trafficProgress} selectedShip={selectedShip}/><div className="map-information"><div className="passage-playback" aria-label={t("해협 지형 위 선박 이동 조작")}><div className="passage-playback-heading"><strong><Ship size={17}/>{region==='arctic'?t("북극 경유점 위 선박 이동"):t("지형 위 선박 통과")}</strong><span>{t("설명용 연출 · 실측 항적 아님")}</span></div><div className="passage-playback-actions"><Button variant="outline" onClick={()=>setTrafficPlaying(!trafficPlaying)} aria-label={trafficPlaying?t("해협 선박 일시정지"):t("해협 선박 재생")}>{trafficPlaying?<Pause size={16}/>:<Play size={16}/>} {trafficPlaying?t("일시정지"):t("재생")}</Button><Button variant="outline" onClick={()=>{setTrafficProgress(0);setTrafficPlaying(false)}} aria-label={t("해협 선박 처음부터")}><RotateCcw size={16}/>{t("처음부터")}</Button><label>{t("연출 속도 ")}<select value={trafficSpeed} onChange={e=>setTrafficSpeed(Number(e.target.value))}><option value={.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option></select></label></div><label className="passage-progress">{t("이동 위치")}<input aria-label={t("해협 선박 이동 위치")} type="range" min="0" max="999" value={Math.round(trafficProgress*999)} onChange={e=>{setTrafficPlaying(false);setTrafficProgress(Number(e.target.value)/1000)}}/></label><div className="passage-ship-picks"><span>{t("강조할 선박")}</span>{[0,1,2].map(n=><button key={n} type="button" aria-pressed={selectedShip===n} onClick={()=>setSelectedShip(n)}>{t("선박 ")}{n+1}</button>)}</div></div><div className="map-legend"><span><i/>{t("해안선")}</span><span><i/>{t("선택한 선박")}</span><span>{t("점선: 설명용 통과선")}</span><span>{t("깃발: 설명용 목적지")}</span><span>{t("드래그 회전 · 스크롤 확대")}</span></div><p className="map-source">Made with <a href="https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/" target="_blank" rel="noreferrer">Natural Earth 1:10m</a>{region==='arctic'?t(" · 북극 중심 투영 · 고도·해빙·수심 미포함"):<> · <a href="/data/terrain-attribution.txt" target="_blank" rel="noreferrer">{t("Mapzen / AWS 고도 · 출처")}</a> {t(" · 높이 ")}{exaggeration}{t("× · 수심 미표현")}</>}</p></div></div>
 <aside className="geography-panel"><p className="eyebrow">{t("선택한 지역의 자료와 실험")}</p><span className="evidence-badge">{t(cfg.badge)}</span><h2>{t(cfg.title)}</h2><div className="connection"><MapPin size={18}/>{t(cfg.connection)}</div><p className="geo-description">{t(cfg.description)}</p><p className="passage-explanation">{region==='arctic'?t("점선은 바렌츠해에서 베링해협 방향으로 직접 배치한 해양 경유점을 연결합니다. 선박 3척은 같은 설명용 선을 따라 움직이며, 실제 교통량·속도·소요시간을 나타내지 않습니다."):t("이 지도에서 배의 이동을 따라가며 양쪽 육지와 통로의 위치를 살펴보세요. 선박 3척은 설명을 위해 배치했습니다. 연료·비용 수치는 아래의 별도 합성 실험 기록에서 확인합니다.")}{region==='suez'&&<><br/>{t("수에즈의 좁은 수로는 축척상 생략되어 있어, 파란 통과선을 실제 폭보다 넓게 표시했습니다.")}</>}</p><div className="geo-boundary"><Info size={18}/><div><strong>{t("프로젝트에서 어떻게 쓰였나요?")}</strong><p>{t(cfg.note)}</p></div></div><div className="geo-question"><span>{region==='arctic'?t("북극 연료 조건 실험"):t("합성 실험 기록 보기")}</span><h3>{t("급유 방식이 달라지면")}<br/>{t("지출과 잔량은 어떻게 될까?")}</h3><p>{region==='arctic'?t("입력한 가정에 따른 소비·구매 후보를 검토합니다. 기존 30단계 기록과는 독립된 계산입니다."):t("같은 합성 조건에서 비교한 네 가지 정책의 기록을 살펴보세요.")}</p><Button onClick={onReplay}><Ship size={17}/>{region==='arctic'?t("북극 항로에서 조건 실험"):t("이 지형에서 운항 체험 ")}<ArrowUpRight size={17}/></Button></div><p className="geo-source"><a href={cfg.source} target="_blank" rel="noreferrer">{region==='arctic'?t("Natural Earth 해안선 출처"):region==='ulsan'?t("울산항만공사 자료 출처"):t("ONS 6개 지역 자료 출처")} <ArrowUpRight size={13}/></a>{region==='arctic'?t("북극 지도에는 공개 해안선만 사용했습니다. 해빙·고도·수심·항로 인허가 정보는 없으며, 경유점과 선박 이동은 합성 계산의 항해 검증이 아닙니다."):t("지형은 공개 고도 자료를 축소·강조한 위치 설명용입니다. 수심·실제 선박 통항로와 실험의 물리 모델은 포함하지 않습니다. 지명을 바꿔도 실험 결과는 바뀌지 않습니다.")}</p></aside></div>}</section>
}
