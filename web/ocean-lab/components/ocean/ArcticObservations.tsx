'use client';

import {useEffect,useState} from 'react';
import {useLocale} from '@/lib/locale';
import {gridPoint,polarPoint,validIce,validTrack,type IceSnapshot,type ObservedTrack} from '@/lib/arctic-observations';
import styles from './ArcticObservations.module.css';

const line=(points:number[][])=>points.map((p,i)=>`${i?'L':'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ');
export default function ArcticObservations(){
  const {lang}=useLocale(),en=lang==='en';
  const [track,setTrack]=useState<ObservedTrack|null>(null),[ice,setIce]=useState<IceSnapshot|null>(null),[coast,setCoast]=useState<number[][][]>([]);
  const [loaded,setLoaded]=useState(false),[iceOn,setIceOn]=useState(false),[index,setIndex]=useState(0);
  useEffect(()=>{
    let cancelled=false;
    async function read(){
      const get=async(name:string)=>{try{const r=await fetch(`/data/arctic-observations/${name}.json`);if(!r.ok)return null;return await r.json();}catch{return null;}};
      const [t,i,c]=await Promise.all([get('track'),get('ice'),get('coastline')]);
      if(cancelled)return;
      if(validTrack(t))setTrack(t);
      if(validIce(i))setIce(i);
      if(c&&typeof c==='object'&&'paths' in c&&Array.isArray(c.paths)&&c.paths.every((path:unknown)=>Array.isArray(path)&&path.every((point:unknown)=>Array.isArray(point)&&point.length===2&&point.every(Number.isFinite))))setCoast(c.paths);
      setLoaded(true);
    }
    void read();return()=>{cancelled=true;};
  },[]);
  const point=track?.points[index],position=point?polarPoint(point[1],point[2]):null;
  const trackPath=track?line(track.points.map(p=>polarPoint(p[1],p[2]))):'';
  return <section className={styles.root} aria-labelledby="arctic-observations-title" data-arctic-observations>
    <header><span className={styles.eyebrow}>{en?'OBSERVATION REFERENCE · NOT MODEL INPUT':'실제 관측 참고 · 모델 입력과 별개'}</span><h2 id="arctic-observations-title">{en?'Explore an observed Arctic research-vessel track':'북극 연구선의 실제 항적 살펴보기'}</h2><p>{en?'PS155 is a research expedition, not a commercial Northern Sea Route transit. Its position observations do not validate the synthetic Buy/Wait fuel results above.':'PS155는 연구 항해이며, 상업용 북극해항로 통과 기록이 아닙니다. 실제 위치 관측은 위 구매·미구매 시뮬레이션의 연료 결과를 검증하지 않습니다.'}</p></header>
    {!track?<p role="status">{loaded?(en?'Track unavailable. No substitute route or invented observations are shown.':'항적을 불러올 수 없습니다. 대체 경로나 임의 관측값은 표시하지 않습니다.'):(en?'Loading verified observations…':'검증된 관측자료 불러오는 중…')}</p>:<div className={styles.layout}>
      <div>
        {iceOn&&ice&&<p className={styles.warning}>{en?'Track: July–August 2026 / Ice: ':'항적: 2026년 7~8월 / 해빙: '}{ice.date.slice(0,10)} · {en?'different dates':'서로 다른 날짜'}</p>}
        <svg className={styles.map} viewBox="0 0 640 640" role="img" aria-label={en?'Polar reference map with the observed Polarstern PS155 track':'Polarstern PS155 실제 항적을 표시한 북극 참고 지도'}>
          <defs><clipPath id="arctic-observation-clip"><circle cx="320" cy="320" r="305"/></clipPath></defs>
          <circle cx="320" cy="320" r="305" fill="#102632"/>
          <g clipPath="url(#arctic-observation-clip)">
            {[50,60,70,80].map(lat=><circle key={lat} cx="320" cy="320" r={Math.abs(polarPoint(lat,-45)[1]-320)} fill="none" stroke="#34505c" strokeDasharray="3 5"/>)}
            {[-135,-90,-45,0,45,90,135,180].map(lon=>{const p=polarPoint(48,lon);return <path key={lon} d={`M320,320L${p[0]},${p[1]}`} stroke="#34505c"/>;})}
            {iceOn&&ice&&ice.cells.map(([x,y,c],i)=>{const p=gridPoint(x,y);return <circle key={i} cx={p[0]} cy={p[1]} r="2.2" fill={`rgb(${Math.round(40+c*190)},${Math.round(80+c*160)},${Math.round(110+c*140)})`}/>;})}
            {coast.map((path,i)=><path key={i} d={line(path)} fill="none" stroke="#90a5a7" strokeWidth=".75"/>)}
            <path d={trackPath} fill="none" stroke="#ffbe60" strokeWidth="2"/>
            {position&&<circle cx={position[0]} cy={position[1]} r="5" fill="#fff" stroke="#e4a64e" strokeWidth="2"/>}
          </g>
          <text x="328" y="314" fill="#bcd0d6" fontSize="13">90°N</text>
          <text x="320" y="627" textAnchor="middle" fill="#bcd0d6" fontSize="12">EPSG:3411 · {en?'reference only':'참고용'}</text>
        </svg>
        <label className={styles.sliderLabel} htmlFor="observed-track-index">{en?'Recorded position':'기록된 위치'} · {index+1} / {track.rowCount.toLocaleString()}</label>
        <input className={styles.slider} id="observed-track-index" type="range" min="0" max={track.points.length-1} step="1" value={index} onChange={e=>setIndex(Number(e.target.value))} aria-valuetext={point?`${point[0]}, ${point[1]}, ${point[2]}`:undefined}/>
        <p className={styles.legend}>{en?'Amber: actual track · white: selected record · gray: coastlines':'주황: 실제 항적 · 흰 점: 선택 기록 · 회색: 해안선'}</p>
      </div>
      <div className={styles.details}>
        <dl><div><dt>{en?'Observation period':'관측 기간'}</dt><dd>{track.start.slice(0,10)} ~ {track.end.slice(0,10)}</dd></div><div><dt>{en?'Source records':'원본 위치 기록'}</dt><dd>{track.rowCount.toLocaleString()} · {en?'10-minute product':'10분 간격 제품'}</dd></div><div><dt>{en?'Selected source timestamp':'선택한 원본 시각'}</dt><dd>{point?.[0].replace('T',' ')}</dd></div><div><dt>{en?'Position (latitude / longitude)':'위치 (위도 / 경도)'}</dt><dd>{point?.[1].toFixed(5)}° / {point?.[2].toFixed(5)}°</dd></div><div><dt>{en?'Source-calculated 10-min speed':'원자료의 계산된 10분 평균 속력'}</dt><dd>{point?.[3]===null?'UNKNOWN':point?.[3]} kn</dd></div></dl>
        <p className={styles.note}>{en?'No measured fuel, bunkering prices or savings. Source times are preserved; no unverified time zone is added. The line connects sampled positions for display, not navigation.':'연료 실측·급유 가격·절감률은 없습니다. 원본 시각을 유지하며 확인되지 않은 시간대를 덧붙이지 않습니다. 위치를 이은 선은 화면 표시용이며 항해용이 아닙니다.'}</p>
        <div className={styles.ice}>
          <label><input type="checkbox" checked={iceOn} disabled={!ice} onChange={e=>setIceOn(e.target.checked)}/>{en?'Show historical ice reference':'과거 해빙 참고 표시'}</label>
          {ice?<><strong>{ice.date.slice(0,10)} · {en?'NOT the voyage date':'항해 시기와 다름'}</strong><p>{en?`Satellite-derived concentration, native ${ice.nativeResolutionKm} km grid, sampled every ${ice.sampleSpacingKm} km. Dots are sampled cells, not a continuous ice edge. Dark = 0%, light = 100%; missing/flagged cells omitted.`:`위성 기반 해빙 농도. 원본 ${ice.nativeResolutionKm} km 격자를 ${ice.sampleSpacingKm} km 간격으로 추출했습니다. 점은 추출한 격자이며 연속 빙연이 아닙니다. 어두움 0%, 밝음 100%, 결측·특수 표식은 제외합니다.`}</p><p>{en?'Each sample is a native 25 km cell, not a 200 km area average.':'각 값은 원본 25 km 격자의 값이며 200 km 영역 평균이 아닙니다.'}</p><p>{en?'The source sets concentrations below 10% to 0%; 0% does not certify ice-free water.':'원제품은 10% 미만 농도를 0%로 처리합니다. 0%가 무빙해역을 보장하지 않습니다.'}</p><p className={styles.warning}>{en?'Historical context only. Not current ice, not conditions during PS155, not a safe-route or fuel-risk estimate.':'과거 참고자료입니다. 현재 해빙도, PS155 당시 조건도 아니며 안전 항로·연료 위험 계산에 쓰지 않습니다.'}</p></>:<p>{en?'Ice observations unavailable; no replacement values.':'해빙 관측자료를 불러올 수 없습니다. 대체 수치는 넣지 않습니다.'}</p>}
        </div>
        <details><summary>{en?'Sources, licence and limitations':'출처·이용조건·한계'}</summary><p>{track.citation}</p><p><a href={track.url} target="_blank" rel="noreferrer">PANGAEA PS155</a> · <a href={track.licenseUrl} target="_blank" rel="noreferrer">{track.license}</a></p><p>{en?'Changes: TSV converted to JSON, positions projected for display. The full source TSV is included.':'변경: TSV를 JSON으로 변환하고 표시용 좌표 투영을 적용했습니다. 원본 TSV도 함께 제공합니다.'}</p><p><a href="/data/arctic-observations/PS155_10min.tsv" download>{en?'Download original TSV':'원본 TSV 내려받기'}</a></p><p><a href="https://coastwatch.pfeg.noaa.gov/erddap/griddap/nsidcG10016v3nh1day.html" target="_blank" rel="noreferrer">NOAA/NSIDC G10016 V3</a> · {en?'No constraints on data access or use (source metadata). V3 retired in June 2026.':'출처 메타데이터상 접근·이용 제한 없음. V3는 2026년 6월 종료된 제품입니다.'}</p>{ice&&<p>{ice.citation}</p>}<p>{en?'Coastlines: Natural Earth, public domain, simplified reference geometry.':'해안선: Natural Earth, 퍼블릭 도메인, 단순화한 참고 지형.'}</p></details>
      </div>
    </div>}
  </section>;
}
