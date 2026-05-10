# Temperature Field Equivalence Audit Report

Generated at: `2026-04-28T08:30:58.038473+00:00`

## Method

- Fixed georeference: CAND_B EPSG:32629 normal x/y transform from the previous investigation.
- tempRes candidates: z=298, z=299, z=300.
- Main validation targets: TEMPpred and HResNew TEMP.
- STD targets are computed only as a separate control and have blank validation rank.
- Domains tested: full overlap, operational ROI, CAND_B ROI, USER_DIRECT ROI.

## Top Temperature-to-Temperature Pairs

| rank | source_tempres_z | source_date_inferred | target_family | target_variable | target_day_index | target_date_inferred | target_is_apriori_or_assimilated | domain_tested | rmse | pearson | gradient_corr | contour_score | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_predModel | TEMPpred | 1 | 2024-10-30 | apriori_main | operational_roi | 0.45354 | 0.683645 | 0.0107487 | 0.511809 | Temperature validation target. |
| 2 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | D4_predModel | TEMPpred | 1 | 2024-10-30 | apriori_main | operational_roi | 0.45354 | 0.683645 | 0.0107487 | 0.511809 | Temperature validation target. |
| 3 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_predModel | TEMPpred | 0 | 2024-10-30 | apriori_main | operational_roi | 0.484598 | 0.657645 | 0.0347898 | 0.504132 | Temperature validation target. |
| 4 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | D4_predModel | TEMPpred | 0 | 2024-10-30 | apriori_main | operational_roi | 0.484598 | 0.657645 | 0.0347898 | 0.504132 | Temperature validation target. |
| 5 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_predModel | TEMPpred |  | 2024-10-31 | apriori_main | operational_roi | 0.563717 | 0.621572 | -0.00160503 | 0.50062 | Temperature validation target. |
| 6 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_predModel | TEMPpred |  | 2024-10-31 | apriori_main | operational_roi | 0.563717 | 0.621572 | -0.00160503 | 0.50062 | Temperature validation target. |
| 7 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_predModel | TEMPpred | 1 | 2024-10-30 | apriori_main | full_overlap | 0.426795 | 0.592988 | 0.0287311 | 0.471989 | Temperature validation target. |
| 8 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_predModel | TEMPpred | 1 | 2024-10-30 | apriori_main | candb_roi | 0.426795 | 0.592988 | 0.0287311 | 0.471989 | Temperature validation target. |
| 9 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | D4_predModel | TEMPpred | 1 | 2024-10-30 | apriori_main | full_overlap | 0.426795 | 0.592988 | 0.0287311 | 0.471989 | Temperature validation target. |
| 10 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | D4_predModel | TEMPpred | 1 | 2024-10-30 | apriori_main | candb_roi | 0.426795 | 0.592988 | 0.0287311 | 0.471989 | Temperature validation target. |
| 11 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_AUVpredModel | TEMPpred |  | 2024-10-31 | assimilated_control | operational_roi | 0.802844 | 0.568994 | -0.0528711 | 0.509691 | Assimilated/control temperature target. |
| 12 | 300 | candidate_2024-10-31_or_day304_clipped_not_metadata_proven | C4_AUVpredModel | TEMPpred |  | 2024-10-31 | assimilated_control | operational_roi | 0.802844 | 0.568994 | -0.0528711 | 0.509691 | Assimilated/control temperature target. |

## Required Checks

