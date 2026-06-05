# Step11Y prototype-based planner input audit

- Verdict: `MIXED_INPUTS_PARTIAL_RERUN_RECOMMENDED`
- Planner rerun performed: `False`
- Corrected arrays created: `True`
- Boundary-distance descriptors available: `True`
- Step10F boundary maps matching Step08 prototypes: 3/3 cases
- Cases with TEMPpred-derived region fallback in Step11C/11D evidence: October_control

## Direct answers

1. Previous Step10F boundary inputs used Step08 prototype descriptors by predicted class.
2. TEMPpred-derived maps appear in the Step11C/Step11D region fallback path where Step09B assigned region maps are unavailable.
3. Correct Step10F cases: C01_representative, C06_representative, October_control.
4. Cases needing rerun: October_control.
5. October fallback issue: yes.
6. Use the new `prototype_based_*` arrays from this Step11Y output going forward.
7. Next step: rerun the minimal affected planner tests with prototype-based regions/maps if the verdict recommends it.
8. If Step08 was rebuilt with explicit boundary-distance maps, Step11Y also exports normalized `boundary_distance_score_r*_cells_norm` maps for Step12A.

## Step10F boundary comparison
| case_id | map_name | rmse | mae | pearson | max_abs_diff | near_exact_match |
| --- | --- | --- | --- | --- | --- | --- |
| C01_representative | boundary_score_norm | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| C06_representative | boundary_score_norm | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |
| October_control | boundary_score_norm | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 |


## Region-mask lineage evidence
| audit_step | source_output | case_id | map_name | inference | mae | max_abs_diff | near_exact_vs_TEMPpred_median_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | region_A_mask | prototype_region_based_raw_Step09B | 0.2179 | 1.0000 | False |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | region_B_mask | prototype_region_based_raw_Step09B | 0.2179 | 1.0000 | False |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | boundary_core_mask | prototype_boundary_core | 0.0000 | 0.0000 | True |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | region_A_mask | prototype_region_based_raw_Step09B | 0.1960 | 1.0000 | True |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | region_B_mask | prototype_region_based_raw_Step09B | 0.1960 | 1.0000 | True |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | boundary_core_mask | prototype_boundary_core | 0.0000 | 0.0000 | True |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | region_A_mask | TEMPpred_median_fallback | 0.1667 | 1.0000 | True |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | region_B_mask | TEMPpred_median_fallback | 0.1667 | 1.0000 | True |
| Step11C | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | boundary_core_mask | prototype_boundary_core | 0.0000 | 0.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | region_A_mask | prototype_region_based_raw_Step09B | 0.2179 | 1.0000 | False |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | region_B_mask | prototype_region_based_raw_Step09B | 0.2179 | 1.0000 | False |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | boundary_core_mask | prototype_boundary_core | 0.0000 | 0.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | step11d_region_A_reward.npy | top_level_C01_reward_file | 0.2179 | 1.0000 |  |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | step11d_region_B_reward.npy | top_level_C01_reward_file | 0.2179 | 1.0000 |  |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | region_A_mask | prototype_region_based_raw_Step09B | 0.1960 | 1.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | region_B_mask | prototype_region_based_raw_Step09B | 0.1960 | 1.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | boundary_core_mask | prototype_boundary_core | 0.0000 | 0.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | region_A_mask | TEMPpred_median_fallback | 0.1667 | 1.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | region_B_mask | TEMPpred_median_fallback | 0.1667 | 1.0000 | True |
| Step11D | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | boundary_core_mask | prototype_boundary_core | 0.0000 | 0.0000 | True |


## Boundary-distance descriptor propagation

- Step08 directory used: `results\fossum_roi_x490_step08_final_descriptors_20260605_141912`
- Step08 keys found: `boundary_distance_cells, boundary_distance_km, boundary_distance_score_r1_cells, boundary_distance_score_r2_cells, boundary_distance_score_r3_cells, boundary_distance_score_r5_cells, boundary_distance_score_r8_cells`
- Step11Y keys written: `boundary_distance_cells_norm, boundary_distance_km_norm, boundary_distance_score_r1_cells_norm, boundary_distance_score_r2_cells_norm, boundary_distance_score_r3_cells_norm, boundary_distance_score_r5_cells_norm, boundary_distance_score_r8_cells_norm`

| boundary_distance_step08_keys_found | boundary_distance_step11y_keys_written |
| --- | --- |
| boundary_distance_cells\|boundary_distance_km\|boundary_distance_score_r1_cells\|boundary_distance_score_r2_cells\|boundary_distance_score_r3_cells\|boundary_distance_score_r5_cells\|boundary_distance_score_r8_cells | boundary_distance_cells_norm\|boundary_distance_km_norm\|boundary_distance_score_r1_cells_norm\|boundary_distance_score_r2_cells_norm\|boundary_distance_score_r3_cells_norm\|boundary_distance_score_r5_cells_norm\|boundary_distance_score_r8_cells_norm |
