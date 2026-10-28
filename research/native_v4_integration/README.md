# native v4 통합 (C06): config·계약 병합·ledger·안전 fixture

> 공개 반영본: 역할명 기반 인터페이스로 가져온 검토용 초안입니다. 원본과 CSV owner/파일명/CLI 인수가 다릅니다. #133·#134에서 step CSV 입력 검증, 설정-실제 seed 일치, 출력 symlink/hardlink 보호와 검증 범위 표시를 보완했습니다. 종료 재고 가치는 `--regenerate-market`로 seed에서 다시 만든 시장값과 대조할 수 있습니다(아래 참고). **C01–C06 채택은 미완료**이므로 전체 검증 완료나 운영 승인으로 읽지 마세요. [현재 보완 범위](LOCAL_INTEGRATION_20261020.md)와 [최초 공개본 호환성·검증 이력](../../docs/audits/native_v4_first_round_20261019.md)을 구분해 확인하세요.

상태: **검토용 초안**. 계약 버전은 `BAI-CONTRACT-v0.1-draft`이고 C01~C06 모두 `pending`입니다. 희찬님이 채택하기 전에는 새 결과를 확정본으로 합치지 않습니다.

## 무엇을 재사용하고 무엇을 추가했나

| 구분 | 파일 | 비고 |
|---|---|---|
| 재사용 (수정 없음) | `envs/bunkering_env.py`, `scripts/baseline.py`, `evaluation/safety_accounting.py`, `agents/dqn.py` | git blob이 pinned `a4634faa`와 같은지 `verify-source`로 확인 |
| 재사용 (번들) | `bunker_disjoint_eval_v3/test_consistency.py`, `run_evaluation.py`, `independent_audit/check.py` | legacy 재현·전체 감사는 이 스크립트로 수행. 여기서 다시 만들지 않음 |
| 추가 | `config.py`, `config/bai_v4_native.json` | native 고정값과 pending 설정을 분리. 단위가 틀리거나 unknown 키가 있으면 오류 |
| 추가 | `contracts.py`, `contracts/` | data_statistics·domain_review·현수 CSV 병합. 담당자가 아닌 사람의 행 수정, 버전 변경, 팀원의 owner_decision 기입은 거부. v1.0 동결은 전부 accepted일 때만 가능 |
| 추가 | `ledger.py` | 임의 경로 입력, 최초 불일치 행 보고, `paired_summary.csv`(n_all/n_common_safe/n_excluded, ddof, n=0은 null, n=1은 구간 추정 불가) |
| 추가 | `policies.py` | `safe_stock_pre_refill_v1` 후보만 제공(C01 pending). 기존 `safe_stock`은 그대로 둠 |
| 추가 | `market_tape.py` | seed로 native 시장 가격·환율 tape를 numpy로 다시 만들어 시작·종료 재고 가치와 결정 시점 가격을 대조. env를 import하지 않고 기록 CSV의 가격도 읽지 않음 |
| 추가 | `cli.py` | 입력 폴더나 입력 파일 위로는 `--overwrite`를 줘도 쓰지 않음. 비어 있지 않은 출력 폴더는 `--overwrite`가 있어야 씀 |

## 실행

저장소 루트에서 실행합니다. 의존성은 번들 `requirements-eval.txt`(numpy 2.3.5, torch 2.5.1+cpu, gymnasium 1.4.0)와 같습니다. 이 모듈 자체는 표준 라이브러리와 numpy만 씁니다.

```bash
python research/native_v4_integration/cli.py validate-config --config research/native_v4_integration/config/bai_v4_native.json
python research/native_v4_integration/cli.py verify-source --source-verification research/native_v4_integration/fixtures/pinned_source_blobs.json
python research/native_v4_integration/cli.py ledger \
  --config research/native_v4_integration/config/bai_v4_native.json \
  --episodes <eval>/results/episodes.csv --steps <eval>/results/steps.csv \
  --legacy-summary <eval>/results/summary.json --regenerate-market --out-dir <new folder>
python research/native_v4_integration/cli.py merge-contracts \
  --template research/native_v4_integration/contracts/input_contract_template.csv \
  --domain-review <domain_review_contract.csv> --data-statistics <data_statistics_contract.csv> \
  --hyeonsu research/native_v4_integration/contracts/hyeonsu_contract.csv --out-dir <new folder>
```

