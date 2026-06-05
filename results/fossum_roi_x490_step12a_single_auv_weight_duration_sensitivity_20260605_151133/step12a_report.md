# Step12A single-AUV weight and duration sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Physical planner runs: 5
- Logical sensitivity rows: 5
- Prototype-based maps only: True
- TEMPpred used as objective: False

## Best weight recommendation
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | STD_retention | regime_balance | path_difference_from_baseline | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_distance_score_r3_cells | boundary_distance_score_r3_cells_alpha100 | 1.000 | 0.995 | 0.000 | 0.926 | 100.928 | 0.688 |


## Alpha sensitivity
| descriptor | alpha | mean_STD | mean_descriptor | mean_difference | mean_regime_balance | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r3_cells | 0.000 | 94.367 | 55.558 | 0.000 | 0.000 | 433.434 | 0.428 |
| boundary_distance_score_r3_cells | 0.250 | 87.323 | 115.839 | 0.922 | 0.000 | 408.892 | 0.625 |
| boundary_distance_score_r3_cells | 0.500 | 96.738 | 125.867 | 0.930 | 0.000 | 268.805 | 0.676 |
| boundary_distance_score_r3_cells | 0.750 | 88.141 | 135.170 | 0.932 | 0.000 | 173.377 | 0.657 |
| boundary_distance_score_r3_cells | 1.000 | 93.864 | 142.109 | 0.926 | 0.000 | 100.928 | 0.688 |


## Duration sensitivity
| mission_duration_requested_h | descriptor | mean_STD | mean_difference | mean_regime_balance | mean_runtime | success_rate |
| --- | --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_distance_score_r3_cells | 92.086 | 0.742 | 0.000 | 277.087 | 1.000 |


## Interpretation
- alpha=0 is the STD-only baseline.
- alpha=1 is the pure descriptor extreme.
- Recommended weights are selected only from successful runs with acceptable STD retention.
- TEMPpred figures are diagnostic backgrounds; objective figures use the real information_map.

## Runtime summary
| mission_duration_requested_h | descriptor | alpha | mean_solver_runtime | max_solver_runtime | runs |
| --- | --- | --- | --- | --- | --- |
| 12.000 | boundary_distance_score_r3_cells | 0.000 | 433.434 | 433.434 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.250 | 408.892 | 408.892 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.500 | 268.805 | 268.805 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 0.750 | 173.377 | 173.377 | 1.000 |
| 12.000 | boundary_distance_score_r3_cells | 1.000 | 100.928 | 100.928 | 1.000 |
