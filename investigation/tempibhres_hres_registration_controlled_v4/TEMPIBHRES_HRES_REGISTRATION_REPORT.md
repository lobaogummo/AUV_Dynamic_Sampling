# TEMPIBHRES_HRES_REGISTRATION_REPORT

Generated at: 2026-04-18T16:02:59

## 1) Executive summary
- Objective: infer a physically defensible spatial registration from `tempIBHRes2024_*` to physically anchored HRes references before creating physical-axis figures.
- Outcome: viable for inferred physical-axis labeling under the configured criteria.
- Best transformation (0-based HRes indices): x0=28, x1=155, y0=34, y1=100, w=128, h=67.
- Best candidate metrics: mask IoU=0.999856, pred mean corr=0.981501, auv mean corr=0.972316.

## 2) Datasets and references
- tempIBHRes source stack: `results/plots/X_surface_300.npy` (shape 300x64x112).
- Physically anchored reference family A: `TEST_C4 predModel_*` using `TEMPpred` (17 steps).
- Physically anchored reference family B: `TEST_C4 AUVpredModel_*` using `TEMPpred` (17 steps).
- Physical frame comes from TEST_C4 NetCDF LAT/LON coordinates and HRes mask (`BATHY`).

## 3) Method
- Stage 1: deterministic coarse search over axis-aligned crop+resample transforms, scored by mask overlap.
- Stage 2: local refinement around top mask candidates.
- Stage 3: local fine search around best refined candidate.
- Temperature validation: for each reference step, transform to tempIBHRes grid and match against all 300 tempIBHRes days by max Pearson correlation.
- Additional metrics per match: second-best correlation, correlation margin, RMSE(raw), RMSE(linear-fit), NRMSE(linear-fit).
- Stability check: per-step local offset re-optimization around the global best transformation.

## 4) Key results
- Candidate ranking and search traces are in `tables/` CSV files.
- Best candidate (1-based HRes indices): x=29..156, y=35..101.
- predModel summary: mean=0.981501, median=0.982200, min=0.962922, p25=0.981166.
- AUVpredModel summary: mean=0.972316, median=0.975080, min=0.945913, p25=0.973531.
- Pred local stability (|delta| means): |dx|=3.412, |dy|=1.882.
- AUV local stability (|delta| means): |dx|=2.765, |dy|=2.059.

## 5) Decision on inferred physical axes
- Viability decision: `True`
- Criteria checks: mask_ok=True, pred_ok=True, auv_ok=True, min_ok=True.
- Inferred-axis figures were exported with explicit inferred labeling (not native tempIBHRes georeferencing).
- Axis mode used: `utm_abs_km`
- Deterministic inferred figures: `investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres`
- Normalized inferred figures: `investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/normalized_tempibhres`

## 6) Facts, inferences, limitations
### Facts observed
- tempIBHRes grid is 64x112 with index-based columns (`x`,`y`,`z`,`temp`).
- TEST_C4 pred/AUV NetCDF grids are physically anchored and include LAT/LON coordinates.
- Registration search produced a top candidate with metrics reported above.
### Inferences
- The best transformation is interpreted as a plausible spatial correspondence between tempIBHRes and a sub-area of the HRes physical grid.
- Inferred axes are therefore registration-derived, not native to tempIBHRes.
### Limitations
- Transformation family is restricted to axis-aligned crop + linear resampling (no rotation/shear/nonlinear warp).
- Temporal pairing uses max-correlation matching; high similarity fields can reduce uniqueness of matched day indices.
- This investigation does not prove native georeferencing metadata exists inside tempIBHRes.

## 7) Output inventory
- `tables/`: candidate search traces, top-candidate evaluations, per-step match metrics, stability checks.
- `plots/`: mask overlays, ranking curves, per-step quality curves, side-by-side diagnostics.
- `manifest.json`: full traceability of inputs, parameters, thresholds, and decision.
- `figures_inferred_axes_km/`: inferred-axis figure exports and inferred axis arrays.

