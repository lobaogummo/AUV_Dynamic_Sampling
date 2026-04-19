# paperfaithful_alignment_report

## 1. Situação inicial
- Baseline já seguia núcleo do paper: contour + dmin + Voronoi + PC-VRP em duas fases.
- Diferenças relevantes identificadas: smoothing ausente no caminho ativo e Voronoi com duas passagens por threshold.

## 2. Diferenças encontradas face ao paper
- Gaussian smoothing: paper descreve explicitamente no pre-processamento.
- Voronoi: paper descreve construção V2 por Voronoi com dmin, sem thresholds adicionais explícitos.
- Semântica 2D de incerteza: dataset atual já fornece `STD` 2D; equivalência plausível.

## 3. Alterações implementadas
- Snapshot `planner_snapshot_paperfaithful` criado sem tocar no baseline.
- `APPLY_GAUSSIAN_FILTER=True`, `sigma=(1,1)` (REQUIRED TO MATCH PAPER).
- `VORONOI_MODE='paper_single_pass'` com dmin e sem threshold adicional (REQUIRED TO MATCH PAPER).
- Solver/VRP/função custo não alterados.

## 4. Evidência visual e quantitativa
- Ver diags `paperfaithful_diag_01` a `paperfaithful_diag_08`.
- Ver `paperfaithful_voronoi_comparison.csv`, `paperfaithful_before_after_summary.csv/json`.

## 5. Comparação baseline vs paper-faithful
- POIs current-voronoi (smoothed map): 418
- POIs paper-faithful-voronoi (smoothed map): 420
- Current visited clients (final): 43
- Paper-faithful visited clients (final): 43
- Current best cost final: 338773
- Paper-faithful best cost final: 289098

## 6. Limitações
- O paper não fixa `N_LEVELS`; escolha continua sendo de implementação.
- A semântica 2D por agregação em profundidade não é reproduzível exatamente com os campos disponíveis neste ficheiro.

## 7. Julgamento final de fidelidade
- Classificação final: **HIGH FIDELITY**
- A variante nova está mais fiel ao paper nos pontos metodológicos críticos (smoothing + Voronoi single-pass + preservação dmin).
- Diferenças remanescentes: moderadas e principalmente de disponibilidade/definição de dados de entrada.