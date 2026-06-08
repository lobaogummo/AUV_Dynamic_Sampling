# Step12D quantitative justification report

Verdict: `QUANTITATIVE_JUSTIFICATION_READY`

This report uses existing CSV/JSON outputs only. No planner or heavy pipeline stage was re-run.

# Step12D weight-selection report

Scores are auxiliary rankings only. The defensible interpretation is the tradeoff among information retention, regime balance/specialization, path change, overlap, and runtime.

## Single-AUV selected candidate
| case_id | mission_duration | descriptor | alpha | STD_retention | STD_loss | regime_balance | descriptor_gain | runtime_seconds | tradeoff_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 24.000 | boundary_score | 0.500 | 0.970 | 0.030 | 0.000 | 71.686 | 209.752 | 0.502 |


## Multi-AUV selected candidate
| case_id | mission_duration | strategy | w_STD | w_region | fleet_STD_retention | fleet_STD_loss | region_B_gain | specialization_score | runtime_seconds | tradeoff_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| October_control | 48.000 | vehicle_specific_5050 | 0.500 | 0.500 | 0.799 | 0.201 | 0.006 | 0.881 | 496.652 | 0.656 |


## Single-AUV Pareto candidates
| case_id | mission_duration | descriptor | alpha | STD_loss | regime_balance | descriptor_gain_norm | runtime_seconds | tradeoff_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_score | 0.250 | -0.005 | 0.000 | 0.059 | 283.979 | 0.464 |
| C01_representative | 12.000 | boundary_score | 0.500 | 0.033 | 0.000 | 0.082 | 208.297 | 0.476 |
| C01_representative | 12.000 | boundary_score | 1.000 | 0.156 | 0.000 | 0.072 | 102.489 | 0.443 |
| C01_representative | 12.000 | representative_zone | 0.250 | 0.003 | 0.000 | 0.039 | 257.434 | 0.460 |
| C01_representative | 12.000 | representative_zone | 1.000 | 0.088 | 0.000 | 0.087 | 118.168 | 0.472 |
| C01_representative | 12.000 | interest_map | 1.000 | 0.111 | 0.000 | 0.041 | 89.614 | 0.460 |
| C01_representative | 24.000 | boundary_score | 0.250 | 0.006 | 0.000 | 0.152 | 280.666 | 0.480 |
| C01_representative | 24.000 | boundary_score | 0.500 | 0.030 | 0.000 | 0.221 | 209.752 | 0.502 |
| C01_representative | 24.000 | representative_zone | 0.750 | 0.081 | 0.000 | 0.177 | 171.260 | 0.482 |
| C01_representative | 24.000 | representative_zone | 1.000 | 0.139 | 0.000 | 0.187 | 135.379 | 0.469 |
| C01_representative | 24.000 | interest_map | 0.500 | 0.007 | 0.000 | 0.074 | 241.593 | 0.472 |
| C01_representative | 24.000 | interest_map | 1.000 | 0.339 | 0.000 | 0.092 | 102.006 | 0.376 |
| C01_representative | 48.000 | boundary_score | 0.250 | 0.024 | 0.056 | 0.151 | 288.957 | 0.478 |
| C01_representative | 48.000 | boundary_score | 0.750 | 0.147 | 0.000 | 0.197 | 176.632 | 0.454 |
| C01_representative | 48.000 | representative_zone | 0.250 | 0.014 | 0.039 | 0.079 | 308.495 | 0.461 |
| C01_representative | 48.000 | representative_zone | 0.750 | 0.061 | 0.000 | 0.227 | 188.027 | 0.491 |
| C01_representative | 48.000 | interest_map | 0.250 | -0.029 | 0.057 | 0.050 | 325.238 | 0.471 |
| C01_representative | 48.000 | interest_map | 0.500 | -0.003 | 0.116 | 0.062 | 282.578 | 0.491 |
| C01_representative | 48.000 | interest_map | 1.000 | 0.221 | 0.000 | 0.119 | 114.968 | 0.425 |
| C06_representative | 12.000 | boundary_score | 1.000 | 0.087 | 0.000 | 0.024 | 103.087 | 0.460 |
| C06_representative | 12.000 | interest_map | 0.750 | 0.031 | 0.000 | 0.041 | 172.270 | 0.472 |
| C06_representative | 24.000 | boundary_score | 0.500 | -0.031 | 0.000 | 0.056 | 278.190 | 0.470 |
| C06_representative | 24.000 | boundary_score | 0.750 | 0.034 | 0.000 | 0.049 | 165.295 | 0.472 |
| C06_representative | 24.000 | boundary_score | 1.000 | 0.068 | 0.000 | 0.078 | 133.375 | 0.474 |
| C06_representative | 24.000 | representative_zone | 0.250 | 0.027 | 0.000 | 0.213 | 335.391 | 0.472 |
| C06_representative | 24.000 | representative_zone | 0.500 | 0.171 | 0.000 | 0.423 | 305.461 | 0.468 |
| C06_representative | 24.000 | representative_zone | 0.750 | 0.297 | 0.000 | 0.454 | 184.622 | 0.452 |
| C06_representative | 24.000 | representative_zone | 1.000 | 0.318 | 0.000 | 0.432 | 129.667 | 0.450 |
| C06_representative | 24.000 | interest_map | 0.750 | 0.012 | 0.000 | 0.043 | 203.815 | 0.470 |
| C06_representative | 24.000 | interest_map | 1.000 | 0.106 | 0.000 | 0.058 | 103.148 | 0.463 |
| C06_representative | 48.000 | boundary_score | 1.000 | 0.025 | 0.000 | 0.069 | 203.717 | 0.470 |
| C06_representative | 48.000 | representative_zone | 0.250 | 0.034 | 0.000 | 0.267 | 491.652 | 0.442 |
| C06_representative | 48.000 | representative_zone | 0.500 | 0.172 | 0.000 | 0.559 | 510.782 | 0.449 |
| C06_representative | 48.000 | representative_zone | 0.750 | 0.282 | 0.000 | 0.625 | 348.255 | 0.455 |
| C06_representative | 48.000 | representative_zone | 1.000 | 0.320 | 0.000 | 0.624 | 223.726 | 0.464 |
| C06_representative | 48.000 | interest_map | 0.250 | -0.034 | 0.000 | 0.045 | 418.852 | 0.428 |
| C06_representative | 48.000 | interest_map | 0.750 | -0.007 | 0.000 | 0.075 | 350.907 | 0.451 |
| October_control | 12.000 | boundary_score | 0.000 | 0.000 | 0.000 | 0.019 | 253.251 | 0.370 |
| October_control | 12.000 | boundary_score | 1.000 | 0.505 | 0.000 | 0.237 | 104.676 | 0.342 |
| October_control | 12.000 | representative_zone | 0.000 | 0.000 | 0.000 | 0.019 | 253.251 | 0.370 |
| October_control | 12.000 | representative_zone | 1.000 | 0.267 | 0.000 | 0.081 | 111.392 | 0.403 |
| October_control | 12.000 | interest_map | 0.000 | 0.000 | 0.000 | 0.019 | 253.251 | 0.370 |
| October_control | 12.000 | interest_map | 1.000 | 0.580 | 0.000 | 0.129 | 86.740 | 0.294 |
| October_control | 24.000 | boundary_score | 1.000 | 0.641 | 0.000 | 0.519 | 110.584 | 0.343 |
| October_control | 24.000 | representative_zone | 1.000 | 0.230 | 0.000 | 0.217 | 124.253 | 0.443 |
| October_control | 24.000 | interest_map | 1.000 | 0.624 | 0.000 | 0.263 | 100.011 | 0.300 |
| October_control | 48.000 | boundary_score | 0.250 | 0.051 | 0.102 | 0.179 | 297.501 | 0.487 |
| October_control | 48.000 | boundary_score | 0.500 | 0.513 | 0.000 | 0.945 | 318.663 | 0.436 |
| October_control | 48.000 | boundary_score | 0.750 | 0.530 | 0.000 | 1.000 | 187.269 | 0.467 |
| October_control | 48.000 | boundary_score | 1.000 | 0.560 | 0.000 | 0.904 | 114.412 | 0.451 |
| October_control | 48.000 | representative_zone | 0.500 | 0.106 | 0.000 | 0.285 | 211.091 | 0.483 |
| October_control | 48.000 | representative_zone | 1.000 | 0.156 | 0.000 | 0.310 | 124.539 | 0.486 |
| October_control | 48.000 | interest_map | 1.000 | 0.549 | 0.000 | 0.386 | 110.151 | 0.353 |


