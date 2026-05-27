# Step11W planner figure/path lineage audit

Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11w_planner_figure_path_audit_20260526_145441`
Figures inventoried: 124
Regenerated diagnostic figures: 16
Coordinate check warnings: 0
Verdict: `FIGURE_AUDIT_FOUND_MISLEADING_BACKGROUND_REGENERATE`

## Main conclusions

- Step11A: planner used baseline STD and STD+boundary formulations recorded in the manifest. Existing figures are diagnostic multi-background overlays, not a single exact-objective plot in every panel.
- Step11B: descriptors were used in the objective for non-baseline runs. The saved `step11b_information_maps_by_descriptor.npz` is direct evidence. Some figures can look like STD because they use common/diagnostic backgrounds rather than the exact blended information_map.
- Step11C: the crossing proxy should be interpreted with region-colored paths. A high crossing_count can reflect short A/B switches near the boundary, not necessarily broad exploration of both regimes.
- Step11D: max computed exact-cell overlap=0.000; mostly same-zone/visual if below 0.05. The main issue is regime specialization and attraction to similar value zones, not necessarily literal overplotting.
- Coordinate audit: the source scripts consistently use ROI row/col coordinates over `imshow(..., origin='lower')` with no extent. No systematic x/y swap or extent bug was detected unless individual rows in the coordinate CSV say otherwise.
- Prototype-based correction: Step11Y/Step11Z remain the preferred methodological reference for region masks; old Step11C/11D region-mask figures should be labelled exploratory if they used fallback-derived masks.

## Recommended figure use

- Use metric barplots and regenerated standardized panels for thesis figures.
- Use original Step11B descriptor panels only with captions saying the background is diagnostic; use regenerated information_map panels to explain the actual objective.
- Use original Step11D overlays as diagnostics; pair them with overlap/distance metrics before claiming path overlap.

## Inventory snapshot

| step | file_type | count |
| --- | --- | --- |
| Step11A | csv | 13 |
| Step11A | figure_png | 23 |
| Step11A | json | 20 |
| Step11A | log_or_text | 45 |
| Step11A | markdown | 4 |
| Step11A | planner_netcdf | 18 |
| Step11A | pyc | 18 |
| Step11A | script | 29 |
| Step11A | vrp | 9 |
| Step11B | array | 3 |
| Step11B | csv | 48 |
| Step11B | figure_png | 51 |
| Step11B | json | 69 |
| Step11B | log_or_text | 157 |
| Step11B | markdown | 9 |
| Step11B | planner_netcdf | 66 |
| Step11B | pyc | 66 |
| Step11B | script | 105 |
| Step11B | vrp | 33 |
| Step11C | array | 6 |
| Step11C | csv | 11 |
| Step11C | figure_png | 21 |
| Step11C | json | 16 |
| Step11C | log_or_text | 35 |
| Step11C | markdown | 4 |
| Step11C | script | 24 |
| Step11C | vrp | 7 |
| Step11D | array | 8 |
| Step11D | csv | 16 |
| Step11D | figure_png | 29 |
| Step11D | json | 9 |
| Step11D | log_or_text | 35 |
| Step11D | markdown | 4 |
| Step11D | script | 24 |
| Step11D | vrp | 7 |

## Figure classification snapshot

| step | figure_name | classification | reason |
| --- | --- | --- | --- |
| Step11A | figures/step11a_all_cases_summary_panel.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | figures/step11a_C01_representative_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | figures/step11a_C06_representative_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | figures/step11a_collected_scores_barplot.png | TRUSTED_FOR_THESIS | Metric figure generated directly from saved metrics. |
| Step11A | figures/step11a_October_control_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | figures/step11a_October_reference_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | figures/step11a_solver_runtime_barplot.png | TRUSTED_FOR_THESIS | Metric figure generated directly from saved metrics. |
| Step11A | planner_runs/C01_representative__baseline_STD/plots/20260520T093931Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/C01_representative__enriched_boundary_alpha025/plots/20260520T094422Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/C01_representative__enriched_boundary_alpha050/plots/20260520T094824Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/C06_representative__baseline_STD/plots/20260520T092555Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/C06_representative__enriched_boundary_alpha025/plots/20260520T093025Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/C06_representative__enriched_boundary_alpha050/plots/20260520T093421Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/October_control__baseline_STD/plots/20260520T095214Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/October_control__enriched_boundary_alpha025/plots/20260520T095706Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | planner_runs/October_control__enriched_boundary_alpha050/plots/20260520T100222Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | step11a_all_cases_summary_panel.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | step11a_C01_representative_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | step11a_C06_representative_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | step11a_collected_scores_barplot.png | TRUSTED_FOR_THESIS | Metric figure generated directly from saved metrics. |
| Step11A | step11a_October_control_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | step11a_October_reference_baseline_vs_enriched_overlay.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11A | step11a_solver_runtime_barplot.png | TRUSTED_FOR_THESIS | Metric figure generated directly from saved metrics. |
| Step11B | figures/step11b_C01_representative_descriptor_trajectories_panel.png | MISLEADING_DUE_TO_BACKGROUND | Descriptors were used in objective, but existing panel backgrounds are not exact blended information_maps. |
| Step11B | figures/step11b_collected_scores_barplot.png | TRUSTED_FOR_THESIS | Metric figure generated directly from saved metrics. |
| Step11B | figures/step11b_distance_from_baseline_barplot.png | TRUSTED_FOR_THESIS | Metric figure generated directly from saved metrics. |
| Step11B | planner_runs/C01_representative__baseline_STD/plots/20260520T151039Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11B | planner_runs/C01_representative__boundary_alpha025/plots/20260520T151441Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11B | planner_runs/C01_representative__boundary_alpha050/plots/20260520T151743Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |
| Step11B | planner_runs/C01_representative__gradient_alpha025/plots/20260520T152142Z_wt.png | OK_BUT_NEEDS_CAPTION_CLARIFICATION | Usable if caption identifies background and coordinate system. |

## Planner map vs figure background snapshot

| step | case_id | run_name | descriptor | map_used_equals_background | conclusion |
| --- | --- | --- | --- | --- | --- |
| Step11A | C06_representative | baseline_STD | none | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | C06_representative | enriched_boundary_alpha025 | boundary_score_norm | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | C06_representative | enriched_boundary_alpha050 | boundary_score_norm | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | C01_representative | baseline_STD | none | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | C01_representative | enriched_boundary_alpha025 | boundary_score_norm | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | C01_representative | enriched_boundary_alpha050 | boundary_score_norm | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | October_control | baseline_STD | none | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | October_control | enriched_boundary_alpha025 | boundary_score_norm | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11A | October_control | enriched_boundary_alpha050 | boundary_score_norm | partial | Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel. |
| Step11B | C01_representative | C01_representative__baseline_STD | none | partial | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__boundary_alpha025 | boundary | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__boundary_alpha050 | boundary | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__gradient_alpha025 | gradient | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__gradient_alpha050 | gradient | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__heterogeneity_alpha025 | heterogeneity | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__heterogeneity_alpha050 | heterogeneity | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__representative_zone_alpha025 | representative_zone | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__representative_zone_alpha050 | representative_zone | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__interest_alpha025 | interest | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C01_representative | C01_representative__interest_alpha050 | interest | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__baseline_STD | none | partial | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__boundary_alpha025 | boundary | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__boundary_alpha050 | boundary | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__gradient_alpha025 | gradient | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__gradient_alpha050 | gradient | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__heterogeneity_alpha025 | heterogeneity | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__heterogeneity_alpha050 | heterogeneity | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__representative_zone_alpha025 | representative_zone | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__representative_zone_alpha050 | representative_zone | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |
| Step11B | C06_representative | C06_representative__interest_alpha025 | interest | no | Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map. |

## Coordinate checks snapshot

| step | case_id | trajectory_file | path_points_inside_fraction | suspected_x_y_swap | verdict |
| --- | --- | --- | --- | --- | --- |
| Step11A | C01_representative | planner_runs/C01_representative__baseline_STD/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | C01_representative | planner_runs/C01_representative__enriched_boundary_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | C01_representative | planner_runs/C01_representative__enriched_boundary_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | C06_representative | planner_runs/C06_representative__baseline_STD/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | C06_representative | planner_runs/C06_representative__enriched_boundary_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | C06_representative | planner_runs/C06_representative__enriched_boundary_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | October_control | planner_runs/October_control__baseline_STD/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | October_control | planner_runs/October_control__enriched_boundary_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11A | October_control | planner_runs/October_control__enriched_boundary_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__baseline_STD/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__boundary_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__boundary_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__gradient_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__gradient_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__heterogeneity_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__heterogeneity_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__interest_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__interest_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__representative_zone_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C01_representative | planner_runs/C01_representative__representative_zone_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__baseline_STD/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__boundary_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__boundary_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__gradient_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__gradient_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__heterogeneity_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__heterogeneity_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__interest_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__interest_alpha050/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
| Step11B | C06_representative | planner_runs/C06_representative__representative_zone_alpha025/trajectory_routes.json | 1.0 | False | OK_COORDINATES |
