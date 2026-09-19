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
   <p>{en?'Reserve rules, supply constraints and linked departure–purchase–consumption–arrival records require review. Field reviews and voyage data are pending, not completed validation.':'안전잔량 기준, 공급·작업 제약, 같은 항차의 출발잔량·급유·소비·도착잔량 연결을 확인해야 합니다. 현장 검토와 실측 자료 반영은 대기 중이며 검증 완료로 표시하지 않습니다.'}</p>
  </details>
  <details><summary>{en?'People, AI and verification':'사람과 AI가 맡은 역할'}</summary>
   <p>{en?'Choi Hee-chan leads problem definition, requirements and team coordination. Codex assists implementation, editing and recorded checks. Contributions and the limits of attribution are documented separately; AI assistance is not domain-expert approval.':'최희찬은 문제 정의·요구사항·팀 조율을 맡고, Codex는 구현·문서 편집·기록 검산을 지원합니다. 기여 내역과 확인 한계는 별도 기록하며, AI의 지원을 현장 전문가의 승인으로 표현하지 않습니다.'}</p>
   <a href="https://github.com/heechan9/bunkering-ai/blob/main/CONTRIBUTIONS.md" target="_blank" rel="noreferrer">{en?'View contribution records ↗':'기여 기록 확인 ↗'}</a>
  </details>
 </section>
}
