# Step12A single-AUV weight and duration sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Physical planner runs: 21
- Logical sensitivity rows: 25
- Prototype-based maps only: True
- TEMPpred used as objective: False

## Best weight recommendation
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | STD_retention | regime_balance | path_difference_from_baseline | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_distance_score_r1_cells | boundary_distance_score_r1_cells_alpha075 | 0.750 | 0.971 | 0.000 | 0.928 | 159.570 | 0.645 |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | boundary_distance_score_r3_cells_alpha100 | 1.000 | 0.995 | 0.000 | 0.926 | 89.566 | 0.688 |
| C01_representative | 12.000 | boundary_distance_score_r5_cells | boundary_distance_score_r5_cells_alpha100 | 1.000 | 0.993 | 0.000 | 0.944 | 92.594 | 0.690 |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.967 | 0.000 | 0.977 | 239.174 | 0.685 |
| C01_representative | 12.000 | interest_map | interest_map_alpha100 | 1.000 | 0.889 | 0.000 | 0.967 | 98.403 | 0.657 |


## Alpha sensitivity
| descriptor | alpha | mean_STD | mean_descriptor | mean_difference | mean_regime_balance | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r1_cells | 0.000 | 94.367 | 24.486 | 0.000 | 0.000 | 398.107 | 0.411 |
| boundary_distance_score_r1_cells | 0.250 | 96.881 | 49.444 | 0.922 | 0.000 | 358.020 | 0.621 |
| boundary_distance_score_r1_cells | 0.500 | 87.734 | 69.782 | 0.934 | 0.000 | 309.576 | 0.640 |
| boundary_distance_score_r1_cells | 0.750 | 91.642 | 66.063 | 0.928 | 0.000 | 159.570 | 0.645 |
| boundary_distance_score_r1_cells | 1.000 | 52.740 | 80.016 | 0.971 | 0.000 | 91.487 | 0.542 |
| boundary_distance_score_r3_cells | 0.000 | 94.367 | 55.558 | 0.000 | 0.000 | 398.107 | 0.428 |
| boundary_distance_score_r3_cells | 0.250 | 87.323 | 115.839 | 0.922 | 0.000 | 351.728 | 0.625 |
| boundary_distance_score_r3_cells | 0.500 | 96.738 | 125.867 | 0.930 | 0.000 | 316.762 | 0.676 |
| boundary_distance_score_r3_cells | 0.750 | 88.141 | 135.170 | 0.932 | 0.000 | 179.432 | 0.657 |
| boundary_distance_score_r3_cells | 1.000 | 93.864 | 142.109 | 0.926 | 0.000 | 89.566 | 0.688 |
| boundary_distance_score_r5_cells | 0.000 | 94.367 | 76.252 | 0.000 | 0.000 | 398.107 | 0.452 |
| boundary_distance_score_r5_cells | 0.250 | 87.505 | 120.629 | 0.925 | 0.000 | 370.851 | 0.625 |
| boundary_distance_score_r5_cells | 0.500 | 95.859 | 135.779 | 0.926 | 0.000 | 311.448 | 0.676 |
| boundary_distance_score_r5_cells | 0.750 | 92.400 | 141.500 | 0.917 | 0.000 | 189.157 | 0.670 |
| boundary_distance_score_r5_cells | 1.000 | 93.691 | 149.732 | 0.944 | 0.000 | 92.594 | 0.690 |
| boundary_score | 0.000 | 94.367 | 116.153 | 0.000 | 0.000 | 398.107 | 0.518 |
| boundary_score | 0.250 | 94.885 | 130.545 | 0.898 | 0.000 | 337.176 | 0.675 |
| boundary_score | 0.500 | 91.255 | 138.618 | 0.977 | 0.000 | 239.174 | 0.685 |
| boundary_score | 0.750 | 81.378 | 126.086 | 0.917 | 0.000 | 203.840 | 0.622 |
| boundary_score | 1.000 | 79.612 | 134.886 | 0.946 | 0.000 | 113.652 | 0.633 |
| interest_map | 0.000 | 94.367 | 54.295 | 0.000 | 0.000 | 398.107 | 0.524 |
| interest_map | 0.250 | 93.931 | 54.569 | 0.852 | 0.000 | 366.801 | 0.652 |
| interest_map | 0.500 | 87.340 | 57.779 | 0.911 | 0.000 | 289.496 | 0.646 |
| interest_map | 0.750 | 83.144 | 60.235 | 0.955 | 0.000 | 279.107 | 0.645 |
| interest_map | 1.000 | 83.847 | 62.333 | 0.967 | 0.000 | 98.403 | 0.657 |


## Duration sensitivity
| mission_duration_requested_h | descriptor | mean_STD | mean_difference | mean_regime_balance | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_distance_score_r1_cells | 84.673 | 0.751 | 0.000 | 263.352 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 92.086 | 0.742 | 0.000 | 267.119 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 92.764 | 0.742 | 0.000 | 272.431 | 1.000 |
| 12.000 | boundary_score | 88.299 | 0.748 | 0.000 | 258.390 | 1.000 |
| 12.000 | interest_map | 88.526 | 0.737 | 0.000 | 286.383 | 1.000 |


## Interpretation
- alpha=0 is the STD-only baseline.
- alpha=1 is the pure descriptor extreme.
- Recommended weights are selected only from successful runs with acceptable STD retention.
- TEMPpred figures are diagnostic backgrounds; objective figures use the real information_map.

## Runtime summary
| mission_duration_requested_h | descriptor | alpha | mean_solver_runtime | max_solver_runtime | runs |
| --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_distance_score_r1_cells | 0.000 | 398.107 | 398.107 | 1.000 |
| 12.000 | boundary_distance_score_r1_cells | 0.250 | 358.020 | 358.020 | 1.000 |
| 12.000 | boundary_distance_score_r1_cells | 0.500 | 309.576 | 309.576 | 1.000 |
| 12.000 | boundary_distance_score_r1_cells | 0.750 | 159.570 | 159.570 | 1.000 |
| 12.000 | boundary_distance_score_r1_cells | 1.000 | 91.487 | 91.487 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.000 | 398.107 | 398.107 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.250 | 351.728 | 351.728 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.500 | 316.762 | 316.762 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.750 | 179.432 | 179.432 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 1.000 | 89.566 | 89.566 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 0.000 | 398.107 | 398.107 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 0.250 | 370.851 | 370.851 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 0.500 | 311.448 | 311.448 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 0.750 | 189.157 | 189.157 | 1.000 |
| 12.000 | boundary_distance_score_r5_cells | 1.000 | 92.594 | 92.594 | 1.000 |
| 12.000 | boundary_score | 0.000 | 398.107 | 398.107 | 1.000 |
| 12.000 | boundary_score | 0.250 | 337.176 | 337.176 | 1.000 |
| 12.000 | boundary_score | 0.500 | 239.174 | 239.174 | 1.000 |
| 12.000 | boundary_score | 0.750 | 203.840 | 203.840 | 1.000 |
| 12.000 | boundary_score | 1.000 | 113.652 | 113.652 | 1.000 |
| 12.000 | interest_map | 0.000 | 398.107 | 398.107 | 1.000 |
| 12.000 | interest_map | 0.250 | 366.801 | 366.801 | 1.000 |
| 12.000 | interest_map | 0.500 | 289.496 | 289.496 | 1.000 |
| 12.000 | interest_map | 0.750 | 279.107 | 279.107 | 1.000 |
| 12.000 | interest_map | 1.000 | 98.403 | 98.403 | 1.000 |
