# 해외자료와 안전재고 전략 연구 실험

2026-10-03에 수행한 별도 연구 실험의 코드·집계 결과를 보관합니다. 공식 DQN, 기본 환경, 기존 평가 결과를 교체하지 않습니다. 최종 판단은 [결정표](DECISIONS.md), 논문용 설명은 [연구 서술 초안](../../docs/technical/external_validation_writeup.md)을 참고하세요.

## 구조와 재현 범위
- `archive/`: 당시 실행 스크립트. `archive_sha256.json`으로 코드 바이트를 검증합니다.
- `snapshots/`: 집계 CSV, 프로토콜, 보고서. 각 보고서의 당시 조건과 한계를 보존합니다.
- `reproduce.py`: 원본 입력과 출력이 위치할 별도 작업 폴더에 스크립트를 준비하고 실행합니다. 저장소 내부를 출력 경로로 쓰지 않습니다.

원본 Parquet·원본 XLSX·테스트 구간 행별 자료·학습 가중치는 이 변경에 포함하지 않습니다. 한바다호는 저장소에 이미 공개된 집계만 사용합니다. FuelCast 원본 및 파생 자료에는 해당 데이터 카드 이용 조건이 적용됩니다. 집계 보고서의 절대 경로·ZIP 설명은 당시 실행 환경의 기록이며 새 실행은 아래 절차를 따릅니다.

## 환경
Python 3.12에서 실행했습니다. 초기 예측 실험과 후속 RL 실험의 환경은 서로 다를 수 있습니다. `requirements.txt`는 후속 RL 환경과 예측 도구를 명시한 재현용 시작점이며 환경 전체의 암호학적 잠금 파일은 아닙니다.

```bash
python -m venv /tmp/bunker-research-venv
source /tmp/bunker-research-venv/bin/activate
pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r research/external_validation/requirements.txt
python research/external_validation/reproduce.py --workspace /tmp/bunker-research
```

## 입력 배치
별도 작업 폴더 아래 다음 경로에 허가된 원본·기존 재현 ZIP의 입력을 배치합니다. 아래 파일은 staging 명령이 다운로드하지 않습니다.

|경로|용도|
|---|---|
|`feasibility/CPS_Poseidon.parquet`, `CPS_Triton.parquet`, `OSS_Ceto.parquet`|FuelCast 공식 원본. `fuelcast-pilot/protocol.json`의 SHA-256으로 확인|
|`integrated-pilot/dqn_final.pt`|공식 Release 체크포인트. SHA-256 `970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392`|
|`upload/upload-weeklyshipcrossingsbyshiptypethroughsixglobalmaritimepassages.csv`|사용자 제공 ONS 선종별 CSV, 해시는 ONS 실험 manifest 참조|
|`country-pilot/eia.html`|확보한 EIA 월별 잔사유 가격 페이지 스냅샷|
|`country-pilot/brest/Maritime Routes and Tracklets/`|기존 확보 Brest `prototypes.csv`, `tracklets.csv`, `nomen.csv`|
|`strathclyde-appendix/supplement.pdf`, `figshare.json`|Figshare 5472880 보충자료 및 메타데이터|

FuelCast: https://huggingface.co/datasets/krohnedigital/FuelCast

Brest: https://zenodo.org/records/6402160

Strathclyde: https://api.figshare.com/v2/articles/5472880

체크포인트: https://github.com/heechan9/bunkering-ai/releases/tag/official-eval-2026-09-01

## 실행 순서
필요한 실험만 선택합니다. `fuelcast-retrain`은 3개 학습 시드 × 1,500 에피소드를 실제 실행하므로 단순 문서 확인에 필요하지 않습니다.

```bash
# 예측값과 시간순 분할 프로토콜 생성
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment fuelcast-pilot/run.py
# 원래 정책의 소비 변동 검증 (ONS CSV도 필요)
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment ons-fuelcast-pilot/run.py
# 실험용 추가 학습
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment fuelcast-retrain/run.py
# 공개 그림 근삿값에 대한 합성 시나리오 및 ±1pp 점검
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment strathclyde-appendix/run.py
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment strathclyde-appendix/uncertainty.py
# 소비량 기반 규칙, 별도 시간 구간, 최소 예비연료 규칙
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment adaptive-stock-review/run.py
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment adaptive-stock-validation/run.py
python research/external_validation/reproduce.py --workspace /tmp/bunker-research --experiment reserve-floor-review/run.py
```

나머지 기록도 `--experiment fuelcast-pilot/policy_pilot.py`, `country-pilot/run_experiments.py`, `integrated-pilot/run.py`, `eia-hanbada-review/run.py`로 실행합니다. 국가 자료 예비 실험이 `eia_monthly.csv`를 생성하고 이후 가격 실험들이 사용합니다. `integrated-pilot`은 Brest nomen.csv도 필요합니다. AdaptiveStock은 Strathclyde 실행이 만든 scenario_assumptions.csv를 읽습니다. 환경 상속을 위해 staging은 모든 연구 스크립트를 함께 준비합니다.

재실행 출력은 같은 실험 디렉터리에 기록됩니다. 이미 주요 결과가 있으면 기본적으로 실행을 막으며, 의도한 재실행에는 `--allow-output-replace`를 사용합니다. 기존 다른 내용의 코드 파일은 덮어쓰지 않습니다. 초기 예측 실행 없이 규칙 평가만 재현하려면 본인이 보관한 기존 재현 ZIP의 `fuelcast-pilot` 예측 CSV와 protocol.json을 배치할 수 있습니다.

## 해석
모든 SCI는 합성 비용지수입니다. 테스트 구간을 재학습에 넣지 않았지만 일부 실험은 이미 검토한 구간을 다시 평가했습니다. 후속 시간 창도 같은 선박 자료이므로 독립 외부검증이 아닙니다. StrictEnv의 급유 전 부족 판정은 공식 환경 판정과 다릅니다. 연구 결과를 공식 수치와 합산하지 않습니다. 추가 안전재고 정책은 과거 소비 관측을 사용하므로 기존 DQN과 정보량이 동일한 알고리즘 비교가 아닙니다.
