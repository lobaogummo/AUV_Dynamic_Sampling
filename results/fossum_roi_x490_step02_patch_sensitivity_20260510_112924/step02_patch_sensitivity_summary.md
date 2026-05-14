# Step02 patch-size sensitivity summary

1. A lógica antiga da patch-size sensitivity foi encontrada? Sim.
2. Script antigo usado como referência: `scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py`.
3. Patch sizes originalmente testados: 16x16, 24x16, 32x20, 40x24, 48x32, 56x32, 64x36, 72x40, 80x44.
4. Esses mesmos patch sizes foram repetidos? Sim.
5. Algum patch antigo teve de ser saltado? Não.
6. Parâmetros fixos preservados: dictionary_size=4, seeds=[11,23,37,53,71], n_classes=4, include_valid_mask=True, mask_encoding=concat, feature_mode=raw, dict_batch_size=4096, transform_nnz=2, Ward n_clusters=4. StandardScaler e SD fraction não fazem parte desta etapa 02b antiga.
7. Alterações feitas apenas para os novos dados: paths de input/output, 370 dias, shape ROI x490, metadados/datas e pasta de PNGs com nomes compatíveis.
8. Melhor patch segundo os mesmos critérios antigos: 40x24.
9. O patch antigo 72x40 continua adequado? O patch 72x40 ficou no rank 8.
10. Patch recomendado para dictionary-size sensitivity: 40x24.

The legacy patch-size sensitivity logic was rerun on the FRESNEL paper ROI x490 dataset with only path, shape, day-count and metadata adaptations.
