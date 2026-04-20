# cost_and_smoothing_audit_report

## 1. Problema observado
- O custo final aumentou fortemente no rerun day1 surface-only com `30-10-2024_predModel_1.nc`.

## 2. Hipoteses testadas
- H1 (comparabilidade de custo): `supported`
- H2 (distribuicao do mapa day1 diferente): `supported`
- H3 (efeito do smoothing): `supported`

## 3. Como o objective e construído (e limites)
- O planner cria `PRIZE_SECTION` a partir de `temperr` via fator decimal (`N_level=1000`, `multiplicative_factor=10^decimal`).
- O solver PyVRP reporta `objective` e `distance`; os logs nao decompõem explicitamente penalties/rewards em componentes completos.
- Foi usada decomposicao proxy: `objective - distance` e confronto com soma de prizes no `.vrp` e prizes visitados debug.

## 4. Comparacao entre mapas
- mapa antigo: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_map_old.png`
- mapa day1: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_map_day1.png`
- diferenca: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_map_difference.png`
- histograma: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_hist_comparison.png`

## 5. Comparacao de prizes
- tabela csv: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_prize_stats.csv`
- tabela json: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_prize_stats.json`
- old client prize sum: `383727.0`
- day1 nosmooth client prize sum: `2287898.0`
- day1 smoothed client prize sum: `1985855.0`

## 6. Efeito do Gaussian smoothing
- log nosmooth: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\planner_stdout_day1_nosmooth.log`
- log smoothed: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\planner_stdout_day1_smoothed.log`
- runtime nosmooth: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\planner_runtime_day1_nosmooth.txt`
- runtime smoothed: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\planner_runtime_day1_smoothed.txt`
- routes nosmooth: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\routes_file_day1_nosmooth.txt`
- routes smoothed: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\routes_file_day1_smoothed.txt`
- plot nosmooth: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\planner_plot_day1_nosmooth.png`
- plot smoothed: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\planner_plot_day1_smoothed.png`
- overlay rotas: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\cost_smoothing_audit_20260419_191848\planner_run\cost_audit_routes_overlay.png`
- objective nosmooth: `1987866`
- objective smoothed: `1754656`

## 7. Conclusao final
- classificacao: **PARTIAL: smoothing reduces the issue but does not fully explain it**
- O aumento do custo e metodologicamente esperado em grande parte por mudanca de escala/distribuicao do problema e comparabilidade limitada entre runs; o Gaussian smoothing melhora parcialmente a comparabilidade e tende a regularizar o comportamento das rotas.