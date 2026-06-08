# Step11Z minimal prototype-based rerun

- Verdict: `PROTOTYPE_BASED_RERUN_COMPLETED_WITH_WARNINGS`
- Cases rerun: October_control
- Single-AUV rows: 3
- Multi-AUV rows: 3
- Warnings: 1

## Single-AUV metrics
| case_id | run_name | solver_status | crossing_count | regions_visited | fraction_path_region_A | fraction_path_region_B | collected_STD | collected_boundary | trajectory_length | solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| October_control | baseline_STD | REUSED | 0.000 | 1.000 | 1.000 | 0.000 | 88.593 | 0.000 | 37.587 | 0.000 |
| October_control | prototype_boundary_alpha050 | REUSED_FAILED | 0.000 | 0.000 |  |  |  |  |  | 0.000 |
| October_control | prototype_crossing_gamma025 | REUSED_FAILED | 0.000 | 0.000 |  |  |  |  |  | 0.000 |


## Multi-AUV metrics
| case_id | strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score | fleet_collected_STD | fleet_collected_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| October_control | baseline_STD | REUSED | 0.039 | 0.000 | 0.022 | 12.583 | 0.509 | 181.985 | 0.000 |
| October_control | prototype_vehicle_specific_maps | FAILED_OR_PARTIAL | 0.000 | 0.000 | 0.000 |  | 0.500 | 0.000 | 0.000 |
| October_control | prototype_vehicle_specific_with_boundary | FAILED_OR_PARTIAL | 0.019 | 0.000 | 0.000 |  | 0.509 | 84.823 | 0.000 |


## Old vs new
| scope | case_id | strategy | old_source_output | old_crossing_count | new_crossing_count | delta_crossing_count | old_regions_visited | new_regions_visited | old_collected_STD | new_collected_STD | old_collected_boundary | new_collected_boundary | old_fleet_region_A_coverage | new_fleet_region_A_coverage | old_fleet_region_B_coverage | new_fleet_region_B_coverage | old_overlap | new_overlap | old_complementarity | new_complementarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_AUV | October_control | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 88.593 | 88.593 | 26.001 | 0.000 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 8.000 | 0.000 | -8.000 | 2.000 | 0.000 | 52.871 |  | 108.477 |  |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 53.384 |  | 111.523 |  |  |  |  |  |  |  |  |  |
| multi_AUV | October_control | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.004 | 0.039 | 0.075 | 0.000 | 0.019 | 0.022 | 0.530 | 0.509 |
| multi_AUV | October_control | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.038 | 0.000 | 0.041 | 0.000 | 0.003 | 0.000 | 0.538 | 0.500 |
| multi_AUV | October_control | prototype_vehicle_specific_with_boundary | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.037 | 0.019 | 0.041 | 0.000 | 0.016 | 0.000 | 0.531 | 0.509 |


## October focus
| scope | case_id | strategy | old_source_output | old_crossing_count | new_crossing_count | delta_crossing_count | old_regions_visited | new_regions_visited | old_collected_STD | new_collected_STD | old_collected_boundary | new_collected_boundary | old_fleet_region_A_coverage | new_fleet_region_A_coverage | old_fleet_region_B_coverage | new_fleet_region_B_coverage | old_overlap | new_overlap | old_complementarity | new_complementarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_AUV | October_control | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 88.593 | 88.593 | 26.001 | 0.000 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 8.000 | 0.000 | -8.000 | 2.000 | 0.000 | 52.871 |  | 108.477 |  |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 53.384 |  | 111.523 |  |  |  |  |  |  |  |  |  |
| multi_AUV | October_control | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.004 | 0.039 | 0.075 | 0.000 | 0.019 | 0.022 | 0.530 | 0.509 |
| multi_AUV | October_control | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.038 | 0.000 | 0.041 | 0.000 | 0.003 | 0.000 | 0.538 | 0.500 |
| multi_AUV | October_control | prototype_vehicle_specific_with_boundary | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.037 | 0.019 | 0.041 | 0.000 | 0.016 | 0.000 | 0.531 | 0.509 |
