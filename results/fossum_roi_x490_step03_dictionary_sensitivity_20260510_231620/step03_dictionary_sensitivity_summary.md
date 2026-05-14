# Step03 dictionary-size sensitivity summary

1. A lógica antiga da dictionary-size sensitivity foi encontrada? Sim.
2. Script antigo usado como referência: `scripts/03a_dictionary_size_sensitivity_fossum_faithful_initial.py`.
3. Dictionary sizes originalmente testados: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12.
4. Esses mesmos dictionary sizes foram repetidos? Sim.
5. Patch usado: 40x24, recomendado pelo Step02.
6. Parâmetros fixos preservados: seeds=[11,23,37,53,71], n_classes=4, include_valid_mask=True, mask_encoding=concat, feature_mode=raw, dict_batch_size=4096, transform_nnz=2, Ward n_clusters=4. StandardScaler e SD fraction não fazem parte desta etapa 03a antiga.
7. Alterações feitas apenas para os novos dados: paths de input/output, 370 dias, shape ROI x490, metadados/datas e patch 40x24 vindo do Step02.
8. Melhor dictionary_size segundo os mesmos critérios antigos: 2.
9. O dictionary_size antigo 4 continua adequado? dictionary_size=4 ficou no rank 2.
10. Dictionary_size recomendado para a próxima etapa: 2.

The legacy dictionary-size sensitivity logic was rerun on the FRESNEL paper ROI x490 dataset using the Step02 recommended patch size, with only path, shape, day-count and metadata adaptations.