## Multi-AUV Pareto candidates
| case_id | mission_duration | strategy | w_region | fleet_STD_loss | region_B_gain | specialization_score | trajectory_overlap_ratio | runtime_seconds | tradeoff_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | baseline_shared_STD | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 307.036 | 0.367 |
| C01_representative | 12.000 | vehicle_specific_9010 | 0.100 | 0.003 | 0.012 | 0.191 | 0.078 | 587.060 | 0.350 |
| C01_representative | 12.000 | vehicle_specific_2575 | 0.750 | 0.245 | 0.021 | 0.630 | 0.003 | 271.924 | 0.490 |
| C06_representative | 12.000 | baseline_shared_STD | 0.000 | 0.000 | 0.000 | 0.217 | 0.000 | 326.358 | 0.408 |
| C01_representative | 12.000 | vehicle_specific_00100 | 1.000 | 0.267 | 0.018 | 0.507 | 0.003 | 140.238 | 0.465 |
| C06_representative | 12.000 | vehicle_specific_2575 | 0.750 | 0.249 | 0.041 | 0.579 | 0.003 | 331.065 | 0.471 |
| October_control | 12.000 | baseline_shared_STD | 0.000 | 0.000 | 0.000 | 0.334 | 0.003 | 232.159 | 0.448 |
| C06_representative | 12.000 | vehicle_specific_00100 | 1.000 | 0.229 | 0.035 | 0.480 | 0.003 | 141.839 | 0.473 |
| October_control | 12.000 | vehicle_specific_9010 | 0.100 | -0.005 | 0.004 | 0.382 | 0.126 | 470.319 | 0.395 |
| October_control | 12.000 | vehicle_specific_8020 | 0.200 | -0.014 | -0.001 | 0.344 | 0.094 | 488.254 | 0.402 |
| October_control | 12.000 | vehicle_specific_7030 | 0.300 | 0.189 | -0.030 | 0.689 | 0.003 | 494.206 | 0.498 |
| October_control | 12.000 | vehicle_specific_5050 | 0.500 | 0.202 | -0.024 | 0.709 | 0.003 | 441.589 | 0.506 |
| October_control | 12.000 | vehicle_specific_2575 | 0.750 | 0.234 | -0.026 | 0.704 | 0.003 | 306.236 | 0.505 |
| October_control | 12.000 | vehicle_specific_00100 | 1.000 | 0.182 | -0.026 | 0.580 | 0.003 | 142.248 | 0.495 |
| C01_representative | 24.000 | vehicle_specific_9010 | 0.100 | 0.002 | 0.001 | 0.238 | 0.057 | 608.581 | 0.393 |
| C01_representative | 24.000 | vehicle_specific_8020 | 0.200 | 0.005 | 0.042 | 0.350 | 0.044 | 548.194 | 0.451 |
| C01_representative | 24.000 | vehicle_specific_6040 | 0.400 | 0.164 | 0.058 | 0.730 | 0.002 | 551.888 | 0.588 |
| C01_representative | 24.000 | vehicle_specific_5050 | 0.500 | 0.256 | 0.062 | 0.806 | 0.002 | 500.605 | 0.585 |
| C01_representative | 24.000 | vehicle_specific_2575 | 0.750 | 0.271 | 0.060 | 0.818 | 0.002 | 278.671 | 0.600 |
| C06_representative | 24.000 | baseline_shared_STD | 0.000 | 0.000 | 0.000 | 0.329 | 0.000 | 334.433 | 0.439 |
| C01_representative | 24.000 | vehicle_specific_00100 | 1.000 | 0.363 | 0.059 | 0.748 | 0.002 | 140.424 | 0.550 |
| C06_representative | 24.000 | vehicle_specific_9010 | 0.100 | -0.113 | 0.000 | 0.325 | 0.256 | 658.089 | 0.378 |
| C06_representative | 24.000 | vehicle_specific_8020 | 0.200 | 0.062 | 0.044 | 0.445 | 0.051 | 605.999 | 0.419 |
| C06_representative | 24.000 | vehicle_specific_6040 | 0.400 | 0.173 | 0.106 | 0.794 | 0.002 | 584.745 | 0.602 |
| C06_representative | 24.000 | vehicle_specific_5050 | 0.500 | 0.212 | 0.101 | 0.788 | 0.002 | 508.251 | 0.587 |
| C06_representative | 24.000 | vehicle_specific_2575 | 0.750 | 0.245 | 0.109 | 0.801 | 0.002 | 333.544 | 0.599 |
| C06_representative | 24.000 | vehicle_specific_00100 | 1.000 | 0.286 | 0.104 | 0.711 | 0.002 | 142.858 | 0.566 |
| October_control | 24.000 | vehicle_specific_9010 | 0.100 | -0.040 | 0.028 | 0.446 | 0.095 | 486.341 | 0.430 |
| October_control | 24.000 | vehicle_specific_6040 | 0.400 | 0.202 | -0.048 | 0.815 | 0.002 | 506.107 | 0.571 |
| October_control | 24.000 | vehicle_specific_5050 | 0.500 | 0.220 | -0.050 | 0.852 | 0.002 | 442.516 | 0.579 |
| October_control | 24.000 | vehicle_specific_2575 | 0.750 | 0.247 | -0.050 | 0.847 | 0.002 | 313.326 | 0.584 |
| October_control | 24.000 | vehicle_specific_00100 | 1.000 | 0.360 | -0.069 | 0.818 | 0.002 | 141.192 | 0.534 |
| C01_representative | 48.000 | vehicle_specific_9010 | 0.100 | -0.140 | -0.029 | 0.111 | 0.157 | 637.407 | 0.374 |
| C01_representative | 48.000 | vehicle_specific_8020 | 0.200 | -0.044 | -0.020 | 0.261 | 0.114 | 572.734 | 0.430 |
| C01_representative | 48.000 | vehicle_specific_7030 | 0.300 | 0.060 | 0.072 | 0.512 | 0.070 | 595.593 | 0.504 |
| C01_representative | 48.000 | vehicle_specific_6040 | 0.400 | 0.160 | 0.111 | 0.704 | 0.014 | 618.796 | 0.612 |
| C01_representative | 48.000 | vehicle_specific_5050 | 0.500 | 0.179 | 0.117 | 0.711 | 0.007 | 526.952 | 0.607 |
| C01_representative | 48.000 | vehicle_specific_2575 | 0.750 | 0.136 | 0.064 | 0.615 | 0.019 | 324.159 | 0.589 |
| C01_representative | 48.000 | vehicle_specific_00100 | 1.000 | 0.639 | -0.011 | 0.748 | 0.002 | 140.174 | 0.453 |
| C06_representative | 48.000 | vehicle_specific_9010 | 0.100 | -0.207 | -0.046 | 0.255 | 0.237 | 723.130 | 0.390 |
| C06_representative | 48.000 | vehicle_specific_8020 | 0.200 | -0.115 | 0.034 | 0.310 | 0.117 | 638.697 | 0.448 |
| C06_representative | 48.000 | vehicle_specific_7030 | 0.300 | -0.020 | 0.105 | 0.515 | 0.038 | 655.686 | 0.523 |
| C06_representative | 48.000 | vehicle_specific_6040 | 0.400 | 0.061 | 0.167 | 0.694 | 0.004 | 612.941 | 0.641 |
| C06_representative | 48.000 | vehicle_specific_5050 | 0.500 | 0.065 | 0.167 | 0.695 | 0.017 | 542.877 | 0.643 |
| C06_representative | 48.000 | vehicle_specific_2575 | 0.750 | 0.095 | 0.176 | 0.688 | 0.001 | 378.074 | 0.648 |
| C06_representative | 48.000 | vehicle_specific_00100 | 1.000 | 0.558 | 0.080 | 0.728 | 0.002 | 142.775 | 0.475 |
| October_control | 48.000 | vehicle_specific_9010 | 0.100 | -0.107 | 0.109 | 0.440 | 0.165 | 571.928 | 0.428 |
| October_control | 48.000 | vehicle_specific_8020 | 0.200 | -0.093 | 0.084 | 0.446 | 0.156 | 545.234 | 0.457 |
| October_control | 48.000 | vehicle_specific_7030 | 0.300 | 0.007 | 0.066 | 0.454 | 0.083 | 529.788 | 0.498 |
| October_control | 48.000 | vehicle_specific_6040 | 0.400 | 0.167 | 0.007 | 0.852 | 0.003 | 542.917 | 0.640 |
| October_control | 48.000 | vehicle_specific_5050 | 0.500 | 0.201 | 0.006 | 0.881 | 0.004 | 496.652 | 0.656 |
| October_control | 48.000 | vehicle_specific_2575 | 0.750 | 0.165 | 0.003 | 0.782 | 0.006 | 344.546 | 0.613 |
| October_control | 48.000 | vehicle_specific_00100 | 1.000 | 0.652 | -0.129 | 0.825 | 0.002 | 140.797 | 0.434 |
| C06_representative | 48.000 | role_swap_of_vehicle_specific_6040 | 0.400 | 0.061 | 0.167 | 0.000 | 0.004 | 612.588 | 0.466 |


