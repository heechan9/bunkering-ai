'use client';
import {useLocale} from '@/lib/locale';
import Link from 'next/link';

export default function ArcticScenarioEntry(){
 const {lang}=useLocale(),en=lang==='en';
 return <section className="arctic-entry" aria-label={en?'Arctic-inspired synthetic scenarios':'북극항로 가상 시나리오'}>
  <div><span className="scenario-tag">{en?'SYNTHETIC SCENARIO':'가상 시나리오'}</span><h2>{en?'Explore Arctic-inspired scenarios':'북극항로 가상 시나리오 체험'}</h2>
   <p>{en?'Compare Normal, Delay + higher consumption, and Intermediate supply unavailable under the same starting conditions.':'같은 시작 조건에서 정상, 지연·소모 증가, 중간 급유 불가의 세 가지 가상 사례를 비교합니다.'}</p>
   <p className="arctic-entry-boundary">{en?'Synthetic examples only. Not validation of real Arctic navigation or safety; no savings claim.':'가상 사례 전용 · 실제 북극항로 운항·안전 검증이 아니며 절감을 입증하지 않습니다.'}</p>
  </div>
  <Link className="arctic-entry-link" href="/arctic">{en?'Open Arctic scenarios →':'북극 가상 시나리오 열기 →'}</Link>
 </section>;
}
