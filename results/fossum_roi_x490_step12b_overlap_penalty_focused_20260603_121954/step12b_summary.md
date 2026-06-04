# Step12B multi-AUV vehicle-specific weight sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Fleet rows: 72
- Vehicle rows: 144
- Prototype-based maps only: True
- TEMPpred used as objective: False
- Overlap/proximity penalty enabled: True
- Penalty comparison rows: 32

## Best weight recommendation
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | STD_retention | fleet_region_B_coverage | regime_specialization_score | trajectory_overlap_ratio | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.901 | 0.037 | 0.454 | 0.020 | 522.599 | 0.560 |
| C01_representative | 24.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.883 | 0.105 | 0.591 | 0.006 | 532.608 | 0.592 |
| C01_representative | 48.000 | vehicle_specific_7030_penalty_both | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.901 | 0.236 | 0.585 | 0.011 | 638.658 | 0.626 |
| C06_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.757 | 0.033 | 0.550 | 0.004 | 588.741 | 0.527 |
| C06_representative | 24.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.800 | 0.100 | 0.768 | 0.002 | 615.744 | 0.600 |
| C06_representative | 48.000 | vehicle_specific_7030_penalty_both | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.992 | 0.174 | 0.563 | 0.021 | 689.210 | 0.636 |
| October_control | 12.000 | vehicle_specific_7030_penalty_both | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.808 | 0.039 | 0.692 | 0.003 | 577.574 | 0.586 |
| October_control | 24.000 | vehicle_specific_7030_penalty_both | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.920 | 0.129 | 0.546 | 0.010 | 500.444 | 0.577 |
| October_control | 48.000 | vehicle_specific_7030_penalty_both | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.993 | 0.297 | 0.452 | 0.026 | 482.681 | 0.610 |


## Weight sensitivity
| strategy | w_STD | w_region | w_boundary | mean_STD_retention | mean_region_B_coverage | mean_specialization | mean_overlap | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vehicle_specific_7030 | 0.700 | 0.300 | 0.000 | 0.888 | 0.117 | 0.564 | 0.028 | 557.590 | 0.586 |
| vehicle_specific_7030_penalty_both | 0.700 | 0.300 | 0.000 | 0.921 | 0.113 | 0.487 | 0.021 | 591.805 | 0.567 |
| vehicle_specific_8020_penalty_both | 0.800 | 0.200 | 0.000 | 0.990 | 0.119 | 0.374 | 0.021 | 630.834 | 0.527 |
| vehicle_specific_8020 | 0.800 | 0.200 | 0.000 | 1.022 | 0.097 | 0.343 | 0.108 | 559.351 | 0.512 |
| vehicle_specific_9010_penalty_both | 0.900 | 0.100 | 0.000 | 1.038 | 0.098 | 0.288 | 0.021 | 662.442 | 0.505 |
| vehicle_specific_9010 | 0.900 | 0.100 | 0.000 | 1.075 | 0.081 | 0.288 | 0.156 | 597.842 | 0.498 |
| role_swap_of_vehicle_specific_7030_penalty_both | 0.700 | 0.300 | 0.000 | 0.950 | 0.153 | 0.064 | 0.026 | 649.590 | 0.495 |
| baseline_shared_STD | 1.000 | 0.000 | 0.000 | 1.000 | 0.072 | 0.164 | 0.004 | 325.337 | 0.473 |
| role_swap_of_vehicle_specific_7030 | 0.700 | 0.300 | 0.000 | 0.835 | 0.069 | 0.000 | 0.008 | 689.909 | 0.451 |


