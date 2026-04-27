# CAND_B No-Mask Report (day299)

## 1. objetivo desta run
Gerar o equivalente ao CAND_B no dominio do planner com o mesmo ROI/bbox e mesmo subgrid, mas sem remover celulas pela mascara do planner.

## 2. isolamento do efeito ROI/crop sem mascara
Nesta run, o objetivo e isolar o efeito do enquadramento ROI/crop sem o efeito de remocao de celulas da mascara.

## 3. como o CAND_B no-mask foi gerado
1. tempRes numerico do dia z=299 carregado de `X_surface_300.npy` (idx=298).
2. campo regridado para grelha completa do planner (linear + nearest fallback).
3. ROI CAND_B exato carregado de `tempres_georef_candidate_transforms.csv`.
4. subgrid CAND_B extraido sem aplicar mascara -> `candb_crop_nomask_day299.npy`.
5. para comparacao, mascara do planner aplicada no mesmo subgrid -> `candb_crop_masked_day299.npy`.

## 4. confirmacao de mesmo ROI/bbox do CAND_B
- same_roi_used: `True`
- same_bbox_used: `True`
- ROI indices usados: x=28..155, y=34..100

## 5. confirmacao de que no-mask nao aplicou mascara
- same_shape_nomask_vs_masked: `True`
- valid_cells_nomask: `8576`
- valid_cells_masked: `8296`
- masked_fraction: `0.03264925373134331`
- difference_due_to_mask_only_explained: `True`

## 6. outputs gerados
- `results/candb_crop_nomask_day299.npy`
- `results/candb_crop_masked_day299.npy`
- `results/candb_mask_day299.npy`
- `results/full_regridded_planner_nomask_day299.npy`
- `results/candb_crop_nomask_day299.png`
- `results/candb_crop_masked_day299.png`
- `results/candb_mask_day299.png`
- `results/full_regridded_planner_nomask_day299.png`
- `results/comparison_candb_nomask_vs_masked_day299.png`
- `results/comparison_candb_pipeline_day299.png`
- `results/comparison_candb_nomask_focus_day299.png`
- `results/candb_nomask_checks_day299.json`
- `results/candb_nomask_metrics_day299.csv`
- `results/candb_nomask_report_day299.md`
- `results/candb_nomask_summary_day299.md`
