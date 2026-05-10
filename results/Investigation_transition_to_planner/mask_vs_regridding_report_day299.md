# Mask vs Regridding Forensic Report (day299)

## 1. objective
Isolar numericamente e visualmente as contribuicoes de regridding/interpolacao, crop/ROI e mascara do planner para a discrepancia visual entre tempRes z=299 e o campo no dominio planner/HResNew.

## 2. day and inputs
- planning date: `2024-10-30`
- tempRes day used: `z=299` (array idx=298)
- temp stack: `results/plots/X_surface_300.npy`
- planner interface oficial usado: `results/planner_baseline_scenario_c4_predmodel/inputs/30-10-2024_predModel_1_planner_interface.nc`
- CAND_B transform source: `results/tempres_georef_candidate_transforms.csv`
- USER_DIRECT_KM manifest: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/manifest.json`

## 3. methods
- Regridding: `xarray interp linear + nearest fallback` para a grelha completa do planner (sem mascara).
- CAND_B: crop por indices `CAND_B_REGISTRATION_TO_HRES_SUBAREA`.
- USER_DIRECT_KM: crop por mapeamento linear dos limites locais-km do manifest para lon/lat do planner.
- Mascara: aplicacao da mascara booleana exata do planner (`landt==1`) em cada ROI.

## 4. required arrays generated
- `results/native_tempres_day299.npy`
- `results/full_regridded_planner_nomask_day299.npy`
- `results/candb_crop_nomask_day299.npy`
- `results/candb_crop_masked_day299.npy`
- `results/candb_mask_day299.npy`
- `results/userdirect_crop_nomask_day299.npy`
- `results/userdirect_crop_masked_day299.npy`
- `results/userdirect_mask_day299.npy`

## 5. figures generated
- `results/native_tempres_day299.png`
- `results/full_regridded_planner_nomask_day299.png`
- `results/candb_crop_nomask_day299.png`
- `results/candb_crop_masked_day299.png`
- `results/candb_mask_day299.png`
- `results/userdirect_crop_nomask_day299.png`
- `results/userdirect_crop_masked_day299.png`
- `results/userdirect_mask_day299.png`
- `results/comparison_pipeline_candb_day299.png`
- `results/comparison_pipeline_userdirect_day299.png`
- `results/comparison_mask_effect_day299.png`
- `results/comparison_both_methods_day299.png`
- `results/difference_maps_candb_day299.png`
- `results/difference_maps_userdirect_day299.png`
- `results/contour_overlay_candb_day299.png`
- `results/contour_overlay_userdirect_day299.png`

## 6. quantitative diagnosis
- metrics csv: `results/mask_vs_regridding_metrics_day299.csv`
- checks json: `results/mask_vs_regridding_checks_day299.json`
- regridding proxy (native vs backprojected): RMSE=0.00027629899567411994, MAE=9.515982547306611e-05, Pearson=0.9999993418336504, nRMSE=0.0012219566628707346, effect=LOW
- CAND_B masked fraction: 0.03264925373134331 (effect_of_mask=LOW)
- USER_DIRECT masked fraction: 0.07659618573797677 (effect_of_mask=MODERATE)
- CAND_B crop effect: area_fraction=0.1985185185185185, mean_shift_sigma=0.4221189396321248, effect_of_crop=HIGH
- USER_DIRECT crop effect: area_fraction=0.22333333333333333, mean_shift_sigma=0.49103541328456246, effect_of_crop=HIGH

## 7. interpretation
1. Mudanca de grelha/resolucao/interpolacao: capturada pelo proxy native->planner->native e classificada acima.
2. Crop: nao altera valores localmente (full-crop-equivalent vs crop_nomask ~0), mas muda o enquadramento espacial visivel.
3. Mascara: remove celulas (NaN) sem alterar valores nas celulas validas (RMSE nomask vs masked em validas ~0).
4. A mascara altera fortemente a percecao visual quando a fracao mascarada e moderada/alta, mesmo sem alterar valores validos.
5. A consistencia geografica permanece quando ROI, indices e mascara sao coerentes com a grelha do planner.
6. CAND_B e USER_DIRECT sofrem o mesmo efeito de regridding; diferem no posicionamento/shape da ROI e na fracao mascarada.

## 8. direct answers (success criteria)
- A mascara e a principal causa da diferenca visual? `NO`
- O regridding/interpolacao e a principal causa da diferenca visual? `NO`
- O crop/ROI contribui materialmente? `YES`
- A regiao geografica permanece consistente entre tempRes e campo final no planner? `YES`

The visual discrepancy is mainly explained by combination, while the underlying geographic mapping is consistent.
