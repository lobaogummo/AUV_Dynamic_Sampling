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
- seeds: 11, 23
- dictionary_size=4
- n_classes=4

## Summary
| patch_w | patch_h | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16.000000 | 16.000000 | 2.000000 | 512.000000 | 19012.000000 | 1564.447220 | 219.897887 | 55.000000 | 584.246341 |
| 24.000000 | 16.000000 | 2.000000 | 768.000000 | 17444.000000 | 1437.793877 | 47.213782 | 51.000000 | 518.776950 |
| 32.000000 | 20.000000 | 2.000000 | 1280.000000 | 14580.000000 | 1632.349373 | 199.356692 | 36.000000 | 426.174425 |
| 40.000000 | 24.000000 | 2.000000 | 1920.000000 | 11972.000000 | 1831.032043 | 58.282836 | 45.000000 | 582.773432 |
| 48.000000 | 32.000000 | 2.000000 | 3072.000000 | 8580.000000 | 1528.960403 | 6.013299 | 46.000000 | 418.476784 |
| 56.000000 | 32.000000 | 2.000000 | 3584.000000 | 7524.000000 | 1556.671516 | 38.739765 | 40.000000 | 385.983273 |
| 64.000000 | 36.000000 | 2.000000 | 4608.000000 | 5684.000000 | 1585.583267 | 298.238167 | 29.000000 | 342.812059 |
| 72.000000 | 40.000000 | 2.000000 | 5760.000000 | 4100.000000 | 1527.657944 | 47.743324 | 52.000000 | 394.482534 |
| 80.000000 | 44.000000 | 2.000000 | 7040.000000 | 2772.000000 | 1952.533699 | 72.372955 | 40.000000 | 235.138908 |

## Top candidates (balanced score)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 48.000000 | 32.000000 | 3.000000 | 1528.960403 | 6.013299 | 46.000000 | 418.476784 |
| 24.000000 | 16.000000 | 3.000000 | 1437.793877 | 47.213782 | 51.000000 | 518.776950 |
| 72.000000 | 40.000000 | 3.600000 | 1527.657944 | 47.743324 | 52.000000 | 394.482534 |

## Outputs
- runs: `results/fossum/faithful_initial_patch_size_sensitivity_spread/runs.csv`
- summary: `results/fossum/faithful_initial_patch_size_sensitivity_spread/summary.csv`
- ranking: `results/fossum/faithful_initial_patch_size_sensitivity_spread/ranking.csv`
- plots: `results/fossum/faithful_initial_patch_size_sensitivity_spread/plots`
- class members: `results/fossum/faithful_initial_patch_size_sensitivity_spread/class_members_wXX_hYY_seedSS`