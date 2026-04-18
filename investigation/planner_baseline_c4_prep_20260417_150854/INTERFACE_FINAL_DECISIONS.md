# INTERFACE_FINAL_DECISIONS

## Objetivo
Fechar as decisoes finais da interface baseline para o planner da Lucrezia, sem alterar planner, funcao custo, grelha nativa, ou integracao de regimes/descriptors.

## Factos Observados
- O planner baseline consome diretamente: `temperr`, `lat`, `lon`, `tbath`, `landt`.
- Fonte baseline escolhida: `predModel` em `FILIPA_DADOS/data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc`.
- No `predModel` escolhido:
- `STD` tem shape `2 x 180 x 240` (dimensao extra `day`).
- `BATHY` tem shape `180 x 240` com valores positivos (`~0.79` a `~1052.06`).
- A grelha fisica e `LAT/LON` com shape `180 x 240`.

## Testes / Verificacoes Feitas

### 1) `STD` por indice `day`
- `STD[0]`: max `0.000716`, media `~0`, p95 `~0` (quase degenerado para score de incerteza).
- `STD[1]`: min `0.004632`, max `0.117726`, media `0.048587`, p95 `0.075626` (campo util para planeamento por incerteza).

### 2) Convencao de `tbath` com logica do planner
- Regra do planner: mascara quando `tbath > -MINIMUM_DEPTH` com `MINIMUM_DEPTH=40`.
- Se `tbath = +BATHY`: fracao mascarada estimada `~0.6974` (mascaramento excessivo, inconsistente com profundidade).
- Se `tbath = -BATHY`: fracao mascarada estimada `~0.0584` (comportamento fisicamente coerente: zonas rasas mascaradas, profundas mantidas).

### 3) Regra de `landt`
- `finitude(STD)` e `finitude(BATHY)` sao identicas pixel-wise.
- `mask.out` (na pasta Nazare) tem 129600 linhas (= `3 x 180 x 240`) com valores `{-1, 0}`:
- as 3 camadas sao identicas;
- `0` coincide com pixels validos (agua) e `-1` com invalidos (terra/fora).
- Como o planner espera `landt==0` para terra, `mask.out` bruto exigiria remapeamento adicional e nao traz ganho face a finitude direta no NetCDF.

## Decisao Final Adotada (Baseline)

### `STD -> temperr`
- Decisao: `temperr = STD[day_index=1]`.
- Justificacao tecnica: `day_index=1` preserva variabilidade de incerteza util ao objetivo baseline; `day_index=0` e praticamente nulo.

### `BATHY -> tbath`
- Decisao: `tbath = -BATHY`.
- Justificacao tecnica: alinha com a logica de mascara por profundidade do planner (`tbath > -MINIMUM_DEPTH`), evitando mascaramento indevido de quase toda a grelha.

### `landt`
- Decisao: `landt = 1` onde `isfinite(temperr)` e `isfinite(tbath)`, caso contrario `0`.
- Justificacao tecnica: regra simples, direta, alinhada ao contrato esperado pelo planner e consistente com as mascaras nativas do ficheiro C4.

## Estado
- Estas decisoes fecham os 3 pontos em aberto da interface baseline para o cenario C4 com `predModel`.
