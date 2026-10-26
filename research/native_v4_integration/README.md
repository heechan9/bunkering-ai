# native v4 통합 (C06): config·계약 병합·ledger·안전 fixture

> 공개 반영본: 역할명 기반 인터페이스로 가져온 검토용 초안입니다. 원본과 CSV owner/파일명/CLI 인수가 다릅니다. #133·#134에서 step CSV 입력 검증, 설정-실제 seed 일치, 출력 symlink/hardlink 보호와 검증 범위 표시를 보완했습니다. **독립 종료 재고 가치 검증과 C01–C06 채택은 미완료**이므로 전체 검증 완료나 운영 승인으로 읽지 마세요. [현재 보완 범위](LOCAL_INTEGRATION_20261020.md)와 [최초 공개본 호환성·검증 이력](../../docs/audits/native_v4_first_round_20261019.md)을 구분해 확인하세요.

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
| 추가 | `cli.py` | 입력 폴더나 입력 파일 위로는 `--overwrite`를 줘도 쓰지 않음. 비어 있지 않은 출력 폴더는 `--overwrite`가 있어야 씀 |

## 실행

저장소 루트에서 실행합니다. 의존성은 번들 `requirements-eval.txt`(numpy 2.3.5, torch 2.5.1+cpu, gymnasium 1.4.0)와 같습니다. 이 모듈 자체는 표준 라이브러리와 numpy만 씁니다.

```bash
python research/native_v4_integration/cli.py validate-config --config research/native_v4_integration/config/bai_v4_native.json
python research/native_v4_integration/cli.py verify-source --source-verification research/native_v4_integration/fixtures/pinned_source_blobs.json
python research/native_v4_integration/cli.py ledger \
  --config research/native_v4_integration/config/bai_v4_native.json \
  --episodes <eval>/results/episodes.csv --steps <eval>/results/steps.csv \
  --legacy-summary <eval>/results/summary.json --out-dir <new folder>
python research/native_v4_integration/cli.py merge-contracts \
  --template research/native_v4_integration/contracts/input_contract_template.csv \
  --domain-review <domain_review_contract.csv> --data-statistics <data_statistics_contract.csv> \
  --hyeonsu research/native_v4_integration/contracts/hyeonsu_contract.csv --out-dir <new folder>
```

테스트(`BAI_EVAL_ROOT`가 없으면 legacy 번들 대조 1건은 skip):

```bash
cd research/native_v4_integration
BAI_EVAL_ROOT=<bunker_disjoint_eval_v3 copy> python -m unittest -v test_native_fixture test_ledger test_config_cli
```

종료 코드: `ledger`는 회계 불일치가 없어도 독립 종료 가격·환율 검증이 없으므로 **INCOMPLETE/3**을 반환합니다. 회계 또는 legacy-summary 불일치는 FAIL/1이며 ledger 출력은 남깁니다. 도구가 `InputError`·`ConfigError`·`ContractError`로 처리하는 형식·값·설정·계약 검증 오류와 `OutputGuardError` 덮어쓰기 차단은 2입니다. 모든 예외가 처리되는 것은 아닙니다. 파일 없음·디코딩 오류, legacy-summary JSON 파싱 오류·필수 키 누락 등 일부 미처리 예외는 traceback과 종료 코드 1을 내므로 코드 1만으로 회계 FAIL과 구분할 수 없습니다. config JSON 파싱 오류는 `ConfigError`로 처리되어 2입니다. `validate-config`, `verify-source`, `merge-contracts`의 정상 종료는 0이지만 전체 ledger 검증이나 계약 채택을 뜻하지 않습니다. `verify-source`의 소스 불일치는 1입니다.

## 고정 수식 (native, 계약 채택 전)

- u=f−c, b=max(0,u), q=max(0,min(0.9·1[a>0], 0.95−b)), f'=min(0.95,b+q). c=0.05, r=0.15. 모두 탱크 비율이며 톤이 아닙니다.
- shortage는 u<−1e−9, reserve 위반은 u<r−1e−9입니다. 둘 다 clipping과 급유 **전**에 판정합니다. strict safe는 legacy 도착 AND shortage 0 AND reserve 위반 0입니다.
- 구매 SCI는 Σ q·P_t·FX_t(결정 시점 snapshot)입니다. 재고보정 SCI는 구매 SCI + f0·P0·FX0 − fT·PT·FXT입니다. SCI는 합성 지수이며 통화나 실제 절감액이 아닙니다.
- 행동 1/2/3의 전이는 같습니다. 항만 선택 성능을 나타내지 않습니다.

## 해석 제한

- 91,000,000–91,000,999는 이미 사용한 재현 세트입니다. unseen으로 부르지 않습니다. config에서 이 범위를 `new_frozen_plan`으로 지정하면 검증 오류가 납니다.
- 쌍 차이 구간은 1.96·sd/√n 기술통계입니다. 우위 검정이 아닙니다. 공통 strict-safe 집합이 0이면 비용 비교는 null입니다.
- legacy `run_evaluation.py`는 n=1일 때 se=0을 씁니다. v4 도구는 같은 경우 구간을 "추정 불가"로 보고합니다. 이는 새 도구 계약일 뿐이며 legacy 출력은 바꾸지 않습니다.
- `fixtures/smoke_*.csv`는 손으로 만든 합성 fixture입니다(`make_smoke_fixture.py`로 재생성). native 결과가 아닙니다.

## Local validation follow-up (2026-10-20)

Clean ledger accounting returns **INCOMPLETE, exit 3**, because terminal market price/FX has not been independently verified. `accounting_status=PASS` is a narrower identity result, not complete valuation or owner adoption. Recorded-step checks run only when `--steps` is supplied; otherwise `step_audit_status=not_checked`. Even `step_audit_status=checked` does not establish terminal market price/FX independently. Accounting mismatches return FAIL/1. Handled `InputError`, `ConfigError`, `ContractError` and `OutputGuardError` exceptions return 2, not every input/output failure. Unhandled errors such as missing files, decoding failures or malformed/missing-key legacy-summary JSON can exit 1 with a traceback; exit 1 alone does not identify an accounting FAIL. Config JSON parse errors are handled as `ConfigError` (exit 2). Other subcommands retain their exit codes.

Only pinned native-legacy-v3 constants/policy are supported by this reproduction tool. Alternate constants need a separately versioned implementation; proposals remain pending. See [local integration and verification](LOCAL_INTEGRATION_20261020.md).

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
