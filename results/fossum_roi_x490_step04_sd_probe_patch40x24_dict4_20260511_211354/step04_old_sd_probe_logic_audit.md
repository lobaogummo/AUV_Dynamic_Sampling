# Step04 old SD probe logic audit

1. Lógica antiga encontrada? Sim.
2. Script antigo identificado: `scripts/04a_separation_distance_probe_fossum_faithful_initial.py`.
3. Papel do script: construir a árvore Ward no espaço de features Fossum faithful e testar cortes por separation distance como frações da distância máxima de merge.
4. Configuração antiga preservada: `seed=11`, `dictionary_size=4`, valid-mask channel ativo, `mask_encoding=concat`, `feature_mode=raw`, sparse coding com `transform_nnz=2`, `StandardScaler=ON`, Ward linkage e ranking por alvo de aproximadamente 5 classes.
5. Valores default antigos: o script oficial define `DEFAULT_FRACTIONS=[0.30]` e `DEFAULT_WORKING_SD_FRACTION=0.30`.
6. Ambiguidade documentada: apesar do default ser apenas 0.30, o próprio script aceita uma lista de `--fractions`; scripts seguintes/diagnósticos antigos referem `sd_20pct`, `sd_30pct` e `sd_40pct`.
7. Valores usados nesta adaptação: `0.20, 0.25, 0.30, 0.35, 0.40`, centrados no SD oficial 0.30, para permitir observar a relação entre corte e número de classes sem mudar a metodologia.
8. Métrica de ranking antiga: `balanced_score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + 0.20*rank(min_class_size desc) + 0.20*rank(abs(n_classes-target))`.
9. Número de classes: inferido por `scipy.cluster.hierarchy.fcluster(..., criterion="distance")` para cada separation distance.
10. Outputs antigos: `runs.csv`, `ranking.csv`, `REPORT.md`, `dendrogram/`, uma pasta `sd_XXpct/` por corte, painéis de membros, protótipos, mapas de std por classe, distância ao protótipo, painéis closest/farthest, PCA e dendrograma com corte.
11. Adaptações feitas: paths para Step00 ROI x490, `patch=40x24`, `dictionary_size=4`, shape novo `[370,72,117]`, PNGs novos do Step00 e output root novo.
12. Metodologia científica alterada? Não.
