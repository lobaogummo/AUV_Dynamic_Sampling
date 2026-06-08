# Step11Z minimal prototype-based rerun

- Verdict: `PROTOTYPE_BASED_RERUN_COMPLETED_WITH_WARNINGS`
- Cases rerun: C01_representative, C06_representative, October_control
- Single-AUV rows: 9
- Multi-AUV rows: 6
- Warnings: 1

## Single-AUV metrics
| case_id | run_name | solver_status | crossing_count | regions_visited | fraction_path_region_A | fraction_path_region_B | collected_STD | collected_boundary | trajectory_length | solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | baseline_STD | SUCCESS | 2.000 | 2.000 | 0.889 | 0.111 | 90.650 | 107.187 | 38.053 | 1578.471 |
| C01_representative | prototype_boundary_alpha050 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 74.780 | 104.019 | 31.056 | 1602.925 |
| C01_representative | prototype_crossing_gamma025 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 76.117 | 114.209 | 31.081 | 1508.761 |
| C06_representative | baseline_STD | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 84.748 | 120.925 | 36.475 | 1693.510 |
| C06_representative | prototype_boundary_alpha050 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 57.381 | 91.240 | 30.849 | 1154.176 |
| C06_representative | prototype_crossing_gamma025 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 60.259 | 95.600 | 29.147 | 1017.497 |
| October_control | baseline_STD | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 88.593 | 0.000 | 37.587 | 1755.377 |
| October_control | prototype_boundary_alpha050 | FAILED | 0.000 | 0.000 |  |  |  |  |  | 9.585 |
| October_control | prototype_crossing_gamma025 | FAILED | 0.000 | 0.000 |  |  |  |  |  | 6.205 |


## Multi-AUV metrics
| case_id | strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score | fleet_collected_STD | fleet_collected_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | baseline_STD | SUCCESS | 0.045 | 0.024 | 0.000 | 19.072 | 0.534 | 187.142 | 219.078 |
| C01_representative | prototype_vehicle_specific_maps | SUCCESS | 0.028 | 0.024 | 0.110 | 4.020 | 0.471 | 145.271 | 144.868 |
| C06_representative | baseline_STD | SUCCESS | 0.058 | 0.000 | 0.000 | 8.528 | 0.529 | 169.193 | 244.615 |
| C06_representative | prototype_vehicle_specific_maps | SUCCESS | 0.039 | 0.034 | 0.003 | 27.311 | 0.535 | 127.680 | 162.429 |
| October_control | baseline_STD | SUCCESS | 0.039 | 0.000 | 0.022 | 12.583 | 0.509 | 181.985 | 0.000 |
| October_control | prototype_vehicle_specific_maps | FAILED_OR_PARTIAL | 0.000 | 0.000 | 0.000 |  | 0.500 | 0.000 | 0.000 |


## Old vs new
| scope | case_id | strategy | old_source_output | old_crossing_count | new_crossing_count | delta_crossing_count | old_regions_visited | new_regions_visited | old_collected_STD | new_collected_STD | old_collected_boundary | new_collected_boundary | old_fleet_region_A_coverage | new_fleet_region_A_coverage | old_fleet_region_B_coverage | new_fleet_region_B_coverage | old_overlap | new_overlap | old_complementarity | new_complementarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_AUV | C01_representative | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | 0.000 | 2.000 | 2.000 | 1.000 | 2.000 | 97.489 | 90.650 | 125.013 | 107.187 |  |  |  |  |  |  |  |  |
| single_AUV | C01_representative | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 96.487 | 74.780 | 139.684 | 104.019 |  |  |  |  |  |  |  |  |
| single_AUV | C01_representative | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | 10.000 | 0.000 | -10.000 | 2.000 | 1.000 | 94.118 | 76.117 | 142.181 | 114.209 |  |  |  |  |  |  |  |  |
| single_AUV | C06_representative | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 3.000 | 0.000 | -3.000 | 2.000 | 1.000 | 84.748 | 84.748 | 120.925 | 120.925 |  |  |  |  |  |  |  |  |
| single_AUV | C06_representative | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 71.747 | 57.381 | 112.692 | 91.240 |  |  |  |  |  |  |  |  |
| single_AUV | C06_representative | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 3.000 | 0.000 | -3.000 | 2.000 | 1.000 | 78.341 | 60.259 | 119.532 | 95.600 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 88.593 | 88.593 | 26.001 | 0.000 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 8.000 | 0.000 | -8.000 | 2.000 | 0.000 | 52.871 |  | 108.477 |  |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 53.384 |  | 111.523 |  |  |  |  |  |  |  |  |  |
| multi_AUV | C01_representative | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 |  |  |  |  |  |  |  |  |  | 0.062 | 0.045 | 0.014 | 0.024 | 0.000 | 0.000 | 0.538 | 0.534 |
| multi_AUV | C01_representative | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 |  |  |  |  |  |  |  |  |  | 0.047 | 0.028 | 0.031 | 0.024 | 0.016 | 0.110 | 0.531 | 0.471 |
| multi_AUV | C06_representative | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.075 | 0.058 | 0.002 | 0.000 | 0.000 | 0.000 | 0.538 | 0.529 |
| multi_AUV | C06_representative | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.042 | 0.039 | 0.034 | 0.034 | 0.026 | 0.003 | 0.525 | 0.535 |
| multi_AUV | October_control | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.004 | 0.039 | 0.075 | 0.000 | 0.019 | 0.022 | 0.530 | 0.509 |
| multi_AUV | October_control | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.038 | 0.000 | 0.041 | 0.000 | 0.003 | 0.000 | 0.538 | 0.500 |


## October focus
| scope | case_id | strategy | old_source_output | old_crossing_count | new_crossing_count | delta_crossing_count | old_regions_visited | new_regions_visited | old_collected_STD | new_collected_STD | old_collected_boundary | new_collected_boundary | old_fleet_region_A_coverage | new_fleet_region_A_coverage | old_fleet_region_B_coverage | new_fleet_region_B_coverage | old_overlap | new_overlap | old_complementarity | new_complementarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_AUV | October_control | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 88.593 | 88.593 | 26.001 | 0.000 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 8.000 | 0.000 | -8.000 | 2.000 | 0.000 | 52.871 |  | 108.477 |  |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 53.384 |  | 111.523 |  |  |  |  |  |  |  |  |  |
| multi_AUV | October_control | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.004 | 0.039 | 0.075 | 0.000 | 0.019 | 0.022 | 0.530 | 0.509 |
| multi_AUV | October_control | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.038 | 0.000 | 0.041 | 0.000 | 0.003 | 0.000 | 0.538 | 0.500 |
