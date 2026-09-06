# Final Independent Audit Report: heechan9/bunkering-ai

**Audit Date:** September 5, 2026
**Auditor:** Jules (Independent Senior Software Engineer)
**Target Repository:** `heechan9/bunkering-ai`
**Overall Status:** **PASS**

---

## 1. Audited Commit SHA and Execution Environment

- **Main Branch Commit SHA:** `9a4ac01d4e11b0808204f5b2a6dace02c7ad2911` (incorporating PR #24 and PR #25)
- **Python Version:** Python 3.12.13
- **Operating System:** Linux devbox `6.8.0-2026-x86_64` (#1 SMP PREEMPT_DYNAMIC)
- **Key Dependencies:** `gymnasium` 1.3.0, `pandas` 3.0.5, `numpy` 2.5.2, `torch` 2.14.0, `pytest` 9.1.1

---

## 2. Integrity Verification of Official Artifacts and PR #24 Changes

An inspection of commit history and git diffs for PR #24 (`6095359f76f0a8a4be01895ee6ce215e30dd1f4d`) and PR #25 (`9a4ac01d4e11b0808204f5b2a6dace02c7ad2911`) was conducted against canonical repository files:

- **Canonical Official 100-Seed Artifacts:** Files in `results/evaluation/` (`raw_double_dqn.csv`, `raw_fixed_fueling.csv`, `raw_price_reactive.csv`, `raw_safe_stock.csv`, `summary.csv`, `termination_reasons.csv`, `comparison.png`), `results/evaluation_results.csv`, and `results/evaluation_manifest.json` were **not modified** by PR #24 or PR #25.
- **Model and Checkpoint Integrity:** Model definitions in `agents/dqn.py` and `agents/__init__.py` were untouched. Official checkpoint reference SHA-256 (`970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392`) remains valid and untampered.
- **Environment & Reward Logic:** `envs/bunkering_env.py` and reward logic remain unchanged.
- **Public Dataset:** `data/public/upa_bunkering_anchorage_20240819.csv` (SHA-256: `b42537ebde057e87ef15f91a8c0fca6ab0ee010ff557b78a531112d4e79da1b7`) was unmodified.

---

## 3. Re-run and Verification of 200-Seed Rule-Based Robustness Evaluation

The independent 200-seed evaluation was executed via `python3 scripts/robustness/script2_baseline_200seed_eval.py`:

- **Execution Scope:** 3 strategies (`fixed_fueling`, `price_reactive`, `safe_stock`) × 200 seeds (seeds 42 to 241 inclusive) = **600 unique policy×seed cases**.
- **Mutual Consistency:**
  - `results/robustness/independent_eval_raw_with_episode.csv` contains exactly 600 episode rows.
  - Re-computed summary metrics (mean/std_ddof0 for reward, Synthetic Cost Index, success, fuel depletion, bunkering count, and termination reason counts) from raw CSV match `results/robustness/independent_eval_summary_final.csv` exactly.
  - Cumulative stability windows (20, 50, 100, 150, 200 seeds) in `results/robustness/independent_eval_stability_final.csv` match prefix aggregations of the raw dataset.
  - `results/robustness/independent_eval_manifest.json` lists all 600 policy×seed cases and matches configuration metadata.

---

## 4. Exact Episode Match for Overlapping Seeds (42-141)

For the 100 seeds (seeds 42–141, 300 policy×seed episodes) shared between the official 100-seed evaluation and the 200-seed robustness run:

- **Fixed Fueling:** 100/100 episodes matched official artifacts byte/float-identical (Reward: -2.030, SCI: 0.0, Bunkering Count: 0, Termination: `fuel_depleted`).
- **Price Reactive:** 100/100 episodes matched official artifacts byte/float-identical across Reward, Synthetic Cost Index, Bunkering Count, and Termination Reason.
- **Safe Stock:** 100/100 episodes matched official artifacts byte/float-identical (Reward mean ~ -0.493, SCI mean ~ 545,393, Bunkering Count: 1.0, Termination: `arrived`).
- **Conclusion:** Zero mismatches across all 300 overlapping policy×seed episodes.

---

## 5. Script Verification & Public-Data Tamper Resistance Test

Both scripts under `scripts/robustness/` were executed directly from the repository root:

- **Automated Directory & Direct Writing:** `script2_baseline_200seed_eval.py` creates `results/robustness/` if needed and writes all 4 artifacts directly without requiring manual file moving. Re-running `script2` reproduced committed artifacts in place with clean `git status`.
- **Public-Data SHA-256 Verifier Test:** `script1_public_data_verification.py` computes the runtime SHA-256 hash using `hashlib`. To verify tamper detection, a temporary script with corrupted data input was executed. It raised `FATAL: SHA-256 mismatch` and exited immediately with non-zero exit code **1**, refusing to proceed with analysis.

---

## 6. Test Suite and Paper Evidence Audit Execution

The full repository test suite and paper-evidence audit script were executed:

- **Pytest Suite Command:** `python3 -m pytest`
  - **Results:** 144 passed in 15.95s
  - **Exit Status:** `0`
- **Paper Evidence Audit Command:** `python3 -m scripts.audit_paper_evidence` (or `PYTHONPATH=. python3 scripts/audit_paper_evidence.py`)
  - **Results:** 8 total claims evaluated, 8 passed, 0 provisional, 0 missing evidence, 0 failed
  - **Exit Status:** `0`
  - **Output Artifacts:** Generated `results/paper_audit/paper_evidence_summary.csv` and `results/paper_audit/paper_evidence_report.json`.

---

## 7. Technical Documentation Distinction

`README.md` and `docs/technical/official_evaluation.md`, `docs/technical/rulebased_robustness.md` clearly distinguish:
- The **official 100-seed four-policy comparison** (`fixed_fueling`, `price_reactive`, `safe_stock`, `double_dqn` over seeds 42-141) as the canonical benchmark result.
- The **auxiliary 200-seed Rule-based robustness check** (over seeds 42-241) as an independent appendix that does not alter or replace the canonical 100-seed benchmark.

---

## 8. Verification of Reported Claims, Numbers, and Disclaimers

All numbers in `README.md` and documentation were checked against canonical CSV artifacts:

- **Official Results Table in README:**
  - Fixed Fueling: Reward `-2.030`, SCI `0`, Success `0%`, Fuel Depletion `100%`, Bunkering `0.00`
  - Price Reactive: Reward `-1.952`, SCI `17,370`, Success `3%`, Fuel Depletion `97%`, Bunkering `0.08`
  - Safe Stock: Reward `-0.493`, SCI `545,393`, Success `100%`, Fuel Depletion `0%`, Bunkering `1.00`
  - Double DQN: Reward `0.044`, SCI `847,118`, Success `100%`, Fuel Depletion `0%`, Bunkering `5.31`
- **Scope & Overclaim Boundary Check:**
  - No claims implying real monetary savings. (Synthetic Cost Index explicitly documented as an internal synthetic environment metric).
  - No claims implying real-vessel validation or operational deployment. (Explicitly disclaimed as offline simulation in synthetic environment).
  - No claims asserting universal Double DQN superiority. (README explicitly states that higher reward comes with higher bunkering count and higher Synthetic Cost Index, disclaiming universal superiority).

---

## 9. Mobile Links, Media Paths, and Section Structural Integrity

- **README Navigation:** Uses mobile-compatible relative file links (`docs/technical/official_evaluation.md`, `docs/data/upa_bunkering_anchorage.md`, `docs/technical/evaluation_contract.md`, `docs/technical/state_action_reward_spec.md`).
- **Media Asset Paths:** All referenced images (`docs/assets/bunkering-project-hero.png`, `docs/assets/bunkering-ai-decision-system-hero-v2.jpg`, `results/evaluation/comparison.png`, `results/public_data/upa_bunkering_reference_summary.png`) exist and render correctly.
- **Section Structure:** Follows Research Question -> Method/Validation -> Official Results -> Discussion/Interpretation -> Limitations.

---

## 10. Reproducibility, Stale Paths, and Code Quality Review

- All script execution paths are relative to repository root and free from hardcoded absolute or local paths.
- No manual file moves or hidden setup steps are required.
- Test coverage protects environment mechanics, agent logic, evaluation contracts, public data analysis, robustness scripts, and claim verifications.

---

## Summary of Findings

| Severity | Count | Summary |
|---|---:|---|
| **Critical** | 0 | None |
| **High** | 0 | None |
| **Medium** | 0 | None |
| **Low** | 0 | None |

### Verified Facts
1. Main branch commit `9a4ac01d4e11b0808204f5b2a6dace02c7ad2911` passes all automated tests (144/144) and paper evidence audits (8/8).
2. PR #24 introduced 200-seed robustness testing without altering any official 100-seed evaluation artifacts or core system logic.
3. Overlapping seeds 42-141 produce 100% identical results between official and robustness harnesses.
4. Public data verifier enforces runtime SHA-256 integrity and fails loudly on data modifications.
5. All public claims adhere strictly to verified, unexaggerated simulation boundaries.

### Inferred Risks
- *Environment Dependency:* Re-running `script1` or `script2` requires `gymnasium` and `pandas`. Standard `pip install -r requirements.txt` fulfills all requirements.

### Recommendations
- Maintain the current automated pre-commit and paper evidence audit scripts for future PRs.

---

**Final Audit Conclusion:** **PASS** (No codebase modifications required).
