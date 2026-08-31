# 논문 근거 감사 계약 (Paper Evidence Audit Specification)

논문/문헌/제출 문서 명세와 저장소의 실제 시스템 상태 간 명시적 주장 부합 여부를 **독립적으로 검증**하기 위한 코드 계약 및 감사 가드레일 도구이다.
본 도구는 논문 PDF의 일반 자연어를 자동 의미 해석하는 범용 도구가 아니라, 저장소 내 `README.md`, 기술 설계 문서(`docs/technical/`), 코드 계약, `BunkeringEnv` 환경 및 canonical CSV/JSON 산출물 간 선언적 주장 부합 여부를 검증하는 제한적 가드레일(guardrail)이다.
이 도구는 기존 RL 모델 동작, 보상 함수 로직, 공식 평가 결과, 또는 이미 검증된 수치를 임의로 수정하지 않는다.

## 1. 개요 및 목적

- **독립성**: 모델 학습 및 평가 계약 파이프라인과 독립된 읽기 전용 검증 도구 (`evaluation/paper_audit.py`, `scripts/audit_paper_evidence.py`).
- **엄격한 Exit Boundary 및 제출 차단 (Submission Blocker)**:
  `failed_claims > 0` 뿐만 아니라 필수 근거 수집이 미비한 `missing_evidence_claims > 0` 일 때도 CLI는 **비 zero exit code (Exit Code 1)**를 반환한다.
  현재 공식 `results/evaluation_results.csv` 및 `results/evaluation_manifest.json`이 존재하지 않는 clean checkout 상태에서 `CLAIM-007`은 `missing_evidence`를 기록하며 CLI Exit Code 1을 발생시킨다. 이는 평가 산출물 미비 시 의도적으로 제출을 차단하기 위함이며, 공식 평가 결과가 준비되기 전 일반 CI 파이프라인의 무조건 성공 빌드 조건으로 직접 연결하지 않는다.
- **주요 검증 항목**:
  1. **MVP State Space (`CLAIM-001`)**: 6개 핵심 변수 (`fuel_price`, `fuel_price_ma30`, `fx_rate`, `fuel_remaining`, `route_remaining`, `sfc`)를 `BunkeringEnv` 동적 관측 공간과 비교.
  2. **Action Space (`CLAIM-002`)**: `action=0` (대기) 및 `action=1..n_ports` (고정 요청량 0.9 급유)를 `BunkeringEnv` 동적 행동 공간과 비교.
  3. **UPA 공공데이터 레코드 수 (`CLAIM-003`)**: `results/public_data/upa_summary_metrics.csv`의 레코드 수(6,028건)와 제출 문서 명세 비교.
  4. **Strict Termination (`CLAIM-004`)**: `arrived`, `fuel_depleted`, `timeout` 3가지 종료 원인을 `evaluation/contract.py`와 비교.
  5. **Safe Stock baseline KPI 상태 (`CLAIM-005`)**: `docs/technical/state_action_reward_spec.md §4.1`의 `provisional` 상태 검증 (불일치 시 실패).
  6. **DQN 비교 경계 검증 (`CLAIM-006`)**: 공식 동일조건 비교 전 정규식 기반 텍스트 가드레일로 근거 없는 비교 우위 선언 금지 및 경계 준수 검증 (완전한 자연어 의미 검증이 아닌 키워드 문구 탐지 가드레일임).
  7. **공식 Rule-based 평가 결과 (`CLAIM-007`)**: `results/evaluation_results.csv`와 canonical `results/evaluation_manifest.json`을 동시 검증한다. manifest 누락 시 `missing_evidence`로 처리된다. CSV 내 `success` 및 `fuel_depletion` 필드는 엄격히 대소문자 구분 없이 `"true"` 또는 `"false"`만 허용하며 (`"invalid"`, `"0"`, `"1"`, `"yes"` 등은 실패 처리), `EpisodeResult` 및 `EvaluationCase` 계약에 맞춰 각 행의 자료형, 유한값, 비음수, 종료원인, exact set equality (누락·추가·중복 케이스 검증)를 엄격 검사한다.
  8. **공공데이터 분리 원칙 (`CLAIM-008`)**: 공공데이터가 학습 입력이 아닌 도메인 참고용으로만 격리되어 있음을 검증.

## 2. CLI 실행 방법 및 산출물 메타데이터 (Provenance)

```bash
PYTHONPATH=. python scripts/audit_paper_evidence.py --output-dir results/paper_audit
```

감사 보고서 JSON (`results/paper_audit/paper_evidence_report.json`)의 `summary`에는 감사 시점의 provenance 추적을 위해 아래 필드가 포함된다:
- `source_commit_sha`: 감사 수행 시점의 git commit SHA (`git rev-parse HEAD` 동적 추출, uncommitted 상태에서는 베이스 HEAD SHA, 커밋 후 실행 시 feature branch HEAD SHA 기록; 확인 불가 시 `"unavailable"`)
- `generated_at_utc`: ISO-8601 형식의 UTC 생성 타임스탬프

## 3. 감사 산출물 (출력 전용)

- `results/paper_audit/paper_evidence_summary.csv`: CSV 요약 리포트
- `results/paper_audit/paper_evidence_report.json`: JSON 상세 감사 결과 및 구조화 데이터

## 4. 변조 검증 및 테스트 명령어

`pytest` 프로세스 실행 명령어 자체의 exit code는 모든 테스트 어서션 통과 시 0이며, 테스트 어서션 내부에서 호출된 감사 CLI (`scripts/audit_paper_evidence.py`)의 반환값(Exit Code 1)을 검증한다.

```bash
# 전체 단위 및 변조 통합 테스트 실행 (pytest Exit Code: 0)
python3 -m pytest tests/test_paper_audit.py -v
```
