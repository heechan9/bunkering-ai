# Rule-based 독립 강건성 검증 (200 seed)

Rule-based 3종(`fixed_fueling`·`price_reactive`·`safe_stock`)을 저장소의 공식 평가
파이프라인 **바깥에서** seed 200개로 독립 실행한 강건성 검증 기록이다.

> **이 문서는 공식 결과가 아니다.**
> 논문의 정본 비교는 여전히
> [`official_evaluation.md`](official_evaluation.md)의 100-seed 4정책 결과
> (`results/evaluation_results.csv`, `results/evaluation/`)다.
> 이 검증은 그 수치를 대체하거나 재실행하지 않으며, DQN을 포함하지 않는다.
> 공식 산출물은 이 작업으로 한 바이트도 변경되지 않았다.

## 1. 무엇이 "독립"인가

| 항목 | 공식 평가 | 이 강건성 검증 |
| --- | --- | --- |
| 실행 주체 | `scripts/evaluate.py` | `scripts/robustness/script2_baseline_200seed_eval.py` (별도 하네스) |
| 정책 | rule-based 3종 + `double_dqn` | rule-based 3종만 |
| seed | 42–141 (100개) | 42–241 (200개) |
| 체크포인트 | 필요 (`dqn_final.pt`) | 불필요 (torch 미임포트) |
| 산출물 | `results/evaluation/` | `results/robustness/` |

하네스·seed 범위·산출물은 이 스크립트가 단독으로 만든다. 다만 **정책 로직과 환경은
재구현하지 않고** 저장소의 `scripts/baseline.py`와 `envs/bunkering_env.py`를 그대로
임포트한다. 커밋된 코드와 동작이 갈라질 수 없게 하려는 의도다.

