# CAND_B No-Mask Report (day299)

## 1) Objective Of This Run
- This run isolates the effect of ROI/crop framing from the effect of planner-mask cell removal for CAND_B.

## 2) Why This Run
- Previous analyses mixed two visual effects: crop framing and masked-cell removal.
- Here, the no-mask CAND_B crop keeps all cells in the same ROI/subgrid to isolate crop effect only.

## 3) How CAND_B No-Mask Was Generated
1. Loaded tempRes numerical field for day z299 (`X_surface_300.npy`, idx=298).
2. Regridded to full planner grid via linear interpolation + nearest fallback.
3. Extracted exact CAND_B ROI (same bbox indices as method CAND_B).
4. Saved crop without applying planner mask (`candb_crop_nomask_day299`).
5. Built masked counterpart only by applying the same planner mask to the same no-mask crop.

## 4) ROI/BBox Consistency Confirmation
- same_roi_used: `True`
- same_bbox_used: `True`
- CAND_B ROI indices: x[28:155], y[34:100]
- CAND_B ROI lon/lat bbox: lon[-9.480707,-9.141214], lat[39.478584,39.652701]

## 5) Mask-Application Confirmation
- No-mask version does not apply planner mask.
- Masked version is created as `np.where(mask, nomask, np.nan)` using the same ROI/subgrid and same shape.
- same_shape_nomask_vs_masked: `True`
- difference_due_to_mask_only_explained: `True`

## 6) Generated Outputs
- `results/299/candb_crop_nomask_day299.npy`
- `results/299/candb_crop_masked_day299.npy`
- `results/299/candb_mask_day299.npy`
- `results/299/full_regridded_planner_nomask_day299.npy`
- `results/299/candb_crop_nomask_day299.png`
- `results/299/candb_crop_masked_day299.png`
- `results/299/candb_mask_day299.png`
- `results/299/full_regridded_planner_nomask_day299.png`
- `results/299/comparison_candb_nomask_vs_masked_day299.png`
- `results/299/comparison_candb_pipeline_day299.png`
- `results/299/comparison_candb_nomask_focus_day299.png`
- `results/299/candb_nomask_checks_day299.json`
- `results/299/candb_nomask_metrics_day299.csv`
