# SCENARIO_INPUT_MAPPING_REPORT

## Resumo Executivo
- Cenario base escolhido: `TEST_C4_NAZARE_30-10-2024_INST1_BASELINE`.
- A maior parte dos parametros de missao/solver esta resolvida diretamente em `OptimalPlanning_Lucrezia/Config_file.py`.
- O bloqueio principal para correr o baseline sem alterar o planner e a interface do mapa NetCDF: o planner exige `temperr`, `tbath`, `landt`, enquanto o cenario C4 fornece `STD`, `BATHY` e mascara implicita por `NaN`.
- Conclusao: cenario esta pronto para fase de preparacao e mapeamento, mas ainda nao esta pronto para execucao direta sem um ficheiro adaptado de interface.

## Inputs Ja Resolvidos
- `file_name_cli` (ficheiro de entrada existe e abre corretamente).
- `AUV_NUMBER`, `SPEED`, `MISSION_DURATIONS`, `STARTING_POINTS`, `ENDING_POINTS`.
- `MINIMUM_DEPTH`, `OPERATION_BBOX`, `OBSTACLE_BOXES`.
- `POI_SELECTION_PARAMS`, `SOLVER_PARAMS`, `HOPS_GRID_RESOLUTION`, `MODEL_HOPS`, `WP_WAITING_TIME`.
- Ficheiros de apoio do cenario (`scene_1/2/3.gslib`, `StDev.gslib`, `Bath.gslib`, `mask.out`) estao presentes.

## Inputs Ambiguos
- `lat_1d` e `lon_1d` no C4 aparecem como aliases funcionais (`ds.lat`, `ds.lon`) apesar das coordenadas originais serem `LAT/LON`.
- Fonte preferencial para `landt` ainda nao esta fechada: opcao A derivar de `isfinite(STD)`/`isfinite(BATHY)`; opcao B usar `mask.out` da pasta de cenario.
- Sematica final de `AUVpredModel` versus `predModel` para baseline C4 ainda deve ser fixada por decisao de cenario.

## Inputs Em Falta
- Nao ha variavel `temperr` com esse nome no NetCDF C4.
- Nao ha variavel `tbath` com esse nome/convencao no NetCDF C4.
- Nao ha variavel `landt` direta no NetCDF C4.

## Riscos Para Correr O Baseline
- Risco critico 1: usar `BATHY` sem ajuste pode invalidar a mascara por profundidade (logica atual assume convencao especifica em `tbath`).
- Risco critico 2: sem `landt`, o mask terra-mar pode ficar inconsistente com o esperado pelo planner.
- Risco critico 3: sem `temperr` nomeado/formatado como esperado, o planner falha logo na leitura do input.
- Risco medio: diferenca de semantica entre `STD` (C4) e `temperr` historico (HOPS) pode alterar escala de premios dos nos.

## Proximo Passo Recomendado
1. Criar um unico ficheiro de preparacao de dados (fora do planner) que gere um `.nc` de interface baseline com campos: `temperr`, `tbath`, `landt`, `lat`, `lon`.
2. Alimentar esse ficheiro ao `OptimalPlanning.py` via argumento CLI, mantendo `MODEL_HOPS=True` e sem alterar custo/planner.
3. Registar no mesmo pacote de preparacao as regras de derivacao usadas (nome de variavel, sinal de batimetria, regra da mascara).

## Factos vs Inferencias
### Factos observados
- O planner le `temperr/lat/lon/tbath/landt` em `OptimalPlanning.py`.
- O NetCDF C4 escolhido contem `STD/BATHY/LAT/LON` e nao contem `temperr/tbath/landt`.
- `STD` e `BATHY` no C4 tem exatamente a mesma mascara de `NaN`.

### Inferencias provaveis
- `STD` e o melhor candidato para `temperr`.
- `landt` pode ser derivado de finitude de `STD/BATHY`.
- `tbath` provavelmente precisa de adaptacao de convencao para manter a mascara por profundidade coerente.

### Pontos ainda em aberto
- Confirmacao operacional da regra final de sinal para `tbath`.
- Escolha definitiva entre `AUVpredModel` e `predModel` para o baseline C4.
