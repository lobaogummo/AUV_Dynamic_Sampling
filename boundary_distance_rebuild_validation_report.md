# Boundary Distance Rebuild Validation Report

Audit created: 2026-06-05T14:04:12

## Inputs

- Step08 directory: `results\fossum_roi_x490_step08_final_descriptors_20260514_164854`
- Step08 NPZ: `results\fossum_roi_x490_step08_final_descriptors_20260514_164854\step08_all_descriptor_maps.npz`
- Step11Y directory: `results\fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260525_001754`
- Step11Y NPZ: `results\fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260525_001754\prototype_based_all_planner_maps.npz`

## 1. Step08 New Map Keys

- Present: `0/7`
- Missing: `boundary_distance_cells, boundary_distance_km, boundary_distance_score_r1_cells, boundary_distance_score_r2_cells, boundary_distance_score_r3_cells, boundary_distance_score_r5_cells, boundary_distance_score_r8_cells`

## 2. Step11Y Normalized Map Keys

- Present: `0/7`
- Missing: `boundary_distance_cells_norm, boundary_distance_km_norm, boundary_distance_score_r1_cells_norm, boundary_distance_score_r2_cells_norm, boundary_distance_score_r3_cells_norm, boundary_distance_score_r5_cells_norm, boundary_distance_score_r8_cells_norm`

## 3. Finite Values Inside ROI Mask

_No data available._

## 4. Homogeneous Class Zero Boundary-Distance Scores

_No data available._

## 5. Radius Spatial Spread Monotonicity

_No data available._

## 6. Step12A Descriptor Loading Smoke Test

- Command: `python scripts\12a_single_auv_weight_duration_sensitivity.py --cases C01_representative --durations 12 --descriptors boundary_distance_score_r3_cells --dry-run`
- Return code: `1`

```text
Traceback (most recent call last):
  File "C:\Users\E713181\Documents\Dados\FILIPA_DADOS\scripts\12a_single_auv_weight_duration_sensitivity.py", line 544, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "C:\Users\E713181\Documents\Dados\FILIPA_DADOS\scripts\12a_single_auv_weight_duration_sensitivity.py", line 360, in main
    raise KeyError(
KeyError: 'Requested descriptors are not present in the selected Step11Y output. Rerun Step08/Step11Y first or remove: boundary_distance_score_r3_cells'
```

## 7. Diagnostic Figure

- Figure not generated because required Step11Y maps are missing:

```text
boundary_distance_score_r1_cells_norm
boundary_distance_score_r3_cells_norm
boundary_distance_score_r5_cells_norm
boundary_distance_score_r8_cells_norm
```

## Final Verdict

`BOUNDARY_DISTANCE_REBUILD_NOT_VALIDATED_NEEDS_REBUILD`

## Check Summary

| step08_contains_all_new_maps | step11y_contains_all_normalized_maps | all_new_maps_have_finite_values_inside_roi | homogeneous_classes_zero_scores | radius_spread_increases | step12a_can_load_new_descriptor | diagnostic_figure_created | final_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| False | False | False | False | False | False | False | BOUNDARY_DISTANCE_REBUILD_NOT_VALIDATED_NEEDS_REBUILD |
