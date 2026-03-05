# REGIMES INPUTS - 2024-10-29 (PRE-ASSIMILACAO)

## Quais dados do dataset usar

- **NetCDF (obrigatorio)**: `data/HResNew/CMEMSnaza_20241029_HResNew.nc`
- **Variaveis**: `TEMP`, `BATHY`
- **Dims confirmadas**: `{"TIME": 14, "DEPT": 17, "LAT": 180, "LON": 240, "lat": 180, "lon": 240, "depth": 17}`
- **Data vars confirmadas**: `["TEMP", "BATHY"]`
- **Slice de profundidade (surface)**: indice `DEPT=0` (valor ~ `0.494025` m, mais proximo de 0)
- **Slice temporal recomendado**:
  usar **todos os TIME** para estatisticas temporais (`all indices 0..13`)
  e usar `mean_t(TEMP)` como campo base para regimes.

## Como os mapas foram gerados

- `mean_t(TEMP)` (surface): media ao longo de TIME
- `std_t(TEMP)` (surface): desvio-padrao ao longo de TIME
- `|grad mean_t(TEMP)|`: magnitude do gradiente espacial da media temporal
- `BATHY`: campo batimetrico (2D, sem TIME)
- `slope = |grad BATHY|`: magnitude do gradiente espacial da batimetria

Equacoes:
- `mean_t(T) = (1/N) * sum_t T(t, z_surface, y, x)`
- `std_t(T) = sqrt((1/N) * sum_t (T - mean_t(T))^2)`
- `|grad F| = sqrt((dF/dlat)^2 + (dF/dlon)^2)`

## Onde estao os PNGs

- `results/plots/regimes_20241029_mean_t_TEMP_surface.png`
- `results/plots/regimes_20241029_std_t_TEMP_surface.png`
- `results/plots/regimes_20241029_grad_mean_t_TEMP_surface.png`
- `results/plots/regimes_20241029_BATHY.png`
- `results/plots/regimes_20241029_slope_BATHY.png`