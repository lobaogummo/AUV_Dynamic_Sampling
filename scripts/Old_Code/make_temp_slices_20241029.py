"""Generate 2D TEMP maps for HResNew 2024-10-29 (pre-assimilation only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
GLOB_PATTERN = "data/HResNew/*20241029*HResNew*.nc"

OUT_TIME_SURF = ROOT / "results" / "plots" / "temp_20241029_time_surface"
OUT_DEPT_MEAN = ROOT / "results" / "plots" / "temp_20241029_dept_mean_time"
OUT_TIME_DEPT = ROOT / "results" / "plots" / "temp_20241029_time_dept"
OUT_SCALES = ROOT / "results" / "plots" / "temp_20241029_color_scales.json"
OUT_INDEX = ROOT / "results" / "plots" / "temp_20241029_index.csv"


def _pick_dim_name(dims: Iterable[str], *candidates: str) -> Optional[str]:
    mapping = {d.lower(): d for d in dims}
    for c in candidates:
        if c.lower() in mapping:
            return mapping[c.lower()]
    return None


def _pick_coord_name(ds: xr.Dataset, *candidates: str) -> Optional[str]:
    mapping = {c.lower(): c for c in ds.coords}
    for c in candidates:
        if c.lower() in mapping:
            return mapping[c.lower()]
    return None


def _quantile_bounds(da: xr.DataArray, q_low: float = 0.02, q_high: float = 0.98) -> Tuple[float, float]:
    q = da.quantile([q_low, q_high], skipna=True).values
    return float(q[0]), float(q[1])


def _plot_2d(
    arr2d: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    title: str,
    out_path: Path,
    vmin: float,
    vmax: float,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    extent = [float(np.nanmin(lon)), float(np.nanmax(lon)), float(np.nanmin(lat)), float(np.nanmax(lat))]
    plt.figure(figsize=(8.2, 4.9))
    plt.imshow(arr2d, origin="lower", aspect="auto", extent=extent, vmin=vmin, vmax=vmax)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(title)
    plt.colorbar(label="TEMP")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> None:
    files = sorted(ROOT.glob(GLOB_PATTERN))
    if not files:
        raise FileNotFoundError(f"No files found with pattern: {GLOB_PATTERN}")
    if len(files) > 1:
        raise RuntimeError(f"Expected one HResNew 20241029 file, found {len(files)}: {files}")
    nc_path = files[0]

    OUT_TIME_SURF.mkdir(parents=True, exist_ok=True)
    OUT_DEPT_MEAN.mkdir(parents=True, exist_ok=True)
    OUT_TIME_DEPT.mkdir(parents=True, exist_ok=True)
    OUT_SCALES.parent.mkdir(parents=True, exist_ok=True)

    ds = xr.open_dataset(nc_path, decode_times=False, engine="netcdf4")
    if "TEMP" not in ds:
        raise KeyError("Variable TEMP not found.")

    temp = ds["TEMP"]
    time_dim = _pick_dim_name(temp.dims, "TIME", "time", "t")
    depth_dim = _pick_dim_name(temp.dims, "DEPT", "depth", "deph", "z")
    lat_dim = _pick_dim_name(temp.dims, "LAT", "lat", "latitude", "y")
    lon_dim = _pick_dim_name(temp.dims, "LON", "lon", "longitude", "x")
    if not all([time_dim, depth_dim, lat_dim, lon_dim]):
        raise RuntimeError(f"Could not infer expected dims in TEMP. Found dims: {temp.dims}")

    lat_coord = _pick_coord_name(ds, "LAT", "lat", "latitude", "y")
    lon_coord = _pick_coord_name(ds, "LON", "lon", "longitude", "x")
    if lat_coord is None or lon_coord is None:
        raise RuntimeError("LAT/LON coordinates not found.")
    lat = np.asarray(ds[lat_coord].values, dtype=float)
    lon = np.asarray(ds[lon_coord].values, dtype=float)

    depth_coord = _pick_coord_name(ds, "DEPT", "depth", "deph", "z")
    if depth_coord is not None:
        depth_vals = np.asarray(ds[depth_coord].values, dtype=float)
    else:
        depth_vals = np.arange(ds.sizes[depth_dim], dtype=float)

    surf_idx = int(np.nanargmin(np.abs(depth_vals - 0.0)))
    surf_depth = float(depth_vals[surf_idx])

    n_time = int(ds.sizes[time_dim])
    n_dept = int(ds.sizes[depth_dim])

    # Scales:
    # (1) all time slices at surface
    group1 = temp.isel({depth_dim: surf_idx})
    g1_vmin, g1_vmax = _quantile_bounds(group1, 0.02, 0.98)

    # (2) all depth slices of mean over time
    group2 = temp.mean(dim=time_dim, skipna=True)
    g2_vmin, g2_vmax = _quantile_bounds(group2, 0.02, 0.98)

    # (3) all time x depth combinations
    g3_vmin, g3_vmax = _quantile_bounds(temp, 0.02, 0.98)

    scales: Dict[str, Dict[str, float]] = {
        "time_surface": {"vmin": g1_vmin, "vmax": g1_vmax, "q_low": 0.02, "q_high": 0.98},
        "dept_mean_time": {"vmin": g2_vmin, "vmax": g2_vmax, "q_low": 0.02, "q_high": 0.98},
        "time_dept": {"vmin": g3_vmin, "vmax": g3_vmax, "q_low": 0.02, "q_high": 0.98},
        "meta": {
            "surface_index": surf_idx,
            "surface_depth_m": surf_depth,
            "n_time": n_time,
            "n_dept": n_dept,
            "source_file": str(nc_path.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    OUT_SCALES.write_text(json.dumps(scales, indent=2), encoding="utf-8")

    index_rows = []

    # 1) TIME at surface
    for ti in range(n_time):
        da = temp.isel({time_dim: ti, depth_dim: surf_idx})
        arr = np.asarray(da.values, dtype=float)
        out_path = OUT_TIME_SURF / f"TEMP_surface_t{ti:02d}.png"
        title = f"TEMP surface — 2024-10-29 — TIME={ti} — DEPT≈{surf_depth:.3f} m"
        _plot_2d(arr, lon, lat, title, out_path, g1_vmin, g1_vmax)
        index_rows.append(
            {
                "kind": "time_surface",
                "time_idx": ti,
                "dept_idx": surf_idx,
                "depth_m": surf_depth,
                "filepath": str(out_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    # 2) DEPT at mean over TIME
    temp_mean_time = temp.mean(dim=time_dim, skipna=True)
    for di in range(n_dept):
        depth_m = float(depth_vals[di])
        da = temp_mean_time.isel({depth_dim: di})
        arr = np.asarray(da.values, dtype=float)
        out_path = OUT_DEPT_MEAN / f"TEMP_meanT_depth{di:02d}_{depth_m:.3f}m.png"
        title = f"TEMP mean over TIME — 2024-10-29 — DEPT={di} ({depth_m:.3f} m)"
        _plot_2d(arr, lon, lat, title, out_path, g2_vmin, g2_vmax)
        index_rows.append(
            {
                "kind": "dept_mean_time",
                "time_idx": np.nan,
                "dept_idx": di,
                "depth_m": depth_m,
                "filepath": str(out_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    # 3) TIME x DEPT (all combinations)
    for ti in range(n_time):
        for di in range(n_dept):
            depth_m = float(depth_vals[di])
            da = temp.isel({time_dim: ti, depth_dim: di})
            arr = np.asarray(da.values, dtype=float)
            out_path = OUT_TIME_DEPT / f"TEMP_t{ti:02d}_d{di:02d}_{depth_m:.3f}m.png"
            title = f"TEMP — 2024-10-29 — TIME={ti} — DEPT={di} ({depth_m:.3f} m)"
            _plot_2d(arr, lon, lat, title, out_path, g3_vmin, g3_vmax)
            index_rows.append(
                {
                    "kind": "time_dept",
                    "time_idx": ti,
                    "dept_idx": di,
                    "depth_m": depth_m,
                    "filepath": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )

    pd.DataFrame(index_rows).to_csv(OUT_INDEX, index=False)

    ds.close()
    print(f"[OK] source={nc_path}")
    print(f"[OK] surf_idx={surf_idx}, surf_depth_m={surf_depth:.6f}")
    print(f"[OK] wrote scales: {OUT_SCALES}")
    print(f"[OK] wrote index: {OUT_INDEX}")
    print(f"[OK] counts: time_surface={n_time}, dept_mean_time={n_dept}, time_dept={n_time * n_dept}")


if __name__ == "__main__":
    main()

