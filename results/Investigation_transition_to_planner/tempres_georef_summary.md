# tempRes Georeference Summary

- status: `TRANSFORMATION PLAUSIBLE BUT NOT PROVEN`
- tempRes native grid: `112 x 64 x 300` with columns `x,y,z,temp`
- planner official grid: `results/planner_baseline_scenario_c4_predmodel/inputs/30-10-2024_predModel_1_planner_interface.nc`
- planner resolution: dx=229.52 m/cell, dy=292.90 m/cell; shape=240x180
- tempRes display-mapped resolution (HRes bbox assumption): dx=494.18 m/cell, dy=832.21 m/cell
- georeference_native_proven: `false`
- strongest_supported_mapping: `registration-derived tempRes -> HRes sub-area`
- note: mapping is plausible and auditable as an inferred transform, not as recovered native CRS metadata.

A tempRes pode ser alinhada de forma plausivel com a grelha do planner, mas nao pode ser alinhada de forma auditavelmente provada com a evidencia atual.

- generated_files:
  - `results/tempres_georef_report.md`
  - `results/tempres_georef_summary.md`
  - `results/tempres_georef_evidence_index.csv`
  - `results/tempres_georef_candidate_transforms.csv`
  - `results/tempres_georef_checks.json`
  - `results/tempres_georef_candidate_overlay_1.png`
  - `results/tempres_georef_candidate_overlay_2.png`
