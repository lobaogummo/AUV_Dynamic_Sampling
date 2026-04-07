# Visual Branch Comparison Report

- Output folder: `results/validation_visual_data_branches_20260405_193102`
- Scope: controlled visual+technical comparison only (no changes to clustering/pipeline core).

## Shared scales
- Thermal shared scale (2-98 pct): [15.6579, 18.0135]
- Uncertainty shared scale (2-98 pct): [0.0000, 0.3781]

## Key observations
- `Test_C4/Images/scene_*` and `Nazare/scene_*` are visually in the same family (180x240, metric-domain scene products).
- `tempIBHRes2024_1` is local-domain-like but lower spatial resolution (64x112) than scene/HRes-like products (180x240).
- `2024IB` remains wider/coarser regional reference (78x120) and is less scene-like in local HRes structure.
- By average similarity to `TestC4_scene_real`, best candidate was `tempIBHRes2024_1` (mean corr=0.861).
- By average similarity to `TestC4_scene_stdev`, best candidate was `Nazare_StDev` (mean corr=0.531).

## Recommended reference set (for next analyses)
- Primary visual/scientific HRes proxy: `data/Test_C4/Images/scene_1..3.gslib` (`Real` + `StDev`).
- Secondary consistency check: `data/Test_C4/Nazare_30-10-2024_1/scene_1..3.gslib`.
- Keep `tempIBHRes2024_1.gslib` as local derived branch baseline and `2024IB` as regional baseline.
