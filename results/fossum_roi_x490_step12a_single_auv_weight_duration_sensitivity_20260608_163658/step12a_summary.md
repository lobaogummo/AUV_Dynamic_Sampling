# Step12A single-AUV weight and duration sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Physical planner runs: 21
- Logical sensitivity rows: 25
- Prototype-based maps only: True
- TEMPpred used as objective: False

## Best weight recommendation
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | STD_retention | regime_balance | path_difference_from_baseline | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | boundary_distance_score_r1_cells_alpha075 | 0.750 | 0.936 | 0.000 | 0.969 | 680.524 | 0.619 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | boundary_distance_score_r3_cells_alpha100 | 1.000 | 1.042 | 0.000 | 0.967 | 214.716 | 0.710 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | boundary_distance_score_r5_cells_alpha100 | 1.000 | 1.034 | 0.000 | 0.971 | 287.738 | 0.708 |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.982 | 0.000 | 0.980 | 924.108 | 0.683 |
| C01_representative | 12.000 | interest_map | interest_map_alpha050 | 0.500 | 1.045 | 0.000 | 0.908 | 1344.849 | 0.685 |


## Alpha sensitivity
| descriptor | alpha | mean_STD | mean_descriptor | mean_difference | mean_regime_balance | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r1_cells | 0.000 | 90.650 | 17.034 | 0.000 | 0.000 | 1524.010 | 0.388 |
| boundary_distance_score_r1_cells | 0.250 |  |  |  | 0.000 | 1800.000 | 0.000 |
| boundary_distance_score_r1_cells | 0.500 |  |  |  | 0.000 | 1800.000 | 0.000 |
| boundary_distance_score_r1_cells | 0.750 | 84.847 | 65.798 | 0.969 | 0.000 | 680.524 | 0.619 |
| boundary_distance_score_r1_cells | 1.000 | 56.245 | 90.079 | 0.980 | 0.000 | 129.997 | 0.565 |
| boundary_distance_score_r3_cells | 0.000 | 90.650 | 42.845 | 0.000 | 0.000 | 1524.010 | 0.410 |
| boundary_distance_score_r3_cells | 0.250 | 86.648 | 113.566 | 0.909 | 0.000 | 1271.844 | 0.630 |
| boundary_distance_score_r3_cells | 0.500 | 96.744 | 126.112 | 0.964 | 0.000 | 949.794 | 0.695 |
| boundary_distance_score_r3_cells | 0.750 | 87.915 | 135.435 | 0.977 | 0.000 | 564.156 | 0.676 |
| boundary_distance_score_r3_cells | 1.000 | 94.488 | 142.867 | 0.967 | 0.000 | 214.716 | 0.710 |
| boundary_distance_score_r5_cells | 0.000 | 90.650 | 55.659 | 0.000 | 0.000 | 1524.010 | 0.424 |
| boundary_distance_score_r5_cells | 0.250 | 85.938 | 118.625 | 0.969 | 0.000 | 1370.500 | 0.636 |
| boundary_distance_score_r5_cells | 0.500 | 91.197 | 130.738 | 0.973 | 0.000 | 1128.910 | 0.673 |
| boundary_distance_score_r5_cells | 0.750 | 92.400 | 141.500 | 0.967 | 0.000 | 625.547 | 0.691 |
| boundary_distance_score_r5_cells | 1.000 | 93.691 | 149.732 | 0.971 | 0.000 | 287.738 | 0.708 |
| boundary_score | 0.000 | 90.650 | 107.187 | 0.000 | 0.000 | 1524.010 | 0.507 |
| boundary_score | 0.250 | 90.082 | 129.473 | 0.959 | 0.000 | 1501.302 | 0.682 |
| boundary_score | 0.500 | 89.061 | 130.766 | 0.980 | 0.000 | 924.108 | 0.683 |
| boundary_score | 0.750 | 76.820 | 125.093 | 0.961 | 0.000 | 1173.437 | 0.625 |
| boundary_score | 1.000 | 84.330 | 136.238 | 0.984 | 0.000 | 1023.533 | 0.673 |
| interest_map | 0.000 | 90.650 | 52.426 | 0.000 | 0.000 | 1524.010 | 0.512 |
| interest_map | 0.250 | 91.731 | 60.511 | 0.904 | 0.000 | 1652.192 | 0.676 |
| interest_map | 0.500 | 94.736 | 59.356 | 0.908 | 0.000 | 1344.849 | 0.685 |
| interest_map | 0.750 | 82.722 | 59.732 | 0.980 | 0.000 | 731.559 | 0.651 |
| interest_map | 1.000 | 59.087 | 64.897 | 0.977 | 0.000 | 370.325 | 0.575 |


## Duration sensitivity
| mission_duration_requested_h | descriptor | mean_STD | mean_difference | mean_regime_balance | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_distance_score_r1_cells | 77.247 | 0.650 | 0.000 | 1186.906 | 0.600 |
| 12.000 | boundary_distance_score_r3_cells | 91.289 | 0.764 | 0.000 | 904.904 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 90.775 | 0.776 | 0.000 | 987.341 | 1.000 |
| 12.000 | boundary_score | 86.189 | 0.777 | 0.000 | 1229.278 | 1.000 |
| 12.000 | interest_map | 83.785 | 0.754 | 0.000 | 1124.587 | 1.000 |


## Interpretation
- alpha=0 is the STD-only baseline.
- alpha=1 is the pure descriptor extreme.
- Recommended weights are selected only from successful runs with acceptable STD retention.
- TEMPpred figures are diagnostic backgrounds; objective figures use the real information_map.