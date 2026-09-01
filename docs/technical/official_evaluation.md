# 공식 동일조건 평가 절차와 결과

Rule-based 3종과 Double DQN을 **같은 seed·episode·환경설정**에서 실행한 공식 비교의
실행 방법, 산출물, 그리고 실제로 관측된 수치를 기록한다.
평가 규격은 [`evaluation_contract.md`](evaluation_contract.md)를 따르고,
산출물 검증은 [`paper_evidence_audit.md`](paper_evidence_audit.md)의 `CLAIM-007`이 담당한다.

## 1. 실행 절차

```bash
# 1) 정책 학습 후 체크포인트 저장
python scripts/train.py --episodes 1000 --seed 42 --checkpoint checkpoints/dqn_final.pt

# 2) 저장된 체크포인트를 불러와 rule-based 3종과 동일조건 비교
python scripts/evaluate.py --episodes 100 --seed 42 --checkpoint checkpoints/dqn_final.pt

# 3) 산출물 감사
PYTHONPATH=. python scripts/audit_paper_evidence.py
```

`scripts/evaluate.py`는 학습을 수행하지 않는다. 체크포인트를 로드해 greedy(=argmax)
행동만 사용하며, epsilon 탐색을 쓰지 않는다. `DQNAgent.greedy_action()`은 난수를
소비하지 않으므로 평가 결과는 전역 RNG 상태와 무관하게 재현된다.

## 2. 공정성 보장 방식

1. 실행 전에 정책 4종 × episode 수만큼 `EvaluationCase`를 만들고
   `validate_fair_evaluation_plan()`으로 검증한다. 한 정책이라도
   `(episode, seed, env_config)` 집합이 다르면 **에피소드를 시작하기 전에** 중단된다.
2. 에피소드는 검증된 계획을 그대로 순회하며 실행한다. 계획과 실행이 갈라질 수 없다.
3. `env_config`는 `configs/dqn.yaml`의 `env` 절 하나만 읽어 모든 정책에 동일하게 넘긴다.
4. 체크포인트의 `state_dim`·`action_dim`이 평가 환경과 다르면 로드 시점에 거부한다.
5. 실행 조건은 `results/evaluation_manifest.json`에 정책별 case 단위로 기록하고,
   감사 도구가 CSV와 manifest의 `(seed, episode, policy)` 집합 일치를 검사한다.

## 3. 산출물

| 경로 | 내용 |
| --- | --- |
| `results/evaluation_results.csv` | 정책별 에피소드 원본 기록(정본, `CSV_FIELDS` 순서) |
| `results/evaluation_manifest.json` | 정책·seed·episode·`env_config`·체크포인트 sha256 |
| `results/evaluation/raw_<policy>.csv` | 정책별 원본 CSV |
| `results/evaluation/summary.csv` | 정책별 mean/std(모집단, ddof=0)와 종료원인 집계 |
| `results/evaluation/termination_reasons.csv` | 종료원인 분할표 |
| `results/evaluation/comparison.png` | 지표별 비교 그래프(오차막대 = 표준편차) |

체크포인트(`checkpoints/*.pt`)는 `.gitignore` 대상이다. manifest에 sha256과 학습
seed·episode 수를 남기므로, 같은 명령으로 재학습하면 동일 가중치를 복원할 수 있다.

## 4. 관측 결과 (2026-09-01, episodes=100, base_seed=42)

`train.py --episodes 1000 --seed 42`로 학습한 체크포인트를 seed 42~141의 100개
에피소드에서 평가한 값이다. 표준편차는 모집단 기준(ddof=0)이다.

