# THESIS_FIGURE_CONVENTIONS

## Scripts usados
- `scripts/export_surface_2024_300_images.py`
- `scripts/01b_export_normalized_surface_pngs.py`
- Suporte comum de coordenadas: `scripts/physical_coords.py`
- Fallback de renderizacao (quando `matplotlib` nao existe): `scripts/pil_geo_plot.py`

## Fonte de coordenadas (lon/lat)
- Fonte: `results/netcdf_files_summary.csv`
- Linha usada: `data/HResNew/CMEMSnaza_20241029_HResNew.nc`
- Campos usados: `lon_min`, `lon_max`, `lat_min`, `lat_max`
- Metodo aplicado: `linear_resample_from_hres_bbox`
  - `lon` e `lat` 1D sao reconstruidos linearmente para a grelha alvo `(nx=112, ny=64)`.

## Significado dos eixos
- Eixo X: **Longitude (degrees)**
- Eixo Y: **Latitude (degrees)**
- As figuras deixaram de usar indices de celula (`x`, `y`) como rotulos finais.

## Labels de colorbar e unidades
- Temperatura original:
  - label: `Temperature (°C)`
- Temperatura normalizada:
  - label adotado: `Normalized temperature (-)`

## Titulos adotados
- Original:
  - `Surface temperature - 2024 day z=NNN`
- Normalizada:
  - `Normalized surface temperature - 2024 day z=NNN`

## Regioes invalidas / mascaradas
- Pixels invalidos sao mostrados em branco.
- Esses pixels nao entram no ajuste da escala de cor.
- Orientacao espacial no renderer fallback foi alinhada com `origin="lower"` (mesma orientacao fisica da versao inicial por indices).
- Layout ajustado para manter o rotulo de latitude totalmente visivel.

## Saidas de amostra geradas nesta etapa
- `results/plots/deterministic_2024_surface_300_thesis_samples/`
- `results/fossum/pngs_normalized_surface_300_thesis_samples/`
