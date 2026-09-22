'use client';
import {useLocale} from '@/lib/locale';
import report from '@/public/data/hanbada-review.json';
import comparison from '@/public/data/hanbada-comparison.json';

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
  <h3>{en?'Aggregate comparison and assumption sensitivity':'집계 직접 비교·가정 민감도 실험'}</h3>
  <p>{en?'Three selections of labeled day rows; these are not verified voyage time windows. Daily volumes are compared in kL. The ratio that matches 195.2 M/T is fitted, not measured fuel density.':'날짜 표기 행을 세 범위로 선택했습니다. 확정된 항차 시간 구간이 아닙니다. 일별 부피는 같은 kL 단위로 비교하며, 195.2 M/T에 맞추는 역산 비율은 실측 밀도가 아닙니다.'}</p>
  <div className="review-table"><table><thead><tr>{(en?['Selected days','M/E kL','G/E kL','Boiler kL','Total kL','Fitted ratio t/kL']:['선택 날짜','M/E kL','G/E kL','Boiler kL','합계 kL','역산 비율 t/kL']).map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{comparison.windows.map(w=><tr key={w.id}><th scope="row">{w.id.replace('days_','').replace('_','–')}</th><td>{Number(w.engine_volumes_kl.ME).toFixed(1)}</td><td>{Number(w.engine_volumes_kl.GE).toFixed(1)}</td><td>{Number(w.engine_volumes_kl.Boiler).toFixed(1)}</td><td>{Number(w.volume_kl).toFixed(1)}</td><td>{Number(w.density_required_to_match_t_per_kl).toFixed(6)}</td></tr>)}</tbody></table></div>
  <p>{en?'Selected days 1–5 total 2.7 kL; day 31 totals 19.7 kL. A close converted total does not establish matching periods or measurement accuracy.':'1~5일 선택 행은 2.7 kL, 31일 행은 19.7 kL입니다. 환산 총량이 비슷해져도 집계 기간이나 측정 정확성이 검증되는 것은 아닙니다.'}</p>
  <details><summary>{en?'View all 15 hypothetical scenarios':'가정 시나리오 15개 전체 보기'}</summary>
   <p>{en?'Analyst-selected density grid 0.800–0.900 t/kL, not observations, an approved physical range or a confidence interval. One common density is assumed across engines and days, without temperature correction. Sheet1 is excluded. Residual = hypothetical mass minus 195.2 M/T.':'0.800~0.900 t/kL는 분석자가 정한 산술 가정 격자이며 관측값·물성 적정 범위·신뢰구간이 아닙니다. 모든 기관·날짜에 공통 밀도를 가정하고 온도 보정은 하지 않았습니다. Sheet1은 제외했습니다. 잔차는 가정 환산량−195.2 M/T입니다.'}</p>
   <div className="review-table"><table><thead><tr>{(en?['Days','Assumed t/kL','Hypothetical t','Residual t','Residual %']:['날짜','가정 t/kL','가정 환산 t','잔차 t','잔차 %']).map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{comparison.density_scenarios.map(s=><tr key={s.window+s.assumed_density_t_per_kl}><th scope="row">{s.window.replace('days_','').replace('_','–')}</th><td>{s.assumed_density_t_per_kl}</td><td>{Number(s.hypothetical_mass_t).toFixed(3)}</td><td>{Number(s.residual_t).toFixed(3)}</td><td>{Number(s.residual_percent).toFixed(3)}</td></tr>)}</tbody></table></div>
   <p>{en?'Engine-level mass/volume ratios for days 1–31 differ: M/E 0.754457, G/E 0.964736, Boiler 0.977011 t/kL. Matching the total with one factor does not reconcile all engines. These ratios are not measured densities. No policy training or savings experiment was performed.':'1~31일 기관별 질량/부피 비율은 M/E 0.754457, G/E 0.964736, Boiler 0.977011 t/kL로 다릅니다. 하나의 계수로 총합을 맞춰도 기관별 정합성이 확인되지 않습니다. 이 비율은 실측 밀도가 아니며 정책 학습·비용절감 실험은 수행하지 않았습니다.'}</p>
   <a href="/data/hanbada-comparison.json" download="hanbada-comparison.json">{en?'Download comparison and scenarios':'집계 비교·시나리오 JSON 다운로드'}</a>
  </details>
  <details><summary>{en?'Outstanding checks and provenance':'확인할 사항과 출처'}</summary>
   <p>{en?'The provider confirmed May 2026 and that the header date is the monthly submission date. Opening ROB around May 6 15:54, closing around 13:00 and the noon berthing explanation are provider estimates, not verified timestamps.':'제공기관이 2026년 5월 자료이며 상단 날짜는 월말 제출일임을 확인했습니다. 초기 ROB 5월 6일 15:54경·종료 약 13시경 및 정오 접안 설명은 담당자 추정으로, 확정 시각이 아닙니다.'}</p>
   <p>{en?'Source workbook is retained privately; the download contains aggregate checks and cell references only.':'원본 파일은 공개하지 않으며 다운로드에는 집계 검산과 근거 셀만 포함합니다.'}</p>
   <p>{en?'Submission date':'제출일'}: {report.record_date} · {report.voyage_id}</p>
  </details>
  <a href="/data/hanbada-review.json" download="hanbada-review.json">{en?'Download review JSON':'검토 결과 JSON 다운로드'}</a>
 </section>;
}