| policy | reward (mean ± std) | Synthetic Cost Index (mean ± std) | 성공률 | 연료고갈률 | 급유횟수 (mean ± std) |
| --- | --- | --- | --- | --- | --- |
| fixed_fueling | -2.0300 ± 0.0000 | 0.0 ± 0.0 | 0.00 | 1.00 | 0.00 ± 0.00 |
| price_reactive | -1.9519 ± 0.2848 | 17,369.5 ± 103,346.1 | 0.03 | 0.97 | 0.08 ± 0.50 |
| safe_stock | -0.4928 ± 0.0108 | 545,392.7 ± 63,453.9 | 1.00 | 0.00 | 1.00 ± 0.00 |
| double_dqn | -1.2857 ± 0.8423 | 354,186.1 ± 366,072.3 | 0.52 | 0.48 | 1.83 ± 3.30 |

종료원인 (100 에피소드 기준):

| policy | arrived | fuel_depleted | timeout |
| --- | --- | --- | --- |
| fixed_fueling | 0 | 100 | 0 |
| price_reactive | 3 | 97 | 0 |
| safe_stock | 100 | 0 | 0 |
| double_dqn | 52 | 48 | 0 |

관측 사실만 기록하면 다음과 같다.

- `safe_stock`이 평균 reward와 성공률에서 가장 높은 값을, 연료고갈률에서 가장 낮은
  값을 기록했다. 이번 실행에서 `double_dqn`은 그보다 낮은 평균 reward(-1.2857)와
  성공률(0.52)을 보였다.
- `double_dqn`의 Synthetic Cost Index 평균은 `safe_stock`보다 낮지만, 이는 비용
  효율이 아니라 48%의 에피소드가 연료고갈로 조기 종료되어 급유 자체가 적게
  집계된 결과로 해석해야 한다. 성공한 에피소드만 놓고 비교한 값이 아니다.
- `fixed_fueling`의 Cost Index 0은 출항 시 탱크가 이미 가득 차 실제 주유량이
  0이기 때문이며, 100 에피소드 전부 연료고갈로 종료됐다.
- `double_dqn`의 표준편차가 모든 지표에서 가장 크다. 정책이 seed에 따라 크게
  다르게 행동한다는 뜻이다.

## 5. 해석 경계와 한계

- **탐색 스케줄 미소진**: `configs/dqn.yaml`의 `epsilon_decay_steps`는 100,000인데
  `n_episodes: 1000`은 약 24,000 step만 생성한다. 이번 학습은 epsilon 1.0에서
  0.7150까지만 감쇠한 상태로 종료됐다. 즉 학습 전 구간이 사실상 무작위 탐색이었고,
  위 수치는 **수렴한 정책이 아니라 이 설정으로 학습한 정책의 상태**를 나타낸다.
  하이퍼파라미터 조정은 별도 합의 후 진행한다.
- **합성 환경**: 가격·환율은 합성 random walk이며 실제 유가·환율 연동은 미구현이다.
- **항만 미차등**: 현재 `action=1..n_ports`는 가격·대기시간·수수료가 동일하다.
  따라서 이번 비교는 항만 선택 능력을 측정하지 않는다.
- **Synthetic Cost Index**: 정규화 탱크 기준의 합성 지표이며 실제 USD/KRW 비용이 아니다.
- **표본**: 정책당 100 에피소드, seed 42~141. 신뢰구간이나 유의성 검정은 아직 수행하지 않았다.

## 6. 미결 항목 (합의 후 반영)

- **README 문구와 감사 규칙의 결합**: `evaluation/paper_audit.py`의 `CLAIM-006`은
  README.md에 "공식 동일조건 성능비교는 아직 수행하지 않았습니다" 문장이 있을 때만
  `passed`를 준다. 4절 결과가 저장소에 들어온 지금 그 문장은 현재 상태와 맞지 않지만,
  문장을 지우면 `CLAIM-006`이 `failed`가 되어 감사 exit code가 1이 된다. README 갱신과
  `CLAIM-006` 판정 로직 수정은 감사 도구 담당자와 함께 한 번에 반영한다.
- **탐색 스케줄 정합성**: 5절 첫 항목의 `epsilon_decay_steps` 대 `n_episodes` 불일치는
  하이퍼파라미터 변경에 해당하므로 별도 합의 후 조정한다.
