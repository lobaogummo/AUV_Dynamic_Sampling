# Boundary Distance Descriptor Pipeline Report

## Purpose

This change keeps the existing `boundary_score` descriptor and adds explicit boundary-distance descriptors for planner sensitivity tests.

The goal is to separate three ideas that were previously easy to mix:

- old blended boundary/front score;
- raw nearest-boundary distance;
- radius-based boundary proximity bands.

## Old Blended Boundary Score

The existing `boundary_score` is not a pure distance-to-boundary map.

For `multi_regime` prototype classes it uses the cold/warm boundary mask, but the final score blends gradient intensity and boundary proximity:

```text
boundary_score = clip(0.65 * grad_norm + 0.35 * exp(-distance_cells / p75(distance_cells)), 0, 1)
```

For `single_gradient` classes it is a high-gradient proxy. For `homogeneous` classes it is zero.

## Pure Boundary Distance

The new raw distance maps are:

```text
boundary_distance_cells = nearest-boundary Euclidean distance in ROI grid cells
boundary_distance_km = nearest-boundary Euclidean distance in km, when X_km/Y_km spacing is reliable
```

The distance transform is computed in the prototype ROI grid using `scipy.ndimage.distance_transform_edt`.

## Radius-Based Boundary Score

The new reward-like score maps are:

```text
boundary_distance_score_r{radius}_cells =
    exp(-(boundary_distance_cells ** 2) / (2 * radius ** 2))
```

Radii tested:

```text
1, 2, 3, 5, 8 cells
```

Cells on the boundary have score close to 1. Nearby cells decay smoothly. Distant cells approach 0.

## Pipeline Entry Points

- Step08 computes and saves the new maps in `step08_all_descriptor_maps.npz`.
- Step11Y extracts them by predicted prototype class and min-max normalizes them over the valid planner mask.
- Step12A can use `boundary_distance_score_r*_cells_norm` in the same alpha sweep:

```text
information_map = normalize((1 - alpha) * STD_norm + alpha * descriptor_norm)
```

Lucrezia's VRP/orienteering objective is not changed. The new descriptors only change the pre-planner `information_map` written as NetCDF `temperr`.
