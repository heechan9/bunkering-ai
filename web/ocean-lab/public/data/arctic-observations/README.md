# Arctic observations reference

This is a reference panel inside the existing Arctic voyage workflow. It does not change the synthetic voyage assumptions, fuel/time arithmetic, Buy/Wait comparisons, or trained policy evaluation.

## Track

Purser, Autun (2026): Master tracks in different resolutions of POLARSTERN cruise PS155, Bremerhaven - Tromsø, 2026-07-04 - 2026-08-03. Alfred Wegener Institute, PANGAEA. https://doi.org/10.1594/PANGAEA.996842

Licence: CC-BY-4.0 https://creativecommons.org/licenses/by/4.0/

`PS155_10min.tsv` is the downloaded source, unmodified. `track.json` contains all 4,314 timestamp/position rows from the 10-minute product, including one missing speed/course pair as null. The PANGAEA metadata's 8,626 data points counts speed/course values and is NOT a count of positions. Source row times range from `2026-07-04T04:20` to `2026-08-03T03:04`; they are preserved without inventing seconds or a timezone. The event metadata has a different start timestamp and end seconds, not substituted for the actual row values.

Changes: TSV→JSON, display-only EPSG:3411 projection. Speed/course are the source's calculated 10-minute averages, not raw instantaneous measurements. This research expedition is NOT evidence of a commercial NSR transit or measured fuel savings.

## Sea ice

Meier, W. N., Fetterer, F., Windnagel, A. K., Stewart, J. S. & Stafford, T. (2024). Near-Real-Time NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration. G10016, Version 3. National Snow and Ice Data Center. https://doi.org/10.7265/j0z0-4h87 . Subset: northern hemisphere, 2026-01-15, every eighth grid center per axis. Accessed 2026-10-14.

Original metadata: `metadata.das`; original query result: `raw-2026-01-15.csv`; provenance: `provenance.json`; display data: `ice.json`.

Licence in original ERDDAP metadata: “No constraints on data access or use”. NSIDC requests the dataset citation above. V3 was retired in June 2026; its official coverage ends January 15, 2026. The ERDDAP catalogue advertises February 22 but our bounded February 21/22 requests returned only NaN. January 15 is the newest usable date checked, not an assertion that every later date was checked.

2,128 requested grid centers; 856 finite valid values; 1,272 missing omitted; zero out-of-range values. 526 of the finite values are 0 and 330 are positive. Native 25 km observations sampled with stride 8 = 200 km spacing, NOT a 200 km mean. Points are not contiguous ice coverage or a validated ice edge. Values below 10% are set to 0% by the source product, so 0 does not prove ice-free water. The map clips samples outside the displayed polar viewport.

Ice is OFF by default. January 15 ice is NOT current and NOT contemporaneous with July–August PS155. No safe-route, ice-class, icebreaker, delay, fuel, or risk inference is made. No combined track/ice training feature is created.

## Reproduction

From the application root:
- python scripts/prepare-arctic-observations.py
- python scripts/prepare-arctic-ice.py
- node scripts/check-arctic-observations.mjs

Rebuild scripts use only these preserved public inputs, not private data or network fetches. `sha256.txt` covers delivered public inputs/outputs in this directory. Regenerate it after deliberate dataset changes.

Coastline display derives from the application's existing Natural Earth simplified public-domain geometry. No new proprietary map source was added.
