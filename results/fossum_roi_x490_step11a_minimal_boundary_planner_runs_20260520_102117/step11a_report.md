# Step11A Minimal Boundary Planner Runs - 12h 2 AUV

- Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11a_minimal_boundary_planner_runs_20260520_102117`
- Runtime: 2 AUVs, 12h each
- Config: `AUV_NUMBER = 2`, `MISSION_DURATIONS = [12, 12]`
- Successful runs: 9/9
- Failed runs: 0/9
- Verdict: **STEP11A_COMPLETED_BASELINE_VS_BOUNDARY_RESULTS_READY**

## Run Metrics
- C06_representative / baseline_STD: SUCCESS, waypoints=53, length=74.928 km, mission_duration_sum=21.68 h, collected boundary=231.392, collected STD=186.493
- C06_representative / enriched_boundary_alpha025: SUCCESS, waypoints=52, length=75.157 km, mission_duration_sum=21.72 h, collected boundary=240.641, collected STD=185.223
- C06_representative / enriched_boundary_alpha050: SUCCESS, waypoints=49, length=74.836 km, mission_duration_sum=21.58 h, collected boundary=267.944, collected STD=180.049
- C01_representative / baseline_STD: SUCCESS, waypoints=48, length=74.358 km, mission_duration_sum=21.43 h, collected boundary=230.794, collected STD=161.418
- C01_representative / enriched_boundary_alpha025: SUCCESS, waypoints=49, length=74.222 km, mission_duration_sum=21.42 h, collected boundary=233.872, collected STD=154.943
- C01_representative / enriched_boundary_alpha050: SUCCESS, waypoints=43, length=75.393 km, mission_duration_sum=21.65 h, collected boundary=222.253, collected STD=145.074
- October_control / baseline_STD: SUCCESS, waypoints=44, length=76.099 km, mission_duration_sum=21.85 h, collected boundary=57.943, collected STD=177.815
- October_control / enriched_boundary_alpha025: SUCCESS, waypoints=45, length=76.266 km, mission_duration_sum=21.92 h, collected boundary=59.996, collected STD=174.060
- October_control / enriched_boundary_alpha050: SUCCESS, waypoints=35, length=73.557 km, mission_duration_sum=21.00 h, collected boundary=180.130, collected STD=117.347

## Baseline vs Enriched
- C06_representative / enriched_boundary_alpha025: overlap=0.172, delta boundary=9.250, delta STD=-1.271
- C06_representative / enriched_boundary_alpha050: overlap=0.094, delta boundary=36.553, delta STD=-6.444
- C01_representative / enriched_boundary_alpha025: overlap=0.124, delta boundary=3.078, delta STD=-6.475
- C01_representative / enriched_boundary_alpha050: overlap=0.109, delta boundary=-8.541, delta STD=-16.344
- October_control / enriched_boundary_alpha025: overlap=0.093, delta boundary=2.053, delta STD=-3.755
- October_control / enriched_boundary_alpha050: overlap=0.015, delta boundary=122.187, delta STD=-60.468

## Note
- `mission_duration_h` in metrics is summed across the two AUV routes; values near 21-22h correspond to about 10.5-11h per AUV, including waypoint waiting time.