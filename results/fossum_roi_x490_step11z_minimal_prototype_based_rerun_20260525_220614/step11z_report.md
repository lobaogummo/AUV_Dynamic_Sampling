# Step11Z minimal prototype-based rerun

- Verdict: `PROTOTYPE_BASED_RERUN_COMPLETED_RESULTS_READY`
- Cases rerun: C01_representative, C06_representative, October_control
- Single-AUV rows: 9
- Multi-AUV rows: 6
- Warnings: 0

## Single-AUV metrics
| case_id | run_name | solver_status | crossing_count | regions_visited | fraction_path_region_A | fraction_path_region_B | collected_STD | collected_boundary | trajectory_length | solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | baseline_STD | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 94.367 | 116.153 | 36.655 | 233.716 |
| C01_representative | prototype_boundary_alpha050 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 91.350 | 137.040 | 38.093 | 233.649 |
| C01_representative | prototype_crossing_gamma025 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 95.496 | 144.364 | 38.549 | 509.112 |
| C06_representative | baseline_STD | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 85.019 | 119.183 | 36.473 | 710.128 |
| C06_representative | prototype_boundary_alpha050 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 76.715 | 112.842 | 36.896 | 283.989 |
| C06_representative | prototype_crossing_gamma025 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 76.651 | 115.219 | 36.767 | 530.697 |
| October_control | baseline_STD | SUCCESS | 2.000 | 2.000 | 0.466 | 0.534 | 93.713 | 28.411 | 37.797 | 184.929 |
| October_control | prototype_boundary_alpha050 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 48.803 | 107.750 | 36.456 | 243.506 |
| October_control | prototype_crossing_gamma025 | SUCCESS | 0.000 | 1.000 | 1.000 | 0.000 | 50.286 | 111.496 | 36.108 | 241.718 |


## Multi-AUV metrics
| case_id | strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score | fleet_collected_STD | fleet_collected_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | baseline_STD | SUCCESS | 0.049 | 0.015 | 0.000 | 15.916 | 0.532 | 186.493 | 231.392 |
| C01_representative | prototype_vehicle_specific_maps | SUCCESS | 0.037 | 0.039 | 0.010 | 13.790 | 0.533 | 180.924 | 193.628 |
| C06_representative | baseline_STD | SUCCESS | 0.056 | 0.000 | 0.000 | 10.629 | 0.528 | 161.418 | 230.794 |
| C06_representative | prototype_vehicle_specific_maps | SUCCESS | 0.039 | 0.035 | 0.003 | 27.580 | 0.535 | 130.471 | 160.970 |
| October_control | baseline_STD | SUCCESS | 0.025 | 0.068 | 0.003 | 12.100 | 0.545 | 178.266 | 58.236 |
| October_control | prototype_vehicle_specific_maps | SUCCESS | 0.034 | 0.043 | 0.037 | 20.200 | 0.520 | 170.634 | 63.157 |


## Old vs new
| scope | case_id | strategy | old_source_output | old_crossing_count | new_crossing_count | delta_crossing_count | old_regions_visited | new_regions_visited | old_collected_STD | new_collected_STD | old_collected_boundary | new_collected_boundary | old_fleet_region_A_coverage | new_fleet_region_A_coverage | old_fleet_region_B_coverage | new_fleet_region_B_coverage | old_overlap | new_overlap | old_complementarity | new_complementarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_AUV | C01_representative | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 97.489 | 94.367 | 125.013 | 116.153 |  |  |  |  |  |  |  |  |
| single_AUV | C01_representative | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 96.487 | 91.350 | 139.684 | 137.040 |  |  |  |  |  |  |  |  |
| single_AUV | C01_representative | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | 10.000 | 0.000 | -10.000 | 2.000 | 1.000 | 94.118 | 95.496 | 142.181 | 144.364 |  |  |  |  |  |  |  |  |
| single_AUV | C06_representative | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 3.000 | 0.000 | -3.000 | 2.000 | 1.000 | 84.748 | 85.019 | 120.925 | 119.183 |  |  |  |  |  |  |  |  |
| single_AUV | C06_representative | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 0.000 | -6.000 | 2.000 | 1.000 | 71.747 | 76.715 | 112.692 | 112.842 |  |  |  |  |  |  |  |  |
| single_AUV | C06_representative | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 3.000 | 0.000 | -3.000 | 2.000 | 1.000 | 78.341 | 76.651 | 119.532 | 115.219 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 2.000 | -4.000 | 2.000 | 2.000 | 88.593 | 93.713 | 26.001 | 28.411 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 8.000 | 0.000 | -8.000 | 2.000 | 1.000 | 52.871 | 48.803 | 108.477 | 107.750 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 53.384 | 50.286 | 111.523 | 111.496 |  |  |  |  |  |  |  |  |
| multi_AUV | C01_representative | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 |  |  |  |  |  |  |  |  |  | 0.062 | 0.049 | 0.014 | 0.015 | 0.000 | 0.000 | 0.538 | 0.532 |
| multi_AUV | C01_representative | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 |  |  |  |  |  |  |  |  |  | 0.047 | 0.037 | 0.031 | 0.039 | 0.016 | 0.010 | 0.531 | 0.533 |
| multi_AUV | C06_representative | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.075 | 0.056 | 0.002 | 0.000 | 0.000 | 0.000 | 0.538 | 0.528 |
| multi_AUV | C06_representative | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.042 | 0.039 | 0.034 | 0.035 | 0.026 | 0.003 | 0.525 | 0.535 |
| multi_AUV | October_control | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.004 | 0.025 | 0.075 | 0.068 | 0.019 | 0.003 | 0.530 | 0.545 |
| multi_AUV | October_control | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.038 | 0.034 | 0.041 | 0.043 | 0.003 | 0.037 | 0.538 | 0.520 |


## October focus
| scope | case_id | strategy | old_source_output | old_crossing_count | new_crossing_count | delta_crossing_count | old_regions_visited | new_regions_visited | old_collected_STD | new_collected_STD | old_collected_boundary | new_collected_boundary | old_fleet_region_A_coverage | new_fleet_region_A_coverage | old_fleet_region_B_coverage | new_fleet_region_B_coverage | old_overlap | new_overlap | old_complementarity | new_complementarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_AUV | October_control | baseline_STD | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 6.000 | 2.000 | -4.000 | 2.000 | 2.000 | 88.593 | 93.713 | 26.001 | 28.411 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_boundary_alpha050 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 8.000 | 0.000 | -8.000 | 2.000 | 1.000 | 52.871 | 48.803 | 108.477 | 107.750 |  |  |  |  |  |  |  |  |
| single_AUV | October_control | prototype_crossing_gamma025 | fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 53.384 | 50.286 | 111.523 | 111.496 |  |  |  |  |  |  |  |  |
| multi_AUV | October_control | baseline_STD | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.004 | 0.025 | 0.075 | 0.068 | 0.019 | 0.003 | 0.530 | 0.545 |
| multi_AUV | October_control | prototype_vehicle_specific_maps | fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 |  |  |  |  |  |  |  |  |  | 0.038 | 0.034 | 0.041 | 0.043 | 0.003 | 0.037 | 0.538 | 0.520 |
