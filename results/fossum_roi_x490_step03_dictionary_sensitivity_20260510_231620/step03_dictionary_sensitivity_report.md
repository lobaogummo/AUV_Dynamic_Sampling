# Step03 dictionary-size sensitivity report

## Scope
This rerun reused the legacy 03a methodology and redirected only data/output paths, plus the Step02-selected patch.

## Legacy Ranking
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 2.000000 | 1.000000 | 1478.119385 | 0.000000 | 541.583776 | 51.000000 | 520.964112 |
| 4.000000 | 2.700000 | 1582.255634 | 79.304146 | 716.401969 | 48.000000 | 746.104454 |
| 3.000000 | 4.500000 | 1702.373557 | 171.606681 | 805.311100 | 37.000000 | 622.158150 |
| 9.000000 | 5.600000 | 1797.032028 | 97.653735 | 548.870471 | 36.000000 | 1598.314560 |
| 5.000000 | 6.400000 | 1754.912204 | 222.534194 | 628.283583 | 34.000000 | 872.337988 |
| 7.000000 | 6.600000 | 1720.352585 | 191.761454 | 809.630932 | 13.000000 | 1232.816007 |
| 10.000000 | 6.700000 | 1758.591193 | 127.270367 | 880.565873 | 40.000000 | 1809.841195 |
| 6.000000 | 7.200000 | 1744.924863 | 184.964380 | 844.616328 | 12.000000 | 1063.506113 |
| 8.000000 | 7.600000 | 1838.930405 | 97.201538 | 827.251689 | 12.000000 | 1395.091554 |
| 11.000000 | 8.100000 | 1882.648674 | 192.339399 | 616.499574 | 15.000000 | 1946.302047 |
| 12.000000 | 9.200000 | 2069.226958 | 789.447320 | 1311.742485 | 40.000000 | 1600.537665 |

## Outputs
- `runs.csv`, `summary.csv`, `ranking.csv` are the direct legacy outputs.
- `dictionary_sensitivity_metrics.csv` and `dictionary_sensitivity_ranking.csv` mirror the legacy outputs for thesis-facing naming.
- `plots/` contains the legacy diagnostic figures.
- `class_members_xdsXX_seedSS/` contains the legacy contact sheets.

The legacy dictionary-size sensitivity logic was rerun on the FRESNEL paper ROI x490 dataset using the Step02 recommended patch size, with only path, shape, day-count and metadata adaptations.
