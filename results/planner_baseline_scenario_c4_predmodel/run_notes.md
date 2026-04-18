# run_notes

## Cenario escolhido
- `TEST_C4_NAZARE_30-10-2024_INST1_BASELINE`
- Baseline com fonte `predModel` (nao `AUVpredModel`).

## Ficheiro-fonte usado
- `FILIPA_DADOS/data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc`

## Grelha de entrada
- Grelha fisica nativa C4: `180 x 240` (`lat/lon` 1D fisicos).
- Sem regridding externo nesta fase.

## Subgrelha operacional esperada
- Crop nativo do planner via `OPERATION_LL_CORNER/OPERATION_UR_CORNER`.
- Shape esperada com a logica atual: `92 x 149`.

## Objetivo desta etapa
- Preparar ficheiro de interface para o planner correr sem alteracoes de codigo.
- Nao alterar planner, nao alterar funcao custo, nao integrar regimes/descriptors nesta fase.
