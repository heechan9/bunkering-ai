# Bunkering-AI | 병커시유

[한국어](README.md) | **English**

**A reproducible research project for sequential ship-refueling decisions.**

Bunkering-AI compares three rule-based policies with Double DQN in a synthetic voyage environment. It examines when to refuel, how policies balance fuel availability and purchase cost, and whether a higher learning reward translates into a useful operational outcome.

[Ocean Lab demo](https://bunkering-ocean-lab.hc24734503.chatgpt.site/) · [Repository](https://github.com/heechan9/bunkering-ai) · [Quick start](#quick-start) · [Evidence and results](#evidence-and-results) · [Research boundaries](#research-boundaries)

> Research prototype. Results describe specified synthetic experiments, not demonstrated fuel savings, monetary savings, or safety certification for real ships. The official DQN remains unchanged; experimental alternatives are evaluated separately.

This English entry point summarizes the repository reviewed at [`c98304b`](https://github.com/heechan9/bunkering-ai/tree/c98304b00158d3cb56891bdc6a42f8f600ae315b). The [Korean README](README.md) and linked technical records contain the fuller development history. Many linked documents are in Korean; Ocean Lab supports Korean and English interface text.

## Why this project exists

Refueling is a sequence of decisions: buying earlier may provide more fuel margin, but also changes purchase cost and remaining inventory. A policy cannot be judged by reward or purchase cost alone. This project asks:

1. Does the policy reach the destination without fuel depletion?
2. Are policy differences reproducible under identical seeds and environment settings?
3. What changes when safety reserves, terminal fuel inventory, and time assumptions are considered explicitly?

The core workflow is **synthetic market and voyage state → policy action → common evaluation → traceable CSV, manifest, and diagnostic results**.

## What is implemented

- **Shared simulation and evaluation:** a Gymnasium `BunkeringEnv`, three rule-based baselines, a PyTorch Double DQN agent, and a common evaluation contract.
- **Traceable accounting:** purchase quantity, consumption, remaining fuel, refueling actions, Synthetic Cost Index (SCI), checkpoint hashes, and source-linked experiment records.
- **Ocean Lab:** bilingual explanations, regional geographic views, recorded-voyage replay, purchase-plan comparison, and source inspection. Geographic displays are explanatory; choosing a region does not change the baseline evaluation.
- **Separate research modules:** route-stress and consumption sensitivity, same-observation planner comparison, shadow recommendations, and incremental port-call time with explicit missing-data handling.
- **Data review tools:** voyage CSV validation, fuel-balance checks, public-source inventories, and checks against official experiment outputs.

The core action space is limited: action 0 skips refueling; positive actions request a fixed quantity, capped by available tank capacity. Although action labels include port IDs, the baseline does not implement different prices or transition dynamics for individual ports. It does not establish optimal port selection or variable-quantity bunkering. See the [environment code](envs/bunkering_env.py) and [model boundary](docs/technical/model_boundary_and_research_roadmap.md).

## Synthetic experiments and real-world reference data

These sources have different roles and should not be combined into one validation claim:

| Source | Role | What it does not establish |
|---|---|---|
| Synthetic market and voyage environment | Training and official policy evaluation | Measured vessel fuel consumption or operational savings |
| Ulsan Port Authority public anchorage applications | Descriptive review of operational fields and distributions | DQN training data, official performance validation, or a live port API |
| Public international datasets and literature | Documented context, scenario assumptions, and separate exploratory studies | A calibrated, integrated model of a specific vessel or route |
| Non-public operational records | Restricted source review and identification of missing measurements | Publicly reproducible real-vessel policy effectiveness |

The public UPA application dataset contains 6,028 rows. Its provenance and limitations are recorded in the [data documentation](docs/data/upa_bunkering_anchorage.md). External-source decisions are documented separately in [adopted and deferred research uses](research/external_validation/DECISIONS.md).

Private operational logs, identifiable correspondence, confidential vessel/company details, and the final submitted manuscript are not included in this English overview. Access to research data does not imply permission to redistribute it. Public availability of this repository is not a claim that its entire historical Git record has been privacy-audited.

## Quick start

### 1. Set up Python

The project documents Python 3.11 for the research setup. The separate automated CPU test workflow uses Python 3.12; see [CI environment and reproduction notes](docs/technical/python_ci.md).

```bash
git clone https://github.com/heechan9/bunkering-ai.git
cd bunkering-ai
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in Windows PowerShell, then install the research dependencies:

```bash
python -m pip install -r requirements.txt
```

The general research requirements are not version-pinned. For the repository's pinned CPU regression-test setup, follow [`requirements-ci.txt`](requirements-ci.txt) and the [workflow](.github/workflows/python-tests.yml), including its separate PyTorch installation step. Record the code commit and dependency versions for any new experiment.

### 2. Reproduce the official evaluation without retraining

Download `dqn_final.pt` from the [official checkpoint release](https://github.com/heechan9/bunkering-ai/releases/tag/official-eval-2026-09-01). Create `checkpoints/` if needed and save the file as `checkpoints/dqn_final.pt`.

Verify its SHA-256 before use:

```text
970aafbf2d32e9bef558a5611a300cd0885f826af2c872a83119a6e9fcbcf392
```

The [official evaluation guide](docs/technical/official_evaluation.md) provides Bash and PowerShell download/hash-check instructions. From the repository root, run:

```bash
python scripts/evaluate.py --episodes 100 --seed 42 --checkpoint checkpoints/dqn_final.pt --output-dir results/local_reproduction
```

Outputs include `evaluation_results.csv`, `evaluation_manifest.json`, and `evaluation/summary.csv` under `results/local_reproduction/`. Use a separate output directory to preserve the committed reference results. Retraining does not guarantee the same weights; use the published checkpoint to compare against the official numbers.

### 3. Run tests and the evidence audit

```bash
python -m pytest -q
python -m scripts.audit_paper_evidence
```

The evidence audit checks the repository's official artifacts and claims; it does not automatically audit the separate local reproduction directory. A passing software test or evidence audit does not validate real-world ship performance. Historical test counts apply to their recorded commits, not automatically to the latest `main`.

### 4. Run Ocean Lab locally

Use Node.js **22.13 or newer** and **pnpm 11.25.0**, as specified in the [web package](web/ocean-lab/package.json).

```bash
cd web/ocean-lab
pnpm install --frozen-lockfile
pnpm dev
```

Open the local URL printed by the development server. `pnpm build` creates a production build. See the [web setup and deployment notes](web/README.md). A GitHub push does not automatically deploy the public demo, and the demo should not be assumed to match every change on `main`.

## Evidence and results

### Official baseline: one checkpoint, 100 synthetic voyages per policy

The official comparison uses the DQN trained with seed 42 and the same evaluation seeds 42–141 for every policy. Source of record: [raw results](results/evaluation_results.csv), [summary](results/evaluation/summary.csv), and [evaluation manifest](results/evaluation_manifest.json).

| Policy | Mean reward | Mean SCI | Arrival rate | Fuel-depletion rate | Mean refueling actions |
|---|---:|---:|---:|---:|---:|
| Fixed Fueling | −2.030 | 0 | 0% | 100% | 0.00 |
| Price Reactive | −1.952 | 17,370 | 3% | 97% | 0.08 |
| Safe Stock | −0.493 | 545,393 | 100% | 0% | 1.00 |
| Double DQN | 0.044 | 847,118 | 100% | 0% | 5.31 |

Double DQN has the highest mean reward in this experiment, but also a higher purchase SCI and more refueling actions than Safe Stock. A failed policy's low purchase SCI is not evidence of an effective strategy. SCI is an internal index based on normalized fuel quantity, synthetic price, and exchange rate; it is not a USD/KRW expense. Refueling actions are not measured port calls.

Arrival and depletion are also different from maintaining a reserve throughout a voyage. The [safety-accounting audit](docs/technical/safety_accounting.md) separately examines fuel before refueling and terminal inventory value. In that audit, DQN and Safe Stock have no shared cases satisfying the full-voyage reserve criterion, so a safety-conditioned cost advantage between those two policies is not established.

### Later comparison: same-observation planner and the official frozen DQN

A separate evaluation compared `planner_ops` with the published DQN on 1,000 fresh cases at execution time, using seeds 50,000,000–50,000,999. This study does not replace the original 100-voyage baseline.

- Safe arrivals: planner **1,000/1,000**, DQN **999/1,000**; paired difference **+0.1 percentage points**, 95% interval **[0, +0.3]**.
- Inventory-adjusted SCI on the 999 jointly safe cases: planner relative difference **−0.0038%**, 95% interval **[−0.0786%, +0.0690%]**. The specified cost non-inferiority criterion was met; a cost-saving advantage was not established.
- Synthetic deadline criteria favored the planner, but depend on the assumed 24-hour sailing steps, 8-hour stops, and port-call tie-breaking. The DQN does not observe the deadline. These are not measured voyage-time improvements.

The automated label `REPLACEMENT_EVIDENCE_SUFFICIENT` means the study's specified synthetic gates passed. It is not operational deployment approval, and the official DQN remains in place. These evaluation seeds are now used data and must not be reused as an independent confirmation set after candidate tuning. See the [evaluation report](research/fair_replacement_eval/OFFICIAL_EVALUATION_20261007.md) and [summary artifact](research/fair_replacement_eval/results/official_20261007_a3/summary.json).

### Additional research, kept separate

| Research | Current evidence and boundary |
|---|---|
| [Four independent training seeds](docs/technical/multiseed_results_4seed.md) | Stability and paired route-stress results within the synthetic environment; separate from the single-checkpoint baseline |
| [Fuel-balance diagnostics](docs/technical/reward_diagnostics_results_4seed.md) | Additional purchases, consumption, terminal inventory, and reward must be interpreted together |
| [Consumption and horizon sensitivity](docs/technical/v1_5_results_4seed.md) | Frozen-checkpoint robustness under specified synthetic shocks; no measured fuel-saving claim |
| [Route-stress scenarios](docs/technical/route_stress_minimum_slice.md) | Suez/Cape representative horizon assumptions; Hormuz is a contextual control without a quantitative shock |
| [External validation](research/external_validation/README.md) | Separate data adaptations and candidate comparisons; official model replacement remains deferred |
| [Shadow recommendation mode](research/fair_replacement_eval/SHADOW_MODE.md) | Logs planner recommendations while preserving DQN actions; research isolation is not live operational integration |
| [Incremental port-call time](research/port_call_time/README.md) | Distinguishes concurrent bunkering during an existing call from dedicated calls; unknown inputs stay unknown; real-data calibration remains incomplete |

## Research boundaries

- **No demonstrated real-world savings.** Matched records of purchases, remaining-on-board fuel (ROB), consumption, prices, and constraints are still needed for operational evaluation. Observational reconciliation alone would not establish a causal policy benefit.
- **Limited baseline physics and operations.** Normalized fuel dynamics are not a vessel-calibrated engine model. Live AIS, weather, port availability, and port-specific supply constraints are not integrated into the official baseline.
- **Reward is not cash savings.** The historical `fuel_cost_saving` reward field is a price-advantage proxy. Purchase SCI, inventory-adjusted SCI, safety, and learning reward answer different questions.
- **Maps are not navigation tools.** Geographic layers, schematic paths, and ship animation do not turn synthetic replay into an observed voyage or operational digital twin.
- **Time models have separate scopes.** Bunkering work duration does not equal extra voyage delay when work overlaps cargo operations. The newer port-call module does not retroactively validate or change the official evaluation's time assumptions.
- **Software verification has a defined scope.** Recorded browser checks and test counts apply to their documented versions. Physical-device and operational validation should not be inferred from build success.

See the [model boundary and research roadmap](docs/technical/model_boundary_and_research_roadmap.md), [operational-validation roadmap](docs/technical/causal_operational_validation.md), and [project history](docs/PROJECT_STATUS.md).

## Repository map

| Path | Purpose |
|---|---|
| `agents/` | Double DQN agent and neural network |
| `envs/` | Gymnasium bunkering environment |
| `configs/` | Training and environment configuration |
| `evaluation/` | Shared result contract and accounting/evidence checks |
| `scripts/` | Training, evaluation, baseline, and data-review entry points |
| `route_stress/` | Source-documented scenario assumptions |
| `results/` | Public experiment outputs and provenance |
| `data/public/` | Public reference data |
| `research/` | Separately scoped exploratory studies and comparison tools |
| `tests/` | Regression tests |
| `web/ocean-lab/` | Ocean Lab application source |
| `docs/` | Technical contracts, data notes, audits, and history |

## Contributing and reuse

Read [CONTRIBUTIONS.md](CONTRIBUTIONS.md) for human/AI attribution and review principles. For research changes, state the hypothesis, data provenance, evaluation contract, and limitations; keep new outputs separate from official reference artifacts.

No top-level project license is present in the reviewed revision. This README does not grant a new license. Third-party code and datasets retain their own notices and terms; do not infer their reuse permissions from repository visibility.
