# 공개 공급자료 대조 — 2026-10-05

## MPA 원본 확보 및 검산

원본 https://www.mpa.gov.sg/api/media/9cd431ec-4e86-418b-951b-b96a09cd3991/bunker-sales_Aug-2026.xls
공식 진입 https://www.mpa.gov.sg/who-we-are/newsroom-resources/research-and-statistics/port-statistics

XLS 제목의 단위는 천 톤이다. 포털 설명의 tonnes만 보고 원시 숫자를 톤으로 사용하지 않는다. 2025 연간 56,774.89천 톤, 월합계 56,774.88천 톤: 차이 0.01천 톤(10톤). 반올림 영향 가능성이 있으며 원본 오류로 확정하지 않는다. 2026-08 잠정 4,772.68천 톤, 7월 4,740.14천 톤 대비 +0.68648%. 공급업체 지연신고 포함 및 추후 수정 가능. 월별·연료별 판매 집계로 사용하며 개별 실선 공급·ROB·가격으로 변환하지 않는다. 원본 SHA-256과 수치: results/mpa_audit.json.

## 울산세관

https://www.customs.go.kr/ulsan/na/ntt/selectNttList.do?bbsId=1644&mi=4650

사용자가 제공한 공식 PDF 원문을 확보하고 월 합계를 검산했다. 2026년 8월 총 95,604톤, 선종별·연료별 합계 모두 일치한다. LNG 1,675톤은 ATLANTIC TOPAZ 850톤과 NOCC PACIFIC 825톤의 합과 일치한다. 원문 SHA-256과 검산은 [JSON](results/ulsan_customs_202608_audit.json), 출처별 대조는 [보고서](results/ulsan_customs_202608_review.md)에 기록했다.

ATLANTIC TOPAZ 공급일은 세관 8월 6일과 UPA 8월 8일이 충돌하므로 확정하지 않는다. NOCC PACIFIC IMO 1041831은 Gard에서 확인했지만 공급 사건은 선명 기반 연결이다. 보유 EMSA 2024·2025 파일의 두 선명·IMO 검색은 0건이었다. 급유 전후 ROB·독립 계측 소비량·실제 구매가는 미확보이며 실제 절감률 검증은 미완료다. UPA 과거 신청·배정 CSV와 2026년 8월 사건은 동일기간 실선 연결 자료가 아니다.

## 자료 결합 판정

UPA 신청자료의 단위 미확인을 MPA 천 톤 단위로 보정하지 않는다. UPA 배정 기록에는 공급량이 없으며 선박 공통 식별자도 부족하다. 세관과 UPA는 신고/신청·시설 이용의 범위가 다를 수 있어 같은 월이라도 합계 일치를 강제하지 않는다. 비교하려면 같은 기간·항만·연료·선박대상 및 신고시점 기준을 먼저 확정해야 한다.
