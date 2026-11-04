# Apache 2.0 source-code scope

## What is licensed

Only the original project-owned software source code in the exact files listed
in [LICENSED_CODE.txt](LICENSED_CODE.txt) is licensed under the
[Apache License, Version 2.0](LICENSE).

This is a source-code grant, not a license for the repository as a whole.
The list contains literal repository-relative paths, not wildcard patterns.
An unlisted file is not covered by this grant. New paths require an explicit
scope review and list update. Existing ownership and contributor attribution
are unchanged.

Any third-party material in a listed file remains subject to its applicable
license and notices; this grant does not replace those terms or claim ownership
of it. Dependencies installed separately retain their own licenses.
The scope rules identify the covered work; they do not add restrictions to
Apache 2.0 for that covered work.

## Material outside this grant

This change does not license datasets, input images, comparison images, artwork,
screenshots, model weights or checkpoints, saved predictions, experiment
results, reports, manuscripts, handoff archives or ZIP contents under Apache 2.0.
In particular, `data/`, `results/`, `docs/`, `web/`, `notebooks/`, and unlisted
files under `research/` retain their existing status and applicable terms.
The README files, configuration/data manifests and research documentation are
not automatically included merely because they accompany the code.

Exclusion from this grant neither revokes an existing license nor creates a
new restriction. Where permission has not been established, repository
visibility, download availability, attribution or a checksum is not permission.
A code license does not supply permission to use or redistribute its input
data, trained models or protected outputs. No dataset condition is assumed
to transfer automatically to every independent statistic or original program.

## 한국어 요약

[정확한 파일 목록](LICENSED_CODE.txt)에 있는 프로젝트 자체 소스코드에만
[Apache 2.0](LICENSE)을 적용합니다. 저장소 전체, 데이터·이미지·가중치·연구
결과·문서·웹 및 아래 별도 항목까지 일괄 허가하는 것이 아닙니다.
기존 제3자 조건과 기여자 표기는 유지하며, 목록 밖 파일에 새로운 허가나
제한을 부여하지 않습니다.

## Preserved boundaries and notices

- `research/procurement_baseline/` and `tests/test_procurement_*.py` are outside
  this initial grant, including
  copied solvers and `provenance/reviewed_bundle.zip`. Its integration manifest
  records byte provenance, not a separate copyright license.
- The public Release asset `dqn_final.pt` under
  [official-eval-2026-09-01](https://github.com/heechan9/bunkering-ai/releases/tag/official-eval-2026-09-01)
  is outside this source-code grant.
- FuelCast source data retains its [CC BY-NC-ND 4.0 provider terms](https://huggingface.co/datasets/krohnedigital/FuelCast/blob/main/README.md).
  See [external-validation scope](research/external_validation/README.md).
  Related saved analyses and outputs are not included by this grant.
- Brest AIS has conflicting labels: the [record](https://zenodo.org/records/6402160)
  identifies CC BY 4.0, while its original ZIP READ_ME identifies CC BY-NC-SA 4.0.
  This change resolves neither the conflict nor rights in related data outputs.
- Global Fishing Watch source data retains its
  [CC BY-NC 4.0 terms](https://zenodo.org/records/14982712);
  [source records](research/public_vessel_linkage/results/source_manifest.json)
  and data/aggregate-use boundaries remain separate from software licensing.
- UPA, PANGAEA, Natural Earth, terrain, ONS and other external data retain their
  own provenance, attribution and terms. See
  [UPA](docs/data/upa_bunkering_anchorage.md),
  [Arctic observations](web/ocean-lab/public/data/arctic-observations/README.md),
  [terrain attribution](web/ocean-lab/public/data/terrain-attribution.txt)
  and [ONS source](data/route_stress/ons_source.json).
- [Private-vessel publication boundaries](docs/technical/hanbada_provider_clarification.md)
  are unchanged. The source-code grant does not republish or relicense vessel data.
- `scripts/build_source_catalog.py` identifies the FabGuard snapshot-build
  pattern it adapts. The [transfer record](docs/technical/fabguard_transfer_20261001.md)
  pins the [Apache-2.0 source revision](https://github.com/heechan9/fabguard-ai/blob/519654ea2362accf2127f4255a4379132402383c/LICENSE);
  its attribution and applicable notices remain in place.
- The excluded web tree contains separately noticed
  [OpenAI Sites Vite plugin code](web/ocean-lab/build/sites-vite-plugin.LICENSE)
  and [shadcn CSS](web/ocean-lab/vendor/shadcn-tailwind-4.13.0.LICENSE.md)
  under MIT. Their notices are unchanged.

Initial path selection is based on main
`e8d2da0040a37944e1bc546661920b8a961ae58a`.
This license-only change does not change source code, results, model files,
existing notices, attribution or release assets.
