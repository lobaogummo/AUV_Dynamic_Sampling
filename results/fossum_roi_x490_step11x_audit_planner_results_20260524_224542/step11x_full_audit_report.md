# Step11X audit summary

- Outputs analyzed: 9
- Missing expected files/outputs: 0
- Warnings: 0
- Verdict: `READY_FOR_STEP11E_VEHICLE_SPECIFIC_PRIZES`

## Main conclusions

1. Step11A succeeded as a baseline-vs-static-descriptor integration test, but boundary-only does not provide a clean regime-aware behavior guarantee.
2. Step11C showed that crossing proxies can change behavior, but gamma sensitivity is non-monotonic and route-level crossing reward is not actually supported.
3. Step11D suggests the multi-AUV issue is specialization by regime more than raw overlap reduction.
4. boundary_score has limited standalone value as the next final descriptor; role-defining descriptors are more promising for multi-AUV.
5. Step11E should prioritize vehicle-specific prize maps, with a narrow descriptor ablation as supporting evidence.

## Evidence snapshots

### Step11C crossing counts

| source_output | case_id | run_name | mission_duration_requested_h | gamma | crossing_count | regions_visited |
| --- | --- | --- | --- | --- | --- | --- |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | baseline_STD | 12.000 | 0.000 | 0.000 | 1.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | boundary_alpha050 | 12.000 | 0.000 | 6.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | crossing_gamma025 | 12.000 | 0.250 | 10.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | crossing_gamma050 | 12.000 | 0.500 | 2.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | baseline_STD_6h | 6.000 | 0.000 | 4.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | boundary_alpha050_6h | 6.000 | 0.000 | 6.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322 | C01_representative | crossing_gamma050_6h | 6.000 | 0.500 | 0.000 | 1.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | baseline_STD | 12.000 | 0.000 | 3.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | boundary_alpha050 | 12.000 | 0.000 | 6.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | crossing_gamma025 | 12.000 | 0.250 | 3.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | C06_representative | crossing_gamma050 | 12.000 | 0.500 | 9.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | baseline_STD | 12.000 | 0.000 | 6.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | boundary_alpha050 | 12.000 | 0.000 | 8.000 | 2.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | crossing_gamma025 | 12.000 | 0.250 | 0.000 | 1.000 |
| fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458 | October_control | crossing_gamma050 | 12.000 | 0.500 | 0.000 | 1.000 |

### Step11D fleet comparison

| source_output | case_id | strategy | fleet_region_B_coverage | trajectory_overlap_ratio | fleet_collected_STD | solver_status |
| --- | --- | --- | --- | --- | --- | --- |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_baseline_STD | 0.014 | 0.000 | 182.088 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_boundary_alpha050 | 0.019 | 0.000 | 185.071 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_regime_maps | 0.031 | 0.016 | 183.943 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_with_crossing_proxy | 0.029 | 0.010 | 174.382 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | sequential_overlap_reduction | 0.027 | 0.023 | 183.459 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | post_solver_selected_pair | 0.030 | 0.023 | 185.289 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_baseline_STD | 0.002 | 0.000 | 158.327 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_boundary_alpha050 | 0.001 | 0.000 | 152.327 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_regime_maps | 0.034 | 0.026 | 137.697 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_with_crossing_proxy | 0.033 | 0.003 | 134.090 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | sequential_overlap_reduction | 0.038 | 0.013 | 130.039 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | post_solver_selected_pair | 0.033 | 0.003 | 142.361 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_baseline_STD | 0.075 | 0.019 | 184.508 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_boundary_alpha050 | 0.000 | 0.000 | 100.917 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_regime_maps | 0.041 | 0.003 | 162.201 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_with_crossing_proxy | 0.041 | 0.016 | 161.909 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | sequential_overlap_reduction | 0.040 | 0.003 | 154.978 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | post_solver_selected_pair | 0.041 | 0.003 | 162.201 | POST_SOLVER_PROXY |

### Descriptor correlation

