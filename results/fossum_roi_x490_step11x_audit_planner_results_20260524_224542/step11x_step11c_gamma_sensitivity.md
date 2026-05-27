# Step11C gamma sensitivity

## Evidence table

| source_output | case_id | run_name | mission_duration_requested_h | gamma | crossing_count | regions_visited | fraction_path_region_A | fraction_path_region_B | collected_STD | collected_boundary | difference_from_baseline | solver_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | baseline_STD_6h | 6.000 | 0.000 | 4.000 | 2.000 | 0.854 | 0.146 | 48.341 | 71.608 | 0.000 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | boundary_alpha050_6h | 6.000 | 0.000 | 6.000 | 2.000 | 0.840 | 0.160 | 47.156 | 71.774 | 0.891 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | crossing_gamma050_6h | 6.000 | 0.500 | 0.000 | 1.000 | 1.000 | 0.000 | 45.983 | 70.381 | 0.913 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | baseline_STD | 12.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 97.489 | 125.013 | 0.000 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | boundary_alpha050 | 12.000 | 0.000 | 6.000 | 2.000 | 0.843 | 0.157 | 96.487 | 139.684 | 0.928 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | crossing_gamma025 | 12.000 | 0.250 | 10.000 | 2.000 | 0.823 | 0.177 | 94.118 | 142.181 | 0.934 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | crossing_gamma050 | 12.000 | 0.500 | 2.000 | 2.000 | 0.929 | 0.071 | 89.587 | 132.231 | 0.932 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | baseline_STD | 12.000 | 0.000 | 3.000 | 2.000 | 0.994 | 0.006 | 84.748 | 120.925 | 0.000 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | boundary_alpha050 | 12.000 | 0.000 | 6.000 | 2.000 | 0.979 | 0.021 | 71.747 | 112.692 | 0.937 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | crossing_gamma025 | 12.000 | 0.250 | 3.000 | 2.000 | 0.987 | 0.013 | 78.341 | 119.532 | 0.878 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | crossing_gamma050 | 12.000 | 0.500 | 9.000 | 2.000 | 0.967 | 0.033 | 76.024 | 115.542 | 0.920 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | baseline_STD | 12.000 | 0.000 | 6.000 | 2.000 | 0.065 | 0.935 | 88.593 | 26.001 | 0.000 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | boundary_alpha050 | 12.000 | 0.000 | 8.000 | 2.000 | 0.943 | 0.057 | 52.871 | 108.477 | 0.984 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | crossing_gamma025 | 12.000 | 0.250 | 0.000 | 1.000 | 1.000 | 0.000 | 53.384 | 111.523 | 0.997 | SUCCESS |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | crossing_gamma050 | 12.000 | 0.500 | 0.000 | 1.000 | 1.000 | 0.000 | 57.707 | 105.386 | 0.997 | SUCCESS |

- Best crossing row by count: C01_representative / crossing_gamma025 with crossing_count=10.
- Non-monotonic gamma behavior detected in 1 case-duration groups.
- The saved audit says route-level reward was unavailable; Step11C is therefore a static-map proxy, not a true path crossing objective.
- gamma=0.25 is defensible where it improves crossings without large STD loss, but the evidence does not support assuming higher gamma is better.
- A warning sign is any row with high boundary-core fraction but zero crossings: that means the proxy can attract the path near the boundary without making the route switch regimes.