# preplanner_sanity

Verificacao rapida do pre-processamento espacial/mask do planner, aplicada ao ficheiro de interface gerado (sem correr solver e sem alterar planner).

## Resultado
- shape operacional: `92 x 149`
- celulas finitas apos `landt`: `11863 / 13708`
- celulas finitas apos mascara de profundidade (`MINIMUM_DEPTH=40`): `11005 / 13708`
- celulas finitas apos obstaculos: `10750 / 13708`
- `temperr2d_op` final (finitas): min `0.007738`, max `0.098472`, media `0.045017`

## Conclusao
- O mapa operacional nao colapsa para vazio apos as mascaras.
- O ficheiro de interface esta coerente para avancar para o Passo 7 (execucao baseline do planner).