| case_id | descriptor | pearson_STD_descriptor | top10_jaccard | hotspot_distance_pixels |
| --- | --- | --- | --- | --- |
| C01_representative | boundary_score | 0.307 | 0.155 | 23.972 |
| C01_representative | gradient | -0.086 | 0.036 | 42.084 |
| C01_representative | heterogeneity | -0.127 | 0.054 | 38.704 |
| C01_representative | representative_zone | 0.506 | 0.097 | 5.119 |
| C01_representative | interest_map | 0.279 | 0.133 | 21.101 |
| C01_representative | cold_region | -0.363 | 0.010 | 42.925 |
| C01_representative | warm_region | -0.266 | 0.034 | 38.250 |
| C06_representative | boundary_score | 0.694 | 0.173 | 12.681 |
| C06_representative | gradient | 0.172 | 0.180 | 3.111 |
| C06_representative | heterogeneity | -0.249 | 0.015 | 68.078 |
| C06_representative | representative_zone | -0.355 | 0.004 | 41.446 |
| C06_representative | interest_map | 0.685 | 0.172 | 8.308 |
| C06_representative | cold_region | 0.467 | 0.215 | 11.418 |
| C06_representative | warm_region | -0.538 | 0.000 | 72.647 |
| October_control | boundary_score | -0.877 | 0.000 | 76.707 |
| October_control | gradient | -0.344 | 0.000 | 76.707 |
| October_control | heterogeneity | 0.428 | 0.128 | 3.872 |
| October_control | representative_zone | 0.638 | 0.016 | 32.576 |
| October_control | interest_map | -0.859 | 0.000 | 77.637 |
| October_control | cold_region | -0.818 | 0.000 | 70.041 |
| October_control | warm_region | 0.609 | 0.235 | 4.202 |


# Step11A diagnosis

- Boundary-only maps changed the sampled-cell set in 100% of enriched comparisons by the saved overlap metric.
- The change often carried an STD cost: 78% of enriched comparisons lost collected STD relative to baseline.
- Boundary collection improved in 67% of enriched comparisons, so the descriptor had signal but was not always aligned with preserving STD.

## Runtime coverage

- 2auv_12h: 9 metric rows
- unknown_runtime: 18 metric rows

## Key table

| runtime_label | case_id | formulation | alpha | trajectory_difference_from_baseline | delta_collected_STD_score | delta_collected_boundary_score | solver_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2auv_12h | C01_representative | enriched_boundary_alpha025 | 0.250 | 0.876 | -6.475 | 3.078 | SUCCESS |
| 2auv_12h | C01_representative | enriched_boundary_alpha050 | 0.500 | 0.891 | -16.344 | -8.541 | SUCCESS |
| 2auv_12h | C06_representative | enriched_boundary_alpha025 | 0.250 | 0.828 | -1.271 | 9.250 | SUCCESS |
| 2auv_12h | C06_representative | enriched_boundary_alpha050 | 0.500 | 0.906 | -6.444 | 36.553 | SUCCESS |
| 2auv_12h | October_control | enriched_boundary_alpha025 | 0.250 | 0.907 | -3.755 | 2.053 | SUCCESS |
| 2auv_12h | October_control | enriched_boundary_alpha050 | 0.500 | 0.985 | -60.468 | 122.187 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha025 | 0.250 | 0.856 | 0.913 | 0.886 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha025 | 0.250 | 0.927 | -4.152 | -5.150 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha050 | 0.500 | 0.928 | -4.626 | -5.726 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha050 | 0.500 | 0.867 | -8.304 | -6.341 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha025 | 0.250 | 0.892 | -1.501 | -0.297 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha025 | 0.250 | 0.907 | 0.629 | 21.343 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha050 | 0.500 | 0.918 | 1.891 | 5.889 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha050 | 0.500 | 0.961 | -3.017 | 20.887 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha025 | 0.250 | 0.860 | 4.910 | 0.854 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha025 | 0.250 | 0.880 | -12.741 | -1.806 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha050 | 0.500 | 0.993 | -10.683 | 24.022 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha050 | 0.500 | 0.997 | -47.119 | 77.174 | SUCCESS |

