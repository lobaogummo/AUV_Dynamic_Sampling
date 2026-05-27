# Step11AE remaining-days multi-AUV vehicle sweep

- Verdict: `STEP11AE_REMAINING_DAYS_MULTI_AUV_COMPLETED`
- Cases: C06_representative, October_control
- Planner runs executed: 10
- Existing Step11Z routes reused: yes

## Multi-AUV metrics
| case_id | strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | fleet_collected_STD | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C06_representative | baseline_STD | REUSED_STEP11Z | 0.052 | 0.000 | 161.418 | 0.000 | 10.629 | 0.526 |
| C06_representative | prototype_boundary_alpha050 | SUCCESS | 0.023 | 0.000 | 145.074 | 0.000 | 12.385 | 0.511 |
| C06_representative | vehicle_specific_conservative | SUCCESS | 0.063 | 0.000 | 159.179 | 0.044 | 5.769 | 0.510 |
| C06_representative | vehicle_specific_balanced | SUCCESS | 0.048 | 0.033 | 122.232 | 0.004 | 32.127 | 0.539 |
| C06_representative | vehicle_specific_strong_regime | SUCCESS | 0.024 | 0.035 | 130.471 | 0.003 | 27.580 | 0.528 |
| October_control | baseline_STD | REUSED_STEP11Z | 0.000 | 0.068 | 178.266 | 0.003 | 12.100 | 0.532 |
| October_control | prototype_boundary_alpha050 | SUCCESS | 0.053 | 0.000 | 117.347 | 0.000 | 13.770 | 0.526 |
| October_control | vehicle_specific_conservative | SUCCESS | 0.000 | 0.067 | 180.811 | 0.094 | 5.939 | 0.486 |
| October_control | vehicle_specific_balanced | SUCCESS | 0.042 | 0.037 | 144.560 | 0.003 | 26.267 | 0.538 |
| October_control | vehicle_specific_strong_regime | SUCCESS | 0.000 | 0.043 | 170.634 | 0.037 | 20.200 | 0.503 |


## Recommendations
| case_id | recommended_strategy | B_gain | std_retained | selection_rule |
| --- | --- | --- | --- | --- |
| C06_representative | vehicle_specific_strong_regime | 35376388.318 | 0.808 | best available tradeoff; criteria not fully met |
| October_control | vehicle_specific_conservative | 0.989 | 1.014 | best available tradeoff; criteria not fully met |


## Visual interpretation

- Use `figures/step11ae_*_multi_auv_predmodel_panel_by_method.png`.
- Each method is in its own panel over that day's TEMPpred predModel.
- Region maps are contours only; they are not the background.