# Step12 predModel trajectory panels

These panels redraw existing Step12A and Step12B planner routes over the day-specific predModel/TEMPpred background.

Important: predModel/TEMPpred is a diagnostic background here. It is not the objective map. The objective logic is grouped by descriptor/alpha for Step12A and vehicle-specific weights for Step12B.

- Step12A source: `results\fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260608_163658`
- Step12B source: `results\fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity_20260608_163658`
- Panels created: 8

## Manifest
| step | case_id | duration_h | group_logic | rows | panel_png | panel_svg |
| --- | --- | --- | --- | --- | --- | --- |
| Step12A | C01_representative | 12.000 | boundary_distance_score_r1_cells | 5.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12a_single_auv\step12a_C01_representative_12h_boundary_distance_score_r1_cells_all_alphas_over_predmodel.png |  |
| Step12A | C01_representative | 12.000 | boundary_distance_score_r3_cells | 5.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12a_single_auv\step12a_C01_representative_12h_boundary_distance_score_r3_cells_all_alphas_over_predmodel.png |  |
| Step12A | C01_representative | 12.000 | boundary_distance_score_r5_cells | 5.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12a_single_auv\step12a_C01_representative_12h_boundary_distance_score_r5_cells_all_alphas_over_predmodel.png |  |
| Step12A | C01_representative | 12.000 | boundary_score | 5.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12a_single_auv\step12a_C01_representative_12h_boundary_score_all_alphas_over_predmodel.png |  |
| Step12A | C01_representative | 12.000 | interest_map | 5.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12a_single_auv\step12a_C01_representative_12h_interest_map_all_alphas_over_predmodel.png |  |
| Step12B | C01_representative | 12.000 | vehicle_specific_weight_strategies | 9.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12b_multi_auv\step12b_C01_representative_12h_all_strategies_over_predmodel.png |  |
| Step12B | C06_representative | 12.000 | vehicle_specific_weight_strategies | 9.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12b_multi_auv\step12b_C06_representative_12h_all_strategies_over_predmodel.png |  |
| Step12B | October_control | 12.000 | vehicle_specific_weight_strategies | 9.000 | docs\lucid_trajectory_results\step12_predmodel_result_panels_20260609_022235\step12b_multi_auv\step12b_October_control_12h_all_strategies_over_predmodel.png |  |
