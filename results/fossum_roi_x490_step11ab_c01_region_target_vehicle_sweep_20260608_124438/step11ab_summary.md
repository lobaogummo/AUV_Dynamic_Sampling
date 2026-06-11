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
| baseline_STD | SUCCESS | 0.000 | 0.000 | 0.000 | 0.000 | 97.489 | 37.356 | 878.798 |
| prototype_boundary_alpha050 | SUCCESS | 0.000 | 0.000 | 0.000 | 0.000 | 96.487 | 38.229 | 796.601 |
| cross_region_targets | SUCCESS | 1.000 | 0.000 | 0.000 | 0.148 | 89.256 | 37.984 | 600.302 |


## Multi-AUV metrics
| strategy | solver_status | fleet_region_A_coverage | fleet_region_B_coverage | fleet_collected_STD | trajectory_overlap_ratio | inter_vehicle_mean_distance | complementarity_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_STD | SUCCESS | 0.000 | 0.000 | 182.088 | 0.000 | 12.889 | 0.500 |
| prototype_boundary_alpha050 | SUCCESS | 0.000 | 0.000 | 185.071 | 0.000 | 12.442 | 0.500 |
| vehicle_specific_conservative | SUCCESS | 0.000 | 0.037 | 178.646 | 0.104 | 2.654 | 0.467 |
| vehicle_specific_balanced | SUCCESS | 0.031 | 0.038 | 166.705 | 0.003 | 25.739 | 0.533 |
| vehicle_specific_strong_regime | SUCCESS | 0.058 | 0.039 | 153.346 | 0.003 | 29.454 | 0.547 |


## Interpretation

- If cross_region_targets still fails to visit both regimes, the map-level proxy is insufficient and the next step should be planner-level mandatory waypoint or route-level reward.
- For multi-AUV, choose the lightest vehicle-specific weight that improves region_B coverage while retaining at least 85% of baseline STD.