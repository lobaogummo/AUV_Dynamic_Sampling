# preplanner_sanity

Verificacao rapida do pre-processamento espacial/mask do planner, aplicada ao ficheiro de interface gerado (sem alterar planner).

## Resultado
- shape operacional: `92 x 149`
- celulas finitas apos land/invalid mask: `11863 / 13708`
- celulas finitas apos mascara de profundidade (`MINIMUM_DEPTH=40`): `11005 / 13708`
- celulas finitas apos obstaculos: `10750 / 13708`
- `temperr2d_op` final (finitas): min `0.016734`, max `0.158887`, media `0.075889`

## Checks adicionais
- depots fora de terra (landt): `True`
- depots em celulas finitas apos todas as mascaras: `True`
- monotonia eixos lat/lon: `lat=True`, `lon=True`

## Conclusao
- O baseline so deve avancar para corrida do planner se `final_map_not_empty=True` e todos os depots forem validos.
