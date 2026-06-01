# Step12C weight-choice justification

Weights are justified by sensitivity analysis rather than by arbitrary selection.

The tested range includes both extremes:
- Single-AUV `alpha=0`: pure STD baseline.
- Single-AUV `alpha=1`: pure descriptor objective.
- Multi-AUV `w_STD=1`: shared STD baseline.
- Multi-AUV `w_STD=0, w_region=1`: pure regime-role objective.

The final recommendation is based on collected STD, regime coverage, difference from baseline, runtime and operational feasibility.

## Single-AUV recommended rows
| case_id | mission_duration_requested_h | descriptor | run_name | alpha | STD_retention | regime_balance | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.967 | 0.000 | 0.686 |
| C01_representative | 12.000 | interest_map | interest_map_alpha100 | 1.000 | 0.889 | 0.000 | 0.657 |
| C01_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.969 | 0.000 | 0.669 |
| C01_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 0.970 | 0.000 | 0.683 |
| C01_representative | 24.000 | interest_map | interest_map_alpha050 | 0.500 | 0.993 | 0.000 | 0.675 |
| C01_representative | 24.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.919 | 0.000 | 0.664 |
| C01_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.976 | 0.056 | 0.664 |
| C01_representative | 48.000 | interest_map | interest_map_alpha050 | 0.500 | 1.003 | 0.116 | 0.682 |
| C01_representative | 48.000 | representative_zone | representative_zone_alpha075 | 0.750 | 0.939 | 0.000 | 0.665 |
| C06_representative | 12.000 | boundary_score | boundary_score_alpha100 | 1.000 | 0.913 | 0.000 | 0.661 |
| C06_representative | 12.000 | interest_map | interest_map_alpha075 | 0.750 | 0.969 | 0.000 | 0.680 |
| C06_representative | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.777 | 0.000 | 0.606 |
| C06_representative | 24.000 | boundary_score | boundary_score_alpha050 | 0.500 | 1.031 | 0.000 | 0.683 |
| C06_representative | 24.000 | interest_map | interest_map_alpha075 | 0.750 | 0.988 | 0.000 | 0.671 |
| C06_representative | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.829 | 0.000 | 0.627 |
| C06_representative | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 1.022 | 0.000 | 0.677 |
| C06_representative | 48.000 | interest_map | interest_map_alpha075 | 0.750 | 1.007 | 0.000 | 0.682 |
| C06_representative | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.828 | 0.000 | 0.617 |
| October_control | 12.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.931 | 0.000 | 0.488 |
| October_control | 12.000 | interest_map | interest_map_alpha025 | 0.250 | 0.948 | 0.000 | 0.524 |
| October_control | 12.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.869 | 0.000 | 0.634 |
| October_control | 24.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.965 | 0.000 | 0.519 |
| October_control | 24.000 | interest_map | interest_map_alpha025 | 0.250 | 1.025 | 0.000 | 0.539 |
| October_control | 24.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.870 | 0.000 | 0.642 |
| October_control | 48.000 | boundary_score | boundary_score_alpha025 | 0.250 | 0.949 | 0.102 | 0.553 |
| October_control | 48.000 | interest_map | interest_map_alpha025 | 0.250 | 1.005 | 0.000 | 0.527 |
| October_control | 48.000 | representative_zone | representative_zone_alpha050 | 0.500 | 0.894 | 0.000 | 0.649 |


## Multi-AUV recommended rows
| case_id | mission_duration_requested_h | strategy | w_STD | w_region | role_assignment | STD_retention | fleet_region_B_coverage | regime_specialization_score | recommendation_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.901 | 0.037 | 0.454 | 0.609 |
| C01_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.836 | 0.104 | 0.730 | 0.662 |
| C01_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.840 | 0.228 | 0.704 | 0.695 |
| C06_representative | 12.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.809 | 0.040 | 0.600 | 0.607 |
| C06_representative | 24.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.827 | 0.106 | 0.794 | 0.665 |
| C06_representative | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.939 | 0.213 | 0.694 | 0.723 |
| October_control | 12.000 | vehicle_specific_7030 | 0.700 | 0.300 | AUV1=region_A;AUV2=region_B | 0.811 | 0.037 | 0.689 | 0.634 |
| October_control | 24.000 | vehicle_specific_5050 | 0.500 | 0.500 | AUV1=region_A;AUV2=region_B | 0.780 | 0.100 | 0.852 | 0.676 |
| October_control | 48.000 | vehicle_specific_6040 | 0.600 | 0.400 | AUV1=region_A;AUV2=region_B | 0.833 | 0.217 | 0.852 | 0.715 |
