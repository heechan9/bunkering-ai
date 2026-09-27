# 병커시유 최종 검증 결과 (논문 v7.5 기준, 2026-09-27)

검증: 이현수 · 실행·문서 정리 지원: Claude Code

- 대상 커밋: `heechan9/bunkering-ai` main `3b5f95b61162263d84034b94208d3e001069cc12` (#65, 2026-09-25)
- 논문 기준: `docs/submission/ack_paper_v7_5.pdf`
- 환경: Windows 11 Pro 10.0.26200 · Python 3.13.14 (venv) · torch 2.13.0+cpu · gymnasium 1.3.0 · numpy 2.5.1 · pandas 3.0.5 · Node 24.16.0 / pnpm 11.25.0
- 체크포인트: Release `dqn_final.pt` SHA-256 `970aafbf…cf392` (README 기재값과 일치)
- 웹: 배포본 https://bunkering-ocean-lab.hc24734503.chatgpt.site (시스템 Chrome 헤드리스 + Playwright 에뮬레이션, 1440×900 / 768 / 390 / 360px)
- 새 학습·코드 수정·논문 수정 없음. 이 문서는 검증 결과 기록만 추가하며, 발견한 문제는 수정하지 않고 제안으로만 남김. 원본 AB-LOG는 받지 않았고 저장소에도 포함하지 않음.

## 1. 실행·결과 재현

| 항목 | 결과 | 근거 |
|---|---|---|
| 전체 테스트 `python -m pytest -q` | 정상 | 245 passed, 17 subtests passed (`final_v7_5_verification_20260927.log`) |
| 근거감사 `python -m scripts.audit_paper_evidence` | 정상 | 8/8 passed (`final_v7_5_verification_20260927.log`) |
| 해기원 공개 집계 `python -m scripts.compare_ab_log --check` | 정상 | `PASS: 3 selected windows and 15 hypothetical density scenarios reproduce exactly` (`final_v7_5_verification_20260927.log`) |
| 저장 모델 평가 `scripts/evaluate.py --episodes 100 --seed 42 --checkpoint checkpoints/dqn_final.pt` | 정상 | 정본 CSV 7종(evaluation_results, summary, termination, raw 4종)과 바이트 단위로 일치. manifest는 `created_at`만 다름 (`final_v7_5_verification_20260927.log`) |
| 웹 빌드·검사 (typecheck, lint, build, check-localization 317항목, check-purchase-comparison 548경로·19,030결정, check-voyage-csv) | 정상 | 저장소 밖 복사본에서 `pnpm install --frozen-lockfile` 후 실행 (lint·build 끝부분은 `final_v7_5_verification_20260927.log`) |
| `tests/test_web_evidence.py` | 정상 | 5 passed, 7 subtests |
| AB-LOG 원본 대조 | 확인 불가 | 원본 미보유. 공개 집계 재현만 수행 |
| 표 2, Suez/Cape 수치, tail 통계 | 확인 불가 (문서와는 일치) | 원 로그가 git-ignore 대상이라 재계산하지 못함. `multiseed_results_4seed.md`, `v1_5_results_4seed.md`와는 일치 |
| 그림 1 값 24,982 / 31,260 | 확인 불가 | 저장소에 텍스트 출처와 생성 스크립트가 없음. 34,317만 v1_5 문서의 34,316.90과 대응 |

참고: README의 공식 DQN(reward 0.044, SCI 847,118, 급유 5.31)은 `dqn_final.pt`, 논문의 "네 Double DQN" 값(0.0439, 839,763.41, 4.900)은 4-seed 평균이라 서로 다른 값임. 논문 문장 안에서 둘이 섞이지는 않음. 다만 4-seed의 `dqn_seed_42.pt`와 공식 `dqn_final.pt`가 서로 다른 파일이라, 표 1의 "학습 seed 42"를 공식 결과와 혼동할 여지는 있음.

## 2. 웹 기능

| 항목 | 결과 | 근거 |
|---|---|---|
| 한·영 전환 | 정상 | `html lang` ko↔en. EN 모드 1·2·3단계에서 한글이 남은 곳은 언어 버튼 "한국어"와 aria-label "Language / 언어"뿐 |
| 지도·지역 선택 (7곳) | 정상 | 7개 지역 제목 전환, 2단계 배지 "선택한 지역 · 호르무즈 해협" 연동 |
| 재생·일시정지·초기화 | 정상 | 재생 3.5초 후 3/30단계 → 일시정지 후 2.5초 동안 멈춤 유지 → 처음으로 누르면 0/30. 키보드 End에서 30/30(구매안 비교 "종료" 안내), ←키에서 29/30 |
| 정책 비교 (3단계 표) | 정상 | 도착률 0/3/100/100%, SCI 0 / 17,370 / 545,393 / 839,763, 구매량 0/2.9/85/131.3, 최종잔량 0/1.3/35/81.3, 미달률 원래/재분류가 논문 표 3과 일치 |
| 구매 후보별 지출·잔량·안전선 | 정상 | 4개 경로(미구매/구매 조합)의 총구매량·가정 SCI·종료잔량·최소잔량 15 판정 표시. Safe Stock 17번째 선택 시점에서 "부동소수점 경계" 표시를 확인 ([캡처](final_v7_5_verification_20260927/desktop_safestock_step16_boundary.png)) |
| 모바일: 조작창과 범례 겹침 (#65) | 정상 | 360/390/768px에서 재생 조작창과 범례의 겹침 면적 0, 12px 간격으로 세로 배치 ([캡처](final_v7_5_verification_20260927/mobile360_ko_map_controls_legend.png)) |
| 모바일: 버튼 잘림 | **문제 발견** | 영어 모드 360·390px에서 상단 탭 목록 폭이 427px라 뷰포트 324px를 넘음 → "03 Compare strategies" 탭이 잘리고(x 295–445) 페이지 전체에 가로 스크롤(문서 폭 445–446px)이 생김. 한국어 모드와 768px에서는 정상 ([캡처](final_v7_5_verification_20260927/mobile360_en_header_tab_cut.png)) |

실기기 GPU/WebGL 렌더링은 헤드리스(SwiftShader) 환경이라 확인하지 않음.

## 3. 논문·웹·결과표 정합성

| 항목 | 결과 | 근거 |
|---|---|---|
| 같은 조건의 비용·구매량·최종잔량 | 정상 | 논문 표 3, 웹 표, `research-summary.json`, `replay.json` 700궤적 재계산이 정본 CSV와 일치. 추가 구매 0.46325 = 추가 잔량 0.46325, SCI +53.97% |
| 목적지 도착과 안전여유 구분 | 정상 | 논문 "미달률은 … 연료고갈률과 다르다", 웹 "도착 여부와 안전여유는 별개입니다" |
| 급유 행동 횟수 ≠ 실제 기항 | 정상 | 논문 "급유 행동 횟수도 실제 기항 횟수가 아니다", 웹 "실제 작업시간이나 운영비를 측정한 값은 아닙니다" |
| kL·M/T, 기록값·가정값 구분 | 정상 | 논문 표 4 주석, 웹 AB-LOG 표(단위·근거 셀 표기), 15개 시나리오를 "가정"으로 표기. 수치(0.852774 등, 194.565 / 192.270 / 175.525, −0.635 t)를 JSON에서 재계산한 값과 일치 |
| ROB 차감값을 실측 정확성·비용절감 검증으로 설명하지 않는지 | 정상 | 논문·웹·README·hanbada 문서 모두 "산술 관계이며 독립 계측 검증이 아니다"로 표기. 과장 표현은 발견하지 못함 |
| 표현 일관성 (경미) | 문제 발견 | 웹 AB-LOG 카드에 "일별표 대조 보류 … 직접 비교하지 않습니다"(`AbLogReview.tsx:20`) 바로 다음에 "집계 직접 비교·가정 민감도 실험"(`:21`) 제목이 나옴. `page.tsx:66`, `SourceInventory.tsx:8`의 "환산·기간 대조 보류"도 v7.5의 "15개 가정 시나리오 계산, 실측 정합성 미확정"과 어긋나 보임. 구매안 비교는 "최소잔량 15", 다른 화면은 "안전선 15"로 용어가 다름 |

## 오래된 링크·설명

- 웹 "검증 근거 · 논문 · 데이터 범위"의 논문 링크가 `ack_paper_v7_0.md`와 `ack_paper_v7_0_layout.pdf`를 가리킴 (`web/ocean-lab/app/page.tsx:66`, 배포본 JS에서도 확인)
- `README.md:1, 5, 9, 337`에서 v7.0을 최신 논문으로 안내함
- `README.md:30` 배지가 `tests-225_passed`로 되어 있음 (현재 245 passed)
- `web/README.md:3`이 "Sites 버전 22, 커밋 3e61217…, 논문 v7.0"으로 되어 있고 #64(구매안 비교)와 #65(모바일 범례)가 빠져 있음
- `web/ocean-lab/SOURCE_IMPORT.json`: 137개 해시만 기록돼 있음. 현재 추적 파일은 144개이고, #64 파일 6개가 누락됐으며 `globals.css`, `page.tsx`, `Geography.tsx`의 해시가 다름
- `SourceInventory.tsx:8`에 "논문 v5.0 반영"이 남아 있음
- 깨진 상대 링크는 없음 (README, web/README, PROJECT_STATUS, hanbada 문서 3종)

## 필요한 파일

- 한바다호 AB-LOG 원본(xlsx): 원본 대조를 하려면 필요함. 받게 되면 `python -m scripts.compare_ab_log --workbook <경로>`로 로컬에서만 확인할 예정이며 GitHub에는 올리지 않음
- 표 2와 tail 통계를 재계산하려면 multiseed/V1.5 원 로그(git-ignore 대상)가 필요함
