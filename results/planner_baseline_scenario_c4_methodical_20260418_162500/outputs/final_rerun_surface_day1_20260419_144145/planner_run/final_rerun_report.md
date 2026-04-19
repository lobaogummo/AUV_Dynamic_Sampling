# final_rerun_report

## Input used
- source file: `C:\Users\pedro\Documents\Filipa_dados\data\TEST_D4\HighRes\Daily_dpt_20241029_NewTest_1\30-10-2024_predModel_1.nc`
- source type: `predModel` (a priori), no AUVpredModel fallback
- surface policy: `surface-only`
- slice used: `STD[day=1,LAT,LON]`
- tbath transform: `tbath = -BATHY`
- interface file: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\inputs\30-10-2024_surface_day1_planner_interface.nc`

## Audit context
- day=1 was selected by numeric/visual evidence (day=0 nearly null), not by explicit semantic metadata in NetCDF.

## Planner execution
- command: `python OptimalPlanning.py C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\inputs\30-10-2024_surface_day1_planner_interface.nc`
- planner workspace: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_snapshot`
- exit code: `0`
- elapsed seconds: `1008.879767`
- stdout/stderr log: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\planner_stdout_surface_day1_final.log`
- runtime file: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\planner_runtime_surface_day1_final.txt`

## Core outputs
- routes file: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\routes_file_surface_day1_final.txt`
- node estimation routes file: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\routes_file_node_estimation_surface_day1_final.txt`
- VRP instance file: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\VRP_instance_problem_surface_day1_final.vrp`
- final plot: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\planner_plot_surface_day1_final.png`

## Final metrics
- candidate clients: `420`
- visited points (final): `46`
- final objective: `1987866`
- number of routes: `2`

## Comparison vs previous baseline
- comparison json: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\final_rerun_comparison.json`
- comparison csv: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\final_rerun_surface_day1_20260419_144145\planner_run\final_rerun_comparison.csv`
- candidate clients: baseline `433` vs rerun `420`
- visited points: baseline `43` vs rerun `46`
- objective: baseline `338773` vs rerun `1987866`
- routes: baseline `2` vs rerun `2`
- visual note: Rerun plot is visually cleaner (single colorbar, no overlay artifacts) and uses 420 candidate points; route geometry shifts with one compact blue route near central-west and one longer orange route covering broader western/central area.

## Execution status
- success: `True`