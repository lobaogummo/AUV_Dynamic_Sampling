# Step10A Revalidation With Local Filipa Data

- Filipa root: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\data\dadosParaPedro_Fresnel\dadosParaPedro_Fresnel`
- C01 count: 41
- C06 count: 72
- Total C01+C06: 113
- October C01/C06 rows: 0
- Local data inventory rows: 616
- Local script inventory rows: 13
- Strong scripts: 2
- MATLAB available on PATH: False
- DSS executable found: True
- Automatic pilot generation now: NO

## Interpretation
The local repository now contains the original Filipa data tree, including raw `thetao_20260427.nc`, October HRes windows, October predModel outputs, MATLAB scripts, and the DSS executable. However, the selected C01/C06 dates are outside October, while ready HRes/predModel outputs are only materialized for 2024-09-30 to 2024-11-02.

Generating C01/C06 pilot outputs therefore requires adapting/running the Filipa MATLAB pipeline: first create HRes 14-day windows from the 370-day CMEMS file, then run DSS simulations and write `predModel_N.nc` files with `TEMPpred` and `STD`.

## Strong Scripts
- `data\dadosParaPedro_Fresnel\dadosParaPedro_Fresnel\00.Code\runSimulations.m`: Runs DSS geostatistical simulations and writes predModel_N.nc with TEMPpred/STD; currently October/hardcoded paths.
- `data\dadosParaPedro_Fresnel\dadosParaPedro_Fresnel\00.Code\write14days.m`: Builds 14-day CMEMS windows and interpolates them to HRes; currently October/hardcoded paths.

## Pilot Dates
- 2024-07-03 C01: REQUIRES_WRITE14DAYS_PLUS_MATLAB_DSS_ADAPTATION
- 2024-07-04 C01: REQUIRES_WRITE14DAYS_PLUS_MATLAB_DSS_ADAPTATION
- 2023-12-22 C06: REQUIRES_WRITE14DAYS_PLUS_MATLAB_DSS_ADAPTATION
- 2023-12-17 C06: REQUIRES_WRITE14DAYS_PLUS_MATLAB_DSS_ADAPTATION

Final verdict: **STEP10A_REVALIDATED_WITH_LOCAL_DATA / NEEDS_FILIPA_SCRIPT_OR_INPUTS**