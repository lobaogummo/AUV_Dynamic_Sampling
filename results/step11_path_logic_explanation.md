# Logica das figuras e dos paths do planner

Este ficheiro resume como foram geradas as figuras recentes dos Steps 11AB, 11AC e 11AE, e de onde vem cada path desenhado.

## Ideia principal

Nas figuras em painel, o fundo visual e o `TEMPpred` do respetivo dia. Esse fundo serve para interpretar espacialmente as trajetorias, mas nao e necessariamente o mapa usado como objective pelo planner.

Em cada painel:

- fundo visual: `TEMPpred` do dia;
- path: trajetoria real produzida pelo planner;
- objective: `information_map` especifico do metodo;
- contorno azul: `region_A`;
- contorno vermelho: `region_B`;
- branco/amarelo: AUV1/AUV2 nos paineis multi-AUV.

Portanto, a leitura correta e:

```text
background mostrado = TEMPpred do dia
mapa usado pelo planner = information_map do metodo
path desenhado = output real do planner convertido para coordenadas ROI
```

## De onde vem o path

O path nao foi desenhado manualmente. Ele vem dos outputs guardados pelo planner.

Fluxo:

1. O script cria um `information_map`.
2. Esse mapa e escrito num ficheiro `.nc` de input para o planner.
3. O planner corre `OptimalPlanning.py`.
4. O planner escreve `routes_file.txt`.
5. O script converte `routes_file.txt` para `trajectory_routes.json`.
6. A figura le `trajectory_routes.json`.
7. Cada waypoint em lat/lon e convertido para indice da grelha high-res.
8. Entre waypoints, o script interpola celulas para desenhar uma linha continua.
9. A coordenada high-res e convertida para coordenada ROI subtraindo:

```text
ROI_ROW_MIN = 55
ROI_COL_MIN = 47
```

Assim, a linha desenhada no painel e a trajetoria do planner em coordenadas ROI.

## Codigo que faz a conversao do path

A leitura dos routes e a conversao para pontos ROI aparece principalmente em:

```text
scripts/11ac_make_step11ab_predmodel_panel_figures.py
scripts/11ae_remaining_days_multi_auv_vehicle_weight_sweep.py
scripts/11z_rerun_minimal_prototype_based_planner_tests.py
scripts/11a_run_minimal_boundary_planner_comparison.py
```

Funcoes importantes:

```text
parse_routes_file(...)
route_grid_points(...)
routes_to_roi_points(...)
plot_panel(...)
plot_case_panel(...)
```

Em termos logicos:

```python
idxs = [(nearest_index(lat_hres, lat), nearest_index(lon_hres, lon)) for lat, lon, depth in waypoints]
segmentos = connect_points(ponto_i, ponto_i+1)
roi_point = (row - ROI_ROW_MIN, col - ROI_COL_MIN)
```

## Figura single-AUV C01

Figura:

```text
single_auv_c01_predmodel_panel_by_method.png
```

Output:

```text
results/fossum_roi_x490_step11ab_c01_region_target_vehicle_sweep_20260526_172106/
```

Script de figura:

```text
scripts/11ac_make_step11ab_predmodel_panel_figures.py
```

Fundo:

```text
TEMPpred do dia 2024-08-24
```

Metodos:

```text
baseline_STD
prototype_boundary_alpha050
cross_region_targets
```

Objectives:

```text
baseline_STD:
information_map = STD_norm

prototype_boundary_alpha050:
information_map = 0.5 * STD_norm + 0.5 * prototype_boundary

cross_region_targets:
information_map = normalize(STD_norm + 2.0 * Gaussian(target_A, target_B))
```

Os targets foram escolhidos assim:

- `target_A`: ponto de STD alto dentro de `region_A`;
- `target_B`: ponto de STD alto dentro de `region_B`;
- `target_B` foi escolhido afastado de `target_A` pelo menos 15 pixels.

Objetivo deste teste:

```text
Ver se uma proxy com pontos-alvo em dois regimes consegue obrigar o AUV single a visitar region_A e region_B.
```

## Figura multi-AUV C01

