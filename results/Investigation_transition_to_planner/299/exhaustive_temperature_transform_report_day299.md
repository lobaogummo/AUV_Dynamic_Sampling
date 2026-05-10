# Exhaustive Temperature Transform Report (day299)

## 1. Question under investigation
Find the best geometric transform between tempRes z299 temperature and planner-domain temperature for the same day.

## 2. Authoritative data sources
- source temperature: `results/plots/X_surface_300.npy[idx=298]`
- target temperature source file: `C:\Users\pedro\Documents\Filipa_dados\data\TEST_D4\HighRes\Daily_dpt_20241029_NewTest_1\30-10-2024_predModel_1.nc`
- target variable used: `TEMPpred` (day index `1`)
- planner interface trace file: `results/planner_baseline_scenario_c4_methodical_20260418_162500/inputs/30-10-2024_surface_dayfix_planner_interface.nc`
- CAND_B ROI source: `results/tempres_georef_candidate_transforms.csv`

## 3. Day/index audit
- source z/index: `z=299`, `idx=298`
- target source date token: `2024-10-30`
- operational date requested: `2024-10-30`
- same day confirmed: `True`

## 4. Comparison domains defined
- source domain = tempRes native temperature
- target domain = planner-compatible HResNew temperature
- full domain shape: `(180, 240)`
- ROI shape: `(67, 128)`
- domain modes evaluated: full/ROI x nomask/masked

## 5. Candidate transform families tested
- A) discrete/basic: identity, crop, resize, transpose/flips, offsets, scale-only, translation-only
- B) linear registration: similarity, affine, projective, polynomial-order2, ECC
- C) non-rigid registration: dense optical flow, piecewise affine, thin-plate spline, smooth-flow deformation
- D) optimization/correspondence: phase correlation, NCC, mutual information, contour/isotherm, ORB feature-based

## 6. Interpolation variants tested
- bicubic, lanczos, linear, nearest, none, spline

## 7. Quantitative leaderboard
- leaderboard file: `results/299/transform_search_temperature_leaderboard_day299.csv`
- Top 5 rows:
  - rank 1: affine_rmse_optimization | family=B_linear_registration | interp=lanczos | domain=full | mask=nomask | rmse=0.045533 | pearson=0.040078
  - rank 2: affine_rmse_optimization | family=B_linear_registration | interp=lanczos | domain=full | mask=masked | rmse=0.045533 | pearson=0.040078
  - rank 3: dense_optical_flow_tvl1 | family=C_nonrigid_registration | interp=linear | domain=full | mask=nomask | rmse=0.717152 | pearson=0.699485
  - rank 4: affine_rmse_optimization | family=B_linear_registration | interp=nearest | domain=full | mask=nomask | rmse=0.052631 | pearson=0.029071
  - rank 5: affine_rmse_optimization | family=B_linear_registration | interp=nearest | domain=full | mask=masked | rmse=0.052631 | pearson=0.029071

## 8. Analysis of top methods
- Best operational (ROI masked): `dense_optical_flow_tvl1` (linear)
- Best full no-mask: `affine_rmse_optimization` (lanczos)
- Best overall composite: `affine_rmse_optimization` (lanczos)

## 9. Exact-match feasibility
- exact transform found: `False`
- near-perfect transform found: `False`
- best operational RMSE: `0.699406`
- best operational Pearson: `0.776598`
- best operational max_abs_error: `1.411508`

## 10. Final verdict
- source variable verified as temperature: `YES`
- target variable verified as temperature: `YES`
- same day confirmed: `YES`
- exact transform found: `NO`
- near-perfect transform found: `NO`
- best method: `dense_optical_flow_tvl1`
- best interpolation: `linear`
- best domain: `roi/masked`
- best RMSE: `0.699406`
- best Pearson: `0.776598`

## 11. Generated artifacts
- `results/299/transform_search_temperature_leaderboard_day299.csv`
- `results/299/transform_search_temperature_checks_day299.json`
- `results/299/transform_search_temperature_best_method_day299.json`
- `results/299/exhaustive_temperature_transform_report_day299.md`
- `results/299/exhaustive_temperature_transform_summary_day299.md`
- `results/299/best_temperature_transform_full_comparison_day299.png`
- `results/299/best_temperature_transform_roi_comparison_day299.png`
- `results/299/best_temperature_transform_masked_comparison_day299.png`
- `results/299/top5_temperature_transform_candidates_day299.png`
- `results/299/temperature_orientation_and_flip_tests_day299.png`
- `results/299/temperature_contour_alignment_best_method_day299.png`
- `results/299/temperature_residual_error_maps_best_method_day299.png`
- `results/299/temperature_transformation_pipeline_best_method_day299.png`
- `results/299/best_temperature_transformed_full.npy`
- `results/299/best_temperature_transformed_roi_nomask.npy`
- `results/299/best_temperature_transformed_roi_masked.npy`
- `results/299/best_temperature_difference_full.npy`
- `results/299/best_temperature_difference_roi.npy`

## 12. Optional STD note
- STD was detected in the target source file and documented in checks JSON, but no STD↔STD optimization was run in this script.
