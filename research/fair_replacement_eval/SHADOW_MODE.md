# Shadow mode — 추천 행동 비교 (운영 교체 전)

기존 DQN이 환경에 적용되는 모든 행동을 계속 결정하고, 같은 시점의 관측으로 `planner_ops`(또는 `planner_ops_hist`)가 추천할 행동을 별도로 계산·기록한다. 연구용 CLI이며 기본 평가 경로(`evaluate.py`, `scripts/evaluate.py`)와 기준·시드·공식 결과·체크포인트는 바뀌지 않는다.

## 이 기능이 하는 것 / 하지 않는 것

- 하는 것: DQN 행동과 계획기 추천의 일치·불일치, 각 계산시간, 계획기 예외·잘못된 행동·**시간 초과** 기록.
- **하지 않는 것: 계획기의 실제 비용·안전 성능 측정.** 계획기 행동은 한 번도 환경에 적용되지 않는다. 불일치율은 성능 차이가 아니다. 계획기 행동을 적용한 평가는 기존 공정 비교 하네스(`evaluate.py`)가 따로 한다.
- shadow 결과는 교체 게이트(G1–G5)·판정에 쓰이지 않는다.
- 시간 초과 격리는 shadow 실행이 계획기 때문에 멈추지 않게 하는 연구 CLI의 안전장치다. 계획기의 성능 개선도, 운영 시스템과의 실시간 연결도 아니다.

## 사용법

```bash
python -m research.fair_replacement_eval.shadow \
  --checkpoint <체크포인트.pt> --out <빈 출력 폴더> \
  --seeds 60000000:60000099 [--planner planner_ops|planner_ops_hist] [--no-isolation-check] \
  [--planner-isolation subprocess|inprocess] [--planner-timeout-sec 1.0] \
  [--planner-startup-timeout-sec 60] [--max-consecutive-timeouts 3]
```

- `--seeds first:last`(양끝 포함)는 필수이며 기본값이 없다. 이미 사용된 범위·학습 범위와의 겹침은 `preflight.json`/`summary.json`에 정보로 기록될 뿐 차단하지 않는다.
- 실행 전 `preflight.py`로 criteria 해시, 체크포인트 형식·차원, `metadata.env_config`, 학습 시드 메타데이터를 검사한다. `fail`이면 에피소드 실행 없이 종료 코드 3. `undecidable`(예: `n_episodes` 누락)은 기록하고 계속한다.
- 종료 코드: 0 정상, 2 출력 폴더가 비어 있지 않음, 3 preflight 실패, 4 격리 검사 불일치. 계획기 시간 초과는 종료 코드를 바꾸지 않는다(기록만 한다).
- 허용 계획기와 정보 범위(`summary.json`의 `planner_information`에도 기록):

  | 계획기 | 정보 단계 | DQN과 같은 정보인가 |
  |---|---|---|
  | `planner_ops` | `I_ops` — 현재 관측만 사용(기억 없음) | 예. DQN이 받는 단일 관측과 같다 |
  | `planner_ops_hist` | `I_ops_hist` — 현재 관측 + 같은 에피소드의 이전 관측(소비량 추정) | **아니오.** DQN보다 많은 정보를 쓴다 |

  미래 가격을 보는 변형은 거부한다. `planner_ops_hist`의 불일치율을 "동일 정보 비교"로 해석하면 안 된다.
- 체크포인트 경로가 일반 파일이 아닌 특수 파일(named pipe·장치 등)이어도 해시 읽기에서 멈추지 않고 같은 방식으로 기록·종료한다.
- 체크포인트 파일이 없거나 읽을 수 없으면(해시·로드 실패) 예외로 끝나지 않고 `preflight.json`에 `checkpoint_file`/`checkpoint_format` 실패를 기록한 뒤 에피소드 실행 없이 종료 코드 3으로 끝난다.

## 격리 방식

