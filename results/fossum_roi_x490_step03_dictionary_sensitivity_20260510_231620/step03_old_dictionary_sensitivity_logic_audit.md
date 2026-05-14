# Step03 old dictionary-size sensitivity logic audit

Generated: 2026-05-11T15:22:23

## 1. Old script
- Reference script: `scripts/03a_dictionary_size_sensitivity_fossum_faithful_initial.py`
- Utility module: `scripts/fossum_faithful_initial_utils.py`

## 2. Original dictionary sizes
- 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12

## 3. Old patch size
- The legacy script default was `72x40`.
- This rerun uses `40x24`, the Step02 recommended patch size, as requested.

## 4. Seeds
- [11, 23, 37, 53, 71]

## 5-7. Old dataset and mask
- `results/fossum/X_surface_300.npy` for SST/original ICV.
- `results/fossum/X_surface_300_norm.npy` for dictionary learning, sparse coding and clustering.
- `results/fossum/mask_common.npy`; legacy loader sets `[:, ~mask] = np.nan`.

## 8-10. Patches, features, valid-mask channel
- Patch extraction uses `sliding_window_view`, deterministic row-major traversal, stride 1.
- Patch vector is `[patch_temp_filled, patch_valid_mask]` with `mask_encoding='concat'`.
- Image feature vector is full sparse-code sequence flattened in patch order: `patches_per_image * dictionary_size`.

## 11-12. StandardScaler / SD fraction
- StandardScaler is not used in legacy 03a.
- SD fraction is not used in legacy 03a.

## 13. Ward clustering
- `AgglomerativeClustering(n_clusters=4, linkage='ward').fit_predict(features)`.

## 14-18. Outputs, metrics, figures, selection
- Outputs: `runs.csv`, `summary.csv`, `ranking.csv`, `plots/`, `class_members_xdsXX_seedSS/`, and markdown doc.
- Metrics: mean/std ICV, per-class ICV, class sizes, min/mean/max class sizes, runtime, feature lengths.
- Figures: ICV boxplot, mean ICV vs dictionary size, min class size vs dictionary size, runtime vs dictionary size.
- Ranking: 0.30 rank(mean_icv) + 0.20 rank(mean_icv_std) + 0.20 rank(std_icv_mean) + 0.20 rank(min_class_size_min descending) + 0.10 rank(runtime).

## New data redirection
- input shape: `[370, 72, 117]`
- X_sst: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490.npy`
- X_norm: `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490_norm.npy`
- mask: `results/fossum_roi_x490_step00_dataset_20260509_232915/mask_common_roi_x490.npy`
- PNG compatibility folder: `results/fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620/legacy_named_normalized_pngs`

## Skipped dictionary sizes
- None.
