# DICTIONARY_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL

## Scope
- This is a new faithful-initial pipeline, separate from baseline historical scripts.
- Only initial classification is included in this phase.

## Faithful initial changes
- patch vector uses `[patch_temp_filled, patch_valid_mask]` (mask_encoding=concat)
- include_valid_mask=True
- patch extraction order is deterministic (left-to-right, top-to-bottom)
- patch order is never shuffled; patch traversal stays left-to-right then top-to-bottom
- image order is deterministic per-seed (non-random permutation) to create controlled ICV spread
- MiniBatchDictionaryLearning uses `shuffle=False`
- feature per image is the full sparse-code sequence (no mean/std reduction)
- feature_mode=raw

## Feature vector definition
- Let `P = patches_per_image` and `K = dictionary_size`.
- Sparse codes per image: shape `(P, K)`.
- Final image feature vector: flatten sparse codes in patch order -> length `P * K`.

## Inputs
- clustering/sparse coding: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490_norm.npy`
- ICV: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490.npy`
- mask: `results/fossum_roi_x490_step00_dataset_20260509_232915/mask_common_roi_x490.npy`
- class member PNG source: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/legacy_named_normalized_pngs`

## Configuration
- fixed patch size: (40,24)
- dictionary sizes: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
- seeds: 11, 23, 37, 53, 71
- n_classes=4

## Summary
| dictionary_size | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2.000000 | 5.000000 | 1920.000000 | 7644.000000 | 1478.119385 | 0.000000 | 51.000000 | 520.964112 |
| 3.000000 | 5.000000 | 1920.000000 | 11466.000000 | 1702.373557 | 171.606681 | 37.000000 | 622.158150 |
| 4.000000 | 5.000000 | 1920.000000 | 15288.000000 | 1582.255634 | 79.304146 | 48.000000 | 746.104454 |
| 5.000000 | 5.000000 | 1920.000000 | 19110.000000 | 1754.912204 | 222.534194 | 34.000000 | 872.337988 |
| 6.000000 | 5.000000 | 1920.000000 | 22932.000000 | 1744.924863 | 184.964380 | 12.000000 | 1063.506113 |
| 7.000000 | 5.000000 | 1920.000000 | 26754.000000 | 1720.352585 | 191.761454 | 13.000000 | 1232.816007 |
| 8.000000 | 5.000000 | 1920.000000 | 30576.000000 | 1838.930405 | 97.201538 | 12.000000 | 1395.091554 |
| 9.000000 | 5.000000 | 1920.000000 | 34398.000000 | 1797.032028 | 97.653735 | 36.000000 | 1598.314560 |
| 10.000000 | 5.000000 | 1920.000000 | 38220.000000 | 1758.591193 | 127.270367 | 40.000000 | 1809.841195 |
| 11.000000 | 5.000000 | 1920.000000 | 42042.000000 | 1882.648674 | 192.339399 | 15.000000 | 1946.302047 |
| 12.000000 | 5.000000 | 1920.000000 | 45864.000000 | 2069.226958 | 789.447320 | 40.000000 | 1600.537665 |

## Top candidates (balanced score)
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 2.000000 | 1.000000 | 1478.119385 | 0.000000 | 51.000000 | 520.964112 |
| 4.000000 | 2.700000 | 1582.255634 | 79.304146 | 48.000000 | 746.104454 |
| 3.000000 | 4.500000 | 1702.373557 | 171.606681 | 37.000000 | 622.158150 |

## Outputs
- runs: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/runs.csv`
- summary: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/summary.csv`
- ranking: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/ranking.csv`
- plots: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/plots`
- class members: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/class_members_xdsXX_seedSS`