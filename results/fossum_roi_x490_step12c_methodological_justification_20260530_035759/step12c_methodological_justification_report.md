# Step12C class-number justification

The canonical pipeline used SD=0.25 and 6 classes because this solution was the best automatic balanced candidate in Step04 and was then fixed in Step05 for the canonical descriptors.

Evidence:
- Step04 strict balanced-score best SD: `0.25`.
- Step04 strict balanced-score best number of classes: `6`.
- The 6-class solution had no singleton classes and a minimum class size of 30 days.
- SD=0.30 was retained as sensitivity/context, but the final canonical Step05 output is the SD=0.25 / 6-class branch.

## Step04 top candidates
| sd_fraction_of_max | number_of_classes | class_sizes | min_class_size | singleton_count | balanced_score |
| --- | --- | --- | --- | --- | --- |
| 0.250 | 6.000 | [41, 70, 50, 107, 30, 72] | 30.000 | 0.000 | 1.950 |
| 0.300 | 5.000 | [41, 120, 107, 30, 72] | 30.000 | 0.000 | 2.100 |
| 0.350 | 4.000 | [41, 120, 107, 102] | 41.000 | 0.000 | 2.250 |


## Step05 canonical class sizes
| class_id | n_days | percent_days | icv_sst_space |
| --- | --- | --- | --- |
| 1.000 | 41.000 | 11.081 | 1680.750 |
| 2.000 | 70.000 | 18.919 | 1474.508 |
| 3.000 | 50.000 | 13.514 | 1351.872 |
| 4.000 | 107.000 | 28.919 | 2005.192 |
| 5.000 | 30.000 | 8.108 | 326.411 |
| 6.000 | 72.000 | 19.459 | 1129.507 |


# Step12C descriptor-choice justification

The descriptors tested in Step12 are the descriptors most directly tied to the planner question.

- `boundary_score`: tests whether rewarding transition/frontier structure changes the path relative to STD-only planning.
- `representative_zone` / `region_A` / `region_B`: supports regime-role assignment, especially for multi-AUV planning where different vehicles should cover different regime structures.
- `interest_map`: a composite/proxy descriptor useful as sensitivity evidence because it mixes several prototype characteristics.

Other descriptors such as `gradient` and `heterogeneity` remain useful ablation diagnostics from Step11B, but Step12 focuses on the smaller set that is easiest to defend as a cost-function choice.

Important methodological constraint: all descriptors used here come from the predicted prototype class. They are not recomputed from the day-specific TEMPpred field.


# Step12C day-selection justification

| date | case_id | predicted_class | justification |
| --- | --- | --- | --- |
| 2024-08-24 | C01_representative | C01 | C01 preservado, STD alto, bom caso para testar se descriptors alteram trajetorias. |
| 2023-12-22 | C06_representative | C06 | C06 estavel e bem classificado, usado como regime robusto. |
| 2024-10-30 | October_control | C02 | Caso de outubro com predModel oficial validado, usado como referencia controlada. |


# Step12C weight-choice justification

Weights are justified by sensitivity analysis rather than by arbitrary selection.

The tested range includes both extremes:
- Single-AUV `alpha=0`: pure STD baseline.
- Single-AUV `alpha=1`: pure descriptor objective.
- Multi-AUV `w_STD=1`: shared STD baseline.
- Multi-AUV `w_STD=0, w_region=1`: pure regime-role objective.

The final recommendation is based on collected STD, regime coverage, difference from baseline, runtime and operational feasibility.