Dominated single-AUV rows: 82
Dominated multi-AUV rows: 27

# Step12D class-number selection report

ICV supports the 6-class branch relative to the 5-class branch in the available Step04 evidence, but ICV must not be used alone because it naturally decreases when more classes are allowed.

The decision combines ICV, minimum class size, fragmentation risk, stability/qualitative notes where available, separation where available, interpretability, and runtime as a secondary criterion.

## Decision table
| n_classes | SD_fraction | ICV_mean | min_class_size | class_balance_score | number_of_small_classes | runtime_seconds | ranking_score | behavior_label | selected_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4.000 | 0.350 | 2131.731 | 41.000 | 0.342 | 0.000 |  | 2.250 | plausivel | 0.000 |
| 4.000 | 0.400 | 2131.731 | 41.000 | 0.342 | 0.000 |  | 2.250 | plausivel | 0.000 |
| 5.000 | 0.300 | 1755.583 | 30.000 | 0.250 | 0.000 |  | 2.100 | plausivel | 0.000 |
| 6.000 | 0.250 | 1328.040 | 30.000 | 0.280 | 0.000 | 1525.718 | 1.950 | plausivel | 1.000 |
| 10.000 | 0.200 | 754.780 | 11.000 | 0.157 | 2.000 |  | 2.600 | fragmenta demais | 0.000 |


