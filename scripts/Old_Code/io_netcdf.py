"""NetCDF inspection utilities with lazy sampling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr

from utils import to_rel


def _safe_attr(attrs: Dict, key: str) -> Optional[str]:
    value = attrs.get(key)
    if value is None:
        return None
    try:
        if isinstance(value, (np.ndarray, list, tuple, dict)):
            return json.dumps(value, default=str)
        return str(value)
    except Exception:
        return str(value)


def _sample_da(da: xr.DataArray, max_points_per_dim: int = 12) -> xr.DataArray:
    indexers = {}
    for dim, size in da.sizes.items():
        if size <= max_points_per_dim:
            indexers[dim] = slice(None)
        else:
            step = max(1, size // max_points_per_dim)
            indexers[dim] = slice(0, size, step)
    return da.isel(indexers)


def _var_stats_sample(da: xr.DataArray) -> Tuple[Optional[float], Optional[float], Optional[float], int]:
    sampled = _sample_da(da)
    sample_size = int(np.prod(list(sampled.sizes.values()))) if sampled.sizes else 1
    try:
        miss = float(sampled.isnull().mean().item() * 100.0)
    except Exception:
        miss = None

    vmin: Optional[float] = None
    vmax: Optional[float] = None
    try:
        values = sampled.values
        if np.issubdtype(np.asarray(values).dtype, np.number):
            with np.errstate(all="ignore"):
                vmin = float(np.nanmin(values))
                vmax = float(np.nanmax(values))
    except Exception:
        pass
    return vmin, vmax, miss, sample_size


def _find_coord_name(ds: xr.Dataset, candidates: Iterable[str]) -> Optional[str]:
    lower_map = {name.lower(): name for name in ds.coords}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def _coord_bounds(ds: xr.Dataset, coord_name: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not coord_name:
        return None, None, None
    try:
        arr = ds[coord_name].values
        arr = np.asarray(arr).astype(float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return None, None, None
        res = None
        if arr.size > 1:
            diffs = np.diff(np.sort(np.unique(arr)))
            diffs = diffs[np.isfinite(diffs)]
            if diffs.size:
                res = float(np.nanmedian(diffs))
        return float(np.nanmin(arr)), float(np.nanmax(arr)), res
    except Exception:
        return None, None, None


def summarize_netcdf_files(
    files: List[Path], root: Path, logger
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    var_rows: List[Dict] = []
    file_rows: List[Dict] = []

    for idx, path in enumerate(files, start=1):
        rel = to_rel(path, root)
        logger.info("NetCDF %d/%d: %s", idx, len(files), rel)
        try:
            ds = xr.open_dataset(path, decode_times=False, engine="netcdf4")
        except Exception as exc:
            file_rows.append(
                {
                    "path": rel,
                    "open_ok": False,
                    "error": str(exc),
                    "n_data_vars": 0,
                    "n_coords": 0,
                    "dims_json": "{}",
                    "dims_summary": None,
                    "lat_coord": None,
                    "lon_coord": None,
                    "depth_coord": None,
                    "time_coord": None,
                    "lat_min": None,
                    "lat_max": None,
                    "lon_min": None,
                    "lon_max": None,
                    "lat_res": None,
                    "lon_res": None,
                    "crs_or_grid_mapping": None,
                }
            )
            continue

        dims = dict(ds.sizes)
        lat_name = _find_coord_name(ds, ["lat", "latitude", "LAT", "LATITUDE", "y"])
        lon_name = _find_coord_name(ds, ["lon", "longitude", "LON", "LONGITUDE", "x"])
        depth_name = _find_coord_name(ds, ["depth", "deph", "DEPT", "z"])
        time_name = _find_coord_name(ds, ["time", "TIME", "t"])
        lat_min, lat_max, lat_res = _coord_bounds(ds, lat_name)
        lon_min, lon_max, lon_res = _coord_bounds(ds, lon_name)
        crs = ds.attrs.get("crs") or ds.attrs.get("grid_mapping")

        dims_summary = ", ".join([f"{k}={v}" for k, v in dims.items()])
        file_rows.append(
            {
                "path": rel,
                "open_ok": True,
                "error": None,
                "n_data_vars": len(ds.data_vars),
                "n_coords": len(ds.coords),
                "dims_json": json.dumps(dims),
                "dims_summary": dims_summary,
                "lat_coord": lat_name,
                "lon_coord": lon_name,
                "depth_coord": depth_name,
                "time_coord": time_name,
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max,
                "lat_res": lat_res,
                "lon_res": lon_res,
                "crs_or_grid_mapping": str(crs) if crs is not None else None,
            }
        )

        for var_name, da in ds.data_vars.items():
            vmin, vmax, miss, sample_size = _var_stats_sample(da)
            var_rows.append(
                {
                    "path": rel,
                    "variable": var_name,
                    "dims": ",".join(da.dims),
                    "shape": json.dumps(list(da.shape)),
                    "dtype": str(da.dtype),
                    "units": _safe_attr(da.attrs, "units"),
                    "long_name": _safe_attr(da.attrs, "long_name"),
                    "standard_name": _safe_attr(da.attrs, "standard_name"),
                    "min_sample": vmin,
                    "max_sample": vmax,
                    "missing_pct_sample": miss,
                    "sample_size": sample_size,
                    "coord_summary": f"time={time_name},depth={depth_name},lat={lat_name},lon={lon_name}",
                }
            )

        ds.close()

    return pd.DataFrame(var_rows), pd.DataFrame(file_rows)