1. DQN 행동을 먼저 계산해 그대로 적용한다. 계획기는 그 뒤에 호출된다.
2. 계획기에는 읽기 전용 관측 복사본과 `max_steps`·`min_safe_fuel`만 가진 객체를 준다. 실제 환경 객체는 전달하지 않아 상태·환경 난수를 읽거나 바꿀 수 없다.
3. 계획기 호출 전후로 python·numpy 전역 난수 상태를 복원한다.
4. 계획기 `Exception`과 잘못된 행동(정수가 아님, bool, 범위 밖)은 기록만 하고 DQN 실행은 계속된다.
5. **시간 초과**는 아래 "계획기 시간 제한" 절의 방식으로 격리한다(기본: 별도 프로세스).
6. 기본으로 같은 seed를 shadow 끈 상태로 다시 돌려 두 가지를 비교하고 `summary.json`의 `isolation_check`에 남긴다.
   - 항차 집계(비용·안전·기항·종료 사유 등): `outcome_identical`
   - 스텝별 DQN trace(DQN이 본 관측의 해시, 행동, 보상, terminated/truncated, 다음 관측의 해시): `trace_identical`. 실행시간은 비교에서 제외한다. 집계가 같아도 중간 행동·전이가 다르면 잡는다(예: 같은 급유인 행동 1과 2를 바꿔 내면 집계는 같고 trace는 다르다).
   - 이 비교는 비교한 seed에서의 동일성이며 일반적인 격리 보장이 아니다. shadow를 켠 실행과 끈 실행은 별개의 실행이므로 환경이 결정적이라는 가정에 기댄다.

## 계획기 시간 제한 (`--planner-isolation subprocess`, 기본값)

계획기를 별도 프로세스(spawn 방식 worker)에서 실행하고, 추천 1건마다 `--planner-timeout-sec`(기본 1.0초) 안에 답이 오는지 기다린다.

