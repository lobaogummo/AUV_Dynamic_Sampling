# tempRes Georeference From Axes Forensic Report (day299)

Generated at: `2026-04-27T19:53:29.153939+00:00`

## 1) Authoritative Sources

- tempRes stack: `results/plots/X_surface_300.npy`
- tempRes original GSLIB: `data/2024/tempIBHRes2024_1.gslib`
- tempRes shape nz,ny,nx: `[300, 64, 112]`
- z/day convention: `1-based z in filenames/reports; numpy index is z-1.`
- z=299 numpy index: `298`

Axis manifests found:
- `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/manifest.json`
- `results/plots/tempibhres_relative_km_display_assumed_user_style_test_v3/manifest.json`

HRes/planner source inventory is stored in `tempres_georef_checks.json`. The planner interface was not used as the primary temperature target because the NetCDF temperature fields `TEMP`/`TEMPpred` are clearer temperature-vs-temperature targets.

## 2) Axis Audit

- The indexed-axis outputs identify tempIBHRes as an indexed grid product.
- The relative-km manifest explicitly labels the km axes as display-derived and not independently validated native georeferencing.
- Therefore the km axes are tested as hypotheses, not assumed as proof.
- Centers and edges conventions, x/y normal orientation, and x/y flipped orientation were all included for the axis-derived candidates.

## 3) Projected HRes/planner Grid

| projection | units | x_min | x_max | y_min | y_max | extent_x_km | extent_y_km | dx_mean_km | dx_std_km | dy_mean_km | dy_std_km | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EPSG_32629_UTM29N_formula | km | 452.158 | 507.176 | 4359.93 | 4412.49 | 55.0185 | 52.5562 | 0.229424 | 0.000452697 | 0.292786 | 1.80788e-05 | WGS84 / UTM zone 29N implemented by standard transverse Mercator formula; pyproj not required. |
| local_azimuthal_equidistant_spherical | km | -27.4524 | 27.4524 | -26.2543 | 26.3029 | 54.9047 | 52.5572 | 0.228947 | 0.000453547 | 0.293344 | 1.67381e-05 | Spherical azimuthal/equidistant projection centered at lon0=-9.23611116, lat0=39.62500000. |
| local_lonlat_linear_km_midlat | km | -27.4272 | 27.4272 | -26.2148 | 26.2148 | 54.8544 | 52.4295 | 0.229516 | 2.17743e-06 | 0.292902 | 1.67104e-05 | Local lon/lat to km approximation centered at lon0=-9.23611116, lat0=39.62500000. |

## 4) Candidate Transform Construction

- Total candidates tested: `112`
- Candidate families include physical axes, HRes bbox, old CAND_B, old USER_DIRECT, controlled registration crops, and top-k registration candidates.
- Candidate geometry details are in `tempres_georef_candidate_transforms.csv`.

## 5) Temperature Validation

- Main rule: temperature vs temperature only.
- TEMPpred/TEMP targets were used.
- STD was not used for validation metrics.
- Metrics are in `tempres_to_hres_temperature_validation_metrics.csv`.

Key finding: the physical-axis candidates were audited and tested, but they did not provide a stronger, orientation-consistent georeference than the controlled CAND_B registration. Absolute Filipa-axis interpretation is not fully contained in HResNew; relative/offset variants are hypotheses rather than native metadata proof.

## 6) Leaderboard

