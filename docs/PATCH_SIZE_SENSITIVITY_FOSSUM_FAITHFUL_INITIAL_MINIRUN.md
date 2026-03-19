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
- patch sizes: (40,24)
- seeds: 11
- dictionary_size=4
- n_classes=4

## Summary
| patch_w | patch_h | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40.000000 | 24.000000 | 1.000000 | 1920.000000 | 11972.000000 | 1422.306580 | nan | 26.000000 | 363.023025 |

## Top candidates (balanced score)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 40.000000 | 24.000000 | nan | 1422.306580 | nan | 26.000000 | 363.023025 |

## Outputs
- runs: `results/fossum/faithful_initial_patch_size_sensitivity_minirun/runs.csv`
- summary: `results/fossum/faithful_initial_patch_size_sensitivity_minirun/summary.csv`
- ranking: `results/fossum/faithful_initial_patch_size_sensitivity_minirun/ranking.csv`
- plots: `results/fossum/faithful_initial_patch_size_sensitivity_minirun/plots`