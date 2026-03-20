"""Create minimal pre-assimilation regime maps for 2024-10-29 (HResNew only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "HResNew"
PLOTS_DIR = ROOT / "results" / "plots"
DOC_PATH = ROOT / "docs" / "REGIMES_INPUTS_20241029.md"


def _pick_existing_dim(dims: Iterable[str], candidates: Sequence[str]) -> Optional[str]:
    lower_to_real = {d.lower(): d for d in dims}
    for c in candidates:
        if c.lower() in lower_to_real:
            return lower_to_real[c.lower()]
    return None


def _pick_coord_name(ds: xr.Dataset, candidates: Sequence[str]) -> Optional[str]:
    lower_to_real = {c.lower(): c for c in ds.coords}
    for c in candidates:
        if c.lower() in lower_to_real:
            return lower_to_real[c.lower()]
    return None


def _surface_index(ds: xr.Dataset, depth_coord_name: Optional[str]) -> Tuple[Optional[str], int]:
    depth_dim = _pick_existing_dim(ds.dims, ["DEPT", "depth", "deph", "z"])
    if depth_dim is None:
        return None, 0
    if depth_coord_name and depth_coord_name in ds.coords:
        depth_vals = np.asarray(ds[depth_coord_name].values, dtype=float)
        depth_vals = np.ravel(depth_vals)
        if depth_vals.size > 0 and np.any(np.isfinite(depth_vals)):
            idx = int(np.nanargmin(np.abs(depth_vals)))
            return depth_dim, idx
    return depth_dim, 0


def _select_surface(da: xr.DataArray, depth_dim: Optional[str], depth_idx: int) -> xr.DataArray:
    out = da
    if depth_dim and depth_dim in out.dims:
        out = out.isel({depth_dim: depth_idx})
    return out


def _to_2d(da: xr.DataArray) -> xr.DataArray:
    out = da
    for dim_candidate in ["TIME", "time", "t"]:
        dim_name = _pick_existing_dim(out.dims, [dim_candidate])
        if dim_name is not None:
            out = out.isel({dim_name: 0})
    while out.ndim > 2:
        out = out.isel({out.dims[0]: 0})
    return out


def _gradient_magnitude(field_2d: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    if field_2d.ndim != 2:
        raise ValueError("Field must be 2D for gradient.")
    if lat.ndim != 1 or lon.ndim != 1:
        raise ValueError("lat/lon must be 1D arrays.")
    d_dlat, d_dlon = np.gradient(field_2d, lat, lon, edge_order=1)
    return np.sqrt(d_dlat**2 + d_dlon**2)


def _plot_2d(arr: np.ndarray, lon: np.ndarray, lat: np.ndarray, title: str, cbar_label: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8.2, 4.8))
    extent = [float(np.nanmin(lon)), float(np.nanmax(lon)), float(np.nanmin(lat)), float(np.nanmax(lat))]
    plt.imshow(arr, origin="lower", aspect="auto", extent=extent)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(title)
    plt.colorbar(label=cbar_label)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> None:
    files = sorted(DATA_DIR.glob("*20241029*.nc"))
    if not files:
        raise FileNotFoundError("No HResNew file found for 20241029.")
    nc_path = files[0]

    ds = xr.open_dataset(nc_path, decode_times=False, engine="netcdf4")

    lat_name = _pick_coord_name(ds, ["LAT", "lat", "latitude", "y"])
    lon_name = _pick_coord_name(ds, ["LON", "lon", "longitude", "x"])
    if lat_name is None or lon_name is None:
        raise ValueError("LAT/LON coordinates not found.")
    lat = np.asarray(ds[lat_name].values, dtype=float)
    lon = np.asarray(ds[lon_name].values, dtype=float)

    if "TEMP" not in ds:
        raise ValueError("TEMP variable not found in selected HResNew file.")
    if "BATHY" not in ds:
        raise ValueError("BATHY variable not found in selected HResNew file.")

    depth_coord_name = _pick_coord_name(ds, ["DEPT", "depth", "deph", "z"])
    depth_dim, depth_idx = _surface_index(ds, depth_coord_name)
    time_dim = _pick_existing_dim(ds.dims, ["TIME", "time", "t"])

    temp = ds["TEMP"]
    temp_surface = _select_surface(temp, depth_dim, depth_idx)

    if time_dim and time_dim in temp_surface.dims:
        temp_mean_t = temp_surface.mean(dim=time_dim, skipna=True)
        temp_std_t = temp_surface.std(dim=time_dim, skipna=True)
        time_slice_note = f"all indices 0..{int(ds.sizes[time_dim]) - 1}"
    else:
        temp_mean_t = temp_surface
        temp_std_t = xr.zeros_like(temp_surface) * np.nan
        time_slice_note = "TIME dimension not present in TEMP surface slice"

    temp_mean_2d = _to_2d(temp_mean_t)
    temp_std_2d = _to_2d(temp_std_t)
    temp_mean_arr = np.asarray(temp_mean_2d.values, dtype=float)
    temp_std_arr = np.asarray(temp_std_2d.values, dtype=float)
    temp_grad_arr = _gradient_magnitude(temp_mean_arr, lat, lon)

    bathy = ds["BATHY"]
    bathy_surface = _select_surface(bathy, depth_dim, depth_idx)
    bathy_2d = _to_2d(bathy_surface)
    bathy_arr = np.asarray(bathy_2d.values, dtype=float)
    bathy_grad_arr = _gradient_magnitude(bathy_arr, lat, lon)

    out1 = PLOTS_DIR / "regimes_20241029_mean_t_TEMP_surface.png"
    out2 = PLOTS_DIR / "regimes_20241029_std_t_TEMP_surface.png"
    out3 = PLOTS_DIR / "regimes_20241029_grad_mean_t_TEMP_surface.png"
    out4 = PLOTS_DIR / "regimes_20241029_BATHY.png"
    out5 = PLOTS_DIR / "regimes_20241029_slope_BATHY.png"

    _plot_2d(temp_mean_arr, lon, lat, "mean_t(TEMP) - HResNew 2024-10-29 (surface)", "deg C", out1)
    _plot_2d(temp_std_arr, lon, lat, "std_t(TEMP) - HResNew 2024-10-29 (surface)", "deg C", out2)
    _plot_2d(temp_grad_arr, lon, lat, "|grad mean_t(TEMP)| - HResNew 2024-10-29", "deg C / degree", out3)
    _plot_2d(bathy_arr, lon, lat, "BATHY - HResNew 2024-10-29", "m", out4)
    _plot_2d(bathy_grad_arr, lon, lat, "slope = |grad BATHY| - HResNew 2024-10-29", "m / degree", out5)

    depth_values_note = "N/A"
    if depth_coord_name and depth_coord_name in ds.coords:
        depth_values = np.asarray(ds[depth_coord_name].values, dtype=float)
        if depth_values.size > depth_idx:
            depth_values_note = f"{float(depth_values[depth_idx]):.6f}"

    dims_json = json.dumps(dict(ds.sizes))
    vars_json = json.dumps(list(ds.data_vars))
    ds.close()

    md = [
        "# REGIMES INPUTS - 2024-10-29 (PRE-ASSIMILACAO)",
        "",
        "## Quais dados do dataset usar",
        "",
        "- **NetCDF (obrigatorio)**: `data/HResNew/CMEMSnaza_20241029_HResNew.nc`",
        "- **Variaveis**: `TEMP`, `BATHY`",
        "- **Dims confirmadas**: " + f"`{dims_json}`",
        "- **Data vars confirmadas**: " + f"`{vars_json}`",
        f"- **Slice de profundidade (surface)**: indice `DEPT={depth_idx}` (valor ~ `{depth_values_note}` m, mais proximo de 0)",
        "- **Slice temporal recomendado**:",
        f"  usar **todos os TIME** para estatisticas temporais (`{time_slice_note}`)",
        "  e usar `mean_t(TEMP)` como campo base para regimes.",
        "",
        "## Como os mapas foram gerados",
        "",
        "- `mean_t(TEMP)` (surface): media ao longo de TIME",
        "- `std_t(TEMP)` (surface): desvio-padrao ao longo de TIME",
        "- `|grad mean_t(TEMP)|`: magnitude do gradiente espacial da media temporal",
        "- `BATHY`: campo batimetrico (2D, sem TIME)",
        "- `slope = |grad BATHY|`: magnitude do gradiente espacial da batimetria",
        "",
        "Equacoes:",
        "- `mean_t(T) = (1/N) * sum_t T(t, z_surface, y, x)`",
        "- `std_t(T) = sqrt((1/N) * sum_t (T - mean_t(T))^2)`",
        "- `|grad F| = sqrt((dF/dlat)^2 + (dF/dlon)^2)`",
        "",
        "## Onde estao os PNGs",
        "",
        f"- `{out1.relative_to(ROOT).as_posix()}`",
        f"- `{out2.relative_to(ROOT).as_posix()}`",
        f"- `{out3.relative_to(ROOT).as_posix()}`",
        f"- `{out4.relative_to(ROOT).as_posix()}`",
        f"- `{out5.relative_to(ROOT).as_posix()}`",
    ]

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"[OK] Wrote: {DOC_PATH}")
    for p in [out1, out2, out3, out4, out5]:
        print(f"[OK] Wrote: {p}")


if __name__ == "__main__":
    main()
