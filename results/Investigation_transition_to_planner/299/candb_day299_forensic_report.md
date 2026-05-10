# CAND_B Day299 Forensic Report

## 1. Question under investigation
Determine whether the CAND_B planner-aligned temperature field for day z=299 (planning date 2024-10-30) is correct,
and explain if visible differences versus original tempRes are expected or bug-driven.

## 2. Data sources located
- tempRes numeric stack: `results/plots/X_surface_300.npy`
- tempRes index file: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/index.csv`
- tempRes PNG references: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z299.png`, `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z300.png`
- planner interface: `results/planner_baseline_scenario_c4_methodical_20260418_162500/inputs/30-10-2024_surface_dayfix_planner_interface.nc`
- CAND_B transform source: `results/tempres_georef_candidate_transforms.csv`
- previously generated CAND_B outputs: `results/candb_planner_crop_day299.npy`, `results/candb_mask_day299.npy`, `results/candb_temperature_on_planner_mask_day299.npy`
- generator script audited: `scripts/compare_method_temperature_exact_mask_day299.py`

Authoritative-source resolution:
- The authoritative numerical source is `X_surface_300.npy` (not PNG) because it provides machine-precision gridded values.
- The authoritative planner-aligned CAND_B outputs are the `_day299.npy` arrays listed above, referenced by the day299 checks JSON.

## 3. Day-index audit
- Requested z index: `299`; selected array index: `298`.
- `index.csv` row for z299 exists and points to: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z299.png`.
- Control row for z300 also exists: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z300.png`.
- Previous run day-mapping declaration: `Requested day 299 interpreted as 1-based day label -> z299; numeric field index=298.`.
- Wrong-day control (z300) diverges from saved day299 output (RMSE=0.246859).

## 4. Native-grid audit
- Native z299 shape: `(64, 112)` (interpreted as `[y, x]`).
- Native z299 stats: min=17.909000, max=18.767433, mean=18.230047, std=0.226112.
- PNG z299 rendered shape is `630x1050` (`RGBA`), confirming rendered-figure form rather than raw native grid.

## 5. Planner-grid audit
- Planner full grid shape: `(180, 240)`.
- CAND_B ROI global indices: x[28:155], y[34:100] -> shape `67x128`.
- Saved planner crop equals recomputed planner crop: `True`.
- ROI extraction is a direct planner-grid subwindow (no additional spatial transform at crop step).

## 6. Reconstruction of mapping pipeline
Reconstructed independently:
1. native z299 numeric field loaded from stack
2. full-grid regridding to planner coordinates (`linear + nearest fallback`)
3. CAND_B ROI crop from regridded planner full grid
4. exact planner mask applied to ROI crop

- Recomputed masked field equals saved field (finite-mask aware): `True`.
- Recomputed vs saved max absolute difference on valid cells: `0.0`.

## 7. Orientation and plotting audit
- Orientation hypotheses tested by remapping swapped/flipped source variants.
- Swap x/y RMSE: `0.399213`; V-flip RMSE: `0.137547`; H-flip RMSE: `0.203988`.
- Plotting-only controls generated (`origin`, transpose, aspect, axis inversion, normalization) to isolate visual-perception effects from numeric content.

## 8. Quantitative comparisons
- Baseline (recomputed vs saved): RMSE=0.000000e+00, MAE=0.000000e+00, Pearson=1.000000, Spearman=1.000000.
- Nearest-vs-saved: RMSE=0.005035, gradient-corr=0.985518.
- Native vs backprojected-native (regridding-loss proxy): RMSE=0.000276, Pearson=0.999999.
- PNG-naive vs saved (H8 control): RMSE=0.779068, Pearson=0.870103.

## 9. Hypothesis-by-hypothesis evaluation
- H1 (expected regridding difference, no bug): SUPPORTED
- H2 (x/y swapped): REJECTED
- H3 (vertical flip): REJECTED
- H4 (horizontal flip): REJECTED
- H5 (plotting/origin/aspect effects): SUPPORTED
- H6 (off-by-one crop): REJECTED
- H7 (wrong day): REJECTED
- H8 (PNG-derived instead of numeric): REJECTED
- H9 (mask correct but field misaligned): REJECTED
- H10 (interpolation smoothing expected): SUPPORTED

## 10. Final verdict
- source day verified: YES
- numerical source used: YES
- planner mask correctly applied: YES
- grid mapping geometrically consistent: YES
- major bug found: NO
- main explanation of visible differences: Differences are expected from interpolation smoothness, planner mask layout, and plotting/aspect choices; no geometric/day-index misalignment bug was detected.

## 11. List of generated artifacts
- `results/299/candb_day299_forensic_metrics.csv`
- `results/299/candb_day299_forensic_checks.json`
- `results/299/candb_day299_forensic_report.md`
- `results/299/candb_day299_forensic_summary.md`
- `results/299/original_day299_native_field.png`
- `results/299/candb_planner_crop_reference.png`
- `results/299/day299_native_vs_regridded_vs_masked.png`
- `results/299/day299_difference_maps.png`
- `results/299/day299_orientation_hypotheses.png`
- `results/299/day299_contour_overlay.png`
- `results/299/day299_plotting_effects.png`
