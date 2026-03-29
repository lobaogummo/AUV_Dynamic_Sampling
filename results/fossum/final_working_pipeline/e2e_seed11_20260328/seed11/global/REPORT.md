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
- max merge distance observed: 1041.835330
- fractions used: 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 312.550599 | 5 | 20 | 60.000000 | 122 | 0 | 1570.662854 | 549.651514 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 312.550599 | 1.000000 | 5 | 0 | 1570.662854 | 549.651514 | plausivel |

## Output locations
- root: `results/fossum/final_working_pipeline/e2e_seed11_20260328/_tmp/seed11/global_stage_out/w72_h40_xds04_seed11_scalerON_official_sd30_seed11`
- runs: `results/fossum/final_working_pipeline/e2e_seed11_20260328/_tmp/seed11/global_stage_out/w72_h40_xds04_seed11_scalerON_official_sd30_seed11/runs.csv`
- ranking: `results/fossum/final_working_pipeline/e2e_seed11_20260328/_tmp/seed11/global_stage_out/w72_h40_xds04_seed11_scalerON_official_sd30_seed11/ranking.csv`
- dendrogram diagnostics: `results/fossum/final_working_pipeline/e2e_seed11_20260328/_tmp/seed11/global_stage_out/w72_h40_xds04_seed11_scalerON_official_sd30_seed11/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).