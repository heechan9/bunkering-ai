# 병커시유 · Ocean Lab

Private interactive 3D visualization of user-supplied synthetic baseline voyage records.

## What this experience does

- Replays 100 shared market cases for three rule policies and four Double DQN checkpoints (700 unique policy/checkpoint/case combinations).
- Provides orbit, zoom, voyage, vessel and normalized-fuel views; play/pause, speed, transition selection and individual bunkering-event navigation.
- Compares arrival, synthetic purchasing index, bunkering volume and terminal inventory with a raw/tolerance safety classification distinction.
- Exports the current concept vessel as a GLB model. Geometry is illustrative, not a ship design, digital twin or physical model.

Data is bundled from the provided baseline diagnostic CSVs: 30 steps, normalized consumption 0.05/step. No live APIs, private workstation paths, vessel identifiers, prices from actual purchase contracts, or credentials are exposed. Case seeds are 42–141. Rule repeats are deduplicated. Four checkpoint hashes are provenance declarations; model binaries were not supplied.

Scene geometry, distance, waves, apparent speed, cranes and ports are visual staging only. They neither change the recorded policy nor simulate port availability, weather, propulsion, fuel physics or geographic routes. The fuel tank is a normalized indicator, not a validated compartment layout.

## Evidence boundaries

Safe Stock's baseline raw post-transition violation at 0.1499999999999997 vs 0.15 is a floating-point threshold effect. Tolerance reclassification uses 1e-12 on the existing trace, not a new rollout. DQN higher final inventory and SCI are reported without claiming cost-saving or practical safety superiority. FuelCast is not used.

Source review: https://github.com/heechan9/bunkering-ai/pull/44
Documentation/evidence commit: 8467fd106d33b4afa7abca6a632b0062e7ca4b58

## Rendering and validation

Three.js WebGL rendering with an SVGRenderer compatibility path using the same 3D scene graph and perspective camera. Compatibility mode simplifies small details and renders on state/camera changes. The local review browser has WebGL disabled, so compatibility rendering and UI are visually checked; GPU rendering is build-checked, not visually verified in that browser. Mobile layout uses responsive CSS; no separate mobile device run is claimed. WebMCP is feature-detected but unavailable in the review browser, so its runtime validation remains unverified.

Use the site's package manager and existing scripts for builds. Publishing is managed by Sites; .openai/hosting.json identifies the site.


## Geographic exhibit and plain-language revision

The experience now opens with Hormuz terrain, followed by the original recorded-voyage replay and policy comparison. The geography viewer is context only: no geographic position, waterway selection, distance or map height enters the policy data. No ship is plotted on the geographic map; the synthetic vessel remains in its separate illustrative harbor scene.

Coastlines use the official Natural Earth 1:10m land GeoJSON (public domain), clipped and simplified for seven regions. `public/data/coastlines.json` records the input URL, SHA-256 and processing. `scripts/prepare-coastlines.py` is a dependency-free reproducer. It accepts a local source GeoJSON file. Approximate place-label anchors are descriptive, not navigation coordinates. The current terrain revision adds a separate display DEM, described below. No bathymetry, shipping-lane alignment, port availability or real-world fuel data is added.

The source feed is https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson and the documentation/license pages are https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/ and https://www.naturalearthdata.com/about/terms-of-use/. Geographic context is linked to the Suez Canal Authority and EIA within the exhibit.

For accessibility to non-specialists, policy names include Korean descriptions, recorded transitions have an event explanation, and fuel amounts are displayed as original normalized value × 100. This is only a display conversion: `replay.json`, the original reward/safety accounting and model outputs remain unchanged. SCI retains its original numeric definition; k means 1,000. Detailed definitions are expandable in the replay panel. A visible start control is provided above the replay and on its timeline.

The current guided-flow revision makes the three-step experience explicit: choose a geographic context, open one verified baseline replay, then compare policies under the shared condition. The replay panel now shows an instructional state before results, labels broad voyage phases, and resets the 3D camera on demand. Replay speed remains presentation-only, while vessel motion between the 30 recorded transitions is visual interpolation rather than measured time or speed. The selected strait remains geographic context and does not alter the baseline replay.

Revision validation: production build; geographic bounds and named land/water anchor checks; desktop compatibility-rendered Suez and Hormuz views; region selection; transition-10 DQN purchase 45.0/final 95.0 on the 100 scale; navigation into the comparison table; unchanged bundled experiment data. GPU terrain and mobile-device rendering have not been visually verified. Existing browser WebMCP remains unavailable. This revision makes no new scientific performance claim.

Cross-review request: assess whether a first-time visitor understands the relationship between fuel purchasing, consumption and remaining inventory; whether the geography is mistaken for a real-voyage replay; and whether the scene, labels and comparison are legible. For another AI project, use this as a presentation reference, but visualize that project's own verified data and preserve its model boundary.

## Regional evidence explorer

