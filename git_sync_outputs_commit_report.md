# Git sync outputs commit report

Generated: 2026-05-14 11:19:21 +01:00
Branch: master

Remote:
```
origin	https://github.com/lobaogummo/FILIPA_DADOS.git (fetch)
origin	https://github.com/lobaogummo/FILIPA_DADOS.git (push)
```

Results total size: 1242.25 MB (1.213 GB)
Git LFS used: yes

LFS tracking rules:
```
data/new_correct_data_from_FILIPA/* filter=lfs diff=lfs merge=lfs -text
*.npy filter=lfs diff=lfs merge=lfs -text
*.npz filter=lfs diff=lfs merge=lfs -text
*.nc filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.mat filter=lfs diff=lfs merge=lfs -text
*.out filter=lfs diff=lfs merge=lfs -text
*.pkl filter=lfs diff=lfs merge=lfs -text
*.joblib filter=lfs diff=lfs merge=lfs -text
```

LFS files currently listed: 8150

Large files in results/ >50 MB:
- results\cmems_370_surface_to_hres_20260509_135642\thetao_surface_370_hres.npy: 60.97 MB

Large files in results/ >100 MB:
- none

Large files in results/ >500 MB:
- none

Cached diff shortstat:
```
 10124 files changed, 43554 insertions(+), 2 deletions(-)
```

Staged path counts by top-level folder/file:
- results: 10114 staged paths
- scripts: 3 staged paths
- sync_audit_report.md: 1 staged paths
- sync_audit_inventory.csv: 1 staged paths
- required_data_check.csv: 1 staged paths
- DATA_MANIFEST.csv: 1 staged paths
- .gitattributes: 1 staged paths
- proposta_gitignore_patch.md: 1 staged paths
- DATA_MANIFEST.md: 1 staged paths

Staged results/ paths: 10114
Staged scripts/ paths: 3
Staged data/ paths: 0
Staged forbidden cache paths: 0

Safety confirmation:
- data/ was explicitly checked and is not staged.
- data/dadosParaPedro_Fresnel was not added.
- No .venv, __pycache__, pytest/mypy/ruff cache, or node_modules paths were staged.

