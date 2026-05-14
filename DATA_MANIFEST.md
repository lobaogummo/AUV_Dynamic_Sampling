# Data manifest

This file lists the minimum local folders/files needed to work on the current ROI x490 pipeline on another PC. Use `python scripts/check_required_data.py` to validate them.

## raw_filipa_root

- Path: `data/dadosParaPedro_Fresnel`
- Exists here: True
- Size: 47095.47 MB (45.992 GB)
- `data/dadosParaPedro_Fresnel/01.Data/ALL/thetao_20260427.nc` - exists=True, size=224.61 MB, tracked=False, ignored=True
- `data/dadosParaPedro_Fresnel/02.Simulations/HighRes` - exists=True, size=43597.42 MB, tracked=False, ignored=True

## step00

- Path: `results/fossum_roi_x490_step00_dataset_20260509_232915`
- Exists here: True
- Size: 71.46 MB (0.07 GB)
- `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490.npy` - exists=True, size=11.89 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490_norm.npy` - exists=True, size=11.89 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step00_dataset_20260509_232915/mask_common_roi_x490.npy` - exists=True, size=0.01 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step00_dataset_20260509_232915/dates_370.csv` - exists=True, size=0.01 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step00_dataset_20260509_232915/normalization_stats.json` - exists=True, size=0.0 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step00_dataset_20260509_232915/dataset_metadata.json` - exists=True, size=0.0 MB, tracked=True, ignored=False

## step05

- Path: `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755`
- Exists here: True
- Size: 55.46 MB (0.054 GB)
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_assignments.csv` - exists=True, size=0.01 MB, tracked=False, ignored=False
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_prototypes.npy` - exists=True, size=0.19 MB, tracked=False, ignored=False
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_feature_matrix.npy` - exists=True, size=21.58 MB, tracked=False, ignored=False
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_scaled_feature_matrix.npy` - exists=True, size=21.58 MB, tracked=False, ignored=False
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_dictionary.npz` - exists=True, size=0.02 MB, tracked=False, ignored=True
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_sparse_codes.npz` - exists=True, size=10.22 MB, tracked=False, ignored=True
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_checks.json` - exists=True, size=0.0 MB, tracked=False, ignored=False
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_summary.md` - exists=True, size=0.0 MB, tracked=False, ignored=False

## step06

- Path: `results/october_surface_temppred_std_roi_x490_20260511_155923`
- Exists here: True
- Size: 15.16 MB (0.015 GB)
- `results/october_surface_temppred_std_roi_x490_20260511_155923/TEMPpred_october_surface_roi_x490.npy` - exists=True, size=1.0 MB, tracked=False, ignored=False
- `results/october_surface_temppred_std_roi_x490_20260511_155923/STD_october_surface_roi_x490.npy` - exists=True, size=1.0 MB, tracked=False, ignored=False
- `results/october_surface_temppred_std_roi_x490_20260511_155923/dates_october.csv` - exists=True, size=0.0 MB, tracked=False, ignored=False
- `results/october_surface_temppred_std_roi_x490_20260511_155923/october_surface_roi_x490_checks.json` - exists=True, size=0.0 MB, tracked=False, ignored=False
- `results/october_surface_temppred_std_roi_x490_20260511_155923/october_surface_TEMPpred_STD_roi_x490.nc` - exists=True, size=1.32 MB, tracked=False, ignored=True

## pipeline_status_audit

- Path: `results/pipeline_status_audit_20260512_222930`
- Exists here: False
- Size: 0.0 MB (0.0 GB)
- `results/pipeline_status_audit_20260512_222930/pipeline_status_inventory.csv` - exists=False, size=0.0 MB, tracked=False, ignored=False
- `results/pipeline_status_audit_20260512_222930/pipeline_status_checks.json` - exists=False, size=0.0 MB, tracked=False, ignored=False
- `results/pipeline_status_audit_20260512_222930/pipeline_status_summary.md` - exists=False, size=0.0 MB, tracked=False, ignored=False
- `results/pipeline_status_audit_20260512_222930/pipeline_status_report.md` - exists=False, size=0.0 MB, tracked=False, ignored=False
- `results/pipeline_status_audit_20260512_222930/recommended_next_steps.md` - exists=False, size=0.0 MB, tracked=False, ignored=False

## step07_cv_notebook_faithful

- Path: `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154`
- Exists here: True
- Size: 1.08 MB (0.001 GB)
- `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154/cv_features_global_seed11.csv` - exists=True, size=0.0 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154/cv_features_global_seed11_simple.csv` - exists=True, size=0.0 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154/cv_features_global_seed11_image_only.csv` - exists=True, size=0.0 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154/step07_cv_notebook_faithful_checks.json` - exists=True, size=0.0 MB, tracked=True, ignored=False
- `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154/step07_cv_notebook_faithful_summary.md` - exists=True, size=0.0 MB, tracked=True, ignored=False
