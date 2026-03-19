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
- clustering/sparse coding: `results/fossum/X_surface_300_norm.npy`
- ICV: `results/fossum/X_surface_300.npy`
- mask: `results/fossum/mask_common.npy`
- class member PNG source: `results/fossum/pngs_normalized_surface_300_thesis`

## Configuration
- fixed patch size: (72,40)
- dictionary sizes: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
- seeds: 71
- n_classes=4

## Summary
| dictionary_size | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2.000000 | 5.000000 | 5760.000000 | 2050.000000 | 1535.472672 | 19.248691 | 39.000000 | 245.310912 |
| 3.000000 | 5.000000 | 5760.000000 | 3075.000000 | 1753.213892 | 332.792820 | 40.000000 | 1266.478637 |
| 4.000000 | 5.000000 | 5760.000000 | 4100.000000 | 1654.883005 | 327.418451 | 33.000000 | 248.080266 |
| 5.000000 | 5.000000 | 5760.000000 | 5125.000000 | 1782.368542 | 314.616303 | 26.000000 | 284.163410 |
| 6.000000 | 5.000000 | 5760.000000 | 6150.000000 | 1850.613437 | 334.521380 | 16.000000 | 329.385784 |
| 7.000000 | 5.000000 | 5760.000000 | 7175.000000 | 1876.583264 | 463.922922 | 12.000000 | 366.709299 |
| 8.000000 | 5.000000 | 5760.000000 | 8200.000000 | 1646.860138 | 249.202926 | 34.000000 | 567.845477 |
| 9.000000 | 5.000000 | 5760.000000 | 9225.000000 | 1876.638644 | 304.716882 | 11.000000 | 527.084389 |
| 10.000000 | 5.000000 | 5760.000000 | 10250.000000 | 1722.824692 | 202.063859 | 20.000000 | 523.206782 |
| 11.000000 | 5.000000 | 5760.000000 | 11275.000000 | 1741.505490 | 158.606536 | 23.000000 | 497.982445 |
| 12.000000 | 5.000000 | 5760.000000 | 12300.000000 | 1699.849733 | 109.418435 | 14.000000 | 684.358366 |

## Top candidates (balanced score)
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 2.000000 | 2.000000 | 1535.472672 | 19.248691 | 39.000000 | 245.310912 |
| 8.000000 | 3.500000 | 1646.860138 | 249.202926 | 34.000000 | 567.845477 |
| 10.000000 | 4.600000 | 1722.824692 | 202.063859 | 20.000000 | 523.206782 |

## Outputs
- runs: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/runs.csv`
- summary: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/summary.csv`
- ranking: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/ranking.csv`
- plots: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/plots`
- class members: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/class_members_xdsXX_seedSS`