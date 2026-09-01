# 공식 동일조건 평가 절차와 결과

Rule-based 3종과 Double DQN을 **같은 seed·episode·환경설정**에서 실행한 공식 비교의
실행 방법, 산출물, 그리고 실제로 관측된 수치를 기록한다.
평가 규격은 [`evaluation_contract.md`](evaluation_contract.md)를 따르고,
산출물 검증은 [`paper_evidence_audit.md`](paper_evidence_audit.md)의 `CLAIM-007`이 담당한다.

## 1. 실행 절차

```bash
# 1) 정책 학습 후 체크포인트 저장 (에피소드 수는 configs/dqn.yaml의 n_episodes)
python scripts/train.py --seed 42 --checkpoint checkpoints/dqn_final.pt

# 2) 저장된 체크포인트를 불러와 rule-based 3종과 동일조건 비교
python scripts/evaluate.py --episodes 100 --seed 42 --checkpoint checkpoints/dqn_final.pt

# 3) 산출물 감사
PYTHONPATH=. python scripts/audit_paper_evidence.py
```

4절의 수치를 그대로 재현하려면 1)을 재학습으로 대신하지 말고 3.1절의 공식 체크포인트를
내려받아 2)부터 실행한다. 재학습은 동일 조건을 재현할 뿐 동일 가중치를 보장하지 않는다
(3.2절).

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

### 3.1 공식 체크포인트의 영구 보존과 다운로드

체크포인트(`checkpoints/*.pt`)는 `.gitignore` 대상이므로 작업 트리에만 두면 결과를
만든 가중치가 한 대의 PC에서 사라진다. 따라서 **공식 평가에 사용한 가중치는 GitHub
Release 자산으로 보존**한다. 보존 위치는 `scripts/evaluate.py`의 `CHECKPOINT_ARCHIVE`
상수 하나에 정의되고, 이후 모든 실행의 manifest `checkpoint.archive`에 그대로 기록된다.

| 항목 | 값 |
| --- | --- |
| 보존 방식 | GitHub Release 자산 (`kind: github_release_asset`) |
| 저장소 | `heechan9/bunkering-ai` |
| Release 태그 | `official-eval-2026-09-01` |
| 자산 이름 | `dqn_final.pt` |
| 다운로드 URL | `https://github.com/heechan9/bunkering-ai/releases/download/official-eval-2026-09-01/dqn_final.pt` |
| sha256 | `970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392` |
| 현재 상태 | `pending_upload` — 아래 업로드 절차가 아직 실행되지 않았다 |

`status`가 `pending_upload`인 동안에는 위 URL이 아직 존재하지 않는다. 저장소 권한이
있는 담당자가 다음을 실행한 뒤 `CHECKPOINT_ARCHIVE["status"]`와
`results/evaluation_manifest.json`의 같은 필드를 `published`로 바꾼다.

```bash
gh release create official-eval-2026-09-01 checkpoints/dqn_final.pt \
  --repo heechan9/bunkering-ai \
  --title "Official same-condition evaluation checkpoint (2026-09-01)" \
  --notes "train_seed=42, n_episodes=5000, sha256=970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392"
```

내려받은 파일이 이 결과를 만든 가중치가 맞는지는 sha256으로 대조한다.

```bash
curl -L -o checkpoints/dqn_final.pt \
  https://github.com/heechan9/bunkering-ai/releases/download/official-eval-2026-09-01/dqn_final.pt
python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('checkpoints/dqn_final.pt').read_bytes()).hexdigest())"
# results/evaluation_manifest.json 의 checkpoint.sha256 과 같아야 한다
```

### 3.2 재학습으로 얻는 것과 얻지 못하는 것

manifest에 학습 seed·episode 수·환경설정을 남기므로 **같은 명령으로 동일 조건 재학습이
가능하다**. 다만 재학습 결과가 위 sha256과 **비트 단위로 같은 가중치**가 된다는 보장은
검증하지 않았다. 학습은 `random`·`numpy`·`torch` 전역 시드를 고정하지만, 완전 결정론은
BLAS 스레딩·라이브러리 버전·하드웨어에 따라 달라질 수 있고 이 저장소는 그 재현성을
측정한 적이 없다. 4절의 수치를 그대로 재현해야 한다면 재학습이 아니라 3.1의
체크포인트를 내려받아 `scripts/evaluate.py`로 평가한다.

## 4. 관측 결과 (2026-09-01, episodes=100, base_seed=42)

`configs/dqn.yaml`(`n_episodes: 5000`)로 seed 42에서 학습한 체크포인트를 seed
42~141의 100개 에피소드에서 평가한 값이다. 표준편차는 모집단 기준(ddof=0)이다.
학습은 149,990 step을 진행해 epsilon이 설정 하한 0.05까지 완전히 감쇠했다.

> **표본 구조 (인용 시 반드시 함께 밝힐 것)** — 이 수치는 **학습 seed 42로 한 번
> 학습한 단일 모델**을 **평가 seed 42~141**에서 검증한 결과다. 여기서 흩어짐을 나타내는
> 표준편차는 전부 *평가 에피소드 간* 분산이며 *학습 재현 간* 분산이 아니다. 학습 seed를
> 바꿔 여러 번 학습한 다중 학습 seed 검증은 수행하지 않았으므로, `double_dqn` 행을
> "여러 seed에서 재현된 성능"으로 인용하면 안 된다. rule-based 3종은 학습이 없어
> 학습 seed 개념 자체가 적용되지 않는다.