## STD-boundary redundancy

Mean Pearson correlation STD vs boundary_score across Step10F cases: 0.042.
Mean top-10% Jaccard overlap: 0.109.
This supports treating boundary_score as partly redundant only in a broad spatial-gradient sense; hotspot overlap is not uniformly high.

## Interpretation

- Step11A worked as a first integration test: the planner received different static prize maps and returned feasible routes.
- It did not prove that boundary_score alone solves regime-aware planning. The response is mixed: some boundary gains are small, and higher alpha can reduce STD sharply.
- The 2-AUV 12h run should be interpreted as shared-map fleet behavior, not true vehicle specialization.

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

# Step11D strategy comparison

## Fleet evidence

| source_output | case_id | strategy | fleet_collected_STD | fleet_collected_boundary | fleet_region_A_coverage | fleet_region_B_coverage | trajectory_overlap_ratio | duplicate_sampled_cells | inter_vehicle_mean_distance | fleet_complementarity_score | solver_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_baseline_STD | 182.088 | 236.057 | 0.062 | 0.014 | 0.000 | 0.000 | 12.889 | 0.538 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_boundary_alpha050 | 185.071 | 260.681 | 0.062 | 0.019 | 0.000 | 0.000 | 12.442 | 0.541 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | post_solver_selected_pair | 185.289 | 218.232 | 0.047 | 0.030 | 0.023 | 7.000 | 12.745 | 0.528 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | sequential_overlap_reduction | 183.459 | 223.885 | 0.049 | 0.027 | 0.023 | 7.000 | 20.027 | 0.527 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_regime_maps | 183.943 | 219.489 | 0.047 | 0.031 | 0.016 | 5.000 | 19.498 | 0.531 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_with_crossing_proxy | 174.382 | 226.014 | 0.046 | 0.029 | 0.010 | 3.000 | 12.066 | 0.533 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_baseline_STD | 158.327 | 236.278 | 0.075 | 0.002 | 0.000 | 0.000 | 8.984 | 0.538 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_boundary_alpha050 | 152.327 | 225.651 | 0.073 | 0.001 | 0.000 | 0.000 | 7.934 | 0.537 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | post_solver_selected_pair | 142.361 | 204.811 | 0.046 | 0.033 | 0.003 | 1.000 | 19.034 | 0.538 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | sequential_overlap_reduction | 130.039 | 166.981 | 0.039 | 0.038 | 0.013 | 4.000 | 25.644 | 0.532 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_regime_maps | 137.697 | 199.366 | 0.042 | 0.034 | 0.026 | 8.000 | 16.746 | 0.525 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_with_crossing_proxy | 134.090 | 207.369 | 0.045 | 0.033 | 0.003 | 1.000 | 13.330 | 0.537 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_baseline_STD | 184.508 | 59.120 | 0.004 | 0.075 | 0.019 | 6.000 | 14.615 | 0.530 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_boundary_alpha050 | 100.917 | 213.799 | 0.079 | 0.000 | 0.000 | 0.000 | 8.908 | 0.540 | REUSED_STEP11D |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | post_solver_selected_pair | 162.201 | 96.463 | 0.038 | 0.041 | 0.003 | 1.000 | 17.884 | 0.538 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | sequential_overlap_reduction | 154.978 | 90.784 | 0.037 | 0.040 | 0.003 | 1.000 | 14.040 | 0.537 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_regime_maps | 162.201 | 96.463 | 0.038 | 0.041 | 0.003 | 1.000 | 13.460 | 0.538 | POST_SOLVER_PROXY |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_with_crossing_proxy | 161.909 | 96.698 | 0.037 | 0.041 | 0.016 | 5.000 | 19.131 | 0.531 | POST_SOLVER_PROXY |

## Vehicle-level specialization evidence

