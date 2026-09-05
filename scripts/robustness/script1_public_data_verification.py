"""Independent verification of the UPA bunkering public-data descriptive
analysis committed in the repository (docs/data/upa_bunkering_anchorage.md,
scripts/analyze_upa_public_data.py, PR #8).

This script re-derives every reported figure directly from the raw CSV
using an independent implementation (it does NOT import or call
scripts/analyze_upa_public_data.py), so it is a true independent check
rather than a re-run of the original code.

Reproduction
------------
    git clone https://github.com/heechan9/bunkering-ai.git
    cd bunkering-ai
    git checkout f915df9922b63bade92c2efba0f7c74f66c21316   # main HEAD at run time
    pip install pandas numpy
    python scripts/robustness/script1_public_data_verification.py

    (This script only needs pandas/numpy — it reads the CSV directly and does
     not import envs/ or scripts/, so gymnasium is not required here. See
     script2_baseline_200seed_eval.py for the environment-dependent check.)

Provenance recorded at verification time
-----------------------------------------
    Repository main commit SHA : f915df9922b63bade92c2efba0f7c74f66c21316
    File verified              : data/public/upa_bunkering_anchorage_20240819.csv
    SHA-256 (UTF-8 copy, full) : b42537ebde057e87ef15f91a8c0fca6ab0ee010ff557b78a531112d4e79da1b7
      (this expected value is the one recorded in docs/data/upa_bunkering_anchorage.md;
       the script below does NOT just print it — it recomputes the hash of the file
       on disk with hashlib at run time and hard-fails if the two don't match, so a
       silently modified or wrong-revision CSV cannot pass unnoticed)
"""
import hashlib
import sys

import pandas as pd
import numpy as np

MAIN_COMMIT_SHA = "f915df9922b63bade92c2efba0f7c74f66c21316"
PUBLIC_DATA_SHA256 = "b42537ebde057e87ef15f91a8c0fca6ab0ee010ff557b78a531112d4e79da1b7"

path = "data/public/upa_bunkering_anchorage_20240819.csv"

print("=== 0. Integrity check (hashlib, computed at run time) ===")
with open(path, "rb") as f:
    file_bytes = f.read()
computed_sha256 = hashlib.sha256(file_bytes).hexdigest()
print("expected SHA-256:", PUBLIC_DATA_SHA256)
print("computed SHA-256:", computed_sha256)
if computed_sha256 != PUBLIC_DATA_SHA256:
    sys.exit(
        "FATAL: SHA-256 mismatch for "
        f"{path}\n  expected: {PUBLIC_DATA_SHA256}\n  computed: {computed_sha256}\n"
        "The file on disk does not match the provenance recorded in "
        "docs/data/upa_bunkering_anchorage.md — refusing to run the analysis "
        "on a file that cannot be verified. Do not edit PUBLIC_DATA_SHA256 to "
        "silence this check; re-fetch the correct file instead."
    )
print("Integrity check passed: file matches recorded provenance.\n")

df = pd.read_csv(path, encoding="utf-8")

print("=== 1. Schema ===")
print(list(df.columns))
print("shape:", df.shape)
print(df.dtypes)

print("\n=== 2. Missing values ===")
print(df.isna().sum())
print("total missing cells:", df.isna().sum().sum())

print("\n=== 3. Exact duplicate rows ===")
dup_mask = df.duplicated(keep=False)
print("rows involved in duplication (keep=False):", dup_mask.sum())
print("excess duplicate rows (keep='first'):", df.duplicated(keep='first').sum())
dup_groups = df[dup_mask].groupby(list(df.columns)).size().reset_index(name='n')
print("num duplicate groups:", len(dup_groups))
print(dup_groups['n'].value_counts())

print("\n=== 4. 벙커량 0 rows ===")
zero_bunker = (df['벙커량']==0).sum()
print("zero bunker rows:", zero_bunker)
print(df[df['벙커량']==0].groupby('입항년도').size())

print("\n=== 5. Schedule reversal (예정종료일 < 예정시작일) ===")
start = pd.to_datetime(df['예정시작일'])
end = pd.to_datetime(df['예정종료일'])
reg = pd.to_datetime(df['등록일'])
dur = (end-start).dt.days
rev = (dur<0).sum()
print("reversal rows:", rev)
print("reversal day distribution:")
print(dur[dur<0].value_counts().sort_index())

print("\n=== 6. 입항구분명 distribution ===")
print(df['입항구분명'].value_counts())
print(df['입항구분명'].value_counts(normalize=True).round(4))

print("\n=== 7. Year distribution (입항년도) ===")
print(df['입항년도'].value_counts().sort_index())

print("\n=== 8. Year mismatch: 입항년도 vs 예정시작일 year ===")
mismatch = (df['입항년도'] != start.dt.year).sum()
print("mismatch rows:", mismatch)

print("\n=== 9. 총톤수 (GT) distribution / high-end values ===")
gt = df['총톤수']
print(gt.describe())
print("top 10 largest:")
print(gt.sort_values(ascending=False).head(10).values)
q1,q3 = gt.quantile(0.25), gt.quantile(0.75)
iqr = q3-q1
upper = q3+1.5*iqr
print("IQR upper fence:", upper, " rows above fence:", (gt>upper).sum())

print("\n=== 10. 벙커량 distribution / high-end values ===")
bq = df['벙커량']
print(bq.describe())
print("top 10 largest:")
print(bq.sort_values(ascending=False).head(10).values)
print("smallest nonzero 10:")
print(bq[bq>0].sort_values().head(10).values)
q1b,q3b = bq.quantile(0.25), bq.quantile(0.75)
iqrb = q3b-q1b
upperb = q3b+1.5*iqrb
print("IQR upper fence:", upperb, " rows above fence:", (bq>upperb).sum())

print("\n=== 11. GT-Bunker correlation ===")
print(df[['총톤수','벙커량']].corr())

print("\n=== 12. Lead time (등록일 -> 예정시작일) ===")
lead = (start-reg).dt.days
print(lead.describe())
print("negative lead (registered after start) rows:", (lead<0).sum())

print("\n=== 13. Partial year check ===")
print("max 예정시작일:", start.max())
print("2024 count:", (df['입항년도']==2024).sum())

print("\n=== Provenance recorded ===")
print("main commit SHA:", MAIN_COMMIT_SHA)
print("public data SHA-256 (full, verified above via hashlib):", PUBLIC_DATA_SHA256)
