# 공통 독립 평가 계약

Double DQN과 세 rule-based 정책을 **동일 조건에서 나중에 평가**하기 위한
코드 계약이다. 이 모듈은 체크포인트를 로드하거나 환경을 실행하거나 CSV를
쓰지 않는다. 따라서 아직 측정하지 않은 성능 결과를 생성하지 않는다.

## 에피소드 결과

각 종료 에피소드마다 `evaluation.contract.EpisodeResult`를 만든다. 필수 값은
`seed`, `episode`, `policy`, `reward`, `synthetic_cost_index`, `success`,
`fuel_depletion`, `bunkering_count`, `termination_reason`이다. `to_row()`의 CSV
표시명은 `Synthetic Cost Index`이며 `CSV_FIELDS`가 열 순서를 정의한다.

종료 원인은 `arrived`, `fuel_depleted`, `timeout`만 허용한다. `success`는
`arrived`와, `fuel_depletion`은 `fuel_depleted`와 정확히 일치해야 한다.
비유한 수, 음수 비용/횟수, 빈 정책명도 생성 시 거부된다.

```python
from evaluation.contract import EpisodeResult

result = EpisodeResult(
    seed=seed,
    episode=episode,
    policy="double_dqn",
    reward=total_reward,
    synthetic_cost_index=info["cumulative_cost_index"],
    success=info["end_reason"] == "arrived",
    fuel_depletion=info["end_reason"] == "fuel_depleted",
    bunkering_count=bunkering_count,
    termination_reason=info["end_reason"],
)
```

## 현수의 독립 평가 스크립트 연결 방법

1. 체크포인트 로딩과 greedy action 선택은 별도 스크립트에 둔다.
2. 정책별 실행 전에 모든 `(episode, seed, env_config)` 조합을
   `EvaluationCase`로 만들고 `validate_fair_evaluation_plan(cases, policies)`를
   호출한다. `env_config`에는 최소한 `BunkeringEnv` 생성자 인자를 모두 넣는다.
3. 실제로 끝난 에피소드만 `EpisodeResult`로 변환한다.
4. 결과가 하나 이상 있을 때만 `aggregate_results(results)`를 호출한다. 반환값은
   정책별 population mean/std (`ddof=0`)이며 reward, Synthetic Cost Index,
   success, fuel depletion, bunkering count를 포함한다.
5. CSV가 필요하면 호출자가 검증된 `result.to_row()`와 `CSV_FIELDS`로 쓴다.
   계약 모듈은 누락 실행을 보완하거나 파일을 자동 생성하지 않는다.

Double DQN과 세 baseline의 우열은 이 계약의 일부가 아니다. 비교 주장은 같은
계획을 통과하고 실제로 수집한 결과가 있을 때만 별도로 판단한다.
