# 비용·수요 오차 검토 체크리스트

상태: 기존 분석을 재사용하는 **검토 절차**. 새 CSV 분석, 모델 추론, 실선 실험,
성능 향상 또는 운영 채택을 완료했다는 뜻이 아니다. 입력과 결과 파일은 변경하지 않는다.
평균·산포, 집단별 오류, 상관과 인과의 구분, 회귀 잔차라는 기초 분석 원칙을
프로젝트의 기존 계약에 맞게 정리한다. 외부 교육자료 원문은 포함하지 않는다.

## 1. 비용 분포와 조건 통제

- [공정 비교 계약](../../research/fair_replacement_eval/README.md)의 동일 seed·환경·행동공간·정보 tier와
  재고 보정 SCI를 우선한다. `decision.py`의 paired bootstrap과 `criteria.json`을
  재사용하며 새 유의성 기준이나 통과 임계값을 사후에 만들지 않는다.
- 보고서에 입력 SHA-256, source commit, 평가 단위(episode/voyage), 전체 건수,
  제외 사유별 건수와 공동 안전 표본 수를 기록한다. 다른 seed 집합이나 다른
  정보 tier를 섞은 평균으로 알고리즘 우위를 주장하지 않는다.
- 전체 안전·실패 건수를 먼저 표시하고 비용은 그 비용 지표가 정의되는 집합에서
  보고한다. 실패 항차를 조용히 빼지 않는다. 공동 안전 표본이 0이면 비교값은
  null/산출 불가이지 0% 절감이 아니다.
- 평균과 함께 중앙값, 산포, 고비용 꼬리를 검토할 때는 표본 수·단위·분위수
  정의·집계 대상을 명시한다. 기존 [꼬리 재계산 기록](../audits/pr66_tail_recalculation_20260927.json)은
  당시 저장 episode 진단이며 현재 v4 평가나 신규 추론으로 재분류하지 않는다.
  새로운 꼬리 표는 승인된 입력과 사전에 정한 정의가 있을 때만 별도 생성한다.
- 같은 항차의 여러 step을 독립 항차처럼 재표집하지 않는다. 반복 실행/항차의
  의존성을 고려한 집계 단위를 먼저 정한다. 구간이 0을 포함하면 방향성 관측과
  우월성 입증을 구분한다. 상관관계는 절감 원인이나 실선 효과를 증명하지 않는다.

## 2. 연료 수요 잔차 검토

[Voyage validation](../../research/voyage_demand/README.md)의 시간·단위·밀도·항차 경계
검증을 먼저 통과해야 한다. 실제 독립 항차·계획 시점 입력이 미확보라면 보류한다.

- 항차별 잔차는 `prediction - actual`로 고정한다. 양수는 과대예측, 음수는
  과소예측이다. `consumption_metrics`의 MAE/RMSE/bias/underprediction/shortfall을
  재사용한다. ROB 수지 잔차와 예측 잔차는 다른 검사이며 서로 대체하지 않는다.
- 잔차 대 예측값·시간순 항차를 확인하고, 사전에 정의한 조건별 n과 오차를
  같이 보고한다. 속도·기상·항로별 비교는 실제 확인된 메타데이터가 있을 때만
  가능하다. 컬럼이 없으면 “미확인”이며 추정 태그로 채우지 않는다.
- 오차가 큰 기록은 삭제하기 전에 원본 단위, 공급/소비 시점, 밀도 기준,
  누락 및 독립 타깃 여부를 확인한다. 제외했다면 이유와 제외 전후 n을 남긴다.
- 잔차 패턴 발견은 탐색 결과다. 같은 테스트 항차로 모델/분할/임계값을 수정한
  뒤 독립 검증이라고 부르지 않는다. 개선 가설은 새 기간 검증으로 넘긴다.

## 검토 기록 양식

각 분석마다 다음을 채운다. 비어 있는 항목은 완료로 취급하지 않는다.

- 입력 파일·SHA-256 / source commit / 데이터 역할(합성·관측·추정):
- 고정 비교 조건 / 분석 단위 / 전체 n / 제외 사유와 n / 비교 가능 n:
- 기존 도구·명령 / 출력 위치 / 검토한 잔차·분포 패턴:
- 확인된 사실 / 탐색 가설 / 미확인·보류 / 다음 검증에 필요한 데이터:

