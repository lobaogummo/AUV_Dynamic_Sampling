# October Surface STD Audit Report

## Scope

- Input root: `C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\02.Simulations\HighRes`
- Depth: predModel_1 / 0.494025 m
- Expected dates: 2024-10-01 to 2024-10-31
- No ROI was applied. Original NetCDF files were only read.

## Main Checks

- Files found: 31 / 31
- Missing days: Nenhum
- STD found all days: True
- TEMPpred found all days: True
- LAT/LON/BATHY found all days: True
- Expected STD shape: [180, 240]
- Shapes match: True
- Day slices detected: [0, 1]
- Selected valid day slice: 1
- Same valid slice all days: True
- Slice 0 degenerate count: 31
- Slice 1 valid count: 31
- Global plotting scale: vmin=0.006806, vmax=0.097637

## Suspicious Days

Nenhum

Detailed reasons are available in `std_october_surface_suspicious_days.csv`.

## Temporal Diagnostics

The CSV `std_october_surface_day_metrics.csv` contains daily mean, max, p99, valid fraction and nan fraction for the selected STD slice.

### Highest Mean STD

- 2024-10-31: mean=0.0739105, max=0.166256, p99=0.1213
- 2024-10-30: mean=0.0719986, max=0.148002, p99=0.112444
- 2024-10-29: mean=0.0643899, max=0.116516, p99=0.0956473
- 2024-10-16: mean=0.0518793, max=0.098673, p99=0.078299
- 2024-10-15: mean=0.0509959, max=0.096533, p99=0.0788137

### Highest Max STD

- 2024-10-31: max=0.166256, mean=0.0739105, p99=0.1213
- 2024-10-30: max=0.148002, mean=0.0719986, p99=0.112444
- 2024-10-20: max=0.12646, mean=0.0463099, p99=0.10415
- 2024-10-21: max=0.126327, mean=0.0382155, p99=0.0969567
- 2024-10-23: max=0.122091, mean=0.0440731, p99=0.0909502

## Figures

- `october_STD_surface_fullgrid_panel.png`
- `october_STD_surface_fullgrid_clean_panel.png`
- `STD_mean_timeseries.png`
- `STD_max_timeseries.png`
- `STD_p99_timeseries.png`
- `STD_valid_fraction_timeseries.png`
- `STD_nan_fraction_timeseries.png`
- `STD_day_slice_comparison_examples.png`
- `STD_suspect_days_panel.png` when suspicious days exist
- Individual maps in `std_surface_fullgrid_daily/` and `std_surface_fullgrid_daily_clean/`

## Recommendation

Sim, numericamente parecem prontos para aplicar o ROI x490, mantendo a convencao de slice identificada.

The slice convention should be carried forward explicitly when applying the FRESNEL x490 ROI.
