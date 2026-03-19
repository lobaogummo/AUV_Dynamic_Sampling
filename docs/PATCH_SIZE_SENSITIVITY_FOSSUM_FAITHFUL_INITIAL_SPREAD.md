# PATCH_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL

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
- patch sizes: (16,16), (24,16), (32,20), (40,24), (48,32), (56,32), (64,36), (72,40), (80,44)
- seeds: 71
- dictionary_size=4
- n_classes=4

## Summary
| patch_w | patch_h | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16.000000 | 16.000000 | 5.000000 | 512.000000 | 19012.000000 | 1625.317644 | 126.759199 | 24.000000 | 1641.151836 |
| 24.000000 | 16.000000 | 5.000000 | 768.000000 | 17444.000000 | 1550.318430 | 224.175096 | 16.000000 | 535.664851 |
| 32.000000 | 20.000000 | 5.000000 | 1280.000000 | 14580.000000 | 1666.103949 | 151.827345 | 14.000000 | 564.018552 |
| 40.000000 | 24.000000 | 5.000000 | 1920.000000 | 11972.000000 | 1837.325064 | 117.901964 | 22.000000 | 783.650481 |
| 48.000000 | 32.000000 | 5.000000 | 3072.000000 | 8580.000000 | 1657.146899 | 124.190053 | 21.000000 | 575.469528 |
| 56.000000 | 32.000000 | 5.000000 | 3584.000000 | 7524.000000 | 1622.910419 | 123.091939 | 25.000000 | 474.132275 |
| 64.000000 | 36.000000 | 5.000000 | 4608.000000 | 5684.000000 | 1685.314520 | 340.347063 | 28.000000 | 385.039634 |
| 72.000000 | 40.000000 | 5.000000 | 5760.000000 | 4100.000000 | 1654.883005 | 327.418451 | 33.000000 | 431.454091 |
| 80.000000 | 44.000000 | 5.000000 | 7040.000000 | 2772.000000 | 1761.140717 | 197.997462 | 14.000000 | 224.998481 |

## Top candidates (balanced score)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 56.000000 | 32.000000 | 2.800000 | 1622.910419 | 123.091939 | 25.000000 | 474.132275 |
| 16.000000 | 16.000000 | 4.400000 | 1625.317644 | 126.759199 | 24.000000 | 1641.151836 |
| 48.000000 | 32.000000 | 4.400000 | 1657.146899 | 124.190053 | 21.000000 | 575.469528 |

## Outputs
- runs: `results/fossum/faithful_initial_patch_size_sensitivity_spread/runs.csv`
- summary: `results/fossum/faithful_initial_patch_size_sensitivity_spread/summary.csv`
- ranking: `results/fossum/faithful_initial_patch_size_sensitivity_spread/ranking.csv`
- plots: `results/fossum/faithful_initial_patch_size_sensitivity_spread/plots`
- class members: `results/fossum/faithful_initial_patch_size_sensitivity_spread/class_members_wXX_hYY_seedSS`