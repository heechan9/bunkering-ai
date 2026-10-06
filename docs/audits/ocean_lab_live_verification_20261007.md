# Ocean Lab 운영 웹 확인 — 2026-10-07 (KST)

기존 공개 사이트 https://bunkering-ocean-lab.hc24734503.chatgpt.site 를 Windows의 Codex 내장 브라우저에서 직접 확인했다. 이 작업에서는 새 배포를 만들지 않았다. Sites에 이미 성공한 36판이 있었고 실제 다운로드에서 PR #99의 음수 수정 동작을 확인했다.

## 배포 식별
- Sites project: `appgprj_6aa43d5618ec8191b8c4c575506aa9ee`
- 저장 버전: `appgprj_6aa43d5618ec8191b8c4c575506aa9ee~appgver_6e7b8cbc39bc8191b2ac1502948ef359` (36판)
- 배포: `appgdep_6ac50f9dcae88191ba74019d97f926c5`, Sites 조회 결과 `succeeded`
- Sites 소스: `651d7a7d26c33922bf228d24c5f21cc1a07db8c2`
- GitHub 수정: [PR #99](https://github.com/heechan9/bunkering-ai/pull/99), 병합 커밋 `04ac897098f06406f8b86498c48c4ca9ece464fa`
- 두 저장소의 전체 SHA가 같다고 주장하지 않는다. 비교한 CSV 함수의 실행 코드는 같고 주석과 검사 배치가 다르다. Sites의 source-catalog는 별도 고정 근거를 사용한다.
- 35판·36판의 반환된 archive content_hash는 같았다. 이 메타데이터만으로 운영 코드가 수정 전이라고 판정할 수 없다. 실제 파일의 숫자 출력으로 수정 반영을 확인했다.

## 실제 운영 검사

| 항목 | 실행 방법 | 결과 |
|---|---|---|
| CSV 숫자·빈값 | 합성 테스트 파일을 파일 선택 API로 선택하고 결과 다운로드 버튼을 클릭, 디스크에 저장된 CSV 읽기 | residual `-5`, `0`, `5`, 빈값을 각각 보존 |
| 사용자 문자열 방어 | source_ref에 `=1+1` 입력 | 파일에서 `'=1+1`로 방어 유지 |
| CSV 오류 복구 | 열 수가 다른 파일 선택 후 정상 4행 파일 선택 | `Inconsistent column count` 표시 후 alert 0개, 정상 결과 복원 |
| 빈 양식 | 실제 버튼 클릭 및 새 저장 파일 확인 | 12개 헤더, 143 bytes |
| GLB | 실제 버튼 클릭 및 새 저장 파일 읽기 | 706,844 bytes, magic `glTF`, version 2, 선언 길이와 실제 길이 일치 |
| 공유 복원 | 실제 복사 버튼으로 생성한 URL을 다시 열고 자료 로딩 후 UI 확인 | English, Ulsan Port, Safe Stock, checkpoint 42, case 77, step 7, ship view 복원 |
| 반응형 지도 | 데스크톱 브라우저 viewport 360/390/412 × 844 | 로딩 완료 후 clientWidth와 scrollWidth 일치. 제목 → 지형높이 → 지도 순서 |
| 운항·비교 탭 | 같은 세 폭에서 탭 클릭 | 페이지 scrollWidth = clientWidth |

### 모바일 측정
classic 세로 스크롤바가 있어 innerWidth와 clientWidth는 15px 다르다. 페이지 가로 넘침은 scrollWidth−clientWidth로 판단했다.

| 설정 폭 | 로딩 직후 지도 client / scroll | 로딩 완료 후 client / scroll |
|---|---|---|
| 360 | 345 / 349 | 345 / 345 |
| 390 | 375 / 378 | 375 / 375 |
| 412 | 397 / 399 | 397 / 397 |

지도 로딩 직후 2~4px의 일시적 넘침은 관측했다. 이전 보고의 약 7px 현상과 같은 원인이라고 확정하지 않으며 임의로 CSS를 수정하지 않았다.

## 로컬 검사와 한계
Sites 소스에서 Node 24.19.0으로 `node scripts/check-voyage-csv.mjs`를 실행해 종료코드 0, 음수·0·양수·빈값·수식 방어 검사를 통과했다. 전체 Python 테스트·lint·build는 이번에 재실행하지 않았다. 새 배포 필요 여부를 판단하기 전 시작한 패키지 설치는 네트워크 timeout으로 첫 시도가 실패했고, 기존 배포의 실제 수정 동작을 확인한 뒤 불필요한 재시도는 중단했다.

실제 다운로드는 디스크에 저장된 파일을 검사했다. 내장 브라우저의 download 이벤트 대기는 timeout이었지만 CSV·양식·GLB가 실제 저장된 것은 확인했다. Blob 가로채기나 페이지 스크립트 주입은 사용하지 않았다. 파일 선택은 자동화 filechooser API이며 실제 OS 파일 선택 창을 사람이 조작한 검사는 아니다.

캡처·합성 검토 CSV·모바일 측정 JSON은 이 작업의 사용자 산출물로 보관했다. 실제 휴대폰·iOS Safari·다른 브라우저, 전체 문자열 공격 조합, 실선 안전성·연료/비용 절감은 검증 범위 밖이다. 공식 모델·수치·README 이미지·표와 PR #98은 변경하지 않았다.