Figuras:

```text
multi_auv_c01_predmodel_panel_by_method.png
multi_auv_c01_predmodel_panel_selected_methods.png
```

Output:

```text
results/fossum_roi_x490_step11ab_c01_region_target_vehicle_sweep_20260526_172106/
```

Script:

```text
scripts/11ac_make_step11ab_predmodel_panel_figures.py
```

Fundo:

```text
TEMPpred do dia 2024-08-24
```

Metodos:

```text
baseline_STD
prototype_boundary_alpha050
vehicle_specific_conservative
vehicle_specific_balanced
vehicle_specific_strong_regime
```

Objectives:

```text
baseline_STD:
2 AUVs nativos, mapa partilhado STD_norm

prototype_boundary_alpha050:
2 AUVs nativos, mapa partilhado 0.5 * STD_norm + 0.5 * prototype_boundary

vehicle_specific_conservative:
AUV1 = 0.8 * STD_norm + 0.2 * region_A
AUV2 = 0.8 * STD_norm + 0.2 * region_B

vehicle_specific_balanced:
AUV1 = 0.7 * STD_norm + 0.3 * region_A
AUV2 = 0.7 * STD_norm + 0.3 * region_B

vehicle_specific_strong_regime:
AUV1 = 0.6 * STD_norm + 0.4 * region_A
AUV2 = 0.6 * STD_norm + 0.4 * region_B
```

Nota importante:

```text
baseline_STD e prototype_boundary_alpha050 sao runs multi-AUV nativas.
vehicle_specific_* sao proxies: AUV1 e AUV2 foram corridos separadamente como 1-AUV e depois desenhados juntos.
```

Isto acontece porque o planner atual ainda nao suporta nativamente `vehicle-specific prize maps` dentro da mesma otimizacao multi-AUV.

## Figuras multi-AUV C06 e October

Figuras:

```text
step11ae_C06_representative_multi_auv_predmodel_panel_by_method.png
step11ae_October_control_multi_auv_predmodel_panel_by_method.png
```

Output:

```text
results/fossum_roi_x490_step11ae_remaining_days_multi_auv_weight_sweep_20260526_231050/
```

Script:

```text
scripts/11ae_remaining_days_multi_auv_vehicle_weight_sweep.py
```

Fundos:

```text
C06_representative:
TEMPpred do dia 2023-12-22

October_control:
TEMPpred do dia 2024-10-30
```

Metodos:

```text
baseline_STD
prototype_boundary_alpha050
vehicle_specific_conservative
vehicle_specific_balanced
vehicle_specific_strong_regime
```

Logica dos mapas:

```text
baseline_STD:
2 AUVs nativos, mapa partilhado STD_norm

prototype_boundary_alpha050:
2 AUVs nativos, mapa partilhado 0.5 * STD_norm + 0.5 * prototype_boundary

vehicle_specific_conservative:
AUV1 = 0.8 * STD_norm + 0.2 * region_A
AUV2 = 0.8 * STD_norm + 0.2 * region_B

vehicle_specific_balanced:
AUV1 = 0.7 * STD_norm + 0.3 * region_A
AUV2 = 0.7 * STD_norm + 0.3 * region_B

vehicle_specific_strong_regime:
AUV1 = 0.6 * STD_norm + 0.4 * region_A
AUV2 = 0.6 * STD_norm + 0.4 * region_B
```

## O que e prototype-based aqui

Nestes testes, a logica correta do pipeline foi:

```text
TEMPpred do dia -> classificar no modelo canonico Step05
classe prevista -> buscar descriptors do prototipo Step08 dessa classe
STD do dia -> incerteza especifica do dia
planner -> STD do dia + descriptors prototype-based
```

Ou seja:

- `TEMPpred` serve para classificar e para visualizacao;
- `STD_norm` e especifico do dia;
- `boundary`, `region_A` e `region_B` vem de descriptors prototype-based;
- nao ha fallback por mediana do `TEMPpred` nestes novos testes.

## Como interpretar visualmente

