"""Forensic georeferencing of tempIBHRes day z=299 from physical display axes.

This script is investigation-only. It builds candidate transforms from the
tempRes physical-axis outputs, compares them with HResNew/planner grids, and
validates temperature against temperature fields only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import RegularGridInterpolator
from scipy.stats import spearmanr

try:
    from skimage.metrics import structural_similarity as skimage_ssim
except Exception:  # pragma: no cover - optional dependency
    skimage_ssim = None


ROOT = Path(__file__).resolve().parents[1]
DAY_Z = 299
DAY_IDX = DAY_Z - 1
WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
EPS = 1e-12


@dataclass
class Projection:
    name: str
    units: str
    forward: Callable[[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]
    inverse: Callable[[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]
    notes: str


@dataclass
class Candidate:
    method_name: str
    source_of_georef: str
    projection_used: str
    centers_or_edges: str
    x_orientation: str
    y_orientation: str
    x_km: np.ndarray
    y_km: np.ndarray
    uses_physical_axes: bool
    source_details: str
    transform_family: str
    candidate_notes: str = ""
    lon_bbox: Tuple[float, float, float, float] | None = None
    geom: Dict[str, object] = field(default_factory=dict)


@dataclass
class TargetMap:
    name: str
    source_path: str
    variable: str
    array: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    bathy_mask: np.ndarray
    notes: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results" / "Investigation_transition_to_planner" / "georef_tempres_from_axes_day299",
    )
    p.add_argument("--day-z", type=int, default=DAY_Z)
    p.add_argument("--topk-registration-candidates", type=int, default=30)
    return p.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def first_existing(candidates: Iterable[Path]) -> Optional[Path]:
    for path in candidates:
        if path.exists():
            return path
    return None


def require_existing(candidates: Iterable[Path], label: str) -> Path:
    found = first_existing(candidates)
    if found is None:
        raise FileNotFoundError(f"Missing {label}; checked: {', '.join(str(p) for p in candidates)}")
    return found


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_df(path: Path, df: pd.DataFrame) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def df_to_markdown(df: pd.DataFrame, max_rows: Optional[int] = None) -> str:
    """Small markdown-table writer to avoid optional pandas/tabulate dependency."""
    work = df.copy()
    if max_rows is not None:
        work = work.head(max_rows)
    cols = [str(c) for c in work.columns]
    rows = []
    for _, row in work.iterrows():
        vals = []
        for c in work.columns:
            v = row[c]
            if isinstance(v, float):
                vals.append("" if not np.isfinite(v) else f"{v:.6g}")
            else:
                vals.append(str(v))
        rows.append(vals)
    def clean(s: str) -> str:
        return s.replace("|", "\\|").replace("\n", " ")
    lines = [
        "| " + " | ".join(clean(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for vals in rows:
        lines.append("| " + " | ".join(clean(v) for v in vals) + " |")
    return "\n".join(lines)


def finite_stats(arr: np.ndarray) -> Dict[str, object]:
    mask = np.isfinite(arr)
    out: Dict[str, object] = {"shape": [int(arr.shape[0]), int(arr.shape[1])], "valid_cells": int(mask.sum())}
    if mask.any():
        vals = arr[mask].astype(np.float64)
        out.update(
            {
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
            }
        )
    else:
        out.update({"min": None, "max": None, "mean": None, "std": None})
    return out


def km_per_degree(lat_deg: float) -> Tuple[float, float]:
    phi = math.radians(float(lat_deg))
    km_deg_lat = (
        111.13292
        - 0.55982 * math.cos(2.0 * phi)
        + 0.001175 * math.cos(4.0 * phi)
        - 0.0000023 * math.cos(6.0 * phi)
    )
    km_deg_lon = 111.41284 * math.cos(phi) - 0.0935 * math.cos(3.0 * phi) + 0.00012 * math.cos(5.0 * phi)
    return float(km_deg_lat), float(km_deg_lon)


def utm_zone29n_forward(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    lon_arr = np.asarray(lon, dtype=np.float64)
    lat_arr = np.asarray(lat, dtype=np.float64)
    a = WGS84_A
    f = WGS84_F
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    lon0 = math.radians(-9.0)
    lat_r = np.radians(lat_arr)
    lon_r = np.radians(lon_arr)
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    tan_lat = np.tan(lat_r)
    n = a / np.sqrt(1.0 - e2 * sin_lat * sin_lat)
    t = tan_lat * tan_lat
    c = ep2 * cos_lat * cos_lat
    aa = cos_lat * (lon_r - lon0)
    m = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat_r
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * np.sin(2 * lat_r)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * np.sin(4 * lat_r)
        - (35 * e2**3 / 3072) * np.sin(6 * lat_r)
    )
    x = k0 * n * (
        aa
        + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120
    ) + 500000.0
    y = k0 * (
        m
        + n
        * tan_lat
        * (
            aa**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720
        )
    )
    return x / 1000.0, y / 1000.0


def utm_zone29n_inverse(x_km: np.ndarray, y_km: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x_km, dtype=np.float64) * 1000.0 - 500000.0
    y = np.asarray(y_km, dtype=np.float64) * 1000.0
    a = WGS84_A
    f = WGS84_F
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    lon0 = math.radians(-9.0)
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    j1 = 3 * e1 / 2 - 27 * e1**3 / 32
    j2 = 21 * e1**2 / 16 - 55 * e1**4 / 32
    j3 = 151 * e1**3 / 96
    j4 = 1097 * e1**4 / 512
    fp = mu + j1 * np.sin(2 * mu) + j2 * np.sin(4 * mu) + j3 * np.sin(6 * mu) + j4 * np.sin(8 * mu)
    sin_fp = np.sin(fp)
    cos_fp = np.cos(fp)
    tan_fp = np.tan(fp)
    c1 = ep2 * cos_fp**2
    t1 = tan_fp**2
    n1 = a / np.sqrt(1 - e2 * sin_fp**2)
    r1 = a * (1 - e2) / (1 - e2 * sin_fp**2) ** 1.5
    d = x / (n1 * k0)
    lat = fp - (n1 * tan_fp / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720
    )
    lon = lon0 + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120
    ) / cos_fp
    return np.degrees(lon), np.degrees(lat)


def make_local_linear_projection(lon0: float, lat0: float) -> Projection:
    km_lat, km_lon = km_per_degree(lat0)

    def fwd(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        return (np.asarray(lon, dtype=np.float64) - lon0) * km_lon, (np.asarray(lat, dtype=np.float64) - lat0) * km_lat

    def inv(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        return np.asarray(x, dtype=np.float64) / km_lon + lon0, np.asarray(y, dtype=np.float64) / km_lat + lat0

    return Projection(
        name="local_lonlat_linear_km_midlat",
        units="km",
        forward=fwd,
        inverse=inv,
        notes=f"Local lon/lat to km approximation centered at lon0={lon0:.8f}, lat0={lat0:.8f}.",
    )


def make_aeqd_projection(lon0: float, lat0: float) -> Projection:
    r_km = 6371.0088
    lon0_r = math.radians(lon0)
    lat0_r = math.radians(lat0)
    sin0 = math.sin(lat0_r)
    cos0 = math.cos(lat0_r)

    def fwd(lon: np.ndarray, lat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        lon_r = np.radians(np.asarray(lon, dtype=np.float64))
        lat_r = np.radians(np.asarray(lat, dtype=np.float64))
        dlon = lon_r - lon0_r
        sin_lat = np.sin(lat_r)
        cos_lat = np.cos(lat_r)
        cosc = np.clip(sin0 * sin_lat + cos0 * cos_lat * np.cos(dlon), -1.0, 1.0)
        c = np.arccos(cosc)
        sinc = np.sin(c)
        k = np.where(np.abs(sinc) < 1e-12, 1.0, c / sinc)
        x = r_km * k * cos_lat * np.sin(dlon)
        y = r_km * k * (cos0 * sin_lat - sin0 * cos_lat * np.cos(dlon))
        return x, y

    def inv(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        x_arr = np.asarray(x, dtype=np.float64)
        y_arr = np.asarray(y, dtype=np.float64)
        rho = np.sqrt(x_arr * x_arr + y_arr * y_arr)
        c = rho / r_km
        sinc = np.sin(c)
        cosc = np.cos(c)
        lat = np.arcsin(np.where(rho < 1e-12, sin0, cosc * sin0 + (y_arr * sinc * cos0) / (rho + EPS)))
        lon = lon0_r + np.arctan2(x_arr * sinc, rho * cos0 * cosc - y_arr * sin0 * sinc)
        lon = np.where(rho < 1e-12, lon0_r, lon)
        return np.degrees(lon), np.degrees(lat)

    return Projection(
        name="local_azimuthal_equidistant_spherical",
        units="km",
        forward=fwd,
        inverse=inv,
        notes=f"Spherical azimuthal/equidistant projection centered at lon0={lon0:.8f}, lat0={lat0:.8f}.",
    )


def make_projections(lon: np.ndarray, lat: np.ndarray) -> Dict[str, Projection]:
    lon0 = float(0.5 * (np.nanmin(lon) + np.nanmax(lon)))
    lat0 = float(0.5 * (np.nanmin(lat) + np.nanmax(lat)))
    return {
        "EPSG_32629_UTM29N_formula": Projection(
            name="EPSG_32629_UTM29N_formula",
            units="km",
            forward=utm_zone29n_forward,
            inverse=utm_zone29n_inverse,
            notes="WGS84 / UTM zone 29N implemented by standard transverse Mercator formula; pyproj not required.",
        ),
        "local_azimuthal_equidistant_spherical": make_aeqd_projection(lon0=lon0, lat0=lat0),
        "local_lonlat_linear_km_midlat": make_local_linear_projection(lon0=lon0, lat0=lat0),
    }


def coord_name(ds: xr.Dataset, candidates: Sequence[str]) -> str:
    for cand in candidates:
        for name in list(ds.coords) + list(ds.dims):
            if name.lower() == cand.lower():
                return name
    raise RuntimeError(f"None of the coordinate candidates exists: {candidates}")


def extract_2d(da: xr.DataArray, selector: Optional[Dict[str, int]] = None) -> np.ndarray:
    work = da
    selector = selector or {}
    for dim in list(work.dims):
        dim_low = dim.lower()
        if dim in selector:
            work = work.isel({dim: selector[dim]})
        elif dim_low in selector:
            work = work.isel({dim: selector[dim_low]})
        elif work.ndim > 2:
            work = work.isel({dim: 0})
    arr = work.values
    if arr.ndim != 2:
        raise RuntimeError(f"Could not reduce {da.name} to 2D; got shape {arr.shape}")
    return arr.astype(np.float64, copy=False)


def load_tempres(day_z: int) -> Dict[str, object]:
    stack_path = require_existing(
        [ROOT / "results" / "plots" / "X_surface_300.npy", ROOT / "results" / "fossum" / "X_surface_300.npy"],
        "tempRes surface stack",
    )
    norm_path = first_existing(
        [ROOT / "results" / "plots" / "X_surface_300_norm.npy", ROOT / "results" / "fossum" / "X_surface_300_norm.npy"]
    )
    mask_path = first_existing(
        [ROOT / "results" / "plots" / "mask_common.npy", ROOT / "results" / "fossum" / "mask_common.npy"]
    )
    gslib_path = first_existing([ROOT / "data" / "2024" / "tempIBHRes2024_1.gslib"])

    stack = np.load(stack_path).astype(np.float64, copy=False)
    if stack.ndim != 3:
        raise RuntimeError(f"Expected tempRes stack as 3D, got {stack.shape}")
    day_idx = int(day_z) - 1
    if day_idx < 0 or day_idx >= stack.shape[0]:
        raise RuntimeError(f"Requested z={day_z} outside stack range 1..{stack.shape[0]}")
    day = stack[day_idx].astype(np.float64, copy=True)
    mask = np.isfinite(day)
    if mask_path and mask_path.exists():
        mask = np.load(mask_path).astype(bool, copy=False)
        day[~mask] = np.nan

    header: Dict[str, object] = {}
    if gslib_path and gslib_path.exists():
        with gslib_path.open("r", encoding="utf-8", errors="ignore") as f:
            title = f.readline().strip()
            nvars_line = f.readline().strip()
            try:
                nvars = int(nvars_line)
            except Exception:
                nvars = None
            var_names = []
            for _ in range(nvars or 0):
                var_names.append(f.readline().strip())
        header = {"title": title, "nvars": nvars, "variables": var_names}

    return {
        "stack_path": stack_path,
        "norm_path": norm_path,
        "mask_path": mask_path,
        "gslib_path": gslib_path,
        "stack": stack,
        "day": day,
        "mask": mask,
        "gslib_header": header,
        "day_z": int(day_z),
        "day_idx_0based": int(day_idx),
        "shape_nz_ny_nx": [int(stack.shape[0]), int(stack.shape[1]), int(stack.shape[2])],
    }


def load_axis_manifests() -> Dict[str, object]:
    plot_root = ROOT / "results" / "plots"
    manifests: Dict[str, object] = {}
    for path in sorted(plot_root.glob("tempibhres_relative_km_display_assumed*/manifest.json")):
        try:
            manifests[to_rel(path)] = read_json(path)
        except Exception as exc:
            manifests[to_rel(path)] = {"error": str(exc)}
    return manifests


def find_filipa_manifest(axis_manifests: Dict[str, object]) -> Tuple[Optional[Path], Optional[Dict[str, object]]]:
    for rel_path, payload in axis_manifests.items():
        if "filipa_xy_km_cropped_v1" in rel_path and isinstance(payload, dict) and "relative_km_geometry" in payload:
            return ROOT / rel_path, payload
    for rel_path, payload in axis_manifests.items():
        if isinstance(payload, dict) and "relative_km_geometry" in payload:
            return ROOT / rel_path, payload
    return None, None


def load_hres_sources() -> Dict[str, object]:
    hres_path = require_existing(
        [
            ROOT / "data" / "HResNew" / "CMEMSnaza_20241030_HResNew.nc",
            ROOT / "data" / "HResNew" / "CMEMSnaza_20241029_HResNew.nc",
        ],
        "HResNew NetCDF",
    )
    d4_pred = first_existing(
        [
            ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc",
            ROOT / "data" / "Test_C4" / "Priori_Nazare_30-10-2024_1" / "30-10-2024_predModel_1.nc",
        ]
    )
    d4_auv = first_existing(
        [
            ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_AUVpredModel_1.nc",
            ROOT / "data" / "Test_C4" / "Nazare_30-10-2024_1" / "30-10-2024_AUVpredModel_1.nc",
        ]
    )
    planner_interface = first_existing(
        [
            ROOT
            / "results"
            / "planner_baseline_scenario_c4_predmodel"
            / "inputs"
            / "30-10-2024_predModel_1_planner_interface.nc"
        ]
    )
    return {"hres_path": hres_path, "d4_pred": d4_pred, "d4_auv": d4_auv, "planner_interface": planner_interface}


def load_targets(sources: Dict[str, object]) -> Tuple[List[TargetMap], Dict[str, object]]:
    targets: List[TargetMap] = []
    inventory: Dict[str, object] = {}

    hres_path = sources["hres_path"]
    with xr.open_dataset(hres_path, decode_times=False) as ds:
        lat_name = coord_name(ds, ["lat", "LAT"])
        lon_name = coord_name(ds, ["lon", "LON"])
        lat = ds[lat_name].values.astype(np.float64)
        lon = ds[lon_name].values.astype(np.float64)
        bathy = extract_2d(ds["BATHY"]) if "BATHY" in ds.data_vars else np.ones((lat.size, lon.size), dtype=bool)
        bathy_mask = np.isfinite(bathy)
        inventory["hresnew"] = {
            "path": to_rel(hres_path),
            "dims": {k: int(v) for k, v in ds.sizes.items()},
            "coords": list(ds.coords),
            "data_vars": list(ds.data_vars),
        }
        if "TEMP" in ds.data_vars:
            temp = extract_2d(ds["TEMP"], {"TIME": 0, "DEPT": 0, "time": 0, "depth": 0})
            targets.append(
                TargetMap(
                    name="HResNew_20241030_TEMP_time0_depth0",
                    source_path=to_rel(hres_path),
                    variable="TEMP[TIME=0,DEPT=0]",
                    array=temp,
                    lat=lat,
                    lon=lon,
                    bathy_mask=bathy_mask,
                    notes="HResNew surface temperature control target.",
                )
            )

    for label, path_key in [("D4_predModel", "d4_pred"), ("D4_AUVpredModel", "d4_auv")]:
        path = sources.get(path_key)
        if not path:
            continue
        with xr.open_dataset(path, decode_times=False) as ds:
            lat_name = coord_name(ds, ["lat", "LAT"])
            lon_name = coord_name(ds, ["lon", "LON"])
            lat = ds[lat_name].values.astype(np.float64)
            lon = ds[lon_name].values.astype(np.float64)
            bathy = extract_2d(ds["BATHY"]) if "BATHY" in ds.data_vars else np.ones((lat.size, lon.size), dtype=bool)
            bathy_mask = np.isfinite(bathy)
            inventory[label] = {
                "path": to_rel(path),
                "dims": {k: int(v) for k, v in ds.sizes.items()},
                "coords": list(ds.coords),
                "data_vars": list(ds.data_vars),
            }
            if "TEMPpred" in ds.data_vars:
                da = ds["TEMPpred"]
                if da.ndim == 2:
                    targets.append(
                        TargetMap(
                            name=f"{label}_TEMPpred",
                            source_path=to_rel(path),
                            variable="TEMPpred",
                            array=da.values.astype(np.float64),
                            lat=lat,
                            lon=lon,
                            bathy_mask=bathy_mask,
                            notes="Primary temperature target candidate; STD is not used.",
                        )
                    )
                elif da.ndim == 3:
                    day_dim = da.dims[0]
                    for idx in range(int(da.shape[0])):
                        targets.append(
                            TargetMap(
                                name=f"{label}_TEMPpred_{day_dim}{idx}",
                                source_path=to_rel(path),
                                variable=f"TEMPpred[{day_dim}={idx}]",
                                array=da.isel({day_dim: idx}).values.astype(np.float64),
                                lat=lat,
                                lon=lon,
                                bathy_mask=bathy_mask,
                                notes="Primary temperature target candidate; STD is not used.",
                            )
                        )

    planner_path = sources.get("planner_interface")
    if planner_path:
        with xr.open_dataset(planner_path, decode_times=False) as ds:
            inventory["planner_interface"] = {
                "path": to_rel(planner_path),
                "dims": {k: int(v) for k, v in ds.sizes.items()},
                "coords": list(ds.coords),
                "data_vars": list(ds.data_vars),
                "validation_policy": "Not used as primary temperature target; TEMP/TEMPpred targets are preferred.",
            }
    return targets, inventory


def parse_config_roi(lat: np.ndarray, lon: np.ndarray) -> Dict[str, object]:
    old_bboxes = ROOT / "results" / "Investigation_transition_to_planner" / "candb_vs_userdirect_bboxes.csv"
    if old_bboxes.exists():
        rows = list(csv.DictReader(old_bboxes.open("r", encoding="utf-8", newline="")))
        row = next((r for r in rows if r.get("roi_id") == "planner_operational_roi"), None)
        if row:
            return {
                "x0": int(row["x0_idx"]),
                "x1": int(row["x1_idx"]),
                "y0": int(row["y0_idx"]),
                "y1": int(row["y1_idx"]),
                "source": to_rel(old_bboxes),
                "lon_min": float(row["lon_min"]),
                "lon_max": float(row["lon_max"]),
                "lat_min": float(row["lat_min"]),
                "lat_max": float(row["lat_max"]),
            }

    cfg = ROOT / "OptimalPlanning_Lucrezia" / "Config_file.py"
    txt = cfg.read_text(encoding="utf-8", errors="ignore")
    ll = re.search(r"OPERATION_LL_CORNER\s*=\s*\[\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*\]", txt)
    ur = re.search(r"OPERATION_UR_CORNER\s*=\s*\[\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*\]", txt)
    if ll is None or ur is None:
        raise RuntimeError("Could not parse OPERATION_LL_CORNER/UR_CORNER")
    lat_min, lon_min = float(ll.group(1)), float(ll.group(2))
    lat_max, lon_max = float(ur.group(1)), float(ur.group(2))
    xi = np.where((lon >= min(lon_min, lon_max)) & (lon <= max(lon_min, lon_max)))[0]
    yi = np.where((lat >= min(lat_min, lat_max)) & (lat <= max(lat_min, lat_max)))[0]
    return {
        "x0": int(xi.min()),
        "x1": int(xi.max()),
        "y0": int(yi.min()),
        "y1": int(yi.max()),
        "source": to_rel(cfg),
        "lon_min": float(lon[xi.min()]),
        "lon_max": float(lon[xi.max()]),
        "lat_min": float(lat[yi.min()]),
        "lat_max": float(lat[yi.max()]),
    }


def roi_mask(shape: Tuple[int, int], roi: Dict[str, object]) -> np.ndarray:
    out = np.zeros(shape, dtype=bool)
    out[int(roi["y0"]) : int(roi["y1"]) + 1, int(roi["x0"]) : int(roi["x1"]) + 1] = True
    return out


def load_old_bboxes() -> Dict[str, Dict[str, object]]:
    path = ROOT / "results" / "Investigation_transition_to_planner" / "candb_vs_userdirect_bboxes.csv"
    out: Dict[str, Dict[str, object]] = {}
    if not path.exists():
        return out
    for row in csv.DictReader(path.open("r", encoding="utf-8", newline="")):
        out[row["roi_id"]] = row
    return out


def axis_centers(min_v: float, max_v: float, n: int, convention: str, orientation: str) -> np.ndarray:
    if convention == "centers":
        arr = np.linspace(float(min_v), float(max_v), int(n), dtype=np.float64)
    elif convention == "edges":
        step = (float(max_v) - float(min_v)) / float(n)
        arr = np.linspace(float(min_v) + 0.5 * step, float(max_v) - 0.5 * step, int(n), dtype=np.float64)
    else:
        raise ValueError(convention)
    if orientation == "flipped":
        arr = arr[::-1].copy()
    return arr


def lonlat_bbox_from_xy(proj: Projection, x_min: float, x_max: float, y_min: float, y_max: float) -> Tuple[float, float, float, float]:
    xs = np.array([x_min, x_max, x_min, x_max], dtype=np.float64)
    ys = np.array([y_min, y_min, y_max, y_max], dtype=np.float64)
    lon, lat = proj.inverse(xs, ys)
    return float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))


def add_bbox_candidates(
    candidates: List[Candidate],
    base_name: str,
    source: str,
    projection: Projection,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    nx: int,
    ny: int,
    uses_axes: bool,
    family: str,
    details: str,
    include_edges: bool = True,
    include_flips: bool = True,
) -> None:
    conventions = ["centers", "edges"] if include_edges else ["centers"]
    orientations = ["normal", "flipped"] if include_flips else ["normal"]
    for conv in conventions:
        for xori in orientations:
            for yori in orientations:
                x = axis_centers(xmin, xmax, nx, conv, xori)
                y = axis_centers(ymin, ymax, ny, conv, yori)
                name = f"{base_name}__{projection.name}__{conv}__x_{xori}__y_{yori}"
                cand = Candidate(
                    method_name=name,
                    source_of_georef=source,
                    projection_used=projection.name,
                    centers_or_edges=conv,
                    x_orientation=xori,
                    y_orientation=yori,
                    x_km=x,
                    y_km=y,
                    uses_physical_axes=uses_axes,
                    source_details=details,
                    transform_family=family,
                )
                cand.lon_bbox = lonlat_bbox_from_xy(projection, float(np.min(x)), float(np.max(x)), float(np.min(y)), float(np.max(y)))
                candidates.append(cand)


def add_crop_candidate(
    candidates: List[Candidate],
    base_name: str,
    source: str,
    projection: Projection,
    hres_x: np.ndarray,
    hres_y: np.ndarray,
    x0: int,
    x1: int,
    y0: int,
    y1: int,
    nx: int,
    ny: int,
    family: str,
    details: str,
    include_flips: bool = False,
) -> None:
    xmin, xmax = float(hres_x[0, x0]), float(hres_x[0, x1])
    ymin, ymax = float(hres_y[y0, 0]), float(hres_y[y1, 0])
    orientations = ["normal", "flipped"] if include_flips else ["normal"]
    for xori in orientations:
        for yori in orientations:
            x = axis_centers(xmin, xmax, nx, "centers", xori)
            y = axis_centers(ymin, ymax, ny, "centers", yori)
            name = f"{base_name}__{projection.name}__hres_crop_centers__x_{xori}__y_{yori}"
            cand = Candidate(
                method_name=name,
                source_of_georef=source,
                projection_used=projection.name,
                centers_or_edges="hres_crop_resampled_centers",
                x_orientation=xori,
                y_orientation=yori,
                x_km=x,
                y_km=y,
                uses_physical_axes=False,
                source_details=details,
                transform_family=family,
                candidate_notes=f"HRes crop indices x={x0}..{x1}, y={y0}..{y1}",
            )
            cand.lon_bbox = lonlat_bbox_from_xy(projection, float(np.min(x)), float(np.max(x)), float(np.min(y)), float(np.max(y)))
            candidates.append(cand)


def build_candidates(
    projections: Dict[str, Projection],
    hres_proj: Dict[str, Dict[str, np.ndarray]],
    temp_shape: Tuple[int, int],
    filipa_manifest: Optional[Dict[str, object]],
    old_bboxes: Dict[str, Dict[str, object]],
    topk: int,
) -> List[Candidate]:
    ny, nx = int(temp_shape[0]), int(temp_shape[1])
    candidates: List[Candidate] = []

    for proj_name, proj in projections.items():
        xg = hres_proj[proj_name]["x"]
        yg = hres_proj[proj_name]["y"]
        hxmin, hxmax = float(np.nanmin(xg)), float(np.nanmax(xg))
        hymin, hymax = float(np.nanmin(yg)), float(np.nanmax(yg))
        add_bbox_candidates(
            candidates,
            "HRES_BBOX_SIMPLE_FULL_DOMAIN",
            "HResNew/planner full lon/lat bbox",
            proj,
            hxmin,
            hxmax,
            hymin,
            hymax,
            nx,
            ny,
            False,
            "simple_bbox",
            "Full HRes/planner projected bbox mapped to full tempRes grid.",
        )

    if filipa_manifest:
        geom = filipa_manifest["relative_km_geometry"]
        offsets = filipa_manifest.get("axis_offsets_km", {})
        crop = filipa_manifest.get("crop", {})
        xoff = float(offsets.get("x_offset_km", 0.0))
        yoff = float(offsets.get("y_offset_km", 0.0))
        rel_xmin, rel_xmax = float(geom["x_km_min"]), float(geom["x_km_max"])
        rel_ymin, rel_ymax = float(geom["y_km_min"]), float(geom["y_km_max"])
        utm = projections["EPSG_32629_UTM29N_formula"]
        add_bbox_candidates(
            candidates,
            "AXES_FILIPA_ABS_KM_FULL",
            "relative_km_display_assumed_filipa_xy_km_cropped_v1 manifest offsets + full geometry",
            utm,
            xoff + rel_xmin,
            xoff + rel_xmax,
            yoff + rel_ymin,
            yoff + rel_ymax,
            nx,
            ny,
            True,
            "physical_axes_absolute_utm",
            "Interprets displayed x/y km offsets as absolute UTM-like km for the full tempRes grid.",
        )
        if crop:
            x0 = int(crop.get("x_start_col_1based", 1)) - 1
            x1 = int(crop.get("x_end_col_1based", nx)) - 1
            y0 = int(crop.get("y_start_row_1based", 1)) - 1
            y1 = int(crop.get("y_end_row_1based", ny)) - 1
            dx = float(geom["dx_km_per_cell"])
            dy = float(geom["dy_km_per_cell"])
            add_bbox_candidates(
                candidates,
                "AXES_FILIPA_DISPLAY_CROP_AS_FULL",
                "Filipa cropped image displayed km bbox",
                utm,
                xoff + x0 * dx,
                xoff + x1 * dx,
                yoff + y0 * dy,
                yoff + y1 * dy,
                nx,
                ny,
                True,
                "physical_axes_crop_as_full",
                "Stress-test: interprets the displayed crop km extent as if it described the full tempRes grid.",
            )

        for proj_name, proj in projections.items():
            xg = hres_proj[proj_name]["x"]
            yg = hres_proj[proj_name]["y"]
            hxmin, hymin = float(np.nanmin(xg)), float(np.nanmin(yg))
            add_bbox_candidates(
                candidates,
                "AXES_RELATIVE_KM_OFFSET_TO_HRES_MIN",
                "relative_km_display_assumed geometry shifted to HRes projected minimum",
                proj,
                hxmin + rel_xmin,
                hxmin + rel_xmax,
                hymin + rel_ymin,
                hymin + rel_ymax,
                nx,
                ny,
                True,
                "physical_axes_relative_offset_fit",
                "Interprets axes as relative km and chooses the offset that aligns their minimum with the HRes projected minimum.",
            )

    for roi_id, row in old_bboxes.items():
        if roi_id not in {"cand_b_roi", "user_direct_km_roi"}:
            continue
        for proj_name, proj in projections.items():
            lon_min, lon_max = float(row["lon_min"]), float(row["lon_max"])
            lat_min, lat_max = float(row["lat_min"]), float(row["lat_max"])
            xs, ys = proj.forward(np.array([lon_min, lon_max]), np.array([lat_min, lat_max]))
            add_bbox_candidates(
                candidates,
                f"OLD_{roi_id.upper()}_BBOX",
                f"Existing {roi_id} bbox from candb_vs_userdirect_bboxes.csv",
                proj,
                float(np.min(xs)),
                float(np.max(xs)),
                float(np.min(ys)),
                float(np.max(ys)),
                nx,
                ny,
                roi_id == "user_direct_km_roi",
                "old_reference_bbox",
                str(row.get("notes", "")),
                include_edges=False,
                include_flips=False,
            )

    # Registration/crop candidates use HRes index crop semantics.
    candb_summary = ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4" / "tables" / "best_candidate_summary.csv"
    if candb_summary.exists():
        row = pd.read_csv(candb_summary).iloc[0]
        for proj_name, proj in projections.items():
            add_crop_candidate(
                candidates,
                "CAND_B_REGISTRATION_TO_HRES_SUBAREA",
                "Controlled registration best candidate",
                proj,
                hres_proj[proj_name]["x"],
                hres_proj[proj_name]["y"],
                int(row["x0"]),
                int(row["x1"]),
                int(row["y0"]),
                int(row["y1"]),
                nx,
                ny,
                "registration_crop",
                to_rel(candb_summary),
                include_flips=True,
            )

    top_eval = ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4" / "tables" / "top_candidates_temperature_eval.csv"
    if top_eval.exists():
        df = pd.read_csv(top_eval).head(int(topk))
        proj = projections["EPSG_32629_UTM29N_formula"]
        for rank, row in enumerate(df.itertuples(index=False), start=1):
            add_crop_candidate(
                candidates,
                f"OPTIMIZED_TOPK_REGISTRATION_R{rank:02d}",
                "Top candidates from controlled registration table",
                proj,
                hres_proj[proj.name]["x"],
                hres_proj[proj.name]["y"],
                int(row.x0),
                int(row.x1),
                int(row.y0),
                int(row.y1),
                nx,
                ny,
                "optimized_registration_topk",
                f"{to_rel(top_eval)} rank {rank}",
                include_flips=False,
            )
    return candidates


def project_grid_stats(projections: Dict[str, Projection], lon: np.ndarray, lat: np.ndarray) -> Tuple[pd.DataFrame, Dict[str, object], Dict[str, Dict[str, np.ndarray]]]:
    lon2, lat2 = np.meshgrid(lon, lat)
    rows: List[Dict[str, object]] = []
    checks: Dict[str, object] = {}
    grids: Dict[str, Dict[str, np.ndarray]] = {}
    for name, proj in projections.items():
        x, y = proj.forward(lon2, lat2)
        grids[name] = {"x": x, "y": y}
        dx = np.diff(x, axis=1)
        dy = np.diff(y, axis=0)
        rows.append(
            {
                "projection": name,
                "units": proj.units,
                "x_min": float(np.nanmin(x)),
                "x_max": float(np.nanmax(x)),
                "y_min": float(np.nanmin(y)),
                "y_max": float(np.nanmax(y)),
                "extent_x_km": float(np.nanmax(x) - np.nanmin(x)),
                "extent_y_km": float(np.nanmax(y) - np.nanmin(y)),
                "dx_mean_km": float(np.nanmean(np.abs(dx))),
                "dx_std_km": float(np.nanstd(dx)),
                "dy_mean_km": float(np.nanmean(np.abs(dy))),
                "dy_std_km": float(np.nanstd(dy)),
                "notes": proj.notes,
            }
        )
        checks[name] = {
            "x_monotonic_by_row": bool(np.all(np.diff(x, axis=1) > 0) or np.all(np.diff(x, axis=1) < 0)),
            "y_monotonic_by_col": bool(np.all(np.diff(y, axis=0) > 0) or np.all(np.diff(y, axis=0) < 0)),
            "units": proj.units,
            "notes": proj.notes,
        }
    return pd.DataFrame(rows), checks, grids


def bbox_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> Dict[str, float]:
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b
    ix0, ix1 = max(ax0, bx0), min(ax1, bx1)
    iy0, iy1 = max(ay0, by0), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    aa = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    ba = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = aa + ba - inter
    return {
        "intersection_area": float(inter),
        "iou": float(inter / union) if union > 0 else 0.0,
        "coverage_of_a": float(inter / aa) if aa > 0 else 0.0,
        "coverage_of_b": float(inter / ba) if ba > 0 else 0.0,
    }


def regrid_to_hres(values: np.ndarray, x_coords: np.ndarray, y_coords: np.ndarray, hres_x: np.ndarray, hres_y: np.ndarray) -> np.ndarray:
    data = values.astype(np.float64, copy=True)
    x = x_coords.astype(np.float64, copy=True)
    y = y_coords.astype(np.float64, copy=True)
    if x[0] > x[-1]:
        x = x[::-1].copy()
        data = data[:, ::-1]
    if y[0] > y[-1]:
        y = y[::-1].copy()
        data = data[::-1, :]
    interp = RegularGridInterpolator((y, x), data, bounds_error=False, fill_value=np.nan)
    pts = np.column_stack([hres_y.ravel(), hres_x.ravel()])
    out = interp(pts).reshape(hres_x.shape)
    return out


def pearson_safe(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 3:
        return float("nan")
    aa = a.astype(np.float64) - float(np.mean(a))
    bb = b.astype(np.float64) - float(np.mean(b))
    den = float(np.sqrt(np.sum(aa * aa) * np.sum(bb * bb)))
    if den < EPS:
        return float("nan")
    return float(np.sum(aa * bb) / den)


def gradient_mag(arr: np.ndarray) -> np.ndarray:
    filled = arr.astype(np.float64, copy=True)
    if np.any(np.isfinite(filled)):
        fill = float(np.nanmean(filled))
    else:
        fill = 0.0
    filled = np.where(np.isfinite(filled), filled, fill)
    gy, gx = np.gradient(filled)
    return np.sqrt(gx * gx + gy * gy)


def contour_alignment(pred: np.ndarray, target: np.ndarray, valid: np.ndarray) -> float:
    scores: List[float] = []
    pv = pred[valid]
    tv = target[valid]
    if pv.size < 128:
        return float("nan")
    for q in [0.25, 0.50, 0.75]:
        pt = float(np.quantile(pv, q))
        tt = float(np.quantile(tv, q))
        pm = valid & (pred >= pt)
        tm = valid & (target >= tt)
        inter = float(np.logical_and(pm, tm).sum())
        union = float(np.logical_or(pm, tm).sum())
        if union > 0:
            scores.append(inter / union)
    return float(np.mean(scores)) if scores else float("nan")


def ssim_score(pred: np.ndarray, target: np.ndarray, valid: np.ndarray) -> float:
    if skimage_ssim is None or valid.sum() < 128:
        return float("nan")
    ys, xs = np.where(valid)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    p = pred[y0 : y1 + 1, x0 : x1 + 1].astype(np.float64)
    t = target[y0 : y1 + 1, x0 : x1 + 1].astype(np.float64)
    m = valid[y0 : y1 + 1, x0 : x1 + 1]
    if p.shape[0] < 7 or p.shape[1] < 7:
        return float("nan")
    p_fill = np.where(np.isfinite(p) & m, p, np.nanmean(p[m]))
    t_fill = np.where(np.isfinite(t) & m, t, np.nanmean(t[m]))
    p_rng = float(np.nanmax(p_fill) - np.nanmin(p_fill))
    t_rng = float(np.nanmax(t_fill) - np.nanmin(t_fill))
    if p_rng < EPS or t_rng < EPS:
        return float("nan")
    p_norm = (p_fill - float(np.nanmin(p_fill))) / p_rng
    t_norm = (t_fill - float(np.nanmin(t_fill))) / t_rng
    try:
        return float(skimage_ssim(p_norm, t_norm, data_range=1.0))
    except Exception:
        return float("nan")


def metric_row(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> Dict[str, object]:
    valid = mask & np.isfinite(pred) & np.isfinite(target)
    n = int(valid.sum())
    if n < 32:
        return {
            "n_valid": n,
            "rmse_temperature": np.nan,
            "mae_temperature": np.nan,
            "bias_mean": np.nan,
            "max_abs_error": np.nan,
            "pearson_temperature": np.nan,
            "spearman_temperature": np.nan,
            "normalized_rmse": np.nan,
            "gradient_corr": np.nan,
            "contour_score": np.nan,
            "ssim": np.nan,
        }
    d = pred[valid] - target[valid]
    rmse = float(np.sqrt(np.mean(d * d)))
    mae = float(np.mean(np.abs(d)))
    bias = float(np.mean(d))
    max_abs = float(np.max(np.abs(d)))
    pear = pearson_safe(pred[valid], target[valid])
    try:
        spear = float(spearmanr(pred[valid], target[valid]).correlation)
    except Exception:
        spear = float("nan")
    rng = float(np.nanmax(target[valid]) - np.nanmin(target[valid]))
    nrmse = float(rmse / (rng + EPS))
    gpred = gradient_mag(pred)
    gtgt = gradient_mag(target)
    gcorr = pearson_safe(gpred[valid], gtgt[valid])
    contour = contour_alignment(pred, target, valid)
    ssim = ssim_score(pred, target, valid)
    return {
        "n_valid": n,
        "rmse_temperature": rmse,
        "mae_temperature": mae,
        "bias_mean": bias,
        "max_abs_error": max_abs,
        "pearson_temperature": pear,
        "spearman_temperature": spear,
        "normalized_rmse": nrmse,
        "gradient_corr": gcorr,
        "contour_score": contour,
        "ssim": ssim,
    }


def evaluate_candidates(
    candidates: Sequence[Candidate],
    temp_day: np.ndarray,
    temp_mask: np.ndarray,
    targets: Sequence[TargetMap],
    projections: Dict[str, Projection],
    hres_proj: Dict[str, Dict[str, np.ndarray]],
    rois: Dict[str, Dict[str, object]],
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, np.ndarray]]:
    geom_rows: List[Dict[str, object]] = []
    metric_rows: List[Dict[str, object]] = []
    regrid_cache: Dict[str, np.ndarray] = {}

    primary_target = targets[0]
    hres_shape = primary_target.array.shape
    hres_bbox_by_proj = {
        name: (
            float(np.nanmin(grids["x"])),
            float(np.nanmax(grids["x"])),
            float(np.nanmin(grids["y"])),
            float(np.nanmax(grids["y"])),
        )
        for name, grids in hres_proj.items()
    }
    region_masks = {
        "full_overlap": np.ones(hres_shape, dtype=bool),
        "operational_roi": roi_mask(hres_shape, rois["operational"]),
        "candb_roi": roi_mask(hres_shape, rois["candb"]) if "candb" in rois else np.zeros(hres_shape, dtype=bool),
        "user_direct_roi": roi_mask(hres_shape, rois["user_direct"]) if "user_direct" in rois else np.zeros(hres_shape, dtype=bool),
    }

    for cand in candidates:
        proj = projections[cand.projection_used]
        bbox_xy = (float(np.min(cand.x_km)), float(np.max(cand.x_km)), float(np.min(cand.y_km)), float(np.max(cand.y_km)))
        hbox = hres_bbox_by_proj[cand.projection_used]
        overlap = bbox_overlap(bbox_xy, hbox)
        center_dist = float(
            math.hypot(0.5 * (bbox_xy[0] + bbox_xy[1]) - 0.5 * (hbox[0] + hbox[1]), 0.5 * (bbox_xy[2] + bbox_xy[3]) - 0.5 * (hbox[2] + hbox[3]))
        )
        hres_x = hres_proj[cand.projection_used]["x"]
        hres_y = hres_proj[cand.projection_used]["y"]
        pred = regrid_to_hres(temp_day, cand.x_km, cand.y_km, hres_x, hres_y)
        mask_pred_float = regrid_to_hres(temp_mask.astype(np.float64), cand.x_km, cand.y_km, hres_x, hres_y)
        pred_support = np.isfinite(pred) & (mask_pred_float >= 0.5)
        cache_key = cand.method_name
        regrid_cache[cache_key] = pred
        bathy = primary_target.bathy_mask
        inter = int(np.logical_and(pred_support, bathy).sum())
        union = int(np.logical_or(pred_support, bathy).sum())
        mask_iou = float(inter / union) if union > 0 else float("nan")
        geom_rows.append(
            {
                "method_name": cand.method_name,
                "source_of_georef": cand.source_of_georef,
                "projection_used": cand.projection_used,
                "centers_or_edges": cand.centers_or_edges,
                "x_orientation": cand.x_orientation,
                "y_orientation": cand.y_orientation,
                "transform_family": cand.transform_family,
                "uses_physical_axes": bool(cand.uses_physical_axes),
                "x_km_min": bbox_xy[0],
                "x_km_max": bbox_xy[1],
                "y_km_min": bbox_xy[2],
                "y_km_max": bbox_xy[3],
                "bbox_lonlat": json.dumps(cand.lon_bbox),
                "contained_in_hres": bool(overlap["coverage_of_a"] >= 0.999),
                "overlap_fraction": overlap["coverage_of_a"],
                "bbox_iou_hres": overlap["iou"],
                "center_distance_km": center_dist,
                "scale_x_ratio_vs_hres": float((bbox_xy[1] - bbox_xy[0]) / (hbox[1] - hbox[0] + EPS)),
                "scale_y_ratio_vs_hres": float((bbox_xy[3] - bbox_xy[2]) / (hbox[3] - hbox[2] + EPS)),
                "mask_iou_hres_bathy": mask_iou,
                "source_details": cand.source_details,
                "candidate_notes": cand.candidate_notes,
            }
        )
        for target in targets:
            if target.array.shape != hres_shape:
                continue
            base_valid = target.bathy_mask
            for region_name, region_mask in region_masks.items():
                mask = base_valid & region_mask
                metrics = metric_row(pred, target.array, mask)
                metric_rows.append(
                    {
                        "method_name": cand.method_name,
                        "target_name": target.name,
                        "target_variable": target.variable,
                        "target_source": target.source_path,
                        "region": region_name,
                        **metrics,
                    }
                )
    return pd.DataFrame(geom_rows), pd.DataFrame(metric_rows), regrid_cache


def build_rois(target: TargetMap, old_bboxes: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    rois = {"operational": parse_config_roi(target.lat, target.lon)}
    for key, roi_id in [("candb", "cand_b_roi"), ("user_direct", "user_direct_km_roi")]:
        row = old_bboxes.get(roi_id)
        if row:
            rois[key] = {
                "x0": int(row["x0_idx"]),
                "x1": int(row["x1_idx"]),
                "y0": int(row["y0_idx"]),
                "y1": int(row["y1_idx"]),
                "source": "candb_vs_userdirect_bboxes.csv",
                "lon_min": float(row["lon_min"]),
                "lon_max": float(row["lon_max"]),
                "lat_min": float(row["lat_min"]),
                "lat_max": float(row["lat_max"]),
            }
    return rois


def leaderboard(metric_df: pd.DataFrame, geom_df: pd.DataFrame, primary_target: str) -> pd.DataFrame:
    sub = metric_df[(metric_df["target_name"] == primary_target) & (metric_df["region"] == "full_overlap")].copy()
    merged = sub.merge(geom_df, on="method_name", how="left")
    for col in ["pearson_temperature", "gradient_corr", "contour_score", "normalized_rmse"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
    merged["score"] = (
        merged["pearson_temperature"].fillna(-1.0)
        + 0.5 * merged["gradient_corr"].fillna(-1.0)
        + 0.5 * merged["contour_score"].fillna(0.0)
        - merged["normalized_rmse"].fillna(10.0)
    )
    merged = merged.sort_values(["score", "pearson_temperature", "rmse_temperature"], ascending=[False, False, True]).reset_index(drop=True)
    merged["rank"] = np.arange(1, len(merged) + 1)
    merged["verdict"] = np.where(
        merged["rank"] == 1,
        "BEST_NUMERIC_MATCH",
        np.where(merged["uses_physical_axes"], "AXES_TESTED", "COMPARATOR"),
    )
    requested_cols = [
        "method_name",
        "source_of_georef",
        "projection_used",
        "centers_or_edges",
        "x_orientation",
        "y_orientation",
        "target_name",
        "bbox_lonlat",
        "contained_in_hres",
        "overlap_fraction",
        "rmse_temperature",
        "pearson_temperature",
        "gradient_corr",
        "contour_score",
        "rank",
        "verdict",
        "score",
        "normalized_rmse",
        "mask_iou_hres_bathy",
        "transform_family",
        "uses_physical_axes",
    ]
    return merged[requested_cols]


def select_recommended_candidate(board: pd.DataFrame) -> Tuple[str, str]:
    """Choose the transform to publish for descriptor transfer.

    The leaderboard is a numeric fixed-day ranking. The recommended transform
    must also be geometrically/documentarily defensible, so avoid adopting a
    flipped-axis variant unless it is the only supported option.
    """
    preferred = (
        "CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__"
        "hres_crop_centers__x_normal__y_normal"
    )
    if preferred in set(board["method_name"]):
        return (
            preferred,
            "Selected because it is the controlled CAND_B registration in UTM 29N with east/north-normal orientation; "
            "the fixed z=299 numeric leaderboard is retained separately and is not enough to justify an x-flipped georeference.",
        )
    defensible = board[
        (board["contained_in_hres"].astype(str).str.lower() == "true")
        & (board["x_orientation"] == "normal")
        & (board["y_orientation"] == "normal")
    ]
    if not defensible.empty:
        row = defensible.iloc[0]
        return str(row["method_name"]), "Selected as the best contained, normal-orientation candidate available."
    return str(board.iloc[0]["method_name"]), "Fallback to top numeric leaderboard candidate; no normal-orientation candidate was available."


def imshow_field(ax: plt.Axes, arr: np.ndarray, title: str, extent: Optional[Sequence[float]] = None, cmap: str = "viridis") -> None:
    cm = plt.get_cmap(cmap).copy()
    cm.set_bad("white")
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cm, extent=extent)
    ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def plot_rect(ax: plt.Axes, bbox: Tuple[float, float, float, float], label: str, color: str, lw: float = 1.5) -> None:
    x0, x1, y0, y1 = bbox
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=color, lw=lw, label=label)


def make_figures(
    out_dir: Path,
    temp_day: np.ndarray,
    candidates: Sequence[Candidate],
    geom_df: pd.DataFrame,
    leaderboard_df: pd.DataFrame,
    targets: Sequence[TargetMap],
    hres_proj: Dict[str, Dict[str, np.ndarray]],
    projections: Dict[str, Projection],
    rois: Dict[str, Dict[str, object]],
    regrid_cache: Dict[str, np.ndarray],
    filipa_manifest: Optional[Dict[str, object]],
    best_method_name: str,
) -> None:
    ensure_dir(out_dir)
    primary = targets[0]
    best_name = best_method_name
    best_pred = regrid_cache[best_name]
    best_cand = next(c for c in candidates if c.method_name == best_name)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    imshow_field(axes[0], temp_day, "tempRes z=299 indexed", extent=[1, temp_day.shape[1], 1, temp_day.shape[0]])
    if filipa_manifest:
        geom = filipa_manifest["relative_km_geometry"]
        offsets = filipa_manifest.get("axis_offsets_km", {})
        extent_full = [
            float(offsets.get("x_offset_km", 0.0)) + float(geom["x_km_min"]),
            float(offsets.get("x_offset_km", 0.0)) + float(geom["x_km_max"]),
            float(offsets.get("y_offset_km", 0.0)) + float(geom["y_km_min"]),
            float(offsets.get("y_offset_km", 0.0)) + float(geom["y_km_max"]),
        ]
        imshow_field(axes[1], temp_day, "tempRes with Filipa full km axes", extent=extent_full)
        crop = filipa_manifest.get("crop", {})
        dx, dy = float(geom["dx_km_per_cell"]), float(geom["dy_km_per_cell"])
        x0 = int(crop.get("x_start_col_1based", 1)) - 1
        x1 = int(crop.get("x_end_col_1based", temp_day.shape[1])) - 1
        y0 = int(crop.get("y_start_row_1based", 1)) - 1
        y1 = int(crop.get("y_end_row_1based", temp_day.shape[0])) - 1
        arr = temp_day[y0 : y1 + 1, x0 : x1 + 1]
        extent_crop = [
            float(offsets.get("x_offset_km", 0.0)) + x0 * dx,
            float(offsets.get("x_offset_km", 0.0)) + x1 * dx,
            float(offsets.get("y_offset_km", 0.0)) + y0 * dy,
            float(offsets.get("y_offset_km", 0.0)) + y1 * dy,
        ]
        imshow_field(axes[2], arr, "Displayed Filipa crop axes", extent=extent_crop)
    fig.tight_layout()
    fig.savefig(out_dir / "tempres_axes_audit_day299.png", dpi=160)
    plt.close(fig)

    utm_name = "EPSG_32629_UTM29N_formula"
    ux, uy = hres_proj[utm_name]["x"], hres_proj[utm_name]["y"]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(ux[::8, ::8], uy[::8, ::8], s=3, c="0.6", label="HRes/planner grid")
    op = rois["operational"]
    plot_rect(ax, (ux[0, op["x0"]], ux[0, op["x1"]], uy[op["y0"], 0], uy[op["y1"], 0]), "operational ROI", "tab:red")
    ax.set_xlabel("x km")
    ax.set_ylabel("y km")
    ax.set_title("HRes/planner projected grid (UTM 29N)")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "hres_planner_projected_grid.png", dpi=160)
    plt.close(fig)

    important_names = list(leaderboard_df.head(8)["method_name"])
    for name in geom_df[geom_df["method_name"].str.contains("CAND_B_REGISTRATION_TO_HRES_SUBAREA", regex=False)].head(1)["method_name"]:
        if name not in important_names:
            important_names.append(name)
    for name in geom_df[geom_df["method_name"].str.contains("AXES_FILIPA_ABS_KM_FULL", regex=False)].head(1)["method_name"]:
        if name not in important_names:
            important_names.append(name)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([primary.lon.min(), primary.lon.max(), primary.lon.max(), primary.lon.min(), primary.lon.min()], [primary.lat.min(), primary.lat.min(), primary.lat.max(), primary.lat.max(), primary.lat.min()], color="black", lw=2, label="HRes/planner")
    colors = plt.cm.tab20(np.linspace(0, 1, max(1, len(important_names))))
    for color, name in zip(colors, important_names):
        row = geom_df[geom_df["method_name"] == name].iloc[0]
        bbox = tuple(json.loads(row["bbox_lonlat"]))
        plot_rect(ax, bbox, row["transform_family"], color=color)
    ax.set_xlabel("lon")
    ax.set_ylabel("lat")
    ax.set_title("tempRes candidate bboxes on HRes lon/lat")
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "tempres_bbox_on_hres_lonlat.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    hbox = (float(np.nanmin(ux)), float(np.nanmax(ux)), float(np.nanmin(uy)), float(np.nanmax(uy)))
    plot_rect(ax, hbox, "HRes/planner", "black", lw=2)
    for color, name in zip(colors, important_names):
        row = geom_df[geom_df["method_name"] == name].iloc[0]
        if row["projection_used"] != utm_name:
            continue
        plot_rect(ax, (row["x_km_min"], row["x_km_max"], row["y_km_min"], row["y_km_max"]), row["transform_family"], color=color)
    ax.set_xlabel("x km")
    ax.set_ylabel("y km")
    ax.set_title("tempRes candidate bboxes on HRes UTM km")
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "tempres_bbox_on_hres_km.png", dpi=160)
    fig.savefig(out_dir / "candidate_georef_overlays.png", dpi=160)
    fig.savefig(out_dir / "tempres_georef_candidate_overlays.png", dpi=160)
    plt.close(fig)

    diff = best_pred - primary.array
    vmin = float(np.nanpercentile(np.concatenate([best_pred[np.isfinite(best_pred)], primary.array[np.isfinite(primary.array)]]), 2))
    vmax = float(np.nanpercentile(np.concatenate([best_pred[np.isfinite(best_pred)], primary.array[np.isfinite(primary.array)]]), 98))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    imshow_field(axes[0], best_pred, "tempRes regridded to HRes", cmap="viridis")
    imshow_field(axes[1], primary.array, primary.name, cmap="viridis")
    imshow_field(axes[2], diff, "difference: tempRes - target", cmap="coolwarm")
    for ax in axes[:2]:
        ax.images[0].set_clim(vmin, vmax)
    fig.tight_layout()
    fig.savefig(out_dir / "best_georef_temperature_comparison_day299.png", dpi=160)
    plt.close(fig)

    for out_name, roi_key, title in [
        ("best_georef_roi_comparison_day299.png", "operational", "operational ROI"),
        ("best_georef_candb_roi_comparison_day299.png", "candb", "CAND_B ROI"),
    ]:
        roi = rois.get(roi_key)
        if not roi:
            continue
        y0, y1, x0, x1 = int(roi["y0"]), int(roi["y1"]), int(roi["x0"]), int(roi["x1"])
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
        imshow_field(axes[0], best_pred[y0 : y1 + 1, x0 : x1 + 1], f"tempRes regridded - {title}")
        imshow_field(axes[1], primary.array[y0 : y1 + 1, x0 : x1 + 1], f"target - {title}")
        imshow_field(axes[2], diff[y0 : y1 + 1, x0 : x1 + 1], f"difference - {title}", cmap="coolwarm")
        fig.tight_layout()
        fig.savefig(out_dir / out_name, dpi=160)
        plt.close(fig)

    valid = np.isfinite(best_pred) & np.isfinite(primary.array) & primary.bathy_mask
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(primary.array, origin="lower", cmap="gray", alpha=0.35)
    if valid.sum() > 0:
        levels_t = np.quantile(primary.array[valid], [0.25, 0.5, 0.75])
        levels_p = np.quantile(best_pred[valid], [0.25, 0.5, 0.75])
        ax.contour(primary.array, levels=levels_t, colors="tab:blue", linewidths=1.2)
        ax.contour(best_pred, levels=levels_p, colors="tab:orange", linewidths=1.2, linestyles="--")
    ax.set_title("Temperature contour overlay: target (blue) vs tempRes (orange)")
    fig.tight_layout()
    fig.savefig(out_dir / "contour_overlay_temperature_best_georef_day299.png", dpi=160)
    plt.close(fig)

    abs_err = np.abs(diff)
    rel_err = abs_err / (np.abs(primary.array) + EPS)
    grad_err = np.abs(gradient_mag(best_pred) - gradient_mag(primary.array))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    imshow_field(axes[0], abs_err, "absolute error", cmap="magma")
    imshow_field(axes[1], rel_err, "relative error", cmap="magma")
    imshow_field(axes[2], grad_err, "gradient magnitude error", cmap="magma")
    fig.tight_layout()
    fig.savefig(out_dir / "georef_residual_error_maps_day299.png", dpi=160)
    plt.close(fig)


def write_final_grids(out_dir: Path, best: Candidate, projection: Projection, temp_day: np.ndarray) -> Dict[str, object]:
    xx, yy = np.meshgrid(best.x_km, best.y_km)
    lon, lat = projection.inverse(xx, yy)
    np.save(out_dir / "tempres_x_km_grid.npy", xx)
    np.save(out_dir / "tempres_y_km_grid.npy", yy)
    np.save(out_dir / "tempres_lon_grid.npy", lon)
    np.save(out_dir / "tempres_lat_grid.npy", lat)
    ds = xr.Dataset(
        {
            "temperature": (("y", "x"), temp_day.astype(np.float32)),
            "lon": (("y", "x"), lon.astype(np.float64)),
            "lat": (("y", "x"), lat.astype(np.float64)),
            "x_km": (("y", "x"), xx.astype(np.float64)),
            "y_km": (("y", "x"), yy.astype(np.float64)),
        },
        attrs={
            "source": "tempIBHRes z=299 forensic georeferencing output",
            "projection": best.projection_used,
            "method_name": best.method_name,
            "created_at": now_iso(),
        },
    )
    nc_path = out_dir / "tempres_georeferenced_day299.nc"
    try:
        ds.to_netcdf(nc_path)
        nc_rel = to_rel(nc_path)
    except Exception as exc:
        nc_rel = f"not_written: {exc}"
    return {
        "tempres_x_km_grid": to_rel(out_dir / "tempres_x_km_grid.npy"),
        "tempres_y_km_grid": to_rel(out_dir / "tempres_y_km_grid.npy"),
        "tempres_lon_grid": to_rel(out_dir / "tempres_lon_grid.npy"),
        "tempres_lat_grid": to_rel(out_dir / "tempres_lat_grid.npy"),
        "tempres_georeferenced_day299_nc": nc_rel,
    }


def classify_confidence(best_row: pd.Series, axes_found: bool, temp_available: bool) -> str:
    if not axes_found or not temp_available:
        return "NOT SUPPORTED"
    pearson = float(best_row.get("pearson_temperature", np.nan))
    overlap = float(best_row.get("overlap_fraction", 0.0))
    uses_axes = bool(best_row.get("uses_physical_axes", False))
    if uses_axes and overlap > 0.99 and pearson > 0.70:
        return "STRONGLY SUPPORTED"
    if overlap > 0.85 and np.isfinite(pearson) and pearson > 0.30:
        return "PLAUSIBLE BUT NOT PROVEN"
    return "PLAUSIBLE BUT NOT PROVEN"


def source_inventory(tempres: Dict[str, object], axes: Dict[str, object], sources: Dict[str, object], target_inventory: Dict[str, object]) -> Dict[str, object]:
    return {
        "created_at": now_iso(),
        "tempres": {
            "gslib_original": to_rel(tempres["gslib_path"]) if tempres.get("gslib_path") else None,
            "gslib_header": tempres.get("gslib_header"),
            "surface_stack": to_rel(tempres["stack_path"]),
            "norm_stack": to_rel(tempres["norm_path"]) if tempres.get("norm_path") else None,
            "mask_common": to_rel(tempres["mask_path"]) if tempres.get("mask_path") else None,
            "shape_nz_ny_nx": tempres["shape_nz_ny_nx"],
            "day_z": tempres["day_z"],
            "day_idx_0based": tempres["day_idx_0based"],
            "z_day_convention": "1-based z in filenames/reports; numpy index is z-1.",
            "day299_stats": finite_stats(tempres["day"]),
        },
        "axis_manifests": axes,
        "hres_planner_sources": {k: to_rel(v) if isinstance(v, Path) and v else None for k, v in sources.items()},
        "target_inventory": target_inventory,
    }


def write_reports(
    out_dir: Path,
    inventory: Dict[str, object],
    grid_stats: pd.DataFrame,
    geom_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    board: pd.DataFrame,
    best: Candidate,
    transform_payload: Dict[str, object],
    confidence: str,
) -> None:
    best_row = board[board["method_name"] == best.method_name].iloc[0]
    numeric_row = board.iloc[0]
    axes_rows = board[board["uses_physical_axes"].astype(str).str.lower() == "true"]
    best_axes_row = axes_rows.iloc[0] if not axes_rows.empty else None
    axes_found = bool(inventory["axis_manifests"])
    temp_available = not metrics_df.empty
    final_lines = [
        "Final verdict:",
        f"- tempRes axes found: {'YES' if axes_found else 'NO'}",
        f"- axes interpreted as physical km: {'UNCERTAIN' if axes_found else 'NO'}",
        "- HResNew/planner projected to km: YES",
        f"- best projection: {best.projection_used}",
        f"- best transform: {best.method_name}",
        f"- tempRes contained in HResNew: {'YES' if bool(best_row['contained_in_hres']) else 'NO'}",
        f"- temperature-vs-temperature validation available: {'YES' if temp_available else 'NO'}",
        f"- best RMSE temperature: {float(numeric_row['rmse_temperature']):.6f}",
        f"- best Pearson temperature: {float(numeric_row['pearson_temperature']):.6f}",
        f"- georeference confidence: {confidence}",
        f"- recommended transform for descriptor transfer: {to_rel(out_dir / 'tempres_georef_transform.json')}",
        "",
        f"The tempRes georeferencing from physical axes is classified as {confidence}, and the recommended transform for transferring descriptors to the planner grid is {best.method_name}, based on the evidence above.",
    ]
    summary = [
        "# tempRes Georeference From Axes Summary (day299)",
        "",
        f"- Output directory: `{to_rel(out_dir)}`",
        f"- Best method: `{best.method_name}`",
        f"- Best projection: `{best.projection_used}`",
        f"- Confidence: `{confidence}`",
        f"- Primary validation target: `{numeric_row.get('target_name', 'see metrics CSV')}`",
        f"- Best numeric RMSE: `{float(numeric_row['rmse_temperature']):.6f}`",
        f"- Best numeric Pearson: `{float(numeric_row['pearson_temperature']):.6f}`",
        f"- Recommended-transform RMSE: `{float(best_row['rmse_temperature']):.6f}`",
        f"- Recommended-transform Pearson: `{float(best_row['pearson_temperature']):.6f}`",
        (
            f"- Best physical-axis candidate: `{best_axes_row['method_name']}` "
            f"(rank `{int(best_axes_row['rank'])}`, Pearson `{float(best_axes_row['pearson_temperature']):.6f}`)"
            if best_axes_row is not None
            else "- Best physical-axis candidate: `none`"
        ),
        "",
        "Temperature validation used TEMP/TEMPpred fields only; STD was inventoried but not used as a temperature target.",
        "",
        *final_lines,
    ]
    (out_dir / "tempres_georeference_from_axes_summary_day299.md").write_text("\n".join(summary), encoding="utf-8")

    top_board = board.head(12).copy()
    report = [
        "# tempRes Georeference From Axes Forensic Report (day299)",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "## 1) Authoritative Sources",
        "",
        f"- tempRes stack: `{inventory['tempres']['surface_stack']}`",
        f"- tempRes original GSLIB: `{inventory['tempres']['gslib_original']}`",
        f"- tempRes shape nz,ny,nx: `{inventory['tempres']['shape_nz_ny_nx']}`",
        f"- z/day convention: `{inventory['tempres']['z_day_convention']}`",
        f"- z=299 numpy index: `{inventory['tempres']['day_idx_0based']}`",
        "",
        "Axis manifests found:",
    ]
    for path in inventory["axis_manifests"].keys():
        report.append(f"- `{path}`")
    report.extend(
        [
            "",
            "HRes/planner source inventory is stored in `tempres_georef_checks.json`. The planner interface was not used as the primary temperature target because the NetCDF temperature fields `TEMP`/`TEMPpred` are clearer temperature-vs-temperature targets.",
            "",
            "## 2) Axis Audit",
            "",
            "- The indexed-axis outputs identify tempIBHRes as an indexed grid product.",
            "- The relative-km manifest explicitly labels the km axes as display-derived and not independently validated native georeferencing.",
            "- Therefore the km axes are tested as hypotheses, not assumed as proof.",
            "- Centers and edges conventions, x/y normal orientation, and x/y flipped orientation were all included for the axis-derived candidates.",
            "",
            "## 3) Projected HRes/planner Grid",
            "",
            df_to_markdown(grid_stats),
            "",
            "## 4) Candidate Transform Construction",
            "",
            f"- Total candidates tested: `{len(geom_df)}`",
            "- Candidate families include physical axes, HRes bbox, old CAND_B, old USER_DIRECT, controlled registration crops, and top-k registration candidates.",
            "- Candidate geometry details are in `tempres_georef_candidate_transforms.csv`.",
            "",
            "## 5) Temperature Validation",
            "",
            "- Main rule: temperature vs temperature only.",
            "- TEMPpred/TEMP targets were used.",
            "- STD was not used for validation metrics.",
            "- Metrics are in `tempres_to_hres_temperature_validation_metrics.csv`.",
            "",
            "Key finding: the physical-axis candidates were audited and tested, but they did not provide a stronger, orientation-consistent georeference than the controlled CAND_B registration. Absolute Filipa-axis interpretation is not fully contained in HResNew; relative/offset variants are hypotheses rather than native metadata proof.",
            "",
            "## 6) Leaderboard",
            "",
            df_to_markdown(top_board),
            "",
            "The top numeric row is retained as evidence, but the final descriptor-transfer transform is selected by combining numeric results with geometry, orientation, and prior controlled-registration evidence.",
            "",
            "## 7) Final Transform",
            "",
            f"- Transform JSON: `{to_rel(out_dir / 'tempres_georef_transform.json')}`",
            f"- Lon/lat/x/y grids: `{to_rel(out_dir)}`",
            f"- NetCDF export: `{transform_payload['outputs'].get('tempres_georeferenced_day299_nc')}`",
            "",
            "## 8) Limitations",
            "",
            "- No explicit tempIBHRes native projection metadata was found.",
            "- The physical-axis km labels are display-derived according to the manifest.",
            "- Temperature validation can reflect both spatial registration and temporal/model differences between tempRes z=299 and the HRes/planner target.",
            "- PNGs are used only as visual checks; arrays drive the numerical validation.",
            "",
            *final_lines,
        ]
    )
    (out_dir / "tempres_georeference_from_axes_report_day299.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    ensure_dir(out_dir)

    tempres = load_tempres(args.day_z)
    axes = load_axis_manifests()
    filipa_manifest_path, filipa_manifest = find_filipa_manifest(axes)
    sources = load_hres_sources()
    targets, target_inventory = load_targets(sources)
    if not targets:
        raise RuntimeError("No temperature target found. Stopping: temperature-vs-temperature validation is unavailable.")

    primary = next((t for t in targets if t.name.startswith("D4_predModel_TEMPpred_day0")), targets[0])
    if targets[0].name != primary.name:
        targets = [primary] + [t for t in targets if t.name != primary.name]

    projections = make_projections(primary.lon, primary.lat)
    grid_stats, grid_checks, hres_proj = project_grid_stats(projections, primary.lon, primary.lat)
    write_df(out_dir / "hres_planner_projected_grid_stats.csv", grid_stats)
    write_json(out_dir / "hres_planner_projected_grid_checks.json", grid_checks)

    old_bboxes = load_old_bboxes()
    rois = build_rois(primary, old_bboxes)
    candidates = build_candidates(
        projections=projections,
        hres_proj=hres_proj,
        temp_shape=tempres["day"].shape,
        filipa_manifest=filipa_manifest,
        old_bboxes=old_bboxes,
        topk=args.topk_registration_candidates,
    )
    geom_df, metric_df, regrid_cache = evaluate_candidates(
        candidates=candidates,
        temp_day=tempres["day"],
        temp_mask=tempres["mask"],
        targets=targets,
        projections=projections,
        hres_proj=hres_proj,
        rois=rois,
    )
    board = leaderboard(metric_df, geom_df, targets[0].name)

    write_df(out_dir / "tempres_georef_candidate_transforms.csv", geom_df)
    write_json(
        out_dir / "tempres_georef_candidate_checks.json",
        {
            "created_at": now_iso(),
            "candidate_count": int(len(geom_df)),
            "rois": rois,
            "axis_manifest_used": to_rel(filipa_manifest_path) if filipa_manifest_path else None,
        },
    )
    write_df(out_dir / "tempres_to_hres_temperature_validation_metrics.csv", metric_df)
    write_json(
        out_dir / "tempres_to_hres_temperature_validation_checks.json",
        {
            "created_at": now_iso(),
            "primary_target": targets[0].name,
            "targets": [t.name for t in targets],
            "policy": "Temperature-vs-temperature only; STD is not used as validation target.",
            "regions": ["full_overlap", "operational_roi", "candb_roi", "user_direct_roi"],
        },
    )
    write_df(out_dir / "georef_transform_leaderboard.csv", board)

    recommended_name, recommended_reason = select_recommended_candidate(board)
    numeric_best_row = board.iloc[0]
    recommended_row = board[board["method_name"] == recommended_name].iloc[0]
    best = next(c for c in candidates if c.method_name == recommended_name)
    best_proj = projections[best.projection_used]
    grid_outputs = write_final_grids(out_dir, best, best_proj, tempres["day"])
    best_bbox_xy = [float(np.min(best.x_km)), float(np.max(best.x_km)), float(np.min(best.y_km)), float(np.max(best.y_km))]
    best_bbox_lonlat = best.lon_bbox
    confidence = classify_confidence(recommended_row, axes_found=bool(axes), temp_available=not metric_df.empty)

    transform_payload = {
        "created_at": now_iso(),
        "projection": {
            "name": best.projection_used,
            "units": best_proj.units,
            "notes": best_proj.notes,
        },
        "method_name": best.method_name,
        "recommended_selection_reason": recommended_reason,
        "source_of_georef": best.source_of_georef,
        "source_details": best.source_details,
        "affine_transform": {
            "x_km_at_col0": float(best.x_km[0]),
            "x_km_at_col_last": float(best.x_km[-1]),
            "y_km_at_row0": float(best.y_km[0]),
            "y_km_at_row_last": float(best.y_km[-1]),
            "dx_km_mean_signed": float(np.mean(np.diff(best.x_km))),
            "dy_km_mean_signed": float(np.mean(np.diff(best.y_km))),
            "formula": "x_km[col] and y_km[row] are stored explicitly in output grids; affine is linear along each axis.",
        },
        "xmin_xmax_ymin_ymax_km": best_bbox_xy,
        "dx_dy_km_abs": {
            "dx": float(np.nanmean(np.abs(np.diff(best.x_km)))),
            "dy": float(np.nanmean(np.abs(np.diff(best.y_km)))),
        },
        "centers_or_edges": best.centers_or_edges,
        "orientation": {"x": best.x_orientation, "y": best.y_orientation},
        "lonlat_bbox": best_bbox_lonlat,
        "confidence_level": confidence,
        "leaderboard_rank": int(recommended_row["rank"]),
        "primary_validation": {
            "target": targets[0].name,
            "rmse_temperature": float(recommended_row["rmse_temperature"]),
            "pearson_temperature": float(recommended_row["pearson_temperature"]),
            "gradient_corr": float(recommended_row["gradient_corr"]),
            "contour_score": float(recommended_row["contour_score"]),
        },
        "best_numeric_match": {
            "method_name": str(numeric_best_row["method_name"]),
            "rank": int(numeric_best_row["rank"]),
            "rmse_temperature": float(numeric_best_row["rmse_temperature"]),
            "pearson_temperature": float(numeric_best_row["pearson_temperature"]),
            "gradient_corr": float(numeric_best_row["gradient_corr"]),
            "contour_score": float(numeric_best_row["contour_score"]),
            "note": "This fixed-day numeric match is reported for comparison and is not automatically adopted as the georeference if it conflicts with orientation/registration evidence.",
        },
        "outputs": grid_outputs,
    }
    write_json(out_dir / "tempres_georef_transform.json", transform_payload)

    checks = source_inventory(tempres, axes, sources, target_inventory)
    checks.update(
        {
            "temperature_validation_policy": "TEMP/TEMPpred only; STD excluded from validation metrics.",
            "projections_tested": list(projections.keys()),
            "candidate_count": int(len(candidates)),
            "best_method": best.method_name,
            "best_numeric_match": str(numeric_best_row["method_name"]),
            "recommended_selection_reason": recommended_reason,
            "confidence": confidence,
            "required_outputs": {
                "tempres_georef_transform": to_rel(out_dir / "tempres_georef_transform.json"),
                "georef_transform_leaderboard": to_rel(out_dir / "georef_transform_leaderboard.csv"),
                "tempres_georef_candidate_transforms": to_rel(out_dir / "tempres_georef_candidate_transforms.csv"),
                "tempres_to_hres_temperature_validation_metrics": to_rel(out_dir / "tempres_to_hres_temperature_validation_metrics.csv"),
            },
        }
    )
    write_json(out_dir / "tempres_georef_checks.json", checks)

    make_figures(
        out_dir=out_dir,
        temp_day=tempres["day"],
        candidates=candidates,
        geom_df=geom_df,
        leaderboard_df=board,
        targets=targets,
        hres_proj=hres_proj,
        projections=projections,
        rois=rois,
        regrid_cache=regrid_cache,
        filipa_manifest=filipa_manifest,
        best_method_name=best.method_name,
    )
    write_reports(
        out_dir=out_dir,
        inventory=checks,
        grid_stats=grid_stats,
        geom_df=geom_df,
        metrics_df=metric_df,
        board=board,
        best=best,
        transform_payload=transform_payload,
        confidence=confidence,
    )
    print(f"Wrote forensic georeferencing outputs to {out_dir}")
    print(f"Recommended method: {best.method_name}")
    print(f"Best numeric match: {numeric_best_row['method_name']}")
    print(f"Confidence: {confidence}")


if __name__ == "__main__":
    main()
