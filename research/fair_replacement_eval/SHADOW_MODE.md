# Shadow mode — 추천 행동 비교 (운영 교체 전)

기존 DQN이 환경에 적용되는 모든 행동을 계속 결정하고, 같은 시점의 관측으로 `planner_ops`(또는 `planner_ops_hist`)가 추천할 행동을 별도로 계산·기록한다. 연구용 CLI이며 기본 평가 경로(`evaluate.py`, `scripts/evaluate.py`)와 기준·시드·공식 결과·체크포인트는 바뀌지 않는다.

## 이 기능이 하는 것 / 하지 않는 것

- 하는 것: DQN 행동과 계획기 추천의 일치·불일치, 각 계산시간, 계획기 예외·잘못된 행동 기록.
- **하지 않는 것: 계획기의 실제 비용·안전 성능 측정.** 계획기 행동은 한 번도 환경에 적용되지 않는다. 불일치율은 성능 차이가 아니다. 계획기 행동을 적용한 평가는 기존 공정 비교 하네스(`evaluate.py`)가 따로 한다.
- shadow 결과는 교체 게이트(G1–G5)·판정에 쓰이지 않는다.

## 사용법

```bash
python -m research.fair_replacement_eval.shadow \
  --checkpoint <체크포인트.pt> --out <빈 출력 폴더> \
  --seeds 60000000:60000099 [--planner planner_ops|planner_ops_hist] [--no-isolation-check]
```

- `--seeds first:last`(양끝 포함)는 필수이며 기본값이 없다. 이미 사용된 범위·학습 범위와의 겹침은 `preflight.json`/`summary.json`에 정보로 기록될 뿐 차단하지 않는다.
- 실행 전 `preflight.py`로 criteria 해시, 체크포인트 형식·차원, `metadata.env_config`, 학습 시드 메타데이터를 검사한다. `fail`이면 에피소드 실행 없이 종료 코드 3. `undecidable`(예: `n_episodes` 누락)은 기록하고 계속한다.
- 종료 코드: 0 정상, 2 출력 폴더가 비어 있지 않음, 3 preflight 실패, 4 격리 검사 불일치.
- 허용 계획기와 정보 범위(`summary.json`의 `planner_information`에도 기록):

  | 계획기 | 정보 단계 | DQN과 같은 정보인가 |
  |---|---|---|
  | `planner_ops` | `I_ops` — 현재 관측만 사용(기억 없음) | 예. DQN이 받는 단일 관측과 같다 |
  | `planner_ops_hist` | `I_ops_hist` — 현재 관측 + 같은 에피소드의 이전 관측(소비량 추정) | **아니오.** DQN보다 많은 정보를 쓴다 |

  미래 가격을 보는 변형은 거부한다. `planner_ops_hist`의 불일치율을 "동일 정보 비교"로 해석하면 안 된다.
- 체크포인트 파일이 없거나 읽을 수 없으면(해시·로드 실패) 예외로 끝나지 않고 `preflight.json`에 `checkpoint_file`/`checkpoint_format` 실패를 기록한 뒤 에피소드 실행 없이 종료 코드 3으로 끝난다.

## 격리 방식

1. DQN 행동을 먼저 계산해 그대로 적용한다. 계획기는 그 뒤에 호출된다.
2. 계획기에는 읽기 전용 관측 복사본과 `max_steps`·`min_safe_fuel`만 가진 객체를 준다. 실제 환경 객체는 전달하지 않아 상태·환경 난수를 읽거나 바꿀 수 없다.
3. 계획기 호출 전후로 python·numpy 전역 난수 상태를 복원한다.
4. 계획기 `Exception`과 잘못된 행동(정수가 아님, bool, 범위 밖)은 기록만 하고 DQN 실행은 계속된다.
5. 기본으로 같은 seed를 shadow 끈 상태로 다시 돌려 두 가지를 비교하고 `summary.json`의 `isolation_check`에 남긴다.
   - 항차 집계(비용·안전·기항·종료 사유 등): `outcome_identical`
   - 스텝별 DQN trace(DQN이 본 관측의 해시, 행동, 보상, terminated/truncated, 다음 관측의 해시): `trace_identical`. 실행시간은 비교에서 제외한다. 집계가 같아도 중간 행동·전이가 다르면 잡는다(예: 같은 급유인 행동 1과 2를 바꿔 내면 집계는 같고 trace는 다르다).
   - 이 비교는 비교한 seed에서의 동일성이며 일반적인 격리 보장이 아니다. shadow를 켠 실행과 끈 실행은 별개의 실행이므로 환경이 결정적이라는 가정에 기댄다.

## 출력 (`--out`)

| 파일 | 내용 |
|---|---|
| `shadow_steps.csv.gz` | 스텝별: seed, step, DQN 행동, 계획기 추천, 상태(`ok`/`error`/`invalid_action`), 불일치(원본·구매/대기), DQN·계획기 계산시간(ns), 오류, 관측 |
| `dqn_episodes.csv.gz` | 실제 적용된 DQN 항차 결과(합성 환경)와 에피소드별 `dqn_trace_sha256` |
| `dqn_trace_shadow_on.csv.gz`, `dqn_trace_shadow_off.csv.gz` | 스텝별 DQN trace(격리 검사를 켰을 때만). 두 파일의 내용이 같아야 한다 |
| `summary.json` | 불일치율, 지연(평균·p50·p95·p99·max), 계획기 실패 집계, 계획기 정보 단계, 격리 검사(집계·trace), `planner_performance_measured: false` |
| `preflight.json`, `manifest.json` | 사전 검증 기록, 해시·환경·git head |

불일치는 *구매 vs 대기*를 기본으로 본다. 이 환경에서 행동 1..n_ports는 같은 급유라서 원본 값 불일치(`disagree_raw`)와 구분해 둔다. 불일치율의 분모는 유효한 추천 수이며 실패한 스텝은 제외하고 별도 집계한다.

## 한계

- 계획기의 추천은 **DQN이 만든 상태**를 기준으로 계산된다. 계획기가 스스로 운항했다면 도달했을 상태가 아니므로, 추천과 DQN 행동이 다르다는 사실만으로 어느 쪽이 낫다고 말할 수 없다.
- 계획기 내부 상태(기항 횟수 추정 등)는 DQN 궤적의 관측으로 갱신된다.
- 계산시간은 이 기계·단일 프로세스에서의 값이다. 계획기에 시간 제한은 없어서 무한 루프는 막지 못한다(예외만 처리).
- `BaseException`(예: `KeyboardInterrupt`)은 잡지 않는다.
- 합성 환경이며 실선 검증이 아니다. 비용은 재고 보정 전의 지표가 아니라 기록하지 않았다.
- 학습 구간과 겹치는 seed에서는 DQN이 학습 중 본 상황일 수 있다.
- 운영 환경의 실시간 연결(실제 관측 스트림)은 구현하지 않았다. 이 CLI는 시뮬레이션 환경에서만 동작한다.
