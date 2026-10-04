# 브레스트 AIS·시간별 해류 결합 점검

2026-10-04: 800 tracklet / 4000점에 대해 사후 결합 평가 완료.
기획·범위 최희찬, 구현·실행·검증 Codex.

|판정|점 수|
|---|---:|
|해류 정상 결합|2070|
|해류 결측 또는 시간 허용범위 초과|1435|
|원격 chunk 접근 실패(403)|355|
|tracklet 시각 순서 보류|140|

5점 모두 정상 결합된 조각은 409/800(51.125%). 정상 점은 2070/4000(51.75%).
시각 엄격 증가 772/800, 나머지28조각 보류. 원본 점 순서를 재정렬하지 않는다.
403은 해류가 없다는 의미로 바꾸지 않는다. 실패한 한 chunk 그룹의 355점을 보류했다.

AIS 원본: NATO STO CMRE, 프랑스 브레스트 해역, https://zenodo.org/records/6402160
READ_ME 라이선스 CC-BY-NC-SA-4.0. 원본 ZIP SHA-256은 summary.json에 기록.
해류: EU Copernicus Marine IBI_MULTIYEAR_PHY_005_002,
cmems_mod_ibi_phy-cur_my_0.027deg_PT1H-m, version 202511.
https://data.marine.copernicus.eu/product/IBI_MULTIYEAR_PHY_005_002/services
표층 uo/vo, m/s. nearest 격자·시간을 사용하고 연안 결측을 다른 격자로 대체하지 않았다.
정상 점 유속 유한값, 시간차30분 이내, 위경도 차 각0.014도 이내 확인.

AIS ts는 Unix seconds UTC로 해석한 조건부 결과다. 시간 표현의 원문 확인은 남아 있다.
재분석은 사후 진단용이고 당시 가용 예보로 간주하지 않는다.
연료·급유·엔진 출력 관측이 없어 연료절감, DQN 개선, 실선 검증을 뜻하지 않는다.
해류 결합 연구의 입력 후보로 유용하나 공식 정책 입력 채택은 보류한다.

재실행: xarray, numpy, dask, zarr, fsspec, aiohttp 설치 후 `python research/brest_currents/join.py`.
출력 point_matches.csv, summary.json. 원격 제품이 갱신되거나 접근 상태가 달라지면 결과도 달라질 수 있다.
결과 CSV 해시는 summary.json에 기록했고 전체 CSV는 Drive 실험결과 ZIP에 보관한다.
공식 모델·제출 논문·웹 변경 없음.
