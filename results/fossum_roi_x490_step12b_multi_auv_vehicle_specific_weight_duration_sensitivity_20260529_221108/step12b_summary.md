# Step12B multi-AUV vehicle-specific weight sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Fleet rows: 81
- Vehicle rows: 162
- Prototype-based maps only: True
- TEMPpred used as objective: False

## Best weight recommendation
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | STD_retention | fleet_region_B_coverage | regime_specialization_score | trajectory_overlap_ratio | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.901 | 0.037 | 0.454 | 0.020 | 522.599 | 0.560 |
| C01_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.836 | 0.104 | 0.730 | 0.002 | 551.888 | 0.612 |
| C01_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.840 | 0.228 | 0.704 | 0.014 | 618.796 | 0.645 |
| C06_representative | 12.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.809 | 0.040 | 0.600 | 0.003 | 563.973 | 0.557 |
| C06_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.827 | 0.106 | 0.794 | 0.002 | 584.745 | 0.616 |
| C06_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.939 | 0.213 | 0.694 | 0.004 | 612.941 | 0.673 |
| October_control | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.811 | 0.037 | 0.689 | 0.003 | 494.206 | 0.584 |
| October_control | 24.000 | vehicle_specific_5050 | 0.500 | 0.500 | AUV1=region_A;AUV2=region_B | 0.780 | 0.100 | 0.852 | 0.002 | 442.516 | 0.626 |
| October_control | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.833 | 0.217 | 0.852 | 0.003 | 542.917 | 0.665 |


## Weight sensitivity
| strategy | w_STD | w_region | w_boundary | mean_STD_retention | mean_region_B_coverage | mean_specialization | mean_overlap | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vehicle_specific_6040 | 0.600 | 0.400 | 0.000 | 0.840 | 0.121 | 0.711 | 0.004 | 555.739 | 0.612 |
| vehicle_specific_5050 | 0.500 | 0.500 | 0.000 | 0.808 | 0.122 | 0.739 | 0.005 | 493.764 | 0.610 |
| vehicle_specific_2575 | 0.250 | 0.750 | 0.000 | 0.790 | 0.117 | 0.718 | 0.005 | 320.172 | 0.598 |
| vehicle_specific_7030 | 0.700 | 0.300 | 0.000 | 0.888 | 0.117 | 0.564 | 0.028 | 557.590 | 0.586 |
| vehicle_specific_00100 | 0.000 | 1.000 | 0.000 | 0.607 | 0.079 | 0.683 | 0.002 | 141.394 | 0.531 |
| vehicle_specific_8020 | 0.800 | 0.200 | 0.000 | 1.022 | 0.097 | 0.343 | 0.108 | 559.351 | 0.512 |
| vehicle_specific_9010 | 0.900 | 0.100 | 0.000 | 1.075 | 0.081 | 0.288 | 0.156 | 597.842 | 0.498 |
| role_swap_of_vehicle_specific_6040 | 0.600 | 0.400 | 0.000 | 0.848 | 0.151 | 0.000 | 0.005 | 561.001 | 0.482 |
| baseline_shared_STD | 1.000 | 0.000 | 0.000 | 1.000 | 0.072 | 0.164 | 0.004 | 325.337 | 0.473 |
| role_swap_of_vehicle_specific_7030 | 0.700 | 0.300 | 0.000 | 0.856 | 0.037 | 0.000 | 0.012 | 502.909 | 0.458 |
| role_swap_of_vehicle_specific_5050 | 0.500 | 0.500 | 0.000 | 0.780 | 0.100 | 0.000 | 0.002 | 441.292 | 0.456 |


## Duration sensitivity
| mission_duration_requested_h | strategy | mean_fleet_STD | mean_region_B_coverage | mean_specialization | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | baseline_shared_STD | 175.392 | 0.028 | 0.184 | 288.517 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_6040 | 130.663 | 0.040 | 0.000 | 559.774 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_7030 | 156.270 | 0.037 | 0.000 | 502.909 | 1.000 |
| 12.000 | vehicle_specific_00100 | 135.681 | 0.036 | 0.522 | 141.442 | 1.000 |
| 12.000 | vehicle_specific_2575 | 132.877 | 0.040 | 0.638 | 303.075 | 1.000 |
| 12.000 | vehicle_specific_5050 | 140.804 | 0.041 | 0.638 | 475.340 | 1.000 |
| 12.000 | vehicle_specific_6040 | 145.634 | 0.041 | 0.602 | 528.086 | 1.000 |
| 12.000 | vehicle_specific_7030 | 144.924 | 0.036 | 0.564 | 535.182 | 1.000 |
| 12.000 | vehicle_specific_8020 | 174.054 | 0.036 | 0.283 | 536.483 | 1.000 |
| 12.000 | vehicle_specific_9010 | 179.341 | 0.033 | 0.258 | 565.035 | 1.000 |
| 24.000 | baseline_shared_STD | 348.124 | 0.066 | 0.215 | 307.013 | 1.000 |
| 24.000 | role_swap_of_vehicle_specific_5050 | 277.801 | 0.100 | 0.000 | 441.292 | 1.000 |
| 24.000 | role_swap_of_vehicle_specific_6040 | 286.284 | 0.105 | 0.000 | 559.285 | 1.000 |
| 24.000 | vehicle_specific_00100 | 230.514 | 0.097 | 0.759 | 141.491 | 1.000 |
| 24.000 | vehicle_specific_2575 | 259.478 | 0.105 | 0.822 | 308.514 | 1.000 |
| 24.000 | vehicle_specific_5050 | 268.118 | 0.103 | 0.815 | 483.791 | 1.000 |
| 24.000 | vehicle_specific_6040 | 285.610 | 0.104 | 0.780 | 547.580 | 1.000 |
| 24.000 | vehicle_specific_7030 | 299.263 | 0.109 | 0.635 | 543.899 | 1.000 |
| 24.000 | vehicle_specific_8020 | 344.922 | 0.097 | 0.408 | 556.015 | 1.000 |
| 24.000 | vehicle_specific_9010 | 364.946 | 0.076 | 0.336 | 584.337 | 1.000 |
| 48.000 | baseline_shared_STD | 615.961 | 0.124 | 0.095 | 380.480 | 1.000 |
| 48.000 | role_swap_of_vehicle_specific_6040 | 534.490 | 0.219 | 0.000 | 562.555 | 1.000 |
| 48.000 | vehicle_specific_00100 | 234.751 | 0.104 | 0.767 | 141.249 | 1.000 |
| 48.000 | vehicle_specific_2575 | 533.557 | 0.205 | 0.695 | 348.926 | 1.000 |
| 48.000 | vehicle_specific_5050 | 522.270 | 0.221 | 0.763 | 522.160 | 1.000 |
| 48.000 | vehicle_specific_6040 | 534.490 | 0.219 | 0.750 | 591.551 | 1.000 |
| 48.000 | vehicle_specific_7030 | 605.484 | 0.205 | 0.494 | 593.689 | 1.000 |
| 48.000 | vehicle_specific_8020 | 666.984 | 0.157 | 0.339 | 585.555 | 1.000 |
| 48.000 | vehicle_specific_9010 | 707.749 | 0.135 | 0.269 | 644.155 | 1.000 |


## Methodological note
- baseline_shared_STD is native 2-AUV with one shared STD map.
- vehicle_specific_* strategies are proxy/wrapper runs: AUV1 and AUV2 are solved separately and combined into fleet metrics.
- This is intentionally non-destructive and does not modify the planner objective.