# 원본 MILP 오류 재현 및 격리 수정
- 사전 고정 120개 사례의 monetary_fees_010에서 원본 1차 MILP가 INFEASIBLE을 반환했다. lexicographic 2차 호출 전이다. 세 규칙이 만든 feasible 원장과 독립 정차조합 열거 LP가 이를 반증했다.
- 이 환경에서 동일 모델의 두 MILP 호출에 presolve=False 옵션만 추가하면 OPTIMAL 13,000 USD, q=[1,10,15]t를 반환한다. 원인 범위는 HiGHS presolve 경로와 연관된 잘못된 infeasible 판정으로 좁혀졌다. 내부 수치 원인의 완전한 분석이나 다른 버전의 일반적인 보장은 주장하지 않는다.
- 기존 프로젝트와 vendor 원본은 불변. patched/procurement.py의 옵션 2곳만 수정. 목적함수, 제약, 허용오차, 정책은 변경하지 않았다. 모든 120개를 수정본으로 재실행하고 독립 열거검산했다.
- solver_diagnostic.json은 두 버전의 MILP 호출 순서/옵션/상태/해를 담는다. original_solver_results.json/summary.json/csv는 수정 전 결과 보존. first_run_results.json은 독립검산 추가 전 최초 원결과다.
- 최초 실행의 요약 JSON 저장 시 numpy int64 직렬화 오류를 Python bool 집계로 고쳤다. 입력/정책/솔버 수학에는 변경 없다.
- 최종 결과는 개발 중 반례를 보고 고친 버전이다. 미사용 holdout 성능이라고 해석할 수 없다.

## 회귀검증 및 원본 출처
원본 출처: /workspace/shared/procurement_prototype_20261015/procurement.py. SOURCE_COPY_SHA256.txt에서 기존 원본과 vendor 복사본의 SHA-256 동일성을 확인한다. 수정본의 해시는 SHA256SUMS.txt에 있다. 원본 27개 회귀시험을 patched 모듈로 명시 로드하여 재실행하고, 정책 8개와 새 solver 반례 1개를 추가해 총 36개 통과했다. 구체 로그는 test_output.txt에 있다.
