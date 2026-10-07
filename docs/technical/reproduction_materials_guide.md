# 모델·평가 재현 자료 찾아보기

2026-10-07 정리. 공식 결과 재현, 후속 연구 비교, 대리 검증은 목적과 모델이 다르다. 코드·공개 결과는 GitHub를 기준으로 하고 원자료·모델 묶음은 기존 Drive에서 찾는다. Drive 접근에는 허가된 계정이 필요하다.

## 목적에 따라 선택

| 하려는 일 | 사용할 자료 | 주의점 |
|---|---|---|
| 기존 공식 4정책 × 100항차 재현 | [공식 Release](https://github.com/heechan9/bunkering-ai/releases/tag/official-eval-2026-09-01)의 dqn_final.pt, [실행 안내](official_evaluation.md) | 평가 seed 42–141은 학습 범위와 겹칠 수 있어 새 독립 교체 판정에 쓰지 않음 |
| 공식 DQN과 동일 관측 계획기 비교 기록 확인 | [공식 A3 평가 ZIP](https://drive.google.com/file/d/1ceN7M5bCmVKb_d-vPkjDEKY3_T8_lE9H/view?usp=drivesdk), [PR #104](https://github.com/heechan9/bunkering-ai/pull/104) | 50M 시드 1,000건; 합성 연구이며 운영 교체 아님 |
| 4개 독립 학습 seed의 원본 비교·연료수지 확인 | [4seed·원본평가 폴더](https://drive.google.com/drive/folders/1dNGPH5qu2QoWmC66-crlLtSHpJ_tbnxP), [출처·해시](../../results/diagnostics/review_4seed/provenance.json) | seed 42/1042/2042/3042 모델과 원본·재실행 ZIP을 구분; manifest의 바이트 차이를 원본 덮어쓰기로 해결하지 않음 |
| 공정 비교 하네스의 대리 모델 검증 확인 | [하네스 안내](../../research/fair_replacement_eval/README.md)의 synthetic_validation 및 synthetic_validation_confirmation | 공식 체크포인트 평가 아님. 대리 학습 5M, 개발 10M, 기존 확인 40M 이력 보존 |
| NTNU 별도 재학습 확인 | [원본 재학습 ZIP](https://drive.google.com/file/d/1UYhsZLRBDM8W2ykSFtUmY_zvdvlmBzRY/view?usp=drivesdk), [연구 안내](../../research/ntnu_bunkering/RETRAINING.md) | 운영 BunkeringEnv·공식 DQN과 다른 연구 조건, 효율 가정 포함 |
| NTNU 5행동/6행동 비교학습 확인 | [비교학습 ZIP](https://drive.google.com/file/d/15uVa4QQCQQGNr0wzV3vIqYb06gDoKaus/view?usp=drivesdk), [후속 코드](../../research/action_space_followup/README.md) | 원본 NTNU 재학습 및 공식 A3 평가와 섞어 집계하지 않음 |

## 공식 A3 평가 자료의 위치와 구성

Drive의 **06_학습모델_및_재현** 바로 아래 `공식DQN_동일관측평가_A3_20261007_운영교체아님.zip`을 사용한다. 기존 이력·탐색 폴더에서 이동했으며 파일 ID는 유지했다.

- 공식 모델 사본, 프로토콜, 보고서, 집계·manifest, 압축 에피소드 및 회귀검사 로그를 보관한다.
- 공식 모델 SHA-256: `970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392`.
- 공개 보고서·집계의 고정 버전: [#104 head 2a73a05](https://github.com/heechan9/bunkering-ai/tree/2a73a05e9a7d79fc5e742f99b7c3897059a65b24/research/fair_replacement_eval).
- #105의 사전 검증은 이후 실행용이다. 기존 A3 ZIP에 `preflight.json`이 없는 것은 정상이며 추가해서 과거 실행 기록처럼 만들지 않는다.
- ZIP을 풀어 기존 결과를 덮어쓰지 않는다. 재실행은 비어 있는 별도 출력 폴더로 하고 사용 커밋·의존성·모델 해시를 함께 기록한다.

## 시드와 판정 해석

| 범위 | 용도·사용 이력 |
|---|---|
| 42–141 | 기존 공식 결과 재현·일치 검사 |
| 42–5041 | 공식 DQN 메타데이터상 학습 시드 |
| 5,000,000–5,002,999 | 대리 DQN 학습 |
| 10,000,000–10,000,999 | 개발 평가 |
| 40,000,000–40,000,999 | 대리 확인 평가에 이미 사용 |
| 50,000,000–50,000,999 | A3 공식 비교에 사용 완료 |

후보를 튜닝한 뒤 사용된 집합을 새로운 독립 확인 집합이라고 부르지 않는다. 파일 해시는 무결성을 확인하며 그 자체로 사전등록 시점을 증명하지 않는다. 비용은 재고 보정 SCI이고 실제 화폐·실선 절감률이 아니다.

## 기록을 읽는 순서

1. [현재 진행 상태](../PROJECT_STATUS.md)에서 병합 여부와 검증 주체 확인.
2. 해당 실험의 README·프로토콜·manifest를 먼저 읽고 모델과 입력 해시 대조.
3. 원본 결과와 재실행 결과를 별도 경로에 보존.
4. [Drive 최신 자료목록](https://drive.google.com/file/d/1H42yNhpf0Ho0kJyZsCt7b7sdUn3UMzfb/view?usp=drivesdk)에서 추가 자료 위치 확인.

요구·정리 승인: 최희찬. 안내 작성: Codex. 이번 정리는 새 성능 실험이 아니다.
