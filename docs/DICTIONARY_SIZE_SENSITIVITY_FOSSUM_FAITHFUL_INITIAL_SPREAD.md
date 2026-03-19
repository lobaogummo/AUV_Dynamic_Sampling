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
- seeds: 11, 23
- n_classes=4

## Summary
| dictionary_size | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2.000000 | 2.000000 | 5760.000000 | 2050.000000 | 1544.080948 | 0.000000 | 69.000000 | 202.831757 |
| 3.000000 | 2.000000 | 5760.000000 | 3075.000000 | 1955.630363 | 467.116654 | 47.000000 | 240.536874 |
| 4.000000 | 2.000000 | 5760.000000 | 4100.000000 | 1527.657944 | 47.743324 | 52.000000 | 247.506811 |
| 5.000000 | 2.000000 | 5760.000000 | 5125.000000 | 1569.337349 | 62.699308 | 42.000000 | 278.084217 |
| 6.000000 | 2.000000 | 5760.000000 | 6150.000000 | 1855.060829 | 603.005538 | 27.000000 | 287.441116 |
| 7.000000 | 2.000000 | 5760.000000 | 7175.000000 | 1639.837601 | 308.908967 | 30.000000 | 307.976958 |
| 8.000000 | 2.000000 | 5760.000000 | 8200.000000 | 1633.094467 | 40.679636 | 34.000000 | 463.357971 |
| 9.000000 | 2.000000 | 5760.000000 | 9225.000000 | 1632.997017 | 135.454053 | 22.000000 | 376.014355 |
| 10.000000 | 2.000000 | 5760.000000 | 10250.000000 | 1751.630600 | 19.504542 | 20.000000 | 393.644935 |
| 11.000000 | 2.000000 | 5760.000000 | 11275.000000 | 1752.169449 | 10.385911 | 23.000000 | 409.952021 |
| 12.000000 | 2.000000 | 5760.000000 | 12300.000000 | 1788.501938 | 56.635201 | 14.000000 | 621.841259 |

## Top candidates (balanced score)
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 2.000000 | 2.900000 | 1544.080948 | 0.000000 | 69.000000 | 202.831757 |
| 4.000000 | 4.000000 | 1527.657944 | 47.743324 | 52.000000 | 247.506811 |
| 8.000000 | 4.500000 | 1633.094467 | 40.679636 | 34.000000 | 463.357971 |

## Outputs
- runs: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/runs.csv`
- summary: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/summary.csv`
- ranking: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/ranking.csv`
- plots: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/plots`
- class members: `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/class_members_xdsXX_seedSS`