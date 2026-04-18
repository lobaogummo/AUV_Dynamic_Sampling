# TEST_SCENARIO_C4_BASELINE

## Cenario Escolhido
- Nome do cenario: `TEST_C4_NAZARE_30-10-2024_INST1_BASELINE`
- Pasta raiz do cenario: `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1`
- Data associada: `2024-10-30` (a partir dos nomes da pasta e dos ficheiros)
- Instancia: `1`

## Porque Este Cenario Foi Escolhido
- E um cenario `TEST_C4` unico, com uma pasta fechada e coerente.
- Junta no mesmo sitio os ficheiros `scene_1/2/3.gslib`, `StDev.gslib`, `Bath.gslib`, `mask.out` e o NetCDF `30-10-2024_AUVpredModel_1.nc`.
- Evita complexidade extra do ramo `Priori_...` (que inclui dimensao adicional `day` no NetCDF correspondente).
- E o candidato mais simples para montar um baseline sem alterar planner/custo, deixando claro o que ainda precisa de derivacao de interface.

## Grelha Associada
- Fonte principal da grelha: `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/30-10-2024_AUVpredModel_1.nc`
- Grelha do cenario: `LAT x LON = 180 x 240`
- Latitude: `39.38888931274414 .. 39.86111068725586`
- Longitude: `-9.55555534362793 .. -8.916666984558105`
- Variavel principal para planeamento (equivalente ao mapa de incerteza): `STD` (shape `180 x 240`)

## Ficheiros Principais do Cenario
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/30-10-2024_AUVpredModel_1.nc`
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/scene_1.gslib`
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/scene_2.gslib`
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/scene_3.gslib`
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/StDev.gslib`
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/Bath.gslib`
- `FILIPA_DADOS/data/Test_C4/Nazare_30-10-2024_1/mask.out`

## Variavel Principal do Planeamento
- Variavel candidata: `STD` no NetCDF `30-10-2024_AUVpredModel_1.nc`.
- Motivo: no planner da Lucrezia o campo principal e `temperr` (mapa 2D de erro/incerteza), e `STD` e o equivalente semantico mais direto no cenario C4.

## Compatibilidade Com O Planner Baseline (Sem Alteracoes)
- O planner consome diretamente `temperr`, `lat`, `lon`, `tbath`, `landt` em `OptimalPlanning_Lucrezia/OptimalPlanning.py` (linhas 109 a 115).
- O NetCDF C4 escolhido tem `STD`, `BATHY`, `LAT/LON`, mas nao tem `temperr`, `tbath`, `landt` com esses nomes/convencoes.
- Portanto, o cenario esta bem definido para preparacao, mas para corrida direta do planner baseline ainda precisa de um ficheiro de adaptacao de interface (sem tocar no planner).

## Factos Observados
- `30-10-2024_AUVpredModel_1.nc` contem `STD`, `BATHY`, `TEMPpred`, `TEMP`.
- `STD` e `BATHY` sao `180x240`.
- `STD` tem `30128` celulas validas e `13072` `NaN`.
- `scene_1/2/3.gslib` existem e representam slices com `z` fixo (`13`, `14`, `15`) e `43200` linhas cada.

## Inferencias Provaveis
- `STD` e o melhor equivalente para `temperr`.
- `landt` pode ser derivado de `isfinite(STD)` (ou equivalente em `BATHY`), porque a mascara de `NaN` coincide entre `STD` e `BATHY`.
- `tbath` do planner parece assumir convencao negativa de profundidade (a partir da logica do mask por `MINIMUM_DEPTH`), pelo que `BATHY` C4 provavelmente precisara de ajuste de sinal no artefacto de preparacao.

## Duvidas / Assuncoes Em Aberto
- Confirmar convencao final de sinal de batimetria esperada operacionalmente no planner (`tbath` negativo versus `BATHY` positivo no C4).
- Confirmar se a mascara operacional final deve vir de `STD`/`BATHY` (`NaN`) ou de `mask.out` no pipeline C4.
- Confirmar se para baseline deve ser usada a versao `AUVpredModel` ou `predModel` (ambas existem para C4, com semantica de `STD` semelhante).
