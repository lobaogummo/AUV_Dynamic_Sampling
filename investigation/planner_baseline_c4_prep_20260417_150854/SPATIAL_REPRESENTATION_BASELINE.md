# SPATIAL_REPRESENTATION_BASELINE

## Secao 1 - Resumo Executivo
- Grelha de entrada (ficheiro/interface baseline): grelha lat/lon 1D regular `180 x 240`, derivada do cenario C4 `predModel` (fonte `LAT/LON` do ficheiro NetCDF).
- Subgrelha operacional efetiva do planner: crop da grelha de entrada pela bounding box operacional de `Config_file.py`, resultando em aproximadamente `92 x 149` (com a logica de slicing atual do planner).
- Decisao metodologica desta fase: o baseline corre no ambiente espacial nativo esperado pelo planner; nao ha ainda acoplamento forcado com a grelha de regimes, descriptors, ou nova discretizacao externa.

## Secao 2 - Grelha De Entrada

### Fonte
- Fonte base do cenario: `FILIPA_DADOS/data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc`.
- Para o baseline, a representacao espacial de interface deve expor coordenadas fisicas em `lat/lon` 1D e campos 2D com os nomes esperados pelo planner (`temperr`, `tbath`, `landt`).

### Shape
- Shape espacial alvo da interface: `LAT x LON = 180 x 240`.

### Bounding box (grelha completa)
- Latitude: `39.38888931274414 .. 39.86111068725586`
- Longitude: `-9.55555534362793 .. -8.916666984558105`
- Resolucao aproximada:
- `dlat = 0.002638193482127349`
- `dlon = 0.002673165069962735`

### Tipo de coordenadas
- Coordenadas geograficas `lat/lon` (graus), eixos 1D regulares.
- Observacao tecnica importante:
- Nos ficheiros C4 `predModel/AUVpredModel`, as coordenadas fisicas estao em `LAT` e `LON`.
- As chaves `lat/lon` nesses ficheiros aparecem indexadas (`0..N-1`) e nao devem ser usadas diretamente como coordenadas fisicas da interface.

## Secao 3 - Subgrelha Operacional Do Planner

### Parametros de bounding box usados no planner
- `OPERATION_LL_CORNER = [39.50934, -9.43520]`
- `OPERATION_UR_CORNER = [39.75313, -9.03402]`
- Fonte: `OptimalPlanning_Lucrezia/Config_file.py:17-18`.

### Logica de crop (codigo atual)
- O planner calcula indices com:
- primeiro indice com `lat > LL_lat`;
- primeiro indice com `lat > UR_lat`, depois `-1`;
- primeiro indice com `lon > LL_lon`;
- primeiro indice com `lon > UR_lon`, depois `-1`;
- e aplica slicing `lat_start:lat_stop` e `lon_start:lon_stop`.
- Fonte: `OptimalPlanning_Lucrezia/OptimalPlanning.py:138-148`.

### Resultado estimado para a grelha C4 (180x240)
- Indices obtidos com a mesma logica do planner:
- `lat_start=46`, `lat_stop=138`
- `lon_start=46`, `lon_stop=195`
- Shape operacional resultante:
- `92 x 149`
- Bounding box efetiva da subgrelha:
- Latitude: `39.51024239822473 .. 39.75031037570378`
- Longitude: `-9.432589750409626 .. -9.036959412706446`

### Relacao com mascaras e obstaculos
- O crop operacional e feito primeiro.
- Depois entram as mascaras no mapa operacional (`temperr2d_op`):
- mascara batimetrica por `MINIMUM_DEPTH`;
- mascara de obstaculos por caixas `OBJECTS_LL_CORNER/OBJECTS_UR_CORNER`.
- Fonte: `OptimalPlanning_Lucrezia/OptimalPlanning.py:178-203`.

## Secao 4 - Decisao Metodologica Desta Fase
- Nesta fase baseline nao se muda a grelha do planner.
- Nao se forca a grelha da pipeline de regimes.
- Nao se forca a grelha dos descriptors.
- Nao se introduz discretizacao externa adicional.
- Objetivo desta etapa: validar que o baseline corre corretamente no ambiente espacial nativo esperado pelo planner da Lucrezia.

## Secao 5 - Factos vs Inferencias

### Factos observados
- O planner consome diretamente `temperr`, `lat`, `lon`, `tbath`, `landt` no ficheiro de entrada.
- O planner recorta a area operacional com `OPERATION_LL_CORNER/UR_CORNER` e slicing por indices.
- No cenario C4, a grelha fisica esta em `LAT/LON` com `180x240` e bbox indicada acima.
- Com essa grelha e a logica atual de crop, a subgrelha operacional sai `92x149`.
- Obstaculos sao aplicados depois do crop.

### Inferencias provaveis
- O ficheiro/interface baseline deve manter exatamente a mesma grelha fisica C4 de entrada (`180x240`) e apenas adaptar nomes/convencoes de campos para o contrato do planner.
- A subgrelha operacional final para o baseline C4 sera a do crop nativo do planner, sem regridding externo.

### Pontos ainda em aberto
- No `predModel` escolhido, `STD` tem dimensao adicional `day` (`2 x 180 x 240`): falta fixar formalmente qual indice `day` sera usado para o campo 2D baseline.
- Regra final de convencao/sinal para `tbath` no ficheiro de interface (compatibilidade com a mascara de profundidade).
- Regra final para derivacao de `landt` (por finitude de campo versus outra mascara disponivel).