## Selected branch
| n_classes | SD_fraction | ICV_mean | min_class_size | class_balance_score | runtime_seconds | justification_note |
| --- | --- | --- | --- | --- | --- | --- |
| 6.000 | 0.250 | 1328.040 | 30.000 | 0.280 | 1525.718 | Selected canonical branch: lower ICV than 5 classes while avoiding the fragmentation seen at 10 classes. |


Runtime is secondary for class-number choice because the largest costs are feature extraction, dictionary learning, sparse coding, and clustering; the final cut between nearby class counts is not the dominant computational burden.

# Step12D runtime discussion

Planner runtime is included as a penalty in the auxiliary weight scores, so a candidate can be rejected if it gains little scientific value at a high runtime cost.

For class number, runtime is treated as secondary. The scientific risks are over-fragmentation, very small classes, weak stability, and reduced interpretability.

## Single-AUV runtime evidence
| case_id | mission_duration | descriptor | alpha | runtime_seconds | STD_retention | tradeoff_score |
| --- | --- | --- | --- | --- | --- | --- |
| C06_representative | 48.000 | interest_map | 0.500 | 579.550 | 0.990 | 0.389 |
| C06_representative | 48.000 | representative_zone | 0.500 | 510.782 | 0.828 | 0.449 |
| C06_representative | 48.000 | boundary_score | 0.500 | 501.168 | 1.013 | 0.411 |
| C06_representative | 48.000 | representative_zone | 0.250 | 491.652 | 0.966 | 0.442 |
| C06_representative | 48.000 | interest_map | 0.250 | 418.852 | 1.034 | 0.428 |
| C01_representative | 48.000 | representative_zone | 0.000 | 390.569 | 1.000 | 0.375 |
| C01_representative | 48.000 | interest_map | 0.000 | 390.569 | 1.000 | 0.375 |
| C01_representative | 48.000 | boundary_score | 0.000 | 390.569 | 1.000 | 0.375 |
| C06_representative | 48.000 | boundary_score | 0.000 | 367.702 | 1.000 | 0.347 |
| C06_representative | 48.000 | representative_zone | 0.000 | 367.702 | 1.000 | 0.347 |
| C06_representative | 48.000 | interest_map | 0.000 | 367.702 | 1.000 | 0.347 |
| October_control | 48.000 | interest_map | 0.500 | 359.449 | 0.966 | 0.423 |
| C06_representative | 24.000 | boundary_score | 0.000 | 358.946 | 1.000 | 0.348 |
| C06_representative | 24.000 | interest_map | 0.000 | 358.946 | 1.000 | 0.348 |
| C06_representative | 24.000 | representative_zone | 0.000 | 358.946 | 1.000 | 0.348 |
| C06_representative | 48.000 | boundary_score | 0.250 | 352.009 | 1.022 | 0.447 |
| C06_representative | 48.000 | interest_map | 0.750 | 350.907 | 1.007 | 0.451 |
| October_control | 24.000 | interest_map | 0.500 | 349.783 | 0.994 | 0.440 |
| C06_representative | 24.000 | interest_map | 0.250 | 349.132 | 1.030 | 0.448 |
| C06_representative | 48.000 | representative_zone | 0.750 | 348.255 | 0.718 | 0.455 |
| October_control | 24.000 | boundary_score | 0.500 | 344.630 | 0.510 | 0.353 |
| C06_representative | 24.000 | representative_zone | 0.250 | 335.391 | 0.973 | 0.472 |
| C06_representative | 12.000 | interest_map | 0.000 | 332.859 | 1.000 | 0.354 |
| C06_representative | 12.000 | representative_zone | 0.000 | 332.859 | 1.000 | 0.354 |
| C06_representative | 12.000 | boundary_score | 0.000 | 332.859 | 1.000 | 0.354 |
| C01_representative | 24.000 | representative_zone | 0.000 | 331.354 | 1.000 | 0.354 |
| C01_representative | 24.000 | interest_map | 0.000 | 331.354 | 1.000 | 0.354 |
| C01_representative | 24.000 | boundary_score | 0.000 | 331.354 | 1.000 | 0.354 |
| C01_representative | 48.000 | interest_map | 0.250 | 325.238 | 1.029 | 0.471 |
| October_control | 12.000 | interest_map | 0.500 | 323.256 | 0.956 | 0.400 |