| policy | reward (mean ± std) | Synthetic Cost Index (mean ± std) | 성공률 | 연료고갈률 | 급유횟수 (mean ± std) |
| --- | --- | --- | --- | --- | --- |
| fixed_fueling | -2.0300 ± 0.0000 | 0.0 ± 0.0 | 0.00 | 1.00 | 0.00 ± 0.00 |
| price_reactive | -1.9519 ± 0.2848 | 17,369.5 ± 103,346.1 | 0.03 | 0.97 | 0.08 ± 0.50 |
| safe_stock | -0.4928 ± 0.0108 | 545,392.7 ± 63,453.9 | 1.00 | 0.00 | 1.00 ± 0.00 |
| double_dqn | 0.0443 ± 0.0579 | 847,117.9 ± 102,320.3 | 1.00 | 0.00 | 5.31 ± 3.48 |

종료원인 (100 에피소드 기준):

| policy | arrived | fuel_depleted | timeout |
| --- | --- | --- | --- |
| fixed_fueling | 0 | 100 | 0 |
| price_reactive | 3 | 97 | 0 |
| safe_stock | 100 | 0 | 0 |
| double_dqn | 100 | 0 | 0 |

관측 사실만 기록하면 다음과 같다.

- `safe_stock`과 `double_dqn` 두 정책만 100 에피소드 전부 도착했다.
  `fixed_fueling`은 100건, `price_reactive`는 97건이 연료고갈로 종료됐다.
- 평균 reward는 `double_dqn`이 0.0443으로 가장 높으며, 네 정책 중 유일한 양수다.
- Synthetic Cost Index는 `double_dqn`이 847,117.9로 가장 높다. `safe_stock`
  (545,392.7)의 약 1.55배이며, 급유 횟수 차이(5.31회 대 1.00회)에서 비롯된다.
- `double_dqn`의 급유 횟수는 에피소드별 3~26회로 흩어져 있고 4회가 47건으로 최빈이다.
  `safe_stock`은 전 에피소드에서 정확히 1회다.
- 이번 실행은 조기 종료가 0건이므로 두 정책의 Cost Index는 모두 30 step을 완주한
  동일 조건에서 비교된 값이다. 조기 종료로 급유량이 적게 집계되는 왜곡이 없다.
- 도착 신뢰성은 두 정책이 같고 비용 지표는 `safe_stock`이 더 낮다. 어느 쪽을 우선할지는
  reward와 비용 중 무엇을 기준으로 삼느냐에 달려 있으며, 이 문서는 그 기준을 정하지 않는다.
- `fixed_fueling`의 Cost Index 0은 출항 시 탱크가 이미 가득 차 실제 주유량이
  0이기 때문이며, 100 에피소드 전부 연료고갈로 종료됐다.

## 5. 해석 경계와 한계

- **학습량이 결과를 좌우한다**: 이전 설정(`n_episodes: 1000`)은 약 30,000 step만
  생성해 `epsilon_decay_steps: 100000`을 소진하지 못했고, epsilon 0.7150에서 학습이
  끝나 `double_dqn`의 성공률이 0.52에 머물렀다. 실패한 48 에피소드는 전부 급유
  0회였다. `n_episodes`를 5000으로 올려 149,990 step을 학습하자 epsilon이 0.05까지
  감쇠하고 성공률이 1.00으로 바뀌었다. 이 결과를 인용할 때는 학습 설정을 반드시
  함께 밝힌다. 수렴 여부 자체는 별도로 검증하지 않았다.
- **합성 환경**: 가격·환율은 합성 random walk이며 실제 유가·환율 연동은 미구현이다.
- **항만 미차등**: 현재 `action=1..n_ports`는 가격·대기시간·수수료가 동일하다.
  따라서 이번 비교는 항만 선택 능력을 측정하지 않는다.
- **Synthetic Cost Index**: 정규화 탱크 기준의 합성 지표이며 실제 USD/KRW 비용이 아니다.
- **표본**: 정책당 100 에피소드, 평가 seed 42~141. 신뢰구간이나 유의성 검정은 아직
  수행하지 않았다.
- **단일 학습 seed**: `double_dqn` 행은 학습 seed 42의 모델 하나에서 나온 값이다.
  학습 seed를 바꿨을 때 성공률 1.00과 급유 5.31회가 유지되는지는 확인하지 않았다.
  4절 첫 실행 이전 설정에서 성공률이 0.52였던 사례가 보여주듯 학습 조건은 결과를
  크게 바꾸므로, 학습 분산은 별도 과제로 남는다.
- **가중치 재현성**: 3.2절 참조. 동일 조건 재학습은 가능하지만 비트 단위 동일 가중치
  복원은 검증되지 않았다.

## 6. 미결 항목 (합의 후 반영)

- **탐색 스케줄 정합성**: 5절 첫 항목의 `epsilon_decay_steps` 대 `n_episodes` 불일치는
  하이퍼파라미터 변경에 해당하므로 별도 합의 후 조정한다.
- **Release 자산 업로드**: 3.1절의 `gh release create` 실행과 `status`를 `published`로
  바꾸는 작업은 저장소 권한이 있는 담당자가 수행한다.

### 해결된 항목

- ~~**README 문구와 감사 규칙의 결합**~~ — 해결됨. `CLAIM-006`은 더 이상 README의 특정
  문장 존재 여부를 보지 않고, `results/evaluation_results.csv`와
  `results/evaluation_manifest.json`의 **존재·상호 정합성·`double_dqn` 기록 포함 여부**로
  비교 수행 상태를 판정한 뒤, README 서술이 그 상태와 어긋나는지만 검사한다. 판정표는
  [`paper_evidence_audit.md`](paper_evidence_audit.md) 1절 6번 항목에 있다.
