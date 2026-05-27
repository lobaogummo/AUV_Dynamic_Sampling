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
