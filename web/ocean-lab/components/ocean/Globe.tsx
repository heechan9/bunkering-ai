// @ts-nocheck
'use client';
import {useLocale,LocaleProvider} from '@/lib/locale';
import {useEffect,useMemo,useRef,useState} from 'react';
import {geoArea,geoDistance,geoGraticule10,geoOrthographic,geoPath} from 'd3-geo';
import {Button} from '@/components/ui/button';
import {ArrowLeft,ArrowRight,Globe2,MapPin} from 'lucide-react';

const areas=[['world','세계',[65,18],1],['europe','유럽·아프리카',[20,20],1.18],['west','서아시아',[49,24],1.5],['east','동아시아',[122,29],1.5]];
const continentLabels=[['아프리카',20,1],['유럽',17,50],['아시아',88,47],['오세아니아',136,-26],['북아메리카',-105,47],['남아메리카',-61,-14]];
const graticule=geoGraticule10();
export default function Globe({regions,region,flight,onArrive,onChoose}){ const {t,lang,setLang}=useLocale();
 const [land,setLand]=useState(null),[error,setError]=useState(false),[camera,setCamera]=useState({lon:65,lat:18,zoom:1}),[area,setArea]=useState('world'),[small,setSmall]=useState(false);
 useEffect(()=>{const mq=matchMedia('(max-width:800px)');const update=()=>setSmall(mq.matches);update();mq.addEventListener('change',update);return()=>mq.removeEventListener('change',update)},[]);
 const current=useRef(camera),drag=useRef(null),raf=useRef(0);current.current=camera;
 useEffect(()=>{const a=new AbortController();fetch('/data/world-land.json',{signal:a.signal}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>{const polys=d.geometry.coordinates.map(c=>{const p={type:'Polygon',coordinates:c};return geoArea(p)>2*Math.PI?c.map(r=>r.slice().reverse()):c});setLand({...d,geometry:{type:'MultiPolygon',coordinates:polys}})}).catch(e=>{if(e.name!=='AbortError')setError(true)});return()=>a.abort()},[]);
 function animate(center,zoom,done){cancelAnimationFrame(raf.current);const from=current.current;let delta=((center[0]-from.lon+540)%360)-180;const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;const duration=reduced?0:1100;let start;
  const tick=t=>{if(start===undefined)start=t;const p=duration?Math.min(1,(t-start)/duration):1;const e=p*p*(3-2*p);setCamera({lon:from.lon+delta*e,lat:from.lat+(center[1]-from.lat)*e,zoom:from.zoom+(zoom-from.zoom)*e});if(p<1)raf.current=requestAnimationFrame(tick);else done?.()};raf.current=requestAnimationFrame(tick);
 }
 useEffect(()=>{if(flight)animate(regions[flight.region].center,2.15,()=>onArrive());return()=>cancelAnimationFrame(raf.current)},[flight]);
 useEffect(()=>()=>cancelAnimationFrame(raf.current),[]);
 const projection=useMemo(()=>geoOrthographic().rotate([-camera.lon,-camera.lat]).translate([480,340]).scale(270*camera.zoom).clipAngle(90).precision(.4),[camera]);
 const path=geoPath(projection);const visible=coords=>geoDistance([camera.lon,camera.lat],coords)<Math.PI/2-.05;
 const move=(lon,lat)=>{if(flight)return;cancelAnimationFrame(raf.current);setCamera(c=>({...c,lon:c.lon+lon,lat:Math.max(-75,Math.min(75,c.lat+lat))}))};
 return <div className="world-workspace"><div className="world-map"><div className="world-caption"><p className="kicker">GLOBAL MARITIME CONTEXT</p><h1>{t("세계에서 해협까지.")}</h1><p>{t("같은 바다 위, 서로 다른 연결 지점.")}</p></div>
 <svg className="world-globe" viewBox={small?"180 0 600 680":"0 0 960 680"} role="img" aria-label={t("드래그로 회전하는 세계 지구본")} tabIndex={0}
 onKeyDown={e=>{const d={ArrowLeft:[-12,0],ArrowRight:[12,0],ArrowUp:[0,10],ArrowDown:[0,-10]}[e.key];if(d){e.preventDefault();move(...d)}}}
 onPointerDown={e=>{if(flight||e.target.closest('[data-region]'))return;drag.current=[e.clientX,e.clientY];e.currentTarget.setPointerCapture(e.pointerId)}}
 onPointerMove={e=>{if(!drag.current)return;const [x,y]=drag.current;move((x-e.clientX)*.22,(e.clientY-y)*.18);drag.current=[e.clientX,e.clientY]}}
 onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null}>
 <defs><radialGradient id="globeOcean" cx="35%" cy="30%"><stop offset="0" stopColor="#285f70"/><stop offset=".65" stopColor="#103645"/><stop offset="1" stopColor="#061c28"/></radialGradient><radialGradient id="globeShade" cx="33%" cy="27%" r="75%"><stop offset=".35" stopColor="#061922" stopOpacity="0"/><stop offset="1" stopColor="#020e17" stopOpacity=".68"/></radialGradient></defs>
 <path d={path({type:'Sphere'})} fill="url(#globeOcean)" stroke="#6597a6" strokeWidth="1.5"/>
 {land&&<path d={path(land)} fill="#82a395" stroke="#acc2a3" strokeWidth=".5"/>}
 <path d={path(graticule)} fill="none" stroke="#8ab2bd" strokeWidth=".55" opacity=".25"/>
 <path d={path({type:'Sphere'})} fill="url(#globeShade)" pointerEvents="none"/>
 {continentLabels.filter(([,lon,lat])=>visible([lon,lat])).map(([name,lon,lat])=>{const p=projection([lon,lat]);return <text key={t(name)} x={p[0].toFixed(3)} y={p[1].toFixed(3)} className="continent-label" textAnchor="middle">{t(name)}</text>})}
 {Object.entries(regions).filter(([,r])=>visible(r.focus)).map(([key,r],i)=>{const p=projection(r.focus);const active=region===key;return <g data-region={key} key={key} transform={`translate(${p[0].toFixed(3)},${p[1].toFixed(3)})`} className="globe-pin" onClick={()=>!flight&&onChoose(key)}><title>{t(r.title)+t(" 지도 열기")}</title><circle r="17" fill="transparent"/><circle r={active?10:6} fill="#c6f36c" fillOpacity={active?.24:1} stroke="#dffcb0"/><circle r="3" fill="#e9ffd0"/><text x={key==='hormuz'||key==='ulsan'?14:-14} y={key==='bab'?23:-13} textAnchor={key==='hormuz'||key==='ulsan'?'start':'end'}>{t(r.title)}</text></g>})}
 </svg>
 {!land&&<p className="world-loading" role={error?'alert':'status'}>{error?t("세계 지도를 불러오지 못했습니다. 지역 버튼으로 상세 지도를 열 수 있습니다."):t("세계 해안선을 불러오는 중…")}</p>}
 <div className="world-areas" role="group" aria-label={t("대륙 시점")}>{areas.map(([id,label,center,zoom])=><Button key={id} variant="ghost" aria-pressed={area===id} disabled={!!flight} onClick={()=>{setArea(id);animate(center,zoom)}}>{t(label)}</Button>)}</div>
 <div className="world-controls"><Button size="icon" variant="outline" aria-label={t("지구본 왼쪽 회전")} disabled={!!flight} onClick={()=>move(-20,0)}><ArrowLeft/></Button><span>{t("드래그 또는 방향키로 회전")}</span><Button size="icon" variant="outline" aria-label={t("지구본 오른쪽 회전")} disabled={!!flight} onClick={()=>move(20,0)}><ArrowRight/></Button></div>
 <p className="world-source">{t("Natural Earth 해안선 · 지구 곡면 투영 · 실제 고도·수심 미포함")}</p>
 {flight&&<div className="world-flight" role="status"><MapPin size={17}/>{t(regions[flight.region].title)} {t(" 주변으로 이동 중")}</div>}
 </div><aside className="world-panel"><Globe2 size={27}/><p className="kicker">EXPLORE THE CONNECTIONS</p><h2>{t("어디의 자료를")}<br/>{t("살펴본 연구일까?")}</h2><p>{t("위의 지역 버튼이나 지구본의 위치 표시를 선택하면 주변 지형과 자료 설명으로 이어집니다.")}</p><div className="world-evidence"><strong>{t("6개 해외 통항 지역")}</strong><p>{t("ONS의 통항량 자료가 다루는 지역입니다. 실제 항차별 급유 기록은 아닙니다.")}</p><strong>{t("1개 국내 업무 자료")}</strong><p>{t("울산항 벙커링정박지 신청현황으로 현장 업무변수를 살펴봤습니다.")}</p></div><p className="world-small">{t("세계·지역 지도는 연구의 지리적 맥락을 설명합니다. 급유 실험은 별도의 합성환경 기록입니다.")}</p></aside></div>
}
