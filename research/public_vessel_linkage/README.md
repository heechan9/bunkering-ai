# Public vessel linkage experiment

Source: Global Fishing Watch, Global AIS-based Apparent Fishing Effort Dataset v3 (2025 release), https://doi.org/10.5281/zenodo.14982712 . Attribution and usage conditions follow the publisher; read the included known-issues and schema documentation.

`acquire.py` downloads the full 2017 MMSI daily ZIP, all-years vessel table and three publisher readmes, verifies exact byte counts and MD5, and records SHA256. `experiment.py` selects 31 days matching DataBio ship1 calendar dates, 2017-09-30 through 2017-10-30 inclusive; audits unique MMSI/year registry joins and holds ambiguous registry keys. Inputs and extracted row-level data stay outside Git.

The public data are daily 0.1-degree cell aggregates, not raw AIS points, port arrivals or fuel observations. The vessel table contains MMSI and mixed registry/inferred properties, not IMO or vessel names. MMSI reuse/spoofing remains possible. DataBio ship1 lacks MMSI, IMO, coordinates or a vessel-name mapping; accepted DataBio vessel matches remain zero. Overlapping dates or similar engine power cannot establish identity. DataBio timezone is unconfirmed; overlapping date labels do not certify the same time interval.

Run `python research/public_vessel_linkage/acquire.py` then `python research/public_vessel_linkage/experiment.py` after placing the authorized DataBio source ZIP in research/fuel_source_review/inputs/. Requires pandas and requests. Source files and result directories are created by acquisition. Read results/linkage_audit.json and daily_join_summary.csv for executed counts. No operating model or fuel-saving claim is changed.
