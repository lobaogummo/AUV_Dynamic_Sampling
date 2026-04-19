# paperfaithful_executive_summary

1. Foi criada uma variante isolada `paperfaithful` sem quebrar o baseline.
2. O solver e a lógica PC-VRP central foram mantidos.
3. O pre-processamento paper-faithful agora aplica filtro Gaussiano (sigma 1,1).
4. A geração Voronoi foi ajustada para single-pass com restrição dmin.
5. A versão atual (legacy) foi preservada para comparação lado a lado.
6. O mapa `temperr` foi auditado semanticamente com reporte explícito.
7. O dataset usado oferece `STD` 2D, classificado como PLAUSIBLE EQUIVALENT.
8. Foram geradas figuras obrigatórias de raw/smoothed e POIs.
9. Foram geradas figuras obrigatórias de rotas current vs paper-faithful e overlay.
10. Foram geradas tabelas CSV/JSON de parâmetros e resultados comparativos.
11. O pipeline paper-faithful foi executado com sucesso.
12. O baseline current também foi reexecutado na nova pasta versionada.
13. A diferença de POIs entre variantes foi quantificada.
14. A diferença de clientes visitados e custo final foi quantificada.
15. Alterações foram classificadas por suporte no paper.
16. Julgamento final: HIGH FIDELITY para a nova variante.