## Single-AUV recommended rows
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | STD_retention | regime_balance | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.967 | 0.000 | 0.686 |
| C01_representative | 12.000 | interest_map | interest_map_alpha100 | 1.000 | 0.889 | 0.000 | 0.657 |
| C01_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.969 | 0.000 | 0.669 |
| C01_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.970 | 0.000 | 0.683 |
| C01_representative | 24.000 | interest_map | interest_map_alpha050 | 0.500 | 0.993 | 0.000 | 0.675 |
| C01_representative | 24.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.919 | 0.000 | 0.664 |
| C01_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.976 | 0.056 | 0.664 |
| C01_representative | 48.000 | interest_map | interest_map_alpha050 | 0.500 | 1.003 | 0.116 | 0.682 |
| C01_representative | 48.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.939 | 0.000 | 0.665 |
| C06_representative | 12.000 | boundary_score | boundary_score_alpha100 | 1.000 | 0.913 | 0.000 | 0.661 |
| C06_representative | 12.000 | interest_map | interest_map_alpha075 | 0.750 | 0.969 | 0.000 | 0.680 |
| C06_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.777 | 0.000 | 0.606 |
| C06_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 1.031 | 0.000 | 0.683 |
| C06_representative | 24.000 | interest_map | interest_map_alpha075 | 0.750 | 0.988 | 0.000 | 0.671 |
| C06_representative | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.829 | 0.000 | 0.627 |
| C06_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 1.022 | 0.000 | 0.677 |
| C06_representative | 48.000 | interest_map | interest_map_alpha075 | 0.750 | 1.007 | 0.000 | 0.682 |
| C06_representative | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.828 | 0.000 | 0.617 |
| October_control | 12.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.931 | 0.000 | 0.488 |
| October_control | 12.000 | interest_map | interest_map_alpha025 | 0.250 | 0.948 | 0.000 | 0.524 |
| October_control | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.869 | 0.000 | 0.634 |
| October_control | 24.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.965 | 0.000 | 0.519 |
| October_control | 24.000 | interest_map | interest_map_alpha025 | 0.250 | 1.025 | 0.000 | 0.539 |
| October_control | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.870 | 0.000 | 0.642 |
| October_control | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.949 | 0.102 | 0.553 |
| October_control | 48.000 | interest_map | interest_map_alpha025 | 0.250 | 1.005 | 0.000 | 0.527 |
| October_control | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.894 | 0.000 | 0.649 |


## Multi-AUV recommended rows
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | STD_retention | fleet_region_B_coverage | regime_specialization_score | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.901 | 0.037 | 0.454 | 0.560 |
| C01_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.836 | 0.104 | 0.730 | 0.612 |
| C01_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.840 | 0.228 | 0.704 | 0.645 |
| C06_representative | 12.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.809 | 0.040 | 0.600 | 0.557 |
| C06_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.827 | 0.106 | 0.794 | 0.616 |
| C06_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.939 | 0.213 | 0.694 | 0.673 |
| October_control | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.811 | 0.037 | 0.689 | 0.584 |
| October_control | 24.000 | vehicle_specific_5050 | 0.500 | 0.500 | AUV1=region_A;AUV2=region_B | 0.780 | 0.100 | 0.852 | 0.626 |
| October_control | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.833 | 0.217 | 0.852 | 0.665 |


# Step12C mission-duration justification

- `12h`: restrictive short mission; useful to see whether the descriptor can change behavior when freedom is limited.
- `24h`: intermediate mission duration.
- `48h`: relaxed mission duration; helps separate descriptor effect from pure endurance effect.

## Step12A duration evidence
| mission_duration_requested_h | descriptor | mean_STD | mean_difference | mean_regime_balance | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_score | 77.276 | 0.743 | 0.000 | 224.620 | 1.000 |
| 12.000 | interest_map | 79.795 | 0.726 | 0.000 | 231.426 | 1.000 |
| 12.000 | representative_zone | 80.984 | 0.767 | 0.000 | 218.678 | 1.000 |
| 24.000 | boundary_score | 154.366 | 0.748 | 0.000 | 241.907 | 1.000 |
| 24.000 | interest_map | 158.078 | 0.742 | 0.000 | 246.933 | 1.000 |
| 24.000 | representative_zone | 160.154 | 0.757 | 0.000 | 236.363 | 1.000 |
| 48.000 | boundary_score | 301.130 | 0.716 | 0.018 | 278.586 | 1.000 |
| 48.000 | interest_map | 315.392 | 0.696 | 0.019 | 298.811 | 1.000 |
| 48.000 | representative_zone | 316.744 | 0.727 | 0.010 | 290.891 | 1.000 |


## Step12B duration evidence
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


# Step12C runtime and feasibility report

- Step12A total script runtime: `14222.578870600002` seconds.
- Step12B total script runtime: `77.49510029998783` seconds.
- Step12A physical runs: `117`.
- Step12B physical runs: `153`.

A configuration is considered operationally more defensible when it improves regime coverage without excessive STD loss or excessive solver/runtime cost.

