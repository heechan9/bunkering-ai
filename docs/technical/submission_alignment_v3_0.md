# 논문 v3.0과 진단 결과의 일치 확인

기존 공식 수치와 환경·학습 정책은 유지하고, 진단 기록의 의미를 코드 설명·기술 문서·논문에 일치시켰다. 제출 일정은 사용자 확인에 따라 **2026년 9월 30일**을 기준으로 한다. 이 문서는 제출 승인이나 현장 성능 검증을 뜻하지 않는다.

## 변경과 근거

| 항목 | 반영 내용 | 근거 |
|---|---|---|
| 보상 필드 혼동 | Safe Stock의 가격우위 보상은 +0.007202244639, 안전 보상은 −0.5 | 원본 전이에서 각각 재계산 |
| 안전선 | 원래 엄격한 비교와 허용오차 후처리를 분리 | 원래 판정 Safe Stock 100/100, 후처리 0/100; DQN 0/400 |
| 구매·잔량 | DQN 추가 구매량 0.46325와 추가 최종잔량이 일치 | 같은 기본조건의 소비량은 모두 1.5 |
| SCI | DQN은 Safe Stock 대비 +53.9741%; 실제 화폐 비용이나 재고가치 차감 후 비용이 아님 | SCI와 최종잔량을 함께 보고 |
| 집계 단위 | 1,600개 원본 기록, 중복 제거 후 700개 정책/체크포인트/case 조합 | 동일 100개 시장 case 공유; 규칙 반복을 학습 표본으로 세지 않음 |
| 필드 이름 | `step_sci_mean`은 기존 통합표에서 항차별 누적 SCI의 평균 | SCI/step으로 잘못 읽지 않도록 요약 함수에 설명 추가 |
| 연구 범위 | 기본조건의 기록 감사·재현과 스트레스 실험의 범위를 분리 | 스트레스 안전선 재분류·보상 변경 재학습은 수행하지 않음 |

논문은 [v3.0 원문](../submission/ack_paper_v3_0.md)에 대응한다. 인용 첫 등장 순서에 맞춰 저장소를 [3], 연료소비 문헌을 [4]로 정리했다. 사사문구는 사용자가 제공한 스마트해운물류 트랙 안내문과 대조했다. 표 3과 정의가 한 페이지에 유지되도록 조판했다.

## 검증 단계의 구분

1. 사용자 Windows 실행: 기존 진단 버전 **215 passed in 37.78s**.
2. 보존된 Linux 체크포인트 재실행: 소스 `8467fd106d33b4afa7abca6a632b0062e7ca4b58`, 기준 main `97233c1c442a687aaed4a34e2cadca0d98aa2fb9`. 네 기본조건 전이 CSV가 각 Windows 원본과 바이트 단위로 일치했다. 정책·타깃·optimizer 상태 불변, 학습 호출 0. 당시 회귀는 **215 passed in 10.47s**였다. 이는 제공된 재실행 증거 묶음의 기록이다.
3. 이번 정리 작업: 보존된 묶음의 SHA-256 24개와 **40,120개 step**을 독립 계산했다. 전체 회귀는 **225 passed in 10.04s**(기존 215개 + 신규 기록 감사 테스트 10개). 이번 추가 검사는 기록 재계산이며 모델을 다시 실행한 결과로 표현하지 않는다.
4. 기존 논문 근거 감사는 **8/8 통과**했다. 해당 도구의 기존 8개 계약 항목 검증이며 논문 v3.0의 모든 문장에 대한 자동 인증은 아니다.

새 [기록 감사 도구](../../scripts/audit_diagnostic_snapshot.py)는 기본조건만 허용하고, 실제 급유량·소비량·상한손실·SCI·보상 성분을 원래 수식으로 확인한다. 원래 안전 판정이나 평가 파일을 수정하지 않는다. 기존 출력 파일은 거부한다. 해시는 묶음 내 일관성을 확인하며 제3자 진위 인증을 뜻하지 않는다.

```bash
python -m pytest -q
python -m scripts.audit_diagnostic_snapshot --bundle /path/to/extracted-replay-bundle --output /path/to/new-snapshot-audit.json
```

증거 묶음 이름: `bunkering_checkpoint_replay_verification_20260912.zip`. 검사하려면 그 묶음의 `SHA256SUMS.json`과 `replayed/`가 함께 필요하다. 저장소 요약표만으로 전체 전이를 검증했다고 표현하지 않는다.

- [이번 기록 감사 JSON](../../results/diagnostics/finalization_v3_0/snapshot_audit.json)
- [이번 회귀 로그](../../results/diagnostics/finalization_v3_0/regression.log)
- [기존 8개 근거 감사](../../results/diagnostics/finalization_v3_0/paper_evidence_report.json)
- [출처·보존 확인 및 문서 검수](../../results/diagnostics/finalization_v3_0/alignment_manifest.json)

## 보존과 남은 절차

`envs/`, `agents/`, `evaluation/` 및 기존 추적 결과 파일은 이번 변경에서 수정하지 않았다. `diagnose_reward.py`와 `summarize_reward_diagnostics.py`의 기존 실행 로직도 유지하며 설명만 추가했다. 신규 검증 결과는 별도 디렉터리에 둔다.

PR #44는 이번 확인 시 Draft/open이며 GitHub의 `mergeable=true`, `mergeable_state=clean`이다. 원격 HEAD는 위 재실행 소스와 동일하고 기준 main도 그대로였다. 이 상태는 아래 미커밋 변경을 포함한 원격 CI 결과가 아니다. 재실행·회귀 미완료였던 과거 기록과 지금의 커밋·통합 대기 상태를 구분한다. 병합 전 기준 브랜치가 바뀌면 해당 변경과 충돌·회귀 영향을 확인한다. `CONTRIBUTIONS.md`에 따라 변경 파일·검증·Author/Committer를 제시한 뒤 최희찬의 승인으로 커밋한다. 이 파일 작성만으로 GitHub 반영·병합·제출이 완료되지는 않는다.

논문 DOCX는 A4 3쪽을 렌더링하고 전 페이지를 확인했다. 공동저자 순서·소속·이메일 자리표시자는 최종 확정이 필요하다. 검수 환경에서는 한국어 대체 글꼴을 사용했으므로 제출 PC의 Word에서도 글꼴과 최종 페이지 수를 확인한다. 실제 항차 데이터 확보, 스트레스 안전선 재분류, 수정 보상하의 재학습은 후속 연구로 남기며 현재 논문에서 완료했다고 쓰지 않는다.
