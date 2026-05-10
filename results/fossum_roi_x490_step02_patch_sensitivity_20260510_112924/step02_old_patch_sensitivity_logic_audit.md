# Step02 old patch-size sensitivity logic audit

Generated: 2026-05-10T13:31:58

## 1. Old script
- Reference script: `scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py`
- Utility module: `scripts/fossum_faithful_initial_utils.py`

## 2. Original patch sizes
- 16x16, 24x16, 32x20, 40x24, 48x32, 56x32, 64x36, 72x40, 80x44

## 3. Old dataset
- `results/fossum/X_surface_300.npy` for SST/original-space ICV.
- `results/fossum/X_surface_300_norm.npy` for sparse coding/clustering.
- `results/fossum/mask_common.npy` for valid-mask operations.
- `results/fossum/pngs_normalized_surface_300_thesis` for class-member contact sheets.

## 4. New dataset redirection
- X_sst: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490.npy`
- X_norm: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490_norm.npy`
- mask: `results/fossum_roi_x490_step00_dataset_20260509_232915/mask_common_roi_x490.npy`
- png source compatibility folder: `results/fossum_roi_x490_step02_patch_sensitivity_20260510_112924/legacy_named_normalized_pngs`
- input shape: `[370, 72, 117]`

## 5. Mask use
The legacy loader copies X_sst/X_norm and sets `[:, ~mask] = np.nan` before modelling/evaluation.

## 6. Patch extraction
`extract_patch_components` uses `sliding_window_view`, row-major traversal, no shuffling.

## 7. Patch-valid mask channel
Enabled by default: patch vector is `[patch_temp_filled, patch_valid_mask]` with `mask_encoding='concat'`.

## 8. Feature vector
Each image feature is the full sparse-code sequence flattened in patch order, length `patches_per_image * dictionary_size`.

## 9-12. Fixed parameters
- dictionary_size = 4
- seeds = [11, 23, 37, 53, 71]
- StandardScaler = not used in this legacy 02b patch sensitivity script.
- SD fraction = not used in this legacy 02b patch sensitivity script.
- n_classes = 4
- dict_batch_size = 4096
- transform_nnz = 2
- feature_mode = raw
- include_valid_mask = True
- mask_encoding = concat

## 13. Ward clustering
`AgglomerativeClustering(n_clusters=cfg.n_classes, linkage='ward').fit_predict(features)`.

## 14-17. Outputs/metrics/figures
- `runs.csv`, `summary.csv`, `ranking.csv`.
- class-member contact-sheet folders `class_members_wXX_hYY_seedSS/`.
- plots: ICV boxplot, mean ICV vs patch size, min class size vs patch size, runtime vs patch size.
- metrics: mean/std ICV, per-class ICV, class sizes, min/mean/max class size, runtime, feature lengths.
- ranking: 0.30 rank(mean_icv) + 0.20 rank(mean_icv_std) + 0.20 rank(std_icv_mean) + 0.20 rank(min_class_size_min descending) + 0.10 rank(runtime).

## Skipped patches
- None; all legacy patch sizes are compatible with the ROI x490 shape.
