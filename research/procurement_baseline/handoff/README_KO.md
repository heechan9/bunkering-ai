# 합성 정적 구매정책 비교 묶음
REPORT_KO.md를 먼저 읽으세요. 120개 개발 사례의 동일정보 비교이며 실제 AI 절감이나 holdout 평가가 아닙니다.

## 실행
Python 3.12, NumPy/SciPy 버전은 environment.json 참조.

1. python benchmark.py
2. python -m unittest test_baselines -v
3. python run_legacy_tests.py
4. python diagnose_solver.py
5. python generate_report.py

benchmark.py는 사전에 저장된 seed와 생성규칙을 적용하고 모든 입력을 저장한 뒤 실행합니다. 재실행 시 cases/results/summary/results.csv/environment/run 출력은 현재 파일을 덮어씁니다. 수정 전 original_solver_* 및 first_run_results.json은 덮어쓰지 않습니다. 원본 구현은 vendor, 수정 옵션 구현은 patched에 있습니다. 수정 전 결과의 재현은 vendor 모듈을 참조해 동일 cases.json의 Case를 solve하면 됩니다.

SHA256SUMS.txt는 생성 당시 파일 해시입니다. 재실행 후 환경정보나 로그가 바뀌면 해시도 바뀔 수 있습니다. PREREGISTERED_SHA256.txt는 결과 계산 이전의 spec/정책 정의 해시입니다. 원본 공급코드와 복사본 동일성은 SOURCE_COPY_SHA256.txt에 있습니다.

외부 업로드·PR·배포는 수행하지 않았고 기존 프로젝트는 수정하지 않았습니다.
