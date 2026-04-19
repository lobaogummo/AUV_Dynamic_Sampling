# PLANNER_INPUT_INTERFACE

## Scope
- This table documents the minimum runnable interface used by `OptimalPlanning_Lucrezia/OptimalPlanning.py` in baseline mode.
- Focus: required inputs only, before any future coupling with custom maps/regimes.

## Minimal input table

| input | current file/source | format | required? | notes |
|---|---|---|---|---|
| `file_name` (CLI arg) | `results/planner_baseline_scenario_c4_methodical_20260418_162500/inputs/31-10-2024_predModel_1_planner_interface.nc` | NetCDF path | yes | script exits if missing |
| `temperr` | same interface `.nc` (`temperr`) | 2D float (`lat x lon`) | yes | primary uncertainty/value map used for POI and prize |
| `tbath` | same interface `.nc` (`tbath`) | 2D float (`lat x lon`) | yes | used by minimum depth mask and route depth report |
| `landt` | same interface `.nc` (`landt`) | 2D int/binary (`lat x lon`) | yes | `0=land`, `1=sea` |
| `lat` | same interface `.nc` (`lat`) | 1D float | yes | monotonic increasing |
| `lon` | same interface `.nc` (`lon`) | 1D float | yes | monotonic increasing |
| `AUV_NUMBER` | `OptimalPlanning_Lucrezia/Config_file.py` | int | yes | vehicle count used in solver setup |
| `SPEED` | `OptimalPlanning_Lucrezia/Config_file.py` | float (m/s) | yes | used to derive max route length |
| `MISSION_DURATIONS` | `OptimalPlanning_Lucrezia/Config_file.py` | list[hours] | yes | one per vehicle |
| `STARTING_POINTS` | `OptimalPlanning_Lucrezia/Config_file.py` | list[(lat,lon)] | yes | depot starts |
| `ENDING_POINTS` | `OptimalPlanning_Lucrezia/Config_file.py` | list[(lat,lon)] | yes | depot ends |
| `OPERATION_LL_CORNER`, `OPERATION_UR_CORNER` | `OptimalPlanning_Lucrezia/Config_file.py` | two coordinate pairs | yes | operational crop is computed from these |
| `MINIMUM_DEPTH` | `OptimalPlanning_Lucrezia/Config_file.py` | float (m) | yes | mask rule: `tbath > -MINIMUM_DEPTH` |
| `OBJECTS_LL_CORNER`, `OBJECTS_UR_CORNER` | `OptimalPlanning_Lucrezia/Config_file.py` | list of obstacle boxes | yes | obstacle cells forced to `-inf` in map |
| `N_LEVELS`, `D_MIN_CONTOUR`, `D_MIN_VORONOI` | `OptimalPlanning_Lucrezia/Config_file.py` | numeric | yes | controls POI generation density |
| `STOP_RUN_TIME`, `STOP_NO_ITER`, `SEED` | `OptimalPlanning_Lucrezia/Config_file.py` | numeric | yes | solver stop/reproducibility |
| `WP_WAITING_TIME` | `OptimalPlanning_Lucrezia/Config_file.py` | minutes | yes | second solve adjusts route limit with waiting time |
| `HOPS_GRID_RESOLUTION`, `MODEL_HOPS` | `OptimalPlanning_Lucrezia/Config_file.py` | numeric/bool | yes | baseline here uses `MODEL_HOPS=True` |

## Notes on optional/non-critical artifacts
- `VRP_instance_problem.vrp`, `routes_file_node_estimation.txt`, `routes_file.txt`, and plot PNG are generated outputs, not required startup inputs.
- Distance-from-land `.npy` assets are not used in the active path because that block is commented in the current planner file.

