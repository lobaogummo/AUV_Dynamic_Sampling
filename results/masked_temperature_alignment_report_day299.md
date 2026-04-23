# Masked Temperature Alignment Report (day299)

## 1) Previous Run Failure
- The previous attempt was considered failed because it resulted in a rectangular temperature crop instead of enforcing exact planner subgrid mask equivalence.

## 2) Correction Applied
- For each method (`CAND_B`, `USER_DIRECT_KM`):
  1. planner crop extracted
  2. exact planner boolean mask extracted
  3. temperature projected/interpolated to planner full grid
  4. same method ROI cropped from projected temperature
  5. exact planner mask applied
- Explicit assertions were executed in code:
  - `assert planner_crop.shape == temperature_mapped.shape`
  - `assert np.array_equal(planner_mask, temperature_mask)`

## 3) Day299 Mapping Audit
- planning_date_used: `2024-10-30`
- tempres_day_requested: `299`
- tempres_indexing_convention_detected: `tempRes numeric stack uses 0-based indexing [0..299], while exported z files use 1-based labels [1..300].`
- final_day_mapping_decision: `Requested day 299 interpreted as 1-based day label -> z299; numeric field index=298.`
- mapping_decision_justification: PNG and index.csv artifacts use z001..z300 labeling. Therefore day299 maps to z299 (not z300); array access is idx=z-1.
- tempres reference used: `results/plots/X_surface_300.npy[idx=298]` with PNG reference `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z299.png`

## 4) Exact Mask/Shape Confirmation
- CAND_B: shape_match=True, exact_mask_match=True, valid_cells_match=True, masked_cells_match=True
- USER_DIRECT_KM: shape_match=True, exact_mask_match=True, valid_cells_match=True, masked_cells_match=True

## 5) Outputs
- `results/candb_planner_crop_day299.npy`
- `results/candb_temperature_on_planner_mask_day299.npy`
- `results/candb_mask_day299.npy`
- `results/userdirect_planner_crop_day299.npy`
- `results/userdirect_temperature_on_planner_mask_day299.npy`
- `results/userdirect_mask_day299.npy`
- `results/candb_planner_crop_day299.png`
- `results/candb_temperature_on_planner_mask_day299.png`
- `results/userdirect_planner_crop_day299.png`
- `results/userdirect_temperature_on_planner_mask_day299.png`
- `results/comparison_candb_1to1_day299.png`
- `results/comparison_userdirect_1to1_day299.png`
- `results/comparison_both_methods_1to1_day299.png`
- `results/masked_crop_consistency_checks_day299.json`
- `results/masked_crop_consistency_metrics_day299.csv`
