# Step12A boundary-distance descriptor results interpretation

## Scope and input audit
- Input folder: `results\fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260605_152501`
- Main metrics CSV identified: `step12a_single_auv_metrics.csv`.
- Main metrics shape: 25 rows x 39 columns.
- CSV files inspected: 31. JSON/manifests inspected: 24. Figure/media files found: 71.
- Filtered analysis subset: case `C01_representative`, duration `12` h, descriptors `boundary_score, boundary_distance_score_r1_cells, boundary_distance_score_r3_cells, boundary_distance_score_r5_cells, interest_map`, alphas `0.00, 0.25, 0.50, 0.75, 1.00`.

## Main metrics columns
The main metrics table combines the logical run definition, planner diagnostics, route outputs, accumulated reward-map proxies, and route coverage/proxy metrics. Its columns are:

`Index`, `case_id`, `date`, `predicted_class`, `mission_duration_requested_h`, `descriptor`, `alpha`, `run_name`, `physical_run_id`, `deduplicated_baseline`, `prototype_based_maps`, `TEMPpred_used_as_objective`, `information_map_formula`, `solver_status`, `solver_runtime`, `solver_gap`, `solver_returncode`, `run_dir`, `total_script_runtime`, `trajectory_length`, `mission_duration`, `number_of_valid_cells_sampled`, `collected_STD`, `collected_descriptor`, `collected_information_score`, `percentage_path_in_top10_STD`, `percentage_path_in_top10_descriptor`, `trajectory_overlap_ratio_with_baseline`, `path_difference_from_baseline`, `regions_visited`, `crossing_count`, `fraction_path_region_A`, `fraction_path_region_B`, `baseline_STD`, `baseline_runtime`, `STD_retention`, `regime_balance`, `runtime_score`, `recommendation_score`

For this thesis interpretation, `collected_information_score` is treated as total collected reward, i.e. the accumulated reward-map proxy along the route. `collected_STD` is the accumulated STD/uncertainty-proxy reward, and `collected_descriptor` is the accumulated descriptor-specific proxy where available.

## Planner completion check
- All filtered planner runs succeeded: `True`.
- Filtered rows checked: 25.
- No failed runs were found in the filtered metrics/diagnostics tables.

