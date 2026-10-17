# 독립검토: 합성 정적 구매정책 비교

판정: 제한된 합성 개발 benchmark로 PASS. 실측, holdout, 일반적 solver 정확성 또는 AI 인과효과 증거로 사용하면 안 된다.

## 확인한 결과
- 사전정의 seed로 120개 입력을 독립 재생성해 cases.json과 정확히 동일함 확인. 세 블록 각각40, 제외/재추출 없음.
- 결과: OPTIMAL 86, INFEASIBLE34. 정책 feasible 최소필요75, 다음저가79, 출항집중79. 기준 feasible86건 중 정책실패11/7/7. 전체 공통 feasible75.
- 자체 순차물량/원가 코드로 446원장(기준86+정책360)을 전수 검산. 공급·최소급유·가용성·중간reserve·용량·종착equality 및 valid/invalid 판정 일치. 모든 feasible 구매합계=sum(consumption)+terminal-initial. 연료비, 톤당수수료, 정차당고정비를 각각 한 번만 더한 금액 및 저장원장 일치.
- pairwise 75/79/79건 비용차23.6967134513%/0.2788431748%/18.4296810235%. 동일 공통75건은23.6967134513%/0.2779945654%/18.5203286090%. 분모별 총액/백분율 독립 재계산 일치.
- 독립 stop enumeration을 120건 모두 다시 실행: status와 목적함수 일치. 최대 절대 목적차7.275957614183426e-12 USD.
- 수정 모듈 로딩 경로를 출력하며 시험36개(원본27+정책8+신규반례1) 별도 재실행, 모두 PASS.
- policy 및 helper 소스 검토와 AST 호출검사: 숨은 solver/최적해 수리 없음. 전체 정적 정보를 받지만 미래 공급량 부족을 보정하지 않는 규칙으로 사전 명시됨.

## 발견한 결함과 조치 검토
원본 monetary_fees_010은1차 MILP가 INFEASIBLE 오판. 독립 재현에서 presolve=True일 때 1차 호출만 status2. 동일 모델에 presolve=False 적용 시1차/2차 모두 OPTIMAL13,000 USD, q=[1,10,15]t, 원장valid, enumeration과 일치. 2차 정차수 최소화의 실패가 아니다. 원본 vendor 및 이전 프로젝트는 동일 SHA256. 패치는 복사본의 두 milp 호출 options에 presolve=False만 추가. 내부 원인 완전규명/다른 환경 보장은 없음. 원본 실행 결과 보존 및 사후변경 공개 확인.

## 사전정의와 해석
초기 spec에는 정책명만 있어 규칙 상세 추가를 요청했고 최초 결과 실행 전 ALGORITHMS_KO.md와 해시 추가를 직접 확인했다. 최종 spec/정책 해시는 최초 보존값과 일치한다. 사전정의는 현재 대화 내 개발실험 기록이며 외부 독립 사전등록이나 미사용 holdout이 아니다. 원본 오류를 본 후 패치했으므로 최종120건은 개발 검증이다.
REPORT_KO.md는 공통분모 결과를 우선 제시하고 전체 실패율·pairwise 분모·원문제 infeasible을 명확히 구분한다. 무수수료 공급충분 블록에서 다음저가규칙34/34 최적 일치도 명시한다. 정적 최적해 우위는 최적화 정의상 기준이며 AI 효과가 아니라는 한계를 적절히 공개한다.

## 증거
independent_checks.json, independent_enumeration.json, independent_test_output.txt, diagnostic.jsonl, reviewed_source_sha256.json. 작성/실행한 독립검토 코드는 이 폴더에만 저장했다. 구현자 소스파일을 수정하지 않았다. 구현 폴더 SHA256SUMS 및 PREREGISTERED_SHA256의 모든 항목 검증 통과.