Se o path segue zonas vermelhas/quentes do fundo, isso significa que esta numa zona quente do `TEMPpred`, mas nao significa por si so que o planner usou temperatura como objective.

Para saber o objective, olhar para o titulo do painel:

```text
baseline_STD -> objective STD
prototype_boundary_alpha050 -> objective STD + boundary prototype
cross_region_targets -> objective STD + bonus em target_A/target_B
vehicle_specific_* -> objective diferente por AUV, via proxy
```

Para saber se houve separacao de regimes, nao basta olhar para cruzamentos visuais. Usar tambem as metricas:

```text
fraction_path_region_A
fraction_path_region_B
fleet_region_A_coverage
fleet_region_B_coverage
trajectory_overlap_ratio
inter_vehicle_mean_distance
complementarity_score
```

## Limitacao metodologica mais importante

Os metodos `vehicle_specific_*` ainda nao sao uma otimizacao multi-AUV nativa com mapas diferentes por veiculo.

Eles sao uma aproximacao operacional:

```text
run AUV1 com mapa A
run AUV2 com mapa B
juntar os paths
calcular metricas de frota
```

Isto e bom para mostrar que mapas especificos por regime podem separar melhor os veiculos, mas a implementacao final mais forte seria alterar o planner para suportar `vehicle-specific prize maps` nativamente.

## Resumo curto

```text
As figuras mostram paths reais do planner sobre TEMPpred do dia.
O background e visual, nao necessariamente o objective.
Cada metodo tem o seu information_map.
Os paths sao lidos de trajectory_routes.json/routes_file.txt.
As coordenadas sao convertidas de lat/lon para grelha high-res e depois para ROI.
baseline/boundary multi-AUV sao nativos.
vehicle_specific_* sao proxies com dois runs 1-AUV separados.
```

## Figuras Step11A baseline vs boundary-enriched

Figuras:

```text
step11a_C01_representative_predmodel_panel_by_method.png
step11a_C06_representative_predmodel_panel_by_method.png
step11a_October_control_predmodel_panel_by_method.png
```

Output:

```text
results/fossum_roi_x490_step11ad_legacy_planner_predmodel_panels_20260526_215441/
```

Script:

```text
scripts/11ad_make_legacy_step11_predmodel_panels.py
```

Output original das trajetorias:

```text
results/fossum_roi_x490_step11a_minimal_boundary_planner_runs_20260520_102117/
```

Estas figuras foram feitas depois, como diagnostico visual padronizado. O script `11ad` nao rerodou o planner. Ele apenas leu as trajetorias antigas do Step11A e redesenhou cada metodo sobre o `TEMPpred` do respetivo dia.

### Fundo da figura

O fundo e sempre o `TEMPpred` day-specific carregado do Step10F:

```text
results/fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022/planner_minimal_boundary_input_maps.npz
```

Para cada caso:

```text
C01_representative:
TEMPpred de 2024-08-24

C06_representative:
TEMPpred de 2023-12-22

October_control:
TEMPpred de 2024-10-30
```

Importante:

```text
O fundo TEMPpred e apenas visual.
O planner nao usou TEMPpred como objective nestes paineis.
```

### Metodos mostrados

Cada figura Step11A tem tres paineis:

```text
baseline_STD
enriched_boundary_alpha025
enriched_boundary_alpha050
```

Objectives usados pelo planner:

```text
baseline_STD:
information_map = STD_norm

enriched_boundary_alpha025:
information_map = 0.75 * STD_norm + 0.25 * prototype_boundary_score_norm

enriched_boundary_alpha050:
information_map = 0.50 * STD_norm + 0.50 * prototype_boundary_score_norm
```

Aqui `STD_norm` e especifico do dia, e `prototype_boundary_score_norm` vem do descriptor prototype-based da classe prevista.

### De onde vem cada path

O script vai buscar as trajetorias a:

```text
results/fossum_roi_x490_step11a_minimal_boundary_planner_runs_20260520_102117/planner_runs/
```

Com esta estrutura:

