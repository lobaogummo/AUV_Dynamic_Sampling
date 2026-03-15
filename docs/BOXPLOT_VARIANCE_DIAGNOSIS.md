# BOXPLOT_VARIANCE_DIAGNOSIS

## 1) Variance existed or not in original runs?

Source analyzed:
- `results/fossum/patch_size_sensitivity_fossum/runs.csv`

Computed table:
- `results/fossum/patch_size_sensitivity_fossum/debug_variance_table.csv`

Findings (`mean_icv` across seeds 11,23,37,53,71):
- `16x16`: exact same value in all 5 runs, spread `0.0`
- `24x16`: exact same value in all 5 runs, spread `0.0`
- `32x20`: exact same value in all 5 runs, spread `0.0`
- `40x24`: exact same value in all 5 runs, spread `0.0`
- `48x32`: exact same value in all 5 runs, spread `0.0`
- `56x32`: exact same value in all 5 runs, spread `0.0`
- `64x36`: exact same value in all 5 runs, spread `0.0`
- `72x40`: one run differs strongly, absolute spread `594.632751`, relative spread `14.769797%`
- `80x44`: tiny nonzero spread, absolute spread `18.876846`, relative spread `0.287680%`

Conclusion:
- For **7/9 patch sizes**, variance is **true near-zero (numerically zero)**.
- `80x44` has **small but nonzero** variance.
- `72x40` has **meaningful** variance (single-seed divergence).

## 2) Was plot scale hiding variance?

Generated diagnostics:
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/icv_seed_points_by_patchsize.png`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/icv_absolute_spread_vs_patchsize.png`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/icv_relative_spread_vs_patchsize.png`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/fig6a_icv_boxplot_patchsize_zoom.png`

Conclusion:
- The original Fig6a scale can hide **very small** spread (example: `80x44`).
- But for most patch sizes, the spread is exactly zero, so this is **not only a plotting-scale issue**.

## 3) Was the original pipeline effectively deterministic?

Inspected file:
- `scripts/02a_patch_size_sensitivity_fossum.py`

Code-path diagnosis:
- Dictionary learning receives `random_state=seed`, but training is done via:
  - deterministic image loop `for i in range(X.shape[0])`
  - deterministic patch extraction (`sliding_window_view`, fixed order)
  - `partial_fit(...)` called with the same batches in the same order each run
- No explicit seed-dependent permutation of:
  - image order
  - patch order within each image
- Clustering uses `AgglomerativeClustering(linkage="ward")`, which is deterministic for fixed features.

Conclusion:
- The pipeline is **effectively deterministic for most patch sizes**.
- Seed influence is weak or null in the practical execution path.

## 4) Code-level likely cause

Most likely cause:
- `seed` is passed to dictionary learning, but the training data stream is almost identical across runs (same deterministic batch order through repeated `partial_fit` calls), so runs collapse to the same solution for most patch sizes.
- Downstream (`encode` + Ward clustering + ICV calculation) is deterministic once features are fixed.

## 5) Fix applied

Created corrected script:
- `scripts/02a_patch_size_sensitivity_fossum_debugfixed.py`

Key fix:
- enforce **seed-dependent training order** in dictionary learning:
  - randomized image order per seed
  - randomized patch order per image per seed
- keep method Fossum-faithful:
  - `xds=4`
  - all patches, stride=1
  - Ward initial clustering
  - ICV computed in image/temperature space

## 6) Finalist rerun results (if performed)

Target finalist set:
- `(32,20)`, `(48,32)`, `(64,36)` with seeds `11,23,37,53,71`

Execution attempt:
- `python scripts/02a_patch_size_sensitivity_fossum_debugfixed.py`
- Blocked by environment dependency:
  - `RuntimeError: scikit-learn is required ... No module named 'sklearn'`

Because rerun could not execute in this environment:
- `results/fossum/patch_size_sensitivity_fossum_debugfixed/runs_finalists.csv`
- `results/fossum/patch_size_sensitivity_fossum_debugfixed/summary_finalists.csv`
- `results/fossum/patch_size_sensitivity_fossum_debugfixed/plots/*.png`
were generated as **baseline from existing original runs** and explicitly marked:
- `execution_status=baseline_from_original_runs__debugfixed_rerun_not_executed`

## 7) Did patch-size ranking change after fix?

- **Not verifiable yet** in this environment, because debugfixed rerun was blocked by missing `scikit-learn`.
- Baseline (original-run finalists) ranking by `mean_icv_mean` remains:
  1. `48x32`
  2. `32x20`
  3. `64x36`

## Files created in this diagnosis task

Diagnostics from existing runs:
- `results/fossum/patch_size_sensitivity_fossum/debug_variance_table.csv`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/icv_seed_points_by_patchsize.png`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/icv_absolute_spread_vs_patchsize.png`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/icv_relative_spread_vs_patchsize.png`
- `results/fossum/patch_size_sensitivity_fossum/debug_plots/fig6a_icv_boxplot_patchsize_zoom.png`

Debugfixed deliverables:
- `scripts/02a_patch_size_sensitivity_fossum_debugfixed.py`
- `results/fossum/patch_size_sensitivity_fossum_debugfixed/runs_finalists.csv`
- `results/fossum/patch_size_sensitivity_fossum_debugfixed/summary_finalists.csv`
- `results/fossum/patch_size_sensitivity_fossum_debugfixed/plots/*.png`
