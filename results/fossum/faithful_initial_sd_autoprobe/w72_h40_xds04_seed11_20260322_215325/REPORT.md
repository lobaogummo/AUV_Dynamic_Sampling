# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (72,40)
- dictionary size: 4
- seed: 11
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True

## Dendrogram-driven SD generation
- max merge distance observed: 1041.835330
- fractions used: 0.10, 0.20, 0.30, 0.40, 0.50
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.100000 | 104.183533 | 22 | 2 | 13.636364 | 86 | 0 | 631.977330 | 564.796000 | fragmenta demais |
| 0.200000 | 208.367066 | 7 | 17 | 42.857143 | 105 | 0 | 1298.016009 | 479.984687 | plausivel |
| 0.300000 | 312.550599 | 5 | 20 | 60.000000 | 122 | 0 | 1570.662854 | 549.651514 | plausivel |
| 0.400000 | 416.734132 | 4 | 20 | 75.000000 | 180 | 0 | 2223.412109 | 679.668315 | plausivel |
| 0.500000 | 520.917665 | 3 | 20 | 100.000000 | 180 | 0 | 3037.678792 | 720.914811 | plausivel |

## Ranking (balanced score, not only mean ICV)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 312.550599 | 1.900000 | 5 | 0 | 1570.662854 | 549.651514 | plausivel |
| 0.400000 | 416.734132 | 2.050000 | 4 | 0 | 2223.412109 | 679.668315 | plausivel |
| 0.200000 | 208.367066 | 2.550000 | 7 | 0 | 1298.016009 | 479.984687 | plausivel |

## Output locations
- root: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_215325`
- runs: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_215325/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_215325/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_215325/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, dendrogram cut, PCA).