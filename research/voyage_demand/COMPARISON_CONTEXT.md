# Synthetic declaration comparator

Implementation base: Bunker main 08ccece5fa8d4332d958d8338861160d862a0351. Existing validation.py is reused unchanged SHA119867bf728f195f75324701d8219e5537a93d0ac7be29ebac8185b811c58305.

Independent review found Python structural equality treats 0/False, 1/True and 0/0.0 as equal while JSON fingerprints differ. R2 compares each normalized field using the SAME canonical JSON representation used for fingerprints.

Normalization policy: timestamps become UTC ISO strings, feature order is sorted by unique name, object keys are sorted. No numerical coercion or physical-unit conversion. All other declaration spelling/types remain significant: latency 0 versus 0.0 conservatively HOLD, as do metadata 0 versus false and 0.0 versus -0.0. This is not a claim that these numbers differ physically. Callers wanting semantic numeric equality must first specify a separate domain normalization policy; this utility does not infer one. A match now implies identical canonical context bytes and fingerprints.

Still synthetic declarations only. Hash reference targets are not read or authenticated, no optimizer/model/real-voyage evaluation/operational approval. Integrated into this repository through [PR #159](https://github.com/heechan9/bunkering-ai/pull/159). Repository integration does not imply deployment, operational use, or approval.

Run from the repository root:

```bash
python -m pytest tests/test_voyage_comparison_contract.py tests/test_voyage_type_regression.py tests/test_voyage_native_regression.py tests/test_voyage_independent.py tests/test_voyage_canonical_boundary.py tests/test_voyage_r3_independent.py -q
```
Repeat under -O is duplicate execution, not extra coverage.

## R3 JSON-native boundary
R2 independent review found Python tuples serialize as lists and non-string object keys can serialize as strings. R3 validates the entire input recursively BEFORE any normalization: exact built-in dict/list/str/bool/int/float and None only, dict keys must be exact strings, floating values finite. Tuples, bytes, sets, custom subclasses, and cyclic containers are rejected with ValueError. Shared but noncyclic containers are permitted. This is an input data contract, not a hostile-input resource isolation/security guarantee. Time values must now be JSON strings (not Python datetime objects). Existing UTC timestamp and feature-order normalization and conservative numeric-type policy remain unchanged. PR #159 added this comparator and its tests without modifying existing upstream files; operational use and approval remain out of scope.


## Review follow-up: lossless normalization boundaries
Before converting any of the six context/feature timestamps, reject nonzero fractional digits beyond six places; trailing zero digits remain accepted. This prevents datetime microsecond truncation from hiding distinct declared instants. Before JSON normalization, reject surrogate code points in every string value and object key, while accepting ordinary Unicode including valid non-BMP characters. This prevents surrogate-pair/Unicode spelling collisions from dropping metadata entries. These are declaration-contract corrections, not proof of real input provenance or an operational security boundary.


## Timezone-offset contract
All six timestamps must end in `Z` or an explicit whole-minute offset written exactly `+HH:MM` / `-HH:MM`. Offset seconds, fractional offsets, and compact/hour-only offset spellings are rejected before datetime conversion, including zero offset seconds. This intentionally narrower declaration syntax prevents fractional timezone offsets from being silently discarded by the underlying parser. Standard positive/negative offsets, including half-hour and quarter-hour zones, retain UTC-equivalence normalization; representable fractional wall-clock seconds and trailing fractional zeroes remain accepted. The upstream shared timestamp validator is unchanged.