```text
planner_runs/C01_representative__baseline_STD/
planner_runs/C01_representative__enriched_boundary_alpha025/
planner_runs/C01_representative__enriched_boundary_alpha050/

planner_runs/C06_representative__baseline_STD/
planner_runs/C06_representative__enriched_boundary_alpha025/
planner_runs/C06_representative__enriched_boundary_alpha050/

planner_runs/October_control__baseline_STD/
planner_runs/October_control__enriched_boundary_alpha025/
planner_runs/October_control__enriched_boundary_alpha050/
```

Dentro de cada pasta, o path vem de:

```text
trajectory_routes.json
```

Se necessario, esse ficheiro tinha sido criado a partir do `routes_file.txt` original do planner.

### Como o path foi desenhado

A logica e a mesma das figuras mais recentes:

1. ler `trajectory_routes.json`;
2. extrair waypoints em lat/lon;
3. converter cada waypoint para indice high-res usando `LAT_hres.npy` e `LON_hres.npy`;
4. interpolar entre waypoints para formar uma linha continua;
5. converter high-res para ROI:

```text
roi_row = highres_row - 55
roi_col = highres_col - 47
```

Depois desenha:

```python
ax.plot([colunas], [linhas])
```

com:

```text
baseline_STD -> preto
enriched_boundary_alpha025 -> amarelo/laranja
enriched_boundary_alpha050 -> azul/ciano
```

### Texto no canto inferior esquerdo

Cada painel mostra tres metricas:

```text
STD=<collected_STD_score>
boundary=<collected_boundary_score>
diff=<trajectory_difference_from_baseline>
```

Significado:

```text
STD:
soma/score de STD recolhido ao longo da trajetoria.

boundary:
soma/score de boundary recolhido ao longo da trajetoria.

diff:
diferenca da trajetoria face ao baseline.
0.00 significa que e o baseline.
Valores perto de 1 indicam trajetoria bastante diferente do baseline.
```

### Interpretacao destas figuras

Estas figuras respondem a uma pergunta simples:

```text
Se eu misturar boundary_score com STD, a trajetoria muda face ao baseline?
```

O que se ve:

- o `alpha025` e o `alpha050` mudam bastante o path em varios casos;
- em C01 e C06, os paths enriched deslocam-se para zonas diferentes do baseline;
- em October, `alpha050` muda muito e perde bastante STD, apesar de ganhar boundary;
- a mudanca nao significa necessariamente melhor exploracao de dois regimes;
- significa apenas que o static prize map com boundary alterou a preferencia espacial do planner.

### Limitacao importante do Step11A

Step11A nao tinha reward de crossing nem especializacao por regimes.

Ele testava apenas:

```text
STD-only
vs
STD + boundary_score
```

Por isso, mesmo quando o path muda, isso nao prova que o AUV atravessou regimes de forma cientificamente util. Prova apenas que o descriptor boundary teve peso suficiente para alterar a rota.

Para avaliar regimes, e melhor usar tambem:

```text
regions_visited
fraction_path_region_A
fraction_path_region_B
crossing_count
path colored by region
```

Essas metricas aparecem melhor em Step11C/Step11Z/Step11AB.

## Figuras Step11B descriptor ablation

Figuras:

```text
step11b_C01_representative_predmodel_panel_by_method_20260520_160652.png
step11b_C06_representative_predmodel_panel_by_method_20260520_165239.png
step11b_October_control_predmodel_panel_by_method_20260520_194733.png
```

Output onde estao as figuras redesenhadas:

```text
results/fossum_roi_x490_step11ad_legacy_planner_predmodel_panels_20260526_215441/
```

Script que as gerou:

```text
scripts/11ad_make_legacy_step11_predmodel_panels.py
```

Outputs originais das trajetorias Step11B:

```text
results/fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_160652
results/fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_165239
results/fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_194733
```

Estas figuras tambem sao pos-processamento read-only. O planner nao foi rerodado. O script `11ad` leu os outputs antigos do Step11B e desenhou todos os metodos sobre o mesmo fundo `TEMPpred` do respetivo dia.

### Fundo da figura

O fundo e:

```text
TEMPpred day-specific vindo do Step10F
```

