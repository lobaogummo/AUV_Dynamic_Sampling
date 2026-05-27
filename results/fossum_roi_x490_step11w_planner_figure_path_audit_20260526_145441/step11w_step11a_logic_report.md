# Step11A logic report

Step11A ran baseline_STD and enriched_boundary_alpha025/alpha050 over the three Step10F cases. The planner information map was written to each planner-interface NetCDF as `temperr` and documented in `step11a_run_manifest.csv`.

The figures show paths over TEMPpred/STD/boundary diagnostic backgrounds. This is reliable for path comparison, but captions should not imply that every panel background is the exact objective.

Coordinate alignment is consistent: route lat/lon is converted to HRes row/col and plotted as ROI col/row over `imshow(origin='lower')`.

For thesis use, prefer barplots and regenerated standardized overlays with explicit background labels.
