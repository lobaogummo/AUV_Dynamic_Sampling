# Step11D logic report

Step11D figures show strategies over region masks/reward diagnostics. They are useful for regime-separation interpretation but do not always show the exact vehicle-specific information_map.

Computed path overlay metrics indicate whether visual overlap is real exact-cell overlap or simply both AUVs being attracted to the same high-value area.

| strategy | trajectory_overlap_ratio | duplicate_sampled_cells | inter_vehicle_mean_distance | visual_vs_real |
| --- | --- | --- | --- | --- |
| multi_baseline_STD | 0.0 | 0.0 | 17.05395907787059 | mostly visual/same-zone issue |
| multi_boundary_alpha050 | 0.0 | 0.0 | 15.34338889246864 | mostly visual/same-zone issue |
| vehicle_specific_regime_maps | 0.0161812297734627 | 5.0 | 19.49782583990364 | from saved fleet metrics; mostly visual/same-zone issue |
| vehicle_specific_with_crossing_proxy | 0.01 | 3.0 | 12.066040201831688 | from saved fleet metrics; mostly visual/same-zone issue |
| sequential_overlap_reduction | 0.022875816993464 | 7.0 | 20.02664363532462 | from saved fleet metrics; mostly visual/same-zone issue |
| post_solver_selected_pair | 0.0225806451612903 | 7.0 | 12.7451116992823 | from saved fleet metrics; mostly visual/same-zone issue |