Ou seja:

```text
C01_representative -> TEMPpred de 2024-08-24
C06_representative -> TEMPpred de 2023-12-22
October_control -> TEMPpred de 2024-10-30
```

Muito importante:

```text
O facto de o fundo ser TEMPpred nao quer dizer que o objective foi TEMPpred.
O fundo e comum para comparacao visual dos paths.
```

### O que o planner usou como objective

Step11B era uma ablation de descriptors. Para cada descriptor e cada alpha, o planner usou:

```text
information_map = (1 - alpha) * STD_norm + alpha * descriptor_norm
```

Com:

```text
alpha = 0.25
alpha = 0.50
```

Descriptors testados:

```text
boundary
gradient
heterogeneity
representative_zone
interest
```

O baseline foi:

```text
baseline_STD:
information_map = STD_norm
```

Assim, os paineis significam:

```text
boundary_alpha025:
information_map = 0.75 * STD_norm + 0.25 * boundary_norm

boundary_alpha050:
information_map = 0.50 * STD_norm + 0.50 * boundary_norm

gradient_alpha025:
information_map = 0.75 * STD_norm + 0.25 * gradient_norm

gradient_alpha050:
information_map = 0.50 * STD_norm + 0.50 * gradient_norm

heterogeneity_alpha025:
information_map = 0.75 * STD_norm + 0.25 * heterogeneity_norm

heterogeneity_alpha050:
information_map = 0.50 * STD_norm + 0.50 * heterogeneity_norm

representative_zone_alpha025:
information_map = 0.75 * STD_norm + 0.25 * representative_zone_norm

representative_zone_alpha050:
information_map = 0.50 * STD_norm + 0.50 * representative_zone_norm

interest_alpha025:
information_map = 0.75 * STD_norm + 0.25 * interest_norm

interest_alpha050:
information_map = 0.50 * STD_norm + 0.50 * interest_norm
```

### Por que parecia que eram mapas STD

Nas figuras antigas do Step11B, algumas visualizacoes mostravam STD ou fundos diagnosticos, o que confundia a leitura do objective.

Estas figuras `Step11AD` foram feitas para corrigir essa interpretacao visual:

```text
todos os metodos sao desenhados sobre o mesmo TEMPpred do dia
o titulo do painel diz qual objective foi usado
as metricas no canto mostram descriptor, alpha, crossings/regimes e diff
```

Portanto:

```text
Sim, os descriptors foram usados no planner.
Nao, estes paineis nao mostram o information_map como fundo.
Mostram TEMPpred para comparacao espacial.
```

### De onde vem cada path

Para cada painel, o script vai buscar o path a:

```text
<output Step11B>/planner_runs/<case_id>__<run_name>/trajectory_routes.json
```

Exemplos:

```text
results/fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_160652/planner_runs/C01_representative__boundary_alpha025/trajectory_routes.json

results/fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_165239/planner_runs/C06_representative__gradient_alpha050/trajectory_routes.json

results/fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_194733/planner_runs/October_control__interest_alpha050/trajectory_routes.json
```

O nome do run e construido assim:

```text
baseline_STD, se descriptor == none
<descriptor>_alpha025, se alpha == 0.25
<descriptor>_alpha050, se alpha == 0.50
```

Depois o path e convertido da mesma forma:

```text
waypoints lat/lon -> indices high-res -> interpolacao entre waypoints -> coordenadas ROI
```

Com:

```text
roi_row = highres_row - 55
roi_col = highres_col - 47
```

### Texto no canto inferior esquerdo

Cada painel mostra:

```text
status=<solver_status>
desc=<descriptor>, a=<alpha>
cross=<boundary_crossing_count_proxy>, regimes=<number_of_distinct_regime_zones_visited_proxy>
diff=<trajectory_difference_from_baseline>
```

Significado:

```text
status:
se o planner terminou com SUCCESS, FAILED, etc.

desc:
descriptor usado no information_map.

a:
peso alpha do descriptor.

cross:
proxy de crossing calculada depois, nao um route-level reward nativo.

regimes:
numero de zonas/regimes visitados segundo a proxy disponivel.

diff:
diferenca do path face ao baseline.
```

