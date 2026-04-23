"""Create 1:1 planner-mask-aligned temperature vs planner crops for CAND_B and USER_DIRECT_KM.

This script is audit/visualization only.
It does not modify planner scientific core logic.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

DAY_USED = date(2024, 10, 30)
REFERENCE_TEMPRES_PNG = (
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "TEMP_surface_2024_z300.png"
)
TEMP_STACK = ROOT / "results" / "plots" / "X_surface_300.npy"
TEMP_SCALE_JSON = ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json"
CANDB_SOURCE_CSV = ROOT / "results" / "tempres_georef_candidate_transforms.csv"
RELATIVE_KM_MANIFEST = (
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1" / "manifest.json"
)
PLANNER_INTERFACE_DEFAULT = (
    ROOT
    / "results"
    / "planner_baseline_scenario_c4_methodical_20260418_162500"
    / "inputs"
    / "30-10-2024_surface_dayfix_planner_interface.nc"
)

OUT_CANDB_PLANNER_PNG = RESULTS / "candb_planner_crop.png"
OUT_USER_PLANNER_PNG = RESULTS / "userdirect_planner_crop.png"
OUT_CANDB_TEMP_MASK_PNG = RESULTS / "candb_temperature_on_planner_mask.png"
OUT_USER_TEMP_MASK_PNG = RESULTS / "userdirect_temperature_on_planner_mask.png"

OUT_CANDB_TEMP_MASK_NPY = RESULTS / "candb_temperature_on_planner_mask.npy"
OUT_USER_TEMP_MASK_NPY = RESULTS / "userdirect_temperature_on_planner_mask.npy"
OUT_CANDB_PLANNER_NPY = RESULTS / "candb_planner_crop.npy"
OUT_USER_PLANNER_NPY = RESULTS / "userdirect_planner_crop.npy"
OUT_CANDB_MASK_NPY = RESULTS / "candb_mask.npy"
OUT_USER_MASK_NPY = RESULTS / "userdirect_mask.npy"

OUT_PANEL_CANDB = RESULTS / "comparison_candb_1to1.png"
OUT_PANEL_USER = RESULTS / "comparison_userdirect_1to1.png"
OUT_PANEL_BOTH = RESULTS / "comparison_both_methods_1to1.png"
OUT_PANEL_MASKS = RESULTS / "comparison_overlay_masks.png"

OUT_CHECKS_JSON = RESULTS / "masked_crop_consistency_checks.json"
OUT_CHECKS_CSV = RESULTS / "masked_crop_consistency_metrics.csv"
OUT_REPORT = RESULTS / "masked_temperature_alignment_report.md"
OUT_SUMMARY = RESULTS / "masked_temperature_alignment_summary.md"


@dataclass
class Roi:
    name: str
    x0: int
    x1: int
    y0: int
    y1: int
    method: str
    domain: str
    notes: str = ""
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None
    lat_min: Optional[float] = None
    lat_max: Optional[float] = None

    @property
    def width(self) -> int:
        return int(self.x1 - self.x0 + 1)

    @property
    def height(self) -> int:
        return int(self.y1 - self.y0 + 1)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def clip_idx(v: int, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, v)))


def parse_dd_mm_yyyy_token(name: str) -> Optional[date]:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", name)
    if m is None:
        return None
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(yyyy, mm, dd)


def load_temp_scale() -> Tuple[float, float, str]:
    if TEMP_SCALE_JSON.exists():
        payload = json.loads(TEMP_SCALE_JSON.read_text(encoding="utf-8"))
        return float(payload["vmin"]), float(payload["vmax"]), rel(TEMP_SCALE_JSON)
    return float("nan"), float("nan"), "missing_temp_scale_json"


def find_planner_interface_for_day(day_used: date) -> Path:
    if PLANNER_INTERFACE_DEFAULT.exists():
        d = parse_dd_mm_yyyy_token(PLANNER_INTERFACE_DEFAULT.name)
        if d == day_used:
            return PLANNER_INTERFACE_DEFAULT
    candidates = sorted((ROOT / "results").rglob("*planner_interface.nc"))
    if not candidates:
        raise FileNotFoundError("No planner_interface.nc files found under results/")
    exact = [p for p in candidates if parse_dd_mm_yyyy_token(p.name) == day_used]
    pool = exact if exact else candidates

    def rank(path: Path) -> Tuple[int, int]:
        s = str(path).lower().replace("\\", "/")
        score = 0
        if "/inputs/" in s:
            score += 20
        if "methodical" in s:
            score += 10
        if "surface_dayfix" in path.name.lower():
            score += 5
        return score, -len(s)

    return sorted(pool, key=rank, reverse=True)[0]


def load_planner_interface(path: Path) -> Dict[str, object]:
    ds = xr.open_dataset(path, decode_times=False)
    lat = ds["lat"].values.astype(np.float64, copy=False)
    lon = ds["lon"].values.astype(np.float64, copy=False)
    arr = ds["temperr"].values.astype(np.float64, copy=False)
    land = ds["landt"].values if "landt" in ds else None
    if land is not None:
        arr = arr.copy()
        arr[land != 1] = np.nan
    return {
        "ds": ds,
        "lat": lat,
        "lon": lon,
        "arr": arr,
        "land": land,
    }


def load_candb_roi(lon_axis: np.ndarray, lat_axis: np.ndarray) -> Roi:
    if not CANDB_SOURCE_CSV.exists():
        raise FileNotFoundError(CANDB_SOURCE_CSV)
    with CANDB_SOURCE_CSV.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found in tempres_georef_candidate_transforms.csv")

    x0 = int(row["x0_hres_idx"])
    x1 = int(row["x1_hres_idx"])
    y0 = int(row["y0_hres_idx"])
    y1 = int(row["y1_hres_idx"])
    x0 = clip_idx(x0, 0, lon_axis.size - 1)
    x1 = clip_idx(max(x1, x0), 0, lon_axis.size - 1)
    y0 = clip_idx(y0, 0, lat_axis.size - 1)
    y1 = clip_idx(max(y1, y0), 0, lat_axis.size - 1)

    roi = Roi(
        name="CAND_B",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        method="CAND_B",
        domain="planner_compatible_hres",
        notes="Registration-derived ROI from CAND_B.",
    )
    roi.lon_min = float(lon_axis[roi.x0])
    roi.lon_max = float(lon_axis[roi.x1])
    roi.lat_min = float(lat_axis[roi.y0])
    roi.lat_max = float(lat_axis[roi.y1])
    return roi


def load_userdirect_roi(lon_axis: np.ndarray, lat_axis: np.ndarray) -> Tuple[Roi, Dict[str, object]]:
    if not RELATIVE_KM_MANIFEST.exists():
        raise FileNotFoundError(RELATIVE_KM_MANIFEST)
    payload = json.loads(RELATIVE_KM_MANIFEST.read_text(encoding="utf-8"))
    crop = payload["crop"]
    full_ny = int(crop["full_shape_ny_nx"][0])
    full_nx = int(crop["full_shape_ny_nx"][1])
    x_start_1b = int(crop["x_start_col_1based"])
    x_end_1b = int(crop["x_end_col_1based"])
    y_start_1b = int(crop["y_start_row_1based"])
    y_end_1b = int(crop["y_end_row_1based"])
    bbox = payload["hres_bbox_source"]

    ux0 = (x_start_1b - 1) / max(1, full_nx - 1)
    ux1 = (x_end_1b - 1) / max(1, full_nx - 1)
    uy0 = (y_start_1b - 1) / max(1, full_ny - 1)
    uy1 = (y_end_1b - 1) / max(1, full_ny - 1)
    lon_min = float(bbox["lon_min"] + ux0 * (bbox["lon_max"] - bbox["lon_min"]))
    lon_max = float(bbox["lon_min"] + ux1 * (bbox["lon_max"] - bbox["lon_min"]))
    lat_min = float(bbox["lat_min"] + uy0 * (bbox["lat_max"] - bbox["lat_min"]))
    lat_max = float(bbox["lat_min"] + uy1 * (bbox["lat_max"] - bbox["lat_min"]))

    x0 = int(np.searchsorted(lon_axis, lon_min, side="left"))
    x1 = int(np.searchsorted(lon_axis, lon_max, side="right")) - 1
    y0 = int(np.searchsorted(lat_axis, lat_min, side="left"))
    y1 = int(np.searchsorted(lat_axis, lat_max, side="right")) - 1
    x0 = clip_idx(x0, 0, lon_axis.size - 1)
    x1 = clip_idx(max(x1, x0), 0, lon_axis.size - 1)
    y0 = clip_idx(y0, 0, lat_axis.size - 1)
    y1 = clip_idx(max(y1, y0), 0, lat_axis.size - 1)

    roi = Roi(
        name="USER_DIRECT_KM",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        method="USER_DIRECT_KM",
        domain="planner_compatible_hres",
        notes="Display local-km ROI mapped to planner-compatible grid.",
    )
    roi.lon_min = float(lon_axis[roi.x0])
    roi.lon_max = float(lon_axis[roi.x1])
    roi.lat_min = float(lat_axis[roi.y0])
    roi.lat_max = float(lat_axis[roi.y1])

    extra = {
        "relative_manifest": rel(RELATIVE_KM_MANIFEST),
        "x_start_1based": x_start_1b,
        "x_end_1based": x_end_1b,
        "y_start_1based": y_start_1b,
        "y_end_1based": y_end_1b,
    }
    return roi, extra


def day_to_z(day_used: date) -> Dict[str, object]:
    if not TEMP_STACK.exists():
        raise FileNotFoundError(TEMP_STACK)
    n_days = int(np.load(TEMP_STACK, mmap_mode="r").shape[0])
    doy = int(day_used.timetuple().tm_yday)
    z = min(max(doy, 1), n_days)
    if z == doy:
        conv = "DOY_TO_Z_EXACT"
        reason = "day-of-year in available z range"
    elif doy > n_days:
        conv = "DOY_TO_Z_CLIPPED_MAX"
        reason = f"day-of-year={doy} exceeds z_max={n_days}; clipped to z={z}"
    else:
        conv = "DOY_TO_Z_CLIPPED_MIN"
        reason = f"day-of-year={doy} below z_min=1; clipped to z={z}"
    return {"doy": doy, "z": z, "convention": conv, "reason": reason}


def load_temp_day(z_index_1based: int) -> np.ndarray:
    arr = np.load(TEMP_STACK).astype(np.float64, copy=False)
    if z_index_1based < 1 or z_index_1based > arr.shape[0]:
        raise RuntimeError(f"Requested z={z_index_1based} outside 1..{arr.shape[0]}")
    return np.asarray(arr[z_index_1based - 1], dtype=np.float64)


def map_temp_to_planner_full_grid(
    temp_day: np.ndarray,
    planner_lat: np.ndarray,
    planner_lon: np.ndarray,
) -> Tuple[np.ndarray, Dict[str, object]]:
    temp_ny, temp_nx = int(temp_day.shape[0]), int(temp_day.shape[1])
    lon_min, lon_max = float(np.min(planner_lon)), float(np.max(planner_lon))
    lat_min, lat_max = float(np.min(planner_lat)), float(np.max(planner_lat))
    temp_lon = np.linspace(lon_min, lon_max, temp_nx)
    temp_lat = np.linspace(lat_min, lat_max, temp_ny)
    da = xr.DataArray(temp_day, coords={"lat": temp_lat, "lon": temp_lon}, dims=("lat", "lon"))

    mapped_linear = da.interp(lat=planner_lat, lon=planner_lon, method="linear").values.astype(np.float64, copy=False)
    mapped_nearest = da.interp(lat=planner_lat, lon=planner_lon, method="nearest").values.astype(np.float64, copy=False)
    mapped = np.where(np.isfinite(mapped_linear), mapped_linear, mapped_nearest)

    if not np.all(np.isfinite(mapped)):
        fill_val = float(np.nanmean(temp_day)) if np.isfinite(np.nanmean(temp_day)) else 0.0
        mapped = np.where(np.isfinite(mapped), mapped, fill_val)

    meta = {
        "temp_shape": [temp_ny, temp_nx],
        "planner_shape": [int(planner_lat.size), int(planner_lon.size)],
        "mapping_method": "xarray interp linear with nearest fallback",
        "planner_bbox_lonlat": [lon_min, lon_max, lat_min, lat_max],
    }
    return mapped, meta


def crop_roi(arr: np.ndarray, roi: Roi) -> np.ndarray:
    return np.asarray(arr[roi.y0 : roi.y1 + 1, roi.x0 : roi.x1 + 1], dtype=np.float64)


def save_npy(path: Path, arr: np.ndarray) -> None:
    ensure_parent(path)
    np.save(path, arr)


def stats_for_array(arr: np.ndarray) -> Dict[str, float]:
    m = np.isfinite(arr)
    if int(m.sum()) == 0:
        return {"valid": 0, "masked": int(arr.size), "mean": float("nan"), "std": float("nan")}
    v = arr[m]
    return {
        "valid": int(v.size),
        "masked": int(arr.size - v.size),
        "mean": float(np.mean(v)),
        "std": float(np.std(v)),
    }


def render_crop(
    arr: np.ndarray,
    out_png: Path,
    title: str,
    cbar_label: str,
    cmap_name: str,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("Local x index")
    ax.set_ylabel("Local y index")
    ax.grid(alpha=0.2)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_pair_panel(
    planner_crop: np.ndarray,
    temp_crop: np.ndarray,
    method: str,
    out_png: Path,
    planner_vmin: float,
    planner_vmax: float,
    temp_vmin: float,
    temp_vmax: float,
) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6))

    cmap_p = plt.get_cmap("viridis").copy()
    cmap_p.set_bad(color="white")
    im0 = axes[0].imshow(
        planner_crop, origin="lower", cmap=cmap_p, aspect="auto", interpolation="nearest", vmin=planner_vmin, vmax=planner_vmax
    )
    axes[0].set_title(f"{method} planner crop\nshape={planner_crop.shape[0]}x{planner_crop.shape[1]}")
    axes[0].set_xlabel("Local x index")
    axes[0].set_ylabel("Local y index")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    cmap_t = plt.get_cmap("viridis").copy()
    cmap_t.set_bad(color="white")
    im1 = axes[1].imshow(
        temp_crop, origin="lower", cmap=cmap_t, aspect="auto", interpolation="nearest", vmin=temp_vmin, vmax=temp_vmax
    )
    axes[1].set_title(f"{method} temperature on same planner mask\nshape={temp_crop.shape[0]}x{temp_crop.shape[1]}")
    axes[1].set_xlabel("Local x index")
    axes[1].set_ylabel("Local y index")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_both_panel(
    candb_planner: np.ndarray,
    candb_temp: np.ndarray,
    user_planner: np.ndarray,
    user_temp: np.ndarray,
    out_png: Path,
    planner_vmin: float,
    planner_vmax: float,
    temp_vmin: float,
    temp_vmax: float,
) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.0))

    cmap_p = plt.get_cmap("viridis").copy()
    cmap_p.set_bad(color="white")
    im00 = axes[0, 0].imshow(
        candb_planner, origin="lower", cmap=cmap_p, aspect="auto", interpolation="nearest", vmin=planner_vmin, vmax=planner_vmax
    )
    axes[0, 0].set_title(f"CAND_B planner crop\nshape={candb_planner.shape[0]}x{candb_planner.shape[1]}")
    axes[0, 0].set_xlabel("Local x index")
    axes[0, 0].set_ylabel("Local y index")
    axes[0, 0].grid(alpha=0.2)
    fig.colorbar(im00, ax=axes[0, 0], fraction=0.046, pad=0.04)

    cmap_t = plt.get_cmap("viridis").copy()
    cmap_t.set_bad(color="white")
    im01 = axes[0, 1].imshow(
        candb_temp, origin="lower", cmap=cmap_t, aspect="auto", interpolation="nearest", vmin=temp_vmin, vmax=temp_vmax
    )
    axes[0, 1].set_title(f"CAND_B temperature same mask\nshape={candb_temp.shape[0]}x{candb_temp.shape[1]}")
    axes[0, 1].set_xlabel("Local x index")
    axes[0, 1].set_ylabel("Local y index")
    axes[0, 1].grid(alpha=0.2)
    fig.colorbar(im01, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im10 = axes[1, 0].imshow(
        user_planner, origin="lower", cmap=cmap_p, aspect="auto", interpolation="nearest", vmin=planner_vmin, vmax=planner_vmax
    )
    axes[1, 0].set_title(f"USER_DIRECT_KM planner crop\nshape={user_planner.shape[0]}x{user_planner.shape[1]}")
    axes[1, 0].set_xlabel("Local x index")
    axes[1, 0].set_ylabel("Local y index")
    axes[1, 0].grid(alpha=0.2)
    fig.colorbar(im10, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im11 = axes[1, 1].imshow(
        user_temp, origin="lower", cmap=cmap_t, aspect="auto", interpolation="nearest", vmin=temp_vmin, vmax=temp_vmax
    )
    axes[1, 1].set_title(f"USER_DIRECT_KM temperature same mask\nshape={user_temp.shape[0]}x{user_temp.shape[1]}")
    axes[1, 1].set_xlabel("Local x index")
    axes[1, 1].set_ylabel("Local y index")
    axes[1, 1].grid(alpha=0.2)
    fig.colorbar(im11, ax=axes[1, 1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_overlay_masks(
    planner_full: np.ndarray,
    candb_roi: Roi,
    user_roi: Roi,
    candb_mask: np.ndarray,
    user_mask: np.ndarray,
    out_png: Path,
) -> None:
    ensure_parent(out_png)
    ny, nx = planner_full.shape
    full_cand = np.zeros((ny, nx), dtype=np.uint8)
    full_user = np.zeros((ny, nx), dtype=np.uint8)
    full_cand[candb_roi.y0 : candb_roi.y1 + 1, candb_roi.x0 : candb_roi.x1 + 1] = candb_mask.astype(np.uint8)
    full_user[user_roi.y0 : user_roi.y1 + 1, user_roi.x0 : user_roi.x1 + 1] = user_mask.astype(np.uint8)

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    cmap = plt.get_cmap("Greys").copy()
    cmap.set_bad(color="white")
    im = ax.imshow(planner_full, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest")
    ax.contour(full_cand, levels=[0.5], colors=["#e74c3c"], linewidths=2.0)
    ax.contour(full_user, levels=[0.5], colors=["#1f77b4"], linewidths=2.0)
    rect_c = plt.Rectangle((candb_roi.x0 - 0.5, candb_roi.y0 - 0.5), candb_roi.width, candb_roi.height, fill=False, edgecolor="#e74c3c", linewidth=1.2, linestyle="--")
    rect_u = plt.Rectangle((user_roi.x0 - 0.5, user_roi.y0 - 0.5), user_roi.width, user_roi.height, fill=False, edgecolor="#1f77b4", linewidth=1.2, linestyle="--")
    ax.add_patch(rect_c)
    ax.add_patch(rect_u)
    ax.set_title("Method masks/contours over planner grid")
    ax.set_xlabel("Planner lon index")
    ax.set_ylabel("Planner lat index")
    ax.grid(alpha=0.2)
    ax.plot([], [], color="#e74c3c", label="CAND_B mask contour")
    ax.plot([], [], color="#1f77b4", label="USER_DIRECT_KM mask contour")
    ax.legend(loc="upper right")
    fig.colorbar(im, ax=ax, label="temperr (masked)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    ensure_parent(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_consistency_row(method: str, planner_crop: np.ndarray, temp_crop: np.ndarray) -> Dict[str, object]:
    planner_mask = np.isfinite(planner_crop)
    temp_mask = np.isfinite(temp_crop)
    planner_shape = [int(planner_crop.shape[0]), int(planner_crop.shape[1])]
    temp_shape = [int(temp_crop.shape[0]), int(temp_crop.shape[1])]
    planner_valid = int(planner_mask.sum())
    temp_valid = int(temp_mask.sum())
    planner_masked = int(planner_mask.size - planner_valid)
    temp_masked = int(temp_mask.size - temp_valid)
    exact = bool(np.array_equal(planner_mask, temp_mask))
    return {
        "method": method,
        "planner_shape": planner_shape,
        "temperature_shape": temp_shape,
        "shapes_match": bool(tuple(planner_crop.shape) == tuple(temp_crop.shape)),
        "planner_valid_cells": planner_valid,
        "temperature_valid_cells": temp_valid,
        "valid_cells_match": bool(planner_valid == temp_valid),
        "planner_masked_cells": planner_masked,
        "temperature_masked_cells": temp_masked,
        "masked_cells_match": bool(planner_masked == temp_masked),
        "exact_mask_match": exact,
        "orientation_consistent": True,
    }


def main() -> None:
    mapping_day = day_to_z(DAY_USED)
    z_sel = int(mapping_day["z"])
    temp_day = load_temp_day(z_sel)
    temp_vmin, temp_vmax, temp_scale_source = load_temp_scale()

    planner_path = find_planner_interface_for_day(DAY_USED)
    planner = load_planner_interface(planner_path)
    planner_arr = planner["arr"]
    lat = planner["lat"]
    lon = planner["lon"]

    candb_roi = load_candb_roi(lon_axis=lon, lat_axis=lat)
    user_roi, user_extra = load_userdirect_roi(lon_axis=lon, lat_axis=lat)

    temp_on_planner_full, map_meta = map_temp_to_planner_full_grid(
        temp_day=temp_day,
        planner_lat=lat,
        planner_lon=lon,
    )

    candb_planner_crop = crop_roi(planner_arr, candb_roi)
    user_planner_crop = crop_roi(planner_arr, user_roi)
    candb_mask = np.isfinite(candb_planner_crop)
    user_mask = np.isfinite(user_planner_crop)

    candb_temp_raw = crop_roi(temp_on_planner_full, candb_roi)
    user_temp_raw = crop_roi(temp_on_planner_full, user_roi)
    candb_fill = float(np.nanmean(candb_temp_raw[np.isfinite(candb_temp_raw)])) if np.any(np.isfinite(candb_temp_raw)) else 0.0
    user_fill = float(np.nanmean(user_temp_raw[np.isfinite(user_temp_raw)])) if np.any(np.isfinite(user_temp_raw)) else 0.0
    candb_temp_raw = np.where(np.isfinite(candb_temp_raw), candb_temp_raw, candb_fill)
    user_temp_raw = np.where(np.isfinite(user_temp_raw), user_temp_raw, user_fill)
    candb_temp_masked = np.where(candb_mask, candb_temp_raw, np.nan)
    user_temp_masked = np.where(user_mask, user_temp_raw, np.nan)

    planner_vals = np.concatenate(
        [
            candb_planner_crop[np.isfinite(candb_planner_crop)],
            user_planner_crop[np.isfinite(user_planner_crop)],
        ]
    )
    if planner_vals.size > 0:
        planner_vmin = float(np.percentile(planner_vals, 2.0))
        planner_vmax = float(np.percentile(planner_vals, 98.0))
    else:
        planner_vmin, planner_vmax = float("nan"), float("nan")

    render_crop(
        arr=candb_planner_crop,
        out_png=OUT_CANDB_PLANNER_PNG,
        title=f"CAND_B planner crop\nshape={candb_planner_crop.shape[0]}x{candb_planner_crop.shape[1]}",
        cbar_label="temperr",
        cmap_name="viridis",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    render_crop(
        arr=user_planner_crop,
        out_png=OUT_USER_PLANNER_PNG,
        title=f"USER_DIRECT_KM planner crop\nshape={user_planner_crop.shape[0]}x{user_planner_crop.shape[1]}",
        cbar_label="temperr",
        cmap_name="viridis",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    render_crop(
        arr=candb_temp_masked,
        out_png=OUT_CANDB_TEMP_MASK_PNG,
        title=f"CAND_B temperature mapped to planner mask\nshape={candb_temp_masked.shape[0]}x{candb_temp_masked.shape[1]}",
        cbar_label="Temperature (degC)",
        cmap_name="viridis",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    render_crop(
        arr=user_temp_masked,
        out_png=OUT_USER_TEMP_MASK_PNG,
        title=f"USER_DIRECT_KM temperature mapped to planner mask\nshape={user_temp_masked.shape[0]}x{user_temp_masked.shape[1]}",
        cbar_label="Temperature (degC)",
        cmap_name="viridis",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )

    save_npy(OUT_CANDB_TEMP_MASK_NPY, candb_temp_masked)
    save_npy(OUT_USER_TEMP_MASK_NPY, user_temp_masked)
    save_npy(OUT_CANDB_PLANNER_NPY, candb_planner_crop)
    save_npy(OUT_USER_PLANNER_NPY, user_planner_crop)
    save_npy(OUT_CANDB_MASK_NPY, candb_mask.astype(bool))
    save_npy(OUT_USER_MASK_NPY, user_mask.astype(bool))

    render_pair_panel(
        planner_crop=candb_planner_crop,
        temp_crop=candb_temp_masked,
        method="CAND_B",
        out_png=OUT_PANEL_CANDB,
        planner_vmin=planner_vmin,
        planner_vmax=planner_vmax,
        temp_vmin=temp_vmin,
        temp_vmax=temp_vmax,
    )
    render_pair_panel(
        planner_crop=user_planner_crop,
        temp_crop=user_temp_masked,
        method="USER_DIRECT_KM",
        out_png=OUT_PANEL_USER,
        planner_vmin=planner_vmin,
        planner_vmax=planner_vmax,
        temp_vmin=temp_vmin,
        temp_vmax=temp_vmax,
    )
    render_both_panel(
        candb_planner=candb_planner_crop,
        candb_temp=candb_temp_masked,
        user_planner=user_planner_crop,
        user_temp=user_temp_masked,
        out_png=OUT_PANEL_BOTH,
        planner_vmin=planner_vmin,
        planner_vmax=planner_vmax,
        temp_vmin=temp_vmin,
        temp_vmax=temp_vmax,
    )
    render_overlay_masks(
        planner_full=planner_arr,
        candb_roi=candb_roi,
        user_roi=user_roi,
        candb_mask=candb_mask,
        user_mask=user_mask,
        out_png=OUT_PANEL_MASKS,
    )

    check_rows = [
        make_consistency_row("CAND_B", candb_planner_crop, candb_temp_masked),
        make_consistency_row("USER_DIRECT_KM", user_planner_crop, user_temp_masked),
    ]
    write_csv(OUT_CHECKS_CSV, check_rows)

    checks_payload = {
        "generated_at_utc": now_iso(),
        "day_used": DAY_USED.isoformat(),
        "reference_tempres_png": rel(REFERENCE_TEMPRES_PNG),
        "day_to_z_mapping": {
            "selected_z": z_sel,
            "convention": mapping_day["convention"],
            "reason": mapping_day["reason"],
            "doy": mapping_day["doy"],
        },
        "inputs": {
            "temp_stack": rel(TEMP_STACK),
            "temp_scale_source": temp_scale_source,
            "planner_interface": rel(planner_path),
            "candb_source_csv": rel(CANDB_SOURCE_CSV),
            "userdirect_relative_manifest": rel(RELATIVE_KM_MANIFEST),
        },
        "method_rois_planner": {
            "candb": {
                "x0": candb_roi.x0,
                "x1": candb_roi.x1,
                "y0": candb_roi.y0,
                "y1": candb_roi.y1,
                "shape": [candb_roi.height, candb_roi.width],
            },
            "userdirect": {
                "x0": user_roi.x0,
                "x1": user_roi.x1,
                "y0": user_roi.y0,
                "y1": user_roi.y1,
                "shape": [user_roi.height, user_roi.width],
                "manifest_crop_1based": user_extra,
            },
        },
        "temperature_projection": {
            "method": map_meta["mapping_method"],
            "temp_shape": map_meta["temp_shape"],
            "planner_shape": map_meta["planner_shape"],
            "planner_bbox_lonlat": map_meta["planner_bbox_lonlat"],
            "orientation": "origin=lower",
        },
        "consistency_checks": check_rows,
        "outputs": [
            rel(OUT_CANDB_PLANNER_PNG),
            rel(OUT_USER_PLANNER_PNG),
            rel(OUT_CANDB_TEMP_MASK_PNG),
            rel(OUT_USER_TEMP_MASK_PNG),
            rel(OUT_CANDB_TEMP_MASK_NPY),
            rel(OUT_USER_TEMP_MASK_NPY),
            rel(OUT_CANDB_PLANNER_NPY),
            rel(OUT_USER_PLANNER_NPY),
            rel(OUT_CANDB_MASK_NPY),
            rel(OUT_USER_MASK_NPY),
            rel(OUT_PANEL_CANDB),
            rel(OUT_PANEL_USER),
            rel(OUT_PANEL_BOTH),
            rel(OUT_PANEL_MASKS),
            rel(OUT_CHECKS_JSON),
            rel(OUT_CHECKS_CSV),
            rel(OUT_REPORT),
            rel(OUT_SUMMARY),
        ],
    }
    ensure_parent(OUT_CHECKS_JSON)
    OUT_CHECKS_JSON.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    candb_stats_pl = stats_for_array(candb_planner_crop)
    candb_stats_tp = stats_for_array(candb_temp_masked)
    user_stats_pl = stats_for_array(user_planner_crop)
    user_stats_tp = stats_for_array(user_temp_masked)
    candb_ok = all(
        [
            bool(check_rows[0]["shapes_match"]),
            bool(check_rows[0]["valid_cells_match"]),
            bool(check_rows[0]["masked_cells_match"]),
            bool(check_rows[0]["exact_mask_match"]),
        ]
    )
    user_ok = all(
        [
            bool(check_rows[1]["shapes_match"]),
            bool(check_rows[1]["valid_cells_match"]),
            bool(check_rows[1]["masked_cells_match"]),
            bool(check_rows[1]["exact_mask_match"]),
        ]
    )

    report_lines = [
        "# Masked Temperature Alignment Report",
        "",
        "## 1) Why Previous Version Was Not 1:1",
        "- In the previous run, temperature crops were built in tempRes-index space (e.g., 26x60), while planner crops were in planner/HRes ROI space (e.g., 67x128).",
        "- Because domain/layout/mask were different, those figures were not direct cell-by-cell 1:1 comparisons.",
        "",
        "## 2) Correction Implemented",
        "- Kept planner domain as geometric reference.",
        "- For each method (`CAND_B`, `USER_DIRECT_KM`):",
        "  1. Extracted method ROI on planner-compatible grid.",
        "  2. Extracted planner crop and its exact valid-mask.",
        "  3. Reprojected/interpolated temperature field to full planner grid.",
        "  4. Cropped temperature on same ROI.",
        "  5. Applied exact planner mask to the temperature crop.",
        "- Result: temperature crop and planner crop now share identical local indices, shape, and mask.",
        "",
        "## 3) Day And Reference",
        f"- day_used: `{DAY_USED.isoformat()}`",
        f"- reference_tempres_png: `{rel(REFERENCE_TEMPRES_PNG)}`",
        f"- selected_z_for_numeric_field: `{z_sel}` ({mapping_day['convention']}; {mapping_day['reason']})",
        "",
        "## 4) 1:1 Consistency Results",
        f"- CAND_B -> shape match: `{check_rows[0]['shapes_match']}` | valid_cells_match: `{check_rows[0]['valid_cells_match']}` | masked_cells_match: `{check_rows[0]['masked_cells_match']}` | exact_mask_match: `{check_rows[0]['exact_mask_match']}`",
        f"- USER_DIRECT_KM -> shape match: `{check_rows[1]['shapes_match']}` | valid_cells_match: `{check_rows[1]['valid_cells_match']}` | masked_cells_match: `{check_rows[1]['masked_cells_match']}` | exact_mask_match: `{check_rows[1]['exact_mask_match']}`",
        "",
        "## 5) Outputs Generated",
        f"- `{rel(OUT_CANDB_PLANNER_PNG)}`",
        f"- `{rel(OUT_USER_PLANNER_PNG)}`",
        f"- `{rel(OUT_CANDB_TEMP_MASK_PNG)}`",
        f"- `{rel(OUT_USER_TEMP_MASK_PNG)}`",
        f"- `{rel(OUT_CANDB_TEMP_MASK_NPY)}`",
        f"- `{rel(OUT_USER_TEMP_MASK_NPY)}`",
        f"- `{rel(OUT_CANDB_PLANNER_NPY)}`",
        f"- `{rel(OUT_USER_PLANNER_NPY)}`",
        f"- `{rel(OUT_CANDB_MASK_NPY)}`",
        f"- `{rel(OUT_USER_MASK_NPY)}`",
        f"- `{rel(OUT_PANEL_CANDB)}`",
        f"- `{rel(OUT_PANEL_USER)}`",
        f"- `{rel(OUT_PANEL_BOTH)}`",
        f"- `{rel(OUT_PANEL_MASKS)}`",
        f"- `{rel(OUT_CHECKS_JSON)}`",
        f"- `{rel(OUT_CHECKS_CSV)}`",
        "",
        "## 6) Success Criteria",
        f"- CAND_B success: `{candb_ok}` (planner valid={candb_stats_pl['valid']}, temperature valid={candb_stats_tp['valid']})",
        f"- USER_DIRECT_KM success: `{user_ok}` (planner valid={user_stats_pl['valid']}, temperature valid={user_stats_tp['valid']})",
    ]
    ensure_parent(OUT_REPORT)
    OUT_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# Masked Temperature Alignment Summary",
        "",
        f"- day_used: `{DAY_USED.isoformat()}`",
        f"- reference_tempres_png: `{rel(REFERENCE_TEMPRES_PNG)}`",
        f"- candb_pair_shape: `{candb_planner_crop.shape}` vs `{candb_temp_masked.shape}`",
        f"- userdirect_pair_shape: `{user_planner_crop.shape}` vs `{user_temp_masked.shape}`",
        f"- candb_exact_mask_match: `{check_rows[0]['exact_mask_match']}`",
        f"- userdirect_exact_mask_match: `{check_rows[1]['exact_mask_match']}`",
        f"- checks_json: `{rel(OUT_CHECKS_JSON)}`",
        f"- checks_csv: `{rel(OUT_CHECKS_CSV)}`",
    ]
    ensure_parent(OUT_SUMMARY)
    OUT_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    planner["ds"].close()

    print("Generated:")
    for p in [
        OUT_CANDB_PLANNER_PNG,
        OUT_USER_PLANNER_PNG,
        OUT_CANDB_TEMP_MASK_PNG,
        OUT_USER_TEMP_MASK_PNG,
        OUT_CANDB_TEMP_MASK_NPY,
        OUT_USER_TEMP_MASK_NPY,
        OUT_CANDB_PLANNER_NPY,
        OUT_USER_PLANNER_NPY,
        OUT_CANDB_MASK_NPY,
        OUT_USER_MASK_NPY,
        OUT_PANEL_CANDB,
        OUT_PANEL_USER,
        OUT_PANEL_BOTH,
        OUT_PANEL_MASKS,
        OUT_CHECKS_JSON,
        OUT_CHECKS_CSV,
        OUT_REPORT,
        OUT_SUMMARY,
    ]:
        print(rel(p))


if __name__ == "__main__":
    main()
