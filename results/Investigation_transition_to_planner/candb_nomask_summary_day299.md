# CAND_B No-Mask Summary (day299)

- day_used: `2024-10-30 / z=299`
- source_numeric_field_used: `results/plots/X_surface_300.npy[idx=298]`
- candb_crop_nomask_shape: `(67, 128)`
- candb_crop_masked_shape: `(67, 128)`
- same_roi_used: `True`
- same_bbox_used: `True`
- same_shape_nomask_vs_masked: `True`
- difference_due_to_mask_only_explained: `True`

The CAND_B no-mask image uses the same ROI and planner subgrid as the original CAND_B crop, but preserves all cells before mask removal, allowing isolation of the crop effect from the mask effect.
