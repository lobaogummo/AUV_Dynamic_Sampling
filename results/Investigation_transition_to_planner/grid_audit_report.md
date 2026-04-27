# grid_audit_report

- generated_utc: `2026-04-22T16:44:20.718804+00:00`
- tempRes_source: `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\data\2024\tempIBHRes2024_1.gslib`
- planner_interface: `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\inputs\30-10-2024_predModel_1_planner_interface.nc`
- c4_predmodel_source: `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\data\Test_C4\Priori_Nazare_30-10-2024_1\30-10-2024_predModel_1.nc`
- test_d4_nc_found: `0`

## 1) Extensao espacial (bbox)

| Grid | BBox | Approx size (km) |
|---|---|---|
| tempIBHRes native | x:[1,112] y:[1,64] z:[1,300] | n/a (index space) |
| tempIBHRes assumed physical | lat:[39.388889,39.861111] lon:[-9.555555,-8.916667] | 52.430 x 55.040 |
| Planner interface full | lat:[39.388889,39.861111] lon:[-9.555555,-8.916667] | 52.430 x 55.040 |
| Planner interface operational | lat:[39.510242,39.750310] lon:[-9.432590,-9.036959] | 26.654 x 34.024 |

## 2) Resolucao espacial real por celula

| Grid | dx (m/cell) | dy (m/cell) | dx (deg) | dy (deg) |
|---|---:|---:|---:|---:|
| tempIBHRes native | n/a | n/a | n/a | n/a |
| tempIBHRes assumed physical | 494.157 | 832.215 | 0.00575575 | 0.00749558 |
| Planner interface full | 229.512 | 292.902 | 0.00267317 | 0.00263819 |
| Planner interface operational | 229.495 | 292.903 | 0.00267317 | 0.00263819 |

## 3) Shape de cada grelha

- tempIBHRes2024_1.gslib: `nx=112, ny=64, nz=300` (rows=2,150,400)
- tempIBHRes surface-like slice (z=1): `ny=64, nx=112`
- Planner interface full: `ny=180, nx=240`
- Planner operational crop: `ny=92, nx=149`

## 4) Orientacao dos eixos

- tempIBHRes row order: x=increasing, y=increasing, z=increasing
- Planner interface: lon=increasing, lat=increasing

## 5) Sistema de coordenadas / coerencia espacial

- tempIBHRes usa eixos indexados (`x,y,z`) sem CRS explicito no ficheiro GSLIB.
- Planner interface usa `lat/lon` geograficos (graus), tambem sem atributo CRS explicito no NetCDF, mas semanticamente georreferenciado.
- Logo, a comparacao espacial direta exige uma hipotese de mapeamento para tempIBHRes (foi usada a hipotese linear via bbox HRes para auditoria).

## 6) Mascara valida / terra-mar

- tempIBHRes finite fraction (3D): `0.966099`
- tempIBHRes finite fraction (z=1): `0.966099`
- Planner interface `landt==1` fraction (full): `0.697407`
- Planner interface mask consistency `landt==1` vs finite(temperr): `1.000000`
- Planner interface `landt==1` fraction (operational crop): `0.865407`

## 7) Contencao tempRes dentro da grelha do planner

- Strict check in native coordinates: `not comparable` (no shared physical CRS).
- Assumed physical mapping check (tempRes->HRes bbox): `tempRes in planner_full = True`
- Assumed physical mapping check: `planner_operational in tempRes_assumed = True`

## 8) Grelha oficial do planeamento

- Oficial recomendada: `planner_interface_c4_full (and its operational crop from Config_file corners)`
- Ficheiro oficial: `c:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\planner_baseline_scenario_c4_predmodel\inputs\30-10-2024_predModel_1_planner_interface.nc`
- Razao: e a grelha nativa usada pelo planner (lat/lon + landt + temperr + tbath), com recorte operacional reproduzivel.

## Conclusao

**GRID MISMATCH FOUND**

### Notas adicionais

- Nao foram encontrados mapas Test_D4 no reposit?rio atual.
