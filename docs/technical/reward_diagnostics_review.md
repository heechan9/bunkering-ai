# 보상·구매량·잔량 보충 진단 및 독립 검토

## 범위

기준 코드: `97233c1c442a687aaed4a34e2cadca0d98aa2fb9`.
기존 환경, 정책, 보상, 공식 CSV와 체크포인트는 수정하지 않는다.
이 도구는 진단용이며 정책 개선 또는 비용절감 입증이 아니다.

## 구현

`python -m scripts.diagnose_reward`는 step별 의사결정 가격·환율,
실급유량, 보상 4성분, 안전잔량 위반, 최종 잔량을 기록한다.
연료수지는 초기잔량 + 구매량 - 실현소비 - clipping 손실 = 최종잔량이다.
내부 raw fuel을 읽는 이유는 float32 관측값 반올림을 수지오차로 오인하지 않기
위함이다. 환경 내부 상태를 변경하지 않는다.
구매 SCI에 최종 재고가치를 임의로 차감하지 않는다.
가격 보상은 구매량 가중치가 없는 가격우위 proxy이고, SCI는 구매량×가격×환율이다.
따라서 높은 보상은 비용절감의 증거가 아니다.

## 실행 확인: 규칙 정책만

100 cases, seeds 42~141, 기본 30-step 환경. 각 값은 episode 평균이다.

| 정책 | 구매량(정규화) | 최종 잔량 | reward | SCI | 안전선 미달 step |
|---|---:|---:|---:|---:|---:|
| Fixed Fueling | 0 | 0 | -2.030000 | 0 | 4.00 |
| Price Reactive | 0.0285 | 0.0135 | -1.951856 | 17,369.517619 | 3.91 |
| Safe Stock | 0.85 | 0.35 | -0.492798 | 545,392.723905 | 1.00 |

실패 항차와 성공 항차의 비용·잔량 평균은 동등한 운송 서비스를 뜻하지 않는다.
Safe Stock의 도착 성공과 안전선 미달은 양립한다. 도착률과 안전위반을 분리한다.
Fixed Fueling의 출발 행동은 초기 탱크 제약으로 실구매가 0이다.
소비량 -10%에서는 초기 1.0에서 첫 step 후 상한 0.95를 적용하며 0.005의
clipping 손실이 발생한다. 기존 환경을 고치지 않고 별도로 기록한다.

## 테스트·실행 상태

새 진단 테스트 7개 통과: 연료수지, SCI, 보상 분해, 반복성, clipping,
출력 덮어쓰기 거부, CLI 및 임의 초기화 DQN 가중치 불변 확인.
최초 실행 당시 전체 회귀는 미실행이었으며, 최신 전체 회귀 결과는 아래 절을 참조한다.
4개 학습 체크포인트 평가도 아직 실행하지 않았다. 아래 평가가 필요하다.

```bat
python -m scripts.diagnose_reward --episodes 100 --base-seed 42 --checkpoint checkpoints\dqn_seed_42.pt --output-dir results\diagnostics\reward_seed_42
```

출력 폴더는 새 경로여야 한다. 다른 학습 seed는 체크포인트와 폴더명만 바꾼다.
`steps.csv`, `episodes.csv`, `manifest.json`을 함께 보존한다.
반복된 Rule-based 실행은 독립 학습 표본으로 세지 않는다.

## Claude 독립 검토 요청

이 문서와 `envs/bunkering_env.py`, `scripts/baseline.py`,
`scripts/diagnose_reward.py`, `scripts/evaluate.py`,
`evaluation/contract.py`, `tests/test_reward_diagnostics.py`를 실제로 읽고 검토한다.
파일 접근이 안 되면 추측해서 통과 처리하지 말고 파일 첨부를 요청한다.

1. 보상 분해와 SCI·연료수지가 실제 코드와 일치하는가?
2. 구매량에 비례하지 않는 가격 보상이 잦은 소량 급유의 유인이 되는가?
   설계상 가능성과 실제 학습 정책의 행동 증거를 구분할 것.
3. Safe Stock의 도착률을 안전선 위반 없음으로 잘못 해석했는가?
4. 최종 잔량 차이 때문에 총 구매 SCI를 단순 비교하기 어려운가?
5. Fixed Fueling이 유효한 경쟁 기준선인지, 단순 음성 대조 정책인지?
6. 다음 step 소비를 고려하는 예방형 재고 규칙을 별도 기준선으로 추가할 가치가 있는가?
   스트레스의 미관측 소비량을 그 규칙에만 알려주는 정보 비대칭을 피할 것.
7. 소비 -10%의 clipping 효과가 결과 해석에 영향을 주는가?

각 답변에 파일·함수 근거와 Critical/High/Medium/Low 우선순위를 제시한다.
불리한 결과도 유지하며, 공식 결과 변경이나 보상 재설계는 이 진단 범위 밖이다.
진단 도구 병합 전 전체 회귀 테스트와 독립 검토를 권장한다.


## Claude 검토 대응: 2026-09-11

보충 진단 테스트는 보강 후 **23 passed**. 전체 저장소 회귀 테스트를 뜻하지 않는다.
4개 정책(규칙 3종 + 임의 초기화 frozen DQN) × 소비량 4조건 × seeds 42~141의
1,600개 조건에서 진단 runner와 공식 `scripts.evaluate.run_episode`를 각각
실행해 reward·SCI·종료사유·실급유횟수를 대조했다. 학습된 4개 DQN의 행동
검증이 아니며 경제적 우위를 주장하지 않는다.

- C-1: 실패 정책의 SCI가 낮다는 것은 효율성 증거가 아니다. 기존 주의 문구를
  유지한다. 이 문서는 코드 실행 장애가 아니라 해석 위험으로 분류한다.
