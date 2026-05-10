# Filipa New Dataset Forensic Audit

## Scope

Input root: `C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel`

This audit is read-only with respect to the input data. All generated artifacts were written to `C:\Users\pedro\Documents\Filipa_dados\results\filipa_data_audit_20260508_233246`.

## Inventory

- Total files: 629
- NetCDF files: 614
- `.out` files: 0
- MATLAB scripts: 13
- predModel files: 544
- Extension counts: `{".nc": 614, ".m": 13, ".exe": 2}`
- Category counts: `{"predModel": 544, "october_grouped_CMEMS_grid": 34, "downscaled_high_resolution": 34, "scripts": 13, "raw_CMEMS_Copernicus": 2, "auxiliary_executable": 2}`

## predModel Coverage

- October days found: 2024-10-01, 2024-10-02, 2024-10-03, 2024-10-04, 2024-10-05, 2024-10-06, 2024-10-07, 2024-10-08, 2024-10-09, 2024-10-10, 2024-10-11, 2024-10-12, 2024-10-13, 2024-10-14, 2024-10-15, 2024-10-16, 2024-10-17, 2024-10-18, 2024-10-19, 2024-10-20, 2024-10-21, 2024-10-22, 2024-10-23, 2024-10-24, 2024-10-25, 2024-10-26, 2024-10-27, 2024-10-28, 2024-10-29, 2024-10-30, 2024-10-31
- October days missing: none
- Depth indices found: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
- October predModel count: 527
- Expected October predModel count from found depths: 527

## Canonical Grid

- Shape: `[180, 240]`
- LAT shape: `[180]`
- LON shape: `[240]`
- BATHY shape: `[180, 240]`
- BBox: `{"lon_min": -9.554771423339844, "lon_max": -8.915862083435059, "lat_min": 39.38798522949219, "lat_max": 39.86022186279297}`
- Resolution estimate: `{"lat_km": 0.2936836984304165, "lon_km": 0.22921486761465, "mean_km": 0.26144928302253323}`
- Same grid across predModels: `True`

## Suspicious Results

Suspicious file count: 0

Reasons: No automated suspicious predModel conditions detected.

See `suspicious_files.csv` for file-level evidence.

## Interesting October Days

Top ranked days: 2024-10-10, 2024-10-13, 2024-10-15, 2024-10-11, 2024-10-31, 2024-10-12, 2024-10-09

Ranking is based on normalized spatial TEMP variability, thermal range, gradient statistics, high-gradient area, and STD metrics for the recommended surface layer.

## Reproducibility

Run:

```powershell
python "C:\Users\pedro\Documents\Filipa_dados\results\filipa_data_audit_20260508_233246\audit_filipa_new_dataset.py"
```

The script regenerates the CSV, JSON, Markdown reports, folder tree, panels, and per-predModel diagnostic maps in the same output directory.
