# Step12A Parallelization Report

## Safety Audit

Parallel Step12A execution is safe when each physical planner run has a unique `physical_run_id`.

The current Step12 bridge writes each independent run to isolated paths:

- NetCDF input: `planner_inputs/<short_hash>.nc`
- Planner runtime copy: `planner_runs/<short_hash>/`
- Runtime config: `planner_runs/<short_hash>/Config_file.py`
- Lucrezia scripts copied per run: `planner_runs/<short_hash>/OptimalPlanning.py`, `planner_runs/<short_hash>/Utils.py`
- Planner logs: `planner_runs/<short_hash>/planner_stdout.txt`, `planner_runs/<short_hash>/planner_stderr.txt`
- Route output: `planner_runs/<short_hash>/routes_file.txt`

The original Lucrezia planner directory and objective are not modified. Figures and CSV summaries are still generated after all planner runs finish, so they remain sequential and collision-free.

The main unsafe point was thread-based execution around NetCDF/runtime setup. The Step12 common wrapper already noted that NetCDF writing is not reliably thread-safe on Windows. Step12A now uses process-based parallelism only when explicitly requested with `--parallel`.

## Changes Made

Changed only:

```text
scripts/12a_single_auv_weight_duration_sensitivity.py
```

Added:

```text
--parallel
--n-workers
--max-workers
--parallel-backend process
```

Kept:

```text
--skip-existing
--dry-run
--workers
```

`--workers` is now treated as a legacy alias for worker count, but parallel execution requires `--parallel`. Sequential execution remains the default.

Independent planner tasks are executed with `concurrent.futures.ProcessPoolExecutor`. Each worker loads the planner helper modules and high-resolution grids inside its own process, then runs one isolated planner directory.

## Failure Isolation

If a process fails, Step12A records that run as failed and continues collecting the other runs. Outputs include:

```text
step12a_solver_diagnostics.csv
step12a_failure_summary.csv
```

## Commands Used

Dry-run smoke test:

```powershell
python scripts\12a_single_auv_weight_duration_sensitivity.py --cases C01_representative --durations 12 --descriptors boundary_distance_score_r3_cells --parallel --n-workers 2 --dry-run
```

Real smoke test:

```powershell
python scripts\12a_single_auv_weight_duration_sensitivity.py --cases C01_representative --durations 12 --descriptors boundary_distance_score_r3_cells --parallel --n-workers 2
```

Full comparison:

```powershell
python scripts\12a_single_auv_weight_duration_sensitivity.py --cases C01_representative --durations 12 --descriptors boundary_score boundary_distance_score_r1_cells boundary_distance_score_r3_cells boundary_distance_score_r5_cells interest_map --parallel --n-workers 3 --skip-existing
```

## Smoke Test Result

Output:

```text
results\fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260605_151133
```

Result:

```text
logical_rows = 5
physical_runs = 5
workers = 2
failed_runs = 0
solver statuses = 5 SUCCESS
figures_created = 12
total_script_runtime_s = 721.40
```

The smoke test completed successfully. The command wrapper timed out at almost the same moment the script finished, but the Step12A output contains final checks, reports, metrics, diagnostics, and figures.

## Full Comparison Result

Output:

```text
results\fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260605_152501
```

Result:

```text
logical_rows = 25
physical_runs = 21
workers = 3
failed_runs = 0
solver statuses = 21 SUCCESS
figures_created = 45
total_script_runtime_s = 1747.17
verdict = STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED
```

Descriptors tested:

```text
boundary_score
boundary_distance_score_r1_cells
boundary_distance_score_r3_cells
boundary_distance_score_r5_cells
interest_map
```

## Recommended Worker Count

Recommended maximum for this machine:

```text
--n-workers 3
```

Use `--n-workers 2` for safer interactive work. Use `--n-workers 3` for batch execution. I do not recommend more than 3 without a separate CPU/RAM stress check because each worker launches a full Lucrezia planner subprocess.