## Duration sensitivity
| mission_duration_requested_h | strategy | mean_fleet_STD | mean_region_B_coverage | mean_specialization | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | baseline_shared_STD | 175.392 | 0.028 | 0.184 | 288.517 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_7030 | 145.106 | 0.035 | 0.000 | 671.961 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_7030_penalty_both | 180.015 | 0.075 | 0.320 | 630.487 | 1.000 |
| 12.000 | vehicle_specific_7030 | 144.924 | 0.036 | 0.564 | 535.182 | 1.000 |
| 12.000 | vehicle_specific_7030_penalty_both | 154.346 | 0.022 | 0.443 | 584.796 | 1.000 |
| 12.000 | vehicle_specific_8020 | 174.054 | 0.036 | 0.283 | 536.483 | 1.000 |
| 12.000 | vehicle_specific_8020_penalty_both | 169.550 | 0.044 | 0.277 | 588.141 | 1.000 |
| 12.000 | vehicle_specific_9010 | 179.341 | 0.033 | 0.258 | 565.035 | 1.000 |
| 12.000 | vehicle_specific_9010_penalty_both | 177.639 | 0.036 | 0.242 | 604.266 | 1.000 |
| 24.000 | baseline_shared_STD | 348.124 | 0.066 | 0.215 | 307.013 | 1.000 |
| 24.000 | role_swap_of_vehicle_specific_7030 | 290.274 | 0.102 | 0.000 | 707.857 | 1.000 |
| 24.000 | role_swap_of_vehicle_specific_7030_penalty_both | 321.648 | 0.119 | 0.000 | 566.821 | 1.000 |
| 24.000 | vehicle_specific_7030 | 299.263 | 0.109 | 0.635 | 543.899 | 1.000 |
| 24.000 | vehicle_specific_7030_penalty_both | 319.591 | 0.082 | 0.485 | 587.102 | 1.000 |
| 24.000 | vehicle_specific_8020 | 344.922 | 0.097 | 0.408 | 556.015 | 1.000 |
| 24.000 | vehicle_specific_8020_penalty_both | 338.663 | 0.105 | 0.423 | 645.135 | 1.000 |
| 24.000 | vehicle_specific_9010 | 364.946 | 0.076 | 0.336 | 584.337 | 1.000 |
| 24.000 | vehicle_specific_9010_penalty_both | 354.165 | 0.085 | 0.360 | 670.687 | 1.000 |
| 48.000 | baseline_shared_STD | 615.961 | 0.124 | 0.095 | 380.480 | 1.000 |
| 48.000 | role_swap_of_vehicle_specific_7030_penalty_both | 580.484 | 0.190 | 0.000 | 683.547 | 1.000 |
| 48.000 | vehicle_specific_7030 | 605.484 | 0.205 | 0.494 | 593.689 | 1.000 |
| 48.000 | vehicle_specific_7030_penalty_both | 591.898 | 0.236 | 0.533 | 603.516 | 1.000 |
| 48.000 | vehicle_specific_8020 | 666.984 | 0.157 | 0.339 | 585.555 | 1.000 |
| 48.000 | vehicle_specific_8020_penalty_both | 636.767 | 0.208 | 0.421 | 659.226 | 1.000 |
| 48.000 | vehicle_specific_9010 | 707.749 | 0.135 | 0.269 | 644.155 | 1.000 |
| 48.000 | vehicle_specific_9010_penalty_both | 665.051 | 0.171 | 0.263 | 712.374 | 1.000 |