| method_name | source_of_georef | projection_used | centers_or_edges | x_orientation | y_orientation | target_name | bbox_lonlat | contained_in_hres | overlap_fraction | rmse_temperature | pearson_temperature | gradient_corr | contour_score | rank | verdict | score | normalized_rmse | mask_iou_hres_bathy | transform_family | uses_physical_axes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAND_B_REGISTRATION_TO_HRES_SUBAREA__local_azimuthal_equidistant_spherical__hres_crop_centers__x_flipped__y_normal | Controlled registration best candidate | local_azimuthal_equidistant_spherical | hres_crop_resampled_centers | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.481638880023441, -9.140851847391765, 39.47876458494493, 39.65309948991889] | True | 1 | 0.697128 | 0.349373 | 0.00650213 | 0.448341 | 1 | BEST_NUMERIC_MATCH | -0.300095 | 0.87689 | 0.259971 | registration_crop | False |
| CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_flipped__y_normal | Controlled registration best candidate | EPSG_32629_UTM29N_formula | hres_crop_resampled_centers | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.482531091523732, -9.141397509229135, 39.478915024326255, 39.653943160534105] | True | 1 | 0.695879 | 0.348344 | -0.019418 | 0.450203 | 2 | COMPARATOR | -0.315453 | 0.87919 | 0.258578 | registration_crop | False |
| CAND_B_REGISTRATION_TO_HRES_SUBAREA__local_azimuthal_equidistant_spherical__hres_crop_centers__x_flipped__y_flipped | Controlled registration best candidate | local_azimuthal_equidistant_spherical | hres_crop_resampled_centers | flipped | flipped | D4_predModel_TEMPpred_day0 | [-9.481638880023441, -9.140851847391765, 39.47876458494493, 39.65309948991889] | True | 1 | 0.704165 | 0.342423 | 0.0321492 | 0.419469 | 3 | COMPARATOR | -0.317511 | 0.885743 | 0.25928 | registration_crop | False |
| CAND_B_REGISTRATION_TO_HRES_SUBAREA__local_lonlat_linear_km_midlat__hres_crop_centers__x_flipped__y_normal | Controlled registration best candidate | local_lonlat_linear_km_midlat | hres_crop_resampled_centers | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.480706721668962, -9.141213804109325, 39.478584076439205, 39.65270103156234] | True | 1 | 0.700256 | 0.334548 | 0.00688186 | 0.444818 | 4 | COMPARATOR | -0.320427 | 0.880825 | 0.262661 | registration_crop | False |
| CAND_B_REGISTRATION_TO_HRES_SUBAREA__local_lonlat_linear_km_midlat__hres_crop_centers__x_flipped__y_flipped | Controlled registration best candidate | local_lonlat_linear_km_midlat | hres_crop_resampled_centers | flipped | flipped | D4_predModel_TEMPpred_day0 | [-9.480706721668962, -9.141213804109325, 39.478584076439205, 39.65270103156234] | True | 1 | 0.704022 | 0.335156 | 0.0304365 | 0.417121 | 5 | COMPARATOR | -0.326628 | 0.885562 | 0.262661 | registration_crop | False |
| CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_flipped__y_flipped | Controlled registration best candidate | EPSG_32629_UTM29N_formula | hres_crop_resampled_centers | flipped | flipped | D4_predModel_TEMPpred_day0 | [-9.482531091523732, -9.141397509229135, 39.478915024326255, 39.653943160534105] | True | 1 | 0.700094 | 0.350504 | -0.0176155 | 0.421723 | 6 | COMPARATOR | -0.331958 | 0.884516 | 0.258215 | registration_crop | False |
| AXES_FILIPA_DISPLAY_CROP_AS_FULL__EPSG_32629_UTM29N_formula__centers__x_flipped__y_flipped | Filipa cropped image displayed km bbox | EPSG_32629_UTM29N_formula | centers | flipped | flipped | D4_predModel_TEMPpred_day0 | [-9.443370300300174, -9.085650697122853, 39.53281786288449, 39.7210913896249] | True | 1 | 0.782732 | 0.293573 | -0.0220684 | 0.377318 | 7 | AXES_TESTED | -0.382196 | 0.853393 | 0.291565 | physical_axes_crop_as_full | True |
| AXES_FILIPA_DISPLAY_CROP_AS_FULL__EPSG_32629_UTM29N_formula__edges__x_flipped__y_flipped | Filipa cropped image displayed km bbox | EPSG_32629_UTM29N_formula | edges | flipped | flipped | D4_predModel_TEMPpred_day0 | [-9.441765066482887, -9.087244183754605, 39.534288451403626, 39.719625658510935] | True | 1 | 0.784742 | 0.286785 | -0.0205079 | 0.375236 | 8 | AXES_TESTED | -0.391436 | 0.855584 | 0.287346 | physical_axes_crop_as_full | True |
| AXES_RELATIVE_KM_OFFSET_TO_HRES_MIN__EPSG_32629_UTM29N_formula__edges__x_flipped__y_normal | relative_km_display_assumed geometry shifted to HRes projected minimum | EPSG_32629_UTM29N_formula | edges | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.556442420189484, -8.920884446065298, 39.3912673018739, 39.8575819906944] | True | 1 | 0.736112 | -0.0543522 | -0.0216729 | 0.325477 | 9 | AXES_TESTED | -0.405293 | 0.502843 | 0.657036 | physical_axes_relative_offset_fit | True |
| HRES_BBOX_SIMPLE_FULL_DOMAIN__EPSG_32629_UTM29N_formula__edges__x_flipped__y_normal | HResNew/planner full lon/lat bbox | EPSG_32629_UTM29N_formula | edges | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.556443002259238, -8.91897308559157, 39.391276260923156, 39.858713299287054] | True | 1 | 0.73656 | -0.0578666 | -0.0215246 | 0.324984 | 10 | COMPARATOR | -0.409286 | 0.503149 | 0.656695 | simple_bbox | False |
| AXES_RELATIVE_KM_OFFSET_TO_HRES_MIN__EPSG_32629_UTM29N_formula__centers__x_flipped__y_normal | relative_km_display_assumed geometry shifted to HRes projected minimum | EPSG_32629_UTM29N_formula | centers | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.559335117195056, -8.918017129018867, 39.387563077357015, 39.86127055439582] | True | 1 | 0.73553 | -0.0514842 | -0.0449678 | 0.3273 | 11 | AXES_TESTED | -0.412764 | 0.502446 | 0.662227 | physical_axes_relative_offset_fit | True |
| AXES_RELATIVE_KM_OFFSET_TO_HRES_MIN__local_azimuthal_equidistant_spherical__edges__x_flipped__y_normal | relative_km_display_assumed geometry shifted to HRes projected minimum | local_azimuthal_equidistant_spherical | edges | flipped | normal | D4_predModel_TEMPpred_day0 | [-9.554851323790315, -8.917960861017944, 39.39214253829631, 39.8562818079282] | True | 1 | 0.73743 | -0.0580955 | -0.00941811 | 0.323547 | 12 | AXES_TESTED | -0.415099 | 0.514068 | 0.653777 | physical_axes_relative_offset_fit | True |

