# Step02 patch-size sensitivity report

## Scope
This rerun reused the legacy 02b methodology and redirected only data/output paths.

## Legacy Ranking
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 40.000000 | 24.000000 | 2.600000 | 1582.255634 | 79.304146 | 716.401969 | 48.000000 | 737.447519 |
| 48.000000 | 32.000000 | 3.000000 | 1611.915045 | 85.441922 | 755.041202 | 49.000000 | 727.715166 |
| 32.000000 | 20.000000 | 3.800000 | 1685.300314 | 238.902672 | 627.087232 | 47.000000 | 716.186585 |
| 56.000000 | 32.000000 | 4.300000 | 1828.502109 | 223.948272 | 640.634172 | 54.000000 | 692.651391 |
| 24.000000 | 16.000000 | 5.400000 | 1776.008327 | 239.700988 | 654.427503 | 28.000000 | 776.407458 |
| 16.000000 | 16.000000 | 6.100000 | 1806.499382 | 127.992506 | 858.363368 | 24.000000 | 916.656339 |
| 64.000000 | 36.000000 | 6.300000 | 1894.286987 | 151.848092 | 787.502039 | 18.000000 | 598.425036 |
| 72.000000 | 40.000000 | 6.300000 | 1776.092804 | 193.049479 | 1018.421849 | 13.000000 | 448.217818 |
| 80.000000 | 44.000000 | 7.200000 | 2046.271729 | 249.443914 | 869.720292 | 40.000000 | 412.666017 |

## Outputs
- `runs.csv`, `summary.csv`, `ranking.csv` are the direct legacy outputs.
- `patch_sensitivity_metrics.csv` mirrors the legacy summary for thesis-facing naming.
- `plots/` contains the legacy diagnostic figures.
- `class_members_wXX_hYY_seedSS/` contains the legacy contact sheets.

The legacy patch-size sensitivity logic was rerun on the FRESNEL paper ROI x490 dataset with only path, shape, day-count and metadata adaptations.
