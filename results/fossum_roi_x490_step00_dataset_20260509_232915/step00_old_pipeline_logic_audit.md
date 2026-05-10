# Step00 old pipeline logic audit

Generated: 2026-05-09T23:32:47

## Scripts found
- `scripts/Old_Code/01_build_fossum_surface_dataset.py`
- `scripts/Old_Code/01b_export_normalized_surface_pngs.py`
- `scripts/Old_Code/export_surface_2024_300_images.py`
- `scripts/fossum_faithful_initial_utils.py`

## Responsibility by script
- `scripts/Old_Code/01_build_fossum_surface_dataset.py`: builds `X_surface_300.npy`, `X_surface_300_norm.npy`, `mask_common.npy`, `global_stats.json`, and `dataset_summary.json`.
- `scripts/Old_Code/export_surface_2024_300_images.py`: parses the old GSLIB deterministic surface file and builds the raw 300-image stack.
- `scripts/Old_Code/01b_export_normalized_surface_pngs.py`: exports normalized PNGs with a common symmetric scale.
- `scripts/fossum_faithful_initial_utils.py`: downstream Fossum utilities expect `X_surface_300.npy`, `X_surface_300_norm.npy`, `mask_common.npy`, and `global_stats.json`.

## Legacy dataset loading
The old builder read the deterministic 2024 depth-1 GSLIB file, converted it to a float32 stack, and required shape `(300, 64, 112)`.

## Legacy mask
The common mask was computed as `np.isfinite(X).all(axis=0)`, meaning a pixel is valid only if it is finite for every image.

## Legacy normalization
The old builder selected `valid_stack = X[:, mask_common]`, computed `mu_global = np.mean(valid_stack)` and `sigma_global = np.std(valid_stack)`, then wrote normalized values only inside the common mask.

## NaN treatment
NaNs were preserved outside `mask_common`. The normalized cube was initialized with NaNs and only common-valid pixels were filled.

## Legacy PNG export
The normalized PNG exporter loaded `X_surface_300_norm.npy` and `mask_common.npy`, set pixels outside the mask to NaN, and used `coolwarm` with a symmetric scale `[-p98(abs(valid)), +p98(abs(valid))]`.

## Expected old outputs
- `X_surface_300.npy`
- `X_surface_300_norm.npy`
- `mask_common.npy`
- `global_stats.json`
- `dataset_summary.json`
- normalized PNG folder and index/scale files

## Reused without methodological changes
- Common finite mask logic.
- Global mean/std normalization over common-valid pixels.
- Preservation of NaNs outside the common mask.
- Normalized PNG color scale based on p98 absolute normalized values.

## Adapted for the new dataset
- Input path changed to the FRESNEL paper ROI x490 HRes stack.
- Number of images changed from 300 to 370.
- Shape changed from `(300, 64, 112)` to `(370, 72, 117)`.
- Output names and metadata now carry `roi_x490` and 370-day dates.