## Extracted metrics by descriptor and alpha
| case_id | mission_duration_requested_h | descriptor | alpha | solver_status | total_collected_reward | collected_STD | collected_descriptor | route_length_km | reward_per_distance_km | solver_runtime | percentage_path_in_top10_STD | percentage_path_in_top10_descriptor | number_of_valid_cells_sampled | trajectory_overlap_ratio_with_baseline | path_difference_from_baseline | regions_visited | crossing_count | fraction_path_region_A | fraction_path_region_B | regime_balance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | 0.000 | SUCCESS | 94.367 | 94.367 | 24.486 | 36.655 | 2.574 | 398.107 | 0.353 | 0.391 | 156.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | 0.250 | SUCCESS | 99.544 | 96.881 | 49.444 | 38.224 | 2.604 | 358.020 | 0.369 | 0.625 | 160.000 | 0.078 | 0.922 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | 0.500 | SUCCESS | 87.243 | 87.734 | 69.782 | 38.805 | 2.248 | 309.576 | 0.313 | 0.627 | 150.000 | 0.066 | 0.934 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | 0.750 | SUCCESS | 76.162 | 91.642 | 66.063 | 38.884 | 1.959 | 159.570 | 0.295 | 0.667 | 156.000 | 0.072 | 0.928 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | 1.000 | SUCCESS | 80.016 | 52.740 | 80.016 | 38.928 | 2.055 | 91.487 | 0.215 | 1.000 | 93.000 | 0.029 | 0.971 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | 0.000 | SUCCESS | 94.367 | 94.367 | 55.558 | 36.655 | 2.574 | 398.107 | 0.353 | 0.391 | 156.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | 0.250 | SUCCESS | 106.093 | 87.323 | 115.839 | 38.209 | 2.777 | 351.728 | 0.345 | 0.986 | 148.000 | 0.078 | 0.922 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | 0.500 | SUCCESS | 123.294 | 96.738 | 125.867 | 38.525 | 3.200 | 316.762 | 0.335 | 0.951 | 164.000 | 0.070 | 0.930 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | 0.750 | SUCCESS | 129.721 | 88.141 | 135.170 | 39.984 | 3.244 | 179.432 | 0.218 | 1.000 | 156.000 | 0.068 | 0.932 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | 1.000 | SUCCESS | 142.109 | 93.864 | 142.109 | 40.113 | 3.543 | 89.566 | 0.245 | 1.000 | 163.000 | 0.074 | 0.926 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | 0.000 | SUCCESS | 94.367 | 94.367 | 76.252 | 36.655 | 2.574 | 398.107 | 0.353 | 0.391 | 156.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | 0.250 | SUCCESS | 105.635 | 87.505 | 120.629 | 38.507 | 2.743 | 370.851 | 0.368 | 0.799 | 144.000 | 0.075 | 0.925 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | 0.500 | SUCCESS | 125.240 | 95.859 | 135.779 | 38.249 | 3.274 | 311.448 | 0.276 | 0.761 | 163.000 | 0.074 | 0.926 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | 0.750 | SUCCESS | 135.831 | 92.400 | 141.500 | 38.933 | 3.489 | 189.157 | 0.331 | 0.962 | 157.000 | 0.083 | 0.917 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | 1.000 | SUCCESS | 149.732 | 93.691 | 149.732 | 39.252 | 3.815 | 92.594 | 0.282 | 1.000 | 163.000 | 0.056 | 0.944 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_score | 0.000 | SUCCESS | 94.367 | 94.367 | 116.153 | 36.655 | 2.574 | 398.107 | 0.353 | 0.038 | 156.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_score | 0.250 | SUCCESS | 102.473 | 94.885 | 130.545 | 37.992 | 2.697 | 337.176 | 0.391 | 0.199 | 156.000 | 0.102 | 0.898 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_score | 0.500 | SUCCESS | 117.251 | 91.255 | 138.618 | 38.192 | 3.070 | 239.174 | 0.270 | 0.264 | 159.000 | 0.023 | 0.977 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_score | 0.750 | SUCCESS | 119.631 | 81.378 | 126.086 | 37.597 | 3.182 | 203.840 | 0.221 | 0.248 | 145.000 | 0.083 | 0.917 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | boundary_score | 1.000 | SUCCESS | 134.886 | 79.612 | 134.886 | 37.615 | 3.586 | 113.652 | 0.199 | 0.160 | 156.000 | 0.054 | 0.946 | 1.000 | 0.000 | 0.224 | 0.000 | 0.000 |
| C01_representative | 12.000 | interest_map | 0.000 | SUCCESS | 94.367 | 94.367 | 54.295 | 36.655 | 2.574 | 398.107 | 0.353 | 0.000 | 156.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | interest_map | 0.250 | SUCCESS | 94.140 | 93.931 | 54.569 | 37.700 | 2.497 | 366.801 | 0.383 | 0.000 | 154.000 | 0.148 | 0.852 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | interest_map | 0.500 | SUCCESS | 98.717 | 87.340 | 57.779 | 37.169 | 2.656 | 289.496 | 0.313 | 0.120 | 150.000 | 0.089 | 0.911 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | interest_map | 0.750 | SUCCESS | 81.250 | 83.144 | 60.235 | 38.719 | 2.098 | 279.107 | 0.174 | 0.228 | 149.000 | 0.045 | 0.955 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| C01_representative | 12.000 | interest_map | 1.000 | SUCCESS | 62.333 | 83.847 | 62.333 | 37.346 | 1.669 | 98.403 | 0.136 | 0.279 | 154.000 | 0.033 | 0.967 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Baseline comparison
Each descriptor-alpha row is compared with its STD-only baseline (`alpha=0`) for the same descriptor. Positive reward/STD deltas mean the route accumulated more of that proxy than the baseline; positive route-length/runtime deltas mean higher operational cost.
| descriptor | alpha | total_collected_reward | delta_total_collected_reward_vs_baseline | pct_total_collected_reward_vs_baseline | collected_STD | delta_collected_STD_vs_baseline | pct_collected_STD_vs_baseline | route_length_km | delta_route_length_km_vs_baseline | reward_per_distance_km | delta_reward_per_distance_km_vs_baseline | solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r1_cells | 0.000 | 94.367 | 0.000 | 0.000 | 94.367 | 0.000 | 0.000 | 36.655 | 0.000 | 2.574 | 0.000 | 398.107 |
| boundary_distance_score_r1_cells | 0.250 | 99.544 | 5.178 | 0.055 | 96.881 | 2.515 | 0.027 | 38.224 | 1.569 | 2.604 | 0.030 | 358.020 |
| boundary_distance_score_r1_cells | 0.500 | 87.243 | -7.123 | -0.075 | 87.734 | -6.632 | -0.070 | 38.805 | 2.150 | 2.248 | -0.326 | 309.576 |
| boundary_distance_score_r1_cells | 0.750 | 76.162 | -18.205 | -0.193 | 91.642 | -2.724 | -0.029 | 38.884 | 2.229 | 1.959 | -0.616 | 159.570 |
| boundary_distance_score_r1_cells | 1.000 | 80.016 | -14.351 | -0.152 | 52.740 | -41.626 | -0.441 | 38.928 | 2.273 | 2.055 | -0.519 | 91.487 |
| boundary_distance_score_r3_cells | 0.000 | 94.367 | 0.000 | 0.000 | 94.367 | 0.000 | 0.000 | 36.655 | 0.000 | 2.574 | 0.000 | 398.107 |
| boundary_distance_score_r3_cells | 0.250 | 106.093 | 11.726 | 0.124 | 87.323 | -7.044 | -0.075 | 38.209 | 1.554 | 2.777 | 0.202 | 351.728 |
| boundary_distance_score_r3_cells | 0.500 | 123.294 | 28.927 | 0.307 | 96.738 | 2.372 | 0.025 | 38.525 | 1.870 | 3.200 | 0.626 | 316.762 |
| boundary_distance_score_r3_cells | 0.750 | 129.721 | 35.355 | 0.375 | 88.141 | -6.226 | -0.066 | 39.984 | 3.329 | 3.244 | 0.670 | 179.432 |
| boundary_distance_score_r3_cells | 1.000 | 142.109 | 47.743 | 0.506 | 93.864 | -0.502 | -0.005 | 40.113 | 3.458 | 3.543 | 0.968 | 89.566 |
| boundary_distance_score_r5_cells | 0.000 | 94.367 | 0.000 | 0.000 | 94.367 | 0.000 | 0.000 | 36.655 | 0.000 | 2.574 | 0.000 | 398.107 |
| boundary_distance_score_r5_cells | 0.250 | 105.635 | 11.269 | 0.119 | 87.505 | -6.862 | -0.073 | 38.507 | 1.852 | 2.743 | 0.169 | 370.851 |
| boundary_distance_score_r5_cells | 0.500 | 125.240 | 30.874 | 0.327 | 95.859 | 1.492 | 0.016 | 38.249 | 1.594 | 3.274 | 0.700 | 311.448 |
| boundary_distance_score_r5_cells | 0.750 | 135.831 | 41.464 | 0.439 | 92.400 | -1.967 | -0.021 | 38.933 | 2.278 | 3.489 | 0.914 | 189.157 |
| boundary_distance_score_r5_cells | 1.000 | 149.732 | 55.366 | 0.587 | 93.691 | -0.676 | -0.007 | 39.252 | 2.597 | 3.815 | 1.240 | 92.594 |
| boundary_score | 0.000 | 94.367 | 0.000 | 0.000 | 94.367 | 0.000 | 0.000 | 36.655 | 0.000 | 2.574 | 0.000 | 398.107 |
| boundary_score | 0.250 | 102.473 | 8.107 | 0.086 | 94.885 | 0.518 | 0.005 | 37.992 | 1.337 | 2.697 | 0.123 | 337.176 |
| boundary_score | 0.500 | 117.251 | 22.885 | 0.243 | 91.255 | -3.112 | -0.033 | 38.192 | 1.537 | 3.070 | 0.496 | 239.174 |
| boundary_score | 0.750 | 119.631 | 25.264 | 0.268 | 81.378 | -12.989 | -0.138 | 37.597 | 0.942 | 3.182 | 0.607 | 203.840 |
| boundary_score | 1.000 | 134.886 | 40.520 | 0.429 | 79.612 | -14.755 | -0.156 | 37.615 | 0.960 | 3.586 | 1.012 | 113.652 |
| interest_map | 0.000 | 94.367 | 0.000 | 0.000 | 94.367 | 0.000 | 0.000 | 36.655 | 0.000 | 2.574 | 0.000 | 398.107 |
| interest_map | 0.250 | 94.140 | -0.226 | -0.002 | 93.931 | -0.435 | -0.005 | 37.700 | 1.045 | 2.497 | -0.077 | 366.801 |
| interest_map | 0.500 | 98.717 | 4.351 | 0.046 | 87.340 | -7.027 | -0.074 | 37.169 | 0.514 | 2.656 | 0.081 | 289.496 |
| interest_map | 0.750 | 81.250 | -13.117 | -0.139 | 83.144 | -11.223 | -0.119 | 38.719 | 2.064 | 2.098 | -0.476 | 279.107 |
| interest_map | 1.000 | 62.333 | -32.034 | -0.339 | 83.847 | -10.519 | -0.111 | 37.346 | 0.691 | 1.669 | -0.905 | 98.403 |