- C-2: 기본 소비량 0.05, +10%, +20%의 clipping 손실은 1e-12 허용오차에서
  0이었다. -10%에서만 초기 손실 0.005가 발생했다. 첫 전이에서
  `max(0, 1-consumption-0.95)`이며 이후 잔량은 이미 상한 이하다.
  공식 SCI는 환경에서 실제 구매량으로 누적하므로 진단 누락을 근거로 기존
  공식 SCI 전체가 무효라는 결론은 성립하지 않는다. -10% 조건은 초기 상한
  처리 효과가 섞인다는 해석상 한계를 명시한다.
- C-3: 소량 다회 구매 유인은 설계상 가설이다. 실제 학습 체크포인트 4개의
  행동 진단은 미완료로 유지한다. 이 가설은 확정 결함이나 관찰 결과가 아니다.
- H-1: 모든 정책·소비조건에서 step별 보상 4성분 합과 SCI를 재구성했다.
- H-2: Safe Stock 도착 성공과 안전선 미달 1 step을 구분한다.
  논문 수정 시 “안전위반 없음”으로 표현하지 않는다.
- M-1: 환경은 양수 `risk_penalty`에 음의 가중치를 적용한다.
  진단의 `safety_reward` 부호가 일치함을 재구성 검사로 확인했다.
- M-2: 자기 일관성 검사 외에 기존 공식 runner 반환값과의 직접 대조를 추가했다.
- 신규-1: 기존 출력 디렉터리에 sentinel CSV를 두고 CLI가 거부한 뒤
  파일 바이트가 그대로인지 확인했다. 모든 존재 디렉터리 재사용을 거부하는
  일반 보호이며, 모든 공식 경로를 판별하는 전용 sandbox는 아니다.

### 미확인 파일의 고정 버전 링크

아래는 진단 기준 커밋의 파일이다. diff에 없더라도 원문을 읽고 검토해야 한다.

- [환경](https://github.com/heechan9/bunkering-ai/blob/97233c1c442a687aaed4a34e2cadca0d98aa2fb9/envs/bunkering_env.py)
- [규칙 정책](https://github.com/heechan9/bunkering-ai/blob/97233c1c442a687aaed4a34e2cadca0d98aa2fb9/scripts/baseline.py)
- [공식 runner](https://github.com/heechan9/bunkering-ai/blob/97233c1c442a687aaed4a34e2cadca0d98aa2fb9/scripts/evaluate.py)
- [평가계약](https://github.com/heechan9/bunkering-ai/blob/97233c1c442a687aaed4a34e2cadca0d98aa2fb9/evaluation/contract.py)

기존 7-test 기록은 최초 실행 시점의 기록이다. 최신 보충 테스트는 23개이며,
전체 회귀는 아래 후속 실행에서 완료했다. 학습 체크포인트 4개 진단은 남아 있다.

## 전체 회귀 완료 및 PC 진단 절차 (2026-09-11)

- 검증 대상 PR HEAD: `498c8b9edc085b61c6ca96582054e70b6eea3de6`.
- main `97233c1`의 격리된 Git worktree에 해당 HEAD의 신규 파일 4개를
  GitHub에서 읽어 적용했다. 기존 tracked 파일의 diff는 없다.
- 실행: `python -m pytest -q`.
- 결과: **209 passed in 10.28s**, 프로세스 종료코드 0.
- 구성: 기존 186개 + 진단 23개.
- 환경: Python 3.12.14, PyTorch 2.14.0+cu130, NumPy 2.5.3,
  Gymnasium 1.3.0. Windows/Conda에서의 별도 실행 결과는 아니다.
- 이 후속 변경은 문서뿐이다.
- 작업공간에는 실제 학습 seed 42/1042/2042/3042 체크포인트가 없어
  해당 4개 행동 진단은 실행하지 않았다. 시험용 checkpoint를 대체 사용하지 않는다.
- PR은 실제 진단과 독립 검토 대기를 위해 Draft로 유지한다.
  체크포인트 미평가는 도구 자체의 정확성 결함과 구분한다.

### Windows Anaconda Prompt에서 실행

현재 작업이 있으면 저장한 뒤 브랜치를 전환한다. `git status`에서
예상 밖 변경이 보이면 강제 전환/삭제하지 않는다.

```bat
conda activate bunkering_ai
cd C:\Users\hc247\bunkering-ai
git fetch origin feat/reward-accounting-diagnostics
git switch feat/reward-accounting-diagnostics
git pull --ff-only origin feat/reward-accounting-diagnostics
for %S in (42 1042 2042 3042) do python -m scripts.diagnose_reward --episodes 100 --base-seed 42 --checkpoint checkpoints\dqn_seed_%S.pt --output-dir results\diagnostics\reward_seed_%S
```

위 `for %S`는 대화형 CMD용이다. 배치파일에서는 `%%S`를 사용한다.
각 출력 폴더가 이미 존재하면 덮어쓰기를 거부하므로 새 폴더명을 사용한다.
재학습은 수행하지 않는다. 학습 seed 4개 모두에서 `wrote 400 episodes`가
표시되는지 확인한다(각각 규칙 3종 + DQN, 각 100회).
반복된 규칙 정책은 독립 표본으로 합산하지 않는다.

진단 후 `results/diagnostics/reward_seed_42`, `reward_seed_1042`,
`reward_seed_2042`, `reward_seed_3042`의 CSV·manifest를 함께 전달한다.
이 파일들로 실제 DQN의 보상 성분, 구매량, 안전선 위반, 최종 잔량을 분석한다.
소량 다회 급유가 관찰돼도 별도 인과 실험 없이 보상 설계의 인과효과로 단정하지 않는다.