## Multi-AUV runtime evidence
| case_id | mission_duration | strategy | runtime_seconds | fleet_STD_retention | tradeoff_score |
| --- | --- | --- | --- | --- | --- |
| C06_representative | 48.000 | vehicle_specific_9010 | 723.130 | 1.207 | 0.390 |
| C06_representative | 24.000 | vehicle_specific_9010 | 658.089 | 1.113 | 0.378 |
| C06_representative | 48.000 | vehicle_specific_7030 | 655.686 | 1.020 | 0.523 |
| C06_representative | 48.000 | vehicle_specific_8020 | 638.697 | 1.115 | 0.448 |
| C06_representative | 12.000 | vehicle_specific_9010 | 637.724 | 1.071 | 0.342 |
| C01_representative | 48.000 | vehicle_specific_9010 | 637.407 | 1.140 | 0.374 |
| C01_representative | 48.000 | vehicle_specific_6040 | 618.796 | 0.840 | 0.612 |
| C06_representative | 24.000 | vehicle_specific_7030 | 615.744 | 0.800 | 0.573 |
| C01_representative | 48.000 | role_swap_of_vehicle_specific_6040 | 613.781 | 0.840 | 0.408 |
| C06_representative | 48.000 | vehicle_specific_6040 | 612.941 | 0.939 | 0.641 |
| C06_representative | 48.000 | role_swap_of_vehicle_specific_6040 | 612.588 | 0.939 | 0.466 |
| C01_representative | 24.000 | vehicle_specific_9010 | 608.581 | 0.998 | 0.393 |
| C06_representative | 24.000 | vehicle_specific_8020 | 605.999 | 0.938 | 0.419 |
| C01_representative | 48.000 | vehicle_specific_7030 | 595.593 | 0.940 | 0.504 |
| C06_representative | 12.000 | vehicle_specific_8020 | 590.761 | 0.986 | 0.373 |
| C06_representative | 12.000 | vehicle_specific_7030 | 588.741 | 0.757 | 0.447 |
| C01_representative | 12.000 | vehicle_specific_9010 | 587.060 | 0.997 | 0.350 |
| C06_representative | 24.000 | vehicle_specific_6040 | 584.745 | 0.827 | 0.602 |
| C01_representative | 48.000 | vehicle_specific_8020 | 572.734 | 1.044 | 0.430 |
| C06_representative | 24.000 | role_swap_of_vehicle_specific_6040 | 572.538 | 0.827 | 0.389 |
| October_control | 48.000 | vehicle_specific_9010 | 571.928 | 1.107 | 0.428 |
| C06_representative | 12.000 | vehicle_specific_6040 | 563.973 | 0.809 | 0.483 |
| C06_representative | 12.000 | role_swap_of_vehicle_specific_6040 | 559.774 | 0.809 | 0.333 |
| C01_representative | 24.000 | vehicle_specific_6040 | 551.888 | 0.836 | 0.588 |
| C01_representative | 24.000 | vehicle_specific_8020 | 548.194 | 0.995 | 0.451 |
| C01_representative | 24.000 | role_swap_of_vehicle_specific_6040 | 546.031 | 0.836 | 0.385 |
| October_control | 48.000 | vehicle_specific_8020 | 545.234 | 1.093 | 0.457 |
| C01_representative | 12.000 | vehicle_specific_6040 | 544.966 | 0.813 | 0.487 |
| October_control | 48.000 | vehicle_specific_6040 | 542.917 | 0.833 | 0.640 |
| C06_representative | 48.000 | vehicle_specific_5050 | 542.877 | 0.935 | 0.643 |


