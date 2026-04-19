# run_notes

## Purpose
- Controlled baseline execution of Lucrezia planner for one fixed TEST_C4 scenario.
- No change to scientific objective/cost logic.

## Scenario
- `TEST_C4_HighRes_31-10-2024_INST1_predModel_BASELINE`
- Source NetCDF:
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_predModel_1.nc`
- Interface generated at:
`inputs/31-10-2024_predModel_1_planner_interface.nc`

## Spatial policy
- Keep planner-native grid and operational crop logic from `Config_file.py`.
- Expected operational shape confirmed: `92 x 149`.

## Outputs
- Validation artifacts in `outputs/validation/`.
- Planner artifacts in `outputs/planner_run/`.
- Snapshot of planner code used for execution in `planner_snapshot/`.

## Important compatibility trace
- Execution was isolated in `planner_snapshot/` to avoid touching official planner outputs.
- Snapshot-only compatibility edits were required for this environment:
  - PyVRP vehicle type capacity argument.
  - Windows-safe plot filename timestamp.

