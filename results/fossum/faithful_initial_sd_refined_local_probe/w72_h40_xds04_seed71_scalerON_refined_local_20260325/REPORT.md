# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (72,40)
- dictionary size: 4
- seed: 71
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30

## Dendrogram-driven SD generation
- max merge distance observed: 1139.428966
- fractions used: 0.20, 0.22, 0.24, 0.26, 0.28, 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 227.885793 | 7 | 2 | 42.857143 | 113 | 0 | 1507.432500 | 1365.423099 | fragmenta demais |
| 0.220000 | 250.674372 | 7 | 2 | 42.857143 | 113 | 0 | 1507.432500 | 1365.423099 | fragmenta demais |
| 0.240000 | 273.462952 | 5 | 16 | 60.000000 | 113 | 0 | 1628.379321 | 996.041181 | plausivel |
| 0.260000 | 296.251531 | 4 | 19 | 75.000000 | 113 | 0 | 1701.556976 | 959.445961 | plausivel |
| 0.280000 | 319.040110 | 4 | 19 | 75.000000 | 113 | 0 | 1701.556976 | 959.445961 | plausivel |
| 0.300000 | 341.828690 | 4 | 19 | 75.000000 | 113 | 0 | 1701.556976 | 959.445961 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.260000 | 296.251531 | 2.250000 | 4 | 0 | 1701.556976 | 959.445961 | plausivel |
| 0.280000 | 319.040110 | 2.250000 | 4 | 0 | 1701.556976 | 959.445961 | plausivel |
| 0.300000 | 341.828690 | 2.250000 | 4 | 0 | 1701.556976 | 959.445961 | plausivel |

## Output locations
- root: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed71_scalerON_refined_local_20260325`
- runs: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed71_scalerON_refined_local_20260325/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed71_scalerON_refined_local_20260325/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed71_scalerON_refined_local_20260325/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).