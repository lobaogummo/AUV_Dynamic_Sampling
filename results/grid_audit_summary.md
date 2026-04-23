# grid_audit_summary

- conclusion: **GRID MISMATCH FOUND**
- official_planning_grid: `planner_interface_c4_full (and its operational crop from Config_file corners)`
- official_grid_path: `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\inputs\30-10-2024_predModel_1_planner_interface.nc`

## Key findings

- tempIBHRes native grid is indexed and 3D: `64x112x300` (y,x,z).
- Planner interface grid is geospatial lat/lon: `180x240` (y,x).
- Planner operational crop is `92x149` using Config LL/UR corners.
- Direct spatial transfer from tempIBHRes to planner is not physically guaranteed without explicit georeferencing transform.
- Under project display assumption (linear map via HRes bbox), extents are compatible, but cell resolution and indexing still differ.

## Generated outputs

- `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\grid_audit_report.md`
- `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\grid_audit_summary.md`
- `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\grid_audit_stats.csv`
- `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\grid_extent_overlay.png`
- `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\grid_resolution_comparison.png`
