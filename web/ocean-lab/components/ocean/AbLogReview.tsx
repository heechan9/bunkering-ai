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
  [en?'Daily selected numeric sum':'일별표 선택 범위 숫자 합계',Number(report.daily_selected_sum).toFixed(1)+(en?' (unit unconfirmed)':' (단위 미확인)'),report.evidence.daily],
 ];
 return <section className="voyage-review" aria-labelledby="ab-log-title">
  <h2 id="ab-log-title">{en?'HANBADA AB-LOG review':'한바다호 AB-LOG 검토'}</h2>
  <p>{en?'Received 22 September 2026 · Review pending':'2026년 9월 22일 수령 · 검토 진행 중'}</p>
  <p>{en?'The summary balances arithmetically if no fuel was supplied. Blank supply cells remain unknown. This does not validate independent measurements, policy safety or cost savings.':'급유가 없었다는 전달 내용을 조건으로 요약표 수지가 일치합니다. 빈 급유 칸은 미확인으로 유지합니다. 독립 실측값의 정확성·정책 안전성·비용절감을 검증한 결과는 아닙니다.'}</p>
  <div className="review-table"><table><thead><tr>{(en?['Item','Recorded value','Cell evidence']:['항목','기록값','근거 셀']).map(x=><th scope="col" key={x}>{x}</th>)}</tr></thead><tbody>{rows.map(([name,value,cell])=><tr key={name}><th scope="row">{name}</th><td>{value}</td><td>{cell}</td></tr>)}</tbody></table></div>
  <p><strong>{en?'Daily comparison on hold':'일별표 대조 보류'}</strong> — {en?'Periods, units and aggregation scopes are unconfirmed. The numeric difference cannot yet be interpreted as a fuel loss or recording error.':'기간·단위·집계 범위가 미확인입니다. 숫자의 차이를 연료 손실이나 기록 오류로 해석할 수 없습니다.'}</p>
  <details><summary>{en?'Outstanding checks and provenance':'확인할 사항과 출처'}</summary>
   <p>{en?'The message describes 2025; the workbook date and voyage identifier indicate 2026. ROB timestamps and whether consumption was independently measured remain unconfirmed.':'전달 메시지는 2025년, 파일 날짜와 항차 식별자는 2026년으로 연도 확인이 필요합니다. ROB의 기준 시각과 소비량의 독립 측정 여부도 미확인입니다.'}</p>
   <p>{en?'Source workbook is retained privately; the download contains aggregate checks and cell references only.':'원본 파일은 공개하지 않으며 다운로드에는 집계 검산과 근거 셀만 포함합니다.'}</p>
   <p>{en?'Record date':'기록 날짜'}: {report.record_date} · {report.voyage_id}</p>
  </details>
  <a href="/data/hanbada-review.json" download="hanbada-review.json">{en?'Download review JSON':'검토 결과 JSON 다운로드'}</a>
 </section>;
}
