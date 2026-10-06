# 2026-10-07 Windows 재검증 및 현황 정리

검사 기준: main `7df50a5f0f34cc2dc33928ea2583645c9762f75d`. 공식 모델·환경·보상·기존 결과는 변경하지 않았다.

## 직접 실행한 확인

- Windows, Python 3.12, pytest 9.1.1. 사용자 기본 인코딩은 CP949였다. 필요한 추가 테스트 의존성은 작업용 디렉터리에 설치했다. pytest 외부 플러그인 자동 로드는 비활성화했다.
- `python -m scripts.audit_paper_evidence --output-dir <별도 작업 폴더>`: 종료 0, 주장 8개 중 8개 통과. 정본 출력 디렉터리는 사용하지 않았다.
- `node scripts/check-voyage-csv.mjs`: 종료 0. 음수·0·양수·빈값, 수식 보호, CP949 및 기존 입력 검증 통과.
- 공개 Release `official-eval-2026-09-01/dqn_final.pt` 다운로드 SHA-256: `970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392`. 정본과 일치.
- `python scripts/evaluate.py --episodes 100 --seed 42 --checkpoint <다운로드 파일> --output-dir results/local_reproduction`: 종료 0. 규칙 3종·Double DQN 400행을 정본과 비교했다. 행 수·컬럼·범주 값 일치, reward와 Synthetic Cost Index 최대 절대 차이는 모두 0. 수치 비교 허용치는 atol=1e-10, rtol=1e-12이며 이번 결과는 정확히 일치했다. 새 학습은 하지 않았다.

## Windows 테스트 수정

`tests/test_source_catalog.py`가 UTF-8 JSON을 기본 인코딩으로 읽어 CP949 환경에서 실패했다. 수정 전 실행은 287 passed, 7 failed, 17 subtests passed였다. 두 `read_text` 및 임시 파일 `write_text`에 UTF-8을 명시했다. 출처 목록의 정본·운영 코드는 변경하지 않았다.

전체 재검사: `python -m pytest -q`, 종료 0, 288 passed（104.14s）, 23 subtests passed. 초기 환경의 누락 의존성 오류를 저장소 결함으로 해석하지 않는다. UTF-8 명시 후 남은 1건은 Git의 core.autocrlf=true가 근거 파일을 CRLF로 변환해서 해시가 달라진 문제였다. 작업용 체크아웃의 추적 텍스트를 Git 원본의 LF로 맞춘 뒤 전체 통과했다. 원문·정본 해시는 변경하지 않았다.

## Jules 재감사 기록과 구분

[Jules 작업 12656040711462439408](https://jules.google.com/session/12656040711462439408)의 한국어 보고서를 확인했다. Jules는 동일 SHA에서 Linux pytest 288 passed, 근거 8/8, 웹 회귀·타입·빌드 통과 및 확정 결함 0건을 보고했다. 이는 Jules 보고 내용이며 위 Windows 직접 실행과 별개다. 초기 모바일 넘침 2~7px는 선택 개선으로 보고했으며 실제 휴대폰·iOS는 미검증이다. 숫자 차이는 서로 다른 브라우저/시점의 관측이고 동일 측정으로 합치지 않는다.

## 남은 범위

실제 휴대폰·iOS Safari, 초기 모바일 넘침 개선, 외부 자료 회신 및 실선 비용절감 검증은 완료되지 않았다. README 상단 시점·Ocean Lab 상태 요약을 운영 확인 범위와 일치하도록 수정했다. 저장소 커밋은 기여 정책에 따른 사용자 승인 전에는 수행하지 않는다.

Requirements: 최희찬. Implementation / verification: Codex. 예정 Author/Committer: `Codex <codex@openai.com>`. 기존 저장소 설정은 `heechan9 <35565999+heechan9@users.noreply.github.com>`이며 승인 시 해당 커밋에만 Codex identity를 지정한다.
