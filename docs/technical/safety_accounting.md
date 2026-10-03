# 급유 전 안전·잔여 연료 비용 보충 평가

2026-10-03 · 공식 동결 체크포인트, 기본조건 30단계, 평가 seed 42–141, 정책별 100회.

| 정책 | 기존 도착 | 급유 전 부족 없는 도착 | 항차 전체 안전여유 충족 도착 |
|---|---:|---:|---:|
| Double DQN | 100/100 | 100/100 | 100/100 |
| Safe Stock | 100/100 | 100/100 | 0/100 |
| Price Reactive | 3/100 | 3/100 | 2/100 |
| Fixed Fueling | 0/100 | 0/100 | 0/100 |

공식 모델은 유지한다. Safe Stock의 도착 성공은 보존되지만 급유 직전까지 15%를 유지하는 기준은 충족하지 않는다. 이 결과는 합성 기본조건에 한정되며 실선 안전 인증이 아니다. 웹의 기존 4개 학습 seed 평균과 이번 단일 공식 체크포인트 결과를 혼합하지 않는다.

## 정의와 해석

- 매 단계 소비 후, 급유 전 잔량을 **0으로 자르기 전** 계산한다.
- 급유 전 부족: `fuel - consumption < -1e-9`. 정확히 0은 부족으로 분류하지 않으나 15% 안전여유는 미충족이다.
- 항차 전체 안전여유: 모든 급유 전 잔량이 `min_safe_fuel - 1e-9` 이상이며 도착한 경우. 도착 성공·소진 방지와 별개다.
- 보정 SCI = 구매 SCI + 초기 연료×초기 가격×초기 환율 − 최종 연료×종료 시점 가격×환율. 정규화 탱크의 합성 지표이며 원화·달러가 아니다. 종료 시점 시장가치는 사후 평가용이며 정책 입력이 아니다.
- 실패/안전 미충족 항차의 보정 SCI는 회계 진단용으로만 남긴다. `safe_arrival_adjusted_sci`는 공란이다. 정책 간 절감 비교는 동일 seed에서 **양쪽 모두 안전 도착한 경우**에만 한다. DQN–Safe Stock은 이 기준의 공통 사례가 0개이므로 안전 조건부 비용 우열을 주장하지 않는다.
- 이는 원래 경로를 그대로 감사한 결과다. 부족 발생 즉시 중단하는 새 환경에서의 성능 실험이 아니다. 원래 도착률·보상·체크포인트·종료 계약은 바꾸지 않았다.

## 재현

```bash
python scripts/evaluate.py --episodes 100 --seed 42 --checkpoint /path/to/dqn_final.pt --output-dir /tmp/safety-review
```

기존 출력에 `evaluation/safety_accounting.csv`가 추가된다. 실행 manifest에 정의와 허용오차를 기록한다.

- [400개 항차 진단 CSV](../../results/diagnostics/safety_accounting/episodes.csv)
- [체크포인트 해시·환경·seed manifest](../../results/diagnostics/safety_accounting/manifest.json)
- [외부자료 채택·보류 판단](../../research/external_validation/DECISIONS.md)

검증: 안전·평가 회귀 테스트 26개 통과. 기존 웹 70개 요약값·19,030개 전이 대조 통과. 모델 재학습 없음.
