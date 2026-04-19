# contours_voronoi_validation_summary

1. Figura principal gerada em paper-faithful com mapa + contours + V1 + V2.
2. Contours calculados com max/min/step e `N_LEVELS` como no pipeline.
3. V1 validado: pontos ao longo das curvas com `dmin` geodésico.
4. Voronoi validado: aplicado sobre V1 e filtrado por área válida + `dmin`.
5. V2 paper-faithful usa single-pass (`UNC_TRESHOLD=-inf`) para aderir ao paper.
6. Legacy current mantém two-pass thresholded (divergência moderada face ao paper).
7. Conclusão contours: corretamente implementados.
8. Conclusão Voronoi: corretamente implementado na paper-faithful.
9. Output principal: `diag_contours_voronoi_validation.png`.
10. Output opcional: `diag_contours_only_validation.png`.