# Step12A single-AUV weight and duration sensitivity

- Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`
- Physical planner runs: 117
- Logical sensitivity rows: 135
- Prototype-based maps only: True
- TEMPpred used as objective: False

## Best weight recommendation
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | STD_retention | regime_balance | path_difference_from_baseline | solver_runtime | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.967 | 0.000 | 0.977 | 208.297 | 0.686 |
| C01_representative | 12.000 | interest_map | interest_map_alpha100 | 1.000 | 0.889 | 0.000 | 0.967 | 89.614 | 0.657 |
| C01_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.969 | 0.000 | 0.974 | 250.724 | 0.669 |
| C01_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.970 | 0.000 | 0.952 | 209.752 | 0.683 |
| C01_representative | 24.000 | interest_map | interest_map_alpha050 | 0.500 | 0.993 | 0.000 | 0.919 | 241.593 | 0.675 |
| C01_representative | 24.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.919 | 0.000 | 0.966 | 171.260 | 0.664 |
| C01_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.976 | 0.056 | 0.812 | 288.957 | 0.664 |
| C01_representative | 48.000 | interest_map | interest_map_alpha050 | 0.500 | 1.003 | 0.116 | 0.827 | 282.578 | 0.682 |
| C01_representative | 48.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.939 | 0.000 | 0.907 | 188.027 | 0.665 |
| C06_representative | 12.000 | boundary_score | boundary_score_alpha100 | 1.000 | 0.913 | 0.000 | 0.935 | 103.087 | 0.661 |
| C06_representative | 12.000 | interest_map | interest_map_alpha075 | 0.750 | 0.969 | 0.000 | 0.934 | 172.270 | 0.680 |
| C06_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.777 | 0.000 | 0.965 | 259.732 | 0.606 |
| C06_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 1.031 | 0.000 | 0.854 | 278.190 | 0.683 |
| C06_representative | 24.000 | interest_map | interest_map_alpha075 | 0.750 | 0.988 | 0.000 | 0.894 | 203.815 | 0.671 |
| C06_representative | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.829 | 0.000 | 0.964 | 305.461 | 0.627 |
| C06_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 1.022 | 0.000 | 0.825 | 352.009 | 0.677 |
| C06_representative | 48.000 | interest_map | interest_map_alpha075 | 0.750 | 1.007 | 0.000 | 0.864 | 350.907 | 0.682 |
| C06_representative | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.828 | 0.000 | 0.918 | 510.782 | 0.617 |
| October_control | 12.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.931 | 0.000 | 0.815 | 292.980 | 0.488 |
| October_control | 12.000 | interest_map | interest_map_alpha025 | 0.250 | 0.948 | 0.000 | 0.966 | 285.417 | 0.524 |
| October_control | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.869 | 0.000 | 0.971 | 208.474 | 0.634 |
| October_control | 24.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.965 | 0.000 | 0.883 | 313.431 | 0.519 |
| October_control | 24.000 | interest_map | interest_map_alpha025 | 0.250 | 1.025 | 0.000 | 0.901 | 281.906 | 0.539 |
| October_control | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.870 | 0.000 | 0.936 | 227.146 | 0.642 |
| October_control | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.949 | 0.102 | 0.840 | 297.501 | 0.553 |
| October_control | 48.000 | interest_map | interest_map_alpha025 | 0.250 | 1.005 | 0.000 | 0.840 | 298.563 | 0.527 |
| October_control | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.894 | 0.000 | 0.932 | 211.091 | 0.649 |


## Alpha sensitivity
| descriptor | alpha | mean_STD | mean_descriptor | mean_difference | mean_regime_balance | mean_runtime | mean_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_score | 0.000 | 208.424 | 197.464 | 0.000 | 0.012 | 322.075 | 0.486 |
| boundary_score | 0.250 | 203.967 | 218.830 | 0.858 | 0.017 | 302.457 | 0.619 |
| boundary_score | 0.500 | 168.325 | 282.590 | 0.922 | 0.000 | 298.714 | 0.616 |
| boundary_score | 0.750 | 156.519 | 286.209 | 0.940 | 0.000 | 190.973 | 0.597 |
| boundary_score | 1.000 | 150.719 | 281.554 | 0.960 | 0.000 | 127.636 | 0.592 |
| interest_map | 0.000 | 208.424 | 88.136 | 0.000 | 0.012 | 322.075 | 0.482 |
| interest_map | 0.250 | 209.296 | 92.218 | 0.847 | 0.006 | 313.604 | 0.609 |
| interest_map | 0.500 | 204.379 | 95.973 | 0.844 | 0.013 | 334.863 | 0.608 |
| interest_map | 0.750 | 157.718 | 127.098 | 0.945 | 0.000 | 217.108 | 0.603 |
| interest_map | 1.000 | 142.291 | 126.705 | 0.971 | 0.000 | 107.633 | 0.583 |
| representative_zone | 0.000 | 208.424 | 199.922 | 0.000 | 0.012 | 322.075 | 0.489 |
| representative_zone | 0.250 | 200.523 | 235.736 | 0.882 | 0.004 | 309.974 | 0.630 |
| representative_zone | 0.500 | 184.403 | 276.650 | 0.941 | 0.000 | 277.141 | 0.639 |
| representative_zone | 0.750 | 170.977 | 286.147 | 0.961 | 0.000 | 191.703 | 0.626 |
| representative_zone | 1.000 | 165.476 | 286.302 | 0.969 | 0.000 | 142.326 | 0.618 |


## Duration sensitivity
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


## Interpretation
- alpha=0 is the STD-only baseline.
- alpha=1 is the pure descriptor extreme.
- Recommended weights are selected only from successful runs with acceptable STD retention.
- TEMPpred figures are diagnostic backgrounds; objective figures use the real information_map.