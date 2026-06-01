# Step12C runtime and feasibility report

- Step12A total script runtime: `14222.578870600002` seconds.
- Step12B total script runtime: `85.05137679999461` seconds.
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
| 12.000 | baseline_shared_STD | 0.000 | 0.000 | 3.000 |
| 12.000 | role_swap_of_vehicle_specific_6040 | 0.000 | 0.000 | 1.000 |
| 12.000 | role_swap_of_vehicle_specific_7030 | 0.000 | 0.000 | 2.000 |
| 12.000 | vehicle_specific_00100 | 0.000 | 0.000 | 3.000 |
| 12.000 | vehicle_specific_2575 | 0.000 | 0.000 | 3.000 |
| 12.000 | vehicle_specific_5050 | 0.000 | 0.000 | 3.000 |
| 12.000 | vehicle_specific_6040 | 0.000 | 0.000 | 3.000 |
| 12.000 | vehicle_specific_7030 | 0.000 | 0.000 | 3.000 |
| 12.000 | vehicle_specific_8020 | 0.000 | 0.000 | 3.000 |
| 12.000 | vehicle_specific_9010 | 0.000 | 0.000 | 3.000 |
| 24.000 | baseline_shared_STD | 0.000 | 0.000 | 3.000 |
| 24.000 | role_swap_of_vehicle_specific_5050 | 0.000 | 0.000 | 1.000 |
| 24.000 | role_swap_of_vehicle_specific_6040 | 0.000 | 0.000 | 2.000 |
| 24.000 | vehicle_specific_00100 | 0.000 | 0.000 | 3.000 |
| 24.000 | vehicle_specific_2575 | 0.000 | 0.000 | 3.000 |
| 24.000 | vehicle_specific_5050 | 0.000 | 0.000 | 3.000 |
| 24.000 | vehicle_specific_6040 | 0.000 | 0.000 | 3.000 |
| 24.000 | vehicle_specific_7030 | 0.000 | 0.000 | 3.000 |
| 24.000 | vehicle_specific_8020 | 0.000 | 0.000 | 3.000 |
| 24.000 | vehicle_specific_9010 | 0.000 | 0.000 | 3.000 |
| 48.000 | baseline_shared_STD | 0.000 | 0.000 | 3.000 |
| 48.000 | role_swap_of_vehicle_specific_6040 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_00100 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_2575 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_5050 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_6040 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_7030 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_8020 | 0.000 | 0.000 | 3.000 |
| 48.000 | vehicle_specific_9010 | 0.000 | 0.000 | 3.000 |
