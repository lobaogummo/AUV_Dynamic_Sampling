# Step04 SD probe summary

1. A l?gica antiga desta etapa foi encontrada? Sim.
2. O script antigo correspondente foi identificado? Sim: `scripts/04a_separation_distance_probe_fossum_faithful_initial.py`.
3. A metodologia foi preservada? Sim. Foram mantidos valid-mask channel, sparse coding, feature vector completo, StandardScaler antes de Ward, `fcluster` por dist?ncia e ranking antigo.
4. Quais valores de separation distance foram testados? Fra??es do m?ximo merge distance: 0.20, 0.25, 0.30, 0.35 e 0.40.
5. Quantas classes resultam para cada valor? SD=0.20 -> 10 classes; SD=0.25 -> 6 classes; SD=0.30 -> 5 classes; SD=0.35 -> 4 classes; SD=0.40 -> 4 classes.
6. Qual valor parece mais adequado segundo a l?gica antiga? Pelo `balanced_score` autom?tico, SD=0.25 fica ligeiramente em primeiro; pela l?gica can?nica antiga com alvo de 5 classes, SD=0.30 ? o corte mais adequado para continuar.
7. O target de aproximadamente 5 classes continua razo?vel no novo dataset? Sim: SD=0.30 gera exatamente 5 classes, sem singletons, e ? marcado como plaus?vel.
8. O resultado visual/estrutural parece coerente? Sim, preliminarmente; SD=0.20 fragmenta demasiado, SD=0.35/0.40 agregam para 4 classes, e SD=0.30 mant?m a estrutura-alvo da pipeline antiga.
9. Qual configura??o deve ser usada na pr?xima etapa? `patch=40x24`, `dictionary_size=4`, `StandardScaler=ON`, `SD fraction=0.30`, 5 classes.
10. O output est? pronto para seguir a pipeline antiga? Sim.

The legacy separation-distance clustering probe was rerun on the ROI x490 dataset using the visually selected patch size 40x24 and dictionary size 4, with the original pipeline logic preserved.
