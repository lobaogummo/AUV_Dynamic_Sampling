# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL

## Scope
- Dedicated SD auto-probe for faithful pipeline only.
- Historical baseline scripts were not modified.

## Fixed configuration lock
- patch size: (72,40)
- dictionary size: 4
- seed: 83
- include_valid_mask=True
- mask_encoding=concat
- feature_mode=raw
- StandardScaler applied before Ward: True
- ranking target classes: 5
- default provisional SD fraction in this script: 0.30
- dictionary mode: trained
- dictionary artifact path: trained in this run

## Dendrogram-driven SD generation
- max merge distance observed: 890.907092
- fractions used: 0.30
- SD values computed as: `fraction * max_merge_distance`

## Summary table
| sd_fraction_of_max | separation_distance | number_of_classes | min_class_size | mean_class_size | max_class_size | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 267.272127 | 7 | 9 | 42.857143 | 104 | 0 | 1264.266872 | 1112.815047 | plausivel |

## Ranking (balanced score, with target-class proximity)
- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)
| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | std_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300000 | 267.272127 | 1.000000 | 7 | 0 | 1264.266872 | 1112.815047 | plausivel |

## Output locations
- root: `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328/raw_global_runs/seed083/w72_h40_xds04_seed83_scalerON_canonical_probe_seed083`
- runs: `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328/raw_global_runs/seed083/w72_h40_xds04_seed83_scalerON_canonical_probe_seed083/runs.csv`
- ranking: `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328/raw_global_runs/seed083/w72_h40_xds04_seed83_scalerON_canonical_probe_seed083/ranking.csv`
- dendrogram diagnostics: `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328/raw_global_runs/seed083/w72_h40_xds04_seed83_scalerON_canonical_probe_seed083/dendrogram`
- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA).