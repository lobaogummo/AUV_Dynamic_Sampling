# Step11C logic report

Step11C used baseline STD, boundary_alpha050, and crossing proxy maps. The route-level crossing reward was not implemented in the planner objective; the saved runs therefore test a map-level proxy.

The visual question is whether the single AUV truly visits both regimes or mainly follows the boundary. The regenerated region-colored figures and `step11w_step11c_crossing_visual_diagnostics.csv` answer this from saved region masks and paths.

| run_name | fraction_region_A | fraction_region_B | fraction_boundary_core | visual_crossing_events_from_masks | interpretation |
| --- | --- | --- | --- | --- | --- |
| baseline_STD | 1.0 | 0.0 | 0.0 | 0 | mostly one region or boundary-adjacent |
| boundary_alpha050 | 0.8928571428571429 | 0.10714285714285714 | 0.03571428571428571 | 4 | visits both regions |
| crossing_gamma025 | 0.8518518518518519 | 0.14814814814814814 | 0.037037037037037035 | 4 | visits both regions |
| crossing_gamma050 | 0.9310344827586207 | 0.06896551724137931 | 0.034482758620689655 | 2 | visits both regions |