```json
{
  "created_at": "2026-04-28T08:30:52.856322+00:00",
  "fixed_transform": {
    "created_at": "2026-04-27T19:53:24.285415+00:00",
    "projection": {
      "name": "EPSG_32629_UTM29N_formula",
      "units": "km",
      "notes": "WGS84 / UTM zone 29N implemented by standard transverse Mercator formula; pyproj not required."
    },
    "method_name": "CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal",
    "recommended_selection_reason": "Selected because it is the controlled CAND_B registration in UTM 29N with east/north-normal orientation; the fixed z=299 numeric leaderboard is retained separately and is not enough to justify an x-flipped georeference.",
    "source_of_georef": "Controlled registration best candidate",
    "source_details": "investigation/tempibhres_hres_registration_controlled_v4/tables/best_candidate_summary.csv",
    "affine_transform": {
      "x_km_at_col0": 458.603485746378,
      "x_km_at_col_last": 487.8392653026646,
      "y_km_at_row0": 4370.035041908689,
      "y_km_at_row_last": 4389.359043590229,
      "dx_km_mean_signed": 0.26338540140798755,
      "dy_km_mean_signed": 0.30673018542126684,
      "formula": "x_km[col] and y_km[row] are stored explicitly in output grids; affine is linear along each axis."
    },
    "xmin_xmax_ymin_ymax_km": [
      458.603485746378,
      487.8392653026646,
      4370.035041908689,
      4389.359043590229
    ],
    "dx_dy_km_abs": {
      "dx": 0.26338540140798755,
      "dy": 0.30673018542126684
    },
    "centers_or_edges": "hres_crop_resampled_centers",
    "orientation": {
      "x": "normal",
      "y": "normal"
    },
    "lonlat_bbox": [
      -9.482531091523732,
      -9.141397509229135,
      39.478915024326255,
      39.653943160534105
    ],
    "confidence_level": "PLAUSIBLE BUT NOT PROVEN",
    "leaderboard_rank": 42,
    "primary_validation": {
      "target": "D4_predModel_TEMPpred_day0",
      "rmse_temperature": 0.7087736916915864,
      "pearson_temperature": 0.01737845263232038,
      "gradient_corr": 0.1861677954669989,
      "contour_score": 0.3052416782686836
    },
    "best_numeric_match": {
      "method_name": "CAND_B_REGISTRATION_TO_HRES_SUBAREA__local_azimuthal_equidistant_spherical__hres_crop_centers__x_flipped__y_normal",
      "rank": 1,
      "rmse_temperature": 0.6971276671936265,
      "pearson_temperature": 0.34937346500001887,
      "gradient_corr": 0.006502133622602109,
      "contour_score": 0.44834111579854014,
      "note": "This fixed-day numeric match is reported for comparison and is not automatically adopted as the georeference if it conflicts with orientation/registration evidence."
    },
    "outputs": {
      "tempres_x_km_grid": "results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_x_km_grid.npy",
      "tempres_y_km_grid": "results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_y_km_grid.npy",
      "tempres_lon_grid": "results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_lon_grid.npy",
      "tempres_lat_grid": "results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_lat_grid.npy",
      "tempres_georeferenced_day299_nc": "results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_georeferenced_day299.nc"
    }
  },
  "all_tempres_candidates_found": true,
  "all_C4_candidates_found": true,
  "all_D4_candidates_found": true,
  "all_HResNew_candidates_found": true,
  "AUVpredModel_candidates_found": true,
  "found_files": {
    "C4_predModel": [
      "data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc",
      "data/Test_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_predModel_1.nc",
      "data/Test_C4/31-10-2024_predModel_1.nc"
    ],
    "D4_predModel": [
      "data/TEST_D4/HighRes/Daily_dpt_20241029_NewTest_1/30-10-2024_predModel_1.nc"
    ],
    "C4_AUVpredModel": [
      "data/Test_C4/Nazare_30-10-2024_1/30-10-2024_AUVpredModel_1.nc",
      "data/Test_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_AUVpredModel_1.nc",
      "data/Test_C4/31-10-2024_AUVpredModel_1.nc"
    ],
    "D4_AUVpredModel": [
      "data/TEST_D4/HighRes/Daily_dpt_20241029_NewTest_1/30-10-2024_AUVpredModel_1.nc"
    ],
    "HResNew": [
      "data/HResNew/CMEMSnaza_20241030_HResNew.nc",
      "data/HResNew/CMEMSnaza_20241031_HResNew.nc",
      "data/HResNew/CMEMSnaza_20241029_HResNew.nc"
    ]
  },
  "best_pair_overall": {
    "source_tempres_z": 300,
    "target_family": "C4_predModel",
    "target_file": "data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc",
    "target_variable": "TEMPpred",
    "target_day_index": 1,
    "target_date_inferred": "2024-10-30",
    "domain_tested": "operational_roi",
    "rank": 1,
    "rmse": 0.4535396109236697,
    "pearson": 0.6836446724069731,
    "notes": "Temperature validation target."
  },
  "best_pair_apriori_only": {
    "source_tempres_z": 300,
    "target_family": "C4_predModel",
    "target_file": "data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc",
    "target_variable": "TEMPpred",
    "target_day_index": 1,
    "target_date_inferred": "2024-10-30",
    "domain_tested": "operational_roi",
    "rank": 1,
    "rmse": 0.4535396109236697,
    "pearson": 0.6836446724069731,
    "notes": "Temperature validation target."
  },
  "best_pair_HResNew_only": {
    "source_tempres_z": 298,
    "target_family": "HResNew",
    "target_file": "data/HResNew/CMEMSnaza_20241030_HResNew.nc",
    "target_variable": "TEMP",
    "target_day_index": 0,
    "target_date_inferred": "2024-10-30",
    "domain_tested": "operational_roi",
    "rank": 39,
    "rmse": 0.8458214243833946,
    "pearson": 0.20982236352602973,
    "notes": "HResNew TEMP time0 depth0 surface control."
  },
  "best_pair_C4": {
    "source_tempres_z": 300,
    "target_family": "C4_predModel",
    "target_file": "data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc",
    "target_variable": "TEMPpred",
    "target_day_index": 1,
    "target_date_inferred": "2024-10-30",
    "domain_tested": "operational_roi",
    "rank": 1,
    "rmse": 0.4535396109236697,
    "pearson": 0.6836446724069731,
    "notes": "Temperature validation target."
  },
  "best_pair_D4": {
    "source_tempres_z": 300,
    "target_family": "D4_predModel",
    "target_file": "data/TEST_D4/HighRes/Daily_dpt_20241029_NewTest_1/30-10-2024_predModel_1.nc",
    "target_variable": "TEMPpred",
    "target_day_index": 1,
    "target_date_inferred": "2024-10-30",
    "domain_tested": "operational_roi",
    "rank": 2,
    "rmse": 0.4535396109236697,
    "pearson": 0.6836446724069731,
    "notes": "Temperature validation target."
  },
  "best_pair_AUV_control": {
    "source_tempres_z": 300,
    "target_family": "C4_AUVpredModel",
    "target_file": "data/Test_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_AUVpredModel_1.nc",
    "target_variable": "TEMPpred",
    "target_day_index": "",
    "target_date_inferred": "2024-10-31",
    "domain_tested": "operational_roi",
    "rank": 11,
    "rmse": 0.8028442922613285,
    "pearson": 0.5689936706736575,
    "notes": "Assimilated/control temperature target."
  },
  "whether_z299_is_best_for_day30": false,
  "best_z_for_day30": 300,
  "whether_z300_is_best_for_day31": true,
  "best_z_for_day31": 300,
  "whether_day0_or_day1_matches_better": "day1",
  "whether_C4_or_D4_matches_better": "tie_C4_D4_indistinguishable",
  "whether_HResNew_matches_better_than_TEMPpred": false,
  "ranking_policy": "Ranks include temperature validation rows only. STD rows are retained with blank rank as a separate control."
}
```

