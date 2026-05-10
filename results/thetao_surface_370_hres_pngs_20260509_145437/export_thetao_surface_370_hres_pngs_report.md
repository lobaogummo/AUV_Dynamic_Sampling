# Export CMEMS Surface HRes PNGs Report

Input array: `C:\Users\pedro\Documents\Filipa_dados\results\cmems_370_surface_to_hres_20260509_135642\thetao_surface_370_hres.npy`

Output folder: `C:\Users\pedro\Documents\Filipa_dados\results\thetao_surface_370_hres_pngs_20260509_145437`

## Checks

- Input shape: `[370, 180, 240]`
- Dates: `2023-10-28` to `2024-10-31`
- PNG count: `370`
- Clean PNG count: `370`
- Mask applied: `True`
- Orientation confirmed: `True`
- Failed exports: `0`

## Color Scale

Used a global robust color scale from all finite cells across the 370-day cube:

- Method: `robust global percentiles p1-p99; absolute min/max recorded in metadata`
- vmin: `14.579598`
- vmax: `19.780499`
- absolute min: `14.084863`
- absolute max: `21.112001`

The robust p1-p99 scale keeps the daily maps visually comparable while reducing the influence of rare extremes.

## Outputs

- `png_daily/`: full labeled PNGs
- `png_daily_clean/`: clean image-only PNGs
- `png_inventory.csv`
- `png_export_metadata.json`
- `png_export_checks.json`
- summary panels

## Verdict

The 370 daily HRes surface temperature PNG maps were successfully exported with a consistent global color scale.
