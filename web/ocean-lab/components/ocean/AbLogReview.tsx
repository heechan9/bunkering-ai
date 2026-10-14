'use client';
import {useLocale} from '@/lib/locale';
export default function AbLogReview(){
 const {lang}=useLocale(); const en=lang==='en';
 return <section className="voyage-review" aria-labelledby="ab-log-title">
  <h2 id="ab-log-title">{en?'Vessel-record review: public summary':'실선 자료 검토: 공개 요약'}</h2>
  <p>{en?'Provided vessel records were reviewed for unit consistency, arithmetic relationships and reporting-period alignment.':'제공받은 실선 자료의 단위, 산술 관계와 집계 기간 정합성을 검토했습니다.'}</p>
  <p>{en?'Original records, identifiers, detailed quantities, dates, cell references and derived detail downloads are not provided on this site.':'원본 기록, 식별정보, 상세 수치·날짜·근거 셀 및 상세 파생자료 다운로드는 이 사이트에서 제공하지 않습니다.'}</p>
  <p>{en?'Arithmetic agreement is not independent measurement validation. Mass–volume conversion and time alignment remain unverified; actual policy safety and cost savings have not been validated.':'산술 일치는 독립 계측 검증이 아닙니다. 질량·부피 환산과 시간 정합성은 미확인이고 실제 정책 안전성·비용절감은 검증하지 않았습니다.'}</p>
 </section>;
}