## Final Answers

1. Qual tempRes z corresponde melhor ao dia 30? `300`
2. Qual tempRes z corresponde melhor ao dia 31? `300`
3. C4 ou D4 corresponde melhor ao tempRes? `tie_C4_D4_indistinguishable`
4. day0 ou day1 corresponde melhor? `day1`
5. HResNew TEMP corresponde melhor do que TEMPpred? `False`
6. O AUVpredModel confirma ou diverge, sabendo que e assimilado? AUV best control pair: `{'source_tempres_z': 300, 'target_family': 'C4_AUVpredModel', 'target_file': 'data/Test_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_AUVpredModel_1.nc', 'target_variable': 'TEMPpred', 'target_day_index': '', 'target_date_inferred': '2024-10-31', 'domain_tested': 'operational_roi', 'rank': 11, 'rmse': 0.8028442922613285, 'pearson': 0.5689936706736575, 'notes': 'Assimilated/control temperature target.'}`. It is assimilated/control, not a primary validation target.
7. A diferenca principal parece vir de georreferencia ou incompatibilidade entre campos/produtos? With the transform fixed, the ranking variation across TEMPpred/HResNew/AUV points to field/product compatibility as a major factor; it does not prove the georeference alone is wrong.

The audit identifies the most coherent temperature-to-temperature pair for validating the tempRes-to-HRes/planner georeferencing, without mixing temperature and STD fields.