| source_output | case_id | strategy | vehicle_id | fraction_path_region_A | fraction_path_region_B | collected_STD | collected_boundary | crossing_count | regions_visited |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_baseline_STD | 1.000 | 0.717 | 0.283 | 86.720 | 108.026 | 14.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_baseline_STD | 2.000 | 0.892 | 0.108 | 95.368 | 128.030 | 8.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_boundary_alpha050 | 1.000 | 0.652 | 0.348 | 94.377 | 127.734 | 12.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | multi_boundary_alpha050 | 2.000 | 0.858 | 0.142 | 90.695 | 132.947 | 2.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | post_solver_selected_pair | 1.000 | 0.205 | 0.795 | 87.800 | 93.219 | 6.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | post_solver_selected_pair | 2.000 | 1.000 | 0.000 | 97.489 | 125.013 | 0.000 | 1.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | sequential_overlap_reduction | 1.000 | 0.987 | 0.013 | 96.143 | 126.270 | 4.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | sequential_overlap_reduction | 2.000 | 0.290 | 0.710 | 87.316 | 97.615 | 14.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_regime_maps | 1.000 | 0.987 | 0.013 | 96.143 | 126.270 | 4.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_regime_maps | 2.000 | 0.205 | 0.795 | 87.800 | 93.219 | 6.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_with_crossing_proxy | 1.000 | 0.980 | 0.020 | 88.823 | 125.285 | 6.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809 | C01_representative | vehicle_specific_with_crossing_proxy | 2.000 | 0.240 | 0.760 | 85.559 | 100.729 | 10.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_baseline_STD | 1.000 | 0.980 | 0.020 | 77.372 | 114.809 | 3.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_baseline_STD | 2.000 | 0.981 | 0.019 | 80.955 | 121.469 | 4.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_boundary_alpha050 | 1.000 | 0.993 | 0.007 | 73.767 | 109.339 | 2.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | multi_boundary_alpha050 | 2.000 | 0.973 | 0.027 | 78.559 | 116.312 | 6.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | post_solver_selected_pair | 1.000 | 0.994 | 0.006 | 84.748 | 120.925 | 3.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | post_solver_selected_pair | 2.000 | 0.166 | 0.834 | 57.613 | 83.886 | 22.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | sequential_overlap_reduction | 1.000 | 0.968 | 0.032 | 80.084 | 115.480 | 9.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | sequential_overlap_reduction | 2.000 | 0.063 | 0.937 | 49.955 | 51.501 | 10.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_regime_maps | 1.000 | 0.968 | 0.032 | 80.084 | 115.480 | 9.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_regime_maps | 2.000 | 0.166 | 0.834 | 57.613 | 83.886 | 22.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_with_crossing_proxy | 1.000 | 0.987 | 0.013 | 76.478 | 123.483 | 3.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | C06_representative | vehicle_specific_with_crossing_proxy | 2.000 | 0.166 | 0.834 | 57.613 | 83.886 | 22.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_baseline_STD | 1.000 | 0.079 | 0.921 | 93.740 | 26.690 | 6.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_baseline_STD | 2.000 | 0.031 | 0.969 | 90.768 | 32.430 | 9.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_boundary_alpha050 | 1.000 | 1.000 | 0.000 | 51.103 | 112.799 | 0.000 | 1.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | multi_boundary_alpha050 | 2.000 | 0.988 | 0.012 | 49.814 | 101.000 | 4.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | post_solver_selected_pair | 1.000 | 0.062 | 0.938 | 91.175 | 30.362 | 9.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | post_solver_selected_pair | 2.000 | 0.923 | 0.077 | 71.026 | 66.101 | 16.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | sequential_overlap_reduction | 1.000 | 0.923 | 0.077 | 71.026 | 66.101 | 16.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | sequential_overlap_reduction | 2.000 | 0.033 | 0.967 | 83.952 | 24.683 | 7.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_regime_maps | 1.000 | 0.923 | 0.077 | 71.026 | 66.101 | 16.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_regime_maps | 2.000 | 0.062 | 0.938 | 91.175 | 30.362 | 9.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_with_crossing_proxy | 1.000 | 0.893 | 0.107 | 70.734 | 66.336 | 20.000 | 2.000 |
| fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935 | October_control | vehicle_specific_with_crossing_proxy | 2.000 | 0.062 | 0.938 | 91.175 | 30.362 | 9.000 | 2.000 |