## Optional overlap/proximity penalty comparison
| case_id | mission_duration_requested_h | base_strategy | strategy | penalty_mode | lambda_overlap | lambda_proximity | trajectory_overlap_ratio_no_penalty | trajectory_overlap_ratio_penalized | overlap_reduction | duplicate_cell_reduction | fleet_reward_delta | fleet_STD_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.213 | 0.013 | 0.200 | 49.000 | -5.517 | -7.040 |
| C01_representative | 12.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.078 | 0.006 | 0.072 | 20.000 | -3.081 | 2.970 |
| C01_representative | 12.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.020 | 0.017 | 0.003 | 1.000 | -20.502 | -5.464 |
| C06_representative | 12.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.231 | 0.010 | 0.221 | 57.000 | -20.547 | -11.704 |
| C06_representative | 12.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.044 | 0.010 | 0.034 | 10.000 | -9.203 | -5.157 |
| C06_representative | 12.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.004 | 0.057 | -0.054 | -15.000 | -17.438 | 34.302 |
| October_control | 12.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.126 | 0.032 | 0.095 | 25.000 | 4.705 | 3.626 |
| October_control | 12.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.094 | 0.040 | 0.055 | 15.000 | -11.493 | -1.313 |
| October_control | 12.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.003 | 0.003 | 0.000 | 0.000 | -1.198 | -0.570 |
| C01_representative | 24.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.057 | 0.008 | 0.048 | 28.000 | -3.808 | -11.690 |
| C01_representative | 24.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.044 | 0.011 | 0.033 | 19.000 | -10.540 | -5.927 |
| C01_representative | 24.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.006 | 0.025 | -0.018 | -11.000 | -37.502 | 3.885 |
| C06_representative | 24.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.256 | 0.034 | 0.222 | 110.000 | -14.119 | -8.833 |
| C06_representative | 24.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.051 | 0.015 | 0.036 | 21.000 | -7.026 | -6.518 |
| C06_representative | 24.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.002 | 0.016 | -0.015 | -9.000 | -28.726 | 46.842 |
| October_control | 24.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.095 | 0.010 | 0.085 | 49.000 | -28.507 | -11.820 |
| October_control | 24.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.135 | 0.016 | 0.119 | 65.000 | -0.608 | -6.332 |
| October_control | 24.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.025 | 0.010 | 0.016 | 9.000 | 25.115 | 10.256 |
| C01_representative | 48.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.114 | 0.026 | 0.088 | 93.000 | -17.292 | -31.070 |
| C01_representative | 48.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.157 | 0.023 | 0.133 | 141.000 | -76.044 | -59.400 |
| C01_representative | 48.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.070 | 0.011 | 0.059 | 67.000 | 9.380 | -25.140 |
| C06_representative | 48.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.237 | 0.038 | 0.199 | 191.000 | -72.260 | -51.037 |
| C06_representative | 48.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.117 | 0.023 | 0.095 | 101.000 | -31.245 | -48.873 |
| C06_representative | 48.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.038 | 0.021 | 0.017 | 20.000 | -22.604 | -15.436 |
| October_control | 48.000 | vehicle_specific_9010 | vehicle_specific_9010_penalty_both | both | 0.200 | 0.300 | 0.165 | 0.028 | 0.138 | 141.000 | -17.117 | -17.656 |
| October_control | 48.000 | vehicle_specific_8020 | vehicle_specific_8020_penalty_both | both | 0.200 | 0.300 | 0.156 | 0.034 | 0.123 | 128.000 | -68.234 | -10.709 |
| October_control | 48.000 | vehicle_specific_7030 | vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 | 0.083 | 0.026 | 0.057 | 63.000 | -20.759 | -0.184 |
| C01_representative | 48.000 | role_swap_of_vehicle_specific_7030 | role_swap_of_vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 |  | 0.011 |  |  |  |  |
| October_control | 12.000 | role_swap_of_vehicle_specific_7030 | role_swap_of_vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 |  | 0.071 |  |  |  |  |
| C06_representative | 48.000 | role_swap_of_vehicle_specific_7030 | role_swap_of_vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 |  | 0.011 |  |  |  |  |
| October_control | 24.000 | role_swap_of_vehicle_specific_7030 | role_swap_of_vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 |  | 0.023 |  |  |  |  |
| October_control | 48.000 | role_swap_of_vehicle_specific_7030 | role_swap_of_vehicle_specific_7030_penalty_both | both | 0.200 | 0.300 |  | 0.013 |  |  |  |  |


## Methodological note
- baseline_shared_STD is native 2-AUV with one shared STD map.
- vehicle_specific_* strategies are proxy/wrapper runs: AUV1 and AUV2 are solved separately and combined into fleet metrics.
- Optional overlap/proximity penalties are reward-map shaping applied to AUV2 before Lucrezia converts the map into node prizes.
- This is intentionally non-destructive and does not modify the planner objective.