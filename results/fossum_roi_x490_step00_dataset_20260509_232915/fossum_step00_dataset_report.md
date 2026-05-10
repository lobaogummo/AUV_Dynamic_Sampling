# Fossum step00 ROI x490 dataset report

## Answers
1. A lógica antiga foi encontrada? Sim.
2. Scripts antigos usados como referência: `scripts/Old_Code/01_build_fossum_surface_dataset.py`, `scripts/Old_Code/01b_export_normalized_surface_pngs.py`, `scripts/Old_Code/export_surface_2024_300_images.py`, `scripts/fossum_faithful_initial_utils.py`
3. A normalização foi mantida igual? Sim: média/desvio global sobre `X[:, mask_common]`.
4. A criação da máscara foi mantida igual? Sim: `np.isfinite(X).all(axis=0)`.
5. Alterações feitas apenas por causa dos novos dados: paths, nomes dos outputs, 370 dias, shape `[370, 72, 117]`, datas e metadados ROI x490.
6. O novo dataset tem shape `[370, 72, 117]`? Sim: `[370, 72, 117]`.
7. Outputs equivalentes criados? Sim: `X_surface_370_roi_x490.npy`, `X_surface_370_roi_x490_norm.npy` e `mask_common_roi_x490.npy`.
8. Pronto para correr a configuração antiga como baseline? Sim: PASS - legacy Fossum step00 dataset-building logic was preserved with only path, shape and metadata adaptations..

## Core metrics
- Days: 370 (2023-10-28 to 2024-10-31)
- Shape: [370, 72, 117]
- Common-mask valid cells: 8004 (0.950142)
- Raw global mean/std: 16.899330139 / 1.348615885
- Normalized valid mean/std: -0.000000094 / 1.000000000

## Logic changes
- Input source changed from old GSLIB/tempRes-derived surface stack to the new ROI x490 HRes .npy stack.
- Output names changed from 300/surface baseline names to 370/roi_x490 names.
- Date handling added because the new stack carries real dates from 2023-10-28 to 2024-10-31.

## Unavoidable adaptations
- Shape changed from (300, 64, 112) to (370, 72, 117).
- Number of images changed from 300 to 370.
- Coordinates are copied from the ROI x490 HRes product instead of old physical coordinate helpers.

The FRESNEL paper ROI x490 dataset was prepared using the legacy Fossum dataset-building logic, with only path, shape and metadata adaptations.
