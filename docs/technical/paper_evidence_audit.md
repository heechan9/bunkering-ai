# 논문 근거 감사 계약 (Paper Evidence Audit Specification)

논문/문헌 명세와 실제 시스템 상태 간의 부합 여부를 **독립적으로 검증**하기 위한 코드 계약 및 감사 도구이다.
이 도구는 기존 RL 모델 동작, 보상 함수 로직, 공식 평가 결과, 또는 이미 검증된 수치를 임의로 수정하지 않는다.

## 1. 개요 및 목적

- **독립성**: 모델 학습 및 평가 계약 파이프라인과 독립된 읽기 전용 검증 도구 (`evaluation/paper_audit.py`, `scripts/audit_paper_evidence.py`).
- **엄격한 Exit Boundary**: `failed_claims > 0` 뿐만 아니라 필수 근거 수집이 미비한 `missing_evidence_claims > 0` 일 때도 CLI는 **비 zero exit code (Exit Code 1)**를 반환한다.
- **주요 검증 항목**:
  1. **MVP State Space (`CLAIM-001`)**: 6개 핵심 변수 (`fuel_price`, `fuel_price_ma30`, `fx_rate`, `fuel_remaining`, `route_remaining`, `sfc`)를 `BunkeringEnv` 동적 관측 공간과 비교.
  2. **Action Space (`CLAIM-002`)**: `action=0` (대기) 및 `action=1..n_ports` (고정 요청량 0.9 급유)를 `BunkeringEnv` 동적 행동 공간과 비교.
  3. **UPA 공공데이터 레코드 수 (`CLAIM-003`)**: `results/public_data/upa_summary_metrics.csv`의 레코드 수(6,028건)와 제출 문서 명세 비교.
  4. **Strict Termination (`CLAIM-004`)**: `arrived`, `fuel_depleted`, `timeout` 3가지 종료 원인을 `evaluation/contract.py`와 비교.
  5. **Safe Stock baseline KPI 상태 (`CLAIM-005`)**: `docs/technical/state_action_reward_spec.md §4.1`의 `provisional` 상태 검증 (불일치 시 실패).
  6. **DQN 비교 경계 검증 (`CLAIM-006`)**: 공식 동일조건 비교 전 근거 없는 비교 우위 선언 금지 및 경계 준수 검증.
  7. **공식 Rule-based 평가 결과 (`CLAIM-007`)**: `results/evaluation_results.csv`와 canonical `results/evaluation_manifest.json`을 동시 검증한다. manifest 누락 시 `missing_evidence`로 처리된다. CSV 내 `success` 및 `fuel_depletion` 필드는 엄격히 대소문자 구분 없이 `"true"` 또는 `"false"`만 허용하며 (`"invalid"`, `"0"`, `"1"`, `"yes"` 등은 실패 처리), `EpisodeResult` 및 `EvaluationCase` 계약에 맞춰 각 행의 자료형, 유한값, 비음수, 종료원인, exact set equality (누락·추가·중복 케이스 검증)를 엄격 검사한다.
  8. **공공데이터 분리 원칙 (`CLAIM-008`)**: 공공데이터가 학습 입력이 아닌 도메인 참고용으로만 격리되어 있음을 검증.

## 2. CLI 실행 방법

```bash
PYTHONPATH=. python scripts/audit_paper_evidence.py --output-dir results/paper_audit
```

## 3. 감사 산출물 (출력 전용)

- `results/paper_audit/paper_evidence_summary.csv`: CSV 요약 리포트
- `results/paper_audit/paper_evidence_report.json`: JSON 상세 감사 결과 및 구조화 데이터

## 4. 변조 검증 및 테스트 명령어

`pytest` 실행 명령어 자체의 exit code는 테스트 성공 시 0이며, 테스트 어서션 내부에서 호출된 감사 CLI (`scripts/audit_paper_evidence.py`)의 반환값(1)을 검증한다.

```bash
# 전체 단위 및 변조 통합 테스트 실행 (pytest Exit Code: 0)
python3 -m pytest tests/test_paper_audit.py -v
```
