# contours_voronoi_validation_report

## 1. Mapa usado
- Variante prioritária: `paper-faithful`.
- Mapa efetivo para POI: `temperr2d_poi (paper-faithful): masked operational map + Gaussian smoothing`.
- Shape operacional: `92 x 149`.

## 2. Como os contour levels foram calculados
- Implementação usada no planner:
  - `max_level = map.max()`
  - `min_level = np.nanmin(map[map != -np.inf])`
  - `step_level = (max_level - min_level) / N_LEVELS`
  - `levels = np.arange(min+step, max+step, step)` com arredondamento por resolução decimal do mapa.
- Valores nesta validação: `N_LEVELS=9`, `min=0.022556`, `max=0.125993`, `step=0.011493`.
- Avaliação: uso de `N_LEVELS` está coerente e aplicado sobre o mapa correto da geração de grafo.

## 3. Como V1 foi gerado
- `V1` vem dos pontos das contour lines, aproximados por `round()` aos índices de grelha.
- Regra `dmin` aplicada por distância geodésica em km (`D_MIN_CONTOUR`).
- Contagem observada: `V1=353`.
- Avaliação face ao paper: coerente com Fig. 3 e Eq. (5) (pontos ao longo das curvas + dmin).

## 4. Como V2 foi gerado
- Voronoi calculado sobre `V1` (geradores).
- Vértices candidatos filtrados por:
  - área válida (`is_inside_op_area`),
  - threshold de incerteza (`UNC_TRESHOLD`)
  - regra `dmin` (`D_MIN_VORONOI`).
- Em paper-faithful foi usado `UNC_TRESHOLD = -inf` (single-pass), equivalente a não impor threshold adicional.
- Contagem observada: `V2=67`.

## 5. Se a implementação está correta face ao paper
- Contours: **corretamente implementados**.
- V1: **corretamente implementado** (amostragem nas curvas + `dmin`).
- Voronoi/V2 paper-faithful: **corretamente implementado** para aderência ao paper (single-pass com `dmin`).

## 6. Pontos de atenção / divergências
- `current` usa duas passagens Voronoi por thresholds (legacy), enquanto o paper descreve lógica single-pass de V2 sobre V1.
- Parâmetros atuais: `D_MIN_CONTOUR=1`, `D_MIN_VORONOI=1` (coerentes com dmin=1 km descrito no paper).

## Conclusão objetiva
- `contours implementados`: **corretamente**.
- `Voronoi implementado`: **corretamente na paper-faithful** / **parcialmente na current (legacy thresholded two-pass)**.