- **정상**: worker가 `ok`로 답하면 기존과 같이 기록한다. worker는 에피소드와 seed를 넘어 재사용된다(계획기는 스텝 0에서 스스로 초기화).
- **계획기 예외·잘못된 행동**: worker 안에서 잡혀 `error`/`invalid_action`으로 기록된다. worker는 그대로 유지되고 재시작 비용이 없다.
- **시간 초과**: 그 스텝을 `timeout`으로 기록하고 DQN 행동·항차 실행은 그대로 이어진다. 기다리기만 멈추지 않고 worker를 종료한다(SIGTERM → `grace` 1초 안에 안 끝나면 SIGKILL → `join` → 파이프 닫기). 그래서 보통은 백그라운드에서 계획기 계산이 계속 돌지 않는다. 회수는 **최선 노력**이다: SIGKILL과 `join` 뒤에도 worker가 살아 있으면 개수(`workers_not_reaped`)와 pid(`unreaped_worker_pids`)를 기록하고 핸들을 보관하며, 그 실행에서는 새 worker를 더 만들지 않는다(`PlannerUnavailable`). `close()`가 한 번 더 kill을 시도한다. 회수에 성공했을 때만 다음 호출에서 새 worker를 만든다(시작 시간은 `planner_startup_ns`로 따로 기록).
- **worker 비정상 종료**(예: 계획기가 프로세스를 죽임): `error`(`PlannerWorkerDied`)로 기록하고 다음 호출에서 새 worker를 만든다.
- **worker 시작 실패**: 부모의 프로세스 생성 실패(파이프·프로세스 생성/시작의 `OSError` 등), worker 안 factory 예외, 핸드셰이크 시간 초과(`--planner-startup-timeout-sec`)를 모두 같은 경로로 기록한다. 중간에 만들어진 파이프·프로세스는 정리하고, 계획기를 그 실행 동안 사용할 수 없는 것으로 보고 이후 스텝을 `error`(`PlannerUnavailable`)로 기록한다. 재시작을 반복하지 않는다. DQN 실행은 그대로 이어진다. (`KeyboardInterrupt`/`SystemExit`는 삼키지 않는다. 자원만 정리하고 그대로 전파한다.)
- **응답 프로토콜**: worker는 계획기의 반환 객체를 부모로 보내지 않는다. 반환값을 **worker 안에서** 검증·정규화해 `[종류, 값, 계산시간]` 형태의 작은 JSON 메시지(최대 4096바이트, 문자열 300자)로만 보낸다(`ok`+정수 행동 / `invalid`+짧은 사유 / `error`+짧은 사유). 부모는 `recv_bytes(최대 길이)`로 읽고 고정 스키마로 검사하며 계획기 쪽에서 온 어떤 것도 unpickle하지 않는다. 스키마에 맞지 않거나 너무 큰 응답은 프로토콜 오류(`PlannerProtocolError`)로 기록하고 그 worker를 버린다(스트림을 믿을 수 없다). 행동의 범위 검사는 부모가 환경의 행동 수로 한다.
- **제한 시간의 성격 — 응답 대기 예산(soft deadline)**: `--planner-timeout-sec`는 요청을 보낸 뒤 남은 시간 동안 `poll()`로 응답이 시작되기를 기다리는 예산이다. 응답이 시작되면 크기가 제한된 `recv_bytes`와 스키마 검사가 부모에서 동기로 실행되며 선점되지 않는다. 내장 worker의 응답은 작은 단일 메시지라 이 구간은 마이크로초 단위지만, 엄격한 벽시계 상한을 **보장하지는 않는다**(OS 스케줄링 지연, 동기 수신·파싱). 파싱이 끝난 뒤 기한을 다시 확인해, 기한을 넘겨 완료된 응답은 추천으로 채택하지 않고 `timeout`(늦은 응답 폐기, worker 종료)으로 기록한다. 계획기 코드가 일부러 worker의 파이프에 직접 쓰는 경우(헤더만 쓰고 본문을 늦게 보내는 등)는 범위 밖이며, 이때 부분 수신 대기는 예산을 넘을 수 있다. 예산에 **포함되지 않는** 것: worker 시작과 실패 뒤 worker 종료·join. 시작 제한(`--planner-startup-timeout-sec`)은 `Process.start()`가 반환한 뒤부터 적용되므로 OS의 프로세스 생성 호출 자체는 그 숫자로 제한되지 않는다. 종료·join은 worker당 최대 약 `2 × grace`다.
- **연속 시간 초과**: 한 에피소드에서 연속 `--max-consecutive-timeouts`(기본 3)번 시간 초과가 나면, 그 에피소드의 남은 스텝은 계획기를 호출하지 않고 `skipped`로 기록한다. 다음 에피소드에서는 다시 시도한다. 0이면 건너뛰지 않는다. 중간에 한 번이라도 답이 오면 연속 횟수는 0으로 돌아간다.
- `inprocess` 모드는 기존 방식(같은 프로세스, 시간 제한 없음)이다. 계획기가 멈추면 실행도 멈추므로 시간 제한이 필요한 실행에는 쓰지 않는다. `summary.json`의 `planner_isolation.time_limit_enforced`로 어느 방식이었는지 남는다.

### 과거 관측 상태(`planner_ops_hist`)

계획기의 내부 상태(이전 관측)는 worker 안에 있다. 시간 초과·비정상 종료·건너뜀이 생기면 worker가 새로 만들어지거나 일부 관측을 받지 못하므로 그 에피소드의 이후 추천은 과거 관측이 불완전하다. 이를 숨기지 않고 스텝마다 `planner_history_intact`로 표시한다.

- 값의 뜻: 이 호출 *직전까지* 계획기가 이 에피소드의 이전 관측을 전부 순서대로 받았는가. 스텝 0은 항상 참. 에피소드의 **첫 실패**(시간 초과·worker 사망·프로토콜 오류·시작 실패)가 난 호출은 그 시점까지 온전했다면 참이고, 그 뒤 같은 에피소드의 모든 호출은 거짓이다(두 번째 연속 시간 초과 호출도 이미 거짓). 새 에피소드에서는 다시 참으로 시작한다. 연속 시간 초과로 인한 `skipped`는 다음 에피소드에서 재시도하지만, worker 시작 실패의 `unavailable`은 그 실행 전체에 유지된다.
- `summary.json`에는 `valid_recommendations_with_incomplete_planner_history`와 이를 뺀 `disagreement_buy_vs_wait_history_intact_only`가 따로 남는다. 불일치율을 해석할 때는 이 값을 같이 봐야 한다.
- `planner_ops`(`I_ops`)는 현재 관측만으로 추천하므로 추천 값은 이 상태에 영향을 받지 않지만, 표시는 같은 규칙으로 붙는다. `planner_ops_hist`는 재시작 직후 첫 호출에서 소비량 추정을 공칭값으로 대신 쓰게 되어 추천이 달라질 수 있다.
- 재시작 후 이력을 다시 채워 넣는(replay) 방식은 쓰지 않는다. 계산이 길어져 시간 제한의 목적과 어긋나기 때문이다.

