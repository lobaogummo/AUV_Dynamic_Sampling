# Lucid trajectory-results diagram

Use `trajectory_results_lucid_board.png` as a single image in Lucid, or rebuild the board with the assets in `assets/`.

Suggested Lucid structure:
1. Methods: prototype classes and descriptor maps.
2. Single-AUV sensitivity: alpha sweep and representative trajectory maps.
3. Multi-AUV sensitivity: vehicle-specific 60/40 recommendation and AUV role maps.
4. Final recommendation: 60/40 vehicle-specific maps for multi-AUV, with the proxy/wrapper limitation stated.

Selected assets:
- `C01_representative_12h_boundary_score_alpha050.png`: Single C01 12h: boundary score alpha 0.50
- `C06_representative_48h_interest_map_alpha075.png`: Single C06 48h: interest map alpha 0.75
- `October_control_48h_representative_zone_alpha050.png`: Single October 48h: representative zone alpha 0.50
- `C06_representative_48h_vehicle_specific_6040_AUV1.png`: Multi C06 48h: AUV1 region A, recommended 60/40
- `C06_representative_48h_vehicle_specific_6040_AUV2.png`: Multi C06 48h: AUV2 region B, recommended 60/40
- `step12a_alpha_sensitivity.png`: Single-AUV descriptor/alpha evidence
- `step12b_weight_sensitivity.png`: Multi-AUV final weight evidence
