# Notebook-faithful CV audit

This audit supersedes the broader Step07-CV attempt.

## Source reviewed

- `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\notebooks\seed11_computer_vision_colab.ipynb`
- `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\notebooks\seed11_computer_vision_colab.localrun.ipynb`

## What the old notebook actually did

1. Loaded exported seed11 prototypes as `.npy` plus `_mask.npy`.
2. Used `_clean.png` only for the image-only branch.
3. Validated `arr.shape == mask.shape`.
4. Used fixed visualization scale `vmin=-2.025433`, `vmax=2.025433`, `coolwarm`.
5. Split arrays into left/right/top/bottom and quadrants.
6. Exported basic features: mean, std, mean_left, mean_right, mean_top, mean_bottom, contrast_lr, contrast_tb.
7. Ran a conservative `simple` analysis over arrays with gaussian smoothing sigma=1, Otsu/mean threshold, region metrics, gradient p90 and rule-based labels.
8. Ran an `image-only` analysis over clean PNGs with alpha mask, score `R-B`, Otsu/mean threshold, region metrics, gradient p90 and rule-based labels.
9. Kept HSL exploration optional and explicitly outside the final CSV exports.

## What was removed relative to the previous Step07-CV attempt

- No heterogeneity ranking invented outside the notebook.
- No member-to-prototype residual outlier analysis.
- No KMeans substructure diagnostics.
- No descriptor-ready composite scores.
- No planner-facing recommendation beyond notebook labels/features.

## Adaptation to ROI x490

The canonical Step05 prototypes were exported into notebook-style inputs:
`notebook_style_exports/global/prototype_class_XX.npy`,
`prototype_class_XX_mask.npy`, and `prototype_class_XX_clean.png`.

The local `class_02` branch is empty because the current canonical run has no
local class_02 prototype stage.
