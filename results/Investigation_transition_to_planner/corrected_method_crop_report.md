# Corrected Method Crop Report

## Objective
This report corrects and expands the previous visual comparison between `CAND_B` and `USER_DIRECT_KM` without changing planner scientific logic.

## Day And Reference
- Day used (same as previous comparison): `2024-10-30` (source: `summary:results/candb_vs_userdirect_summary.md`)
- Existing tempRes PNG set used as primary full-day reference: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes`
- Selected reference image: `results/plots/deterministic_2024_surface_300_thesis_indexed_axes/TEMP_surface_2024_z300.png`
- Day-to-z mapping convention: `DOY_TO_Z_CLIPPED_MAX` (`day-of-year=304 exceeds z_max=300; clipped to z=300.`)
- Output full-day image: `results/temperature_full_day_tempres.png`

## Domain Choice For Method Crops
- Method crops were generated in the **planner-compatible HRes domain** (planner interface grid).
- This is methodologically the most consistent operational option for linking regimes/descriptors to planning inputs.
- Temperature crops were generated on the tempRes indexed grid for the same day and mapped using documented linear lon/lat normalization.

## Generated Visual Outputs
- `results/temperature_full_day_tempres.png` (full tempRes day reference from existing PNG set)
- `results/candb_hres_crop.png` and `results/userdirect_hres_crop.png` (method crops in planner-compatible HRes domain)
- `results/candb_temperature_crop.png` and `results/userdirect_temperature_crop.png` (same-day temperature crops in tempRes domain)
- `results/candb_planner_crop.png` and `results/userdirect_planner_crop.png` (planner-domain method crops)
- `results/comparison_panel_temperature_methods.png`
- `results/comparison_panel_hres_methods.png`
- `results/comparison_panel_all.png`

## Grid Mapping And Orientation
- No orientation inversion was applied in array-based figures (`origin=lower` used explicitly).
- Cross-domain mapping applied for tempRes method crops: linear lon/lat normalization from planner-compatible full bbox to tempRes indexed grid.
- Mapping note: Linear lon/lat normalization from planner-compatible full bbox to tempRes indexed grid (112x64 equivalent), preserving bbox corner order.

## Visual Differences Between Methods
- Planner-domain IoU (`CAND_B` vs `USER_DIRECT_KM`): `0.2837`
- TempRes-domain IoU (`CAND_B` vs `USER_DIRECT_KM`): `0.3064`
- Planner center-distance in cells: `40.215`
- TempRes center-distance in cells: `15.914`
- `CAND_B` planner crop shape: `67x128`; `USER_DIRECT_KM` planner crop shape: `72x134`
- `CAND_B` temp crop shape: `26x60`; `USER_DIRECT_KM` temp crop shape: `26x63`

## Tables And Checks
- Metrics table: `results/method_crop_metrics.csv`
- Bounding boxes table: `results/method_crop_bboxes.csv`
- Detailed checks and provenance: `results/method_crop_checks.json`

## Conclusion
- The corrected comparison now includes the full-day tempRes image for `2024-10-30` from the existing 300-image set,
- plus both temperature-domain and planner-compatible HRes/planner-domain method crops for `CAND_B` and `USER_DIRECT_KM`.