- Baseline overlap was already near zero in 67% of native baseline rows, so overlap is not the main bottleneck.
- vehicle_specific_regime_maps improved mean B coverage by 0.0047 but changed mean STD by -13.69.
- The strongest thesis-safe statement is: vehicle-specific regime roles are useful, but the current implementation is a wrapper/proxy because native vehicle-specific prize maps are not supported.
- Post-solver selected pairs are excellent diagnostics but weaker as an operational planner contribution unless formalized into the planner workflow.

# Descriptor redundancy analysis

| descriptor | mean_pearson | mean_spearman | mean_top10_jaccard | mean_hotspot_distance |
| --- | --- | --- | --- | --- |
| representative_zone | 0.263 | 0.236 | 0.039 | 26.380 |
| boundary_score | 0.042 | 0.066 | 0.109 | 37.787 |
| interest_map | 0.035 | 0.066 | 0.102 | 35.682 |
| heterogeneity | 0.017 | 0.032 | 0.066 | 36.885 |
| warm_region | -0.065 | -0.064 | 0.090 | 38.366 |
| gradient | -0.086 | -0.022 | 0.072 | 40.634 |
| cold_region | -0.238 | -0.225 | 0.075 | 41.462 |

- boundary_score is not fully redundant by top-hotspot overlap, but it often follows broad high-value spatial structures and can still pull vehicles toward similar areas.
- Lower-redundancy descriptors worth testing first: cold_region, gradient, warm_region.
- For multi-AUV separation, cold/warm or representative-zone maps are more directly role-defining than boundary_score.

# Planner limitations summary

## Observed capabilities

- Static prize by node: supported through `information_map`.
- Native multi-AUV with a shared prize map: supported.
- Baseline STD objective: supported.
- Enriched static map `(1-alpha)*STD + alpha*descriptor`: supported as a wrapper/input-map change.

## Current limitations

- Route-level reward: not supported in the observed Step11C runs; crossing reward was implemented as a static-map proxy.
- Vehicle-specific prize maps: not supported natively in the observed Step11D runs; vehicle-specific strategies were proxy/post-solver constructions.
- Overlap/proximity penalty: not supported directly in the native objective; sequential/post-solver variants are wrappers.
- Sequential planning: usable as an external wrapper, not a native joint objective.

## Consequence

The planner can test whether descriptors make good static prize maps, but it cannot yet express the two most interesting behavioral objectives directly: "cross this boundary along the route" and "assign different regime roles to different vehicles".


# Next experiments plan

1. Keep C01 2024-08-24, C06 2023-12-22, and October 2024-10-30 as the controlled case set, but label confidence and regime type explicitly.
2. For single-AUV, repeat only baseline_STD, boundary_alpha050, crossing_gamma025, and one improved crossing proxy; avoid a broad gamma sweep until the proxy is cleaner.
3. For multi-AUV, prioritize true or emulated vehicle-specific prize maps: AUV1 = regime_A/STD blend and AUV2 = regime_B/STD blend.
4. Treat post-solver selection as diagnostic evidence, not the final operational method.
5. Keep overlap penalty as secondary unless future native runs show nonzero duplicate sampling is the dominant failure.


# Step11E recommendation

Primary option: **Option B - Step11E = vehicle-specific prize maps**.

Justification: Step11D indicates the key multi-AUV problem is not merely duplicate-cell overlap. Native shared-map multi-AUV can already avoid exact overlap, but vehicles still chase similar value structures unless they are given different regime roles. Vehicle-specific prize maps are therefore the most direct next planner improvement and the strongest thesis contribution.

Secondary option: **Option A - descriptor ablation test**.

Reason: boundary_score alone is not a complete descriptor solution. A narrow ablation over representative_zone, interest_map, gradient, and heterogeneity should be used to choose better static maps or role maps, but it should not replace the need for vehicle-specific objectives in the multi-AUV setting.

Verdict: `READY_FOR_STEP11E_VEHICLE_SPECIFIC_PRIZES`.