# Step12D final recommendations

Verdict: `QUANTITATIVE_JUSTIFICATION_READY`

1. The most useful weight plots are the Pareto plots: `single_auv_STD_loss_vs_regime_balance_pareto.png` and `multi_auv_STD_loss_vs_region_B_gain_pareto.png`.
2. The best single-AUV weight under the auxiliary score is listed in `step12d_single_auv_weight_decision_table.csv` with `selected_candidate_flag=True`.
3. The best multi-AUV weight under the auxiliary score is listed in `step12d_multi_auv_weight_decision_table.csv` with `selected_candidate_flag=True`.
4. Mission duration should be discussed as a sensitivity axis, because the same weights can behave differently under short and long missions.
5. Dominated configurations are those with `pareto_front_flag=False`; Pareto candidates are exported separately.
6. Runtime affects weight selection through `runtime_penalty`, but does not override scientific tradeoff metrics by itself.
7. Runtime has limited influence on class-number choice compared with ICV, class size, stability, separation, interpretability, and fragmentation risk.
8. The available ICV evidence supports 6 classes versus 5 classes, while the 10-class alternative illustrates why minimum ICV alone is not enough.
9. Yes, there is a real risk of choosing too many classes if ICV is minimized naively.
10. Thesis recommendation: present 6 classes as the canonical Fossum-style branch, and present planner weights as Pareto-supported tradeoffs rather than universal optima.
