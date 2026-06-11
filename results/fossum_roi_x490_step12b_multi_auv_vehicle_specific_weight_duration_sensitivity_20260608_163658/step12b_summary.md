# Step12B multi-AUV vehicle-specific weight sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Fleet rows: 27
- Vehicle rows: 54
- Prototype-based maps only: True
- TEMPpred used as objective: False
- Overlap/proximity penalty enabled: False
- Penalty comparison rows: 0

## Best weight recommendation
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | STD_retention | fleet_region_B_coverage | regime_specialization_score | trajectory_overlap_ratio | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.891 | 0.038 | 0.452 | 0.003 | 2488.208 | 0.557 |
| C06_representative | 12.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.856 | 0.038 | 0.551 | 0.003 | 3051.685 | 0.561 |
| October_control | 12.000 | role_swap_of_vehicle_specific_2575 | 0.250 | 0.750 | AUV1=region_B;AUV2=region_A | 0.974 | 0.019 | 0.000 | 1.000 | 3101.715 | 0.397 |


## Weight sensitivity
| strategy | w_STD | w_region | w_boundary | mean_STD_retention | mean_region_B_coverage | mean_specialization | mean_overlap | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vehicle_specific_6040 | 0.600 | 0.400 | 0.000 | 0.883 | 0.032 | 0.382 | 0.335 | 2889.657 | 0.504 |
| vehicle_specific_7030 | 0.700 | 0.300 | 0.000 | 0.888 | 0.031 | 0.337 | 0.336 | 2786.785 | 0.500 |
| vehicle_specific_5050 | 0.500 | 0.500 | 0.000 | 0.851 | 0.032 | 0.389 | 0.337 | 2610.520 | 0.497 |
| vehicle_specific_2575 | 0.250 | 0.750 | 0.000 | 0.828 | 0.032 | 0.407 | 0.336 | 1944.730 | 0.493 |
| role_swap_of_vehicle_specific_7030 | 0.700 | 0.300 | 0.000 | 0.891 | 0.038 | 0.000 | 0.003 | 2249.272 | 0.467 |
| role_swap_of_vehicle_specific_6040 | 0.600 | 0.400 | 0.000 | 0.856 | 0.038 | 0.000 | 0.003 | 2739.458 | 0.451 |
| baseline_shared_STD | 1.000 | 0.000 | 0.000 | 1.000 | 0.021 | 0.053 | 0.007 | 1201.011 | 0.448 |
| vehicle_specific_8020 | 0.800 | 0.200 | 0.000 | 1.013 | 0.021 | 0.183 | 0.366 | 2710.697 | 0.443 |
| vehicle_specific_9010 | 0.900 | 0.100 | 0.000 | 1.018 | 0.017 | 0.128 | 0.419 | 2738.769 | 0.427 |
| vehicle_specific_00100 | 0.000 | 1.000 | 0.000 | 0.495 | 0.022 | 0.343 | 0.002 | 179.931 | 0.414 |
| role_swap_of_vehicle_specific_2575 | 0.250 | 0.750 | 0.000 | 0.974 | 0.019 | 0.000 | 1.000 | 3101.715 | 0.397 |


## Duration sensitivity
| mission_duration_requested_h | strategy | mean_fleet_STD | mean_region_B_coverage | mean_specialization | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | baseline_shared_STD | 175.818 | 0.021 | 0.053 | 1201.011 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_2575 | 177.187 | 0.019 | 0.000 | 3101.715 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_6040 | 135.601 | 0.038 | 0.000 | 2739.458 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_7030 | 166.705 | 0.038 | 0.000 | 2249.272 | 1.000 |
| 12.000 | vehicle_specific_00100 | 85.176 | 0.022 | 0.343 | 179.931 | 0.667 |
| 12.000 | vehicle_specific_2575 | 146.202 | 0.032 | 0.407 | 1944.730 | 1.000 |
| 12.000 | vehicle_specific_5050 | 150.354 | 0.032 | 0.389 | 2610.520 | 1.000 |
| 12.000 | vehicle_specific_6040 | 155.378 | 0.032 | 0.382 | 2889.657 | 1.000 |
| 12.000 | vehicle_specific_7030 | 156.880 | 0.031 | 0.337 | 2786.785 | 1.000 |
| 12.000 | vehicle_specific_8020 | 178.019 | 0.021 | 0.183 | 2710.697 | 1.000 |
| 12.000 | vehicle_specific_9010 | 178.534 | 0.017 | 0.128 | 2738.769 | 1.000 |


## Optional overlap/proximity penalty comparison
_No data available._


## Methodological note
- baseline_shared_STD is native 2-AUV with one shared STD map.
- vehicle_specific_* strategies are proxy/wrapper runs: AUV1 and AUV2 are solved separately and combined into fleet metrics.
- Optional overlap/proximity penalties are reward-map shaping applied to AUV2 before Lucrezia converts the map into node prizes.
- This is intentionally non-destructive and does not modify the planner objective.