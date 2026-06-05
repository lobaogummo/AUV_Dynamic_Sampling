# Descriptor audit report

Audit date: 2026-06-05

Scope: current trajectory-planning descriptor pipeline for `boundary_score`, `representative_zone`, `interest_map`, `region_A`, `region_B`, plus boundary distance, contour, gradient, mask, dilation/erosion and distance-transform logic.

## Executive summary

- The final planner descriptors are computed in `scripts/08_build_final_descriptors_from_canonical_prototypes.py` and saved to `step08_all_descriptor_maps.npz`.
- Step11Y rebuilds planner-ready maps from Step08 by indexing the Step08 prototype descriptor stack with each case's predicted class. See `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py`.
- Step12 loads the Step11Y `prototype_based_all_planner_maps.npz` through `scripts/step12_common.py`.
- `TEMPpred` is not used as a descriptor objective in Step12. It is only a case/classification and diagnostic-background field.
- The planner receives a run-specific `information_map` as NetCDF variable `temperr`; Lucrezia's planner then converts `temperr` values at selected POIs into integer node prizes.
- Boundary distance inside Step08 is a Euclidean distance transform in grid cells/pixels, not metres and not lat/lon geodesic distance.
- Lucrezia's contour logic is not the descriptor computation. It selects POIs from the final `temperr` map and enforces POI spacing with geodesic distances in km.

## Main files

- Descriptor construction: `scripts/08_build_final_descriptors_from_canonical_prototypes.py`
- Prototype-based planner map rebuild: `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py`
- Region masks used by Step12: `scripts/11ab_c01_region_target_and_vehicle_weight_sweep.py`
- Common Step12 planner bridge: `scripts/step12_common.py`
- Single-AUV sensitivity: `scripts/12a_single_auv_weight_duration_sensitivity.py`
- Multi-AUV sensitivity: `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py`
- Planner NetCDF bridge: `scripts/11a_run_minimal_boundary_planner_comparison.py`
- Lucrezia planner POI/prize logic: `OptimalPlanning_Lucrezia/OptimalPlanning.py`, `OptimalPlanning_Lucrezia/Utils.py`

## Shared Step08 inputs

Step08 loads:

- `canonical_prototypes.npy`: normalized canonical prototype fields from Step05.
- `canonical_class_std_maps.npy`: per-class STD maps, if available.
- `mask_common_roi_x490.npy`: valid ROI mask.
- `LAT_roi_x490.npy`, `LON_roi_x490.npy`, `X_km_roi_x490.npy`, `Y_km_roi_x490.npy`: coordinate grids.
- Step07/CV regime labels for each prototype, used to choose `homogeneous`, `single_gradient`, or `multi_regime`.

Code references:

