# External fuel and shaft-power research review

Updated 2026-10-05 (KST). Official DQN and operating model remain unchanged.

|Study|Executed result|Decision|
|---|---|---|
|DataBio consumption, ships 1/3|Chronological holdout: residual model MAE +8.65% / -1.91% versus cubic; ship 3 R² negative|No replacement|
|French-inspired shaft-power MLP|Three seeds each: ship 1 MAE improves 5.12–8.01%; ship 3 0.51–3.27%|Ship 1 prediction candidate; no deployment|
|Private vessel review|Detailed records withheld; unit/time alignment unresolved|No operating adoption or measured savings claim|
|Private vessel review|Detailed records withheld; unit/time alignment unresolved|No operating adoption or measured savings claim|
|Australia connection|50 port-quarter aggregate delays, hypothetical 1000nm voyage; speed-up may produce misleading energy reduction|Hold policy optimization|

The French work adapts an MLP architecture and training protocol from SSRN 7232001. It does not reproduce its resistance/efficiency physics or proprietary nine-vessel dataset. DataBio fishing vessels are different ships. Shaft kW is not fuel L/h. Seed runs are not independent ship trials. Australia records are aggregates, not matched DataBio port calls.

Sources: https://zenodo.org/records/3563390 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7232001 ; https://www.bitre.gov.au/publications/2026/waterline-71 . The private Hanbada workbook already exists in the project Drive; daily units are kL, summary consumption uses ROB difference, Sheet1 is excluded. Density and actual planned deadlines are unresolved.

## Reproduction

Research dependencies: numpy, pandas, scipy, scikit-learn, openpyxl, joblib; shaft-power adaptation additionally requires torch (recorded runtime versions in result JSON). Use a separate research environment.

Place authorized DataBioDataset1.zip in inputs/; audit_databio.py verifies the publisher checksum. Run train_consumption.py for L/h candidates or french_mlp_adaptation.py for kW candidates. The latter also reads the public Australia CSV in ../canada_anchorage/inputs/.

Private vessel CLI exports are disabled in this public workspace. Authorized analysis must use a private workspace; detailed data and derived quantities must not be committed.

Private/licensed originals, row-level predictions, PDFs, correspondence and weights are excluded from this repository. Acquire inputs under applicable terms. Published JSON is aggregate diagnostic evidence; no operational safety or measured fuel-saving claim follows from it. Hanbada folds include later periods when holding out earlier legs, so they are diagnostic rather than prospective validation.


## Condition audit, 2026-10-05

Both ships have all-zero wind speed/direction. Ship3 draught is constant. Weather sensitivity cannot be validated; the four-input MLP has only two varying inputs for ship1 and one for ship3. All8 frozen candidates fail the validation-based baseline replacement gate despite some holdout improvements. [Detailed report](results/condition_diagnostics/판정.md). Run condition_diagnostics.py; the --hanbada option is rejected here; authorized vessel-specific analysis is kept private.
