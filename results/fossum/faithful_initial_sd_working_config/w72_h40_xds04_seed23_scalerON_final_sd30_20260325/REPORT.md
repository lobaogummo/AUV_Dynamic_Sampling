# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (72,40)
- dictionary size: 4
- seed: 23
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30

## Dendrogram-driven SD generation
- max merge distance observed: 1025.473228
- fractions used: 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 307.641968 | 5 | 26 | 60.000000 | 125 | 0 | 2018.333459 | 1198.176327 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 307.641968 | 1.000000 | 5 | 0 | 2018.333459 | 1198.176327 | plausivel |

## Output locations
- root: `results/fossum/faithful_initial_sd_working_config/w72_h40_xds04_seed23_scalerON_final_sd30_20260325`
- runs: `results/fossum/faithful_initial_sd_working_config/w72_h40_xds04_seed23_scalerON_final_sd30_20260325/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_working_config/w72_h40_xds04_seed23_scalerON_final_sd30_20260325/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_working_config/w72_h40_xds04_seed23_scalerON_final_sd30_20260325/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).