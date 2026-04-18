# tempIBHRes Indexed-Axes Fix Report

## Summary
This fix updates presentation for figures derived from `tempIBHRes2024_*` to indexed axes only.
No clustering, prototypes, compact model, descriptors, planner, or cost-function logic was changed.

## Final Convention Adopted
- `tempIBHRes2024_*` figures: `X index` / `Y index`
- Coordinate mode in metadata: `indexed_grid_from_gslib_xy`
- Methodological note:
  - Figures derived from `tempIBHRes2024_*` are shown in indexed grid coordinates (`X index`, `Y index`), since independently verified native georeferencing of this reduced product is not established in the current repository state.

## Corrected Scripts
- `scripts/Old_Code/export_surface_2024_300_images.py`
- `scripts/Old_Code/01b_export_normalized_surface_pngs.py`
- `scripts/12_fix_tempibhres_indexed_axes.py` (indexed-axis generation for tempIBHRes auxiliary validation artifacts)
- `scripts/12_fix_tempibhres_display_mapping_labels.py` (legacy filename copy currently kept for compatibility in this workspace)
- `docs/THESIS_FIGURE_CONVENTIONS.md`

## Regenerated Outputs (new versioned folders)
- `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/` (300 PNG + `index.csv` + `color_scale.json`)
- `results/plots/pngs_normalized_surface_300_thesis_indexed_axes/` (300 PNG + `index.csv` + `color_scale_norm.json`)
- `results/plots/tempibhres_indexed_axes_fix_20260417_185500/`
  - deterministic set copy with indexed metadata
  - normalized set copy with indexed metadata
  - validation tempIBHRes examples (steps 013, 014, 015)
  - `comparison_panel_caption_overrides.csv`
  - `manifest.json`

## What Remains Physically Georeferenced
Outputs based on physically supported coordinate sources (for example HRes/TEST_C4/predModel/AUVpredModel families) are not changed by this fix and can keep physical axis conventions where already supported.

## Legacy / Historical Artifacts
The following folders can still contain old axis conventions and are preserved for traceability:
- `results/plots/deterministic_2024_surface_300_thesis/`
- `results/plots/pngs_normalized_surface_300_thesis/`
- `results/plots/tempibhres_display_mapping_label_fix_20260417_1730/`

These are historical outputs and should not be used as the current thesis convention for `tempIBHRes2024_*`.
