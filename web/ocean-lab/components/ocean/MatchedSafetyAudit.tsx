'use client';
import {useLocale} from '@/lib/locale';
import report from '@/lib/matched-safety-report.json';

/** Archived evaluation only: deliberately independent of the selected replay. */
export default function MatchedSafetyAudit(){
 const {lang}=useLocale(); const en=lang==='en';
 const text=(ko:string,english:string)=>en?english:ko;
 return <section aria-labelledby="matched-safety-heading" className="review-card" style={{margin:'24px 0',padding:20,border:'1px solid #35515a',borderRadius:12}}>
  <h2 id="matched-safety-heading">{text('강의 적용 · 저장 평가의 정책별 짝비교','Lecture application · matched archived policy audit')}</h2>
  <p>{text('별도 보관 평가: 4개 정책 × 100개 사례 = 400행, DQN 훈련 seed 42 한 개. 현재 화면의 700개 리플레이·선택 체크포인트와 다른 자료입니다.','Separate archived evaluation: 4 policies × 100 cases = 400 rows, one DQN training seed (42). This is not the 700-record replay or the selected checkpoint.')}</p>
  <p>{text('신뢰구간: 보류(null) · p값: 보류(null). 독립적인 항해/훈련 반복을 확인하지 않아 유의성·개선 효과를 주장하지 않습니다.','Confidence interval: withheld (null) · p-value: withheld (null). Independent voyage/training replications are not established; no significance or performance-gain claim.')}</p>
  <details><summary>{text('6개 정책쌍의 안전 교차표와 조건부 비용 차이 보기','Show safety counts and conditional cost differences for 6 policy pairs')}</summary>
  <ul style={{paddingLeft:20}}>{report.comparisons.map(c=><li key={`${c.policy_a}-${c.policy_b}`} style={{margin:'14px 0'}}>
   <strong>{c.policy_a} (A) ↔ {c.policy_b} (B)</strong>
   <p>{text('매칭','Matched')}: {c.matched_cases} · {text('둘 다 안전','Both safe')}: {c.safety_counts.both_safe} · {text('A만 안전','Only A safe')}: {c.safety_counts.a_only_safe} · {text('B만 안전','Only B safe')}: {c.safety_counts.b_only_safe} · {text('둘 다 미충족','Neither safe')}: {c.safety_counts.neither_safe}</p>
   <p>{text('안전 도착률 차이 B−A','Safe-arrival rate difference B−A')}: {(100*c.safe_arrival_difference_b_minus_a).toFixed(1)}%p · {text('조건부 비용차 B−A','Conditional cost difference B−A')}: {c.cost_difference_b_minus_a===null?text('비교 불가: 둘 다 안전한 사례 0개','Unavailable: zero jointly safe cases'):Number(c.cost_difference_b_minus_a.mean).toLocaleString(en?'en-US':'ko-KR',{maximumFractionDigits:2})+' SCI'}</p>
  </li>)}</ul>
  <p>{text('비용 차이는 두 정책 모두 안전한 사례에만 한정합니다. 정책 결과로 표본이 선택되므로 전체 정책 비용효과가 아니며, 비교쌍마다 대상 사례가 다를 수 있습니다. SCI는 합성 지수이며 실제 통화·절감액이 아닙니다.','Cost differences are conditional on both policies being safe. Post-policy selection prevents interpreting this as an overall policy cost effect; pairwise subsets may differ. SCI is synthetic, not currency or monetary savings.')}</p>
  <p>{text('동일 seed·설정은 평가 계획의 일치만 확인합니다. 동일한 외생 경로·실제 항해 독립성은 증명하지 않습니다. 기존 안전회계는 관찰 감사이며 시뮬레이터 종료·모델·기존 리플레이를 바꾸지 않았습니다.','Identical seeds/configuration verify the evaluation plan only, not identical exogenous trajectories or independent real voyages. This observational safety audit does not change simulator termination, models, or existing replay data.')}</p>
  <p>{text('원자료','Source')}: results/diagnostics/safety_accounting/episodes.csv · <a href="https://github.com/heechan9/bunkering-ai/blob/fcf3c38d5606285626734d1f8cc8bfc14408b300/results/diagnostics/safety_accounting/manifest.json" target="_blank" rel="noreferrer">{text('고정 평가 명세','Pinned evaluation manifest')}</a></p>
  <a href="/data/matched-safety-report.json" download>{text('짝별 상세 보고서 내려받기','Download pair-level audit report')}</a>
  </details>
 </section>
}
