# GRID AND COORDS

## Resumo

### cmems_original
- path: `data/20241030/CMEMSnaza_20241030_.nc`
- open_ok: `True`
- dims: `{"TIME": 14, "DEPT": 17, "LAT": 78, "LON": 120, "lat": 78, "lon": 120, "hours since 1950-01-01": 14, "depth": 17}`
- lat: `{"name": "LAT", "min": 39.0, "max": 41.13888931274414, "res": 0.02777862548828125, "n": 78}`
- lon: `{"name": "LON", "min": -11.75, "max": -8.44444465637207, "res": 0.027777671813964844, "n": 120}`
- depth: `{"name": "DEPT", "min": 0.49402499198913574, "max": 40.344051361083984, "res": 1.9470715522766113, "n": 17}`
- time: `{"name": "TIME", "min": 655632.0, "max": 655944.0, "res": 24.0, "n": 14}`
- crs: `None`

### hresnew
- path: `data/HResNew/CMEMSnaza_20241029_HResNew.nc`
- open_ok: `True`
- dims: `{"TIME": 14, "DEPT": 17, "LAT": 180, "LON": 240, "lat": 180, "lon": 240, "depth": 17}`
- lat: `{"name": "LAT", "min": 39.38888931274414, "max": 39.86111068725586, "res": 0.002638193482127349, "n": 180}`
- lon: `{"name": "LON", "min": -9.55555534362793, "max": -8.916666984558105, "res": 0.002673165069962735, "n": 240}`
- depth: `{"name": "DEPT", "min": 0.49402499198913574, "max": 40.344051361083984, "res": 1.9470715522766113, "n": 17}`
- time: `{"name": null, "min": null, "max": null, "res": null, "n": null}`
- crs: `None`

### pred_model
- path: `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_predModel_1.nc`
- open_ok: `True`
- dims: `{"TIME": 14, "DEPT": 17, "LAT": 180, "LON": 240, "lat": 180, "lon": 240, "depth": 17}`
- lat: `{"name": "LAT", "min": 39.38888931274414, "max": 39.86111068725586, "res": 0.002638193482127349, "n": 180}`
- lon: `{"name": "LON", "min": -9.55555534362793, "max": -8.916666984558105, "res": 0.002673165069962735, "n": 240}`
- depth: `{"name": "DEPT", "min": 0.49402499198913574, "max": 40.344051361083984, "res": 1.9470715522766113, "n": 17}`
- time: `{"name": null, "min": null, "max": null, "res": null, "n": null}`
- crs: `None`

### auv_pred_model
- path: `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_AUVpredModel_1.nc`
- open_ok: `True`
- dims: `{"TIME": 14, "DEPT": 17, "LAT": 180, "LON": 240, "lat": 180, "lon": 240, "depth": 17}`
- lat: `{"name": "LAT", "min": 39.38888931274414, "max": 39.86111068725586, "res": 0.002638193482127349, "n": 180}`
- lon: `{"name": "LON", "min": -9.55555534362793, "max": -8.916666984558105, "res": 0.002673165069962735, "n": 240}`
- depth: `{"name": "DEPT", "min": 0.49402499198913574, "max": 40.344051361083984, "res": 1.9470715522766113, "n": 17}`
- time: `{"name": null, "min": null, "max": null, "res": null, "n": null}`
- crs: `None`

### sim_gslib
- path: `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/auxi.gslib`
- open_ok: `True`
- x: `{"min": 10060.0, "max": 110219.0, "n_unique": 292, "res": 1.0}`
- y: `{"min": 10047.0, "max": 110180.0, "n_unique": 208, "res": 1.0}`
- z: `{"min": 1.0, "max": 2.0, "n_unique": 2, "res": 1.0}`
- crs: `None`

## Diferencas observadas

- Resolucao lat: CMEMS original ~0.027779 vs HResNew ~0.002638 (ratio 10.53x).
- Resolucao lon: CMEMS original ~0.027778 vs HResNew ~0.002673 (ratio 10.39x).
- Bounding box HResNew e subdominio do CMEMS original.
- predModel vs HResNew dims iguais: True.
- GSLIB usa coordenadas de grade/index (passo 1), nao lat/lon em graus.
- CRS explicito nos NetCDF: cmems_original: None; hresnew: None; pred_model: None; auv_pred_model: None
