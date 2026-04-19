# BASELINE_PLANNER_WORKING_STATE

## Baseline status
- Status: `WORKING` for the controlled scenario.
- Final planner execution exit code: `0`.
- Output root:
`results/planner_baseline_scenario_c4_methodical_20260418_162500`

## Scenario frozen for baseline
- Scenario: `TEST_C4_HighRes_31-10-2024_INST1_predModel_BASELINE`
- Interface file:
`results/planner_baseline_scenario_c4_methodical_20260418_162500/inputs/31-10-2024_predModel_1_planner_interface.nc`

## Commands used
1. Build interface and validation:
`python results/planner_baseline_scenario_c4_methodical_20260418_162500/build_planner_interface.py`
2. Preplanner sanity checks:
`python results/planner_baseline_scenario_c4_methodical_20260418_162500/preplanner_sanity.py`
3. Baseline planner run (snapshot, Agg backend):
`python OptimalPlanning.py <interface_nc_abs_path>`

## Generated outputs (key)
- Preplanner diagnostics:
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/validation/preplanner_sanity.md`
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/validation/preplanner_sanity.json`
- Planner results:
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/planner_run/routes_file.txt`
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/planner_run/routes_file_node_estimation.txt`
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/planner_run/VRP_instance_problem.vrp`
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/planner_run/20260418T171719Z_wt.png`
`results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/planner_run/run_report.md`

## Baseline run metrics (final)
- End-to-end elapsed runtime: `587.768 s`
- Final solver objective: `338773`
- Final solver iterations: `29385`
- Solver reported runtime (2nd solve): `228.42 s`
- Route count: `2`
- Route 1: `18.961 km`, mission `5h30m`, minimum depth `129.347 m`
- Route 2: `40.683 km`, mission `11h40m`, minimum depth `151.489 m`
- Aggregated uncertainty signal:
`Total WP Routes Temperr = 4.756237`
`Total All Routes Temperr = 40.82792`

## Compatibility notes (kept isolated)
- The repository planner core was not modified in-place.
- Two compatibility fixes were applied only to `planner_snapshot/OptimalPlanning.py` under the scenario output folder:
  - `VehicleType(..., capacity=[0], ...)` for PyVRP API compatibility in this environment.
  - Windows-safe timestamp for final plot filename.
- These fixes do not change objective/cost formulation; they only address runtime/API/platform compatibility.

