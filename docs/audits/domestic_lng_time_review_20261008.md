# 국내 LNG 사례와 합성 시간 가정 대조 — 2026-10-08

검토 기준: main `54b0ad1a9813f8f6514ea96ed1eed2880f36be2a`. 자료 확보일 2026-10-07. 문서 검토이며 새 정책 평가나 현장 성능 검증이 아니다.

## 현재 구현

[criteria.json](../../research/fair_replacement_eval/criteria.json)의 time_overlay는 구간당 24시간, 급유 기항당 8시간이다. [common.py](../../research/fair_replacement_eval/common.py)의 voyage_hours는 `legs * leg_hours + stops * stop_hours`이며, stops는 실제 구매량이 환경의 미소량 기준을 넘은 스텝을 센다. 이는 실제 입출항 기록으로 측정한 기항 수가 아니다. BunkeringEnv 자체에는 시계·마감이 없고 이 상수는 SYNTHETIC PLACEHOLDER다.

30구간이면 항해 가정만 720시간이며 기준 마감은 700/720/728/736/760시간이다. 기항시간을 바꾸면 마감의 달성 가능성 분류·준수율도 바뀐다. 기존 판정 기준을 사후 수정하지 않는다.

## 국내 사례

|항목|UPA DAYTONA|BPA VISBY|
|---|---|---|
|작업 날짜|2026-02-23~24|2024-08-08|
|발표 날짜|2026-02-25|2024-08-09|
|장소|울산항 자동차부두|부산신항 5부두 BNCT|
|선종|자동차운반선|2,000TEU 컨테이너선|
|LNG 공급량|1,375톤|270톤|
|보도된 시간|10시간|08~22시 약14시간|
|하역 동시작업|있음|있음, STS 명시|
|성격|상업 공급|실증|
|보관 상태|공식 게시문 텍스트·본문 사진; 첨부 PDF/HWP 미확보|공식 PDF 3페이지·사진·게시문 텍스트|

출처: [UPA 공식 발표](https://www.upa.or.kr/portal/board/post/view.do?bcIdx=671&idx=16112&mid=0501010000), [BPA 공식 발표](https://busanpa.com/board/view.do?boardId=BBS_0000031&dataSid=32526&menuCd=DOM_000000105002001000&paging=ok&startPage=1).

## 결론: 현재 8시간을 실측값으로 교체할 근거는 부족

- 10시간·14시간은 순수 이송시간인지 준비·연결·분리 등을 포함하는지 서로 일치하는 정의가 확인되지 않았다. 양/시간의 단순 몫(137.5 및 약19.29톤/시간)을 펌프 속도나 항만 효율로 비교하지 않는다.
- 하역과 급유가 겹치므로 보고된 급유 관련 시간 전체가 항차의 추가 지연은 아니다. 단순화된 동시작업 모형에서는 추가시간을 max(하역시간, 급유시간)−하역시간으로 생각할 수 있지만, 시작 시각·선행 작업·대기·접안 조건이 필요하다. 이는 설계 설명이며 구현하거나 현장 자료에 적합한 값으로 추정한 것이 아니다.
- 두 사례에는 항해 구간 소요시간의 대응 기록이 없어 24시간 가정도 검증하지 못한다. DAYTONA가 이틀에 걸쳤다는 사실을 48시간 급유로 바꾸지 않는다.
- 사례 2건만으로 평균 기항시간을 추정하거나 공식 평가의 R3 시간 우위를 실선 성능으로 해석하지 않는다.
- 다음에 필요한 필드: 동일 항차의 도착·접안·출항, 급유 연결/이송/분리 시작·종료, 하역 시작·종료, 대기, 공급량, ROB, 구매가, 선박·항차 식별자.
- 시간 민감도 실험을 새로 한다면 기존 결과와 분리하고 후보·시간 정의·마감 시나리오·사용 시드를 실행 전에 기록한다. 이번에는 실행하지 않았다.

## 국내외 자료 확보 상태

|자료|실제 보관 범위|남은 일|
|---|---|---|
|MPA|공식 XLS: 2013~2025 연간, 2025 및2026년1~8월 월별; 원본 단위 천 톤|data.gov.sg 1995년부터의 장기 CSV 미다운로드; 페이지 단위 설명을 XLS에 적용하지 않음|
|Rotterdam|신규 공식 PDF: 2024~2026 Q2; LNG는 m³, 다른 연료는 톤; subtotal의 LNG 환산은 원문0.45톤/m³|미공표 x를0으로 처리하지 않음|
|EMSA|기존2024-v246·2025-v59 XLSX 재확보·시트 읽기 확인|10월7일 화면의2024-v248·2025-v61 다운로드 미완료|
|DAYTONA·VISBY|위 사례표 참조|DAYTONA 첨부 PDF/HWP 다운로드 미완료|

[MPA 공식 통계](https://www.mpa.gov.sg/port-marine-ops/marine-services/bunkering/bunkering-statistics), [MPA 장기 CSV 목록](https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view), [Rotterdam 원본](https://www.portofrotterdam.com/sites/default/files/2026-08/bunker-sales-2024-2026.pdf), [EMSA 공개 자료](https://mrv.emsa.europa.eu/).

원본 묶음과 해시는 프로젝트 비공개 Drive에 보관한다. 공개 GitHub에는 비공개 링크·모델·원자료를 추가하지 않는다. MPA/Rotterdam은 항만 집계, EMSA는 연간 보고 자료이며 항차별 급유 정책 검증을 대체하지 않는다. EMSA Full/Partial 보고를 단순 중복 합산하지 않는다. 울산세관 날짜·비율 불일치는 별도 미해결이다.

## 검증 범위

Codex가 공개 게시문·확보 파일 및 위 코드·criteria를 대조했다. 문서만 변경하며 criteria/해시/정책/공식 결과/체크포인트는 변경하지 않는다. 기존 pytest 통과 수를 이번 실행값으로 재기록하지 않는다.
