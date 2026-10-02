# 병커시유 | Bunkering-AI

선박의 가격·환율·연료잔량·잔여항로를 바탕으로 급유 의사결정을 실험하는 프로젝트입니다.
합성 항해 환경에서 규칙 기반 정책 3종과 Double DQN을 같은 조건으로 비교하고,
구매·소비·최종잔량과 결과의 근거를 함께 확인합니다.

[웹 시연](https://bunkering-ocean-lab.hc24734503.chatgpt.site/) ·
[빠른 시작](#빠른-시작) ·
[평가 결과](#평가-결과) ·
[자료 위치](#자료-위치와-최신본) ·
[진행 상태](docs/PROJECT_STATUS.md)

![병커시유 프로젝트 대표 이미지](docs/assets/bunkering-project-hero.png)

## 현재 상태

2026-10-03 문서 정리 기준입니다. 상세 기록은 각 실행 시점의 근거를 따릅니다.

| 항목 | 상태와 확인 위치 |
|---|---|
| 코드·공개 결과 | 이 저장소에서 관리. [평가계약](docs/technical/evaluation_contract.md)과 CSV·JSON을 함께 확인 |
| 웹 | 30판 배포 완료 기록. [웹 소스·실행 안내](web/README.md), [최종 검사 기록](docs/audits/final_web_check_20261002.md) |
| 논문 | 멘토 검토 반영 최종 파일로 제출했다고 사용자가 2026-10-01 확인. [제출 상태·파일 식별](docs/submission/submission_status.md) |
| 비공개 자료 | Google Drive에 원본 데이터·제출본·수정본·인수인계 자료 분류. 아래 자료 목록 참조 |
| 남은 확인 | 최신 배포본의 실제 브라우저·모바일 UI, 실선 자료의 밀도·시간 정합성, 실제 구매정책 성능 |

논문 제출은 채택·심사 통과를 뜻하지 않습니다.
공개 [v7.5 원고](docs/submission/ack_paper_v7_5.md)와 이전 원고는 작성 이력이며 최종 제출본이 아닙니다.

## 주요 기능

- **정책 비교:** 고정 급유·가격 반응형·안전재고·Double DQN을 동일 seed·평가 횟수·환경설정으로 평가합니다.
- **결과 추적:** 구매량·소비량·잔량·급유 행동 횟수·합성비용과 원본 CSV·체크포인트 해시를 연결합니다.
- **Ocean Lab:** 한·영 전환, 7개 지역 지도, 항차 기록 재생·초기화, 구매안 비교와 자료 출처 확인을 제공합니다.
- **항차 자료 검토:** CSV 입력·연료수지·자료 변경 비교와 한바다호 AB-LOG 집계 검토를 지원합니다.

지도·선박 모형은 설명용입니다. 지역 선택은 평가 조건을 바꾸지 않으며, 실제 항적이나 선박 물리 시뮬레이션을 의미하지 않습니다.

## 빠른 시작

### Python 환경

Python 3.11 환경에서 저장소 루트 기준으로 실행합니다.

```bash
git clone https://github.com/heechan9/bunkering-ai.git
cd bunkering-ai
python -m pip install -r requirements.txt
```

가상환경 생성·활성화는 사용하는 Conda 또는 venv 환경에 맞춰 진행합니다.

### 공식 결과 재현 — 재학습 불필요

[공식 Release](https://github.com/heechan9/bunkering-ai/releases/tag/official-eval-2026-09-01)에서
`dqn_final.pt`를 내려받아 `checkpoints/dqn_final.pt`로 저장합니다.
`checkpoints` 폴더가 없으면 먼저 생성합니다. 다운로드·해시 대조의
[Bash 및 PowerShell 예시](docs/technical/official_evaluation.md)를 참고하세요.

공식 파일 SHA-256:

```text
970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392
```

```bash
python scripts/evaluate.py --episodes 100 --seed 42 --checkpoint checkpoints/dqn_final.pt --output-dir results/local_reproduction
```

결과는 `results/local_reproduction/`의 `evaluation_results.csv`,
`evaluation_manifest.json`, `evaluation/summary.csv` 등에 생성됩니다.
저장소의 공식 결과와 별도 경로에 기록합니다.
재학습은 동일 가중치를 보장하지 않으므로 공식 수치 대조에는 배포 체크포인트를 사용합니다.

### 검사와 추가 실험

```bash
# 현재 저장소의 테스트 및 공식 근거 검사
python -m pytest -q
python -m scripts.audit_paper_evidence
```

근거 감사는 저장소의 공식 결과를 대상으로 합니다. 위 별도 재현 폴더를 자동 검사하는 명령은 아닙니다.
새 학습·기준선·항로 스트레스·소비량 민감도 실행은
[공식 평가](docs/technical/official_evaluation.md),
[Route-stress](docs/technical/route_stress_minimum_slice.md),
[V1.5 평가](docs/technical/v1_5_robustness.md)를 따릅니다.

### 웹 로컬 실행

Node.js·pnpm 요구 버전은 [웹 README](web/README.md)를 확인합니다.

```bash
cd web/ocean-lab
pnpm install --frozen-lockfile
pnpm dev
```

출력된 로컬 주소를 엽니다. 프로덕션 빌드는 `pnpm build`입니다.
GitHub 반영과 웹 배포는 별개이며 GitHub push만으로 자동 배포되지 않습니다.

## 평가 결과

### 공식 단일 체크포인트 비교

Rule-based 3종과 Double DQN의 **공식 동일조건 성능비교를 수행했으며**,
정본은 [원본 CSV](results/evaluation_results.csv)와
[평가 manifest](results/evaluation_manifest.json)입니다.
학습 seed 42의 모델 하나를 평가 seed 42~141의 100개 합성 항차에서 비교했습니다.

| 정책 | 평균 Reward | Synthetic Cost Index | 성공률 | 연료고갈률 | 평균 급유횟수 |
|---|---:|---:|---:|---:|---:|
| Fixed Fueling (고정 급유) | -2.030 | 0 | 0% | 100% | 0.00 |
| Price Reactive (가격 반응형) | -1.952 | 17,370 | 3% | 97% | 0.08 |
| Safe Stock (안전재고) | -0.493 | 545,393 | 100% | 0% | 1.00 |
| Double DQN (학습 정책) | 0.044 | 847,118 | 100% | 0% | 5.31 |


Double DQN은 평균 보상이 가장 높았지만 Safe Stock보다 SCI와 급유 행동 횟수도 높았습니다.
낮은 SCI만으로 실패 정책을 우수하다고 평가하지 않으며, 도착 여부·연료 부족·잔량을 함께 봅니다.
[공식 평가 상세](docs/technical/official_evaluation.md)

### 네 개 학습 체크포인트의 연료수지 진단

학습 seed 42·1042·2042·3042의 기본조건 결과입니다.
위 단일 체크포인트 표와 구분해서 사용합니다.

| 항차 평균 | Safe Stock | DQN 4개 체크포인트 평균 |
|---|---:|---:|
| 도착률 | 100% | 100% |
| 총급유량 | 0.85000 | 1.31325 |
| 소비량 | 1.50000 | 1.50000 |
| 최종잔량 | 0.35000 | 0.81325 |
| SCI | 545,392.72 | 839,763.41 |
| 급유횟수 | 1.00 | 4.90 |


연료량은 정규화 단위입니다. DQN의 추가 구매량은 추가 최종잔량과 일치하며 SCI는 53.97% 높았습니다.
기본조건 Safe Stock의 기존 안전선 위반 판정에는 부동소수점 경계 효과가 확인됐습니다.
허용오차를 적용한 후처리 재분류와 환경 수정·재평가는 서로 다릅니다.
[진단 결과](docs/technical/reward_diagnostics_results_4seed.md) ·
[결과표](results/diagnostics/review_4seed/policy_accounting_comparison.csv) ·
[원본 출처·해시](results/diagnostics/review_4seed/provenance.json)

결과를 읽을 때 다음을 구분합니다.

- **목적지 도착과 안전여유 확보:** 도착률만으로 항해 전 과정의 안전잔량 확보를 판단하지 않습니다.
- **급유 행동과 기항:** 표의 급유횟수는 환경 내 행동 집계이며 실제 기항 횟수가 아닙니다.
- **SCI와 실화폐 비용:** Synthetic Cost Index는 합성환경 내부 지표로 실제 USD/KRW 비용이나 비용절감 실적이 아닙니다.
- **단일 모델과 4-seed 확장:** 서로 다른 평가 묶음이며 수치를 섞어 인용하지 않습니다.

추가 실험은 [4-seed 결과](docs/technical/multiseed_results_4seed.md),
[V1.5 소비량·horizon 민감도](docs/technical/v1_5_results_4seed.md),
[규칙 정책 강건성](docs/technical/rulebased_robustness.md)에 분리해 보존합니다.

## 자료 위치와 최신본

| 자료 | 기준 위치 | 사용 안내 |
|---|---|---|
| 코드·실행 방법 | 이 저장소와 [웹 README](web/README.md) | 현재 구현은 main, 재현 시에는 사용한 커밋을 함께 기록 |
| 공개 실험 결과 | [results](results/), [평가 manifest](results/evaluation_manifest.json) | 조건·체크포인트·원본 해시와 함께 확인 |
| 공개 체크포인트 | [GitHub Release](https://github.com/heechan9/bunkering-ai/releases/tag/official-eval-2026-09-01) | 공식 단일 모델. 4-seed 체크포인트 전체 보관을 뜻하지 않음 |
| 원본 데이터·논문·인수인계 | [병커시유 Drive](https://drive.google.com/drive/folders/1g5uRRYEoS69lhMiuRyHNi_u1lwkd33Bx) | 비공개 보관함. 허가된 계정만 열 수 있음 |
| 자료별 위치·최신본 목록 | [Drive 자료 목록](https://drive.google.com/file/d/1H42yNhpf0Ho0kJyZsCt7b7sdUn3UMzfb/view) | 파일 링크·최종본 식별·중복 확인·미확보 항목 |
| 논문 공개 안내 | [제출 상태](docs/submission/submission_status.md) | 최종 Word 식별 기록. 최종본 전문은 공개하지 않음 |

Drive는 `01_원본데이터`, `02_실험결과`, `03_논문제출본`,
`04_논문수정본`, `05_인수인계`로 구분했습니다.
최종 논문은 `03_논문제출본`의 버전 번호 없는 Word이며,
v12.0·v12.5·멘토 검토본은 수정 이력입니다.
업로드 날짜만으로 최신본을 판단하지 않습니다.

기존 자료는 삭제하지 않았고 동일 파일은 해시를 대조해 중복 업로드를 줄였습니다.
코드와 공개 결과는 GitHub에 유지하고 Drive 목록에서 연결합니다.
원본 AB-LOG와 실명·이메일이 포함된 최종 논문은 공개 저장소에 추가하지 않습니다.
과거 Git 기록에는 개인정보가 남아 있을 수 있습니다.

## 현장 참고자료

- **울산항만공사 벙커링정박지 신청현황:** 6,028건의 업무변수·분포를 검토했습니다.
  공공데이터를 DQN 학습 입력이나 공식 성능평가 데이터로 사용하지 않았으며,
  실시간 API 연동도 구현하지 않았습니다.
  [출처·해시](docs/data/upa_bunkering_anchorage.md) ·
  [검토 기록](docs/data/upa_review_20260919.md) · [분석 결과](results/public_data/)
- **한바다호 AB-LOG:** 2026년 5월 기록의 요약표 M/T·일별표 kL를 구분하고
  날짜 범위 3개 × 가정 밀도 5개의 산술 민감도를 계산했습니다.
  ROB 차감값의 일치는 독립 소비량 계측 검증이 아니며 밀도·기준 조건·시간 정합성은 미확인입니다.
  [검토 기능](docs/technical/hanbada_ab_log_design_20260922.md) ·
  [집계 비교·15개 가정 시나리오](docs/technical/hanbada_comparison_experiment.md)

## 검증 기록과 남은 범위

| 기록 | 확인 범위 |
|---|---|
| [PR #66](https://github.com/heechan9/bunkering-ai/pull/66) | 2026-09-27 main `3b5f95b` 기준 245개 테스트 기록 |
| [최종 웹 검사](docs/audits/final_web_check_20261002.md) | 관련 Python 25개, 구매 비교·CSV·한영 검사와 소스 동기화 기록 |
| [근거 감사](docs/technical/paper_evidence_audit.md) | 문서·코드·공식 산출물의 일관성 검사 |
| [보안 검토](docs/technical/security_review.md) | 당시 오프라인 정적 검토 범위와 미검증 항목 |

테스트 수는 해당 시점의 실행 기록이며 최신 main 전체 재검증 배지가 아닙니다.
최신 배포본의 실제 브라우저 클릭·모바일·WebGL·다운로드 실사용 검증은 별도로 남아 있습니다.
실제 운항 비용절감, 항만별 가격·공급·대기 제약 및 외부 성능 검증도 완료되지 않았습니다.
[모델 경계와 연구 로드맵](docs/technical/model_boundary_and_research_roadmap.md)

## 저장소와 문서 안내

| 경로·문서 | 내용 |
|---|---|
| `agents/`, `envs/`, `configs/` | 에이전트·환경·학습 설정 |
| `evaluation/`, `scripts/`, `tests/` | 공통 평가·실행 CLI·검사 |
| `web/ocean-lab/` | Ocean Lab 웹 소스 |
| `data/public/`, `results/` | 공개 데이터와 실험 산출물 |
| [상태·행동·보상 명세](docs/technical/state_action_reward_spec.md) | 환경 계약 |
| [공통 평가계약](docs/technical/evaluation_contract.md) | 정책 간 동일조건 비교 |
| [다중 학습 seed 평가](docs/technical/multiseed_evaluation.md) | 독립 체크포인트·페어드 집계 |
| [항차 CSV 검토](docs/technical/voyage_intake.md) | 입력 필드·연료수지·변경 감지 |
| [운항 검증 로드맵](docs/technical/causal_operational_validation.md) | 실선 효과 검증에 필요한 조건 |
| [팀 검토 절차](docs/technical/ax_evidence_communication.md) | 결과 설명과 근거 확인 |
| [해양 분야 검토](docs/technical/maritime_domain_review_20260920.md) | 팀 검토 의견과 채택 범위 |
| [기여 정책](CONTRIBUTIONS.md) · [직무 연계](docs/ROLE_ALIGNMENT.md) | 사람·AI 협업 역할과 구현 근거 |

과거 논문·검토·배포 이력은 [진행 상태 문서](docs/PROJECT_STATUS.md)와 각 상세 문서에 보존합니다.
