# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (40,24)
- dictionary size: 4
- seed: 11
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30
- dictionary mode: trained
- dictionary artifact path: trained in this run

## Dendrogram-driven SD generation
- max merge distance observed: 1916.841076
- fractions used: 0.20, 0.25, 0.30, 0.35, 0.40
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 383.368215 | 10 | 11 | 37.000000 | 70 | 0 | 754.779803 | 435.898636 | fragmenta demais |
| 0.250000 | 479.210269 | 6 | 30 | 61.666667 | 107 | 0 | 1328.039917 | 524.028695 | plausivel |
| 0.300000 | 575.052323 | 5 | 30 | 74.000000 | 120 | 0 | 1755.583032 | 1098.961926 | plausivel |
| 0.350000 | 670.894377 | 4 | 41 | 92.500000 | 120 | 0 | 2131.731201 | 913.968574 | plausivel |
| 0.400000 | 766.736431 | 4 | 41 | 92.500000 | 120 | 0 | 2131.731201 | 913.968574 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.250000 | 479.210269 | 1.950000 | 6 | 0 | 1328.039917 | 524.028695 | plausivel |
| 0.300000 | 575.052323 | 2.100000 | 5 | 0 | 1755.583032 | 1098.961926 | plausivel |
| 0.350000 | 670.894377 | 2.250000 | 4 | 0 | 2131.731201 | 913.968574 | plausivel |

## Output locations
- root: `results/fossum_roi_x490_step04_sd_probe_patch40x24_dict4_20260511_211354`
- runs: `results/fossum_roi_x490_step04_sd_probe_patch40x24_dict4_20260511_211354/runs.csv`
- ranking: `results/fossum_roi_x490_step04_sd_probe_patch40x24_dict4_20260511_211354/ranking.csv`
- dendrogram diagnostics: `results/fossum_roi_x490_step04_sd_probe_patch40x24_dict4_20260511_211354/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).