# FRESNEL Paper ROI x490 Export Report

Input folder: `C:\Users\pedro\Documents\Filipa_dados\results\cmems_370_surface_to_hres_20260509_135642`

Previous ROI outputs were deleted before this generation:

- `results/fresnel_roi_surface_370_20260509_164727`
- `results/fresnel_paper_roi_surface_370_20260509_174142`

## ROI Applied

- Requested ROI: `{'x_min_km': 463.0, 'x_max_km': 490.0, 'y_min_km': 4376.0, 'y_max_km': 4397.0}`
- Actual snapped ROI: `{'x_min_km': 463.1213684082031, 'x_max_km': 489.7983093261719, 'y_min_km': 4375.94287109375, 'y_max_km': 4396.81298828125}`
- Actual lat/lon: `{'lat_min': 39.533084869384766, 'lat_max': 39.72039794921875, 'lon_min': -9.429128646850586, 'lon_max': -9.119029998779297}`
- Indices: `{'row_min': 55, 'row_max': 126, 'col_min': 47, 'col_max': 163}`
- Shape: `[370, 72, 117]`
- Area: `556.75` km²
- Valid fraction: `0.9501`
- NaN fraction: `0.0499`
- x-axis ends near 490 km: `True`

## Export

- Normal PNGs: `370`
- Clean PNGs: `370`
- Color scale: coolwarm, p1-p99, vmin=`14.574130`, vmax=`19.654915`
- Absolute min/max: `14.110956` / `20.068953`
- Failed days: `[]`

The corrected FRESNEL paper ROI with x_max near 490 km was applied to the 370 HRes surface temperature maps, the previous ROI outputs were deleted, and all ROI PNGs were exported with a consistent global color scale.