테스트(`BAI_EVAL_ROOT`가 없으면 legacy 번들 대조 1건은 skip):

```bash
cd research/native_v4_integration
BAI_EVAL_ROOT=<bunker_disjoint_eval_v3 copy> python -m unittest -v test_native_fixture test_ledger test_config_cli test_market_tape
```

종료 코드: `ledger`는 `--steps`와 `--regenerate-market`을 함께 주고 회계·재생성 시장값과 **제공된 경우의 legacy-summary 비교**가 모두 맞으면 **PASS/0**입니다. `--steps` 없이 재생성만 하면 구매 SCI를 확인하지 않았으므로 INCOMPLETE/3입니다. 이 옵션이 없으면 회계 불일치가 없어도 독립 종료 가격·환율 검증이 없으므로 **INCOMPLETE/3**을 반환합니다. 회계 또는 legacy-summary 불일치는 FAIL/1이며 ledger 출력은 남깁니다. 도구가 `InputError`·`ConfigError`·`ContractError`로 처리하는 형식·값·설정·계약 검증 오류와 `OutputGuardError` 덮어쓰기 차단은 2입니다. 모든 예외가 처리되는 것은 아닙니다. 파일 없음·디코딩 오류, legacy-summary JSON 파싱 오류·필수 키 누락 등 일부 미처리 예외는 traceback과 종료 코드 1을 내므로 코드 1만으로 회계 FAIL과 구분할 수 없습니다. config JSON 파싱 오류는 `ConfigError`로 처리되어 2입니다. `validate-config`, `verify-source`, `merge-contracts`의 정상 종료는 0이지만 전체 ledger 검증이나 계약 채택을 뜻하지 않습니다. `verify-source`의 소스 불일치는 1입니다.

## Legacy summary 비교 상태

`--legacy-summary`는 제공된 경우에만 기존 요약과 비교합니다.
manifest의 `report.legacy_summary_status`와 CLI 보고서에 다음 상태를 기록합니다.

- `not_checked`: legacy summary 미제공, 비교하지 않음.
- `checked_match`: 제공된 summary가 기존 비교 규약상 일치함.
- `checked_mismatch`: 제공된 summary에서 불일치가 확인됨(FAIL/1).

따라서 PASS/0만으로 legacy summary를 제공하거나 비교했다고 해석하지 않습니다.
이 상태 표시는 계산 결과·기존 CSV·종료 코드 규약을 바꾸지 않습니다.
제공된 summary의 n은 음이 아닌 정수여야 하며 mean/CI는 허용된 null 또는 유한한 수치여야 합니다. NaN·Infinity·잘못된 형식은 일치로 처리하지 않고 입력 오류(2)로 거부합니다.

## 고정 수식 (native, 계약 채택 전)

- u=f−c, b=max(0,u), q=max(0,min(0.9·1[a>0], 0.95−b)), f'=min(0.95,b+q). c=0.05, r=0.15. 모두 탱크 비율이며 톤이 아닙니다.
- shortage는 u<−1e−9, reserve 위반은 u<r−1e−9입니다. 둘 다 clipping과 급유 **전**에 판정합니다. strict safe는 legacy 도착 AND shortage 0 AND reserve 위반 0입니다.
- 구매 SCI는 Σ q·P_t·FX_t(결정 시점 snapshot)입니다. 재고보정 SCI는 구매 SCI + f0·P0·FX0 − fT·PT·FXT입니다. SCI는 합성 지수이며 통화나 실제 절감액이 아닙니다.
- 행동 1/2/3의 전이는 같습니다. 항만 선택 성능을 나타내지 않습니다.

## 종료 재고 가치 재생성 검증 (`--regenerate-market`)

pinned env는 시장을 `env.np_random`에서만 뽑습니다. reset에서 가격·환율 정규분포 2개, 그 뒤 step마다 가격 1개·환율 1개를 연료 계산보다 먼저 뽑고, 행동은 이 난수를 쓰지 않습니다. 그래서 (seed, step)이 정해지면 정책과 관계없이 P_t·FX_t가 정해집니다. `market_tape.py`는 이 흐름을 `Generator(PCG64(SeedSequence(seed)))`로 다시 만들고 다음을 대조합니다.

