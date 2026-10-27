# Contribution and Attribution Record

이 문서는 Git commit metadata만으로 표현하기 어려운 병커시유 프로젝트의
기획, 구현, AI 지원, 검토, 재현 검증, 병합 역할을 과장 없이 기록한다.
기존 Git history는 수정하지 않으며, 확인할 수 없는 기여는 추정하지 않는다.

## Attribution policy

- Codex가 독립적으로 구현·수정하고 직접 커밋한 변경은
  `Codex <codex@openai.com>`를 Author와 Committer로 사용한다.
- 최희찬(`heechan9`)이 직접 작성하거나 실질적으로 수정한 변경은
  `heechan9`의 Git identity로 기록한다.
- 이현수가 직접 구현한 변경은 이현수 본인의 Git identity로 기록한다.
- AI 지원과 사람의 기획·검토·통합이 함께 이루어진 경우 PR에
  Requirements/Planning, Implementation, AI-assisted editing, Review,
  Merge/Integration을 각각 기록한다.
- PR 병합자는 원본 코드 작성자와 동일한 것으로 간주하지 않는다.
- 기존 `main` commit의 Author/Committer를 바꾸기 위한 history rewrite나
  force push를 하지 않는다.
- 커밋 전 변경 파일, 테스트 결과, `git config user.name`,
  `git config user.email`, 예정 Author/Committer를 최희찬에게 제시하고
  승인을 받은 뒤 커밋한다.

## Role definitions

- **Requirements/Planning**: 문제 정의, 범위, 우선순위, 수용 기준 결정
- **Implementation**: 실제 코드·테스트·문서 변경 작성
- **AI-assisted editing**: AI가 코드·테스트·문서의 작성 또는 수정에 관여
- **Review**: 코드 검토, 독립 재현, 결과 검증, 승인 판단
- **Merge/Integration**: 병합 실행과 `main` 통합 책임

## Project-level roles

### 최희찬 (`heechan9`)

- 프로젝트 PM 및 저장소 운영
- 문제 정의, 요구사항, 우선순위와 실험 방향 결정
- State·Action·Reward와 KPI 방향 검토
- 팀 작업 배정, 결과 검토, 멘토링·발표·보고서 통합
- GitHub review 기능 밖의 프로젝트 채팅에서 수정 요구, 재검토 및
  PR별 최종 승인 판단 수행

### 이현수 (`HyeonSuuuuu`)

- Windows 환경 독립 재현 및 코드 검토
- PR #4, #5, #6 병합과 `main` 통합
- PR #5 Safe Stock 결과 재현, 결정론 및 CSV 검증
- PR #6 termination/truncation 의미론 검토와 dead-code 위험 발견

### Codex

- 대화 기반 요구사항을 코드·테스트·문서 변경으로 구현하거나 편집 지원
- Linux sandbox 검증, 회귀 테스트와 기술 문서 작성 지원
- Git 기록상 명시된 범위와 별도 작업 기록으로 확인되는 경우에만
  구체적인 구현 기여를 표기

## Historical pull-request ledger

| PR | Requirements/Planning | Implementation | AI-assisted editing | Review | Merge/Integration | Evidence limits |
|---|---|---|---|---|---|---|
| #1 Terminal reasons | 최희찬 | Git 기록만으로 세부 작성자 확정 불가 | 프로젝트 작업 기록상 AI 지원 | 최희찬 채팅 기반 검토·승인; 별도 GitHub review 없음 | 최희찬 | Commit metadata는 `heechan9`만 표시 |
| #2 Cost/reward accounting | 최희찬 | Git 기록만으로 세부 작성자 확정 불가 | 프로젝트 작업 기록상 AI 지원 | 최희찬 채팅 기반 검토·승인; 별도 GitHub review 없음 | 최희찬 | Commit metadata는 `heechan9`만 표시 |
| #4 Baseline metrics | 최희찬 | 최희찬 (Issue #3 본문에 직접 구현 범위로 사전 명시) | 프로젝트 작업 기록상 AI 지원 | 최희찬 채팅 기반 검토·승인; 이현수 reviewer 지정, 공개 review 제출 기록 없음 | 이현수 | Commit metadata는 `heechan9`만 표시하나, Issue #3이 구현 주체를 사전 기록 |
| #5 Safe Stock | 최희찬 | Git 기록만으로 세부 작성자 확정 불가 | 프로젝트 작업 기록상 AI 지원 | 최희찬 채팅 기반 수정 요구·최종 승인; 이현수 Windows 독립 재현 및 PR 코멘트로 승인 의견 게시(GitHub review 상태 아님) | 이현수 | Git만으로 코드 입력 주체 확정 불가 |
| #6 DQN truncation bootstrap | 최희찬 | Codex-assisted implementation (commit은 `heechan9` 명의) | Codex Linux sandbox 작업이 PR에 명시됨 | 최희찬 채팅 기반 검토·승인; 이현수 Windows 독립 재현 및 PR 코멘트로 승인 의견 게시(GitHub review 상태 아님) | 이현수 | Codex 관여 표기는 프로젝트 작업 기록과 PR의 validation 환경 서술에 근거한다. Commit metadata 자체는 이를 독립적으로 증명하지 않으며 Author는 `heechan9`다. |

