# Step10E ROI Status Audit Summary

- Step10D predModel NetCDF files found: `20`.
- Persisted TEMPpred ROI stack `[20,72,117]`: `False`.
- Persisted STD/variance ROI stack `[20,72,117]`: `False`.
- Complete persisted ROI array set exists: `False`.
- Step00 mask valid cells: `8004`.
- ROI reference mask valid cells used by fixed-scale figures: `8182`.
- Mask difference: `178` cells; ROI reference has `178` extra valid cells relative to Step00.
- LAT/LON/BATHY match Step00 exactly; mask does not.
- Fixed-scale figures used ROI arrays in memory, sliced from full-grid predModels; they did not save numeric ROI `.npy` stacks.
- Recommended Step10E mask: `Step00 mask_common_roi_x490.npy`.
- Verdict: `NEEDS_STEP10E_ROI_EXTRACTION`.

## Interpretation

The visual PNGs are ROI x490 views, but they are not a persisted numeric ROI dataset. For downstream Step09B/planner work, create canonical `[20,72,117]` arrays from the predModels using the Step00 mask_common, not the broader paper ROI mask used in the visual-only script.