- 시작 재고 가치 = 1.0·P0·FX0
- 종료 재고 가치 = fT·PT·FXT (T = episode steps)
- `--steps`가 있으면 step k의 decision_price·decision_fx = tape[k−1]

정책끼리 같은 가짜 가격을 쓰거나, 종료 가치 +100과 재고보정 SCI −100처럼 항등식을 맞춘 변조는 기존 회계 검사로는 잡히지 않지만 이 검사에서는 잡힙니다(`test_market_tape.py`). 이 검사는 native-legacy-v3 수식으로 기록값을 확인할 뿐입니다. C05 평가 방식의 채택이나 실제 시장 가격을 뜻하지 않습니다. 상수나 난수 순서가 다른 env에는 쓸 수 없습니다.

## 해석 제한

- 91,000,000–91,000,999는 이미 사용한 재현 세트입니다. unseen으로 부르지 않습니다. config에서 이 범위를 `new_frozen_plan`으로 지정하면 검증 오류가 납니다.
- 쌍 차이 구간은 1.96·sd/√n 기술통계입니다. 우위 검정이 아닙니다. 공통 strict-safe 집합이 0이면 비용 비교는 null입니다.
- legacy `run_evaluation.py`는 n=1일 때 se=0을 씁니다. v4 도구는 같은 경우 구간을 "추정 불가"로 보고합니다. 이는 새 도구 계약일 뿐이며 legacy 출력은 바꾸지 않습니다.
- `fixtures/smoke_*.csv`는 손으로 만든 합성 fixture입니다(`make_smoke_fixture.py`로 재생성). native 결과가 아닙니다.

## Local validation follow-up (2026-10-20)

Without `--regenerate-market`, clean ledger accounting remains **INCOMPLETE/3**. With the flag and `--steps`, clean recorded accounting/market checks return **PASS/0**; legacy summary is compared when supplied. PASS certifies only these recorded-data checks; it is not policy superiority, real-vessel safety, savings, personal review or contract adoption. `contract_adoption_status` remains `not_established_by_ledger`. Missing independent inputs or errors retain the documented narrower status.

Only pinned native-legacy-v3 constants/policy are supported by this reproduction tool. Alternate constants need a separately versioned implementation; proposals remain pending. See [local integration and verification](LOCAL_INTEGRATION_20261020.md).

## Round-2 follow-up (2026-10-26): regenerated terminal valuation

`--regenerate-market` rebuilds each seed's price/FX tape from the pinned env formula and checks initial value, terminal value and, with `--steps`, every decision price/FX. With `--steps` and all checks clean the ledger returns PASS/0 (without `--steps` it stays INCOMPLETE/3) and `terminal_valuation_status=regenerated_market_tape_match`; `contract_adoption_status` stays `not_established_by_ledger`. Without the flag the previous INCOMPLETE/3 behaviour is unchanged.

Submitted Windows logs (Claude Code execution, not a teammate's completed personal review) report 78 native tests and the recorded 91M/60M PASS runs. They are submission evidence, not this integration's independent execution. The original raw evaluation bundle/model and raw 60M CSVs are not included in the submitted ZIP.

## 2026-10-26 contract/code review candidate

[Contract reflection table, input draft and evidence limits](../../docs/audits/native_contract_integration_20261026.md).
This unmerged follow-up adds `paired_final_fuel.csv`: both policies use the same
seeds within `all` or `common_safe`; an empty common-safe subset leaves both means
null (empty CSV cells). Its `common_safe` corresponds to SCI `common_strict_safe`.
Per-policy means in `policy_summary.csv` are not paired safe-population estimates.
Existing SCI/ledger outputs and native configuration are preserved; fuel is a
normalized tank fraction, not savings. No contract is accepted or frozen.
The domain-review draft under `contracts/drafts/` is prepared by Codex from the
first-round document, not a new personal review, and is not loaded by default.


## Round-2 integration review

[Integration basis, direct tests, submitted-log limits and remaining conditions](../../docs/audits/native_market_round2_integration_20261026.md).
The paired-final-fuel output and domain draft from #144 remain intact. C01–C06
and all human approval fields remain pending. The earlier audit is a dated record
of checks before this round-2 implementation, not a current claim that the flag
is unavailable. Raw input CSVs, models and private logs are not published.