The top numeric row is retained as evidence, but the final descriptor-transfer transform is selected by combining numeric results with geometry, orientation, and prior controlled-registration evidence.

## 7) Final Transform

- Transform JSON: `results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_georef_transform.json`
- Lon/lat/x/y grids: `results/Investigation_transition_to_planner/georef_tempres_from_axes_day299`
- NetCDF export: `results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_georeferenced_day299.nc`

## 8) Limitations

- No explicit tempIBHRes native projection metadata was found.
- The physical-axis km labels are display-derived according to the manifest.
- Temperature validation can reflect both spatial registration and temporal/model differences between tempRes z=299 and the HRes/planner target.
- PNGs are used only as visual checks; arrays drive the numerical validation.

Final verdict:
- tempRes axes found: YES
- axes interpreted as physical km: UNCERTAIN
- HResNew/planner projected to km: YES
- best projection: EPSG_32629_UTM29N_formula
- best transform: CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal
- tempRes contained in HResNew: YES
- temperature-vs-temperature validation available: YES
- best RMSE temperature: 0.697128
- best Pearson temperature: 0.349373
- georeference confidence: PLAUSIBLE BUT NOT PROVEN
- recommended transform for descriptor transfer: results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_georef_transform.json

The tempRes georeferencing from physical axes is classified as PLAUSIBLE BUT NOT PROVEN, and the recommended transform for transferring descriptors to the planner grid is CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal, based on the evidence above.