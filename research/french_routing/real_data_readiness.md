# 프랑스 항로 연구 실제 데이터 연결 점검 — 2026-10-04

공식 Copernicus Marine 제품 GLOBAL_ANALYSISFORECAST_PHY_001_024는 해류 관련 자료와 다운로드 경로를 제공한다.
https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024/services
https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024/description
공식 안내는 CLI/Python subset 접근을 제공한다. 이는 EU 서비스 자료이며 프랑스 대학 논문의 원자료라고 부르지 않는다.

상태: 제품·접근 경로 확인만 완료, 데이터 다운로드·연결은 미수행.
필수 입력: 확정 실제 항로의 좌표와 UTC 출항시각, 해역/기간에 맞는 제품·버전,
동서/남북 유속 단위와 시간축, 육지/수심 제약, 선박 속도·소비모형.
현재 합성 평면 x/y는 위경도가 아니다. 한바다호 공개 소비 집계만으로 이 입력을 복원하지 않는다.
실측 평가에는 실제 운항 시점의 가용 예보와 사후 분석장을 구분해야 미래정보 누출을 피할 수 있다.
검증 순서: 입력 범위/단위/해시 → 좌표·시각 일치 → 육지 회피 → 공통 기상비용 평가 → 기존 경로와 비교.
결론: 자료원이 없어서 중단된 것이 아니라 항로·시각·선박모형 결합을 아직 검증하지 못한 상태.
