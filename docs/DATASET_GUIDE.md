# DATASET GUIDE - FRESNEL / Nazare C4-D4

## Visao geral

Este dataset combina campos CMEMS, interpolacao para grade de alta resolucao, modelos geoestatisticos a priori, assimilacao com observacoes AUV e produtos derivados em GSLIB/NetCDF para os testes C4 e D4.

## Como comecar

```bash
python scripts/explore_dataset.py
```

Se tiveres um ambiente virtual com dependencias:
```bash
C:/.../.venv/Scripts/python.exe scripts/explore_dataset.py
```

## Onde esta o que

- `data/20241029`, `data/20241030`: CMEMS original.
- `data/HResNew`: CMEMS interpolado para grade local.
- `data/TEST_C4`, `data/TEST_D4`: casos de teste com `Priori_` e `Nazare_`.
- `data/AUVdata`: observacoes dos AUV.

## Data dictionary gerado

- `results/dataset_inventory.csv`
- `results/netcdf_summary.csv`
- `results/netcdf_files_summary.csv`
- `results/gslib_schema.csv`
- `results/gslib_samples.csv`
- `results/sim_out_schema.csv`
- `results/auv_schema.csv`
- `results/auv_quickstats.csv`

## Exemplos minimos em Python

```python
import xarray as xr
import pandas as pd

ds = xr.open_dataset('data/HResNew/CMEMSnaza_20241030_HResNew.nc')
print(ds.data_vars)

g = pd.read_csv('results/gslib_samples.csv').query("path.str.contains('temp.gslib')", engine='python')
print(g.head())

auv = xr.open_dataset('data/AUVdata/lauv-xplore-2_2024_10_29.nc')
print(auv[['TIME','LATITUDE','LONGITUDE','DEPH','TEMP']])

# cruzamento simples AUV com grid: comparar bbox
print(float(auv.LATITUDE.min()), float(auv.LATITUDE.max()))
print(float(ds.LAT.min()), float(ds.LAT.max()))
```

## Artefactos adicionais

- `docs/DATASET_GUIDE.md`
- `docs/FILE_MAP.md`
- `docs/FORMATS_sim_out.md`
- `docs/GRID_AND_COORDS.md`
- `results/auv_quickstats.csv`
- `results/auv_schema.csv`
- `results/dataset_inventory.csv`
- `results/file_count_by_extension.csv`
- `results/file_count_by_folder.csv`
- `results/grid_comparison.json`
- `results/gslib_samples.csv`
- `results/gslib_schema.csv`
- `results/netcdf_files_summary.csv`
- `results/netcdf_summary.csv`
- `results/plots/auv_temp_vs_depth_day1.png`
- `results/plots/auv_track_day1.png`
- `results/plots/hres_temp_surface.png`
- `results/plots/post_auvpredmodel_std_surface.png`
- `results/plots/post_auvpredmodel_temp_surface.png`
- `results/plots/prior_predmodel_std_surface.png`
- `results/plots/prior_predmodel_temp_surface.png`
- `results/sim_out_schema.csv`
- `results/tree_depth5.txt`