PR #3은 존재하지 않으며, 해당 번호는 Issue #3(open)이 사용하고 있다.
Issue #3은 PR #4(#3A)의 요구사항 명세이며 구현·리뷰 담당을 사전에 명시한다.

## Known limitations

- 기존 commit metadata만으로 코드 입력 주체, AI별 편집 범위,
  사람의 직접 수정 비율을 복원할 수 없다.
- 과거 역할은 GitHub PR·commit, Issue 본문, 공개 검증 댓글, 프로젝트 작업
  기록으로 확인되는 범위에서만 기술한다.
- 새로운 증거가 확인되면 history를 재작성하지 않고 이 문서를 일반
  commit으로 갱신한다.

## 2026-10-27 팀원 기여·진행 보고 접수

기준 main은 `34e1e82ce10309ba737572fdae24625e4bc722a7`이다. 아래는 이날 접수한
화면 자료와 진행 보고의 범위이며, 파일명의 날짜를 실제 실행 일시로 확정하지 않는다.
[접수 범위와 원본 목록](https://drive.google.com/file/d/1ehKgA3jcVBSbID9c9xduVaySg-Q_4Pb0/view)을
기존 기여 기록에 연결한다.

- **승섭 — 제한된 CLI 실행 확인:** [원본 화면 4장과 요청 안내 PDF](https://drive.google.com/drive/folders/1wdjCHRuk9B0itJA3-grRY_h7VOAGmqHO).
  안내 PDF는 수행 요청 범위이며 완료 증거가 아니다. 별도 화면들에서
  `python research/native_v4_integration/cli.py --help`의 도움말,
  `validate-config`의 `status: valid`와 pending 6개, `git rev-parse HEAD`의
  `40100e398efb15f44cf9a032bf000cf519a6fa87`, `Python 3.11.9` 출력을 확인했다.
  이 SHA는 [PR #136](https://github.com/heechan9/bunkering-ai/pull/136)의 기준이다.
  pending은 `consumption_known_at_decision`, `reserve_phase`, `seed_range_inclusive`,
  `seed_status`, `statistics_ddof`, `terminal_valuation`이다. 설정 valid는
  C01–C06 채택이나 전체 검증 PASS를 뜻하지 않는다. OS·명령별 종료 코드·전체 원시 로그,
  전체 테스트·웹 검수 완료와 별도 본인 검토 메모는 미확보다.
- **기예 — 환경 준비·진행 현황 보고:** [2026-10-27 접수한 상태표 화면](https://drive.google.com/drive/folders/1DxWbCSLf-ELo_A05w5E_0Z1juML0AE6-).
  저장소 다운로드·Python 가상환경·패키지 설치·`pip check`는 PASS,
  환경 정보 로그 저장은 완료라고 보고했다. Python 자동 테스트는 진행 중이며
  pnpm 웹 설치는 미진행이다. 이는 상태표 보고이며 원본 환경 로그·최종 테스트 수·종료 코드,
  실행 SHA·정확한 Python 버전·OS는 미확보다. 승섭의 SHA나 Python 버전을 대입하지 않는다.
- **민재 — 정식 팀원, 도메인 검토·제안 제출:** 1차 도메인 검토와 2차 19개 제안
  제출은 완료했으며, 계약 채택은 pending이다. 제출과 채택을 구분한다.

접수 시 [PR #146](https://github.com/heechan9/bunkering-ai/pull/146)과
[문서 PR #147](https://github.com/heechan9/bunkering-ai/pull/147)은 별도 Draft/open/미병합이다.
위 개인별 화면·보고를 #146 검증 완료, 모델 성능 검증, main 통합 또는 배포의 근거로
확대하지 않는다. 전체 정책 공통 strict-safe 0/1000·비용 null과
DDQN–Price Reactive 쌍의 33/1000은 서로 다른 비교 집합이다.
이번 기록은 모델·계약·실험 수치를 변경하지 않으며 Claude 검토 완료를 의미하지 않는다.