Cached diff stat preview:
```
 .gitattributes                                     |    8 +
 DATA_MANIFEST.csv (new)                            |   32 +
 DATA_MANIFEST.md (new)                             |   70 +
 proposta_gitignore_patch.md (new)                  |   31 +
 required_data_check.csv (new)                      |   24 +
 .../299/best_temperature_difference_full.npy       |  Bin 345728 -> 131 bytes
 .../299/best_temperature_difference_roi.npy        |  Bin 68736 -> 130 bytes
 .../299/best_temperature_transformed_full.npy      |  Bin 345728 -> 131 bytes
 .../best_temperature_transformed_roi_masked.npy    |  Bin 68736 -> 130 bytes
 .../best_temperature_transformed_roi_nomask.npy    |  Bin 68736 -> 130 bytes
 .../299/candb_crop_masked_day299.npy               |  Bin 68736 -> 130 bytes
 .../299/candb_crop_masked_day299.png               |  Bin 48967 -> 130 bytes
 .../299/candb_crop_nomask_day299.npy               |  Bin 68736 -> 130 bytes
 .../299/candb_crop_nomask_day299.png               |  Bin 48880 -> 130 bytes
 .../299/candb_mask_day299.npy                      |  Bin 8704 -> 129 bytes
 .../299/candb_mask_day299.png                      |  Bin 43499 -> 130 bytes
 .../299/candb_planner_crop_day299.png              |  Bin 91769 -> 130 bytes
 .../299/candb_planner_crop_reference.png           |  Bin 97860 -> 130 bytes
 .../candb_temperature_on_planner_mask_day299.png   |  Bin 51473 -> 130 bytes
 .../299/comparison_both_methods_1to1_day299.png    |  Bin 236961 -> 131 bytes
 .../299/comparison_candb_1to1_day299.png           |  Bin 115618 -> 131 bytes
 .../299/comparison_candb_nomask_focus_day299.png   |  Bin 50283 -> 130 bytes
 .../comparison_candb_nomask_vs_masked_day299.png   |  Bin 72185 -> 130 bytes
 .../299/comparison_candb_pipeline_day299.png       |  Bin 141466 -> 131 bytes
 .../299/comparison_userdirect_1to1_day299.png      |  Bin 123641 -> 131 bytes
 .../299/day299_contour_overlay.png                 |  Bin 186551 -> 131 bytes
 .../299/day299_difference_maps.png                 |  Bin 65134 -> 130 bytes
 .../299/day299_native_vs_regridded_vs_masked.png   |  Bin 187049 -> 131 bytes
 .../299/day299_orientation_hypotheses.png          |  Bin 240204 -> 131 bytes
 .../299/day299_plotting_effects.png                |  Bin 273218 -> 131 bytes
 .../299/full_regridded_planner_nomask_day299.npy   |  Bin 345728 -> 131 bytes
 .../299/full_regridded_planner_nomask_day299.png   |  Bin 61488 -> 130 bytes
 .../299/original_day299_native_field.png           |  Bin 65972 -> 130 bytes
 .../299/tempres_reference_z299.png                 |  Bin 37045 -> 130 bytes
 .../299/userdirect_planner_crop_day299.png         |  Bin 98361 -> 130 bytes
 ...erdirect_temperature_on_planner_mask_day299.png |  Bin 54893 -> 130 bytes
 .../300/candb_hres_crop.png                        |  Bin 99084 -> 130 bytes
 .../300/candb_planner_crop.png                     |  Bin 90421 -> 130 bytes
 .../300/candb_roi_crop.png                         |  Bin 83801 -> 130 bytes
 .../300/candb_roi_on_planner_fullgrid.png          |  Bin 177728 -> 131 bytes
 .../300/candb_temperature_crop.png                 |  Bin 49056 -> 130 bytes
 .../300/candb_temperature_on_planner_mask.png      |  Bin 49857 -> 130 bytes
 .../300/comparison_both_methods_1to1.png           |  Bin 235112 -> 131 bytes
 .../300/comparison_candb_1to1.png                  |  Bin 114573 -> 131 bytes
 .../300/comparison_crops_methods_vs_reference.png  |  Bin 159083 -> 131 bytes
 .../300/comparison_overlay_masks.png               |  Bin 157025 -> 131 bytes
 .../300/comparison_overlay_planner_methods.png     |  Bin 191598 -> 131 bytes
 .../300/comparison_panel_all.png                   |  Bin 465449 -> 131 bytes
 .../300/comparison_panel_hres_methods.png          |  Bin 170364 -> 131 bytes
 .../300/comparison_panel_roi_methods.png           |  Bin 252294 -> 131 bytes
 .../300/comparison_panel_temperature_methods.png   |  Bin 139044 -> 131 bytes
 .../300/comparison_userdirect_1to1.png             |  Bin 120731 -> 131 bytes
 .../300/deterministic_same_day_full.png            |  Bin 55999 -> 130 bytes
 .../300/deterministic_same_day_roi_crop.png        |  Bin 58677 -> 130 bytes
 .../300/grid_extent_overlay.png                    |  Bin 63939 -> 130 bytes
 .../300/grid_resolution_comparison.png             |  Bin 51748 -> 130 bytes
 .../300/planner_operational_roi_crop.png           |  Bin 87636 -> 130 bytes
 .../300/planner_operational_roi_fullgrid.png       |  Bin 179248 -> 131 bytes
 .../300/temperature_full_day_tempres.png           |  Bin 43172 -> 130 bytes
 .../300/tempres_georef_candidate_overlay_1.png     |  Bin 58046 -> 130 bytes
 .../300/tempres_georef_candidate_overlay_2.png     |  Bin 68001 -> 130 bytes
 .../300/tempres_reference_z300.png                 |  Bin 36341 -> 130 bytes
 .../300/user_direct_km_roi_crop.png                |  Bin 86768 -> 130 bytes
 .../300/user_direct_km_roi_on_planner_fullgrid.png |  Bin 179003 -> 131 bytes
 .../300/userdirect_hres_crop.png                   |  Bin 102489 -> 131 bytes
 .../300/userdirect_planner_crop.png                |  Bin 96835 -> 130 bytes
 .../300/userdirect_temperature_crop.png            |  Bin 50679 -> 130 bytes
 .../300/userdirect_temperature_on_planner_mask.png |  Bin 51674 -> 130 bytes
 .../candb_crop_masked_day299.npy                   |  Bin 68736 -> 130 bytes
 .../candb_crop_masked_day299.png                   |  Bin 68975 -> 130 bytes
 .../candb_crop_nomask_day299.npy                   |  Bin 68736 -> 130 bytes
 .../candb_crop_nomask_day299.png                   |  Bin 69475 -> 130 bytes
 .../candb_mask.npy                                 |  Bin 8704 -> 129 bytes
 .../candb_mask_day299.npy                          |  Bin 8704 -> 129 bytes
 .../candb_mask_day299.png                          |  Bin 42899 -> 130 bytes
 .../candb_planner_crop.npy                         |  Bin 68736 -> 130 bytes
 .../candb_planner_crop_day299.npy                  |  Bin 68736 -> 130 bytes
 .../candb_temperature_on_planner_mask.npy          |  Bin 68736 -> 130 bytes
 .../candb_temperature_on_planner_mask_day299.npy   |  Bin 68736 -> 130 bytes
 .../comparison_both_methods_day299.png             |  Bin 270914 -> 131 bytes
 .../comparison_candb_nomask_focus_day299.png       |  Bin 70431 -> 130 bytes
 .../comparison_candb_nomask_vs_masked_day299.png   |  Bin 87034 -> 130 bytes
 .../comparison_candb_pipeline_day299.png           |  Bin 208508 -> 131 bytes
 .../comparison_mask_effect_day299.png              |  Bin 174318 -> 131 bytes
 .../comparison_pipeline_candb_day299.png           |  Bin 203629 -> 131 bytes
 .../comparison_pipeline_userdirect_day299.png      |  Bin 210888 -> 131 bytes
 .../contour_overlay_candb_day299.png               |  Bin 168798 -> 131 bytes
 .../contour_overlay_userdirect_day299.png          |  Bin 188050 -> 131 bytes
 .../difference_maps_candb_day299.png               |  Bin 103132 -> 131 bytes
 .../difference_maps_userdirect_day299.png          |  Bin 107466 -> 131 bytes
 .../full_regridded_planner_nomask_day299.npy       |  Bin 345728 -> 131 bytes
 .../full_regridded_planner_nomask_day299.png       |  Bin 102843 -> 131 bytes
 .../best_georef_candb_roi_comparison_day299.png    |  Bin 104583 -> 131 bytes
 .../best_georef_roi_comparison_day299.png          |  Bin 95411 -> 130 bytes
 .../best_georef_temperature_comparison_day299.png  |  Bin 219286 -> 131 bytes
 .../candidate_georef_overlays.png                  |  Bin 52177 -> 130 bytes
 ...tour_overlay_temperature_best_georef_day299.png |  Bin 116679 -> 131 bytes
 .../georef_residual_error_maps_day299.png          |  Bin 174565 -> 131 bytes
 .../hres_planner_projected_grid.png                |  Bin 45146 -> 130 bytes
 .../tempres_axes_audit_day299.png                  |  Bin 95171 -> 130 bytes
 .../tempres_bbox_on_hres_km.png                    |  Bin 52177 -> 130 bytes
 .../tempres_bbox_on_hres_lonlat.png                |  Bin 58726 -> 130 bytes
 .../tempres_georef_candidate_overlays.png          |  Bin 52177 -> 130 bytes
 .../tempres_lat_grid.npy                           |  Bin 57472 -> 130 bytes
 .../tempres_lon_grid.npy                           |  Bin 57472 -> 130 bytes
 .../tempres_x_km_grid.npy                          |  Bin 57472 -> 130 bytes
 .../tempres_y_km_grid.npy                          |  Bin 57472 -> 130 bytes
 .../native_tempres_day299.npy                      |  Bin 57472 -> 130 bytes
 .../native_tempres_day299.png                      |  Bin 69328 -> 130 bytes
 .../best_temperature_pair_comparison.png           |  Bin 479120 -> 131 bytes
 .../difference_maps_best_pairs.png                 |  Bin 1170319 -> 132 bytes
 .../temporal_candidate_comparison_panel.png        |  Bin 182323 -> 131 bytes
 .../userdirect_crop_masked_day299.npy              |  Bin 77312 -> 130 bytes
 .../userdirect_crop_masked_day299.png              |  Bin 77703 -> 130 bytes
 .../userdirect_crop_nomask_day299.npy              |  Bin 77312 -> 130 bytes
 .../userdirect_crop_nomask_day299.png              |  Bin 78556 -> 130 bytes
 .../userdirect_mask.npy                            |  Bin 9776 -> 129 bytes
 .../userdirect_mask_day299.npy                     |  Bin 9776 -> 129 bytes
 .../userdirect_mask_day299.png                     |  Bin 47043 -> 130 bytes
 .../userdirect_planner_crop.npy                    |  Bin 77312 -> 130 bytes
 .../userdirect_planner_crop_day299.npy             |  Bin 77312 -> 130 bytes
 .../userdirect_temperature_on_planner_mask.npy     |  Bin 77312 -> 130 bytes
 ...erdirect_temperature_on_planner_mask_day299.npy |  Bin 77312 -> 130 bytes
 .../BATHY_hres.npy                                 |  Bin 172928 -> 131 bytes
 .../LAT_hres.npy                                   |  Bin 848 -> 128 bytes
 .../LON_hres.npy                                   |  Bin 1088 -> 129 bytes
 .../MASK_hres.npy                                  |  Bin 43328 -> 130 bytes
 .../bathymetry_hres_mask.png                       |  Bin 80865 -> 130 bytes
 .../hres_interpolation_difference_maps.png         |  Bin 28113 -> 130 bytes
 .../hres_interpolation_validation_panel.png        |  Bin 224232 -> 131 bytes
 .../thetao_370_hres_monthly_samples.png            |  Bin 230131 -> 131 bytes
 .../thetao_370_hres_sample_days.png                |  Bin 146076 -> 131 bytes
 .../thetao_surface_370_hres.nc (new)               |    3 +
 .../thetao_surface_370_hres.npy                    |  Bin 63936128 -> 133 bytes
 .../figures/example_halves.png                     |  Bin 29195 -> 130 bytes
 .../figures/example_quadrants.png                  |  Bin 26614 -> 130 bytes
 .../figures/global_prototypes_fixed_scale.png      |  Bin 67801 -> 130 bytes
 .../figures/image_only_global_grid.png             |  Bin 414471 -> 131 bytes
 .../figures/image_only_local_grid.png              |  Bin 218691 -> 131 bytes
 .../local_class02_prototypes_fixed_scale.png       |  Bin 39971 -> 130 bytes
 .../figures/optional_hsl_exploration.png           |  Bin 420743 -> 131 bytes
 .../figures/simple_global_grid.png                 |  Bin 138047 -> 131 bytes
 .../figures/simple_local_grid.png                  |  Bin 66535 -> 130 bytes
 .../bathymetry_map.png                             |  Bin 92657 -> 130 bytes
 .../grid_latlon_extent.png                         |  Bin 24360 -> 130 bytes
 .../interesting_days_ranking.png                   |  Bin 28631 -> 130 bytes
 .../missing_or_blank_maps_panel.png                |  Bin 9213 -> 129 bytes
 .../october_STD_surface_panel.png                  |  Bin 2748437 -> 132 bytes
 .../october_TEMP_surface_panel.png                 |  Bin 756650 -> 131 bytes
 .../01-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12760 -> 130 bytes
 .../02-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13070 -> 130 bytes
 .../03-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12955 -> 130 bytes
 .../04-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12865 -> 130 bytes
 .../05-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12878 -> 130 bytes
 .../06-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12964 -> 130 bytes
 .../07-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12863 -> 130 bytes
 .../08-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12993 -> 130 bytes
 .../09-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12996 -> 130 bytes
 .../10-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12938 -> 130 bytes
 .../11-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12722 -> 130 bytes
 .../12-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12977 -> 130 bytes
 .../13-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12907 -> 130 bytes
 .../14-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12847 -> 130 bytes
 .../15-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12857 -> 130 bytes
 .../16-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12915 -> 130 bytes
 .../17-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12840 -> 130 bytes
 .../18-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12938 -> 130 bytes
 .../19-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12940 -> 130 bytes
 .../20-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13049 -> 130 bytes
 .../21-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12908 -> 130 bytes
 .../22-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13120 -> 130 bytes
 .../23-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13125 -> 130 bytes
 .../24-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12994 -> 130 bytes
 .../25-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13092 -> 130 bytes
 .../26-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13159 -> 130 bytes
 .../27-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13096 -> 130 bytes
 .../28-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13182 -> 130 bytes
 .../29-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13158 -> 130 bytes
 .../30-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 13107 -> 130 bytes
 .../31-10-2024_predModel_1_TEMPpred_nan.png        |  Bin 12910 -> 130 bytes
 .../STD/01-10-2024_predModel_1_STD.png             |  Bin 297173 -> 131 bytes
 .../STD/02-10-2024_predModel_1_STD.png             |  Bin 315185 -> 131 bytes
 .../STD/03-10-2024_predModel_1_STD.png             |  Bin 359233 -> 131 bytes
 .../STD/04-10-2024_predModel_1_STD.png             |  Bin 358966 -> 131 bytes
 .../STD/05-10-2024_predModel_1_STD.png             |  Bin 339878 -> 131 bytes
 .../STD/06-10-2024_predModel_1_STD.png             |  Bin 353432 -> 131 bytes
 .../STD/07-10-2024_predModel_1_STD.png             |  Bin 286500 -> 131 bytes
 .../STD/08-10-2024_predModel_1_STD.png             |  Bin 279314 -> 131 bytes
 .../STD/09-10-2024_predModel_1_STD.png             |  Bin 282711 -> 131 bytes
 .../STD/10-10-2024_predModel_1_STD.png             |  Bin 288128 -> 131 bytes
 .../STD/11-10-2024_predModel_1_STD.png             |  Bin 303788 -> 131 bytes
 .../STD/12-10-2024_predModel_1_STD.png             |  Bin 305879 -> 131 bytes
 .../STD/13-10-2024_predModel_1_STD.png             |  Bin 328349 -> 131 bytes
 .../STD/14-10-2024_predModel_1_STD.png             |  Bin 352566 -> 131 bytes
 .../STD/15-10-2024_predModel_1_STD.png             |  Bin 359743 -> 131 bytes
 .../STD/16-10-2024_predModel_1_STD.png             |  Bin 359622 -> 131 bytes
 .../STD/17-10-2024_predModel_1_STD.png             |  Bin 354850 -> 131 bytes
 .../STD/18-10-2024_predModel_1_STD.png             |  Bin 351650 -> 131 bytes
 .../STD/19-10-2024_predModel_1_STD.png             |  Bin 333240 -> 131 bytes
 .../STD/20-10-2024_predModel_1_STD.png             |  Bin 322527 -> 131 bytes
 .../STD/21-10-2024_predModel_1_STD.png             |  Bin 299004 -> 131 bytes
 .../STD/22-10-2024_predModel_1_STD.png             |  Bin 300484 -> 131 bytes
 .../STD/23-10-2024_predModel_1_STD.png             |  Bin 319354 -> 131 bytes
 .../STD/24-10-2024_predModel_1_STD.png             |  Bin 337276 -> 131 bytes
 .../STD/25-10-2024_predModel_1_STD.png             |  Bin 327647 -> 131 bytes
 .../STD/26-10-2024_predModel_1_STD.png             |  Bin 339217 -> 131 bytes
 .../STD/27-10-2024_predModel_1_STD.png             |  Bin 359733 -> 131 bytes
 .../STD/28-10-2024_predModel_1_STD.png             |  Bin 350155 -> 131 bytes
 .../STD/29-10-2024_predModel_1_STD.png             |  Bin 362801 -> 131 bytes
 .../STD/30-10-2024_predModel_1_STD.png             |  Bin 341886 -> 131 bytes
 .../STD/31-10-2024_predModel_1_STD.png             |  Bin 327852 -> 131 bytes
 .../TEMPpred/01-10-2024_predModel_1_TEMPpred.png   |  Bin 108149 -> 131 bytes
 .../TEMPpred/02-10-2024_predModel_1_TEMPpred.png   |  Bin 100256 -> 131 bytes
 .../TEMPpred/03-10-2024_predModel_1_TEMPpred.png   |  Bin 81131 -> 130 bytes
 .../TEMPpred/04-10-2024_predModel_1_TEMPpred.png   |  Bin 84346 -> 130 bytes
 .../TEMPpred/05-10-2024_predModel_1_TEMPpred.png   |  Bin 86803 -> 130 bytes
 .../TEMPpred/06-10-2024_predModel_1_TEMPpred.png   |  Bin 79774 -> 130 bytes
 .../TEMPpred/07-10-2024_predModel_1_TEMPpred.png   |  Bin 76176 -> 130 bytes
 .../TEMPpred/08-10-2024_predModel_1_TEMPpred.png   |  Bin 89070 -> 130 bytes
 .../TEMPpred/09-10-2024_predModel_1_TEMPpred.png   |  Bin 95599 -> 130 bytes
... truncated in report; use git diff --cached --stat for full output.
```
