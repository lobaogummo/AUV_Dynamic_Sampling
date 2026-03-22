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
- StandardScaler applied before Ward: False

## Dendrogram-driven SD generation
- max merge distance observed: 29961.261036
- fractions used: 0.10, 0.20, 0.30, 0.40, 0.50
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.100000 | 2996.126104 | 12 | 8 | 25.000000 | 52 | 0 | 763.970238 | 272.392235 | fragmenta demais |
| 0.200000 | 5992.252207 | 5 | 22 | 60.000000 | 120 | 0 | 1343.843970 | 630.965620 | plausivel |
| 0.300000 | 8988.378311 | 4 | 52 | 75.000000 | 120 | 0 | 1493.898315 | 758.425394 | plausivel |
| 0.400000 | 11984.504414 | 2 | 128 | 150.000000 | 172 | 0 | 3628.445557 | 952.611084 | mistura demais |
| 0.500000 | 14980.630518 | 2 | 128 | 150.000000 | 172 | 0 | 3628.445557 | 952.611084 | mistura demais |

## Ranking (balanced score, not only mean ICV)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 8988.378311 | 2.100000 | 4 | 0 | 1493.898315 | 758.425394 | plausivel |
| 0.200000 | 5992.252207 | 2.150000 | 5 | 0 | 1343.843970 | 630.965620 | plausivel |
| 0.400000 | 11984.504414 | 2.450000 | 2 | 0 | 3628.445557 | 952.611084 | mistura demais |

## Output locations
- root: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_164245`
- runs: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_164245/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_164245/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_164245/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, dendrogram cut, PCA).