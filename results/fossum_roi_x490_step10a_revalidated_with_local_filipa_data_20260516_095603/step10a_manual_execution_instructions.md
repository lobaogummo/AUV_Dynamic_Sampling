# Step10A Manual Execution Instructions

1. Adapt `write14days.m` so `File`, `outputDataPath`, `outputHresPath`, and the date loop are parameters.
2. For each pilot date D, create the same HRes input window expected by `runSimulations.m`.
3. Adapt `runSimulations.m` so `ProjP`, `DataPath`, `predDate`, and `dayDate` are parameters.
4. Run only the selected pilot dates first, not all 113 C01/C06 dates.
5. Validate that each generated `predModel_1.nc` contains `TEMPpred`, `STD`, `LAT`, `LON`, and `BATHY`.
6. After predModels exist, run a Step10B extraction/ROI script to crop to x490 and produce `[N,72,117]` arrays.