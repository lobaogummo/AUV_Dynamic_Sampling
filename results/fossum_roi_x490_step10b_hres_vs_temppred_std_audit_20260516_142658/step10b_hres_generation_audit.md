# Step10B HRes Generation Audit

## A. CMEMS -> HRes

- Python script: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\cmems_370_surface_to_hres_20260509_135642\interpolate_cmems_370_surface_to_hres.py`
- Output folder: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\cmems_370_surface_to_hres_20260509_135642`
- MATLAB used: **No**. The script is pure Python using `netCDF4`, `numpy`, `pandas`, `scipy.interpolate.RegularGridInterpolator`, and matplotlib for figures.
- It reproduces the HRes part of `write14days.m`: crop around the Fresnel operational box, 4-cell margin, `inc=10`, and linear interpolation on the same index grid as MATLAB `interp2`.
- Output shape: `[370, 180, 240]`.
- Validation against Filipa October HRes: RMSE 0.0, MAE 0.0, Pearson 1.0 on 2024-10-10, 2024-10-13, 2024-10-31.
- It covers all 370 dates from `2023-10-28` to `2024-10-31`.

## B. C01/C06 Pilot Availability

All 4 pilot dates already exist in the Python HRes output, in ROI x490, and in Step00 raw/normalized arrays. None has ready Filipa predModel/TEMPpred/STD.

| date | class_label | hres_180x240_available_in_python_output | roi_x490_72x117_available | step00_raw_roi_available | TEMPpred_STD_exists_for_date | predmodel_existing_depth_count |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-07-03 | C01_frontal | True | True | True | False | 0 |
| 2024-07-04 | C01_frontal | True | True | True | False | 0 |
| 2023-12-22 | C06_mixed | True | True | True | False | 0 |
| 2023-12-17 | C06_mixed | True | True | True | False | 0 |

## C. HRes vs TEMPpred/STD

- `thetao_surface_370_hres` is CMEMS surface temperature interpolated to the Filipa 180x240 grid.
- `TEMPpred` is the geostatistical prediction/median written after DSS simulations in `runSimulations.m`/`giveCoordinateInformation_naza.m`.
- `STD` is uncertainty/variance from the DSS simulation realizations (`readoutput_AUV.m`).
- Therefore, STD does **not** come from CMEMS -> HRes interpolation alone.

## D. MATLAB/DSS Boundary

- `write14days.m` is essentially the HRes preparation layer. Its HRes surface logic has already been reproduced in Python.
- `runSimulations.m` is the layer that prepares GSLIB/DSS inputs, calls `DSS.C.64.exe`, reads 100 realizations, computes median/STD, and writes `predModel_N.nc`.
- `DSS.C.64.exe` can likely be called directly from Python, but Python must first reproduce the MATLAB prep/read/write functions: `grid2gslib`, `writealldata_naza`, `parFileDSS`, `readoutput_AUV`, `giveCoordinateInformation_naza`, plus NetCDF writing.

## Recommendation

**Option 1**: Nao precisamos de MATLAB para HRes; ja temos HRes/ROI para C01/C06. Mas ainda precisamos de MATLAB/DSS ou de uma reimplementacao Python validada para TEMPpred/STD.
