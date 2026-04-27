# Masked Temperature Alignment Report

## 1) Why Previous Version Was Not 1:1
- In the previous run, temperature crops were built in tempRes-index space (e.g., 26x60), while planner crops were in planner/HRes ROI space (e.g., 67x128).
- Because domain/layout/mask were different, those figures were not direct cell-by-cell 1:1 comparisons.

## 2) Correction Implemented
- Kept planner domain as geometric reference.
- For each method (`CAND_B`, `USER_DIRECT_KM`):
  1. Extracted method ROI on planner-compatible grid.
  2. Extracted planner crop and its exact valid-mask.
  3. Reprojected/interpolated temperature field to full planner grid.
  4. Cropped temperature on same ROI.
  5. Applied exact planner mask to the temperature crop.
- Result: temperature crop and planner crop now share identical local indices, shape, and mask.

## 3) Day And Reference
- day_used: `2024-10-30`
- reference_tempres_png: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z300.png`
- selected_z_for_numeric_field: `300` (DOY_TO_Z_CLIPPED_MAX; day-of-year=304 exceeds z_max=300; clipped to z=300)

## 4) 1:1 Consistency Results
- CAND_B -> shape match: `True` | valid_cells_match: `True` | masked_cells_match: `True` | exact_mask_match: `True`
- USER_DIRECT_KM -> shape match: `True` | valid_cells_match: `True` | masked_cells_match: `True` | exact_mask_match: `True`

## 5) Outputs Generated
- `results/candb_planner_crop.png`
- `results/userdirect_planner_crop.png`
- `results/candb_temperature_on_planner_mask.png`
- `results/userdirect_temperature_on_planner_mask.png`
- `results/candb_temperature_on_planner_mask.npy`
- `results/userdirect_temperature_on_planner_mask.npy`
- `results/candb_planner_crop.npy`
- `results/userdirect_planner_crop.npy`
- `results/candb_mask.npy`
- `results/userdirect_mask.npy`
- `results/comparison_candb_1to1.png`
- `results/comparison_userdirect_1to1.png`
- `results/comparison_both_methods_1to1.png`
- `results/comparison_overlay_masks.png`
- `results/masked_crop_consistency_checks.json`
- `results/masked_crop_consistency_metrics.csv`

## 6) Success Criteria
- CAND_B success: `True` (planner valid=8296, temperature valid=8296)
- USER_DIRECT_KM success: `True` (planner valid=8909, temperature valid=8909)
