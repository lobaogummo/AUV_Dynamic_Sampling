# CAND_B vs USER_DIRECT_KM Summary

- day_used: `2024-10-30`
- deterministic_selected: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/deterministic_2024_surface_300_thesis_relative_km_display_assumed/TEMP_surface_2024_z300.png`
- candb_iou_vs_operational: `0.3727`
- user_direct_iou_vs_operational: `0.1086`
- candb_vs_user_iou: `0.2837`
- final_classification: `CAND_B PREFERRED`

Methodological distinction:
- CAND_B = registration-derived inferred transform (stronger operational consistency, not native georef proof).
- USER_DIRECT_KM = direct local-km display method (simpler and intuitive, but display-derived).

Recommendation:
Para os proximos passos, recomenda-se usar CAND_B como referencia operacional para transferir a ROI/regimes para a grelha do planner.