## Step12A runtime table
| mission_duration_requested_h | descriptor | alpha | mean_solver_runtime | max_solver_runtime | runs |
| --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_score | 0.000 | 302.231 | 332.859 | 3.000 |
| 12.000 | boundary_score | 0.250 | 289.959 | 292.980 | 3.000 |
| 12.000 | boundary_score | 0.500 | 257.807 | 309.624 | 3.000 |
| 12.000 | boundary_score | 0.750 | 169.684 | 181.880 | 3.000 |
| 12.000 | boundary_score | 1.000 | 103.417 | 104.676 | 3.000 |
| 12.000 | interest_map | 0.000 | 302.231 | 332.859 | 3.000 |
| 12.000 | interest_map | 0.250 | 287.208 | 312.900 | 3.000 |
| 12.000 | interest_map | 0.500 | 293.515 | 323.256 | 3.000 |
| 12.000 | interest_map | 0.750 | 184.894 | 197.336 | 3.000 |
| 12.000 | interest_map | 1.000 | 89.282 | 91.494 | 3.000 |
| 12.000 | representative_zone | 0.000 | 302.231 | 332.859 | 3.000 |
| 12.000 | representative_zone | 0.250 | 277.671 | 307.851 | 3.000 |
| 12.000 | representative_zone | 0.500 | 239.643 | 259.732 | 3.000 |
| 12.000 | representative_zone | 0.750 | 155.420 | 161.874 | 3.000 |
| 12.000 | representative_zone | 1.000 | 118.423 | 125.708 | 3.000 |
| 24.000 | boundary_score | 0.000 | 317.807 | 358.946 | 3.000 |
| 24.000 | boundary_score | 0.250 | 304.589 | 319.671 | 3.000 |
| 24.000 | boundary_score | 0.500 | 277.524 | 344.630 | 3.000 |
| 24.000 | boundary_score | 0.750 | 186.160 | 202.681 | 3.000 |
| 24.000 | boundary_score | 1.000 | 123.454 | 133.375 | 3.000 |
| 24.000 | interest_map | 0.000 | 317.807 | 358.946 | 3.000 |
| 24.000 | interest_map | 0.250 | 306.052 | 349.132 | 3.000 |
| 24.000 | interest_map | 0.500 | 303.883 | 349.783 | 3.000 |
| 24.000 | interest_map | 0.750 | 205.200 | 215.029 | 3.000 |
| 24.000 | interest_map | 1.000 | 101.722 | 103.148 | 3.000 |
| 24.000 | representative_zone | 0.000 | 317.807 | 358.946 | 3.000 |
| 24.000 | representative_zone | 0.250 | 294.598 | 335.391 | 3.000 |
| 24.000 | representative_zone | 0.500 | 263.700 | 305.461 | 3.000 |
| 24.000 | representative_zone | 0.750 | 175.944 | 184.622 | 3.000 |
| 24.000 | representative_zone | 1.000 | 129.766 | 135.379 | 3.000 |
| 48.000 | boundary_score | 0.000 | 346.186 | 390.569 | 3.000 |
| 48.000 | boundary_score | 0.250 | 312.822 | 352.009 | 3.000 |
| 48.000 | boundary_score | 0.500 | 360.809 | 501.168 | 3.000 |
| 48.000 | boundary_score | 0.750 | 217.075 | 287.324 | 3.000 |
| 48.000 | boundary_score | 1.000 | 156.036 | 203.717 | 3.000 |
| 48.000 | interest_map | 0.000 | 346.186 | 390.569 | 3.000 |
| 48.000 | interest_map | 0.250 | 347.551 | 418.852 | 3.000 |
| 48.000 | interest_map | 0.500 | 407.192 | 579.550 | 3.000 |
| 48.000 | interest_map | 0.750 | 261.230 | 350.907 | 3.000 |
| 48.000 | interest_map | 1.000 | 131.895 | 170.567 | 3.000 |
| 48.000 | representative_zone | 0.000 | 346.186 | 390.569 | 3.000 |
| 48.000 | representative_zone | 0.250 | 357.652 | 491.652 | 3.000 |
| 48.000 | representative_zone | 0.500 | 328.081 | 510.782 | 3.000 |
| 48.000 | representative_zone | 0.750 | 243.746 | 348.255 | 3.000 |
| 48.000 | representative_zone | 1.000 | 178.790 | 223.726 | 3.000 |


