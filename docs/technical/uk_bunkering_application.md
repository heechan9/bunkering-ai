# 영국 급유 최적화 2편 적용 — 2026-10-04

상태: 관련 연구·비교 실험 계약 반영. 논문 알고리즘 구현·재현·추가 학습은 미수행이다. 기존 공식 환경과 제출본은 변경하지 않았다.

## 자료와 확인 범위

1. Aydin, N., Lee, H., & Mansouri, S. A. (2017). Speed optimization and bunkering in liner shipping in the presence of uncertain service times and time windows at ports. European Journal of Operational Research, 259(1), 143–154. DOI: https://doi.org/10.1016/j.ejor.2016.10.002
당시 소속: 영국 Warwick Business School 및 Brunel Business School. 대학 저장소 공개 원문에서 소속·초록·모형 개요를 확인했다.
원문: https://wrap.warwick.ac.uk/id/eprint/82038/7/WRAP-speed-optimization-shipping-time-windows-ports-Aydin-2017.pdf

2. De, A., Choudhary, A., Turkay, M., & Tiwari, M. K. (2021). Bunkering policies for a fuel bunker management problem for liner shipping networks. European Journal of Operational Research, 289(3), 927–939. DOI: https://doi.org/10.1016/j.ejor.2019.07.044
영국 Loughborough University 참여 국제 공동연구. Manchester 저장소에 수록됐다는 이유로 모든 저자의 당시 소속을 Manchester로 분류하지 않는다. 온라인 선공개는 2019년, 권호 발행은 2021년이다. 대학 저장소의 초록·서지를 확인했으며 전체 수식·정책을 재현하지 않았다.
자료: https://repository.lboro.ac.uk/articles/journal_contribution/Bunkering_policies_for_a_fuel_bunker_management_problem_for_liner_shipping_networks/9033818

## 우리 프로젝트에 반영한 설계

| 문헌의 관점 | 현재 문제 | 후속 실험 계약 |
|---|---|---|
| Aydin: 불확실한 항만 처리시간과 도착기한 | 현재 step은 실제 시간으로 보정되지 않음 | 별도 시간 단위 환경에서 항만 처리시간·운항시간·도착기한을 명시하고 지각률·지각시간을 평가 |
| Aydin: 선속·급유의 동적 의사결정 | 현재 선속 행동이 없음 | 최초 비교는 기존 행동 유지. 선속을 추가하면 모든 정책에 같은 행동 집합을 부여하고 별도 실험으로 명명 |
| De: 가격·소비량 불확실성 | 가격 변화와 소비 충격의 효과가 혼재할 수 있음 | 가격만, 소비만, 둘 다 변동하는 조건을 동일 평가 사례로 비교 |
| De: 급유량·재고·비용을 함께 평가 | 높은 보상이 낮은 구매비용을 보장하지 않음 | 구매량·소비량·최종잔량·SCI를 병렬 보고하고 잔량가치 보정 비용을 별도 표시 |

## 비교 실험 표준안

아래는 합성 실험 제안이며 두 논문의 원래 시나리오나 실측 분포를 옮긴 것이 아니다.

- U0: 가격·소비량 모두 고정. 전이와 비용 회계 확인용.
- U1: 가격만 변동, 소비량 고정.
- U2: 가격 고정, 소비량만 변동.
- U3: 가격·소비량 모두 변동. 상관관계 가정과 생성 방법을 기록.
- T0/T1: 확정 시간 단위의 별도 환경에서 항만 처리시간 고정/변동 비교. 현재 공식 step에 임의의 시간을 부여하지 않음.

공통 조건: 평가 seed·초기재고·탱크용량·허용 행동·가격 관측 범위 동일. 미래 실현 가격·소비량을 미리 읽는 정책은 완전정보 참고값으로 분리. 튜닝용 사례와 최종 평가 사례 분리. 학습 seed와 평가 seed를 각각 기록.

필수 지표: 도착률, 급유 전 부족률, 예비연료 위반률, 구매량, 소비량, 최종잔량, 급유횟수, 구매 SCI. 시간 환경에는 지각률·시간·처리시간 추가. 비용 정의가 달라지면 같은 열로 합치지 않음. 실패 정책의 낮은 지출을 절감 효과로 해석하지 않음.

공식 환경의 소비 후 0 제한·급유 전이와 연구 StrictEnv의 부족 즉시 종료는 다르므로 결과 표마다 환경 식별자·소스 해시를 기록한다. 공통 안전 조건을 만족하는 사례의 비용과 전체 사례의 안전성 모두 보고한다. 안전 조건을 만족하는 공통 사례가 없으면 조건부 비용 비교는 산출하지 않는다.

## 후속 논문 문단 초안

Aydin 등(2017)은 항만 서비스 시간의 불확실성과 시간창을 고려한 선속 및 급유 의사결정을 동적계획법으로 다루었다. De 등(2021)은 가격과 소비량의 불확실성을 고려하여 급유 항만과 급유량을 결정하는 정책을 연구하였다. 이러한 연구는 급유 정책을 가격 반응만으로 설명하기보다 시간 제약·소비 불확실성·재고 및 비용과 함께 평가해야 함을 보여준다. 본 프로젝트의 현재 합성환경은 선속과 실제 항만 처리시간을 포함하지 않으므로 해당 연구의 운영상 비용 개선과 직접 비교하지 않는다. 후속 비교에서는 동일한 정보·행동 조건 아래 가격과 소비량의 변동 효과를 분리하고, 시간 제약은 별도 환경으로 확장할 계획이다.

## 완료 기준

이번 반영은 문헌과 실험 설계의 연결이다. 실행된 시나리오·원본 결과 파일·정책 검증이 생기기 전까지 README에 알고리즘 도입 완료 또는 성능 개선으로 표시하지 않는다. De 논문의 본문 확보 및 세부 정책 확인이 추가로 필요하다.
