# HRes Surface Comparison Report

- Output folder: `FILIPA_DADOS\results\validation_hres_surface_comparison_20260405_130636`
- Objective: compare two existing 300-image sets against HRes/refined branch evidence.

## HRes source selected
- Used `FILIPA_DADOS/data/Test_C4/Images/scene_1.gslib`, `scene_2.gslib`, `scene_3.gslib`.
- Why: each file contains 43200 cells (shape 180x240), consistent with HRes metadata in `results/netcdf_files_summary.csv`.
- Available comparable snapshots used: 3 (scene_1..scene_3).

## Main technical comparison
- `2024IB` is a wider, coarser regional grid (78x120) with CMEMS-scale bbox.
- `tempIBHRes2024_1.gslib` is a smaller local grid (64x112) mapped to HRes local bbox, not full HRes resolution.
- HRes scenes are 180x240 and align with HRes bbox metadata, indicating the refined local domain at higher resolution.

## Interpretation
- `2024IB` behaves as regional/zoom-out source.
- `tempIBHRes2024_1.gslib` is more HRes-like in geographic domain than `2024IB`, but appears to be a reduced-resolution local product (not full 180x240 HRes).
- Evidence is compatible with `tempIBHRes2024_1.gslib` being a transformed/downsampled local derivative rather than the complete HRes refined field.

## Files generated
- `tables/grid_comparison.csv`
- `tables/image_stats_selected_steps.csv`
- `panels/panel_compare_step_013.png`, `...014.png`, `...015.png`
- image subfolders for each dataset
- `manifest.json`

## Limitation
- Direct pixel extraction from `.nc` files was not used here; comparison relies on local GSLIB HRes scenes plus existing NetCDF metadata summaries in the repository.