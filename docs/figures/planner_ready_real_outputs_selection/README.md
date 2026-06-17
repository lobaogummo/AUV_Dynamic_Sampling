# Planner-ready outputs: real repo outputs

These images are copied from real pipeline outputs under `results/`. They are not the schematic assets from `docs/figures/planner_ready_output_assets`.

| Diagram element | Use this image | Original source |
| --- | --- | --- |
| `reward maps / NetCDF / NPZ` | `01_real_reward_maps_step11y_prototype_maps_panel.png` | `results/fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260605_143425/figures/step11y_prototype_based_maps_panel.png` |
| `Lucrezia AUV planner` / planner run example | `02_real_lucrezia_planner_baseline_run.png` | `results/fossum_roi_x490_step11z_minimal_prototype_based_rerun_20260607_192933/planner_runs/C01_representative__single_auv_12h__baseli__51c49ddc1b/plots/20260607T185552Z_wt.png` |
| baseline trajectory | `03_real_baseline_trajectory.png` | same baseline planner-run plot as above |
| enriched/prototype trajectory | `04_real_enriched_prototype_trajectory.png` | `results/fossum_roi_x490_step11z_minimal_prototype_based_rerun_20260607_192933/planner_runs/C01_representative__single_auv_12h__protot__9ce4d78139/plots/20260607T192235Z_wt.png` |
| metrics: STD collected and region coverage | `05a_real_metrics_STD_collected_vs_region_coverage.png` | `results/fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity_20260608_163658/figures/step12b_STD_collected_vs_region_coverage.png` |
| metrics: overlap/specialization | `05b_real_metrics_overlap_vs_specialization.png` | `results/fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity_20260608_163658/figures/step12b_overlap_vs_specialization.png` |
| metrics: STD retention vs IQR10 gain | `05c_real_metrics_STD_retention_vs_IQR10_gain.png` | `results/fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260608_163658/figures/step12a_STD_retention_vs_IQR10_gain.png` |
| baseline vs enriched trajectory comparison | `06_real_baseline_vs_enriched_single_AUV_comparison.png` | `results/fossum_roi_x490_step11z_minimal_prototype_based_rerun_20260607_192933/figures/prototype_based_single_AUV_comparison_panel.png` |
| optional multi-AUV comparison | `07_real_multi_AUV_comparison_optional.png` | `results/fossum_roi_x490_step11z_minimal_prototype_based_rerun_20260607_192933/figures/prototype_based_multi_AUV_comparison_panel.png` |

Recommended use in the shown diagram:

- Use `01_real_reward_maps_step11y_prototype_maps_panel.png` in or under the reward-map box.
- Use `03_real_baseline_trajectory.png` and `04_real_enriched_prototype_trajectory.png` for the two middle thumbnails.
- Use one of the `05*.png` files in the metrics box; `05a` is closest to `STD collected / regime coverage`.
- Use `06_real_baseline_vs_enriched_single_AUV_comparison.png` in the final comparison box.
