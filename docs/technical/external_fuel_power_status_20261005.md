# External fuel and shaft-power research review

Updated 2026-10-05 (KST). Official DQN and operating model remain unchanged.

|Study|Executed result|Decision|
|---|---|---|
|DataBio consumption, ships 1/3|Chronological holdout: residual model MAE +8.65% / -1.91% versus cubic; ship 3 R² negative|No replacement|
|French-inspired shaft-power MLP|Three seeds each: ship 1 MAE improves 5.12–8.01%; ship 3 0.51–3.27%|Ship 1 prediction candidate; no deployment|
|Hanbada consumption|Seven selected 24h daily blocks; target fit 4 train/3 test; separate four-leg leave-out review|Exploratory only|
|Hanbada slowdown|2/5/10% slower: modeled volume -2.15/-5.23/-9.93%, extra 3.43/8.84/18.67h|Assumptions, not measured savings|
|Australia connection|50 port-quarter aggregate delays, hypothetical 1000nm voyage; speed-up may produce misleading energy reduction|Hold policy optimization|

The French work adapts an MLP architecture and training protocol from SSRN 7232001. It does not reproduce its resistance/efficiency physics or proprietary nine-vessel dataset. DataBio fishing vessels are different ships. Shaft kW is not fuel L/h. Seed runs are not independent ship trials. Australia records are aggregates, not matched DataBio port calls.

Sources: https://zenodo.org/records/3563390 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7232001 ; https://www.bitre.gov.au/publications/2026/waterline-71 . The private Hanbada workbook already exists in the project Drive; daily units are kL, summary consumption uses ROB difference, Sheet1 is excluded. Density and actual planned deadlines are unresolved.

## Reproduction

Research dependencies: numpy, pandas, scipy, scikit-learn, openpyxl, joblib; shaft-power adaptation additionally requires torch (recorded runtime versions in result JSON). Use a separate research environment.

Place authorized DataBioDataset1.zip in inputs/; audit_databio.py verifies the publisher checksum. Run train_consumption.py for L/h candidates or french_mlp_adaptation.py for kW candidates. The latter also reads the public Australia CSV in ../canada_anchorage/inputs/.

Run `python research/fuel_source_review/validate_hanbada.py --workbook /absolute/private/workbook.xlsx`, then `python research/fuel_source_review/hanbada_policy_review.py --workbook /absolute/private/workbook.xlsx`. Both require the exact audited workbook SHA256; neither downloads private data. These scripts write aggregate results under results/.

Private/licensed originals, row-level predictions, PDFs, correspondence and weights are excluded from this repository. Acquire inputs under applicable terms. Published JSON is aggregate diagnostic evidence; no operational safety or measured fuel-saving claim follows from it. Hanbada folds include later periods when holding out earlier legs, so they are diagnostic rather than prospective validation.


## 조건별 소비·출력 감사 — 2026-10-05

저장된8개 후보의 기존 MAE 재현 및 속도·흘수·일자별 진단 완료. 선박1·3 풍속/풍향은 전부0, 선박3 흘수는 상수여서 해당 조건 변화 효과를 검증할 수 없다. 선박1 출력 테스트 개선은 유지되지만 학습 조건 내 검증 구간에서3시드 모두 cubic보다 악화했다.8개 후보 모두 검증 MAE 기반 교체 기준 미통과. 한바다7개 일별 기록은 전체 입력 조건 이식에 부족하다. [상세 판정](../../research/fuel_source_review/results/condition_diagnostics/판정.md).
