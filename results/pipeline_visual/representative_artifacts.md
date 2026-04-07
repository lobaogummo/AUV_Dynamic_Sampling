# Artefactos representativos por etapa

## STG01_BUILD_SURFACE_DATASET
- `data/2024/tempIBHRes2024_1.gslib`
- `results/fossum/dataset_summary.json`
- `results/plots/X_surface_300.npy`

## STG02_NORMALIZE_COMMON_MASK
- `results/plots/X_surface_300_norm.npy`
- `results/plots/mask_common.npy`
- `results/fossum/global_stats.json`

## STG03_EXPORT_NORMALIZED_PNGS
- `results/plots/pngs_normalized_surface_300_thesis/index.csv`
- `results/plots/pngs_normalized_surface_300_thesis/color_scale_norm.json`
- `results/plots/pngs_normalized_surface_300_thesis/X_surface_norm_z001.png`

## STG04_INITIAL_VISUAL_EXPLORATION
- `results/plots/deterministic_2024_surface_300_thesis/index.csv`
- `results/plots/deterministic_2024_surface_300_thesis/color_scale.json`
- `results/plots/deterministic_2024_surface_300_thesis/TEMP_surface_2024_z001.png`

## STG05_PATCH_SIZE_SENSITIVITY
- `results/fossum/faithful_initial_patch_size_sensitivity_spread/summary.csv`
- `results/fossum/faithful_initial_patch_size_sensitivity_spread/ranking.csv`
- `results/fossum/faithful_initial_patch_size_sensitivity_spread/plots/icv_boxplot_patchsize_faithful_initial.png`

## STG06_DICTIONARY_SIZE_SENSITIVITY
- `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/summary.csv`
- `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/ranking.csv`
- `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/plots/icv_boxplot_dictionarysize_faithful_initial.png`

## STG07_SD_PROBE_AND_SCALER_COMPARISON
- `results/fossum/faithful_initial_sd_autoprobe/w72_h40_xds04_seed11_20260322_215325/runs.csv`
- `results/fossum/faithful_initial_sd_autoprobe/comparison_w72_h40_xds04_seed11_20260322_164245_VS_w72_h40_xds04_seed11_20260322_215325_by_nclass/comparison_summary.json`
- `results/fossum/faithful_initial_sd_autoprobe/comparison_fullassign_w72_h40_xds04_seed11_20260322_164245_VS_w72_h40_xds04_seed11_20260322_215325/comparison_summary.json`

## STG08_SD_REFINED_LOCAL_PROBE
- `results/fossum/faithful_initial_sd_refined_local_probe/summary_runs_all_seeds_20260325.csv`
- `results/fossum/faithful_initial_sd_refined_local_probe/summary_fraction_profile_20260325.csv`
- `results/fossum/faithful_initial_sd_refined_local_probe/summary_nclasses_by_seed_fraction_20260325.csv`

## STG09_SD30_WORKING_CONFIG_SUMMARY
- `results/fossum/faithful_initial_sd_working_config/summary_final_sd30_all_seeds_20260325.csv`
- `results/fossum/faithful_initial_sd_working_config/w72_h40_xds04_seed11_scalerON_final_sd30_20260325/sd_30pct/class_02_members_list.csv`

## STG10_CLASS02_LOCAL_REFINEMENT_KSWEEP
- `results/fossum/class02_local_refinement_sd30_20260326/refined_class02_summary.csv`
- `results/fossum/class02_local_refinement_sd30_20260326/refined_class02_aggregate_by_k.csv`
- `results/fossum/class02_local_refinement_sd30_20260326/seed_11/k2/subclass_prototypes_panel.png`

## STG11_CANONICAL_DICTIONARY_SELECTION
- `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328/CANONICAL_DICTIONARY_REPORT.md`
- `results/fossum/canonical_dictionary/canonical_dictionary.npz`
- `results/fossum/canonical_dictionary/canonical_dictionary_manifest.json`

## STG12_E2E_WORKING_PRE_OFFICIAL
- `results/fossum/final_working_pipeline/e2e_seed11_20260328/pipeline_manifest.json`
- `results/fossum/final_working_pipeline/e2e_fixed_seed11_20260328/pipeline_manifest.json`
- `results/final_working_pipeline/final_working_20260328/pipeline_manifest.json`

## STG13_OFFICIAL_FROZEN_PIPELINE
- `configs/thesis_official_state.json`
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/pipeline_manifest.json`
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/PIPELINE_REPORT.md`
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed11/global/REPORT.md`
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed11/local_class02/refined_class02_summary.csv`

## STG14_BUILD_COMPACT_MODEL
- `results/fossum/compact_model/v0_base/compact_model_final.npz`
- `results/fossum/compact_model/v0_base/compact_model_manifest.json`

## STG15_EXPORT_CV_PROTOTYPES
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/computer_vision_exports_seed11/manifest_cv_exports.json`
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/computer_vision_exports_seed11/seed11/global/prototype_class_01_clean.png`
- `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/computer_vision_exports_seed11/seed11/local_class02/k2/subclass_prototype_01.npy`

## STG16_CV_IMAGE_ONLY_DOWNSTREAM
- `results/computer_vision_seed11/official_fixed_dictionary_seed11/official_image_only_default/manifest.json`
- `results/computer_vision_seed11/official_fixed_dictionary_seed11/official_image_only_default/run_report.md`
- `results/computer_vision_seed11/official_fixed_dictionary_seed11/official_image_only_default/cv_features_global_seed11_image_only.csv`

## STG17_PIXELWISE_CHARACTERIZATION_V2
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/manifest.json`
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/run_report.md`
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/pixel_descriptors_all.csv`
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/global/class_03/figures/segment_map.png`

## STG18_VALIDATION_AND_AUDITS
- `results/validation_descriptor_audit_v2_20260403_215918/AUDIT_REPORT.md`
- `results/validation_descriptor_audit_v2_20260403_215918/audit_manifest.json`
- `results/validation_visual_data_branches_20260405_193102/REPORT.md`
- `results/validation_hres_surface_comparison_20260405_130636/REPORT.md`
