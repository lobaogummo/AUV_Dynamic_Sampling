# Step12B IQR10 Temporal-Variability Proxy

This is post-processing only. The planner was not rerun.

IQR10 is the interquartile range of temperature over the previous 10 available days at each ROI cell. It is a robust temporal-variability proxy, not data assimilation and not evidence of uncertainty reduction.

The diagnostic indicates whether existing trajectories sample recently variable regions that may be relevant for future model-uncertainty, adaptive-sampling, or assimilation-aware experiments.

## IQR10 Window Validation
| case_id | date | iqr10_previous_days_used | iqr10_window_start_date | iqr10_window_end_date | iqr10_raw_min | iqr10_raw_max | iqr10_raw_mean | iqr10_raw_finite_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01_representative | 2024-08-24 | 10.0000 | 2024-08-14 | 2024-08-23 | 0.1624 | 1.5306 | 0.7699 | 8004.0000 |
| C06_representative | 2023-12-22 | 10.0000 | 2023-12-12 | 2023-12-21 | 0.0442 | 0.5551 | 0.2173 | 8004.0000 |
| October_control | 2024-10-30 | 10.0000 | 2024-10-20 | 2024-10-29 | 0.2351 | 1.7777 | 1.0293 | 8004.0000 |

## Best Fleet Routes by IQR10 Collected
| case_id | date | strategy | fleet_iqr10_collected_total | fleet_iqr10_collected_per_km | mean_percentage_path_in_top10_IQR10 | fleet_collected_STD | STD_retention | fleet_trajectory_length |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C06_representative | 2023-12-22 | vehicle_specific_9010 | 157.3875 | 2.1374 | 0.0819 | 170.3502 | 1.0759 | 73.6350 |
| C06_representative | 2023-12-22 | vehicle_specific_8020 | 153.3069 | 2.1173 | 0.1041 | 163.8860 | 1.0351 | 72.4060 |
| C06_representative | 2023-12-22 | baseline_shared_STD | 147.3220 | 2.0088 | 0.0881 | 158.3267 | 1.0000 | 73.3370 |
| C06_representative | 2023-12-22 | vehicle_specific_00100 | 103.7854 | 1.4093 | 0.0292 | 124.2397 | 0.7847 | 73.6440 |
| C06_representative | 2023-12-22 | role_swap_of_vehicle_specific_6040 | 93.7639 | 1.2881 | 0.0216 | 135.6011 | 0.8565 | 72.7920 |
| October_control | 2024-10-30 | baseline_shared_STD | 126.7066 | 1.6442 | 0.0000 | 181.9847 | 1.0000 | 77.0650 |
| October_control | 2024-10-30 | role_swap_of_vehicle_specific_2575 | 120.8252 | 1.6073 | 0.0000 | 177.1868 | 0.9736 | 75.1740 |
| October_control | 2024-10-30 | vehicle_specific_2575 | 120.8252 | 1.6073 | 0.0000 | 177.1868 | 0.9736 | 75.1740 |
| October_control | 2024-10-30 | vehicle_specific_5050 | 120.8252 | 1.6073 | 0.0000 | 177.1868 | 0.9736 | 75.1740 |
| October_control | 2024-10-30 | vehicle_specific_6040 | 120.8252 | 1.6073 | 0.0000 | 177.1868 | 0.9736 | 75.1740 |

## Best Fleet Routes by IQR10 Gain vs Baseline
| case_id | date | strategy | fleet_IQR10_gain_vs_baseline | fleet_IQR10_retention_vs_baseline | fleet_IQR10_gain_pct_vs_baseline | fleet_iqr10_collected_total | baseline_fleet_iqr10_collected_total | STD_retention |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C06_representative | 2023-12-22 | vehicle_specific_9010 | 10.0655 | 1.0683 | 6.8323 | 157.3875 | 147.3220 | 1.0759 |
| C06_representative | 2023-12-22 | vehicle_specific_8020 | 5.9849 | 1.0406 | 4.0625 | 153.3069 | 147.3220 | 1.0351 |
| C06_representative | 2023-12-22 | baseline_shared_STD | 0.0000 | 1.0000 | 0.0000 | 147.3220 | 147.3220 | 1.0000 |
| C06_representative | 2023-12-22 | vehicle_specific_00100 | -43.5365 | 0.7045 | -29.5520 | 103.7854 | 147.3220 | 0.7847 |
| C06_representative | 2023-12-22 | role_swap_of_vehicle_specific_6040 | -53.5581 | 0.6365 | -36.3545 | 93.7639 | 147.3220 | 0.8565 |
| October_control | 2024-10-30 | baseline_shared_STD | 0.0000 | 1.0000 | 0.0000 | 126.7066 | 126.7066 | 1.0000 |
| October_control | 2024-10-30 | role_swap_of_vehicle_specific_2575 | -5.8814 | 0.9536 | -4.6418 | 120.8252 | 126.7066 | 0.9736 |
| October_control | 2024-10-30 | vehicle_specific_2575 | -5.8814 | 0.9536 | -4.6418 | 120.8252 | 126.7066 | 0.9736 |
| October_control | 2024-10-30 | vehicle_specific_5050 | -5.8814 | 0.9536 | -4.6418 | 120.8252 | 126.7066 | 0.9736 |
| October_control | 2024-10-30 | vehicle_specific_6040 | -5.8814 | 0.9536 | -4.6418 | 120.8252 | 126.7066 | 0.9736 |

## Validation Checks
- Vehicle rows processed: 54
- Fleet rows produced: 27
- Vehicle routes mapped: 52/54
- Fleet baseline comparisons available: 27/27
- Planner rerun: `False`