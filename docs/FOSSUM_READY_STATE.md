# FOSSUM Ready State

## Dataset source
- Source file used for the 300 surface maps:
  - `data/2024/tempIBHRes2024_1.gslib`
- Confirmed in:
  - `results/plots/deterministic_2024_surface_300/color_scale.json` (`source_file`)
  - `scripts/export_surface_2024_300_images.py` (`EXACT_SOURCE`)

## Number of images
- Surface set already generated:
  - `results/plots/deterministic_2024_surface_300/`
  - PNG count: **300** (`TEMP_surface_2024_z001.png` ... `TEMP_surface_2024_z300.png`)
- Index file:
  - `results/plots/deterministic_2024_surface_300/index.csv`
  - rows: **300**

## Shape of each image
- Underlying data grid shape (for tensor reconstruction): **(64, 112)** per image.
  - From `scripts/export_surface_2024_300_images.py`: `NY=64`, `NX=112`, and stack shape `(300, 64, 112)`.
- Rendered PNG resolution in `deterministic_2024_surface_300`: **630 x 1050 px** (figure with axes/colorbar).

## Common mask
- There is **no saved common-mask file** found in `results/`.
- There is **no saved stacked tensor file** (`.npy/.npz/.pt/.pkl/...`) found in project.
- Existing NaN signal available in:
  - `results/plots/deterministic_2024_surface_300/index.csv` (`missing_fraction`)
  - mean missing fraction across 300 images: `0.0339006696428571`
- Reconstructable common mask definition (not yet materialized):
  - `common_mask = np.isfinite(stack).all(axis=0)`

## Next recommended scripts for Fossum implementation
- Primary reusable script to reconstruct the 300-image stack from source:
  - `scripts/export_surface_2024_300_images.py`
  - It already builds `grids` with shape `(300, 64, 112)` in memory (`second_pass_build_grids`).
- Also available (depth-wise deterministic set):
  - `scripts/export_2024_images_by_day_and_depth.py`
  - Produces `results/plots/deterministic_2024_by_depth/depth_XX/` with 300 PNG per depth and `index.csv`.
- Practical recommendation for next implementation step:
  - Add a dedicated script to materialize:
    - stacked tensor (`.npy`)
    - common mask (`.npy`)
    - global mean/std over finite points (JSON/CSV)
  - Use `export_surface_2024_300_images.py` logic as baseline.
