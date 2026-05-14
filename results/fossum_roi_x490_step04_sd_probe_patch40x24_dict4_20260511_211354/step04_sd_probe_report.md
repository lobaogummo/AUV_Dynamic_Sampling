# Step04 SD probe report

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


## Run result

- Dataset: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step00_dataset_20260509_232915`
- Dataset shape: `[370, 72, 117]`
- Patch: `40x24`
- Dictionary size: `4`
- StandardScaler: `ON`
- Ranking target classes: `5`

## Values tested

| sd_fraction_of_max | separation_distance | number_of_classes | class_sizes | min_class_size | max_class_size | singleton_count | mean_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.200000 | 383.368215 | 10 | [12, 29, 70, 50, 51, 56, 30, 11, 31, 30] | 11 | 70 | 0 | 754.779803 | fragmenta demais |
| 0.250000 | 479.210269 | 6 | [41, 70, 50, 107, 30, 72] | 30 | 107 | 0 | 1328.039917 | plausivel |
| 0.300000 | 575.052323 | 5 | [41, 120, 107, 30, 72] | 30 | 120 | 0 | 1755.583032 | plausivel |
| 0.350000 | 670.894377 | 4 | [41, 120, 107, 102] | 41 | 120 | 0 | 2131.731201 | plausivel |
| 0.400000 | 766.736431 | 4 | [41, 120, 107, 102] | 41 | 120 | 0 | 2131.731201 | plausivel |

## Ranking

| sd_fraction_of_max | separation_distance | balanced_score | number_of_classes | singleton_count | mean_icv | behavior_label |
| --- | --- | --- | --- | --- | --- | --- |
| 0.250000 | 479.210269 | 1.950000 | 6 | 0 | 1328.039917 | plausivel |
| 0.300000 | 575.052323 | 2.100000 | 5 | 0 | 1755.583032 | plausivel |
| 0.350000 | 670.894377 | 2.250000 | 4 | 0 | 2131.731201 | plausivel |
| 0.400000 | 766.736431 | 2.250000 | 4 | 0 | 2131.731201 | plausivel |
| 0.200000 | 383.368215 | 2.600000 | 10 | 0 | 754.779803 | fragmenta demais |

## Recommendation

Strict automatic ranking picks SD=0.25 because it has lower mean ICV while staying plausible. For faithful continuation of the old pipeline, SD=0.30 is recommended because it reproduces the official old cut and gives exactly the target of 5 classes without singletons. Keep SD=0.25 as a documented 6-class alternative only if later visual inspection argues for more granularity.

## Main artefacts

- `run_fossum_step04_sd_probe_from_legacy.py`
- `runs.csv`
- `ranking.csv`
- `sd_probe_values_tested.csv`
- `sd_probe_leaderboard.csv`
- `sd_fraction_vs_n_classes.png`
- `sd_probe_top_candidates.png`
- `dendrogram/dendrogram_reference.png`
- `REPORT.md`
- `step04_sd_probe_checks.json`
