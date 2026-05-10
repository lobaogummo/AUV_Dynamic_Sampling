# CAND_B vs USER_DIRECT_KM ROI Comparison

## 1. objetivo
Comparar visualmente e quantitativamente dois metodos para definir/mover a ROI da tempRes para a grelha de planeamento: CAND_B registration-derived vs USER_DIRECT_KM display-axes-direct.

## 2. inputs usados
- Planner interface oficial: `results/planner_baseline_scenario_c4_predmodel/inputs/30-10-2024_predModel_1_planner_interface.nc`
- Config operacional: `OptimalPlanning_Lucrezia/Config_file.py`
- CAND_B source: `results/tempres_georef_candidate_transforms.csv`
- Relative-km deterministic package: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1`
- Relative-km manifest: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/manifest.json`
- temp stack numeric source: `results/plots/X_surface_300.npy`

## 3. dia selecionado
- Dia de planeamento detectado: `2024-10-30`
- Convencao deterministic usada: `DOY_TO_Z_CLIPPED_MAX`
- Justificacao: day-of-year=304 exceeds available z_max=300; clipped to z=300
- deterministic file usado: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/deterministic_2024_surface_300_thesis_relative_km_display_assumed/TEMP_surface_2024_z300.png`

## 4. planner input oficial usado
- `results/planner_baseline_scenario_c4_predmodel/inputs/30-10-2024_predModel_1_planner_interface.nc`
- ROI operacional (indices): x=46..194, y=46..137, shape=92x149

## 5. ficheiro deterministic usado
- Pasta: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/deterministic_2024_surface_300_thesis_relative_km_display_assumed`
- Ficheiro selecionado: `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1/deterministic_2024_surface_300_thesis_relative_km_display_assumed/TEMP_surface_2024_z300.png`
- z selecionado: `300`

## 6. descricao do metodo CAND_B
- registration-derived (transformacao inferida por alinhamento controlado).
- usa bbox/indexes do melhor candidato CAND_B na grelha HRes/planner.
- forte quantitativamente para consistencia operacional, sem afirmar georreferencia nativa do tempRes.

## 7. descricao do metodo USER_DIRECT_KM
- display-axes-direct / USER_DIRECT_KM_METHOD.
- ROI definida diretamente a partir dos eixos locais-km do painel deterministic relative-km.
- projetada para planner por correspondencia linear local-km->HRes bbox->planner indices.
- nao usa CAND_B como transformacao principal.

## 8. figuras geradas
- `results/planner_operational_roi_fullgrid.png`
- `results/planner_operational_roi_crop.png`
- `results/candb_roi_on_planner_fullgrid.png`
- `results/candb_roi_crop.png`
- `results/deterministic_same_day_full.png`
- `results/deterministic_same_day_roi_crop.png`
- `results/user_direct_km_roi_on_planner_fullgrid.png`
- `results/user_direct_km_roi_crop.png`
- `results/comparison_panel_roi_methods.png`
- `results/comparison_overlay_planner_methods.png`
- `results/comparison_crops_methods_vs_reference.png`

## 9. metricas comparativas
- CAND_B overlap IoU vs operational ROI: `0.3727`
- USER_DIRECT_KM overlap IoU vs operational ROI: `0.1086`
- CAND_B overlap coverage of operational ROI: `0.4413`
- USER_DIRECT_KM overlap coverage of operational ROI: `0.1669`
- CAND_B vs USER_DIRECT_KM IoU: `0.2837`
- CAND_B pearson vs deterministic ref: `-0.5167073010445428`
- USER_DIRECT_KM pearson vs deterministic ref: `-0.5240821385452855`
- Tabela completa: `results/candb_vs_userdirect_metrics.csv` e `results/candb_vs_userdirect_bboxes.csv`

## 10. interpretacao
- CAND_B fica mais consistente com o referencial espacial operacional do planner (maior IoU com ROI operacional).
- USER_DIRECT_KM representa melhor a sugestao intuitiva de usar diretamente os eixos locais-km do painel.
- Neste caso, USER_DIRECT_KM desloca a ROI para uma zona mais extensa e mais a sudoeste no planner, reduzindo a coincidencia com a ROI operacional definida no planner.
- A comparacao com deterministic requer reamostragem (bilinear) para igualar shape; este passo foi aplicado explicitamente.

## 11. conclusao final
1. Metodo mais consistente com o referencial do planner: `CAND_B`.
2. Metodo mais proximo da sugestao intuitiva: `USER_DIRECT_KM_METHOD`.
3. USER_DIRECT_KM suficientemente proximo de CAND_B: `nao` (IoU=0.2837).
4. Classificacao final: `CAND_B PREFERRED`.

Para os proximos passos, recomenda-se usar CAND_B como referencia operacional para transferir a ROI/regimes para a grelha do planner.
