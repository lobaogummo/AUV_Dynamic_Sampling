# PATCH_SIZE_SENSITIVITY_FOSSUM

## Scope
- Stage purpose: select best patch size `xpa` only.
- Dictionary size fixed: `xds = 4`.
- Initial clustering target: `4` classes (Ward linkage).
- Patch extraction: stride = 1, all possible patches.

## Inputs
- `results/fossum/X_surface_300_norm.npy`
- `results/fossum/mask_common.npy`
- `results/fossum/global_stats.json`
- Image shape from inputs: `45 run rows`, source n_images=`300`

## What Was Tested
- Patch sizes (w,h): (16,16), (24,16), (32,20), (40,24), (48,32), (56,32), (64,36), (72,40), (80,44)
- Seeds used per patch size: 11, 23, 37, 53, 71
- ICV definition (Fossum image-space): for each class, pixelwise variance across images, summed over valid mask.

## Summary Table
| patch_w | patch_h | executed_runs | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16.000000 | 16.000000 | 5.000000 | 9109.012970 | 0.000000 | 5075.799968 | 26.000000 | 341.743548 |
| 24.000000 | 16.000000 | 5.000000 | 6034.187027 | 0.000000 | 5988.781158 | 18.000000 | 311.266758 |
| 32.000000 | 20.000000 | 5.000000 | 3664.479691 | 0.000000 | 3488.230142 | 35.000000 | 278.731123 |
| 40.000000 | 24.000000 | 5.000000 | 5636.534637 | 0.000000 | 5599.239776 | 32.000000 | 243.989080 |
| 48.000000 | 32.000000 | 5.000000 | 3647.115730 | 0.000000 | 5044.095513 | 16.000000 | 221.360647 |
| 56.000000 | 32.000000 | 5.000000 | 5392.134201 | 0.000000 | 6430.977250 | 19.000000 | 224.627505 |
| 64.000000 | 36.000000 | 5.000000 | 3989.765015 | 0.000000 | 4989.648414 | 33.000000 | 193.089732 |
| 72.000000 | 40.000000 | 5.000000 | 4026.004816 | 265.927851 | 4026.084663 | 21.000000 | 156.018693 |
| 80.000000 | 44.000000 | 5.000000 | 6561.744897 | 8.441982 | 5391.557308 | 54.000000 | 99.783827 |

## Candidate Ranking (Balanced)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32.000000 | 20.000000 | 2.100000 | 3664.479691 | 0.000000 | 3488.230142 | 35.000000 | 278.731123 |
| 64.000000 | 36.000000 | 2.600000 | 3989.765015 | 0.000000 | 4989.648414 | 33.000000 | 193.089732 |
| 48.000000 | 32.000000 | 3.500000 | 3647.115730 | 0.000000 | 5044.095513 | 16.000000 | 221.360647 |

## Why Top Candidates
- Low mean ICV across runs.
- Low run-to-run ICV spread (stability).
- Better minimum class sizes (avoid degenerate tiny classes).
- Reasonable runtime.
- Visual inspection enabled by:
  - `results/fossum/patch_size_sensitivity_fossum/prototypes_wXX_hYY_seedSS/`
  - `results/fossum/patch_size_sensitivity_fossum/class_members_wXX_hYY_seedSS/`

## Rejected Patch Sizes
| patch_w | patch_h | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 4026.004816 | 265.927851 | 21.000000 | 156.018693 |
| 40.000000 | 24.000000 | 5636.534637 | 0.000000 | 32.000000 | 243.989080 |
| 56.000000 | 32.000000 | 5392.134201 | 0.000000 | 19.000000 | 224.627505 |
| 80.000000 | 44.000000 | 6561.744897 | 8.441982 | 54.000000 | 99.783827 |
| 16.000000 | 16.000000 | 9109.012970 | 0.000000 | 26.000000 | 341.743548 |
| 24.000000 | 16.000000 | 6034.187027 | 0.000000 | 18.000000 | 311.266758 |

## Key Outputs
- Runs: `results/fossum/patch_size_sensitivity_fossum/runs.csv`
- Summary: `results/fossum/patch_size_sensitivity_fossum/summary.csv`
- Fig 6a boxplot: `results/fossum/patch_size_sensitivity_fossum/plots/fig6a_icv_boxplot_patchsize.png`
