"""AUV data inspection helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr

from utils import to_rel


def _detect_role(var_name: str, attrs: Dict) -> str:
    name = var_name.lower()
    std = str(attrs.get("standard_name", "")).lower()
    long_name = str(attrs.get("long_name", "")).lower()
    text = f"{name} {std} {long_name}"
    if "time" in text:
        return "timestamp"
    if "lat" in text:
        return "lat"
    if "lon" in text or "long" in text:
        return "lon"
    if "depth" in text or "deph" in text:
        return "depth"
    if "temp" in text:
        return "temperature"
    if "sal" in text or "psal" in text:
        return "salinity"
    if "vehicle" in text or "auv" in text:
        return "vehicle_id"
    return "other"


def _sample_minmax(da: xr.DataArray, max_points: int = 2000) -> Tuple[Optional[float], Optional[float]]:
    try:
        if da.size == 0:
            return None, None
        step = max(1, da.size // max_points)
        sampled = da.values[::step]
        arr = np.asarray(sampled)
        if np.issubdtype(arr.dtype, np.number):
            with np.errstate(all="ignore"):
                return float(np.nanmin(arr)), float(np.nanmax(arr))
    except Exception:
        pass
    return None, None


def summarize_auv_files(files: List[Path], root: Path, logger) -> Tuple[pd.DataFrame, pd.DataFrame]:
    schema_rows: List[Dict] = []
    quick_rows: List[Dict] = []

    for idx, path in enumerate(files, start=1):
        rel = to_rel(path, root)
        logger.info("AUV %d/%d: %s", idx, len(files), rel)
        ext = path.suffix.lower()
        vehicle_match = re.search(r"(lauv-[^_]+-\d+)", path.name.lower())
        vehicle_id = vehicle_match.group(1) if vehicle_match else None

        if ext != ".nc":
            quick_rows.append(
                {
                    "path": rel,
                    "format": ext or "<none>",
                    "vehicle_id": vehicle_id,
                    "n_records": None,
                    "time_min": None,
                    "time_max": None,
                    "lat_min": None,
                    "lat_max": None,
                    "lon_min": None,
                    "lon_max": None,
                    "depth_min": None,
                    "depth_max": None,
                    "temp_min": None,
                    "temp_max": None,
                    "salinity_min": None,
                    "salinity_max": None,
                    "notes": "not_netcdf",
                }
            )
            continue

        try:
            ds = xr.open_dataset(path, decode_times=False, engine="netcdf4")
        except Exception as exc:
            quick_rows.append(
                {
                    "path": rel,
                    "format": ext,
                    "vehicle_id": vehicle_id,
                    "n_records": None,
                    "time_min": None,
                    "time_max": None,
                    "lat_min": None,
                    "lat_max": None,
                    "lon_min": None,
                    "lon_max": None,
                    "depth_min": None,
                    "depth_max": None,
                    "temp_min": None,
                    "temp_max": None,
                    "salinity_min": None,
                    "salinity_max": None,
                    "notes": f"open_error: {exc}",
                }
            )
            continue

        role_to_var = {}
        for coord_name in ds.coords:
            role = _detect_role(coord_name, ds[coord_name].attrs)
            role_to_var.setdefault(role, coord_name)
            schema_rows.append(
                {
                    "path": rel,
                    "var_name": coord_name,
                    "kind": "coord",
                    "dtype": str(ds[coord_name].dtype),
                    "dims": ",".join(ds[coord_name].dims),
                    "units": str(ds[coord_name].attrs.get("units")),
                    "long_name": str(ds[coord_name].attrs.get("long_name")),
                    "standard_name": str(ds[coord_name].attrs.get("standard_name")),
                    "detected_role": role,
                }
            )

        for var_name, da in ds.data_vars.items():
            role = _detect_role(var_name, da.attrs)
            role_to_var.setdefault(role, var_name)
            schema_rows.append(
                {
                    "path": rel,
                    "var_name": var_name,
                    "kind": "data_var",
                    "dtype": str(da.dtype),
                    "dims": ",".join(da.dims),
                    "units": str(da.attrs.get("units")),
                    "long_name": str(da.attrs.get("long_name")),
                    "standard_name": str(da.attrs.get("standard_name")),
                    "detected_role": role,
                }
            )

        time_var = role_to_var.get("timestamp", "TIME" if "TIME" in ds.coords else None)
        lat_var = role_to_var.get("lat", "LATITUDE" if "LATITUDE" in ds.coords else None)
        lon_var = role_to_var.get("lon", "LONGITUDE" if "LONGITUDE" in ds.coords else None)
        depth_var = role_to_var.get("depth", "DEPH" if "DEPH" in ds.data_vars else None)
        temp_var = role_to_var.get("temperature", "TEMP" if "TEMP" in ds.data_vars else None)
        sal_var = role_to_var.get("salinity", "PSAL" if "PSAL" in ds.data_vars else None)

        tmin, tmax = (None, None)
        if time_var and time_var in ds:
            tmin, tmax = _sample_minmax(ds[time_var])
        lat_min, lat_max = (None, None)
        if lat_var and lat_var in ds:
            lat_min, lat_max = _sample_minmax(ds[lat_var])
        lon_min, lon_max = (None, None)
        if lon_var and lon_var in ds:
            lon_min, lon_max = _sample_minmax(ds[lon_var])
        depth_min, depth_max = (None, None)
        if depth_var and depth_var in ds:
            depth_min, depth_max = _sample_minmax(ds[depth_var])
        temp_min, temp_max = (None, None)
        if temp_var and temp_var in ds:
            temp_min, temp_max = _sample_minmax(ds[temp_var])
        sal_min, sal_max = (None, None)
        if sal_var and sal_var in ds:
            sal_min, sal_max = _sample_minmax(ds[sal_var])

        n_records = None
        if "TIME" in ds.sizes:
            n_records = int(ds.sizes["TIME"])
        elif ds.sizes:
            n_records = int(next(iter(ds.sizes.values())))

        quick_rows.append(
            {
                "path": rel,
                "format": ext,
                "vehicle_id": vehicle_id,
                "n_records": n_records,
                "time_min": tmin,
                "time_max": tmax,
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max,
                "depth_min": depth_min,
                "depth_max": depth_max,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "salinity_min": sal_min,
                "salinity_max": sal_max,
                "notes": None,
            }
        )
        ds.close()

    return pd.DataFrame(schema_rows), pd.DataFrame(quick_rows)