`script1_public_data_verification.py`는 UPA 공공데이터 기술통계(PR #8)를
`scripts/analyze_upa_public_data.py`를 호출하지 않고 원본 CSV에서 직접 재도출한다.
따라서 원본 코드의 재실행이 아니라 진짜 독립 대조다.

## 2. 실행 조건

| 항목 | 값 |
| --- | --- |
| 검증 시점 main 커밋 | `f915df9922b63bade92c2efba0f7c74f66c21316` |
| `env_config` | `n_ports=3, max_steps=30, min_safe_fuel=0.15` (`configs/dqn.yaml`의 `env` 절과 동일) |
| seed 범위 | 42–241 (200 에피소드 × 3정책 = 600 케이스) |
| 표준편차 규약 | 모집단 표준편차 (`numpy.std`, ddof=0) — 공식 `summary.csv`와 동일 |
| 공공데이터 SHA-256 | `b42537ebde057e87ef15f91a8c0fca6ab0ee010ff557b78a531112d4e79da1b7` |

### 실행 방법

두 스크립트 모두 **저장소 루트에서** 실행한다 (`sys.path`에 `.`를 넣고
`envs`·`scripts`를 임포트하므로 CWD가 루트여야 한다).

```bash
pip install -r requirements.txt
PYTHONPATH=. python scripts/robustness/script1_public_data_verification.py
PYTHONPATH=. python scripts/robustness/script2_baseline_200seed_eval.py
```

`script2`는 `envs/bunkering_env.py`를 통해 **gymnasium을 요구한다.** `pip install
numpy pandas`만으로는 임포트 단계에서 실패한다. 최소 구성으로 돌리려면
`pip install numpy pandas gymnasium`이 정확한 전체 목록이다(`script1`은 pandas·numpy만
필요). `requirements.txt`가 나열하는 torch·tensorboard·matplotlib·plotly·streamlit은
두 스크립트 모두 임포트하지 않는다.

`script2`는 산출물을 **CWD에 쓴다.** 위 명령을 루트에서 실행하면 루트에 생성되므로,
저장소에 반영할 때는 `results/robustness/`로 옮긴다. 커밋된 4개 파일이 그 결과다.

### 공공데이터 무결성 실패 처리

`script1`은 기록된 SHA-256을 출력만 하지 않고 실행 시점에 `hashlib`으로 디스크의
파일을 다시 해싱해 대조한다. 불일치하면 분석을 수행하지 않고 종료 코드 1로 중단한다.
파일 끝에 1바이트를 덧붙여 실제로 확인했다.

```
expected SHA-256: b42537eb...79da1b7
computed SHA-256: e3c303e6...13657ec
FATAL: SHA-256 mismatch for data/public/upa_bunkering_anchorage_20240819.csv
```

즉 조용히 수정되었거나 리비전이 다른 CSV는 통과하지 못한다.

## 3. 산출물

| 경로 | 내용 |
| --- | --- |
| `results/robustness/independent_eval_raw_with_episode.csv` | 600행 원본 기록(정책×seed) |
| `results/robustness/independent_eval_summary_final.csv` | 정책별 200-seed 집계(ddof=0) |
| `results/robustness/independent_eval_stability_final.csv` | 누적 seed 윈도우별 추정치 변화 |
| `results/robustness/independent_eval_manifest.json` | 실행 조건과 600개 case 목록 |

## 4. 200-seed 결과

| 정책 | reward mean | reward std(ddof=0) | 도착 | 연료고갈 | 평균 벙커링 횟수 |
| --- | --- | --- | --- | --- | --- |
| `fixed_fueling` | -2.0300 | 0.0 | 0 / 200 | 200 / 200 | 0.000 |
| `price_reactive` | -1.9539 | 0.2776 | 6 / 200 | 194 / 200 | 0.095 |
| `safe_stock` | -0.4919 | 0.0122 | 200 / 200 | 0 / 200 | 1.000 |

timeout 종료는 세 정책 모두 0건이다. `fixed_fueling`의 std `4.44e-16`은 부동소수점
잔차이며 실질적으로 0이다(모든 에피소드가 동일하게 즉시 연료고갈로 끝난다).

## 5. 공식 100-seed 결과와의 대조

이 실행의 seed 42–141 구간은 공식 평가와 같은 seed·같은 `env_config`다. 두 산출물을
에피소드 단위로 대조한 결과 **rule-based 3종 × 100 에피소드 = 300건 전부**
`reward`·`synthetic_cost_index`·`bunkering_count`·`termination_reason`이
완전히 일치했다(최대 절대 오차 0).

| 정책 | 공식 reward mean (100-seed) | 이 검증의 100-seed 윈도우 |
| --- | --- | --- |
| `fixed_fueling` | -2.0300 | -2.0300 |
| `price_reactive` | -1.9519 (도착 3) | -1.9519 (도착 3) |
| `safe_stock` | -0.4928 (도착 100) | -0.4928 (도착 100) |

별도 하네스가 공식 수치를 그대로 재현했다는 뜻이며, 이것이 이 검증의 핵심 결과다.

## 6. 누적 윈도우 해석 시 주의

20/50/100/150/200 윈도우는 **독립된 5개 표본이 아니다.** 전부 같은 `BASE_SEED=42`에서
시작하는 같은 200-seed 실행의 누적 접두사다. 50-seed 윈도우는 100·150·200 윈도우에도
포함된다. "seed를 늘려갈 때 추정치가 어떻게 수렴하는가"로 읽어야 하며, 다섯 번의
독립 실험으로 읽으면 안 된다.

`price_reactive`의 도착률은 20-seed에서 0.10, 200-seed에서 0.03으로 내려간다. 초기
소표본이 이 정책을 과대평가했다는 뜻이다. 반대로 `safe_stock`은 20-seed부터 200-seed까지
도착률 1.00과 reward mean -0.492±0.001 수준을 유지해, 100-seed 공식 결과가 소표본
우연이 아님을 보인다.

## 7. 기여

200-seed 독립 검증 설계와 두 스크립트 작성은 승현이 수행했고, 저장소 반영 시점에
공개데이터 해시·환경 API·공식 결과 대조를 재검증했다. 스크립트는 검증받은 원문
그대로 커밋했다.
