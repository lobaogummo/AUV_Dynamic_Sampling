# Step11AE remaining-days multi-AUV vehicle sweep

- Verdict: `STEP11AE_COMPLETED_WITH_WARNINGS`
- Cases: C06_representative, October_control
- Planner runs executed: 12
- Existing Step11Z routes reused: yes

## Multi-AUV metrics
| case_id | strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | fleet_collected_STD | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C06_representative | baseline_STD | REUSED_STEP11Z | 0.057 | 0.000 | 169.193 | 0.000 | 8.528 | 0.528 |
| C06_representative | prototype_boundary_alpha050 | REUSED | 0.040 | 0.000 | 152.327 | 0.000 | 7.934 | 0.520 |
| C06_representative | vehicle_specific_conservative | SUCCESS | 0.061 | 0.000 | 164.109 | 0.081 | 4.074 | 0.490 |
| C06_representative | vehicle_specific_balanced | SUCCESS | 0.049 | 0.033 | 128.477 | 0.003 | 30.584 | 0.539 |
| C06_representative | vehicle_specific_strong_regime | SUCCESS | 0.024 | 0.034 | 127.680 | 0.003 | 27.311 | 0.527 |
| October_control | baseline_STD | REUSED_STEP11Z | 0.039 | 0.039 | 181.985 | 0.022 | 12.583 | 0.528 |
| October_control | prototype_boundary_alpha050 | REUSED_FAILED | 0.000 | 0.000 | 0.000 | 0.000 |  | 0.500 |
| October_control | vehicle_specific_conservative | SUCCESS | 0.019 | 0.019 | 177.187 | 1.000 | 0.000 | 0.019 |
| October_control | vehicle_specific_balanced | SUCCESS | 0.019 | 0.019 | 177.187 | 1.000 | 0.000 | 0.019 |
| October_control | vehicle_specific_strong_regime | SUCCESS | 0.019 | 0.019 | 177.187 | 1.000 | 0.000 | 0.019 |


## Recommendations
| case_id | recommended_strategy | B_gain | std_retained | selection_rule |
| --- | --- | --- | --- | --- |
| C06_representative | vehicle_specific_strong_regime | 34142328.260 | 0.755 | best available tradeoff; criteria not fully met |
| October_control | vehicle_specific_conservative | 0.489 | 0.974 | best available tradeoff; criteria not fully met |


## Visual interpretation

- Use `figures/step11ae_*_multi_auv_predmodel_panel_by_method.png`.
- Each method is in its own panel over that day's TEMPpred predModel.
- Region maps are contours only; they are not the background.

## Warnings

- October_control__multi_auv_12h__prototype_vehicle_specific_maps__AUV1 missing; running strong-regime proxy.
- October_control__multi_auv_12h__prototype_vehicle_specific_maps__AUV2 missing; running strong-regime proxy.
- 1 planner runs failed/timed out.