# State / Action / Reward 정의 명세서

**SDS STEP 2 — RL 환경 설계** | 작성: 최희찬 (PM/RL Technical Lead) | 상태: 초안 (구현 착수 전)

> 본 문서는 사업화 전략 문서 03장(AI 시스템 워크플로우) 및 개발 프로세스 문서 STEP 02에서
> 정의한 State/Action/Reward 개념을 `BunkeringEnv` 코드로 옮기기 위한 구체화 명세서입니다.
> 실측 데이터 확보 전이므로 값의 범위·정규화 방식은 데이터 조사(신민재) 결과에 따라 조정될 수 있습니다.

## 1. State Space

| 변수 | 설명 | 타입 | 출처(예정) | 비고 |
|---|---|---|---|---|
| `fuel_price` | 현재 항만 벙커유 가격 | float | 공개 벙커유 가격 소스 | 정규화 필요 |
| `fuel_price_ma30` | 최근 30일 평균 대비 가격 | float | 파생 변수 | 사업화 문서 04장 XAI 예시와 연계 |
| `oil_index` | 국제 유가(WTI/Brent) | float | IEA/EIA | |
| `fx_rate` | 환율 | float | 한국은행 등 | |
| `ship_lat`, `ship_lon` | 선박 위치 | float | AIS | 공개 API 우선, 실무데이터는 협의 중 |
| `fuel_remaining` | 연료 잔량 (탱크 대비 %) | float | 시뮬레이션 상태값 | |
| `route_remaining` | 잔여 항로 거리 | float | AIS 기반 계산 | |
| `sfc` | 연료 소비율 (Specific Fuel Consumption) | float | 신민재 현장 상수값 | |
| `port_wait_time` | 예상 항만 대기시간 | float | 항만 API | 선택적 |
| `weather_risk` | 기상 리스크 지수 | float | 기상청 API | 선택적, 초기 버전 제외 가능 |

**초기 MVP 범위(7월 목표)**: `fuel_price`, `fuel_price_ma30`, `fx_rate`, `fuel_remaining`, `route_remaining`, `sfc` 6개 변수로 우선 구현하고, AIS·기상 연동 확보 시 확장.

## 2. Action Space

사업화 문서 03장 기준, DQN·PPO 비교를 위해 두 알고리즘의 이산/연속 구조 차이를 아래와 같이 정의한다.

| Action | 정의 | DQN 처리 | PPO 처리 |
|---|---|---|---|
| 급유 여부 | Yes / No | 이산 (2) | 이산 (2) |
| 항만 선택 | 후보 항만 N개 중 선택 | 이산 (N) | 이산 (N) |
| 급유량 | 탱크 용량 대비 비율 | 이산 구간 (0/25/50/75/100%) | 연속값 [0, 1] |

> Action Space 정의 차이는 문서 규칙(운영가이드 02장 "DQN/PPO 비교 기준")에 따라 A·B 문서 동시 반영 대상.

## 3. Reward Function

사업화 문서 02장/03장 기준 4개 항으로 구성 (초기 계수는 자리표시자, 튜닝 대상):

```
R = w1 * fuel_cost_saving
  - w2 * risk_penalty
  + w3 * operational_efficiency
  + w4 * imo_compliance_bonus
```

| 항 | 의미 | 초기 방향 |
|---|---|---|
| `fuel_cost_saving` | Rule-based 대비 절감액 | 연료비 절감 시 + |
| `risk_penalty` | 안전 연료 마진 미달, 과도한 대기 등 | 위반 시 - |
| `operational_efficiency` | 불필요한 입항·대기 감소 | 효율적일수록 + |
| `imo_compliance_bonus` | CII/EEXI 규제 대응 | 규제 준수 시 + |

**계수(w1~w4)는 7월 구현 시 우선 상수(예: 1.0, 0.5, 0.3, 0.2)로 시작 → STEP 03(8~9월) 하이퍼파라미터 튜닝 및 Reward Shaping 단계에서 조정.**

## 4. Rule-based 베이스라인 (백테스트 비교 기준, 운영가이드 확정본)
1. **고정 급유 전략**: 출항 전 항상 최대 연료 탑재
2. **가격 반응 전략**: 유가 5% 이상 하락 시 급유, 상승 시 대기

## 5. 미확정 사항 (데이터 조사 완료 후 확정 필요)
- [ ] 각 State 변수의 정규화 방식 (min-max vs z-score)
- [ ] 항만 후보 리스트(N) 확정 — 초기 항로(싱가포르–부산 등) 기준
- [ ] Reward 계수(w1~w4) 초기값 근거
- [ ] `weather_risk`, `port_wait_time` MVP 포함 여부
