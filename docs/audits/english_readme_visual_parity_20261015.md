# English README visual and table correspondence — October 15, 2026

Scope: documentation and English assets based on `8ea74a952c9d0fd60875bde152c5196e81d3b8da`. The Korean README, original images, official results, models, manuscript, and web application source are preserved. No new Korean diagram is uploaded, and no deployment or merge is performed by this change.

## Original images and English counterparts

| Korean README asset | English README asset | Treatment |
|---|---|---|
| `docs/assets/bunkering-project-hero.png` | `docs/assets/bunkering-project-hero-en.png` | Raster text localization using imagegen; headline translated to “Read the fuel. Navigate the voyage.” Existing English branding retained. Concept artwork, not evidence. |
| `docs/assets/bunkering-ai-decision-system-hero-v2.jpg` | Same original file | No Korean text to translate; reused with English alt text and conceptual/model-boundary caption. |
| `results/evaluation/comparison.png` | Same original file | Already English. Its source is `scripts/evaluate.py::plot_comparison`; panels and labels are English. Error bars are standard deviations, not confidence intervals. Original chart and data were not regenerated or edited. |
| `docs/assets/international-evidence-pipeline.jpg` | `docs/assets/international-evidence-pipeline-en.png` | Raster localization using imagegen: remove redundant Korean footer while preserving its English counterpart, four stages, and research limits. Caption limits the “not training” statement to the route-stress pipeline. Illustrative charts are not measured results. |
| `docs/assets/international-evidence-flow-ko.png` | `docs/assets/international-evidence-flow-en.png` | Raster localization using imagegen; retain seven boxes, split/merge arrows, frozen evaluation, 43-step sensitivity, and no-shock Hormuz control. Transparent background retained. |

All three English derivatives were inspected visually after saving. Labels fit, text is legible, and the main composition/semantic connections are retained; generative localization can redraw decorative details and is not pixel-identical. The generated diagrams must not be treated as experimental plots or actual UI screenshots. The original raster files remain available unchanged.

Flowchart labels: Public international sources → Suez/Cape route evidence → Synthetic 43-step sensitivity → Frozen Double DQN evaluation → Normalized metrics and claim boundaries. The right branch is Hormuz traffic context → Control without quantitative shock → the same frozen evaluation.

The original Mermaid workflow is translated in place in the English README. Its six nodes and six connections retain the same structure. All six badges have counterparts; historical test counts and evidence-audit scope remain explicitly dated.

## Table correspondence

The 13 original tables have 105 data rows. English counterparts preserve the original order, row counts, and table link targets. Numeric experiments remain separated by checkpoint/evaluation scope.

| Table | English counterpart | Data rows |
|---|---|---:|
| 1 | Research/development status | 30 |
| 2 | Problem, work, evidence, and practical relevance | 3 |
| 3 | Same-observation planner versus official DQN | 5 |
| 4 | Official single-checkpoint comparison | 4 |
| 5 | Adopted/deferred follow-up research | 5 |
| 6 | Stability across four independent training seeds | 4 |
| 7 | Four-checkpoint fuel-balance diagnostics | 6 |
| 8 | Data locations and authoritative versions | 6 |
| 9 | Models and reproduction materials | 2 |
| 10 | Operational-reference evidence | 4 |
| 11 | Historical verification records and scope | 5 |
| 12 | Repository structure | 13 |
| 13 | Documentation guide | 18 |

The existing English Quick start, Research boundaries, and Contributing and reuse sections are retained. The public checkpoint hash and synthetic-data limitations remain unchanged. No restricted original logs, private company/vessel/contact identifiers, correspondence, or manuscript content are added. Public source-study titles and public reference cases from the Korean README retain their existing scope.

## Authentic public-demo screenshots

Source: <https://bunkering-ocean-lab.hc24734503.chatgpt.site/> on October 15, 2026. The existing English button was present and selected; no UI implementation change was needed. Captures were made by Playwright controlling installed Chrome on the user's laptop in headless mode, viewport 1440 × 1080, device scale factor 1. The primary browser connector failed initialization, so this direct browser route was used. The rendered remote site was not modified, translated by DOM injection, or replaced with a local build.

- `docs/assets/ocean-lab-live-en-route-20261015.png`: full-page English region view, Strait of Hormuz, observation-only control, explanatory terrain and vessel paths, height exaggeration 8×.
- `docs/assets/ocean-lab-live-en-replay-20261015.png`: viewport capture of the baseline synthetic Double DQN record, training seed 42, market case 42, step 5 of 30. Fuel remaining is 75.0, cumulative consumption 25.0, purchases 0.0, and spending SCI 0.0k on the initial-fuel=100 scale. English replay was started; the visible step is the animation's capture-time state, not real voyage time.
- `docs/assets/ocean-lab-live-en-compare-20261015.png`: full-page English policy comparison. DQN values are the four-checkpoint mean (SCI 839,763, purchases 131.3, terminal fuel 81.3, refueling actions 4.90 on the UI's initial-fuel=100 scale). This is distinct from the official single-checkpoint SCI 847,118 / 5.31-action table. The original/reclassified threshold columns and caveats remain visible.

The deployment source commit and Sites version were not exposed or independently established. Repository commit `8ea74a9` identifies the documentation baseline, not the live site's deployed revision. The captured UI includes features beyond the historical Sites 36 description; no version is inferred from that observation. The screenshots document only the UI visible at capture time and can become historical as the public site changes.

The old September 27 Korean screenshot remains in its historical audit directory but is no longer the English README preview. These captures use public explanatory geography and synthetic experiment records only. They do not establish real-vessel safety, cost/fuel savings, navigation validity, or a calibrated physical model.

This session checks English rendering, navigation to the selected synthetic record, and comparison visibility. It does not repeat CSV/GLB downloads, shared-state restoration, responsive-width checks, physical-phone tests, iOS Safari, or operational validation. Previously documented tests retain their original dates and scope.

## Verification scope

- Compare all 13 table row counts (105 total) and 68 table source links with the Korean README.
- Compare numeric result cells and preserve the official chart/error-bar interpretation.
- Resolve local Markdown/image references and verify PNG integrity.
- Compare preserved English setup/boundary/reuse text and unchanged Korean README/original image bytes with Git HEAD.
- Inspect all generated English images and the three rendered public-demo captures visually.
- Run `git diff --check` and inspect the changed-file scope before commit.

This is a documentation-only change. No model training, evaluation rerun, model replacement, manuscript edit, web build, merge, or deployment is part of it. An exploratory import of the plotting module was blocked because the base Python environment lacked `gymnasium`; the existing English chart is reused without claiming a new evaluation or full Python test run.

Automated correspondence checks passed: 13 tables, 105 data rows, 68 table source links, 106 local references, numeric result cells, six preserved original files (Markdown compared with checkout newline normalization), and preserved English setup/boundary/reuse sections. All six new PNGs passed integrity checks; the flowchart has an alpha channel. [Machine-readable result and image hashes](english_readme_checks_20261015.json) · [Reproduction script](english_readme_20261015_check.py).

Run from the repository root with Python and Pillow installed:

```bash
python docs/audits/english_readme_20261015_check.py
git diff --check
```

The script compares against the fixed source revision `8ea74a9`; it is an audit for this documentation update, not an evergreen assertion that later Korean and English READMEs remain synchronized. `git diff --check` passed before commit. Original Korean images and the official chart also passed visual inspection; the English region, replay, and comparison captures were inspected after their final capture.
