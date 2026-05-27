# Required fixes before next planner step

1. Standardize figure backgrounds and captions: explicitly state STD, descriptor, information_map, TEMPpred, or region mask.
2. For Step11B, show actual blended information_map when discussing planner objective.
3. For Step11C/11D, use prototype-based masks from Step11Y/Step11Z when making methodological claims.
4. Keep coordinate plotting as ROI row/col with `origin='lower'`, or move fully to km extent; do not mix both in the same figure.
5. Treat old Step11C/11D region-mask outputs as exploratory where Step11Y identified fallback-derived masks.
