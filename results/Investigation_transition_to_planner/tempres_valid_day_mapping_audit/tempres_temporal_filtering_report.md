# tempRes Temporal Filtering Audit Report

Generated at: `2026-04-28T12:06:36.172095+00:00`

## Evidence Summary

- The authoritative tempRes source located for the official 300-map stack is `data/2024/tempIBHRes2024_1.gslib`.
- The GSLIB header has columns `x`, `y`, `z`, `temp`; no `time` or `date` variable was found.
- The build/export scripts use `TARGET_Z_MAX = 300` and materialize native `z=1..300`.
- `mask_common.npy` is a spatial common mask. It does not remove time slices.
- `configs/thesis_official_state.json` describes this as a 300-day dataset and says extension to 365 days is pending.

## Key z Rows

| z | zero_based_index | real_date | calendar_day_hypothesis_date | kept_in_final_stack | date_status | nan_fraction | mean_temp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 298 | 297 |  | 2024-10-24 | True | no_explicit_date_metadata_found | 0.0339007 | 18.601 |
| 299 | 298 |  | 2024-10-25 | True | no_explicit_date_metadata_found | 0.0339007 | 18.23 |
| 300 | 299 |  | 2024-10-26 | True | no_explicit_date_metadata_found | 0.0339007 | 18.0043 |

## October 29-31 Calendar Check

- 2024-10-29 would be day-of-year/z `303` under calendar indexing; present: `False`.
- 2024-10-30 would be day-of-year/z `304` under calendar indexing; present: `False`.
- 2024-10-31 would be day-of-year/z `305` under calendar indexing; present: `False`.
- To make z=300 equal 2024-10-29/30/31, the pipeline would need 3/4/5 undocumented removed days before those dates.

## Removed/Absent Days Table

- Rows in `tempres_removed_days.csv`: `66`.
- These rows are calendar days absent under the calendar-day hypothesis, not documented QC removals.

## Required Checks

