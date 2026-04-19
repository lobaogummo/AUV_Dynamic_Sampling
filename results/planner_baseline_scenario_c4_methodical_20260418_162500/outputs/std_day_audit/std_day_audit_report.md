# std_day_audit_report

## 1. Ficheiro auditado
- primary file: `C:\Users\pedro\Documents\Filipa_dados\data\TEST_D4\HighRes\Daily_dpt_20241029_NewTest_1\30-10-2024_predModel_1.nc`
- primary sha256: `6cffa66b30c46c1f1fb5b1534ba9b4a2d0bbef82a86577ec67d45a8033193895`
- secondary copy: `C:\Users\pedro\Documents\Filipa_dados\data\TEST_D4\HighRes\Daily_dpt_20241029_NewTest_1\Priori_Nazare_30-10-2024_1\30-10-2024_predModel_1.nc`
- secondary exists: `True`
- secondary sha256: `6cffa66b30c46c1f1fb5b1534ba9b4a2d0bbef82a86577ec67d45a8033193895`
- primary/secondary identical: `True`

## 2. Estrutura da variavel STD
- STD dims: `['day', 'LAT', 'LON']`
- STD shape: `[2, 180, 240]`
- number of day slices: `2`
- valid day indices: `[0, 1]`
- dataset sizes: `{'TIME': 14, 'DEPT': 17, 'LAT': 180, 'LON': 240, 'lat': 180, 'lon': 240, 'depth': 17, 'day': 2}`

## 3. Interpretacao da dimensao day
- has explicit `day` variable: `False`
- STD attrs: `{}`
- global attrs: `{}`
- time-like dims found: `['TIME', 'day']`
- time-like variables found: `[]`
- Observacao: nao foi encontrada metadata explicita que mapeie `day=0/1` para timestamps ou semanticas documentadas.

## 4. Comparacao quantitativa entre day=0 e day=1
- day=0: min=0.000000, max=0.000716, mean=0.000000, std=0.000004, zero_fraction_all=0.697384, finite_fraction=0.697407
- day=1: min=0.004632, max=0.117726, mean=0.048587, std=0.016968, zero_fraction_all=0.000000, finite_fraction=0.697407
- day1-day0 diff: min=0.004632, max=0.117726, mean=0.048587, std=0.016968
- overlap corr(day0,day1): `-0.01389270572134619`
- overlap rmse(day1 vs day0): `0.051464705079621524`
- overlap mae(day1 vs day0): `0.048586936271906536`
- day0 nearly-zero flag: `True`
- day1 structured flag: `True`

## 5. Evidencia visual
- `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\std_day_audit\std_day0_map.png`
- `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\std_day_audit\std_day1_map.png`
- `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\std_day_audit\std_day_difference_map.png`
- `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\std_day_audit\std_day_hist_comparison.png`

## 6. Conclusao
- decision: **UNCERTAIN: day=1 plausible but not proven**
- A escolha de STD[day=1] e auditavelmente defensavel para o input surface-only do planner como opcao operacional pragmatica, mas sem prova semantica completa no metadata do NetCDF.

## 7. Recomendacao final para o pipeline
- Para input surface-only do planner, `STD[day=1, LAT, LON]` e a melhor slice observada numericamente neste ficheiro.
- Como nao ha metadata semantica explicita para `day`, manter documentacao da regra e registrar a decisao no manifest.
- outputs machine-readable: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\std_day_audit\std_day_audit_checks.json` e `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\std_day_audit\std_day_audit_stats.csv`