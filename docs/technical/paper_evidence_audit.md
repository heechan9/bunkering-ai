# 논문 근거 감사 계약 (Paper Evidence Audit Specification)

논문/문헌 명세와 실제 시스템 상태 간의 부합 여부를 **독립적으로 검증**하기 위한 코드 계약 및 감사 도구이다.
이 도구는 기존 RL 모델 동작, 보상 함수 로직, 공식 평가 결과, 또는 이미 검증된 수치를 임의로 수정하지 않는다.

## 1. 개요 및 목적

- **독립성**: 모델 학습 및 평가 계약 파이프라인과 독립된 읽기 전용 검증 도구 (`evaluation/paper_audit.py`, `scripts/audit_paper_evidence.py`).
- **주요 검증 항목**:
  1. **MVP State Space**: 6개 핵심 변수 (`fuel_price`, `fuel_price_ma30`, `fx_rate`, `fuel_remaining`, `route_remaining`, `sfc`).
  2. **Action Space**: `action=0` (대기) 및 `action=1..n_ports` (고정 요청량 0.9 급유).
  3. **Synthetic Cost Index**: 탱크 용량 확정 전 비용 지수 단위 명시.
  4. **Strict Termination**: `arrived`, `fuel_depleted`, `timeout` 3가지 엄격한 에피소드 종료 사유.
  5. **Safe Stock baseline KPI 상태**: `provisional` 명시 (공통 evaluation seed 확대 검증 대기).
  6. **공공데이터 분리 원칙**: 학습 입력이 아닌 도메인 참고/시나리오 설계 참고용 분리 검증.

## 2. CLI 실행 방법

```bash
PYTHONPATH=. python scripts/audit_paper_evidence.py --output-dir results/paper_audit
```

## 3. 감사 산출물

- `results/paper_audit/paper_evidence_summary.csv`: CSV 요약 리포트
- `results/paper_audit/paper_evidence_report.json`: JSON 상세 감사 결과 및 구조화 데이터
