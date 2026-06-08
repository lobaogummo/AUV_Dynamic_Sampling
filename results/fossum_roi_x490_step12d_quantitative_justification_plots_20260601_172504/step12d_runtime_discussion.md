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

