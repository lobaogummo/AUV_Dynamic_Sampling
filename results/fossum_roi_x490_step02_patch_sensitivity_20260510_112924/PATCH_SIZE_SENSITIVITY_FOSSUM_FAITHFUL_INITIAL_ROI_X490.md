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
- clustering/sparse coding: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490_norm.npy`
- ICV: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490.npy`
- mask: `results/fossum_roi_x490_step00_dataset_20260509_232915/mask_common_roi_x490.npy`
- class member PNG source: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/legacy_named_normalized_pngs`

## Configuration
- patch sizes: (16,16), (24,16), (32,20), (40,24), (48,32), (56,32), (64,36), (72,40), (80,44)
- seeds: 11, 23, 37, 53, 71
- dictionary_size=4
- n_classes=4

## Summary
| patch_w | patch_h | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16.000000 | 16.000000 | 5.000000 | 512.000000 | 23256.000000 | 1806.499382 | 127.992506 | 24.000000 | 916.656339 |
| 24.000000 | 16.000000 | 5.000000 | 768.000000 | 21432.000000 | 1776.008327 | 239.700988 | 28.000000 | 776.407458 |
| 32.000000 | 20.000000 | 5.000000 | 1280.000000 | 18232.000000 | 1685.300314 | 238.902672 | 47.000000 | 716.186585 |
| 40.000000 | 24.000000 | 5.000000 | 1920.000000 | 15288.000000 | 1582.255634 | 79.304146 | 48.000000 | 737.447519 |
| 48.000000 | 32.000000 | 5.000000 | 3072.000000 | 11480.000000 | 1611.915045 | 85.441922 | 49.000000 | 727.715166 |
| 56.000000 | 32.000000 | 5.000000 | 3584.000000 | 10168.000000 | 1828.502109 | 223.948272 | 54.000000 | 692.651391 |
| 64.000000 | 36.000000 | 5.000000 | 4608.000000 | 7992.000000 | 1894.286987 | 151.848092 | 18.000000 | 598.425036 |
| 72.000000 | 40.000000 | 5.000000 | 5760.000000 | 6072.000000 | 1776.092804 | 193.049479 | 13.000000 | 448.217818 |
| 80.000000 | 44.000000 | 5.000000 | 7040.000000 | 4408.000000 | 2046.271729 | 249.443914 | 40.000000 | 412.666017 |

## Top candidates (balanced score)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 40.000000 | 24.000000 | 2.600000 | 1582.255634 | 79.304146 | 48.000000 | 737.447519 |
| 48.000000 | 32.000000 | 3.000000 | 1611.915045 | 85.441922 | 49.000000 | 727.715166 |
| 32.000000 | 20.000000 | 3.800000 | 1685.300314 | 238.902672 | 47.000000 | 716.186585 |

## Outputs
- runs: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/runs.csv`
- summary: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/summary.csv`
- ranking: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/ranking.csv`
- plots: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/plots`
- class members: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/class_members_wXX_hYY_seedSS`