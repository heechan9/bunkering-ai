'use client';
import {useLocale} from '@/lib/locale';

const root='https://github.com/heechan9/bunkering-ai/blob/bc3293f06e4118e5d245a716b2402fe7080905b8';

export default function DecisionGuide(){
 const {lang}=useLocale();
 const en=lang==='en';
 return <section className="decision-guide" aria-labelledby="decision-guide-title">
  <h2 id="decision-guide-title">{en?'What can this comparison tell us?':'이 비교로 무엇을 판단할 수 있을까요?'}</h2>
  <p>{en?'Compare purchasing, remaining fuel and arrival under the same synthetic conditions. Real operating savings have not been validated.':'같은 합성 조건에서 구매량·남은 연료·도착 여부를 비교합니다. 실제 운항의 비용절감 효과는 검증하지 않았습니다.'}</p>
  <div className="decision-grid">
   <article><h3>{en?'For purchasing decisions':'구매 담당자의 관점'}</h3><p>{en?'Read expenditure alongside purchased fuel and ending inventory. More stock can explain higher spending; SCI does not deduct inventory value.':'구매지출과 구매량·최종잔량을 함께 보세요. 더 남긴 재고가 지출 차이를 설명할 수 있으며, SCI는 재고가치를 차감하지 않습니다.'}</p></article>
   <article><h3>{en?'For voyage planning':'운항 담당자의 관점'}</h3><p>{en?'Arrival and reserve margins are separate questions. Bunkering frequency shows repeated actions, not measured work time or operating cost.':'도착 여부와 안전여유는 별개입니다. 급유횟수는 반복 행동을 보여주지만 실제 작업시간이나 운영비를 측정한 값은 아닙니다.'}</p></article>
  </div>
  <details><summary>{en?'A finding that changed the interpretation':'결과 해석을 바꾼 검증 사례'}</summary>
   <p>{en?'Safe Stock was initially flagged below the reserve threshold. Inspecting transition records revealed a floating-point boundary effect. Reclassifying existing records with a tolerance removed those baseline violations; this was not retraining or evaluation in a corrected environment.':'Safe Stock은 처음에 안전선 미달로 집계됐습니다. 전이 기록을 확인하니 부동소수점 경계 효과가 있었고, 기존 기록에 허용오차를 적용한 재분류에서는 기본조건 미달이 사라졌습니다. 재학습이나 수정 환경에서의 새 평가 결과는 아닙니다.'}</p>
   <a href={root+'/docs/technical/submission_alignment_v3_0.md'} target="_blank" rel="noreferrer">{en?'Read the correction and evidence ↗':'정정 내용과 검증 근거 확인 ↗'}</a>
  </details>
  <details><summary>{en?'What still needs field evidence?':'현장 적용 전에 무엇을 더 확인해야 할까요?'}</summary>
   <p>{en?'Reserve rules, supply constraints and linked departure–purchase–consumption–arrival records require review. The Ulsan source-data review has been received and cross-checked. The team maritime review has also been received. HANBADA is confirmed as May 2026. Daily kL and summary M/T are distinct; ROB-derived consumption is an arithmetic check only.':'안전잔량 기준, 공급·작업 제약, 같은 항차의 출발잔량·급유·소비·도착잔량 연결을 확인해야 합니다. 울산항 원자료 검토는 수령·대조했습니다. 민재의 팀 내 해양 분야 검토도 수령했습니다. 한바다호는 2026년 5월 자료로 확인됐습니다. 일별 kL·요약 M/T를 구분하며 ROB 차감값의 산술 관계만 확인합니다.'}</p>
  </details>
  <details><summary>{en?'Ulsan data: what the review established':'울산항 자료 검토에서 확인한 것'}</summary>
   <p>{en?'The archived CSV contains 6,028 rows and 8 fields. Vessel identifiers, voyage consumption, departure/arrival fuel and prices are absent. The bunker quantity unit and whether it means requested or delivered volume remain unconfirmed.':'보관된 CSV는 6,028행·8개 항목입니다. 선박 식별자, 항차 소비량, 출발·도착잔량과 가격이 없으며, 벙커량의 단위와 신청량·실공급량 여부는 미확인입니다.'}</p>
   <p>{en?'There are 38 duplicate rows beyond the first occurrence, across 37 groups (75 rows in those groups). Year and voyage-number combinations also repeat. These facts do not identify duplicate applications or link records to the same voyage.':'첫 행을 제외한 추가 중복은 38행이며, 37개 그룹의 전체 75행에 해당합니다. 입항년도·입항항차 조합도 반복되므로 중복 신청 여부나 같은 항차를 확정할 수 없습니다.'}</p>
   <p>{en?'Used to understand operational data, not to validate real fuel balances. Source-data review: Kim Seung-hyeon; official-page cross-check and CSV recalculation: Codex.':'이 자료는 업무 맥락 파악에 활용하며 실측 연료수지 검증에 사용하지 않습니다. 김승현의 원자료 검토를 바탕으로 Codex가 공식 페이지 대조와 CSV 재계산을 수행했습니다.'}</p>
   <a href="https://www.data.go.kr/data/15132700/fileData.do" target="_blank" rel="noreferrer">{en?'Official data description ↗':'공식 자료 설명 ↗'}</a>
   {' · '}<a href="https://github.com/heechan9/bunkering-ai/blob/main/docs/data/upa_review_20260919.md" target="_blank" rel="noreferrer">{en?'Review and correction record ↗':'검토·정정 기록 ↗'}</a>
  </details>
  <details><summary>{en?'What the maritime review adds':'민재의 해양 분야 검토에서 보완한 점'}</summary>
   <p>{en?'A fixed tank percentage does not fully represent remaining voyage demand, unusable fuel or separate fuel grades. Arrival and reserve margin should be read separately.':'고정 탱크 비율만으로는 남은 항해의 소비량, 사용할 수 없는 잔량, 연료 종류별 차이를 충분히 표현하기 어렵습니다. 도착 여부와 안전여유를 구분해서 보세요.'}</p>
   <p>{en?'Priority missing constraints are port supply and fuel specifications, bunkering and waiting time, and minimum orders and fixed fees. These are proposed limitations to address, not constraints implemented in this simulation.':'우선 보완할 제약은 항만별 공급·연료 규격, 급유·대기시간, 최소 주문량·고정비입니다. 현재 시뮬레이션에 구현된 제약이 아니라 후속 보완 항목입니다.'}</p>
   <p>{en?'Read purchased fuel, SCI and ending inventory together. Bunkering actions are not port calls. Day-based reserves, minimum-fuel reporting and inventory valuation remain future analysis; no new savings or safety result is claimed.':'구매량·SCI·최종잔량을 함께 비교해야 하며 급유 행동 횟수는 실제 기항 횟수가 아닙니다. 일수 기반 안전기준, 최소잔량 추가 집계, 재고가치 평가는 후속 검토 항목으로 새 비용절감·안전성 결과를 뜻하지 않습니다.'}</p>
   <p>{en?'Review by team member Shin Min-jae. This is qualitative maritime feedback, not an official operating standard or field validation. Unsupported numerical examples were not adopted.':'신민재의 팀 내 해양 분야 검토를 반영했습니다. 공식 운항 기준이나 현장 성능 검증이 아닌 정성적 의견이며, 출처 없는 수치 예시는 적용하지 않았습니다.'}</p>
   <a href="https://github.com/heechan9/bunkering-ai/blob/main/docs/technical/minjae_domain_review_20260920.md" target="_blank" rel="noreferrer">{en?'Review and adoption scope ↗':'검토 내용과 채택 범위 ↗'}</a>
  </details>
  <details><summary>{en?'People, AI and verification':'사람과 AI가 맡은 역할'}</summary>
   <p>{en?'Choi Hee-chan leads problem definition, requirements and team coordination. Codex assists implementation, editing and recorded checks. Contributions and the limits of attribution are documented separately; AI assistance is not domain-expert approval.':'최희찬은 문제 정의·요구사항·팀 조율을 맡고, Codex는 구현·문서 편집·기록 검산을 지원합니다. 기여 내역과 확인 한계는 별도 기록하며, AI의 지원을 현장 전문가의 승인으로 표현하지 않습니다.'}</p>
   <a href="https://github.com/heechan9/bunkering-ai/blob/main/CONTRIBUTIONS.md" target="_blank" rel="noreferrer">{en?'View contribution records ↗':'기여 기록 확인 ↗'}</a>
  </details>
 </section>
}
