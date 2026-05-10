# CMEMS 370 Surface To HRes Report

Output folder: `C:\Users\pedro\Documents\Filipa_dados\results\cmems_370_surface_to_hres_20260509_135642`

## MATLAB Inspection Notes

- `write14days.m` downloads/reads `thetao_20260427.nc`, writes moving 14-day October windows to `01.Data/October/CMEMSGrid`, then converts those files to HRes.
- The HRes conversion crops the CMEMS grid around `OPERATION_LL_CORNER = [39.50955, -9.43575]` and `OPERATION_UR_CORNER = [39.75365, -9.03419]`, expands each side by 4 source cells, and uses `inc=10`.
- For each depth/time, MATLAB builds index grids and calls `interp2(..., linspace(..., size*inc))`; this Python script reproduces that as linear interpolation on source index coordinates.
- The crop is 18 latitude cells x 24 longitude cells, yielding the canonical 180 x 240 target grid.


## Inputs

- Raw CMEMS file: `C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\01.Data\ALL\thetao_20260427.nc`
- Target grid source file: `C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\02.Simulations\HighRes\Daily_dpt_20240930\01-10-2024_predModel_1.nc`
- Depth: index `1`, value `0.494025` m
- Source shape: `(370, 17, 78, 120)`
- Target shape: `(180, 240)`
- Output shape: `(370, 180, 240)`

## Validation

| date | rmse | mae | max_abs_error | pearson | shape_match | orientation_match | n_compare |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-10-10 | 0.0 | 0.0 | 0.0 | 1.0 | True | True | 26570 |
| 2024-10-13 | 0.0 | 0.0 | 0.0 | 1.0 | True | True | 26570 |
| 2024-10-31 | 0.0 | 0.0 | 0.0 | 1.0 | True | True | 26570 |

## Outputs

- `thetao_surface_370_hres.npy`
- `LAT_hres.npy`
- `LON_hres.npy`
- `BATHY_hres.npy`
- `MASK_hres.npy`
- `dates_370.csv`
- `cmems_370_surface_hres_metadata.json`
- `thetao_surface_370_hres.nc`
- diagnostic figures

## Verdict

The 370-day CMEMS surface temperature dataset was interpolated to the canonical high-resolution grid and validated against the existing October HRes files.
