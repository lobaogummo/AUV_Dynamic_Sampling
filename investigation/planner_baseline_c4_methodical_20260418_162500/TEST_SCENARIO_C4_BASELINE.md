# TEST_SCENARIO_C4_BASELINE

## Scenario identity
- Scenario name: `TEST_C4_HighRes_31-10-2024_INST1_predModel_BASELINE`
- Date: `2024-10-31`
- Depth/layer used by planner baseline: `2D uncertainty layer (STD over LAT/LON)` from the selected NetCDF.
- Main goal: run Lucrezia planner baseline without changing clustering/prototypes/compact model/descriptors/planner cost function.

## Fixed grid and spatial frame
- Grid source: `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_predModel_1.nc`
- Native grid: `LAT x LON = 180 x 240`
- Latitude range: `39.38888931274414 .. 39.86111068725586`
- Longitude range: `-9.55555534362793 .. -8.916666984558105`

## Input files fixed for this baseline
- Uncertainty/value map source: `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_predModel_1.nc`
- Reference mask file: `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/mask.out`
- Scene support files:
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/scene_1.gslib`
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/scene_2.gslib`
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/scene_3.gslib`
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/StDev.gslib`
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/Median.gslib`
`data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/Bath.gslib`

## Main planning variable and uncertainty map
- Planner uncertainty field (`temperr`) is built from NetCDF `STD`.
- Baseline interface file created:
`results/planner_baseline_scenario_c4_methodical_20260418_162500/inputs/31-10-2024_predModel_1_planner_interface.nc`

## Mask/obstacles fixed
- Land/sea mask (`landt`) built as:
`landt = 1 where finite(STD) and finite(-BATHY), else 0`
- Bathymetry field (`tbath`) built as:
`tbath = -BATHY`
- Obstacles and operation box are taken from:
`OptimalPlanning_Lucrezia/Config_file.py`

## Vehicles and depot settings fixed
- Number of AUVs: `2` (`AUV_NUMBER=2`)
- Starts:
`[39.57331662, -9.29314]`
`[39.57644, -9.29321]`
- Ends:
`[39.57331662, -9.29314]`
`[39.57644, -9.29321]`
- Mission durations: `[6, 13]` hours

## Objective for this phase
- Execute baseline planner behavior on a single controlled scenario.
- No change to planner objective/cost logic.
- Keep outputs isolated in a versioned folder for traceability.

