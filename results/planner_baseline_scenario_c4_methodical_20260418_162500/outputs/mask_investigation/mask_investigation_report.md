# mask_investigation_report

## 1. Problema observado
- No plot final da solução PC-VRP (`20260418T171719Z_wt.png`) apareciam:
  - múltiplas colorbars sobrepostas;
  - elementos gráficos acumulados na mesma figura;
  - zonas pretas visualmente mais extensas que o esperado nas referências.
- Suspeitas testadas: sinal de bathy, construção de `landt`, uso de `mask.out`, combinação de máscaras e pipeline de visualização.

## 2. Hipóteses testadas

### H1 — `tbath = -BATHY` está correto?
- Regra do planner: em `OptimalPlanning.py`, profundidade inválida quando `tbath_op[i,j] > -MINIMUM_DEPTH`.
- Com `MINIMUM_DEPTH=40`:
  - Variante A (`tbath=-BATHY`): 858 células adicionais removidas por profundidade; 11005 células ainda válidas após depth-mask.
  - Variante B (`tbath=+BATHY`): 11863 células removidas por profundidade; 0 células válidas após depth-mask.
- Conclusão H1: `tbath=-BATHY` está correto e inverter o sinal destrói o domínio operacional.

### H2 — `landt` foi construído de forma errada?
- `build_planner_interface.py` cria `landt` por finitude: `landt = finite(temperr) & finite(tbath)`.
- Diagnóstico operacional: `landt_current` inválido = 1845 células (13.46%).
- Conclusão H2: não há evidência de erro interno em `landt` para este cenário.

### H3 — `mask.out` devia ser a fonte principal?
- `mask.out` foi lido e testado com ambas convenções.
- `mask.out` layer0 tem valores `{-1, 0}` e 3 layers idênticas.
- Concordância com `landt_current`:
  - `0 = mar`: 100% (agreement = 1.0)
  - `-1 = mar`: 0%
- Conclusão H3: a convenção correta aqui é `0=mar`, e o `landt` atual já coincide com `mask.out`.

### H4 — excesso de preto vem da combinação de máscaras?
- No crop operacional (13708 células):
  - inválidas por `landt`: 1845 (13.46%)
  - inválidas adicionais por profundidade: 858 (6.26%)
  - inválidas adicionais por obstáculos: 255 (1.86%)
  - válidas finais: 10750 (78.42%)
  - inválidas finais: 2958 (21.58%)
- Conclusão H4: existe área mascarada real (científica) relevante, mas não explica sozinha a aparência “poluída” do plot antigo.

### H5 — problema também de visualização?
- Em `OptimalPlanning.py` antigo (snapshot), havia vários `plt.imshow/plt.colorbar/plt.show` no estado global sem reset explícito entre figuras.
- Resultado observado no output antigo: sobreposição de colorbars e artefactos visuais.
- Conclusão H5: confirmado. A visualização era causa primária do aspeto anómalo.

## 3. Evidência recolhida
- Diagnósticos e métricas:
  - `mask_diagnostics_summary.csv`
  - `mask_diagnostics_summary.json`
  - `diag_01_landt_current.png`
  - `diag_02_landt_from_maskout.png`
  - `diag_03_bathymetry_raw.png`
  - `diag_04_bathymetry_mask_lt_40m.png`
  - `diag_05_obstacle_mask.png`
  - `diag_06_final_combined_mask.png`
  - `diag_07_mask_component_comparison.png`
- Comparação before/after:
  - `before_after_mask_comparison.png`
  - `before_after_planner_solution.png`
  - `before_after_summary.json`
- Métrica visual direta (pixels pretos no PNG):
  - before: `0.051476`
  - after: `0.008741`
- Máscara científica before/after:
  - discordância: `0 / 13708` células.

## 4. Causa raiz identificada

### Causa primária
- Pipeline de plotting (estado global `matplotlib`) com sobreposição de elementos gráficos + representação de `-inf` com a cor mais baixa do colormap (preto/escuro).

### Causas secundárias
- Parte da área preta corresponde a máscara real válida do cenário (land/depth/obstacles), mas não é erro de ciência por si só.

## 5. Correção aplicada
- Correção mínima, sem alterar função custo/planner/VRP/máscaras científicas:
  - criação de helper `_plot_base_map(...)`:
    - `fig, ax = plt.subplots(...)`
    - conversão de não-finitos para `np.nan`
    - `cmap.set_bad('white')`
    - `fig.colorbar(...)`
    - `fig.tight_layout()`
    - `plt.close(fig)` após cada uso
  - aplicação deste padrão nos plots intermédios e no plot final.
- Mantido `tbath = -BATHY`.
- Mantido `landt` e lógica de máscaras.

## 6. Resultado após correção
- Planner rerun no snapshot compatível terminou com `exit_code=0`.
- Nova figura final: `20260418T183627Z_wt.png`.
- Comparação before/after mostra:
  - eliminação de sobreposição de colorbars;
  - máscara renderizada de forma limpa (invalid em branco);
  - rotas e solução preservadas.
- `routes_file.txt` vs `routes_file_maskfix.txt`: conteúdo igual, exceto timestamp.

## 7. Riscos / pontos ainda em aberto
- A correção foi aplicada no `planner_snapshot` de execução e no `OptimalPlanning_Lucrezia/OptimalPlanning.py` do repositório.
- O ficheiro core `OptimalPlanning_Lucrezia/OptimalPlanning.py` continua sem ajuste de compatibilidade PyVRP (`capacity`) porque isso é dependência de ambiente, não lógica científica.
- Se outros cenários tiverem convenção diferente de `mask.out`, repetir o diagnóstico H3 antes de generalizar.

## 8. Ficheiros alterados
- `OptimalPlanning_Lucrezia/OptimalPlanning.py` (plot hygiene e timestamp UTC seguro)
- `results/planner_baseline_scenario_c4_methodical_20260418_162500/planner_snapshot/OptimalPlanning.py` (mesma correção visual no ambiente executado)
- `results/planner_baseline_scenario_c4_methodical_20260418_162500/mask_investigation.py` (diagnóstico forense)
- `results/planner_baseline_scenario_c4_methodical_20260418_162500/mask_fix_postcompare.py` (comparações before/after)
