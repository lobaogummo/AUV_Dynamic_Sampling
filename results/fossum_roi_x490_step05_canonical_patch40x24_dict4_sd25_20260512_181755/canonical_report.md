# Step05 canonical Fossum ROI x490 report

## Logic Audit

- Patch vectors: `build_patch_vectors`, with temperature values plus valid-mask channel concatenated.
- Dictionary: `train_dictionary_ordered_stream`, deterministic image order from seed 11, `MiniBatchDictionaryLearning`, `dictionary_size=4`.
- Sparse coding: OMP through the trained dictionary model, `transform_nnz=2`.
- Feature construction: full raw sparse-code matrix per image flattened into one vector.
- Scaling: `StandardScaler` applied before Ward linkage.
- Clustering: `scipy.cluster.hierarchy.linkage(..., method='ward', metric='euclidean')`.
- Cut: `fcluster(linkage, t=0.25*max_merge_distance, criterion='distance')`.

## Configuration

- Input Step00: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step00_dataset_20260509_232915`
- Output folder: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755`
- Shape: `[370, 72, 117]`
- Dates: `2023-10-28` to `2024-10-31`
- Mask valid cells: `8004` (0.950142)
- Patch: `40x24`
- Dictionary size: `4`
- Seed: `11`
- StandardScaler: `ON`
- SD fraction: `0.25`

## Numeric Artefacts

- patches per image: `3822`
- patch vector length: `1920`
- feature vector length: `15288`
- feature matrix shape: `[370, 15288]`
- sparse codes shape: `[370, 3822, 4]`
- max merge distance: `1916.841076`
- SD cut value: `479.210269`

## Classes

| class_id | n_days | percent_days | icv_sst_space |
| --- | --- | --- | --- |
| 1.000000 | 41.000000 | 11.081081 | 1680.749512 |
| 2.000000 | 70.000000 | 18.918919 | 1474.508423 |
| 3.000000 | 50.000000 | 13.513514 | 1351.871582 |
| 4.000000 | 107.000000 | 28.918919 | 2005.192383 |
| 5.000000 | 30.000000 | 8.108108 | 326.411011 |
| 6.000000 | 72.000000 | 19.459459 | 1129.506592 |

## Warnings

- none

## Interpretation

The canonical run produced the expected six-class structure for the ROI x490 dataset with SD=0.25. This matches the selected Step05 configuration and keeps the pipeline ready for the next legacy stage without introducing STD, TEMPpred or planner integration.