```json
{
  "created_at": "2026-04-28T12:06:36.124100+00:00",
  "source_gslib": {
    "path": "data/2024/tempIBHRes2024_1.gslib",
    "exists": true,
    "title": "tempOcean",
    "nvars": 4,
    "columns": [
      "x",
      "y",
      "z",
      "temp"
    ],
    "row_count": 2150400,
    "x_min": 1,
    "x_max": 112,
    "y_min": 1,
    "y_max": 64,
    "z_min": 1,
    "z_max": 300,
    "n_unique_z": 300,
    "z_values_contiguous": true,
    "expected_rows": 2150400,
    "grid_complete_cartesian": true,
    "finite_count": 2077500,
    "nan_count": 72900,
    "sentinel_count": 0,
    "all_nan_z": [],
    "missing_z_values": [],
    "notes": "gslib_has_x_y_z_temp_only_no_time_or_date_column"
  },
  "optional_2024IB_source": null,
  "final_stack": {
    "stack_path": "results/plots/X_surface_300.npy",
    "stack_shape": [
      300,
      64,
      112
    ],
    "stack_dtype": "float32",
    "norm_stack_exists": true,
    "norm_stack_shape": [
      300,
      64,
      112
    ],
    "mask_exists": true,
    "mask_shape": [
      64,
      112
    ],
    "mask_valid_fraction": 0.9660993303571429,
    "n_all_nan_days": 0,
    "n_all_zero_days": 0,
    "nan_fraction_min": 0.033900669642857144,
    "nan_fraction_max": 0.033900669642857144,
    "nan_fraction_is_constant": true
  },
  "index_file": {
    "path": "results/plots/deterministic_2024_surface_300_thesis_indexed_axes/index.csv",
    "exists": true,
    "n_rows": 300,
    "z_min": 1,
    "z_max": 300,
    "has_date_column": false,
    "columns": [
      "z",
      "filepath",
      "x_index_min",
      "x_index_max",
      "y_index_min",
      "y_index_max",
      "mean_temp",
      "std_temp",
      "min_temp",
      "max_temp",
      "missing_fraction"
    ]
  },
  "official_state_notes": [
    "Current official thesis dataset is the 300-day version already used by the frozen regime pipeline.",
    "Extension to 365 days (missing 65 days) is intentionally pending and out of scope for this closure step."
  ],
  "generation_scripts_found": [
    {
      "path": "scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/03a_dictionary_size_sensitivity_fossum_faithful_initial.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/04a_separation_distance_probe_fossum_faithful_initial.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/05_compare_scaler_vs_no_scaler_by_classcount.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/05b_compare_scaler_vs_no_scaler_full_assignments.py",
      "matched_terms": "X_surface_300;X_surface_300_norm"
    },
    {
      "path": "scripts/06_class02_local_refinement_sd30.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/07_run_faithful_pipeline_end_to_end.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/08_build_compact_model.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/08_select_canonical_dictionary.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/09_export_cv_prototypes.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/10_seed11_cv_analysis.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/12_fix_tempibhres_indexed_axes.py",
      "matched_terms": "tempIBHRes2024;X_surface_300;X_surface_300_norm;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/13_export_tempibhres_relative_km_display_assumed.py",
      "matched_terms": "tempIBHRes2024;X_surface_300;X_surface_300_norm;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/14_tempibhres_hres_registration_controlled.py",
      "matched_terms": "tempIBHRes2024;X_surface_300;X_surface_300_norm;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/audit_tempres_georeference.py",
      "matched_terms": "tempIBHRes2024;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/compact_model.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/compare_candb_vs_userdirect_roi.py",
      "matched_terms": "X_surface_300;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/compare_method_temperature_exact_mask_day299.py",
      "matched_terms": "X_surface_300;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/compare_method_temperature_same_mask.py",
      "matched_terms": "X_surface_300;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/compare_tempres_day_vs_hres_method_crops.py",
      "matched_terms": "X_surface_300;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/cv_seed11_utils.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/fossum_faithful_initial_utils.py",
      "matched_terms": "X_surface_300;X_surface_300_norm"
    },
    {
      "path": "scripts/generate_candb_nomask_day299.py",
      "matched_terms": "X_surface_300;date"
    },
    {
      "path": "scripts/georeference_tempres_from_axes_day299.py",
      "matched_terms": "tempIBHRes2024;X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/investigate_candb_day299_alignment.py",
      "matched_terms": "X_surface_300;deterministic_2024_surface_300;date"
    },
    {
      "path": "scripts/investigate_mask_vs_regridding_day299.py",
      "matched_terms": "X_surface_300;date"
    },
    {
      "path": "scripts/Old_Code/01_build_fossum_surface_dataset.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;TARGET_Z_MAX;second_pass_build_grids;date"
    },
    {
      "path": "scripts/Old_Code/01b_export_normalized_surface_pngs.py",
      "matched_terms": "X_surface_300;X_surface_300_norm"
    },
    {
      "path": "scripts/Old_Code/02_patch_size_selection.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/Old_Code/02a_patch_size_sensitivity_fossum.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/Old_Code/02a_patch_size_sensitivity_fossum_debugfixed.py",
      "matched_terms": "X_surface_300;X_surface_300_norm"
    },
    {
      "path": "scripts/Old_Code/02a_patch_size_sensitivity_fossum_rerun_corrected.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/Old_Code/03_dictionary_size_sensitivity_fossum.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/Old_Code/explore_dataset.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/Old_Code/export_2024_images_by_day_and_depth.py",
      "matched_terms": "tempIBHRes2024;date"
    },
    {
      "path": "scripts/Old_Code/export_surface_2024_300_images.py",
      "matched_terms": "tempIBHRes2024;deterministic_2024_surface_300;TARGET_Z_MAX;second_pass_build_grids;date"
    },
    {
      "path": "scripts/Old_Code/io_netcdf.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/Old_Code/make_regime_maps_20241029.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/Old_Code/make_temp_slices_20241029.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/Old_Code/utils.py",
      "matched_terms": "date"
    },
    {
      "path": "scripts/prototype_characterization_utils.py",
      "matched_terms": "X_surface_300;X_surface_300_norm;date"
    },
    {
      "path": "scripts/temperature_field_equivalence_audit.py",
      "matched_terms": "X_surface_300;date"
    },
    {
      "path": "scripts/tempres_valid_day_mapping_audit.py",
      "matched_terms": "tempIBHRes2024;X_surface_300;X_surface_300_norm;deterministic_2024_surface_300;TARGET_Z_MAX;second_pass_build_grids;valid_days;selected_days;missing_days;date"
    }
  ],
  "metadata_files_audited_count": 965,
  "date_mapping_files_found": [],
  "metadata_filtering_evidence_sample": [
    {
      "path": "results/Investigation_transition_to_planner/auv_quickstats.csv",
      "size_bytes": 1300,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/Investigation_transition_to_planner/candb_nomask_checks_day299.json",
      "size_bytes": 2649,
      "name_matches": "",
      "content_matches": "nan",
      "date_tokens_sample": "2024-10-30"
    },
    {
      "path": "results/Investigation_transition_to_planner/candb_nomask_metrics_day299.csv",
      "size_bytes": 558,
      "name_matches": "",
      "content_matches": "nan",
      "date_tokens_sample": "2024-10-30"
    },
    {
      "path": "results/Investigation_transition_to_planner/candb_vs_userdirect_metrics.csv",
      "size_bytes": 974,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/Investigation_transition_to_planner/corrected_method_crop_report.md",
      "size_bytes": 3112,
      "name_matches": "report",
      "content_matches": "nan",
      "date_tokens_sample": "2024-10-30"
    },
    {
      "path": "results/Investigation_transition_to_planner/dataset_inventory.csv",
      "size_bytes": 1682840,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": "2024-10-29;2024-10-30;2024-10-31;20241029;20241030;2024_10/30;2024_10/31;2024_11/30;2024_11/31;2024_12/30;2024_12/31;2024_13/30;2024_13/31;2024_14/30;2024_14/31;2024_15/30;2024_15/31;2024_16/30;2024_16/31;2024_17/30"
    },
    {
      "path": "results/Investigation_transition_to_planner/file_count_by_folder.csv",
      "size_bytes": 19300,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": "20241029;20241030"
    },
    {
      "path": "results/Investigation_transition_to_planner/mask_vs_regridding_checks_day299.json",
      "size_bytes": 7740,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": "2024-10-30"
    },
    {
      "path": "results/Investigation_transition_to_planner/mask_vs_regridding_metrics_day299.csv",
      "size_bytes": 1600,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/Investigation_transition_to_planner/mask_vs_regridding_report_day299.md",
      "size_bytes": 4152,
      "name_matches": "report",
      "content_matches": "nan;365",
      "date_tokens_sample": "2024-10-30"
    },
    {
      "path": "results/Investigation_transition_to_planner/method_crop_metrics.csv",
      "size_bytes": 1990,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": "2024-10-30"
    },
    {
      "path": "results/Investigation_transition_to_planner/netcdf_summary.csv",
      "size_bytes": 135508,
      "name_matches": "summary",
      "content_matches": "365",
      "date_tokens_sample": "20241029;20241030;2024_10/30;2024_10/31;2024_11/30;2024_11/31;2024_12/30;2024_12/31;2024_13/30;2024_13/31;2024_14/30;2024_14/31;2024_15/30;2024_15/31;2024_16/30;2024_16/31;2024_17/30;2024_17/31"
    },
    {
      "path": "results/Investigation_transition_to_planner/tempres_georef_candidate_transforms.csv",
      "size_bytes": 2230,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/Investigation_transition_to_planner/tempres_georef_checks.json",
      "size_bytes": 6139,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/Investigation_transition_to_planner/tempres_georef_evidence_index.csv",
      "size_bytes": 68008,
      "name_matches": "",
      "content_matches": "nan;365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/pipeline_visual/pipeline_overview.md",
      "size_bytes": 8234,
      "name_matches": "",
      "content_matches": "nan",
      "date_tokens_sample": ""
    },
    {
      "path": "results/computer_vision_seed11/seed11_cv_20260402_204213/cv_features_global_seed11_simple.csv",
      "size_bytes": 1715,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/class_01_distance_to_prototype.csv",
      "size_bytes": 6045,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/class_01_members_list.csv",
      "size_bytes": 5098,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/class_04_distance_to_prototype.csv",
      "size_bytes": 3951,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/class_04_members_list.csv",
      "size_bytes": 3834,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/class_05_distance_to_prototype.csv",
      "size_bytes": 6660,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/class_05_members_list.csv",
      "size_bytes": 5151,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/local_class02/refined_class02_subclass_metrics.csv",
      "size_bytes": 369,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    },
    {
      "path": "results/final_working_pipeline/final_working_20260328/seed11/global/dendrogram_probe/merge_distances.csv",
      "size_bytes": 5781,
      "name_matches": "",
      "content_matches": "365",
      "date_tokens_sample": ""
    }
  ],
  "n_original_days_found": 300,
  "n_original_calendar_days_found": null,
  "n_final_days": 300,
  "filtering_detected": false,
  "filtering_reason": "No day-level filtering script or selected/valid/missing-days table was found. Located build scripts materialize native GSLIB z=1..300. The common mask removes pixels, not days. configs/thesis_official_state.json notes a 300-day dataset and a pending extension to 365 days.",
  "z_is_calendar_day_or_valid_day_index": "native_1_based_z_index; calendar_day_mapping_not_metadata_proven; valid_day_filtering_not_supported",
  "date_for_z298": {
    "real_date": null,
    "calendar_day_hypothesis": "2024-10-24",
    "calendar_day_of_year": 298,
    "metadata_status": "not_explicitly_proven"
  },
  "date_for_z299": {
    "real_date": null,
    "calendar_day_hypothesis": "2024-10-25",
    "calendar_day_of_year": 299,
    "metadata_status": "not_explicitly_proven"
  },
  "date_for_z300": {
    "real_date": null,
    "calendar_day_hypothesis": "2024-10-26",
    "calendar_day_of_year": 300,
    "metadata_status": "not_explicitly_proven"
  },
  "oct29_present": false,
  "oct30_present": false,
  "oct31_present": false,
  "z_for_oct29": null,
  "z_for_oct30": null,
  "z_for_oct31": null,
  "removed_days_required_if_z300_were_late_october": {
    "if_z300_is_2024-10-29": 3,
    "if_z300_is_2024-10-30": 4,
    "if_z300_is_2024-10-31": 5
  },
  "can_z300_be_oct29_oct30_oct31_due_to_filtering": "theoretically_possible_but_not_supported_by_current_metadata_or_scripts",
  "final_verdict": "No evidence was found that the 300 tempRes z slices are valid days after filtering. The reproducible source path treats z as a native 1-based GSLIB index and copies z=1..300. No time/date variable exists in the GSLIB header. Under the calendar-day hypothesis from 2024-01-01, z=300 is 2024-10-26 and 2024-10-29/30/31 are outside the stack. z=300 could correspond to 2024-10-29/30/31 only if 3/4/5 earlier days had been removed, but no such removed-day metadata or filtering code was found."
}
```

