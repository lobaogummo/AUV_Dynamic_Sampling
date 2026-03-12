# PATCH_SIZE_SELECTION_REPORT

## 1) What Was Tested
- Dataset: `results/fossum/X_surface_300_norm.npy` + `results/fossum/mask_common.npy`
- Image shape: `(300, 64, 112)`
- Tested patch sizes (w, h): (16,16), (24,16), (32,20), (40,24), (48,32), (56,32), (64,36), (72,40), (80,44)

## 2) Fixed Parameters Used
- dictionary_size: 4
- n_initial_classes: 4
- patch_stride: 1
- dictionary_learning: MiniBatchDictionaryLearning (partial_fit on all patches)
- encoding: per-image mean|std of absolute sparse codes
- clustering: AgglomerativeClustering(linkage='ward')
- random_state: 42
- transform_algorithm: omp
- transform_n_nonzero_coefs: 2

## 3) Table of Results
| patch_w | patch_h | patches_per_image | total_patches | patch_vector_length | mean_icv | std_icv | number_of_classes | min_class_size | mean_class_size | max_class_size | runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16.000000 | 16.000000 | 4753.000000 | 1425900.000000 | 256.000000 | 8.602156 | 3.569064 | 4.000000 | 26.000000 | 75.000000 | 149.000000 | 323.155553 |
| 24.000000 | 16.000000 | 4361.000000 | 1308300.000000 | 384.000000 | 21.730946 | 7.590001 | 4.000000 | 18.000000 | 75.000000 | 152.000000 | 297.798437 |
| 32.000000 | 20.000000 | 3645.000000 | 1093500.000000 | 640.000000 | 50.636641 | 31.376619 | 4.000000 | 35.000000 | 75.000000 | 99.000000 | 279.132631 |
| 40.000000 | 24.000000 | 2993.000000 | 897900.000000 | 960.000000 | 108.844195 | 81.283811 | 4.000000 | 32.000000 | 75.000000 | 132.000000 | 265.505552 |
| 48.000000 | 32.000000 | 2145.000000 | 643500.000000 | 1536.000000 | 170.751777 | 54.154645 | 4.000000 | 18.000000 | 75.000000 | 105.000000 | 218.180377 |
| 56.000000 | 32.000000 | 1881.000000 | 564300.000000 | 1792.000000 | 257.310622 | 102.345137 | 4.000000 | 19.000000 | 75.000000 | 168.000000 | 225.043969 |
| 64.000000 | 36.000000 | 1421.000000 | 426300.000000 | 2304.000000 | 363.937089 | 189.181134 | 4.000000 | 33.000000 | 75.000000 | 108.000000 | 177.818095 |
| 72.000000 | 40.000000 | 1025.000000 | 307500.000000 | 2880.000000 | 172.622132 | 67.888526 | 4.000000 | 21.000000 | 75.000000 | 134.000000 | 127.103046 |
| 80.000000 | 44.000000 | 693.000000 | 207900.000000 | 3520.000000 | 227.244487 | 80.584646 | 4.000000 | 54.000000 | 75.000000 | 89.000000 | 90.518005 |

## 4) Selection Criteria
- Lower `mean_icv` is better.
- Lower `std_icv` is better.
- Avoid tiny classes (`min_class_size` too low).
- Prefer visually interpretable prototypes (checked from prototype panels).
- Keep runtime reasonable.
- Final ranking uses a balanced score across these metrics (not a single metric).

## 5) Best Patch-Size Candidate(s)
Top candidate labels: 32x20, 16x16, 80x44

| patch_w | patch_h | mean_icv | std_icv | min_class_size | mean_class_size | runtime_seconds | score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32.000000 | 20.000000 | 50.636641 | 31.376619 | 35.000000 | 75.000000 | 279.132631 | 3.300000 |
| 16.000000 | 16.000000 | 8.602156 | 3.569064 | 26.000000 | 75.000000 | 323.155553 | 3.400000 |
| 80.000000 | 44.000000 | 227.244487 | 80.584646 | 54.000000 | 75.000000 | 90.518005 | 4.100000 |

Prototype interpretability proxy (`spatial_std_mean`) by patch size:
- `16x16` spatial_std_mean=0.205660
- `24x16` spatial_std_mean=0.264877
- `32x20` spatial_std_mean=0.244359
- `40x24` spatial_std_mean=0.271852
- `48x32` spatial_std_mean=0.297656
- `56x32` spatial_std_mean=0.311018
- `64x36` spatial_std_mean=0.280581
- `72x40` spatial_std_mean=0.225513
- `80x44` spatial_std_mean=0.224261

## 6) Why Those Candidates Were Selected
- They jointly achieved low `mean_icv`, low-to-moderate `std_icv`, and healthier minimum class sizes.
- Runtime remained competitive versus larger patch sizes.
- Prototype panels are visually structured and less degenerate for these candidates.

## 7) Rejected Patch Sizes and Why
| patch_w | patch_h | mean_icv | std_icv | min_class_size | runtime_seconds | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 24 | 16 | 21.730946 | 7.590001 | 18 | 297.798437 | tiny class detected; high runtime |
| 40 | 24 | 108.844195 | 81.283811 | 32 | 265.505552 | high ICV dispersion |
| 72 | 40 | 172.622132 | 67.888526 | 21 | 127.103046 | tiny class detected; mean ICV above median |
| 48 | 32 | 170.751777 | 54.154645 | 18 | 218.180377 | tiny class detected |
| 64 | 36 | 363.937089 | 189.181134 | 33 | 177.818095 | mean ICV above median; high ICV dispersion |
| 56 | 32 | 257.310622 | 102.345137 | 19 | 225.043969 | tiny class detected; mean ICV above median |

## Output Paths
- Comparison CSV: `results/fossum/patch_selection/patch_size_comparison.csv`
- Plots: `results/fossum/patch_selection/plots/`
- Prototypes: `results/fossum/patch_selection/prototypes_wXX_hYY/`
