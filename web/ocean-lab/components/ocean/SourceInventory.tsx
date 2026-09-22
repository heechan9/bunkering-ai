'use client';
import {useLocale} from '@/lib/locale';

const root='https://github.com/heechan9/bunkering-ai/blob/3b38e8adfb73fa9a31f150e56a3ebbe256bb840d/';
const sources=[
 {id:'simulation',ko:['합성환경 실험 결과','저장 결과·웹 수치 대조 완료','SCI는 합성 비용지수. 실선 비용절감 근거 아님'],en:['Synthetic experiments','Stored results checked against web figures','SCI is a synthetic cost index, not real-vessel savings'],path:'docs/technical/web_evidence_guard.md'},
 {id:'upa',ko:['울산항 정박지 신청자료','6,028행·8열 확인','벙커량 단위·실제 공급 여부 미확인. 소비·잔량·가격 없음'],en:['UPA anchorage applications','6,028 rows and 8 columns confirmed','Quantity unit and actual supply basis unconfirmed; no consumption, inventory or price'],path:'docs/data/upa_review_20260919.md'},
 {id:'minjae',ko:['민재 급유업무 관점 검토','수령·논문 v5.0 반영','팀 내 정성 검토. 공식 운항기준·현장 성능검증 아님'],en:['Minjae domain review','Received; incorporated in paper v5.0','Qualitative team review, not official operating standards or field validation'],path:'docs/technical/minjae_domain_review_20260920.md'},
 {id:'kmou',ko:['해기원 한바다호 AB-LOG','수령·요약표 조건부 검산','연도·ROB 시각·일별 집계 범위 미확인. 정책 실증 아님'],en:['KMOU HANBADA AB-LOG','Received; conditional summary check','Year, ROB timestamps and daily scope unconfirmed; not policy validation'],path:'docs/technical/hanbada_ab_log_design_20260922.md'},
];
export default function SourceInventory(){
 const {lang}=useLocale();const en=lang==='en';
 return <details className="voyage-review"><summary>{en?'Sources and confirmation status':'자료 출처·확인 상태'}</summary>
  <p>{en?'Project record as of 22 September 2026. Each link opens the supporting record with its stated evidence scope. Locally uploaded files are reviewed separately below.':'2026년 9월 22일 프로젝트 기록 기준입니다. 링크에서 해당 판단의 근거 기록을 확인할 수 있습니다. 직접 올린 파일은 아래 항차 CSV 검토에서 별도로 확인합니다.'}</p>
  <div className="review-table"><table><thead><tr>{(en?['Source','Confirmed status','Limits / needed information','Evidence']:['자료','확인 상태','한계·추가 필요 정보','근거']).map(h=><th scope="col" key={h}>{h}</th>)}</tr></thead><tbody>{sources.map(s=>{const v=en?s.en:s.ko;return <tr key={s.id}><th scope="row">{v[0]}</th><td>{v[1]}</td><td>{v[2]}</td><td><a href={(s.id==='kmou'?'https://github.com/heechan9/bunkering-ai/blob/main/':root)+s.path} target="_blank" rel="noreferrer">{en?'View record':'기록 보기'}</a></td></tr>})}</tbody></table></div>
 </details>;
}
