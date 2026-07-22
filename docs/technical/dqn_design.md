# DQN 구조 설계 문서

**SDS STEP 2 — RL 환경 설계 · 모델 구현** | 작성: 최희찬 (PM/RL Technical Lead) | 상태: 초안 (구현 착수 전)

> `BunkeringEnv`(envs/bunkering_env.py)를 대상으로 하는 DQN 에이전트 설계.
> 사업화 문서 03장 "왜 DQN을 1차로 선택했는가" 근거(이산 Action Space에 적합, Experience Replay·Target
> Network로 학습 안정성 확보)를 그대로 구현 기준으로 사용한다.

## 1. 네트워크 구조 (초안)

```
Input (state_dim = 6, MVP 기준 state_action_reward_spec.md 참고)
  → Linear(6, 128) → ReLU
  → Linear(128, 128) → ReLU
  → Linear(128, action_dim)   # action_dim = 1 + n_ports
```

- 은닉층 크기(128)는 초기값 — 8월 하이퍼파라미터 튜닝(STEP 03) 시 탐색 대상
- State/Action 차원이 확정되면(항만 수 N 확정 후) 재계산 필요

## 2. 핵심 구성요소

| 구성요소 | 적용 여부 | 설명 |
|---|---|---|
| Experience Replay | 적용 | Replay Buffer 크기 초기값 100,000 (튜닝 대상) |
| Target Network | 적용 | 매 N step마다 동기화 (초기값 1,000 step) |
| Double DQN | 적용 | 사업화 문서 STEP02 근거대로 과대추정 방지 |
| Epsilon-Greedy | 적용 | 초기 ε=1.0 → 최종 ε=0.05, 감쇠 스케줄은 튜닝 대상 |
| Dueling DQN | 미정 | 초기 MVP 범위 밖 — 성능 부족 시 STEP03에서 추가 검토 |

## 3. 하이퍼파라미터 (초기값 — 전부 튜닝 대상, STEP 03에서 확정)

| 파라미터 | 초기값 | 비고 |
|---|---|---|
| learning_rate | 1e-4 | |
| gamma | 0.99 | |
| batch_size | 64 | |
| replay_buffer_size | 100,000 | |
| target_update_freq | 1,000 step | |
| epsilon_start / end / decay | 1.0 / 0.05 / 선형 감쇠 (10만 step 기준) | |

## 4. 학습 루프 구조 (scripts/train.py 예정 로직)

```
for episode in range(N_EPISODES):
    state, _ = env.reset()
    done = False
    while not done:
        action = agent.select_action(state, epsilon)
        next_state, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        replay_buffer.push(state, action, reward, next_state, done)
        agent.update(replay_buffer.sample(batch_size))
        state = next_state
    if episode % target_update_freq_episodes == 0:
        agent.sync_target_network()
    logger.log_scalar("episode_reward", ...)   # TensorBoard (김승현 파이프라인 연동)
```

## 5. 구현 우선순위 (7~8월)
1. `agents/dqn.py` — Q-Network, Replay Buffer, Double DQN 업데이트 로직 (7월 말)
2. `scripts/train.py` — 학습 루프 + TensorBoard 로깅 연동 (8월 초, 김승현과 협업)
3. `configs/dqn.yaml` — 하이퍼파라미터 외부화
4. 8월 중순: 첫 학습 실행 → Episode Reward 수렴 여부 1차 확인

## 6. 미확정 사항
- [ ] 항만 후보 수(N) 확정 → action_dim 확정
- [ ] Reward 계수 확정 전까지는 Q값 수렴 여부만 확인, 실제 절감률 해석 보류
- [ ] Dueling DQN 도입 여부 (성능 이슈 발생 시 재검토)
