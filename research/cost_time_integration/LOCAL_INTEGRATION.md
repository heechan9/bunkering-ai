# Cost/time integration on merged main (2026-10-17)

This note describes the new integration candidate. README.md, FOLLOWUP.md,
STATIC_REVIEW.md, validation_results.json, and followup_results.json are preserved
historical source evidence, not current-main verification claims. All original
review reports, including timing-test failures and the historical full-suite
counts, remain unchanged inside provenance/reviewed_bundle.zip.

## Scope and provenance

- Base: main 984411c436f16c555cfb8d789d43de8025e2df66, after procurement integration.
- Imported only the original archive's source/research/cost_time_integration tree.
- Replaced ledger.py with the exact reviewed guard-v2 candidate and imported its
  direct-ledger regression tests, boundary characterization tests, and frozen replay.
- No archive procurement dependencies or Windows compatibility overlays were
  applied. Current procurement, port-call timing, web, and existing frozen results
  are unchanged.
- Original review archive SHA256:
  6767e207a93378925959171056574e9ea0ae6d6726ecc9f0790abf584eba8e9f.
- Guard-v2 archive SHA256:
  6ac9d5516e13b96a74a06a73efb420c2df6fced9039ec935b469e73d21b78285.
- Both archives are preserved under provenance/. All 95 original and 19 guard
  manifest members were verified. integration_manifest.json maps each imported
  file to its archive member, original hash, and integrated hash.
- The package-local .gitattributes preserves original bytes, including historical
  CRLF evidence. No frozen fixture, expectation, or saved result was regenerated.

## Integration-only test harness fix

The guard scripts use generated stdlib unittest methods. They left the final
helper named test(self) in module scope. Pytest collected that helper as an extra
standalone test and could not resolve its self fixture. The initial focused run
had 481 passing tests and two setup errors.

Each integrated script now deletes only this leftover module-level binding after
registering every method on its TestCase. All class tests remain intact: direct
unittest execution still runs 187 numeric/container regressions and 8 boundary
characterizations. Archived originals remain byte-for-byte unchanged. Production
ledger and solver code needed no integration changes.

## Meaning and limits

This is a synthetic fixed-route research adapter, not operational validation.
The independent ledger checks numerical inputs and sequential accounting; it is
not a complete schema, unit, or precision-grid validator. Guard rejection of
unknown timing, including unused calls, is intentional and does not impute zero.

Existing reserve indexing, monetary/time formulas, and tolerances are unchanged.
At deadline 26.32 - 5e-7 hours, the solver returns INFEASIBLE while the ledger
accepts the baseline witness within its 1e-6-hour tolerance. A valid ledger result
therefore does not assert exact solver feasibility. Floating-point LP results are
not rational optimality certificates; the ledger does not prove optimality.

## Reproduction without overwriting evidence

Run from the repository root with a compatible Python/SciPy environment:

    python -m research.cost_time_integration.replay_frozen_cases > /new/path/frozen_replay.json
    python -m unittest research.cost_time_integration.test_ledger_case_validation
    python -m unittest research.cost_time_integration.test_boundary_characterization
    python -m pytest research/cost_time_integration -q --strict-config --strict-markers -W error
    python -m pytest -q --strict-config --strict-markers -W error

Do not delete or overwrite validation_results.json or followup_results.json to
run the original write-once runners. The replay prints fresh evidence to stdout.
Fresh verification results and environment are recorded separately in
integration_verification.json; historical counts must not be added to fresh totals.
