# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (72,40)
- dictionary size: 4
- seed: 53
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30

## Dendrogram-driven SD generation
- max merge distance observed: 1104.201513
- fractions used: 0.20, 0.22, 0.24, 0.26, 0.28, 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 220.840303 | 7 | 5 | 42.857143 | 117 | 0 | 1046.825810 | 486.398531 | plausivel |
| 0.220000 | 242.924333 | 6 | 15 | 50.000000 | 117 | 0 | 1182.848043 | 352.376949 | plausivel |
| 0.240000 | 265.008363 | 6 | 15 | 50.000000 | 117 | 0 | 1182.848043 | 352.376949 | plausivel |
| 0.260000 | 287.092393 | 5 | 30 | 60.000000 | 117 | 0 | 1373.161890 | 317.419899 | plausivel |
| 0.280000 | 309.176424 | 5 | 30 | 60.000000 | 117 | 0 | 1373.161890 | 317.419899 | plausivel |
| 0.300000 | 331.260454 | 5 | 30 | 60.000000 | 117 | 0 | 1373.161890 | 317.419899 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.260000 | 287.092393 | 2.050000 | 5 | 0 | 1373.161890 | 317.419899 | plausivel |
| 0.280000 | 309.176424 | 2.050000 | 5 | 0 | 1373.161890 | 317.419899 | plausivel |
| 0.300000 | 331.260454 | 2.050000 | 5 | 0 | 1373.161890 | 317.419899 | plausivel |

## Output locations
- root: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed53_scalerON_refined_local_20260325`
- runs: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed53_scalerON_refined_local_20260325/runs.csv`
- ranking: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed53_scalerON_refined_local_20260325/ranking.csv`
- dendrogram diagnostics: `results/fossum/faithful_initial_sd_refined_local_probe/w72_h40_xds04_seed53_scalerON_refined_local_20260325/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).