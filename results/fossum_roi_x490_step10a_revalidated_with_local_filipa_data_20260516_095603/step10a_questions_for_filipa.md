# Questions For Filipa

- Can `write14days.m` and `runSimulations.m` be parameterized for arbitrary dates outside October?
- Is `thetao_20260427.nc` the intended CMEMS source for all 370 canonical days?
- Should Step10B use `TEMPpred(:,:,1)` or `TEMPpred(:,:,2)` when `outputDays = 2` for a target date?
- Are the current variogram values valid for all seasons/classes, or only for the October example?
- Is MATLAB Mapping Toolbox required for `projcrs/projfwd`, and is DSS.C.64.exe the correct executable for this PC?