## Rankings
The ranking uses four thesis-oriented criteria: reward efficiency, preservation of accumulated STD reward, descriptor/boundary coverage, and operational feasibility. The composite rank is only a decision aid; the raw columns above should remain the primary evidence.
| descriptor | alpha | total_collected_reward | reward_per_distance_km | STD_retention | descriptor_coverage_score | operational_feasibility_score | overall_rank_score | rank_reward_efficiency | rank_std_preservation | rank_descriptor_coverage | rank_operational_feasibility | rank_overall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r5_cells | 1.000 | 149.732 | 3.815 | 0.993 | 1.000 | 0.658 | 0.918 | 1.000 | 12.000 | 1.000 | 5.000 | 1.000 |
| boundary_distance_score_r3_cells | 1.000 | 142.109 | 3.543 | 0.995 | 1.000 | 0.550 | 0.859 | 3.000 | 11.000 | 1.000 | 10.000 | 2.000 |
| boundary_distance_score_r5_cells | 0.750 | 135.831 | 3.489 | 0.979 | 0.932 | 0.558 | 0.832 | 4.000 | 13.000 | 5.000 | 9.000 | 3.000 |
| boundary_distance_score_r3_cells | 0.750 | 129.721 | 3.244 | 0.934 | 0.968 | 0.436 | 0.772 | 6.000 | 16.000 | 4.000 | 20.000 | 4.000 |
| boundary_distance_score_r3_cells | 0.500 | 123.294 | 3.200 | 1.025 | 0.896 | 0.425 | 0.767 | 7.000 | 2.000 | 6.000 | 21.000 | 5.000 |
| boundary_distance_score_r5_cells | 0.500 | 125.240 | 3.274 | 1.016 | 0.780 | 0.469 | 0.755 | 5.000 | 3.000 | 8.000 | 16.000 | 6.000 |
| boundary_score | 1.000 | 134.886 | 3.586 | 0.844 | 0.430 | 0.840 | 0.744 | 2.000 | 24.000 | 16.000 | 2.000 | 7.000 |
| boundary_score | 0.500 | 117.251 | 3.070 | 0.967 | 0.558 | 0.582 | 0.682 | 9.000 | 15.000 | 13.000 | 8.000 | 8.000 |
| boundary_distance_score_r3_cells | 0.250 | 106.093 | 2.777 | 0.925 | 0.870 | 0.415 | 0.676 | 10.000 | 20.000 | 7.000 | 22.000 | 9.000 |
| boundary_score | 0.750 | 119.631 | 3.182 | 0.862 | 0.326 | 0.711 | 0.640 | 8.000 | 23.000 | 18.000 | 3.000 | 10.000 |
| boundary_distance_score_r5_cells | 0.250 | 105.635 | 2.743 | 0.927 | 0.721 | 0.349 | 0.621 | 11.000 | 18.000 | 9.000 | 25.000 | 11.000 |
| boundary_distance_score_r1_cells | 0.250 | 99.544 | 2.604 | 1.027 | 0.555 | 0.404 | 0.595 | 14.000 | 1.000 | 14.000 | 23.000 | 12.000 |
| boundary_distance_score_r1_cells | 1.000 | 80.016 | 2.055 | 0.559 | 1.000 | 0.701 | 0.577 | 23.000 | 25.000 | 1.000 | 4.000 | 13.000 |
| boundary_score | 0.250 | 102.473 | 2.697 | 1.005 | 0.375 | 0.465 | 0.570 | 12.000 | 4.000 | 17.000 | 17.000 | 14.000 |
| boundary_distance_score_r1_cells | 0.750 | 76.162 | 1.959 | 0.971 | 0.699 | 0.608 | 0.568 | 24.000 | 14.000 | 11.000 | 7.000 | 15.000 |
| boundary_distance_score_r1_cells | 0.500 | 87.243 | 2.248 | 0.930 | 0.702 | 0.399 | 0.558 | 21.000 | 17.000 | 10.000 | 24.000 | 16.000 |
| interest_map | 0.500 | 98.717 | 2.656 | 0.926 | 0.245 | 0.642 | 0.548 | 13.000 | 19.000 | 19.000 | 6.000 | 17.000 |
| boundary_distance_score_r1_cells | 0.000 | 94.367 | 2.574 | 1.000 | 0.235 | 0.550 | 0.533 | 15.000 | 5.000 | 20.000 | 10.000 | 18.000 |
| boundary_distance_score_r3_cells | 0.000 | 94.367 | 2.574 | 1.000 | 0.235 | 0.550 | 0.533 | 15.000 | 5.000 | 20.000 | 10.000 | 18.000 |
| boundary_distance_score_r5_cells | 0.000 | 94.367 | 2.574 | 1.000 | 0.235 | 0.550 | 0.533 | 15.000 | 5.000 | 20.000 | 10.000 | 18.000 |
| interest_map | 1.000 | 62.333 | 1.669 | 0.889 | 0.568 | 0.897 | 0.533 | 25.000 | 21.000 | 12.000 | 1.000 | 21.000 |
| boundary_score | 0.000 | 94.367 | 2.574 | 1.000 | 0.023 | 0.550 | 0.480 | 15.000 | 5.000 | 23.000 | 10.000 | 22.000 |
| interest_map | 0.000 | 94.367 | 2.574 | 1.000 | 0.000 | 0.550 | 0.475 | 15.000 | 5.000 | 25.000 | 10.000 | 23.000 |
| interest_map | 0.750 | 81.250 | 2.098 | 0.881 | 0.433 | 0.455 | 0.469 | 22.000 | 22.000 | 15.000 | 19.000 | 24.000 |
| interest_map | 0.250 | 94.140 | 2.497 | 0.995 | 0.014 | 0.460 | 0.448 | 20.000 | 10.000 | 24.000 | 18.000 | 25.000 |

