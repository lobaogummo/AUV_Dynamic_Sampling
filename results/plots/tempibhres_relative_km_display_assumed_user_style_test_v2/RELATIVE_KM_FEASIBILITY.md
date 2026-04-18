# Relative-km Feasibility (tempIBHRes)

## Conclusion
- Relative-km axes are technically possible for display.
- In current repo state, spacing is not independently validated from tempIBHRes native metadata.
- This output therefore uses a display-derived assumption from HRes bbox mapping.

## Axes Used
- X: `x`
- Y: `y`
- Unit tag: `km`
- Figure tag: `a)`

## Method
- Source bbox from `results/netcdf_files_summary.csv` (HRes row).
- Converted deg-per-cell to km-per-cell at midpoint latitude.
- Built relative axes from origin `(0,0)` plus optional axis offsets.
- Cropped grid: x=1..63, y=1..43 (1-based).

## Key Parameters
- dx_km_per_cell: `0.494184`
- dy_km_per_cell: `0.832215`
- x_extent_km: `0.000000 .. 54.854386`
- y_extent_km: `0.000000 .. 52.429515`

## Methodological Safety
- Relative-km axes are display-derived from local HRes bounding-box mapping and are not independently verified native georeferencing of tempIBHRes.