## Final Answers

1. Os 300 dias sao dias corridos ou dias validos apos filtragem? Nao ha prova de filtragem por dias validos; o caminho reprodutivel mostra z=1..300 nativo do GSLIB. A conversao para dias corridos e apenas hipotese porque nao ha time/date no GSLIB.
2. Houve remocao de dias nulos/NaN/invalidos? Nao foi detectada remocao de dias. Foram detectados NaNs espaciais constantes/mascara comum, isto e filtragem de pixels, nao de dias.
3. z=300 corresponde a que data real? Data real nao esta em metadata; na hipotese calendario desde 2024-01-01 corresponde a `2024-10-26`.
4. 29/10/2024 existe no tempRes? `NO` sob hipotese calendario; seria z=303 e esta fora de z=1..300.
5. 30/10/2024 existe no tempRes? `NO` sob hipotese calendario; seria z=304 e esta fora de z=1..300.
6. 31/10/2024 existe no tempRes? `NO` sob hipotese calendario; seria z=305 e esta fora de z=1..300.
7. As comparacoes anteriores com 30/10 e 31/10 estavam temporalmente corretas ou nao? Nao ficam temporalmente provadas. Se z for dia-do-ano, essas comparacoes nao estavam corretas; a melhoria numerica com z=300 deve ser tratada como matching de campo/produto, nao prova temporal.

The audit determines whether z in tempRes is a calendar-day index or a valid-day index after filtering.