### Como interpretar Step11B

Step11B responde a pergunta:

```text
Que descriptor altera mais o path quando combinado com STD?
```

Nao responde perfeitamente a:

```text
O AUV explorou bem dois regimes?
```

Porque nesta fase ainda nao havia:

- route-level crossing reward;
- obrigatoriedade de visitar region_A e region_B;
- vehicle-specific prize maps;
- avaliacao forte de tempo/fraction em cada regime.

Entao, se um painel mostra `regimes=2`, isso sugere que o path tocou/visitou duas zonas segundo a proxy. Mas ainda e preciso confirmar com:

```text
fraction_path_region_A
fraction_path_region_B
path colored by region
crossing events marked
```

### Leitura especifica dos paineis

Para C01:

```text
Alguns descriptors mudam muito o path face ao baseline.
interest, heterogeneity e representative_zone podem dar regimes=2 em alguns alphas.
boundary e gradient tambem mudam a trajetoria, mas podem continuar muito proximos de zonas de alto STD/boundary.
```

Para C06:

```text
Os paths tendem a ficar mais deslocados para a estrutura quente/frontal do dia.
Alguns descriptors alteram muito a geometria da rota, mas a inferencia sobre regimes continua dependente das metricas.
```

Para October:

```text
Os descriptors puxam muitos paths para a zona quente/esquerda do TEMPpred.
Isto pode ser coerente com os prototype descriptors da classe prevista, mas tambem mostra que a visualizacao sobre TEMPpred nao deve ser confundida com objective de temperatura.
```

### Conclusao metodologica para Step11B

Step11B e util como:

```text
descriptor ablation diagnostic
```

Mas nao deve ser usado sozinho como prova final de regime-aware planning.

Melhor uso:

```text
usar Step11B para escolher descriptors candidatos
depois testar esses descriptors em Step11AB/Step11AE ou num planner com vehicle-specific prize maps
```

## Figuras Step11C crossing proxy single-AUV

Figura:

```text
step11c_C01_12h_predmodel_panel_by_method.png
```

Tambem existe uma versao 6h:

```text
step11c_C01_6h_predmodel_panel_by_method.png
```

Output onde estao as figuras redesenhadas:

```text
results/fossum_roi_x490_step11ad_legacy_planner_predmodel_panels_20260526_215441/
```

Script que as gerou:

```text
scripts/11ad_make_legacy_step11_predmodel_panels.py
```

Output original das trajetorias Step11C:

```text
results/fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322/
```

Estas figuras tambem nao rerodam o planner. Elas apenas leem os paths antigos do Step11C e redesenham cada metodo sobre o `TEMPpred` do dia.

### Fundo da figura

O fundo e:

```text
TEMPpred de C01_representative, dia 2024-08-24
```

Mais uma vez:

```text
TEMPpred e fundo visual.
O objective do planner e o information_map do painel.
```

### Contornos desenhados

Nestas figuras aparecem tambem contornos de regioes:

```text
region_A / region_B
```

Eles sao carregados do output antigo Step11C:

```text
region_A_mask.npy
region_B_mask.npy
```

O contorno vermelho/azulado ajuda a perceber se a trajetoria fica num regime, toca na fronteira ou entra nos dois regimes.

### Metodos mostrados na figura 12h

```text
baseline_STD
boundary_alpha050
crossing_gamma025
crossing_gamma050
```

Objectives/logica:

```text
baseline_STD:
information_map = STD_norm

boundary_alpha050:
information_map = 0.5 * STD_norm + 0.5 * boundary_score_norm

crossing_gamma025:
information_map = mapa proxy de crossing com gamma = 0.25

crossing_gamma050:
information_map = mapa proxy de crossing com gamma = 0.50
```

Nota critica:

```text
crossing_gamma025 e crossing_gamma050 nao sao route-level rewards verdadeiros.
Sao proxies por mapa estatico.
```

Ou seja, o planner continua a maximizar premio por celula/no, nao uma regra do tipo:

```text
tem obrigatoriamente de visitar region_A e region_B
```

### De onde vem cada path

O script vai buscar cada path a:

```text
results/fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322/planner_runs/<run_id>/trajectory_routes.json
```

O `run_id` vem diretamente da tabela:

```text
step11c_crossing_metrics.csv
```

Exemplo logico:

```text
planner_runs/C01_representative__single_auv_12h__baseline_STD/
planner_runs/C01_representative__single_auv_12h__boundary_alpha050/
planner_runs/C01_representative__single_auv_12h__crossing_gamma025/
planner_runs/C01_representative__single_auv_12h__crossing_gamma050/
```

Depois:

```text
trajectory_routes.json -> waypoints lat/lon -> high-res row/col -> ROI row/col
```

### Texto no canto inferior esquerdo

Cada painel mostra:

```text
regions=<number_of_distinct_regions_visited>
cross=<boundary_crossing_count>
frac A=<fraction_path_region_A>, B=<fraction_path_region_B>
core=<fraction_path_boundary_core>
```

Significado:

```text
regions:
numero de regioes visitadas pela trajetoria.

cross:
numero de mudancas/atravessamentos detetados entre regioes.

frac A:
fracao do path dentro da region_A.

frac B:
fracao do path dentro da region_B.

core:
fracao do path dentro da boundary_core.
```

### Interpretacao da figura Step11C 12h

A leitura correta nao e apenas olhar para `cross`.

Por exemplo:

```text
crossing_gamma025 pode ter crossing_count alto,
mas ainda assim ficar muito perto da boundary,
sem explorar de forma equilibrada os dois regimes.
```

Por isso, a metrica mais importante e o conjunto:

```text
regions_visited
fraction_path_region_A
fraction_path_region_B
fraction_path_boundary_core
crossing_count
```

No painel mostrado:

```text
baseline_STD:
regions=1, cross=0, frac A=1.00, B=0.00

boundary_alpha050:
regions=2, cross=6, frac A=0.84, B=0.16

crossing_gamma025:
regions=2, cross=10, frac A=0.82, B=0.18

crossing_gamma050:
regions=2, cross=2, frac A=0.93, B=0.07
```

Conclusao:

```text
gamma025 melhorou crossing face ao baseline,
mas ainda nao garante exploracao forte de region_B.
gamma050 nao foi monotonicamente melhor.
```

Isto foi uma das razoes para depois testar `cross_region_targets` no Step11AB.

## Figuras Step11D multi-AUV regime separation

Figura:

```text
step11d_C01_multi_predmodel_panel_by_strategy.png
```

Output onde esta a figura redesenhada:

```text
results/fossum_roi_x490_step11ad_legacy_planner_predmodel_panels_20260526_215441/
```

Script que a gerou:

```text
scripts/11ad_make_legacy_step11_predmodel_panels.py
```

Output original das trajetorias Step11D:

```text
results/fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809/
```

Esta figura mostra as estrategias multi-AUV antigas do Step11D, todas sobre o mesmo `TEMPpred` do dia C01.

### Fundo da figura

```text
TEMPpred de C01_representative, dia 2024-08-24
```

O fundo e apenas visual. Os objectives mudam por estrategia.

### Contornos

O script tenta carregar:

```text
step11d_regime_A_mask.npy
step11d_regime_B_mask.npy
```

e desenha os contornos das regioes no painel. Isso ajuda a ver se cada AUV fica mais associado a um regime ou se ambos ficam na mesma zona geral.

### Estrategias mostradas

```text
multi_baseline_STD
multi_boundary_alpha050
vehicle_specific_regime_maps
vehicle_specific_with_crossing_proxy
sequential_overlap_reduction
post_solver_selected_pair
```

### Logica de cada estrategia

