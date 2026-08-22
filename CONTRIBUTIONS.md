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
| #4 Baseline metrics | 최희찬 | Git 기록만으로 세부 작성자 확정 불가 | 프로젝트 작업 기록상 AI 지원 | 최희찬 채팅 기반 검토·승인; 이현수 reviewer 지정, 공개 review 제출 기록 없음 | 이현수 | 병합 기록은 구현 작성 증거가 아님 |
| #5 Safe Stock | 최희찬 | Git 기록만으로 세부 작성자 확정 불가 | 프로젝트 작업 기록상 AI 지원 | 최희찬 채팅 기반 수정 요구·최종 승인; 이현수 Windows 독립 재현 및 Approve | 이현수 | Git만으로 코드 입력 주체 확정 불가 |
| #6 DQN truncation bootstrap | 최희찬 | Codex-assisted implementation (commit은 `heechan9` 명의) | Codex Linux sandbox 작업이 PR에 명시됨 | 최희찬 채팅 기반 검토·승인; 이현수 Windows 독립 재현 및 Approve | 이현수 | Codex 관여 표기는 프로젝트 작업 기록과 PR의 validation 환경 서술에 근거한다. Commit metadata 자체는 이를 독립적으로 증명하지 않으며 Author는 `heechan9`다. |

PR #3은 저장소에 존재하지 않는다. PR 번호가 비어 있다는 사실을 별도
기여나 삭제된 작업의 증거로 해석하지 않는다.

## Known limitations

- 기존 commit metadata만으로 코드 입력 주체, AI별 편집 범위,
  사람의 직접 수정 비율을 복원할 수 없다.
- 과거 역할은 GitHub PR·commit, 공개 검증 댓글, 프로젝트 작업 기록으로
  확인되는 범위에서만 기술한다.
- 새로운 증거가 확인되면 history를 재작성하지 않고 이 문서를 일반
  commit으로 갱신한다.
