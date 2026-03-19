# DICTIONARY_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL

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
- fixed patch size: (72,40)
- dictionary sizes: 2, 4, 6, 8, 10
- seeds: 11, 23
- n_classes=4

## Summary
| dictionary_size | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2.000000 | 2.000000 | 5760.000000 | 2050.000000 | 1544.080948 | 0.000000 | 69.000000 | 108.633048 |
| 4.000000 | 2.000000 | 5760.000000 | 4100.000000 | 1643.332092 | 0.000000 | 46.000000 | 159.154427 |
| 6.000000 | 2.000000 | 5760.000000 | 6150.000000 | 1554.660347 | 0.000000 | 22.000000 | 177.729563 |
| 8.000000 | 2.000000 | 5760.000000 | 8200.000000 | 1833.577171 | 13.488480 | 30.000000 | 202.009418 |
| 10.000000 | 2.000000 | 5760.000000 | 10250.000000 | 1463.693382 | 38.104937 | 28.000000 | 207.766110 |

## Top candidates (balanced score)
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 2.000000 | 1.700000 | 1544.080948 | 0.000000 | 69.000000 | 108.633048 |
| 4.000000 | 2.200000 | 1643.332092 | 0.000000 | 46.000000 | 159.154427 |
| 10.000000 | 3.000000 | 1463.693382 | 38.104937 | 28.000000 | 207.766110 |

## Outputs
- runs: `results/fossum/faithful_initial_dictionary_size_sensitivity/runs.csv`
- summary: `results/fossum/faithful_initial_dictionary_size_sensitivity/summary.csv`
- ranking: `results/fossum/faithful_initial_dictionary_size_sensitivity/ranking.csv`
- plots: `results/fossum/faithful_initial_dictionary_size_sensitivity/plots`