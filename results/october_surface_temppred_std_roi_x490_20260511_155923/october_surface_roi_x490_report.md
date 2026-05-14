# October Surface TEMPpred/STD ROI x490 Report

## Scope

- Input predModel root: `C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\02.Simulations\HighRes`
- STD audit folder: `C:\Users\pedro\Documents\Filipa_dados\results\std_october_surface_audit_20260511_153958`
- ROI reference folder: `C:\Users\pedro\Documents\Filipa_dados\results\fresnel_paper_roi_x490_surface_370_20260509_180348`
- Selected day slice: `1`
- Selected depth: predModel_1 / 0.494025 m
- Original NetCDF files were read only.

## ROI

- Requested bounds: `{'x_min_km': 463.0, 'x_max_km': 490.0, 'y_min_km': 4376.0, 'y_max_km': 4397.0}`
- Actual bounds: `{'x_min_km': 463.1213684082031, 'x_max_km': 489.7983093261719, 'y_min_km': 4375.94287109375, 'y_max_km': 4396.81298828125}`
- Indices: `{'row_min': 55, 'row_max': 126, 'col_min': 47, 'col_max': 163}`
- Shape: `[72, 117]`
- Mask applied: `True`
- Orientation preserved: `True`

## Outputs

- `TEMPpred_october_surface_roi_x490.npy`
- `STD_october_surface_roi_x490.npy`
- `october_surface_TEMPpred_STD_roi_x490.nc`
- Daily PNG folders for STD and TEMPpred, normal and clean.
- Panels and daily metrics CSV.

## Validation

- All files found: `True`
- Expected stack shape: `[31, 72, 117]`
- TEMP stack shape: `[31, 72, 117]`
- STD stack shape: `[31, 72, 117]`
- Reference LAT/LON match: `True`
- Reference BATHY match: `True`
- Reference MASK match: `True`
- Same orientation as reference: `True`
- Blank STD maps: `False`
- Zero STD maps: `False`
- Failed days: `Nenhum`

## Highest STD Mean Days

- 2024-10-31: STD mean=0.0676181, STD max=0.166256, STD p99=0.119196
- 2024-10-30: STD mean=0.0671324, STD max=0.148002, STD p99=0.111896
- 2024-10-29: STD mean=0.0614461, STD max=0.106789, STD p99=0.0946132
- 2024-10-16: STD mean=0.0570721, STD max=0.092018, STD p99=0.0794824
- 2024-10-15: STD mean=0.0557645, STD max=0.090821, STD p99=0.0799765

## Highest TEMPpred Mean Days

- 2024-10-22: TEMP mean=19.4981, TEMP range=1.03485, TEMP max=19.7666
- 2024-10-21: TEMP mean=19.4349, TEMP range=1.0865, TEMP max=19.7619
- 2024-10-24: TEMP mean=19.2614, TEMP range=1.1501, TEMP max=19.6793
- 2024-10-23: TEMP mean=19.2574, TEMP range=1.295, TEMP max=19.6152
- 2024-10-20: TEMP mean=19.2299, TEMP range=1.23925, TEMP max=19.6822

## Final Recommendation

Sim, os outputs estao prontos para integracao com descriptors e planner.