## Descriptor comparison
- `boundary_distance_score_r5_cells` is best represented by alpha=1.00 in this run: reward efficiency=3.815, STD retention=0.993, descriptor coverage score=1.000, route=39.252 km, runtime=92.594 s.
- `boundary_distance_score_r3_cells` is best represented by alpha=1.00 in this run: reward efficiency=3.543, STD retention=0.995, descriptor coverage score=1.000, route=40.113 km, runtime=89.566 s.
- `boundary_score` is best represented by alpha=1.00 in this run: reward efficiency=3.586, STD retention=0.844, descriptor coverage score=0.430, route=37.615 km, runtime=113.652 s.
- `boundary_distance_score_r1_cells` is best represented by alpha=0.25 in this run: reward efficiency=2.604, STD retention=1.027, descriptor coverage score=0.555, route=38.224 km, runtime=358.020 s.
- `interest_map` is best represented by alpha=0.50 in this run: reward efficiency=2.656, STD retention=0.926, descriptor coverage score=0.245, route=37.169 km, runtime=289.496 s.

## Boundary-distance radius comparison
- `boundary_distance_score_r1_cells` best alpha=0.25: overall=0.595, efficiency=2.604, STD retention=1.027, coverage=0.555.
- `boundary_distance_score_r3_cells` best alpha=1.00: overall=0.859, efficiency=3.543, STD retention=0.995, coverage=1.000.
- `boundary_distance_score_r5_cells` best alpha=1.00: overall=0.918, efficiency=3.815, STD retention=0.993, coverage=1.000.
- r1 behaves as a narrow boundary proxy: it is less competitive on descriptor coverage and overall utility than r3.
- r5 remains competitive, but its broader boundary band should be described as lower selectivity unless it also improves efficiency.

## Recommended combination
The recommended non-baseline combination is `boundary_distance_score_r5_cells` with alpha=1.00.
It is recommended because it gives the strongest combined balance in this run: reward efficiency=3.815, STD retention=0.993, descriptor/boundary coverage score=1.000, operational feasibility=0.658, and overall score=0.918.
This should be described as a reward-map sensitivity and potential-informativeness result, not as demonstrated data-assimilation uncertainty reduction.

## Thesis wording guardrails
- Use: potential informativeness, accumulated uncertainty proxy, boundary/regime coverage, reward-map sensitivity, operational efficiency.
- Avoid claiming actual data-assimilation uncertainty reduction, because these outputs evaluate planner reward proxies rather than a completed assimilation experiment.

## Generated plots
- `figures/step12a_alpha_vs_reward.png`
- `figures/step12a_alpha_vs_route_length.png`
- `figures/step12a_alpha_vs_reward_efficiency.png`
- `figures/step12a_descriptor_alpha_ranking.png`

## Existing diagnostics and figures inspected
- Diagnostics/log-like files found: 48.
- Existing figures/media found: 71.
