# Step10B Not Created Reason

Step10B was not created/executed as an automatic generator because the local ready outputs do not cover C01/C06 dates and the available generation scripts are MATLAB/DSS scripts with hardcoded paths/date ranges.

Blocking items:
- MATLAB on PATH: False
- DSS executable found: True
- `write14days.m` is hardcoded to `I:\dadosParaPedro_Fresnel` and October output paths.
- `runSimulations.m` is hardcoded to `I:\dadosParaPedro_Fresnel`, `01.Data\October\HRes`, and `predDate = datetime('2024-10-30') + dayDate - 1`.
- C01/C06 selected dates are outside October and have no ready HRes/predModel outputs.