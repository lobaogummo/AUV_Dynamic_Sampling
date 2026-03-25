# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (72,40)
- dictionary size: 4
- seed: 37
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30

## Dendrogram-driven SD generation
- max merge distance observed: 995.990538
- fractions used: 0.20, 0.22, 0.24, 0.26, 0.28, 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 199.198108 | 11 | 6 | 27.272727 | 115 | 0 | 856.857572 | 388.322553 | fragmenta demais |
| 0.220000 | 219.117918 | 9 | 6 | 33.333333 | 140 | 0 | 964.726034 | 538.012597 | fragmenta demais |
| 0.240000 | 239.037729 | 7 | 14 | 42.857143 | 140 | 0 | 1272.432556 | 667.403013 | plausivel |
| 0.260000 | 258.957540 | 6 | 14 | 50.000000 | 154 | 0 | 1481.916534 | 675.161214 | plausivel |
| 0.280000 | 278.877351 | 6 | 14 | 50.000000 | 154 | 0 | 1481.916534 | 675.161214 | plausivel |
| 0.300000 | 298.797162 | 6 | 14 | 50.000000 | 154 | 0 | 1481.916534 | 675.161214 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.260000 | 258.957540 | 2.050000 | 6 | 0 | 1481.916534 | 675.161214 | plausivel |
| 0.280000 | 278.877351 | 2.050000 | 6 | 0 | 1481.916534 | 675.161214 | plausivel |
| 0.300000 | 298.797162 | 2.050000 | 6 | 0 | 1481.916534 | 675.161214 | plausivel |

## Output locations
- root: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed37_scalerON_refined_local_20260325`
- runs: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed37_scalerON_refined_local_20260325/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed37_scalerON_refined_local_20260325/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed37_scalerON_refined_local_20260325/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).