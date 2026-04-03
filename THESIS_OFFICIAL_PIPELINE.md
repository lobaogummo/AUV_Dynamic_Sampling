# Thesis Official Pipeline State

Last updated: 2026-04-03

This file freezes the **official technical state** used by the thesis after closure of governance + downstream CV + strong spatial characterization.

## 1) Official Dataset (Current)

- Official dataset label: `fossum_2024_surface_300days_v1`
- Source file: `data/2024/tempIBHRes2024_1.gslib`
- Derived arrays used by pipeline:
  - `results/plots/X_surface_300.npy`
  - `results/plots/X_surface_300_norm.npy`
  - `results/plots/mask_common.npy`
  - `results/fossum/global_stats.json`
  - `results/fossum/dataset_summary.json`
- Scope note:
  - This official state is based on the current 300-day dataset.
  - Extension to 365 days (missing 65 days from CMEMS continuation) is pending by design and out of scope here.

## 2) Official Regime Pipeline (Frozen)

- Official pipeline label: `faithful_frozen_working_config_end_to_end`
- Official run root (decision taken):  
  `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328`
- Frozen config:
  - patch size: `72 x 40`
  - dictionary size: `4`
  - StandardScaler: `ON`
  - official SD fraction: `0.30`
  - official global classes: `5`
  - local refinement target: `class_02`
  - default local split: `k=2`
- Pipeline manifests/reports:
  - `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/pipeline_manifest.json`
  - `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/PIPELINE_REPORT.md`

## 3) Official Binary Artifacts

- Canonical dictionary:
  - `results/fossum/canonical_dictionary/canonical_dictionary.npz`
  - `results/fossum/canonical_dictionary/canonical_dictionary_manifest.json`
- Compact model:
  - `results/fossum/compact_model/v0_base/compact_model_final.npz`
  - `results/fossum/compact_model/v0_base/compact_model_manifest.json`

These paths are the official local artifact locations. They are required for reproducible downstream stages.

## 4) Official CV Downstream Binding

- Official CV export root (prototype assets for CV):
  - `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/computer_vision_exports_seed11`
- Official CV analysis output root:
  - `results/computer_vision_seed11/official_fixed_dictionary_seed11`
- Official chain:
  - Official regime run root
  - -> official CV prototype export (`09_export_cv_prototypes.py`)
  - -> official CV downstream analysis (`10_seed11_cv_analysis.py`, image-only default)

## 5) Official Strong Spatial Characterization (Pixel-Wise)

- Script:
  - `scripts/11_prototype_characterization.py`
  - `scripts/prototype_characterization_utils.py`
- Official output root:
  - `results/prototype_characterization_seed11/official_fixed_dictionary_seed11`
- Output content per prototype:
  - pixel table (`pixel_descriptors.csv`) with at least:
    - `lat`, `lon`, `temp_mean`, `temp_std`, `region_label`, `boundary_score`
  - optional-rich descriptors:
    - `gradient_magnitude`, `gradient_direction`, `distance_to_boundary`, `region_id`
  - maps:
    - segmented map
    - gradient map
    - boundary score map
    - boundary map
  - raster arrays (`.npy`) for all descriptor maps

## 6) Official Script Set

- Core regime stages:
  - `scripts/04a_separation_distance_probe_fossum_faithful_initial.py`
  - `scripts/06_class02_local_refinement_sd30.py`
  - `scripts/07_run_faithful_pipeline_end_to_end.py`
- Artifact/governance stages:
  - `scripts/08_select_canonical_dictionary.py`
  - `scripts/08_build_compact_model.py`
  - `scripts/compact_model.py`
- CV stages:
  - `scripts/09_export_cv_prototypes.py`
  - `scripts/10_seed11_cv_analysis.py`
  - `scripts/cv_seed11_utils.py`
- Strong characterization stage:
  - `scripts/11_prototype_characterization.py`
  - `scripts/prototype_characterization_utils.py`

## 7) Baseline vs Official

- **Official**:
  - paths/scripts listed above in sections 2-6
  - roots under `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328`
  - downstream roots explicitly bound in `configs/thesis_official_state.json`
- **Auxiliary / historical / exploratory**:
  - notebooks under `notebooks/`
  - older runs under other result roots (for example `results/final_working_pipeline/final_working_20260328`, sensitivity runs, debug runs)
  - any `Old_Code` scripts and non-official experiment folders

## 8) Central State Config

Official paths and defaults are centralized in:

- `configs/thesis_official_state.json`

Downstream scripts consume this config by default when explicit paths are not provided.
