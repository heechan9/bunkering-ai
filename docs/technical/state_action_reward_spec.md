# State / Action / Reward 정의 명세서

**SDS STEP 2 — RL 환경 설계** | 작성: 최희찬 (PM/RL Technical Lead) | 상태: M1 구현 진행 중

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

**현재 임시 구현 계약**: `action=0`은 급유하지 않음, `action=1..n_ports`는
선택 항만에서 고정 요청량(`0.9`)을 급유함을 의미한다. 실제 급유량은 연료 소비 후
남은 탱크 여유와 요청량 중 작은 값이며, 이 Action Contract 자체의 재설계는 별도
팀 합의 후 진행한다.

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
| `fuel_cost_saving` | 의사결정 시점 현재가가 MA30 대비 유리한 정도를 나타내는 가격 우위 대리값(price advantage proxy) | 실제 급유량이 있고 현재가가 MA30보다 낮을 때 + |
| `risk_penalty` | 안전 연료 마진 미달, 과도한 대기 등 | 위반 시 - |
| `operational_efficiency` | 불필요한 입항·대기 감소 | 효율적일수록 + |
| `imo_compliance_bonus` | CII/EEXI 규제 대응 | 규제 준수 시 + |

**계수(w1~w4)는 7월 구현 시 우선 상수(예: 1.0, 0.5, 0.3, 0.2)로 시작 → STEP 03(8~9월) 하이퍼파라미터 튜닝 및 Reward Shaping 단계에서 조정.**

### 3.1 Decision-time 계산 계약

- `decision_fuel_price`, `decision_price_ma30`, `decision_fx_rate`는 액션을
  실행하고 가격·환율 랜덤워크를 갱신하기 **직전** 값으로 고정한다.
- `fuel_cost_saving` 키는 기존 호환성을 위해 유지하지만 실제 비용 절감액이 아니다.
  실제 급유량이 `1e-6`보다 클 때만 다음 가격 우위 대리값을 계산한다.

```
fuel_cost_saving =
    max(0, (decision_price_ma30 - decision_fuel_price) / decision_price_ma30)
```

- Rule-based 전략 대비 실제 절감액과 절감률은 episode-level 평가가 필요한 별도
  KPI이며, 평가 파이프라인 단계에서 계산한다.

### 3.2 Synthetic Cost Index

실제 선박 탱크 용량이 확정되지 않았으므로 M1에서는 정규화 탱크 기준의 비교 지수만
누적한다.

```
step_cost_index =
    actual_bunker_amount * decision_fuel_price * decision_fx_rate

cumulative_cost_index =
    sum(step_cost_index)
```

- `actual_bunker_amount`는 연료 소비 후 남은 탱크 여유와 고정 요청량 중 작은 값이다.
- `step_cost_index`, `cumulative_cost_index`는 실제 USD 또는 KRW 비용이 아니라
  **Synthetic Cost Index**다. 탱크 용량 확정 전 실제 화폐 단위로 해석하지 않는다.
- CSV·리포트로 확장할 때도 `_index` 접미사와 위 단위 주석을 유지한다.
- 이 지수는 현재 Reward에 직접 더하지 않는다.

## 4. Rule-based 베이스라인 (백테스트 비교 기준, 운영가이드 확정본)

1. **고정 급유 전략**: 출항 전 항상 최대 연료 탑재
2. **가격 반응 전략**: 유가 5% 이상 하락 시 급유, 상승 시 대기
3. **Safe Stock 전략 (PR #5A)**: 아래 4.1 참고

### 4.1 Safe Stock Baseline (PR #5A, provisional)

> **provisional**: 이 절은 샌드박스(numpy 재구현) 상의 사전 시뮬레이션 결과를 근거로
> 작성되었으며, 실제 Gymnasium 환경에서의 로컬 재현 전까지는 provisional 상태다.
> 아래 수치는 일반화된 성능 주장이 아니라 seed 42~61, 현재 Synthetic Environment
> 설정 한정 결과로만 해석한다.

- 관측 가능한 현재 `fuel_remaining`만 사용하고, 미래 가격이나 향후 상태는 보지 않는다.
- 임계값은 새로 정의하지 않고 기존 `env.min_safe_fuel`(기본값 0.15)을 그대로 재사용한다.
- 결정 규칙: `fuel_remaining <= env.min_safe_fuel`이면 급유, 아니면 급유하지 않는다.
- observation dtype(float32)에 맞춰 임계값을 비교해 float32 경계 오판을 방지한다 —
  `env.min_safe_fuel`(float64)을 observation과 같은 dtype으로 변환한 뒤 비교하며,
  새로운 epsilon 상수는 추가하지 않는다.
- 현재 환경은 `action=1..n_ports`를 정의하지만 항만별 가격·비용·전이 차이가 아직
  구현되지 않았으므로, Safe Stock은 대표 급유 `action=1`을 사용한다 —
  급유량이나 항만을 선택하는 전략이 아니다.
- 항만 선택 성능을 검증하는 baseline이 아니다. Action encoding에는 항만 번호가
  존재하지만, 현재 Transition에서는 항만별 동작 차이가 구현되지 않았다(2절 참고).
  이 전략은 "언제 급유할지"만 다룬다.
- **Safe Stock은 현재 "Reference Baseline 후보"일 뿐 확정 Reference가 아니다.**
  실제 Gymnasium 환경 로컬 재현으로 20/20 도착이 확인되어야 후보에서 확정으로
  올라간다. 확정 전까지 `absolute_cost_saving_index`·`cost_saving_rate` 계산과
  절감액·절감률 표현은 계속 보류한다(PR #3B 합의와 동일한 원칙 적용).

**Preliminary sandbox simulation 결과** (seed 42~61, 20 episodes, numpy 재구현 기준 —
**실제 gymnasium 패키지로는 아직 재현되지 않았고, 공식 프로젝트 결과로 확정된 것이
아니다.** 아래 표는 참고용이며, 실제 로컬 재현 결과가 다르게 나오면 이 표가 아니라
로컬 재현 결과가 우선한다):

| strategy | mean_reward | std_reward | arrived | fuel_depleted | timeout | voyage_success_rate | mean n_bunkering | mean cumulative_cost_index |
|---|---|---|---|---|---|---|---|---|
| fixed_fueling | -2.0300 | 0.0000 | 0 | 20 | 0 | 0.00 | 0 | 0.00 |
| price_reactive | -1.8395 | 0.5125 | 2 | 18 | 0 | 0.10 | 0.25 (0~4회) | 67932.19 |
| safe_stock | -0.4921 | 0.0134 | 20 | 0 | 0 | 1.00 | 1 (전 episode 동일) | 546626.71 |

평가 단계에서는 같은 seed·운항 조건에서 다음 episode-level KPI를 계산한다.

```
absolute_cost_saving =
    baseline cumulative cost - policy cumulative cost

cost_saving_rate =
    absolute_cost_saving / baseline cumulative cost
```

## 5. 미확정 사항 (데이터 조사 완료 후 확정 필요)
- [ ] 각 State 변수의 정규화 방식 (min-max vs z-score)
- [ ] 항만 후보 리스트(N) 확정 — 초기 항로(싱가포르–부산 등) 기준
- [ ] Reward 계수(w1~w4) 초기값 근거
- [ ] `weather_risk`, `port_wait_time` MVP 포함 여부
