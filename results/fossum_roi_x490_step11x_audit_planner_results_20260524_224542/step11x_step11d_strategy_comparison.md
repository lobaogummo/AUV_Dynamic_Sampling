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