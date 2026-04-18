# run_report

## Interface File
- path: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\inputs\30-10-2024_predModel_1_planner_interface.nc`
- source: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\data\Test_C4\Priori_Nazare_30-10-2024_1\30-10-2024_predModel_1.nc`

## Required Fields
- required_vars_present: `True`
- present_vars: `['landt', 'lat', 'lon', 'tbath', 'temperr']`

## Shapes
- temperr: `[180, 240]`
- tbath: `[180, 240]`
- landt: `[180, 240]`
- lat: `[180]`
- lon: `[240]`

## Ranges and Validity
- landt sea fraction: `0.697407`
- landt land fraction: `0.302593`
- temperr finite fraction: `0.697407`
- tbath finite fraction: `0.697407`
- landt matches temperr finite: `True`
- landt matches tbath finite: `True`

## Expected Planner Crop (native logic)
- OPERATION_LL_CORNER: `[39.50934, -9.4352]`
- OPERATION_UR_CORNER: `[39.75313, -9.03402]`
- indices: lat_start=46, lat_stop=138, lon_start=46, lon_stop=195
- expected shape: `92 x 149`

## Artifacts
- summary table: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\outputs\validation\interface_summary.csv`
- checks: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\outputs\validation\checks.json`
- figures: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\outputs\validation\figures`
