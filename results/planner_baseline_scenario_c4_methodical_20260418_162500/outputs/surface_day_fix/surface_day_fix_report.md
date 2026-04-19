# surface_day_fix_report

## Goal
- Keep surface-only and force the prior model day file (`30-10-2024_predModel_1.nc`).

## Current source
- `C:\Users\pedro\Documents\Filipa_dados\data\TEST_C4\HighRes\Daily_dpt_20241030_NewTest_1\31-10-2024_predModel_1.nc`
- STD dims: `{'LAT': 180, 'LON': 240}`

## Required prior source
- `C:\Users\pedro\Documents\Filipa_dados\data\TEST_D4\HighRes\Daily_dpt_20241029_NewTest_1\30-10-2024_predModel_1.nc`
- exists: `True`
- required vars present (`STD`,`LAT`,`LON`,`BATHY`): `{'STD': True, 'LAT': True, 'LON': True, 'BATHY': True}`
- STD dims: `{'day': 2, 'LAT': 180, 'LON': 240}`
- STD ndim: `3`

## Decision
- status: `FOUND AND FIXED`
- note: Using `30-10-2024_predModel_1.nc` with one 2D day slice of STD (selected day index=1).

## STD day diagnostics (prior file)
- day=0: mean=0.000000, std=0.000004, min=0.000000, max=0.000716, finite_fraction=0.697407
- day=1: mean=0.048587, std=0.016968, min=0.004632, max=0.117726, finite_fraction=0.697407
- selected source: `C:\Users\pedro\Documents\Filipa_dados\data\TEST_D4\HighRes\Daily_dpt_20241029_NewTest_1\30-10-2024_predModel_1.nc`
- selected slice: `STD[day=1,LAT,LON]`
- interface generated: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\inputs\30-10-2024_surface_dayfix_planner_interface.nc`
- rules kept: `temperr = STD` (single 2D surface slice), `tbath = -BATHY`, no other pipeline changes.
- comparison figure: `C:\Users\pedro\Documents\Filipa_dados\results\planner_baseline_scenario_c4_methodical_20260418_162500\outputs\surface_day_fix\surface_day_comparison.png`