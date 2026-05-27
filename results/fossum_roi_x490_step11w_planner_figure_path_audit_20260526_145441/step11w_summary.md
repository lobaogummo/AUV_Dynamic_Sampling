# Step11W planner figure/path lineage audit

Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11w_planner_figure_path_audit_20260526_145441`
Figures inventoried: 124
Regenerated diagnostic figures: 16
Coordinate check warnings: 0
Verdict: `FIGURE_AUDIT_FOUND_MISLEADING_BACKGROUND_REGENERATE`

## Main conclusions

- Step11A: planner used baseline STD and STD+boundary formulations recorded in the manifest. Existing figures are diagnostic multi-background overlays, not a single exact-objective plot in every panel.
- Step11B: descriptors were used in the objective for non-baseline runs. The saved `step11b_information_maps_by_descriptor.npz` is direct evidence. Some figures can look like STD because they use common/diagnostic backgrounds rather than the exact blended information_map.
- Step11C: the crossing proxy should be interpreted with region-colored paths. A high crossing_count can reflect short A/B switches near the boundary, not necessarily broad exploration of both regimes.
- Step11D: max computed exact-cell overlap=0.000; mostly same-zone/visual if below 0.05. The main issue is regime specialization and attraction to similar value zones, not necessarily literal overplotting.
- Coordinate audit: the source scripts consistently use ROI row/col coordinates over `imshow(..., origin='lower')` with no extent. No systematic x/y swap or extent bug was detected unless individual rows in the coordinate CSV say otherwise.
- Prototype-based correction: Step11Y/Step11Z remain the preferred methodological reference for region masks; old Step11C/11D region-mask figures should be labelled exploratory if they used fallback-derived masks.

## Recommended figure use

- Use metric barplots and regenerated standardized panels for thesis figures.
- Use original Step11B descriptor panels only with captions saying the background is diagnostic; use regenerated information_map panels to explain the actual objective.
- Use original Step11D overlays as diagnostics; pair them with overlap/distance metrics before claiming path overlap.