## Step12B runtime table
| mission_duration_requested_h | strategy | mean_solver_runtime | max_solver_runtime | fleet_rows |
| --- | --- | --- | --- | --- |
| 12.000 | baseline_shared_STD | 288.517 | 326.358 | 3.000 |
| 12.000 | role_swap_of_vehicle_specific_6040 | 559.774 | 559.774 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_7030 | 502.909 | 517.790 | 2.000 |
| 12.000 | vehicle_specific_00100 | 141.442 | 142.248 | 3.000 |
| 12.000 | vehicle_specific_2575 | 303.075 | 331.065 | 3.000 |
| 12.000 | vehicle_specific_5050 | 475.340 | 501.409 | 3.000 |
| 12.000 | vehicle_specific_6040 | 528.086 | 563.973 | 3.000 |
| 12.000 | vehicle_specific_7030 | 535.182 | 588.741 | 3.000 |
| 12.000 | vehicle_specific_8020 | 536.483 | 590.761 | 3.000 |
| 12.000 | vehicle_specific_9010 | 565.035 | 637.724 | 3.000 |
| 24.000 | baseline_shared_STD | 307.013 | 334.433 | 3.000 |
| 24.000 | role_swap_of_vehicle_specific_5050 | 441.292 | 441.292 | 1.000 |
| 24.000 | role_swap_of_vehicle_specific_6040 | 559.285 | 572.538 | 2.000 |
| 24.000 | vehicle_specific_00100 | 141.491 | 142.858 | 3.000 |
| 24.000 | vehicle_specific_2575 | 308.514 | 333.544 | 3.000 |
| 24.000 | vehicle_specific_5050 | 483.791 | 508.251 | 3.000 |
| 24.000 | vehicle_specific_6040 | 547.580 | 584.745 | 3.000 |
| 24.000 | vehicle_specific_7030 | 543.899 | 615.744 | 3.000 |
| 24.000 | vehicle_specific_8020 | 556.015 | 605.999 | 3.000 |
| 24.000 | vehicle_specific_9010 | 584.337 | 658.089 | 3.000 |
| 48.000 | baseline_shared_STD | 380.480 | 401.621 | 3.000 |
| 48.000 | role_swap_of_vehicle_specific_6040 | 562.555 | 613.781 | 3.000 |
| 48.000 | vehicle_specific_00100 | 141.249 | 142.775 | 3.000 |
| 48.000 | vehicle_specific_2575 | 348.926 | 378.074 | 3.000 |
| 48.000 | vehicle_specific_5050 | 522.160 | 542.877 | 3.000 |
| 48.000 | vehicle_specific_6040 | 591.551 | 618.796 | 3.000 |
| 48.000 | vehicle_specific_7030 | 593.689 | 655.686 | 3.000 |
| 48.000 | vehicle_specific_8020 | 585.555 | 638.697 | 3.000 |
| 48.000 | vehicle_specific_9010 | 644.155 | 723.130 | 3.000 |


# Step12C final recommendations

Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`

Recommended use in thesis:
- Use Step12A as evidence for single-AUV descriptor sensitivity.
- Use Step12B as the stronger argument for multi-AUV regime-role planning.
- State clearly that vehicle-specific maps are currently a wrapper/proxy unless the planner is later modified to support native vehicle-specific prize maps.
- Use information_map figures when discussing objectives; use TEMPpred figures only as diagnostic spatial context.

## Best single-AUV rows
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | recommendation_score |
| --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.686 |
| C01_representative | 12.000 | interest_map | interest_map_alpha100 | 1.000 | 0.657 |
| C01_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.669 |
| C01_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.683 |
| C01_representative | 24.000 | interest_map | interest_map_alpha050 | 0.500 | 0.675 |
| C01_representative | 24.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.664 |
| C01_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.664 |
| C01_representative | 48.000 | interest_map | interest_map_alpha050 | 0.500 | 0.682 |
| C01_representative | 48.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.665 |
| C06_representative | 12.000 | boundary_score | boundary_score_alpha100 | 1.000 | 0.661 |
| C06_representative | 12.000 | interest_map | interest_map_alpha075 | 0.750 | 0.680 |
| C06_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.606 |
| C06_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.683 |
| C06_representative | 24.000 | interest_map | interest_map_alpha075 | 0.750 | 0.671 |
| C06_representative | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.627 |
| C06_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.677 |
| C06_representative | 48.000 | interest_map | interest_map_alpha075 | 0.750 | 0.682 |
| C06_representative | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.617 |
| October_control | 12.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.488 |
| October_control | 12.000 | interest_map | interest_map_alpha025 | 0.250 | 0.524 |
| October_control | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.634 |
| October_control | 24.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.519 |
| October_control | 24.000 | interest_map | interest_map_alpha025 | 0.250 | 0.539 |
| October_control | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.642 |
| October_control | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.553 |
| October_control | 48.000 | interest_map | interest_map_alpha025 | 0.250 | 0.527 |
| October_control | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.649 |


## Best multi-AUV rows
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.560 |
| C01_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.612 |
| C01_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.645 |
| C06_representative | 12.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.557 |
| C06_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.616 |
| C06_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.673 |
| October_control | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.584 |
| October_control | 24.000 | vehicle_specific_5050 | 0.500 | 0.500 | AUV1=region_A;AUV2=region_B | 0.626 |
| October_control | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.665 |


## Limitations
- Static descriptors do not guarantee true route-level crossing behavior.
- Vehicle-specific maps can improve specialization but can reduce STD collection.
- The current planner does not yet implement native route-level reward or native vehicle-specific prize maps.