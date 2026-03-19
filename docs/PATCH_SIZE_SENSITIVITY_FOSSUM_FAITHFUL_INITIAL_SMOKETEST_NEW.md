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
- patch sizes: (72,40)
- seeds: 11
- dictionary_size=4
- n_classes=4

## Summary
| patch_w | patch_h | executed_runs | patch_vector_length | feature_vector_length | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 1.000000 | 5760.000000 | 4100.000000 | 1493.898315 | nan | 52.000000 | 190.409346 |

## Top candidates (balanced score)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | nan | 1493.898315 | nan | 52.000000 | 190.409346 |

## Outputs
- runs: `results/fossum/faithful_initial_patch_size_sensitivity_smoketest_new/runs.csv`
- summary: `results/fossum/faithful_initial_patch_size_sensitivity_smoketest_new/summary.csv`
- ranking: `results/fossum/faithful_initial_patch_size_sensitivity_smoketest_new/ranking.csv`
- plots: `results/fossum/faithful_initial_patch_size_sensitivity_smoketest_new/plots`
- class members: `results/fossum/faithful_initial_patch_size_sensitivity_smoketest_new/class_members_wXX_hYY_seedSS`