- Inputs loaded: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:807-825`
- Main per-class loop: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:868-927`
- Output NPZ: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:1075-1089`

## Gradient logic

File/function:

- `scripts/08_build_final_descriptors_from_canonical_prototypes.py:418`, `compute_gradient(...)`

Inputs:

- `field`: Step05 prototype field for one class.
- `valid`: common ROI mask intersected with finite prototype values.
- `x_km`, `y_km`: kilometre coordinate grids.

Operation:

```text
filled = field inside valid mask, invalid cells filled with valid mean
y_axis = mean axis from Y_km, fallback to row index if invalid
x_axis = mean axis from X_km, fallback to column index if invalid
gy, gx = np.gradient(filled, y_axis, x_axis)
gradient_magnitude = sqrt(gx^2 + gy^2)
gradient_direction = atan2(gy, gx)
```

Value type:

- Continuous.

Normalization:

- Final `gradient_map` is min-max normalized over valid cells with `minmax01(...)` at `scripts/08_build_final_descriptors_from_canonical_prototypes.py:875-877`.

Distance/unit:

- If `x_km/y_km` axes are valid, gradient is in normalized-temperature units per km. If not, it falls back to pixel/cell spacing.

## boundary_score

File/functions:

- Segmentation: `segment_cold_warm_neutral(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:475`
- Binary boundary: `boundary_mask_from_binary(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:499`
- Distance transform: `distance_to_boundary(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:517`
- Boundary score: `old_style_boundary_score(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:526`
- Main call: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:887-905`

Inputs:

- Prototype field `proto`.
- Gradient magnitude `grad_mag`.
- Valid ROI mask.
- Regime label (`multi_regime`, `single_gradient`, or `homogeneous`).

Operation:

For `multi_regime` classes:

```text
t = Otsu threshold on prototype values, fallback to mean
binary_labels = 0 if proto < t, 1 if proto >= t
boundary_mask = cells whose 4-neighbour label differs
dist = distance_transform_edt(~boundary_mask)
grad_norm = clip(grad_mag / p95(grad_mag_valid), 0, 1)
d75 = p75(dist_valid)
boundary_proximity = exp(-dist / d75)
boundary_score_raw = clip(0.65 * grad_norm + 0.35 * boundary_proximity, 0, 1)
boundary_score_norm = minmax01(boundary_score_raw over valid cells)
```

For `single_gradient` classes:

```text
high_grad_mask = grad_mag >= p90(grad_mag_valid)
boundary_mask = high_grad_mask, but distance is not used in the score
grad_norm = clip(grad_mag / p95(grad_mag_valid), 0, 1)
boundary_score_raw = clip(0.35 * grad_norm, 0, 1)
boundary_score_norm = minmax01(boundary_score_raw over valid cells)
```

For `homogeneous` classes:

```text
boundary_mask = all false
boundary_score_raw = 0 on valid cells
boundary_score_norm = 0 on valid cells
```

Value type:

- Continuous score in final planner maps.
- The intermediate `boundary_mask` is binary.

Normalization:

- `grad_norm`: percentile normalization by p95 inside `old_style_boundary_score`.
- `boundary_score_raw`: clipped to `[0, 1]`.
- Final `boundary_score_norm`: min-max normalized over valid cells.
- Step11Y applies `minmax01(...)` again when it extracts the predicted-class prototype map.

Distance/unit:

- `distance_transform_edt(~boundary)` uses array indices, so distance is in pixels/cells.
- It is nearest-boundary Euclidean distance in grid-cell space.
- It is not perpendicular distance to a fitted contour.
- It is not gradient-based distance, although gradient magnitude is blended into the score.
- It is not metres or lat/lon geodesic distance.

Mask/contour/dilation notes:

- Boundary mask uses 4-neighbour label changes via `np.roll`.
- No dilation or erosion is used in this final Step08 boundary computation.
- `binary_dilation` appears in older Step07 analysis, but not in the current final Step08 planner descriptor generation.

## representative_zone

File/function:

- `build_representative_zone_map(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:662`
- Main call: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:918`

Inputs:

- Prototype field `proto`.
- Normalized gradient map `grad_norm`.
- Normalized boundary map `boundary_norm`.
- Heterogeneity map `hetero`.
- Valid ROI mask.

Operation:

```text
med = median(proto_valid)
mad = median(abs(proto_valid - med))
scale = max(1.4826 * mad, 1e-6)
centrality = exp(-abs(proto - med) / scale)
calm = 1 - clip(0.4 * grad_norm + 0.3 * boundary_norm + 0.3 * hetero, 0, 1)
representative_zone = clip(centrality * calm, 0, 1)
```

Value type:

- Continuous.

Normalization:

- Step08 clips the map to `[0, 1]` but does not min-max normalize this map at creation.
- Step11Y extracts the predicted-class map and applies `minmax01(...)` over the case mask before planner use.

Distance/unit:

- No explicit spatial distance transform.
- "Distance" here is value distance from the prototype median, measured in normalized prototype-field units.

Interpretation:

- High values mark calm, central, low-gradient, low-boundary, low-heterogeneity zones.

## interest_map

File/operation:

- Weights declared at `scripts/08_build_final_descriptors_from_canonical_prototypes.py:53`
- Main operation at `scripts/08_build_final_descriptors_from_canonical_prototypes.py:920-927`

Inputs:

- `boundary_norm`
- `grad_norm`
- `hetero`

Operation:

```text
interest_raw = 0.4 * boundary_norm + 0.4 * grad_norm + 0.2 * heterogeneity
interest_raw[~valid] = NaN
interest_map = minmax01(interest_raw over valid cells)
```

Value type:

- Continuous.

Normalization:

- The weighted sum is min-max normalized over valid cells in Step08.
- Step11Y applies `minmax01(...)` again when extracting the predicted-class prototype map.

Distance/unit:

- No direct distance computation.
- It inherits boundary proximity indirectly through `boundary_norm`.

## Heterogeneity input used by interest_map

File/operation:

- Local variance function: `local_variance_map(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:545`
- Main operation: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:907-916`

Inputs:

- Prototype field `proto`.
- Class STD map `std_map`.
- Valid ROI mask.

Operation:

```text
local_var = uniform_filter(proto, 5)^2-style local variance
local_var_norm = minmax01(local_var)
roughness_raw = abs(laplace(proto_filled))
rough_norm = minmax01(roughness_raw)
std_norm = minmax01(class_std_map)
heterogeneity = mean(local_var_norm, rough_norm, std_norm)
```

Value type:

- Continuous.

Normalization:

- Components are min-max normalized; the final mean is in `[0, 1]` if all components are in `[0, 1]`.

Distance/unit:

- No boundary distance. Local variance uses a 5-cell window.

## cold_region and warm_region

File/operation:

- Segmentation: `segment_cold_warm_neutral(...)`, `scripts/08_build_final_descriptors_from_canonical_prototypes.py:475`
- Main cold/warm maps: `scripts/08_build_final_descriptors_from_canonical_prototypes.py:880-888`

Inputs:

- Prototype field `proto`.
- Valid ROI mask.
- Regime label.

Operation:

For all classes, Step08 creates three labels: cold/low, neutral, warm/high.

```text
default:
    p33, p67 = percentiles(proto_valid, 33.333 and 66.667)

if regime == multi_regime:
    t = Otsu threshold, fallback to mean
    p33 = median(values below t), if available
    p67 = median(values above/equal t), if available

label 0 cold: proto <= p33
label 1 neutral: p33 < proto < p67
label 2 warm: proto >= p67

cold_region = 1 where label == 0, 0 on other valid cells, NaN outside mask
warm_region = 1 where label == 2, 0 on other valid cells, NaN outside mask
```

Value type:

- Binary maps in Step08 (`0/1/NaN`).
- After Step11Y `minmax01(...)`, they remain effectively binary unless a degenerate map is constant.

Normalization:

- Saved by Step08 as binary maps.
- Step11Y applies min-max normalization per predicted class and case mask.

Distance/unit:

- No spatial distance transform.
- Segmentation thresholds are value thresholds in normalized prototype-field units.

## region_A and region_B

Important naming distinction:

- Step08 saves `cold_region` and `warm_region`.
- Step12 names the operational role masks `region_A` and `region_B`.
- In the common interpretation, `region_A` corresponds to cold/lower-regime structure and `region_B` to warm/higher-regime structure.

Files/functions:

- Step11Y full partition helper: `region_masks_from_cold_warm(...)`, `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py:212`
- Step12 mask helper: `descriptor_region_masks(...)`, `scripts/11ab_c01_region_target_and_vehicle_weight_sweep.py:112`
- Step12 calls: `scripts/12a_single_auv_weight_duration_sensitivity.py:319-321`, `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py:804-808`

Step12 mask operation:

```text
valid = mask & finite(cold) & finite(warm)
region_A = (cold >= 0.5) & (cold >= warm) & valid
region_B = (warm >= 0.5) & (warm > cold) & valid

if region_A has < 50 cells:
    threshold = p85(cold_valid)
    region_A = (cold >= threshold) & (cold >= warm) & valid

if region_B has < 50 cells:
    threshold = p85(warm_valid)
    region_B = (warm >= threshold) & (warm > cold) & valid

if still empty:
    fallback to p95 non-exclusive threshold for that map
```

Value type:

- `region_A_mask` and `region_B_mask` are binary masks.
- The role maps entering Step12B information maps are usually the continuous/binary `cold_region_norm` and `warm_region_norm`, not the final mask files.

Normalization:

- Region masks are boolean.
- `cold_region_norm` and `warm_region_norm` are already Step11Y-normalized maps.

Distance/unit:

- No distance calculation.
- Selection is based on descriptor values and thresholds.

## boundary_core

Files/functions:

- Step12 common helper: `boundary_core(...)`, `scripts/step12_common.py:245`
- Similar Step11Y helper: `boundary_core(...)`, `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py:205`
- Step12B call: `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py:805`

Operation:

```text
thr = p90(boundary_score_valid)
boundary_core = boundary_score >= thr within valid mask
```

Step11Y additionally keeps the largest connected component. Step12 common simply returns the p90 mask.

Value type:

- Binary mask.

Normalization:

- Thresholded from normalized `boundary_score_norm`.

Distance/unit:

- No new distance computation.

## Step11C crossing proxy distance logic

This is not a base descriptor from Step08, but it is trajectory-planning reward-map shaping and uses a distance transform.

File/function:

- `build_crossing_proxy(...)`, `scripts/11c_single_auv_boundary_crossing_reward.py:251`

Inputs:

- `boundary_score_norm`
- `region_A`
- `region_B`
- `boundary_core`
- Valid mask

Operation:

```text
dist_to_core = distance_transform_edt(~boundary_core)
scale = max(p25(dist_to_core inside mask), 3.0)
boundary_proximity = exp(-dist_to_core / scale)
side_band = (region_A or region_B) and dist_to_core <= max(4.0, scale)
core = boundary_core
raw = 0.55 * boundary_proximity + 0.30 * side_band + 0.15 * core
crossing_proxy = minmax01(raw over mask)
```

Value type:

- Continuous map after min-max normalization.

Distance/unit:

- `distance_transform_edt` is in pixels/cells.
- It is nearest-core Euclidean distance in grid-cell space.

Where it enters planner:

- `make_information_maps(...)`, `scripts/11c_single_auv_boundary_crossing_reward.py:276`
- Formula used there:

```text
baseline_STD = STD_norm
boundary_alpha050 = 0.5 * STD_norm + 0.5 * boundary_score_norm
crossing_gamma = 0.5 * STD_norm
               + 0.3 * boundary_score_norm
               + 0.2 * ((1 - gamma) * boundary_score_norm + gamma * crossing_proxy)
```

## Step12A information maps

File:

- `scripts/12a_single_auv_weight_duration_sensitivity.py`

Descriptor keys:

- `boundary_score -> boundary_score_norm`
- `representative_zone -> representative_zone_norm`
- `interest_map -> interest_map_norm`

Code references:

- Descriptor mapping: `scripts/12a_single_auv_weight_duration_sensitivity.py:26-30`
- Formula stored in manifest: `scripts/12a_single_auv_weight_duration_sensitivity.py:64`
- Map construction: `scripts/12a_single_auv_weight_duration_sensitivity.py:331-339`

Formula:

```text
if alpha == 0:
    information_map = STD_norm
else:
    information_map = normalize_map((1 - alpha) * STD_norm + alpha * descriptor_norm)
```

Normalization:

- The mixture is min-max normalized over the Step12 valid mask with `step12_common.normalize_map(...)`.

## Step12B information maps

File:

- `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py`

Base weights:

- `vehicle_specific_9010`: `0.90 STD + 0.10 region`
- `vehicle_specific_8020`: `0.80 STD + 0.20 region`
- `vehicle_specific_7030`: `0.70 STD + 0.30 region`
- `vehicle_specific_6040`: `0.60 STD + 0.40 region`
- `vehicle_specific_5050`: `0.50 STD + 0.50 region`
- `vehicle_specific_2575`: `0.25 STD + 0.75 region`
- `vehicle_specific_00100`: `0.00 STD + 1.00 region`

Code references:

- Weights: `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py:31-39`
- Build map: `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py:345`
- Initial role maps: `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py:822-893`
- Role swap maps: `scripts/12b_multi_auv_vehicle_specific_weight_duration_sensitivity.py:958-985`

Formula:

```text
build_map(std, role_map, boundary, mask, w_std, w_region, w_boundary):
    information_map = normalize_map(w_std * std + w_region * role_map + w_boundary * boundary)

normal role assignment:
    AUV1 role_map = cold_region_norm / region_A logic
    AUV2 role_map = warm_region_norm / region_B logic

role swap:
    AUV1 role_map = warm_region_norm
    AUV2 role_map = cold_region_norm
```

Boundary-support optional formula:

```text
AUV1 = 0.60 * STD_norm + 0.30 * cold_region_norm + 0.10 * boundary_score_norm
AUV2 = 0.60 * STD_norm + 0.30 * warm_region_norm + 0.10 * boundary_score_norm
```

Normalization:

- Every Step12B vehicle map is min-max normalized by `step12_common.normalize_map(...)`.

## Step11Y prototype-based map rebuild

File:

- `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py`

Purpose:

- Ensures planner maps come from Step08 prototype descriptors selected by the predicted class, instead of being recomputed directly from `TEMPpred`.

Code references:

- Step08 descriptor extraction: `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py:324`
- Rebuild loop: `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py:340-381`
- Output NPZ: `scripts/11y_audit_and_rebuild_prototype_based_planner_inputs.py:606-620`

Operation:

```text
descriptor_map_for_case = Step08_descriptor_stack[predicted_class - 1]
descriptor_map_for_case = minmax01(descriptor_map_for_case over mask)
STD_norm = minmax01(day_specific_STD over mask)
```

Saved arrays include:

- `baseline_STD_norm`
- `boundary_score_norm`
- `gradient_norm`
- `heterogeneity_norm`
- `cold_region_norm`
- `warm_region_norm`
- `representative_zone_norm`
- `interest_map_norm`
- `enriched_boundary_alpha025`
- `enriched_boundary_alpha050`
- `AUV1_region_map`
- `AUV2_region_map`

## How descriptors enter Lucrezia's planner

Bridge file/function:

- `build_interface_nc(...)`, `scripts/11a_run_minimal_boundary_planner_comparison.py:192`
- Step12 wrapper call: `run_planner(...)`, `scripts/step12_common.py:283`

Operation:

```text
temperr = embed_roi_to_hres(information_roi, mask_roi, fill=-inf)
NetCDF variable "temperr" = temperr
NetCDF also includes "tbath", "landt", "lat", "lon"
```

Planner entry:

- `OptimalPlanning.py` reads `temperr` when `MODEL_HOPS=True`.
- Audit reference in code: `scripts/11a_run_minimal_boundary_planner_comparison.py:515-538`

Lucrezia POI and prize logic:

- Contours are built over the final `temperr` map, not over raw descriptors.
- `OptimalPlanning_Lucrezia/OptimalPlanning.py:238-262`:

```text
max_level = max(finite temperr)
min_level = min(finite temperr)
step_level = (max_level - min_level) / N_LEVELS
contour_points = get_contour_levels(temperr, max, min, step)
POIs = find_POI_on_contour_levels(D_MIN_CONTOUR, ...)
additional POIs = Voronoi vertices above uncertainty thresholds
```

- `OptimalPlanning_Lucrezia/Utils.py:19`, `get_contour_levels(...)` uses `plt.contour(...)`.
- `OptimalPlanning_Lucrezia/Utils.py:63`, `find_POI_on_contour_levels(...)` rounds contour coordinates to nearest grid index and enforces spacing using `geopy.distance.geodesic(...).km`.
- `OptimalPlanning_Lucrezia/Utils.py:101`, `additional_POI_inside_contour_levels(...)` adds Voronoi vertices if map value exceeds a threshold and spacing is at least `D_MIN`.
- `OptimalPlanning_Lucrezia/Utils.py:165`, `get_nodes_prize(...)` converts map values at nodes to integer prizes.

Prize operation:

```text
valid_map = finite map values excluding -inf
range = max(valid_map) - min(valid_map)
decimal_number = ceil(-log10(range / 1000)), if range > 0
multiplicative_factor = 10 ** decimal_number
node_prize = int(multiplicative_factor * temperr[node_row, node_col])
depot prizes = 0
```

Distance units inside Lucrezia:

- POI spacing (`D_MIN_CONTOUR`, `D_MIN_VORONOI`) is geodesic distance in km.
- Node distance matrix uses Euclidean distance in grid index units, with obstacles set to a huge distance. See `OptimalPlanning_Lucrezia/Utils.py:221-231`.
- Vehicle max route distance is converted from mission duration, speed and `HOPS_GRID_RESOLUTION` into grid-step units. See `OptimalPlanning_Lucrezia/Utils.py:243-252` and `OptimalPlanning_Lucrezia/Config_file.py:40`.

## Dilation, erosion, distance-transform inventory

Current final planner descriptor path:

- `distance_transform_edt` in Step08 boundary score: yes, nearest boundary in cells.
- `distance_transform_edt` in Step11C crossing proxy: yes, nearest boundary core in cells.
- `binary_dilation`: not used in final Step08/Step12 descriptor path.
- `binary_erosion`: not found in the final Step08/Step12 descriptor path.
- Contours: used by Lucrezia planner for POI selection from final `temperr`; not used to compute Step08 descriptors.
- Gradient: used in Step08 `boundary_score`, `gradient_map`, `representative_zone`, and `interest_map`.

Historical/non-final notes:

- `scripts/prototype_characterization_utils.py` has an older/parallel descriptor characterization implementation with similar region, distance-transform and boundary-score functions. It is useful lineage, but Step08 final planner outputs are generated by `scripts/08_build_final_descriptors_from_canonical_prototypes.py`.
- `scripts/07_cv_analysis_canonical_fossum_roi_x490.py` uses `ndi.binary_dilation(...)` in analysis logic, but that is not the current final planner-map construction.

## Descriptor-by-descriptor compact table

| Descriptor | Computed in | Inputs | Formula summary | Binary/continuous | Normalized | Distance unit |
|---|---|---|---|---|---|---|
| `boundary_score` | Step08 `old_style_boundary_score` | prototype, gradient, regime boundary mask | multi: `0.65*grad_norm + 0.35*exp(-dist/d75)`; single-gradient: `0.35*grad_norm`; homogeneous: 0 | continuous final; binary intermediate boundary mask | p95 gradient, p75 distance proximity, final minmax; Step11Y minmax again | boundary distance in pixels/cells |
| `representative_zone` | Step08 `build_representative_zone_map` | prototype, grad, boundary, heterogeneity | `exp(-abs(proto-med)/scale) * calm` | continuous | clipped `[0,1]`; Step11Y minmax | no spatial distance |
| `interest_map` | Step08 main loop | boundary, gradient, heterogeneity | `0.4*boundary + 0.4*gradient + 0.2*heterogeneity` | continuous | Step08 minmax; Step11Y minmax | inherits boundary cell distance indirectly |
| `cold_region` | Step08 segmentation | prototype, regime label | cold/low class from tertiles or Otsu-guided tertiles | binary | Step11Y minmax | no distance |
| `warm_region` | Step08 segmentation | prototype, regime label | warm/high class from tertiles or Otsu-guided tertiles | binary | Step11Y minmax | no distance |
| `region_A` | Step11Y/Step12 from cold/warm | cold_region_norm, warm_region_norm | cold-dominant mask / role map | binary mask; role map can be 0/1 continuous array | mask boolean; role maps Step11Y-normalized | no distance |
| `region_B` | Step11Y/Step12 from cold/warm | cold_region_norm, warm_region_norm | warm-dominant mask / role map | binary mask; role map can be 0/1 continuous array | mask boolean; role maps Step11Y-normalized | no distance |
| `crossing_proxy` | Step11C | boundary_core, region_A/B | `0.55*exp(-dist/scale)+0.30*side_band+0.15*core` | continuous | minmax | distance to boundary core in pixels/cells |

## Conclusions

1. The current Step12 planner descriptors are prototype-based and come from Step08 via Step11Y.
2. `boundary_score` is not a pure geometric distance-to-boundary map. It is a blended score: gradient intensity plus exponential proximity to a boundary mask for multi-regime classes.
3. Boundary distance is nearest-boundary Euclidean distance in grid cells, not metres/lat-lon and not perpendicular distance to a fitted contour.
4. `representative_zone` is a calm-centrality descriptor, not a boundary descriptor.
5. `interest_map` is a weighted composite of boundary, gradient and heterogeneity.
6. `region_A` and `region_B` are operational role masks/maps derived from Step08 `cold_region` and `warm_region`; they are not computed from `TEMPpred` in the current Step12 path.
7. Lucrezia's contour logic is downstream of the descriptor maps: it samples POIs from whatever `information_map` was written as `temperr`.