### 시간 기록: 계산시간과 프로세스 통신 시간의 구분

| 필드(`shadow_steps.csv.gz`) | 의미 |
|---|---|
| `planner_ns` | worker 안에서 `planner.select_action`이 실제로 걸린 시간(계산시간). 시간 초과·건너뜀이면 비어 있다 |
| `planner_roundtrip_ns` | 부모가 요청 전송을 시작해 응답을 받아 파싱할 때까지(또는 기한이 끝날 때까지)의 시간. 이 호출 자체가 DQN 루프를 막는 시간이며, 시작·정리 시간은 포함하지 않는다 |
| `planner_ipc_ns` | `roundtrip − compute`. 직렬화·파이프 전달·스케줄링·worker 루프 오버헤드의 합이며 더 나눌 수 없다 |
| `planner_startup_ns` | 이 호출이 worker를 새로 시작했다면 프로세스 생성부터 핸드셰이크 결과(성공·실패)까지의 시간(roundtrip에 포함되지 않음) |
| `planner_cleanup_ns` | 시간 초과·비정상 종료·프로토콜 오류·시작 실패 뒤 worker를 종료·join하는 데 걸린 시간. 시작 실패의 정리 시간은 `planner_startup_ns`가 아니라 여기에 따로 기록된다 |

`summary.json`에는 `latency_planner_compute`(= 기존 `latency_planner`), `latency_planner_roundtrip`, `latency_planner_ipc`, 시작·정리·시간 초과 대기 합계가 따로 있다. 시간 초과 스텝은 계산시간 분포에 넣지 않고 개수(`planner_timeout_steps`)와 대기 합계(`planner_timeout_wait_ms_total`)로 따로 센다.

### 제한 시간 선택 근거와 한계

- 기본값 1.0초는 **성능 요구사항에서 도출한 값이 아니다.** 이 연구 환경에서 `planner_ops` 계산시간 최대가 수 ms(앞선 공식 체크포인트 shadow 실행 600스텝에서 p99 약 2 ms, 최대 약 2.7 ms; 이번 작업의 별도 측정 145회에서 평균 0.56 ms, 최대 2.1 ms, 통신 오버헤드 평균 0.14 ms·최대 0.37 ms, worker 시작 약 150–200 ms)이므로, 일시적인 스케줄링 지연이나 느린 기계에서 정상 호출이 시간 초과로 오인되지 않을 만큼 넉넉하면서 멈춘 계획기를 스텝당 1초 이내로 묶는 값으로 골랐다. 위 수치는 이 기계·이 환경의 관측이며 다른 환경을 보장하지 않는다. 실행 환경이 느리면 `--planner-timeout-sec`를 늘린다.
- 지연의 **대략적인 설계 상한**(엄격한 보장이 아니다 — 위 soft deadline 참고): 호출 1건이 DQN 루프를 막는 시간은 `제한 시간 + 정리(최대 약 2 × grace) + (worker를 새로 시작해야 했다면) 시작 시간(`Process.start()` 이후 최대 --planner-startup-timeout-sec, 기본 60초; 생성 호출 자체는 제외)`을 기준으로 잡는다. roundtrip만이 DQN을 막는 전부가 아니다. 한 에피소드에서 계획기가 계속 멈추면 연속 초과 한도 횟수만큼 이 값이 반복된다(한도 0이면 스텝 수만큼). 관측 예시: 기본값에서 정상 시작은 약 0.15–0.2초이므로 에피소드당 약 3 × (1 s + 0.2 s), 이 값은 상한이 아니다. 시작이 실패하면 계획기가 그 실행 동안 unavailable이 되어 더는 반복되지 않는다.
- 제한은 **벽시계 시간**이다. CPU·메모리 사용량은 제한하지 않는다.
- 계획기가 자체적으로 하위 프로세스를 만들면 그 하위 프로세스는 회수하지 못한다.
- worker 종료는 SIGTERM/SIGKILL과 `join`에 의존한다. 커널 상태(예: 해제되지 않는 uninterruptible sleep)로 SIGKILL 뒤에도 남는 극단 경로는 실제 OS 상태로 재현하지 못했고, 가짜 프로세스 객체로 기록·중단 동작만 시험했다.
- 부모 프로세스가 SIGKILL 등으로 강제 종료되면, 무한 계산 중인 worker는 스스로 끝나지 않을 수 있다. 정상 종료·예외 종료·`KeyboardInterrupt` 때는 `finally`에서 worker를 정리한다.
- DQN 행동 계산은 이 제한과 무관하며, 시간 초과는 DQN 행동·보상·관측을 바꾸지 않는다. `isolation_check`는 시간 초과가 생긴 실행에서도 shadow를 끈 실행과 스텝별 trace를 비교한다(비교한 seed에 한한 동일성).
- 이 기능은 계획기를 더 빠르게 하거나 더 좋게 만들지 않는다. 계획기의 비용·안전 성능, 운영 연결과 무관하다.

