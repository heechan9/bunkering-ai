'use client';
import {useLocale} from '@/lib/locale';
import report from '@/public/data/hanbada-review.json';

export default function AbLogReview(){
 const {lang}=useLocale();const en=lang==='en';
 const rows=[
  [en?'Upper ROB':'상단 ROB',report.opening_rob+' M/T',report.evidence.opening],
  [en?'Reported consumption':'기재 소비량',report.consumption+' M/T',report.evidence.consumption],
  [en?'Lower ROB':'하단 ROB',report.closing_rob+' M/T',report.evidence.closing],
  [en?'Summary consumption sum':'요약표 소비량 합계',Number(report.summary_consumption_sum).toFixed(1)+' M/T',report.evidence.summary],
  [en?'Daily selected numeric sum':'일별표 선택 범위 숫자 합계',Number(report.daily_selected_sum).toFixed(1)+' kL',report.evidence.daily],
 ];
 return <section className="voyage-review" aria-labelledby="ab-log-title">
  <h2 id="ab-log-title">{en?'HANBADA AB-LOG review':'한바다호 AB-LOG 검토'}</h2>
  <p>{en?'May 2026 record · Provider clarification applied':'2026년 5월 기록 · 제공기관 최종 회신 반영'}</p>
  <p>{en?'Summary consumption is calculated from the ROB difference. Its arithmetic agreement is not independent measurement validation. Blank supply cells remain unknown; policy safety and savings are not validated.':'요약 소비량은 ROB 차이로 산출된 값입니다. 산술 일치는 독립 계측 검증이 아닙니다. 빈 급유 칸은 미확인으로 유지하며 정책 안전성·비용절감은 검증하지 않았습니다.'}</p>
  <div className="review-table"><table><thead><tr>{(en?['Item','Recorded value','Cell evidence']:['항목','기록값','근거 셀']).map(x=><th scope="col" key={x}>{x}</th>)}</tr></thead><tbody>{rows.map(([name,value,cell])=><tr key={name}><th scope="row">{name}</th><td>{value}</td><td>{cell}</td></tr>)}</tbody></table></div>
  <p><strong>{en?'Daily comparison on hold':'일별표 대조 보류'}</strong> — {en?'Daily values are kL; summary values are M/T. Density, volume reference conditions and time alignment remain unconfirmed. Do not compare directly. Sheet1 is unrelated and its 0.95 factor is excluded.':'일별표는 kL, 요약표는 M/T입니다. 밀도·부피 기준 조건·집계 시간 정합성이 미확인이라 직접 비교하지 않습니다. Sheet1은 무관한 시트이며 ×0.95 환산은 제외합니다.'}</p>
  <details><summary>{en?'Outstanding checks and provenance':'확인할 사항과 출처'}</summary>
   <p>{en?'The provider confirmed May 2026 and that the header date is the monthly submission date. Opening ROB around May 6 15:54, closing around 13:00 and the noon berthing explanation are provider estimates, not verified timestamps.':'제공기관이 2026년 5월 자료이며 상단 날짜는 월말 제출일임을 확인했습니다. 초기 ROB 5월 6일 15:54경·종료 약 13시경 및 정오 접안 설명은 담당자 추정으로, 확정 시각이 아닙니다.'}</p>
   <p>{en?'Source workbook is retained privately; the download contains aggregate checks and cell references only.':'원본 파일은 공개하지 않으며 다운로드에는 집계 검산과 근거 셀만 포함합니다.'}</p>
   <p>{en?'Submission date':'제출일'}: {report.record_date} · {report.voyage_id}</p>
  </details>
  <a href="/data/hanbada-review.json" download="hanbada-review.json">{en?'Download review JSON':'검토 결과 JSON 다운로드'}</a>
 </section>;
}