2026-10-21 확인 기준 v4/C01–C06은 main이 아닌 미병합 Draft
[#132](https://github.com/heechan9/bunkering-ai/pull/132) →
[#133](https://github.com/heechan9/bunkering-ai/pull/133) →
[#134](https://github.com/heechan9/bunkering-ai/pull/134) →
[#136](https://github.com/heechan9/bunkering-ai/pull/136)의 검토 범위다.
해당 v4의 회계 일치와 독립 종료 가격·환율 검증, C01–C06 채택은 별개다.
이 체크리스트는 해당 승인을 대신하지 않는다. Cp/Cpk나 6시그마 수치를 AI 성능에
붙이지 않으며, 정규분포 가정이나 R² 절대 기준을 자동으로 적용하지 않는다.

## 3. 제출 검토: 한 주장에 근거·실행·승인 연결하기

2026-10-26 추가. 위 2026-10-21 상태는 당시 기록으로 보존한다. 아래는 새 분석기가
아니라 **기존 검토 기록에 보충할 필드와 점검 순서**다. 반도체 데이터 강의의 이력
추적·단계별 진단 원칙을 해양 입력→결정→결과로 옮긴 것이며, 공정 KPI나 강의의
개선 수치를 우리 성과로 사용하지 않는다. p값·상관·오류 패턴만으로 원인을 확정하지 않는다.

### 같은 평가를 보고 있는지 먼저 확인

- 본문 표/그림에 claim ID를 붙이고 원본 보고서·입력 해시·분석 단위·분모·제외 사유를
  기존 manifest와 연결한다. 새 CSV나 두 번째 계약표를 만들 필요는 없다.
- 검토 기준 main은 `34e1e82ce10309ba737572fdae24625e4bc722a7`이다. 아래 native 링크는
  main에 없는 [#146의 고정 head](https://github.com/heechan9/bunkering-ai/tree/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621)이며,
  열린 Draft의 코드·테스트를 가리킬 뿐 병합·배포·C01–C06 채택을 뜻하지 않는다.
- native의 [짝비교 기록](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/docs/audits/native_contract_integration_20261026.md#final-fuel-cohorts-and-numerical-impact)에서
  **모든 정책 공통 strict-safe 0/1000**과 **DDQN–Price Reactive 쌍 33/1000**은 다른 집합이다.
  빈 비용 비교는 null이고, 정책별 안전 평균은 짝비교 평균이 아니다. 사후 안전 부분집합의
  차이는 전체 정책 효과가 아니다. SCI와 탱크 비율을 원화·톤·절감률로 바꾸지 않는다.
- [#141의 저장자료 짝비교](https://github.com/heechan9/bunkering-ai/blob/ab49947837fc167d8ac6cc9dab91b58232102f8a/docs/technical/matched_safety_audit.md)는
  별도 4정책×100사례다. native 1000사례, 700개 웹 replay, U01의 t/USD 예제와 합산하지 않는다.

### 어느 단계에서 확인했는지 남기기

아래는 존재하는 검사로 가는 지도다. **테스트 이름이나 파일 존재는 실행 증거가 아니다.**
실행한 항목만 아래 영수증에 SHA·명령·로그·종료 코드와 함께 기록한다.

| 단계 | 재사용할 파일 / 실제 검사 | 기록할 판단과 한계 |
|---|---|---|
| 입력·비교 계획 | [evaluation/contract.py](../../evaluation/contract.py), [test_evaluation_contract.py](../../tests/test_evaluation_contract.py)의 `test_fairness_rejects_policy_with_different_run_conditions` | seed/episode/config 일치와 누락·비유한값 여부. 계획 일치만으로 독립 항차나 동일 외생 경로를 입증하지 않음 |
| 결정·연료 전이 | [ledger.py](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/research/native_v4_integration/ledger.py), [test_ledger.py](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/research/native_v4_integration/test_ledger.py)의 `ValidationTests.test_purchase_error_reports_first_row` | 같은 seed/policy/step에서 입력→급유 전 잔량→행동·구매→다음 잔량을 연결. 첫 불일치 행은 조사 위치이지 원인 확정이 아님 |
| 안전·비용 결과 | 같은 `test_ledger.py`의 `LedgerTests.test_strict_safe_refill_does_not_recover`, `PairedFinalFuelTests.test_final_fuel_and_sci_denominators_agree`, `StatisticsTests.test_empty_is_null_not_zero` | 급유 후 회복으로 앞선 위반을 지우지 않고 실패·동일 짝 분모·null 보존 확인 |
| 가격·환율 검증 | [test_market_tape.py](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/research/native_v4_integration/test_market_tape.py)의 `ValuationAuditTests.test_balanced_terminal_shift_is_caught` | 회계 항등식 일치와 독립 시장 tape 검증을 구분. [CLI 상태 규약](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/research/native_v4_integration/README.md)에 따라 PASS/FAIL/INCOMPLETE 및 legacy_summary_status를 함께 읽음 |
| 사람 검토·채택 | [기존 contracts.py의 INTEGRATION / integration_map](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/research/native_v4_integration/contracts.py) | 기존 C01–C06 코드·테스트 연결을 재사용. 작성자·실행자·개인 검토자·최종 채택자를 구분하고 pending을 유지 |

단계별 이상을 찾으면 `관측 사실 / 원인 가설 / 확인한 반례·검사 / 아직 필요한 검증`을
분리한다. 사례 한 개의 추적은 설명용이며 전체 효과 추정이 아니다. 합성 fixture 검사,
저장 CSV 재계산, 모델 추론, 실제 선박 검증을 서로 대신하지 않는다. 과거 실행과 현재
수정본의 검사도 구분한다. 최신 native 실행 범위는 [누적 검증 기록](https://github.com/heechan9/bunkering-ai/blob/6436a0a0a7cfa7bae4c8c4365e09b860bb0d5621/docs/audits/native_v4_cumulative_main_20261026.md)을
기준으로 읽고, 과거 미실행 문장을 다른 실행자에게 전가하지 않는다.

### English reproduction / review receipt

기존 issue/PR 또는 검토 회신에 아래만 채운다. 빈칸은 검증 완료가 아니다. 명령은 실제
실행한 그대로, 비공개 경로·데이터는 공개하지 않는 식별자로 기록하고 원 로그는 허가된
저장소에 보존한다. 테스트 실패나 미실행을 통과로 바꾸지 않는다.

```text
Claim ID and report/table location:
Source record -> code path -> exact test ID:
Source commit SHA / tested SHA (PR head or CI merge SHA; distinguish them):
Input/config/checkpoint SHA-256 (checkpoint: not used, if no inference):
Data role / scenario / seed range / unit / all n / excluded n+reason / paired n:
Environment (OS, Python, dependency versions) / execution date / executor:
Exact command / expected result / observed result / exit code / log location+hash:
Scope: synthetic fixture | recorded-data recalculation | inference | field validation
Verified observation / cause hypothesis / not tested / remaining limitation:
Human reviewer / reviewed SHA / decision and evidence (pending until supplied):
```

- [Autoware #13433 검토](https://github.com/autowarefoundation/autoware_universe/pull/13433#pullrequestreview-5325138353)의
  재현한 조건과 재현하지 못한 조건 분리, [#13150 응답](https://github.com/autowarefoundation/autoware_universe/pull/13150#discussion_r4104244197)의
  수정 SHA·동작 설명·재검토 요청을 참고한 **협업 절차의 적용**이다. 외부 기여자의
  성과·직책이나 우리 모델의 성능을 추론하는 근거가 아니다.
- 수용 기준: 주장마다 위 연결이 있고 분모·단위·미검증 범위가 본문과 같아야 한다.
  작은 문서/검사 변경 하나만 검토하고 별도 문제는 후속 항목으로 남긴다. 이번 절차는
  모델·수치·계약 변경을 요구하지 않는다. 커밋 전 파일·검사 결과·예정 Author/Committer를
  공개하고 [기여 정책](../../CONTRIBUTIONS.md)의 승인을 받는다.