## 출력 (`--out`)

| 파일 | 내용 |
|---|---|
| `shadow_steps.csv.gz` | 스텝별: seed, step, DQN 행동, 계획기 추천, 상태(`ok`/`error`/`invalid_action`/`timeout`/`skipped`), 불일치(원본·구매/대기), DQN 계산시간, 계획기 계산·왕복·통신·시작·정리 시간(ns), `planner_history_intact`, 오류, 관측 |
| `dqn_episodes.csv.gz` | 실제 적용된 DQN 항차 결과(합성 환경)와 에피소드별 `dqn_trace_sha256` |
| `dqn_trace_shadow_on.csv.gz`, `dqn_trace_shadow_off.csv.gz` | 스텝별 DQN trace(격리 검사를 켰을 때만). 두 파일의 내용이 같아야 한다 |
| `summary.json` | 불일치율, 지연(평균·p50·p95·p99·max; 계산/왕복/통신 구분), 계획기 실패·시간 초과·건너뜀 집계, 계획기 정보 단계, 시간 제한 설정(`planner_isolation`: 모드·제한 시간·worker 시작/종료/회수 집계), 격리 검사(집계·trace), `planner_performance_measured: false` |
| `preflight.json`, `manifest.json` | 사전 검증 기록, 해시·환경·git head |

불일치는 *구매 vs 대기*를 기본으로 본다. 이 환경에서 행동 1..n_ports는 같은 급유라서 원본 값 불일치(`disagree_raw`)와 구분해 둔다. 불일치율의 분모는 유효한 추천 수이며 실패한 스텝은 제외하고 별도 집계한다.

## 한계

- 계획기의 추천은 **DQN이 만든 상태**를 기준으로 계산된다. 계획기가 스스로 운항했다면 도달했을 상태가 아니므로, 추천과 DQN 행동이 다르다는 사실만으로 어느 쪽이 낫다고 말할 수 없다.
- 계획기 내부 상태(기항 횟수 추정 등)는 DQN 궤적의 관측으로 갱신된다.
- 계산시간은 이 기계에서의 값이다. 시간 제한은 `subprocess` 모드에서만 적용된다(`inprocess`는 무한 루프를 막지 못한다). 한계는 위 "제한 시간 선택 근거와 한계" 참고.
- `BaseException`(예: `KeyboardInterrupt`)은 잡지 않는다.
- 합성 환경이며 실선 검증이 아니다. 비용은 재고 보정 전의 지표가 아니라 기록하지 않았다.
- 학습 구간과 겹치는 seed에서는 DQN이 학습 중 본 상황일 수 있다.
- 운영 환경의 실시간 연결(실제 관측 스트림)은 구현하지 않았다. 이 CLI는 시뮬레이션 환경에서만 동작한다.
