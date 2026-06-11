# Step12A IQR10 Temporal-Variability Proxy

This is post-processing only. The planner, VRP objective, Step08, Step11Y, and Step12A execution were not modified or rerun.

## Interpretation
IQR10 is the interquartile range of temperature over the previous available days at each ROI cell. It is a robust temporal-variability proxy: high values indicate places where recent temperature variability was larger, which may be relevant for future adaptive sampling or data-assimilation experiments.

This is not actual data assimilation. It does not prove uncertainty reduction and should not be described as assimilation skill. It only indicates whether an existing trajectory sampled recently variable regions that could be valuable for model-error diagnosis, model uncertainty evaluation, or future assimilation-aware mission planning.

Conceptual link: recent temporal variability is often associated with dynamical change, model mismatch potential, and information-rich sampling opportunities. In adaptive sampling, such regions are plausible candidates for observations because they may constrain evolving features more strongly than temporally stable zones.

## Literature Notes for Thesis Framing
Use IQR10 as a diagnostic proxy rather than an assimilation result. The interpretation is conceptually aligned with data-assimilation and adaptive-sampling literature in which observations are valuable when they target regions of larger forecast/model uncertainty, temporal change, or dynamically active structure. Suitable background references include Kalnay (2003) for atmospheric/oceanic data assimilation principles, Evensen (2009) for ensemble-based uncertainty and assimilation framing, and Lermusiaux (2007) for adaptive sampling/modeling links in ocean applications.

## IQR10 Window Validation
| case_id | date | iqr10_previous_days_used | iqr10_window_start_date | iqr10_window_end_date | iqr10_raw_min | iqr10_raw_max | iqr10_raw_mean | iqr10_raw_finite_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 2024-08-24 | 10.0000 | 2024-08-14 | 2024-08-23 | 0.1624 | 1.5306 | 0.7699 | 8004.0000 |

## Top Routes by IQR10 Collected
| descriptor | alpha | iqr10_collected_total | iqr10_collected_mean | iqr10_collected_per_km | percentage_path_in_top10_IQR10 | collected_STD | STD_retention | trajectory_length |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_score | 0.0000 | 95.2976 | 0.6229 | 2.5043 | 0.3203 | 90.6500 | 1.0000 | 38.0530 |
| boundary_distance_score_r1_cells | 0.0000 | 95.2976 | 0.6229 | 2.5043 | 0.3203 | 90.6500 | 1.0000 | 38.0530 |
| boundary_distance_score_r3_cells | 0.0000 | 95.2976 | 0.6229 | 2.5043 | 0.3203 | 90.6500 | 1.0000 | 38.0530 |
| boundary_distance_score_r5_cells | 0.0000 | 95.2976 | 0.6229 | 2.5043 | 0.3203 | 90.6500 | 1.0000 | 38.0530 |
| interest_map | 0.0000 | 95.2976 | 0.6229 | 2.5043 | 0.3203 | 90.6500 | 1.0000 | 38.0530 |

## Top Routes by IQR10 Gain vs Baseline
| descriptor | alpha | IQR10_gain_vs_baseline | IQR10_retention_vs_baseline | iqr10_collected_total | baseline_iqr10_collected_total | STD_retention | trajectory_length |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_score | 0.0000 | 0.0000 | 1.0000 | 95.2976 | 95.2976 | 1.0000 | 38.0530 |
| boundary_distance_score_r1_cells | 0.0000 | 0.0000 | 1.0000 | 95.2976 | 95.2976 | 1.0000 | 38.0530 |
| boundary_distance_score_r3_cells | 0.0000 | 0.0000 | 1.0000 | 95.2976 | 95.2976 | 1.0000 | 38.0530 |
| boundary_distance_score_r5_cells | 0.0000 | 0.0000 | 1.0000 | 95.2976 | 95.2976 | 1.0000 | 38.0530 |
| interest_map | 0.0000 | 0.0000 | 1.0000 | 95.2976 | 95.2976 | 1.0000 | 38.0530 |

## Validation Checks
- Existing Step12A rows processed: 25
- Routes with at least one valid ROI cell: 23/25
- Baseline comparisons available: 25/25
- Planner rerun: `False`

## Outputs
- `step12a_iqr10_metrics.csv`
- `step12a_iqr10_summary_by_descriptor_alpha.csv`
- `step12a_iqr10_checks.json`
- `figures/step12a_alpha_vs_iqr10_collected.png`
- `figures/step12a_iqr10_gain_vs_baseline.png`
- `figures/step12a_STD_retention_vs_IQR10_gain.png`
- `figures/step12a_iqr10_map_and_selected_routes.png`