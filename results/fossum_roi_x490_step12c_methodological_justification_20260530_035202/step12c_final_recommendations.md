# Step12C final recommendations

Verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`

Recommended use in thesis:
- Use Step12A as evidence for single-AUV descriptor sensitivity.
- Use Step12B as the stronger argument for multi-AUV regime-role planning.
- State clearly that vehicle-specific maps are currently a wrapper/proxy unless the planner is later modified to support native vehicle-specific prize maps.
- Use information_map figures when discussing objectives; use TEMPpred figures only as diagnostic spatial context.

## Best single-AUV rows
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | recommendation_score |
| --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.686 |
| C01_representative | 12.000 | interest_map | interest_map_alpha100 | 1.000 | 0.657 |
| C01_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.669 |
| C01_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.683 |
| C01_representative | 24.000 | interest_map | interest_map_alpha050 | 0.500 | 0.675 |
| C01_representative | 24.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.664 |
| C01_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.664 |
| C01_representative | 48.000 | interest_map | interest_map_alpha050 | 0.500 | 0.682 |
| C01_representative | 48.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.665 |
| C06_representative | 12.000 | boundary_score | boundary_score_alpha100 | 1.000 | 0.661 |
| C06_representative | 12.000 | interest_map | interest_map_alpha075 | 0.750 | 0.680 |
| C06_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.606 |
| C06_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.683 |
| C06_representative | 24.000 | interest_map | interest_map_alpha075 | 0.750 | 0.671 |
| C06_representative | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.627 |
| C06_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.677 |
| C06_representative | 48.000 | interest_map | interest_map_alpha075 | 0.750 | 0.682 |
| C06_representative | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.617 |
| October_control | 12.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.488 |
| October_control | 12.000 | interest_map | interest_map_alpha025 | 0.250 | 0.524 |
| October_control | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.634 |
| October_control | 24.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.519 |
| October_control | 24.000 | interest_map | interest_map_alpha025 | 0.250 | 0.539 |
| October_control | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.642 |
| October_control | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.553 |
| October_control | 48.000 | interest_map | interest_map_alpha025 | 0.250 | 0.527 |
| October_control | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.649 |


## Best multi-AUV rows
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.609 |
| C01_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.662 |
| C01_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.695 |
| C06_representative | 12.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.607 |
| C06_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.665 |
| C06_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.723 |
| October_control | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.634 |
| October_control | 24.000 | vehicle_specific_5050 | 0.500 | 0.500 | AUV1=region_A;AUV2=region_B | 0.676 |
| October_control | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.715 |


## Limitations
- Static descriptors do not guarantee true route-level crossing behavior.
- Vehicle-specific maps can improve specialization but can reduce STD collection.
- The current planner does not yet implement native route-level reward or native vehicle-specific prize maps.