Seven explicit region buttons appear above the map (two columns on small screens):
Suez, Hormuz, Taiwan, Bab-Al Mandab, Cape of Good Hope, Dover and Ulsan.
The first six are the coverage of the ONS 2024-04-24 dataset referenced by the
Bunkering-AI route-stress provenance. Dataset coverage is not a claim that six
regions were individually evaluated, or that their traffic observations trained DQN.

- ONS coverage confirmed from https://www.ons.gov.uk/businessindustryandtrade/internationaltrade/datasets/weeklyshipcrossingsbyshiptypethroughsixglobalmaritimepassages
- Suez/Cape: one representative horizon assumption; Singapore–Rotterdam distance comparison.
- Hormuz: unchanged contextual control, not closure or rerouting simulation.
- Taiwan, Bab-Al Mandab, Dover: source coverage / traffic context only.
- Ulsan: UPA 6,028 application records for descriptive reference, not linked purchase/consumption/ROB telemetry. https://www.data.go.kr/data/15132700/fileData.do
- Research use checked against Bunkering-AI main `docs/technical/route_stress_minimum_slice.md` (blob 8b9c8a5a95b5ca245420a63edb151e2321185f69) and `docs/data/upa_bunkering_anchorage.md`.

Natural Earth coastlines are cropped to all seven regions. The separate DEM is a display layer: Ulsan is not a berth/anchorage chart, and Suez is not an engineered
canal alignment. Selecting a geographic view does not alter experiment records.
No new traffic numbers or raw ONS data were added. The existing replay and
experiment provenance files are unchanged.

Validation: production build; browser region switching for all seven views;
visual checks of Hormuz, Taiwan and Ulsan using the compatible renderer. Actual
mobile hardware and the GPU rendering path were not exercised in this run.

## Globe-to-region navigation

An interactive orthographic globe remains available under “전체 위치 보기”. The initial view is now Hormuz terrain. Natural Earth
land is simplified by `scripts/prepare-world.py`, then projected with d3-geo.
This is a spherical geographic visualization, not measured topography or a
new simulation environment. There are no elevation, country-boundary or shipping
lane datasets in this view. Continent labels provide orientation; country labels
remain in the regional coastal views.

Users can drag or use keyboard/rotation buttons, choose continent viewpoints,
select any of the seven regional markers or buttons, and move through an animated
regional focus into the existing coastal map. The world-map button returns to the
globe. Reduced-motion preferences skip the camera animation. No experiment,
replay or regional coastline records were changed.

Verified in the browser: globe land rendering, rotation, continent selection,
animated Hormuz and Taiwan entry, return to world and onward replay navigation.
Fixed server/client SVG coordinate precision and single-string title rendering
before validation. Actual mobile hardware was not exercised.

## Measured-elevation geographic display (current revision)

All seven regional views use Mapzen / AWS Terrain Tiles, decoded from Terrarium RGB into metres. `scripts/prepare-terrain.py` resamples onto a 257×257 north-to-south geographic grid (bilinear interpolation, whole metres), retaining original sampled heights separately from the Natural Earth land mask. Regional JSONs include source tile URLs and SHA-256 digests. This display resolution is not the native DEM resolution or a survey accuracy claim. The reproducer uses Python NumPy and Pillow; neither adds a browser dependency.

Horizontal scale uses an equirectangular approximation at the region's centre latitude (111,320 m per latitude degree). Vertical scale uses the same metres conversion times 1, 4, 8 or 12; the default 8× is visibly labelled. Colour is an elevation ramp, not imagery or vegetation. Negative land elevations and ocean values are clamped to zero only for rendering. No bathymetry is shown. Coastline simplification and masking can omit small coastal detail; this is not a navigation chart. The lower-detail SVG compatibility mesh samples every second grid point (129×129), whereas WebGL uses the full 257×257 grid.

The globe remains a locator. DEMs are not fed into BunkeringEnv, policies, routes or the recorded experiment. This revision adds geographic context and no new experiment, digital twin or real-world performance claim. Attribution and processing details are visible via `public/data/terrain-attribution.txt`. Primary source documentation: https://registry.opendata.aws/terrain-tiles/ and https://github.com/tilezen/joerd/blob/master/docs/formats.md.

Terrain revision validation: Hormuz compatibility rendering and 1×/8× selection were visually checked. A shared preview was replaced by another active Site during later regional checks, so no all-region browser or GPU/mobile-device verification is claimed. Production build and regional geometry/data checks are recorded separately. The retained globe and experiment replay are unchanged in their data and logic.

Data/geometry checks passed for all seven regions: exact coastline/DEM bounds agreement, grid dimensions and finite elevations, binary land masks, north-to-south orientation, nonempty land meshes, finite normals and 1×→8× vertex-height scaling in full and reduced meshes. Verified 285 downloaded source-tile SHA-256 digests. `replay.json`, `provenance.json`, `coastlines.json` and `world-land.json` remain byte-identical to the preceding source revision.