```text
multi_baseline_STD:
run nativa 2-AUV com mapa partilhado STD_norm.

multi_boundary_alpha050:
run nativa 2-AUV com mapa partilhado 0.5 * STD_norm + 0.5 * boundary_score_norm.

vehicle_specific_regime_maps:
proxy com AUV1 associado a region_A e AUV2 associado a region_B.

vehicle_specific_with_crossing_proxy:
proxy semelhante, mas adicionando informacao de crossing/boundary ao mapa de cada AUV.

sequential_overlap_reduction:
proxy sequencial: planeia primeiro uma trajetoria e depois penaliza/desloca a segunda para reduzir overlap.

post_solver_selected_pair:
nao e uma run unica do planner; e uma selecao posterior de um par de candidatos ja gerados.
```

### Nativo vs proxy

Muito importante:

```text
multi_baseline_STD e multi_boundary_alpha050 sao multi-AUV nativos.
```

Isto quer dizer que os dois AUVs sao planeados dentro da mesma chamada ao planner, usando o mesmo mapa de premio.

Mas:

```text
vehicle_specific_regime_maps
vehicle_specific_with_crossing_proxy
sequential_overlap_reduction
post_solver_selected_pair
```

sao estrategias wrapper/proxy, nao uma otimizacao multi-AUV nativa com objectives diferentes por veiculo.

### De onde vem cada path

Para as estrategias nativas:

```text
multi_baseline_STD
multi_boundary_alpha050
```

o script le:

```text
results/fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809/planner_runs/<run_id>/trajectory_routes.json
```

e cada rota dentro do ficheiro e desenhada como:

```text
AUV1 -> branco
AUV2 -> amarelo
```

Para as estrategias proxy, os paths sao obtidos a partir da tabela:

```text
step11d_candidate_trajectories.csv
```

Essa tabela aponta para pastas de runs candidatas, que podem vir do Step11C ou do Step11D. O script cria um lookup por nome de candidato:

```text
region_A
region_B
region_A_with_crossing
region_B_with_crossing
region_B_sequential_penalized
baseline_STD
```

Depois combina esses candidatos nos paineis.

Exemplos:

```text
vehicle_specific_regime_maps:
AUV1 = candidato region_A
AUV2 = candidato region_B

vehicle_specific_with_crossing_proxy:
AUV1 = candidato region_A_with_crossing
AUV2 = candidato region_B_with_crossing

sequential_overlap_reduction:
AUV1 = candidato region_A
AUV2 = candidato region_B_sequential_penalized

post_solver_selected_pair:
AUV1/AUV2 = par selecionado em step11d_selected_pair_summary.csv
```

### Texto no canto inferior esquerdo

Cada painel mostra:

```text
Bcov=<fleet_region_B_coverage>
STD=<fleet_collected_STD>
overlap=<trajectory_overlap_ratio>
meanD=<inter_vehicle_mean_distance>
comp=<fleet_complementarity_score>
```

Significado:

```text
Bcov:
cobertura da region_B pela frota.

STD:
STD total recolhido pela frota.

overlap:
sobreposicao real de celulas amostradas pelos dois AUVs.

meanD:
distancia media entre os paths dos dois AUVs.

comp:
score de complementaridade combinando cobertura de regioes e baixo overlap.
```

### Como interpretar Step11D

A figura nao deve ser lida apenas como:

```text
os paths estao ou nao sobrepostos visualmente?
```

A auditoria Step11W mostrou que o problema principal nao era grande overlay literal nem erro de coordenadas. O problema era mais:

```text
same-zone behavior
```

Ou seja, os AUVs podiam nao repetir exatamente as mesmas celulas, mas continuavam atraidos por zonas parecidas de valor.

Por isso, as metricas importantes sao:

```text
fleet_region_B_coverage
trajectory_overlap_ratio
inter_vehicle_mean_distance
complementarity_score
fleet_collected_STD
```

### Conclusao metodologica para Step11D

Step11D foi importante porque mostrou que:

```text
reduzir overlap nao basta.
e preciso dar papeis diferentes aos veiculos.
```

A estrategia mais interpretavel foi:

```text
vehicle_specific_regime_maps
```

mas ela ainda era proxy/wrapper, nao suporte nativo do planner.

Por isso, a melhoria metodologica mais forte continua a ser:

```text
implementar vehicle-specific prize maps no planner
```
