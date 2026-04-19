# SPATIAL_REPRESENTATION_BASELINE

## Decision (step 4)
- Baseline was executed in the native spatial representation expected by Lucrezia planner.
- No forced regridding to external descriptors/regimes/tempIBHRes grids.

## Representation used
- Global input grid to planner interface: `180 x 240` (`lat/lon` physical axes from C4 NetCDF).
- Operational subgrid used internally by planner:
  - `OPERATION_LL_CORNER = [39.50934, -9.43520]`
  - `OPERATION_UR_CORNER = [39.75313, -9.03402]`
  - resulting index window: `lat 46..137`, `lon 46..194`
  - effective shape: `92 x 149`

## Why this is defensible
- It preserves planner-native assumptions and avoids introducing geometric bias from external remapping.
- It isolates this baseline objective: prove controlled planner execution and interpretable outputs before any coupling.

## What was intentionally not changed
- No change to planner objective/cost behavior.
- No change to contour/POI logic.
- No change to compact model, descriptors, clustering, prototypes, or planner research pipeline.

