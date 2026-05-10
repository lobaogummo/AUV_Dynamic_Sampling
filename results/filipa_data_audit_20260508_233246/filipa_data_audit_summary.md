# Filipa New Dataset Audit Summary

Output folder: `C:\Users\pedro\Documents\Filipa_dados\results\filipa_data_audit_20260508_233246`

1. Os dados novos estão completos? Sim para a cobertura predModel de outubro por profundidade encontrada.
2. Existem 31 mapas de outubro com TEMP/TEMPpred e STD? Sim, existem 31 mapas surface e 527 predModels de outubro no total.
3. Existem mapas em branco ou suspeitos? Não nos predModels, pelos critérios automáticos aplicados.
4. Qual é a grelha canónica? A grelha dos ficheiros `predModel` high-resolution.
5. Qual é o shape da grelha? `[180, 240]`.
6. Qual é a resolução aproximada? 0.294 km em latitude, 0.229 km em longitude, média 0.261 km.
7. Quais profundidades estão disponíveis? Índices [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]; valores aproximados [0.4940253794193268, 1.5413753986358643, 2.6456685066223145, 3.8194947242736816, 5.078223705291748, 6.440614223480225, 7.92956018447876, 9.572997093200684, 11.40500259399414, 13.467138290405273, 15.810072898864746, 18.495559692382812, 21.59881591796875, 25.211408615112305, 29.44472885131836, 34.43415451049805, 40.344051361083984] m.
8. Qual camada/profundidade deve ser usada primeiro para o pipeline surface? Profundidade índice 1, valor 0.4940253794193268 m.
9. Quais dias de outubro parecem mais heterogéneos/interessantes? 2024-10-10, 2024-10-13, 2024-10-15, 2024-10-11, 2024-10-31, 2024-10-12, 2024-10-09.
10. Os dados estão prontos para substituir o tempRes antigo? Ready as a replacement candidate: no suspicious predModel files detected by automated checks.
11. Quais problemas precisam ser reportados à Filipa? No automated suspicious predModel conditions detected.; além disso, não foram encontrados ficheiros `.out` nesta pasta.

The new Filipa dataset audit determines which high-resolution October TEMP/STD fields are valid, which files are suspicious, and which canonical grid should be used for regime discovery and planner integration.
