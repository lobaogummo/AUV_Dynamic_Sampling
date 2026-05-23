# Step11A Minimal Boundary Planner Runs

- Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11a_minimal_boundary_planner_runs_20260519_195804`
- Successful runs: 8/9
- Timeout/failed runs: 1/9
- Verdict: **STEP11A_COMPLETED_WITH_OVERLAY_TRAJECTORIES_REVIEW_PARAMETERS**

## Planner Interface
- Information map: NetCDF variable `temperr`.
- Objective: maximize prize/value derived from `temperr` POIs via `Utils.get_nodes_prize()`.
- Baseline/enriched maps are swapped by writing different `temperr` maps.
- MODEL_HOPS=True.

## Run Metrics
- C06_representative / baseline_STD: SUCCESS, waypoints=13, length=19.139 km, collected boundary=66.266, collected STD=46.155, runtime=271.4s
- C06_representative / enriched_boundary_alpha025: SUCCESS, waypoints=13, length=19.085 km, collected boundary=65.969, collected STD=44.653, runtime=252.3s
- C06_representative / enriched_boundary_alpha050: SUCCESS, waypoints=13, length=18.737 km, collected boundary=72.155, collected STD=48.046, runtime=214.2s
- C01_representative / baseline_STD: SUCCESS, waypoints=13, length=18.833 km, collected boundary=58.940, collected STD=36.723, runtime=271.4s
- C01_representative / enriched_boundary_alpha025: SUCCESS, waypoints=14, length=18.763 km, collected boundary=59.826, collected STD=37.636, runtime=223.5s
- C01_representative / enriched_boundary_alpha050: SUCCESS, waypoints=13, length=17.633 km, collected boundary=53.214, collected STD=32.097, runtime=228.7s
- October_control / baseline_STD: TIMEOUT, waypoints=10, length=17.985 km, collected boundary=13.542, collected STD=42.382, runtime=900.0s
- October_control / enriched_boundary_alpha025: SUCCESS, waypoints=9, length=18.427 km, collected boundary=14.396, collected STD=47.292, runtime=221.4s
- October_control / enriched_boundary_alpha050: SUCCESS, waypoints=13, length=18.904 km, collected boundary=37.564, collected STD=31.700, runtime=223.6s

## Baseline vs Enriched
- C06_representative / enriched_boundary_alpha025: overlap=0.108, delta boundary=-0.297, delta STD=-1.501
- C06_representative / enriched_boundary_alpha050: overlap=0.082, delta boundary=5.889, delta STD=1.891
- C01_representative / enriched_boundary_alpha025: overlap=0.144, delta boundary=0.886, delta STD=0.913
- C01_representative / enriched_boundary_alpha050: overlap=0.072, delta boundary=-5.726, delta STD=-4.626
- October_control / enriched_boundary_alpha025: overlap=0.140, delta boundary=0.854, delta STD=4.910
- October_control / enriched_boundary_alpha050: overlap=0.007, delta boundary=24.022, delta STD=-10.683

## Warnings
- October_control / baseline_STD reached timeout after 900 s, but route outputs were present and metrics were computed; rerun this one with longer timeout before treating it as final.
- Single-AUV runtime used first original AUV start/end/duration as requested for the first round.