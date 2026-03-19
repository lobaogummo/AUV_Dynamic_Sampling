# PATCH_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL

## Scope
- This is a new faithful-initial pipeline, separate from baseline historical scripts.
- Only initial classification is included in this phase.

## Faithful initial changes
- patch vector uses `[patch_temp_filled, patch_valid_mask]` (mask_encoding=concat)
- include_valid_mask=True
- patch extraction order is deterministic (left-to-right, top-to-bottom)
- no patch-order shuffle and no image-order shuffle during dictionary training
- MiniBatchDictionaryLearning uses `shuffle=False`; variability comes from `random_state=seed`
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

## Configuration
- patch sizes: (24,16), (40,24), (56,32), (72,40)
- seeds: 11, 23
- dictionary_size=4
- n_classes=4

## Summary
| patch_w | patch_h | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24.000000 | 16.000000 | 2.000000 | 768.000000 | 17444.000000 | 1454.044693 | 0.000000 | 32.000000 | 364.347695 |
| 40.000000 | 24.000000 | 2.000000 | 1920.000000 | 11972.000000 | 1422.306580 | 0.000000 | 26.000000 | 307.410751 |
| 56.000000 | 32.000000 | 2.000000 | 3584.000000 | 7524.000000 | 1932.643707 | 0.000000 | 30.000000 | 265.229921 |
| 72.000000 | 40.000000 | 2.000000 | 5760.000000 | 4100.000000 | 1643.332092 | 0.000000 | 46.000000 | 159.875644 |

## Top candidates (balanced score)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 1.600000 | 1643.332092 | 0.000000 | 46.000000 | 159.875644 |
| 40.000000 | 24.000000 | 2.200000 | 1422.306580 | 0.000000 | 26.000000 | 307.410751 |
| 24.000000 | 16.000000 | 2.400000 | 1454.044693 | 0.000000 | 32.000000 | 364.347695 |

## Outputs
- runs: `results/fossum/faithful_initial_patch_size_sensitivity/runs.csv`
- summary: `results/fossum/faithful_initial_patch_size_sensitivity/summary.csv`
- ranking: `results/fossum/faithful_initial_patch_size_sensitivity/ranking.csv`
- plots: `results/fossum/faithful_initial_patch_size_sensitivity/plots`