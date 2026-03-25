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
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30

## Dendrogram-driven SD generation
- max merge distance observed: 1043.700080
- fractions used: 0.20, 0.22, 0.24, 0.26, 0.28, 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 208.740016 | 7 | 20 | 42.857143 | 76 | 0 | 1383.248832 | 433.560988 | plausivel |
| 0.220000 | 229.614018 | 7 | 20 | 42.857143 | 76 | 0 | 1383.248832 | 433.560988 | plausivel |
| 0.240000 | 250.488019 | 6 | 20 | 50.000000 | 76 | 0 | 1457.872599 | 547.175013 | plausivel |
| 0.260000 | 271.362021 | 5 | 20 | 60.000000 | 117 | 0 | 1601.534888 | 492.161215 | plausivel |
| 0.280000 | 292.236023 | 5 | 20 | 60.000000 | 117 | 0 | 1601.534888 | 492.161215 | plausivel |
| 0.300000 | 313.110024 | 5 | 20 | 60.000000 | 117 | 0 | 1601.534888 | 492.161215 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 208.740016 | 1.800000 | 7 | 0 | 1383.248832 | 433.560988 | plausivel |
| 0.220000 | 229.614018 | 1.800000 | 7 | 0 | 1383.248832 | 433.560988 | plausivel |
| 0.260000 | 271.362021 | 2.050000 | 5 | 0 | 1601.534888 | 492.161215 | plausivel |

## Output locations
- root: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed11_scalerON_refined_local_20260325`
- runs: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed11_scalerON_refined_local_20260325/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed11_scalerON_refined_local_20260325/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed11_scalerON_refined_local_20260325/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).