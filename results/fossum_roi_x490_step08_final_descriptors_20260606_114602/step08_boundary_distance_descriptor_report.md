# Step08 Boundary Distance Descriptor Report

## Purpose
The previous `boundary_score` is retained unchanged, but it is a blended front score rather than a pure distance descriptor. This report documents the new explicit boundary-distance maps.

## Old blended boundary score
`boundary_score` combines gradient intensity with boundary proximity for multi-regime classes:

```text
boundary_score = clip(0.65 * grad_norm + 0.35 * exp(-distance_cells / p75(distance_cells)), 0, 1)
```

For homogeneous classes it is zero; smooth gradients are not treated as boundaries.

## Pure distance-to-boundary maps
`boundary_distance_cells` is the raw nearest-boundary Euclidean distance computed by `scipy.ndimage.distance_transform_edt` on the existing boundary mask.
`boundary_distance_km` is saved only when `X_km`/`Y_km` spacing is regular enough; otherwise it remains NaN and metadata marks the conversion as unavailable.

## Radius/band boundary scores
For each radius in cells, the new score maps are:

```text
boundary_distance_score_r{radius}_cells = exp(-(boundary_distance_cells ** 2) / (2 * radius ** 2))
```

Radii tested in cells: [1, 2, 3, 5, 8].

These are reward-like proximity bands: cells on the boundary have score near 1, nearby cells decay smoothly, and far cells approach 0.

## Regime-specific boundary mask source
- `multi_regime`: cold/warm Otsu boundary mask.
- `homogeneous`: no boundary; score maps are zero over valid cells.

## Planner use
Step11Y extracts these maps by predicted prototype class and Step12A can use the `boundary_distance_score_r*_cells_norm` maps in the same alpha sweep as the existing descriptors.
Lucrezia's planner objective is not changed; these maps only change the `information_map` written as NetCDF `temperr`.