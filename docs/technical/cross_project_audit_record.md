# 프로젝트 간 기능 검토 — 2026-10-01

기준: bunkering-ai 8b16b73, judicial-ai-safety-lab 25d15f9,
triguard-ai d0db55a, fabguard-ai 519654e, AdversarialAI_Security 451b8a1.
병커시유의 열린 PR은 조회 시점에 없었다.

## 채택

법률 AI `src/judicial_ai_safety_lab/evidence_package.py`의 파일별 SHA-256·크기 기록과
TriGuard `public-statistics/validation-trace.js`의 명시적 검증 상태를 참고해
기존 `scripts/audit_web_evidence.py`에 `--json`을 추가했다. 원문 코드를 복제하지 않고
병커시유의 기존 검사와 고정된 4개 입력 파일에 맞춰 구현했다.
성공·실패, 실행 시각, Python 버전, 입력 식별값, 실패 사유를 출력한다.
실패는 종료 코드 1이며 성공 결과로 표시하지 않는다.
GitHub Actions는 검사 결과를 30일 보관한다. 선행 검사가 실패해도 이 검사를 시도한다.

## 중복 및 보류

- 적대적 AI `scripts/audit_research_evidence.py`: 독립 근거 검사 진입점은 이미
  병커시유 `audit_web_evidence.py`에 있으므로 검사기를 중복 이식하지 않았다.
- FabGuard `web/smt/evidence-model.mjs`: 출처 연결 및 관측·추정값 구분은
  병커시유의 출처·AB-LOG 검토 기능과 대조 후 별도 UI 범위를 정해야 하므로 보류했다.
- 타 프로젝트의 분류기·위험 점수는 급유정책 성능 개선 근거가 없어 이식하지 않았다.

## 사용 및 검증

```sh
python scripts/audit_web_evidence.py --json > web-evidence-audit.json
python -m unittest discover -s tests -p test_web_evidence.py -v
```

Python 3.12.14에서 8개 테스트 통과. 현재 입력의 요약값 70개,
정책·사례 조합 700개, 전이 19,030개를 검사했다.
해시 불일치·파일 누락 시 실패 기록 및 CLI 종료 코드도 확인했다.
파일 해시는 진위 증명이 아니며 새 모델 실행이나 실선 검증을 뜻하지 않는다.
기존 결과표·논문·모델·웹 화면은 수정하지 않았다.
