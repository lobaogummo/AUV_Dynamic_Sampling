# Step11AB C01 region-target and vehicle-specific weight sweep

- Verdict: `STEP11AB_COMPLETED_RESULTS_READY`
- Single-AUV target success: `False`
- Recommended single-AUV: `planner-level mandatory waypoint/route-level reward needed`
- Recommended multi-AUV: `vehicle_specific_balanced`

## Targets
| target | roi_row | roi_col | std_value | selection_method |
| --- | --- | --- | --- | --- |
| target_A | 61.000 | 102.000 | 0.764 | max STD inside prototype region |
| target_B | 24.000 | 21.000 | 0.838 | max STD inside prototype region; min distance 15 cells enforced |


## Single-AUV metrics
| run_name | solver_status | regions_visited | crossing_count | fraction_path_region_A | fraction_path_region_B | collected_STD | trajectory_length | solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_STD | SUCCESS | 0.000 | 0.000 | 0.000 | 0.000 | 94.367 | 36.655 | 352.442 |
| prototype_boundary_alpha050 | SUCCESS | 0.000 | 0.000 | 0.000 | 0.000 | 91.350 | 38.093 | 287.345 |
| cross_region_targets | SUCCESS | 1.000 | 0.000 | 0.000 | 0.088 | 86.942 | 37.937 | 282.841 |


## Multi-AUV metrics
| strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | fleet_collected_STD | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_STD | SUCCESS | 0.000 | 0.015 | 186.493 | 0.000 | 15.916 | 0.507 |
| prototype_boundary_alpha050 | SUCCESS | 0.000 | 0.000 | 180.049 | 0.000 | 10.831 | 0.500 |
| vehicle_specific_conservative | SUCCESS | 0.000 | 0.036 | 180.676 | 0.268 | 1.286 | 0.384 |
| vehicle_specific_balanced | SUCCESS | 0.031 | 0.037 | 167.980 | 0.020 | 25.077 | 0.524 |
| vehicle_specific_strong_regime | SUCCESS | 0.059 | 0.039 | 151.711 | 0.003 | 30.808 | 0.548 |


## Interpretation

- If cross_region_targets still fails to visit both regimes, the map-level proxy is insufficient and the next step should be planner-level mandatory waypoint or route-level reward.
- For multi-AUV, choose the lightest vehicle-specific weight that improves region_B coverage while retaining at least 85% of baseline STD.