# Step11AD legacy Step11 predModel panel figures

These figures are generated from existing routes only. No planner rerun was performed.

## Visual rule

- One panel per method/strategy.
- Background is the day-specific `TEMPpred` predModel from Step10F.
- Regime masks are contour overlays only where useful.
- Old STD/descriptor/region backgrounds should be treated as diagnostic unless explicitly captioned.

## Figures

| step | case_id | figure | methods_included | background |
| --- | --- | --- | --- | --- |
| Step11A | C06_representative | step11a_C06_representative_predmodel_panel_by_method.png | baseline_STD,enriched_boundary_alpha025,enriched_boundary_alpha050 | TEMPpred |
| Step11A | C01_representative | step11a_C01_representative_predmodel_panel_by_method.png | baseline_STD,enriched_boundary_alpha025,enriched_boundary_alpha050 | TEMPpred |
| Step11A | October_control | step11a_October_control_predmodel_panel_by_method.png | baseline_STD,enriched_boundary_alpha025,enriched_boundary_alpha050 | TEMPpred |
| Step11B | C01_representative | step11b_C01_representative_predmodel_panel_by_method_20260520_160652.png | baseline_STD,boundary_alpha025,boundary_alpha050,gradient_alpha025,gradient_alpha050,heterogeneity_alpha025,heterogeneity_alpha050,representative_zone_alpha025,representative_zone_alpha050,interest_alpha025,interest_alpha050 | TEMPpred |
| Step11B | C06_representative | step11b_C06_representative_predmodel_panel_by_method_20260520_165239.png | baseline_STD,boundary_alpha025,boundary_alpha050,gradient_alpha025,gradient_alpha050,heterogeneity_alpha025,heterogeneity_alpha050,representative_zone_alpha025,representative_zone_alpha050,interest_alpha025,interest_alpha050 | TEMPpred |
| Step11B | October_control | step11b_October_control_predmodel_panel_by_method_20260520_194733.png | baseline_STD,boundary_alpha025,boundary_alpha050,gradient_alpha025,gradient_alpha050,heterogeneity_alpha025,heterogeneity_alpha050,representative_zone_alpha025,representative_zone_alpha050,interest_alpha025,interest_alpha050 | TEMPpred |
| Step11C | C01_representative | step11c_C01_12h_predmodel_panel_by_method.png | baseline_STD,boundary_alpha050,crossing_gamma025,crossing_gamma050 | TEMPpred |
| Step11C | C01_representative | step11c_C01_6h_predmodel_panel_by_method.png | baseline_STD_6h,boundary_alpha050_6h,crossing_gamma050_6h | TEMPpred |
| Step11D | C01_representative | step11d_C01_multi_predmodel_panel_by_strategy.png | multi_baseline_STD,multi_boundary_alpha050,vehicle_specific_regime_maps,vehicle_specific_with_crossing_proxy,sequential_overlap_reduction,post_solver_selected_pair | TEMPpred |


## Interpretation notes

- Step11A: first baseline vs boundary-enriched test; use panels to see that boundary-only often changes little against baseline.
- Step11B: descriptors were used in the objective; old figures could look like STD/diagnostic backgrounds. These panels show all descriptor runs over the same day predModel for path comparison.
- Step11C: 12h boundary/crossing runs do visit two labelled regions in metrics, but the panel helps show whether this is broad exploration or mostly boundary-adjacent motion.
- Step11D: low exact overlap in metrics means the issue is mostly same-zone behaviour, not literal path overlay. Use the per-strategy panels plus distance/overlap metrics.