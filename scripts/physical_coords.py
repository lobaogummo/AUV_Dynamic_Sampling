"""Utilities to recover physical lon/lat axes for thesis-ready plots."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np


PREFERRED_HRES_REL = "data/HResNew/CMEMSnaza_20241029_HResNew.nc"
NETCDF_SUMMARY_REL = "results/netcdf_files_summary.csv"


def _find_hres_row(summary_csv: Path, preferred_rel: str) -> Dict[str, str]:
    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing NetCDF summary: {summary_csv}")

    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    preferred = next((r for r in rows if r.get("path") == preferred_rel and r.get("open_ok") == "True"), None)
    if preferred is not None:
        return preferred

    fallback = next((r for r in rows if "/HResNew/" in (r.get("path") or "").replace("\\", "/") and r.get("open_ok") == "True"), None)
    if fallback is not None:
        return fallback

    raise RuntimeError(f"No valid HResNew row found in {summary_csv}")


def load_physical_lon_lat(root: Path, nx: int, ny: int) -> Tuple[np.ndarray, np.ndarray, Dict[str, object]]:
    """Build 1D lon/lat arrays for a target grid shape from existing project metadata.

    Notes:
    - Uses `results/netcdf_files_summary.csv` (already generated in this project).
    - Uses HResNew bbox (`lon_min/max`, `lat_min/max`) and linearly maps to target `nx, ny`.
    """
    summary_csv = root / NETCDF_SUMMARY_REL
    row = _find_hres_row(summary_csv, PREFERRED_HRES_REL)

    try:
        lon_min = float(row["lon_min"])
        lon_max = float(row["lon_max"])
        lat_min = float(row["lat_min"])
        lat_max = float(row["lat_max"])
    except Exception as exc:
        raise RuntimeError(f"Invalid lon/lat bounds in {summary_csv}: {row}") from exc

    dims_json = row.get("dims_json") or "{}"
    try:
        dims = json.loads(dims_json)
    except Exception:
        dims = {}

    lon = np.linspace(lon_min, lon_max, nx, dtype=np.float64)
    lat = np.linspace(lat_min, lat_max, ny, dtype=np.float64)

    metadata = {
        "method": "linear_resample_from_hres_bbox",
        "source_csv": str(summary_csv.relative_to(root)).replace("\\", "/"),
        "source_row_path": row.get("path"),
        "hres_lon_min": lon_min,
        "hres_lon_max": lon_max,
        "hres_lat_min": lat_min,
        "hres_lat_max": lat_max,
        "hres_lon_count": int(dims.get("LON")) if isinstance(dims, dict) and dims.get("LON") is not None else None,
        "hres_lat_count": int(dims.get("LAT")) if isinstance(dims, dict) and dims.get("LAT") is not None else None,
        "target_nx": int(nx),
        "target_ny": int(ny),
    }
    return lon, lat, metadata
