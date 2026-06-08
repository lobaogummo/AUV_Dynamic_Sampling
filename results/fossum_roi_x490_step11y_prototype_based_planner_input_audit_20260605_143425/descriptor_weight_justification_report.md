# Descriptor weight justification statistics

This diagnostic supports alpha-weight interpretation only. It does not rerun the planner and does not claim data-assimilation uncertainty reduction.

## Inputs
- Step08: `results\fossum_roi_x490_step08_final_descriptors_20260605_141912`
- Step11Y: `results\fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260605_143425`

## Computation
- Per-prototype statistics use finite valid cells from the Step08 descriptor maps.
- Class heterogeneity `H_c` is computed first from robust prototype amplitude, gradient P90, mean local variance, boundary density, and cold/neutral/warm entropy, after min-max normalization across classes.
- Descriptor selectivity `S_c,D` is computed from descriptor robust amplitude relative to its global robust amplitude and clipped to [0,1] for the hierarchical score.
- Global descriptor median/IQR pool finite cells across all six Step08 prototype maps for the same descriptor.
- STD correlation uses Step11Y `prototype_based_baseline_STD_norm` for cases whose predicted class matches the prototype.
- Classes without a Step11Y case have correlation, novelty, utility score, and alpha category marked as unavailable.
- Hierarchical alpha score uses `0.50*H_c + 0.30*S_c,D + 0.20*(1-|corr_STD|)` when STD correlation is available.
- When STD correlation is unavailable, the fallback diagnostic is `0.65*H_c + 0.35*S_c,D`; those rows are marked in `hierarchical_alpha_basis`.
- The final alpha is capped by class heterogeneity: low H -> max 0.25; medium H -> max 0.50; high/very-high H -> max 0.75. Alpha 1.00 is retained only as descriptor-only sensitivity.

## Class Heterogeneity First
| class_label_short | cv_regime_label | prototype_robust_amplitude | prototype_gradient_p90 | prototype_local_variance_mean | prototype_boundary_density | prototype_regime_entropy | class_heterogeneity_score | class_heterogeneity_category | class_alpha_cap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | multi_regime | 1.221 | 0.076 | 0.002 | 0.018 | 0.940 | 0.997 | very high heterogeneity | 0.750 |
| C02 | single_gradient | 0.496 | 0.042 | 0.000 | 0.100 | 0.500 | 0.239 | low heterogeneity | 0.250 |
| C03 | homogeneous | 0.355 | 0.053 | 0.000 | 0.000 | 0.000 | 0.136 | low heterogeneity | 0.250 |
| C04 | homogeneous | 0.338 | 0.022 | 0.000 | 0.000 | 0.000 | 0.000 | low heterogeneity | 0.250 |
| C05 | single_gradient | 0.725 | 0.044 | 0.001 | 0.100 | 0.500 | 0.329 | low heterogeneity | 0.250 |
| C06 | multi_regime | 0.613 | 0.038 | 0.000 | 0.018 | 0.936 | 0.554 | medium heterogeneity | 0.500 |

## Descriptor-Level Ranking
| descriptor | median_hierarchical_score | median_class_heterogeneity | median_selectivity | median_abs_correlation | median_hierarchical_alpha | rows_with_STD |
| --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r3_cells | 0.532 | 0.284 | 0.846 | 0.306 | 0.250 | 3.000 |
| warm_region | 0.531 | 0.284 | 1.000 | 0.538 | 0.250 | 3.000 |
| boundary_distance_score_r5_cells | 0.527 | 0.284 | 0.942 | 0.391 | 0.250 | 3.000 |
| boundary_distance_score_r1_cells | 0.519 | 0.284 | 0.223 | 0.182 | 0.250 | 3.000 |
| cold_region | 0.510 | 0.284 | 1.000 | 0.467 | 0.250 | 3.000 |
| boundary_score | 0.492 | 0.284 | 0.786 | 0.694 | 0.250 | 3.000 |
| representative_zone | 0.491 | 0.284 | 0.932 | 0.506 | 0.250 | 3.000 |
| interest_map | 0.475 | 0.284 | 0.829 | 0.685 | 0.250 | 3.000 |

## Interpretation
- High relative contrast means the descriptor varies strongly within that prototype relative to its global contrast.
- For sparse boundary-distance maps, very small global IQR can inflate relative contrast; use robust amplitude and planner behavior as companion evidence.
- Low absolute STD correlation means the descriptor adds a more independent reward-map signal, summarized by novelty = 1 - |correlation|.
- The hierarchical alpha score is therefore a diagnostic for reward-map sensitivity, not a direct measure of assimilation benefit.
- Boundary-distance descriptors should be interpreted as boundary/regime coverage proxies, while interest/representative maps are potential informativeness or typical-zone proxies.

## Correlation Availability
- Rows with available STD correlation: 24/48
- Rows without matching Step11Y STD case: 24

## Outputs
- `descriptor_weight_justification_statistics.csv`
- `figures/descriptor_weight_iqr_heatmap.png`
- `figures/descriptor_weight_robust_amplitude_heatmap.png`
- `figures/descriptor_weight_correlation_with_STD_heatmap.png`
- `figures/descriptor_weight_suggested_alpha_heatmap.png`
- `figures/descriptor_weight_class_heterogeneity.png`