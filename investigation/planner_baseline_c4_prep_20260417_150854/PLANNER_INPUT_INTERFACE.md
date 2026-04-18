# PLANNER_INPUT_INTERFACE

## Escopo
- Documento tecnico da interface minima de inputs do planner da Lucrezia, com base no codigo atual.
- Sem alteracoes no planner e sem alteracoes na funcao custo.

## Inputs Consumidos Diretamente Pelo Planner

| input_name | descricao | formato esperado | shape esperado | obrigatorio | onde aparece no codigo | observacoes |
|---|---|---|---|---|---|---|
| `file_name` | Caminho para ficheiro de entrada principal | argumento CLI | caminho valido para `.nc` | sim | `OptimalPlanning_Lucrezia/OptimalPlanning.py:98-105` | Sem este argumento o script termina (`sys.exit(1)`). |
| `temperr` | Mapa 2D de incerteza/erro usado para score | variavel NetCDF | 2D (`lat x lon`) | sim (modo baseline `MODEL_HOPS=True`) | `OptimalPlanning_Lucrezia/OptimalPlanning.py:109` | Campo principal para mascaras, POI e premios. |
| `lat` | Eixo de latitude da grelha | coord NetCDF 1D | `n_lat` | sim | `OptimalPlanning_Lucrezia/OptimalPlanning.py:112` | Usado para crop operacional e georreferencia de depots/POI. |
| `lon` | Eixo de longitude da grelha | coord NetCDF 1D | `n_lon` | sim | `OptimalPlanning_Lucrezia/OptimalPlanning.py:113` | Usado para crop operacional e georreferencia de depots/POI. |
| `tbath` | Batimetria 2D | variavel NetCDF | 2D (`lat x lon`) | sim | `OptimalPlanning_Lucrezia/OptimalPlanning.py:114` | Usada no mask por profundidade e depth ao longo das rotas. |
| `landt` | Mascara terra-mar | variavel NetCDF binaria | 2D (`lat x lon`) | sim | `OptimalPlanning_Lucrezia/OptimalPlanning.py:115` | `0` e tratado como terra. |
| `AUV_NUMBER` | Numero de veiculos | config python | escalar inteiro | sim | `OptimalPlanning_Lucrezia/Config_file.py:4`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:301-315` | Define numero de depots e vehicle types. |
| `SPEED` | Velocidade veiculo | config python | escalar (`m/s`) | sim | `OptimalPlanning_Lucrezia/Config_file.py:5`, `OptimalPlanning_Lucrezia/Utils.py:233-243` | Entra no calculo de max distance por missao. |
| `MISSION_DURATIONS` | Duracoes alvo por AUV | config python | lista tamanho `AUV_NUMBER` (horas) | sim | `OptimalPlanning_Lucrezia/Config_file.py:6`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:290-293` | Base dos limites de distancia no VRP. |
| `STARTING_POINTS` | Pontos de inicio dos AUVs (lat,lon) | config python | lista de pares | sim | `OptimalPlanning_Lucrezia/Config_file.py:9`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:268` | Convertidos para indices de grelha em `get_depots()`. |
| `ENDING_POINTS` | Pontos de fim/recovery dos AUVs (lat,lon) | config python | lista de pares | sim | `OptimalPlanning_Lucrezia/Config_file.py:10`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:268` | Mesmo tamanho logico de `STARTING_POINTS`. |
| `MINIMUM_DEPTH` | Limite minimo de profundidade navegavel | config python | escalar (`m`) | sim | `OptimalPlanning_Lucrezia/Config_file.py:13`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:178-182` | Aplicado como mascara sobre `temperr2d_op`. |
| `OPERATION_LL_CORNER`, `OPERATION_UR_CORNER` | Bounding box operacional | config python | dois pares `(lat,lon)` | sim | `OptimalPlanning_Lucrezia/Config_file.py:17-18`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:138-148` | Define subgrelha operacional onde o planner atua. |
| `OBJECTS_LL_CORNER`, `OBJECTS_UR_CORNER` | Obstaculos retangulares na area operacional | config python | listas de pares `(lat,lon)` | sim | `OptimalPlanning_Lucrezia/Config_file.py:23-24`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:185-203` | Viram mascaras `-inf` no mapa de planeamento. |
| `N_LEVELS`, `D_MIN_CONTOUR`, `D_MIN_VORONOI` | Parametros de selecao de POI | config python | escalares | sim | `OptimalPlanning_Lucrezia/Config_file.py:28-30`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:229-247` | Controlam densidade/dispersao dos clientes VRP. |
| `STOP_RUN_TIME`, `STOP_NO_ITER`, `SEED` | Parametros de paragem e reproducibilidade do solver | config python | escalares | sim | `OptimalPlanning_Lucrezia/Config_file.py:33-36`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:321,369-370` | Usados nas 2 corridas do VRP. |
| `HOPS_GRID_RESOLUTION` | Conversao fisica para distancia em celulas | config python | escalar (`m`) | sim | `OptimalPlanning_Lucrezia/Config_file.py:40`, `OptimalPlanning_Lucrezia/Utils.py:242,257` | Impacta limite de distancia por veiculo no VRP. |
| `MODEL_HOPS` | Se usa formato HOPS pronto (`True`) ou preprocessamento Model2 (`False`) | config python | booleano | sim | `OptimalPlanning_Lucrezia/Config_file.py:39`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:25,106-110` | Baseline atual assume `True`. |
| `WP_WAITING_TIME` | Tempo de espera por waypoint | config python | escalar (min) | sim (2a fase VRP) | `OptimalPlanning_Lucrezia/Config_file.py:7`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:344-346` | Ajusta duracao efetiva de viagem na corrida final. |
| `CLEAN_ROUTE`, `START_END_POINT_DISPLACEMENT` | Pos-processamento de waypoints | config python | booleano + escalar | opcional funcional | `OptimalPlanning_Lucrezia/Config_file.py:8,43`, `OptimalPlanning_Lucrezia/OptimalPlanning.py:398-409` | Nao altera o solver, altera apenas forma final da rota exportada. |

## Inputs Derivados / Preparados Antes Do Solver

| input_derivado | como e gerado | usado em | observacoes |
|---|---|---|---|
| `temperr2d_op` | Crop operacional + mascaras (land, depth, obstaculos) sobre `temperr` | selecao de POI e premio de nos | `OptimalPlanning.py:137-203` |
| `uncertain_points` / `uncertain_points_coord` | Contornos + filtragem por distancia + Voronoi | construcao dos nos VRP | `OptimalPlanning.py:232-247` e `Utils.py` |
| `node_prices` | Escalonamento de `temperr2d_op` nos nos | VRP prize collecting | `OptimalPlanning.py:280`, `Utils.py:165-191` |
| `node_distances` | Distancia euclidiana em indice de grelha com penalizacao por obstaculo | VRP distance matrix | `OptimalPlanning.py:283`, `Utils.py:211-221` |
| `VRP_instance_problem.vrp` | Ficheiro de instancia gerado a partir de nos/distancias/premios/depots | leitura pelo PyVRP | `OptimalPlanning.py:293-297`, `Utils.py:249-281` |
| `effective_travel_duration` | `MISSION_DURATIONS - waiting_time` por rota | 2a corrida VRP | `OptimalPlanning.py:344-346`, `Utils.py:323-342` |

## Nota Importante Sobre Distancia A Terra
- Existe logica para mask por `DISTANCE_FROM_LAND`, mas esta dentro de bloco comentado (`""" ... """`) em `OptimalPlanning.py:151-176`.
- No estado atual, os `.npy` de distancia a terra no repositorio nao sao consumidos no fluxo baseline executado.

## Distincao Direto vs Derivado
- Direto: ficheiro `.nc` de entrada + parametros em `Config_file.py`.
- Derivado: mapas mascarados, POI, matriz de distancias, ficheiro `.vrp` e rotas intermediarias/finais.
