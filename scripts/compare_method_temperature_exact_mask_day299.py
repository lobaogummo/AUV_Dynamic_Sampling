"""Exact-mask planner-aligned temperature comparison for CAND_B and USER_DIRECT_KM (day299).

This script is audit/visualization only.
It does not modify planner scientific core logic.
"""

from __future__ import annotations

import csv
import json
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

PLANNING_DATE = date(2024, 10, 30)
TEMPRES_DAY_REQUESTED = 299

TEMP_STACK = ROOT / "results" / "plots" / "X_surface_300.npy"
TEMP_SCALE_JSON = ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json"
TEMPRES_PNG_DIR = ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes"
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


OUT_CANDB_PLANNER_NPY = RESULTS / "candb_planner_crop_day299.npy"
OUT_CANDB_TEMP_NPY = RESULTS / "candb_temperature_on_planner_mask_day299.npy"
OUT_CANDB_MASK_NPY = RESULTS / "candb_mask_day299.npy"

OUT_USER_PLANNER_NPY = RESULTS / "userdirect_planner_crop_day299.npy"
OUT_USER_TEMP_NPY = RESULTS / "userdirect_temperature_on_planner_mask_day299.npy"
OUT_USER_MASK_NPY = RESULTS / "userdirect_mask_day299.npy"

OUT_CANDB_PLANNER_PNG = RESULTS / "candb_planner_crop_day299.png"
OUT_CANDB_TEMP_PNG = RESULTS / "candb_temperature_on_planner_mask_day299.png"
OUT_USER_PLANNER_PNG = RESULTS / "userdirect_planner_crop_day299.png"
OUT_USER_TEMP_PNG = RESULTS / "userdirect_temperature_on_planner_mask_day299.png"

OUT_PANEL_CANDB = RESULTS / "comparison_candb_1to1_day299.png"
OUT_PANEL_USER = RESULTS / "comparison_userdirect_1to1_day299.png"
OUT_PANEL_BOTH = RESULTS / "comparison_both_methods_1to1_day299.png"

OUT_CHECKS_JSON = RESULTS / "masked_crop_consistency_checks_day299.json"
OUT_CHECKS_CSV = RESULTS / "masked_crop_consistency_metrics_day299.csv"
OUT_REPORT = RESULTS / "masked_temperature_alignment_report_day299.md"
OUT_SUMMARY = RESULTS / "masked_temperature_alignment_summary_day299.md"


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


def parse_png_z_values(folder: Path) -> List[int]:
    vals: List[int] = []
    for p in folder.glob("TEMP_surface_2024_z*.png"):
        m = re.search(r"_z(\d{3})\.png$", p.name)
        if m is not None:
            vals.append(int(m.group(1)))
    if not vals:
        raise RuntimeError(f"No z-indexed tempRes PNG files in {folder}")
    return sorted(set(vals))


def audit_day299_mapping(day_requested: int) -> Dict[str, object]:
    if not TEMP_STACK.exists():
        raise FileNotFoundError(TEMP_STACK)
    if not TEMPRES_PNG_DIR.exists():
        raise FileNotFoundError(TEMPRES_PNG_DIR)

    stack = np.load(TEMP_STACK, mmap_mode="r")
    stack_shape = [int(s) for s in stack.shape]
    n_days = int(stack.shape[0])
    stack_range = [0, n_days - 1]

    z_vals = parse_png_z_values(TEMPRES_PNG_DIR)
    z_min, z_max = int(min(z_vals)), int(max(z_vals))

    index_csv = TEMPRES_PNG_DIR / "index.csv"
    idx_rows = 0
    idx_z_min = None
    idx_z_max = None
    if index_csv.exists():
        with index_csv.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        idx_rows = len(rows)
        zcol = [int(r["z"]) for r in rows if r.get("z")]
        if zcol:
            idx_z_min = int(min(zcol))
            idx_z_max = int(max(zcol))

    candidate_if_1based = int(day_requested)
    candidate_if_0based = int(day_requested + 1)

    # Decision rule for this repo:
    # - external day/z labeling is 1..300
    # - in-memory indexing is 0..299
    selected_z = candidate_if_1based
    selected_idx = selected_z - 1

    if selected_z < 1 or selected_z > n_days:
        raise RuntimeError(f"Selected z={selected_z} out of numeric stack range 1..{n_days}")
    if selected_z not in z_vals:
        raise RuntimeError(f"Selected z={selected_z} not present in PNG set z-range {z_min}..{z_max}")

    selected_png = TEMPRES_PNG_DIR / f"TEMP_surface_2024_z{selected_z:03d}.png"
    if not selected_png.exists():
        raise FileNotFoundError(selected_png)

    convention_text = (
        f"tempRes numeric stack uses 0-based indexing [{stack_range[0]}..{stack_range[1]}], "
        f"while exported z files use 1-based labels [{z_min}..{z_max}]."
    )
    decision = (
        f"Requested day {day_requested} interpreted as 1-based day label -> z{selected_z:03d}; "
        f"numeric field index={selected_idx}."
    )
    justification = (
        "PNG and index.csv artifacts use z001..z300 labeling. "
        "Therefore day299 maps to z299 (not z300); array access is idx=z-1."
    )

    return {
        "planning_date_used": PLANNING_DATE.isoformat(),
        "tempres_day_requested": int(day_requested),
        "tempres_indexing_convention_detected": convention_text,
        "stack_shape": stack_shape,
        "stack_index_range": stack_range,
        "png_dir": rel(TEMPRES_PNG_DIR),
        "png_z_range": [z_min, z_max],
        "index_csv": rel(index_csv) if index_csv.exists() else None,
        "index_csv_rows": idx_rows,
        "index_csv_z_range": [idx_z_min, idx_z_max],
        "candidate_if_day_is_1based": candidate_if_1based,
        "candidate_if_day_is_0based": candidate_if_0based,
        "selected_z": selected_z,
        "selected_array_index": selected_idx,
        "tempres_png_reference_selected": rel(selected_png),
        "final_day_mapping_decision": decision,
        "mapping_decision_justification": justification,
    }


def load_temp_scale(temp_field: np.ndarray) -> Tuple[float, float, str]:
    if TEMP_SCALE_JSON.exists():
        payload = json.loads(TEMP_SCALE_JSON.read_text(encoding="utf-8"))
        return float(payload["vmin"]), float(payload["vmax"]), rel(TEMP_SCALE_JSON)
    vmin = float(np.nanpercentile(temp_field, 2.0))
    vmax = float(np.nanpercentile(temp_field, 98.0))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.nanmin(temp_field))
        vmax = float(np.nanmax(temp_field))
    return vmin, vmax, "computed_from_selected_tempres_field"


def find_planner_interface_for_day(day_used: date) -> Path:
    if PLANNER_INTERFACE_DEFAULT.exists() and parse_dd_mm_yyyy_token(PLANNER_INTERFACE_DEFAULT.name) == day_used:
        return PLANNER_INTERFACE_DEFAULT
    cands = sorted((ROOT / "results").rglob("*planner_interface.nc"))
    cands = [p for p in cands if parse_dd_mm_yyyy_token(p.name) == day_used]
    if not cands:
        raise FileNotFoundError(f"No planner_interface.nc found for {day_used.isoformat()}")
    return cands[0]


def load_planner_interface(path: Path) -> Dict[str, object]:
    ds = xr.open_dataset(path, decode_times=False)
    lat = ds["lat"].values.astype(np.float64, copy=False)
    lon = ds["lon"].values.astype(np.float64, copy=False)
    arr = ds["temperr"].values.astype(np.float64, copy=False)
    land = ds["landt"].values if "landt" in ds else None
    if land is not None:
        arr = arr.copy()
        arr[land != 1] = np.nan
    return {"ds": ds, "lat": lat, "lon": lon, "arr": arr}


def load_candb_roi(lon_axis: np.ndarray, lat_axis: np.ndarray) -> Roi:
    with CANDB_SOURCE_CSV.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found")

    x0 = clip_idx(int(row["x0_hres_idx"]), 0, lon_axis.size - 1)
    x1 = clip_idx(int(row["x1_hres_idx"]), 0, lon_axis.size - 1)
    y0 = clip_idx(int(row["y0_hres_idx"]), 0, lat_axis.size - 1)
    y1 = clip_idx(int(row["y1_hres_idx"]), 0, lat_axis.size - 1)
    x1 = max(x1, x0)
    y1 = max(y1, y0)

    roi = Roi(
        name="CAND_B",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        method="CAND_B",
        domain="planner_compatible_hres",
        notes="Registration-derived ROI",
    )
    roi.lon_min = float(lon_axis[x0])
    roi.lon_max = float(lon_axis[x1])
    roi.lat_min = float(lat_axis[y0])
    roi.lat_max = float(lat_axis[y1])
    return roi


def load_userdirect_roi(lon_axis: np.ndarray, lat_axis: np.ndarray) -> Tuple[Roi, Dict[str, object]]:
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

    x0 = clip_idx(int(np.searchsorted(lon_axis, lon_min, side="left")), 0, lon_axis.size - 1)
    x1 = clip_idx(int(np.searchsorted(lon_axis, lon_max, side="right")) - 1, 0, lon_axis.size - 1)
    y0 = clip_idx(int(np.searchsorted(lat_axis, lat_min, side="left")), 0, lat_axis.size - 1)
    y1 = clip_idx(int(np.searchsorted(lat_axis, lat_max, side="right")) - 1, 0, lat_axis.size - 1)
    x1 = max(x1, x0)
    y1 = max(y1, y0)

    roi = Roi(
        name="USER_DIRECT_KM",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        method="USER_DIRECT_KM",
        domain="planner_compatible_hres",
        notes="Relative-km ROI mapped to planner grid",
    )
    roi.lon_min = float(lon_axis[x0])
    roi.lon_max = float(lon_axis[x1])
    roi.lat_min = float(lat_axis[y0])
    roi.lat_max = float(lat_axis[y1])

    extra = {
        "x_start_1based": x_start_1b,
        "x_end_1based": x_end_1b,
        "y_start_1based": y_start_1b,
        "y_end_1based": y_end_1b,
        "manifest": rel(RELATIVE_KM_MANIFEST),
    }
    return roi, extra


def map_temp_to_planner_full_grid(temp_day: np.ndarray, planner_lat: np.ndarray, planner_lon: np.ndarray) -> Tuple[np.ndarray, Dict[str, object]]:
    temp_ny, temp_nx = int(temp_day.shape[0]), int(temp_day.shape[1])
    lon_min, lon_max = float(np.min(planner_lon)), float(np.max(planner_lon))
    lat_min, lat_max = float(np.min(planner_lat)), float(np.max(planner_lat))

    temp_lon = np.linspace(lon_min, lon_max, temp_nx)
    temp_lat = np.linspace(lat_min, lat_max, temp_ny)
    da = xr.DataArray(temp_day, coords={"lat": temp_lat, "lon": temp_lon}, dims=("lat", "lon"))

    mapped_lin = da.interp(lat=planner_lat, lon=planner_lon, method="linear").values.astype(np.float64, copy=False)
    mapped_near = da.interp(lat=planner_lat, lon=planner_lon, method="nearest").values.astype(np.float64, copy=False)
    mapped = np.where(np.isfinite(mapped_lin), mapped_lin, mapped_near)

    if not np.all(np.isfinite(mapped)):
        fill = float(np.nanmean(temp_day)) if np.isfinite(np.nanmean(temp_day)) else 0.0
        mapped = np.where(np.isfinite(mapped), mapped, fill)

    meta = {
        "method": "xarray interp linear with nearest fallback",
        "temp_shape": [temp_ny, temp_nx],
        "planner_shape": [int(planner_lat.size), int(planner_lon.size)],
        "planner_bbox_lonlat": [lon_min, lon_max, lat_min, lat_max],
    }
    return mapped, meta


def crop(arr: np.ndarray, roi: Roi) -> np.ndarray:
    return np.asarray(arr[roi.y0 : roi.y1 + 1, roi.x0 : roi.x1 + 1], dtype=np.float64)


def render_png(arr: np.ndarray, out_png: Path, title: str, cbar_label: str, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("Local x index")
    ax.set_ylabel("Local y index")
    ax.grid(alpha=0.2)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_pair_panel(planner_crop: np.ndarray, temp_crop: np.ndarray, method: str, out_png: Path, pvmin: float, pvmax: float, tvmin: float, tvmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im0 = axes[0].imshow(planner_crop, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=pvmin, vmax=pvmax)
    axes[0].set_title(f"{method} planner crop\nshape={planner_crop.shape[0]}x{planner_crop.shape[1]}")
    axes[0].set_xlabel("Local x index")
    axes[0].set_ylabel("Local y index")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(temp_crop, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=tvmin, vmax=tvmax)
    axes[1].set_title(f"{method} temperature mapped with exact planner mask\nshape={temp_crop.shape[0]}x{temp_crop.shape[1]}")
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
    pvmin: float,
    pvmax: float,
    tvmin: float,
    tvmax: float,
) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.0))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im00 = axes[0, 0].imshow(candb_planner, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=pvmin, vmax=pvmax)
    axes[0, 0].set_title(f"CAND_B planner crop\nshape={candb_planner.shape[0]}x{candb_planner.shape[1]}")
    axes[0, 0].set_xlabel("Local x index")
    axes[0, 0].set_ylabel("Local y index")
    axes[0, 0].grid(alpha=0.2)
    fig.colorbar(im00, ax=axes[0, 0], fraction=0.046, pad=0.04)

    im01 = axes[0, 1].imshow(candb_temp, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=tvmin, vmax=tvmax)
    axes[0, 1].set_title(f"CAND_B temperature same mask\nshape={candb_temp.shape[0]}x{candb_temp.shape[1]}")
    axes[0, 1].set_xlabel("Local x index")
    axes[0, 1].set_ylabel("Local y index")
    axes[0, 1].grid(alpha=0.2)
    fig.colorbar(im01, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im10 = axes[1, 0].imshow(user_planner, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=pvmin, vmax=pvmax)
    axes[1, 0].set_title(f"USER_DIRECT_KM planner crop\nshape={user_planner.shape[0]}x{user_planner.shape[1]}")
    axes[1, 0].set_xlabel("Local x index")
    axes[1, 0].set_ylabel("Local y index")
    axes[1, 0].grid(alpha=0.2)
    fig.colorbar(im10, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im11 = axes[1, 1].imshow(user_temp, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=tvmin, vmax=tvmax)
    axes[1, 1].set_title(f"USER_DIRECT_KM temperature same mask\nshape={user_temp.shape[0]}x{user_temp.shape[1]}")
    axes[1, 1].set_xlabel("Local x index")
    axes[1, 1].set_ylabel("Local y index")
    axes[1, 1].grid(alpha=0.2)
    fig.colorbar(im11, ax=axes[1, 1], fraction=0.046, pad=0.04)

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
        for k in row.keys():
            if k not in seen:
                fields.append(k)
                seen.add(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def make_check_row(method: str, planner_crop: np.ndarray, temp_mapped: np.ndarray) -> Dict[str, object]:
    planner_mask = np.isfinite(planner_crop)
    temp_mask = np.isfinite(temp_mapped)
    planner_valid = int(planner_mask.sum())
    temp_valid = int(temp_mask.sum())
    planner_masked = int(planner_mask.size - planner_valid)
    temp_masked = int(temp_mask.size - temp_valid)
    return {
        "method": method,
        "planner_shape": [int(planner_crop.shape[0]), int(planner_crop.shape[1])],
        "temperature_shape": [int(temp_mapped.shape[0]), int(temp_mapped.shape[1])],
        "shapes_match": bool(tuple(planner_crop.shape) == tuple(temp_mapped.shape)),
        "planner_valid_cells": planner_valid,
        "temperature_valid_cells": temp_valid,
        "valid_cells_match": bool(planner_valid == temp_valid),
        "planner_masked_cells": planner_masked,
        "temperature_masked_cells": temp_masked,
        "masked_cells_match": bool(planner_masked == temp_masked),
        "exact_mask_match": bool(np.array_equal(planner_mask, temp_mask)),
    }


def main() -> None:
    day_audit = audit_day299_mapping(TEMPRES_DAY_REQUESTED)
    selected_idx = int(day_audit["selected_array_index"])
    selected_z = int(day_audit["selected_z"])

    stack = np.load(TEMP_STACK).astype(np.float64, copy=False)
    temp_day = np.asarray(stack[selected_idx], dtype=np.float64)
    temp_vmin, temp_vmax, temp_scale_source = load_temp_scale(temp_day)

    planner_path = find_planner_interface_for_day(PLANNING_DATE)
    planner = load_planner_interface(planner_path)
    planner_arr = planner["arr"]
    lat = planner["lat"]
    lon = planner["lon"]

    candb_roi = load_candb_roi(lon_axis=lon, lat_axis=lat)
    user_roi, user_extra = load_userdirect_roi(lon_axis=lon, lat_axis=lat)

    temp_full_on_planner, map_meta = map_temp_to_planner_full_grid(temp_day=temp_day, planner_lat=lat, planner_lon=lon)

    candb_planner_crop = crop(planner_arr, candb_roi)
    user_planner_crop = crop(planner_arr, user_roi)
    candb_planner_mask = np.isfinite(candb_planner_crop)
    user_planner_mask = np.isfinite(user_planner_crop)

    candb_temp_crop_raw = crop(temp_full_on_planner, candb_roi)
    user_temp_crop_raw = crop(temp_full_on_planner, user_roi)
    candb_temp_mapped = np.where(candb_planner_mask, candb_temp_crop_raw, np.nan)
    user_temp_mapped = np.where(user_planner_mask, user_temp_crop_raw, np.nan)

    # Explicit non-negotiable assertions requested by user.
    assert candb_planner_crop.shape == candb_temp_mapped.shape
    assert np.array_equal(candb_planner_mask, np.isfinite(candb_temp_mapped))
    assert user_planner_crop.shape == user_temp_mapped.shape
    assert np.array_equal(user_planner_mask, np.isfinite(user_temp_mapped))

    np.save(OUT_CANDB_PLANNER_NPY, candb_planner_crop)
    np.save(OUT_CANDB_TEMP_NPY, candb_temp_mapped)
    np.save(OUT_CANDB_MASK_NPY, candb_planner_mask.astype(bool))
    np.save(OUT_USER_PLANNER_NPY, user_planner_crop)
    np.save(OUT_USER_TEMP_NPY, user_temp_mapped)
    np.save(OUT_USER_MASK_NPY, user_planner_mask.astype(bool))

    planner_values = np.concatenate(
        [
            candb_planner_crop[np.isfinite(candb_planner_crop)],
            user_planner_crop[np.isfinite(user_planner_crop)],
        ]
    )
    if planner_values.size > 0:
        planner_vmin = float(np.percentile(planner_values, 2.0))
        planner_vmax = float(np.percentile(planner_values, 98.0))
    else:
        planner_vmin = float("nan")
        planner_vmax = float("nan")

    render_png(
        arr=candb_planner_crop,
        out_png=OUT_CANDB_PLANNER_PNG,
        title=f"CAND_B planner crop day299\nshape={candb_planner_crop.shape[0]}x{candb_planner_crop.shape[1]}",
        cbar_label="temperr",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    render_png(
        arr=candb_temp_mapped,
        out_png=OUT_CANDB_TEMP_PNG,
        title=f"CAND_B temperature on exact planner mask day299\nshape={candb_temp_mapped.shape[0]}x{candb_temp_mapped.shape[1]}",
        cbar_label="Temperature (degC)",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    render_png(
        arr=user_planner_crop,
        out_png=OUT_USER_PLANNER_PNG,
        title=f"USER_DIRECT_KM planner crop day299\nshape={user_planner_crop.shape[0]}x{user_planner_crop.shape[1]}",
        cbar_label="temperr",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    render_png(
        arr=user_temp_mapped,
        out_png=OUT_USER_TEMP_PNG,
        title=f"USER_DIRECT_KM temperature on exact planner mask day299\nshape={user_temp_mapped.shape[0]}x{user_temp_mapped.shape[1]}",
        cbar_label="Temperature (degC)",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )

    render_pair_panel(
        planner_crop=candb_planner_crop,
        temp_crop=candb_temp_mapped,
        method="CAND_B",
        out_png=OUT_PANEL_CANDB,
        pvmin=planner_vmin,
        pvmax=planner_vmax,
        tvmin=temp_vmin,
        tvmax=temp_vmax,
    )
    render_pair_panel(
        planner_crop=user_planner_crop,
        temp_crop=user_temp_mapped,
        method="USER_DIRECT_KM",
        out_png=OUT_PANEL_USER,
        pvmin=planner_vmin,
        pvmax=planner_vmax,
        tvmin=temp_vmin,
        tvmax=temp_vmax,
    )
    render_both_panel(
        candb_planner=candb_planner_crop,
        candb_temp=candb_temp_mapped,
        user_planner=user_planner_crop,
        user_temp=user_temp_mapped,
        out_png=OUT_PANEL_BOTH,
        pvmin=planner_vmin,
        pvmax=planner_vmax,
        tvmin=temp_vmin,
        tvmax=temp_vmax,
    )

    check_rows = [
        make_check_row("CAND_B", candb_planner_crop, candb_temp_mapped),
        make_check_row("USER_DIRECT_KM", user_planner_crop, user_temp_mapped),
    ]
    write_csv(OUT_CHECKS_CSV, check_rows)

    # Hard fail if any requirement is false.
    for r in check_rows:
        assert bool(r["shapes_match"]) is True
        assert bool(r["valid_cells_match"]) is True
        assert bool(r["masked_cells_match"]) is True
        assert bool(r["exact_mask_match"]) is True

    outputs = [
        OUT_CANDB_PLANNER_NPY,
        OUT_CANDB_TEMP_NPY,
        OUT_CANDB_MASK_NPY,
        OUT_USER_PLANNER_NPY,
        OUT_USER_TEMP_NPY,
        OUT_USER_MASK_NPY,
        OUT_CANDB_PLANNER_PNG,
        OUT_CANDB_TEMP_PNG,
        OUT_USER_PLANNER_PNG,
        OUT_USER_TEMP_PNG,
        OUT_PANEL_CANDB,
        OUT_PANEL_USER,
        OUT_PANEL_BOTH,
        OUT_CHECKS_JSON,
        OUT_CHECKS_CSV,
        OUT_REPORT,
        OUT_SUMMARY,
    ]

    checks_payload = {
        "generated_at_utc": now_iso(),
        "planning_date_used": PLANNING_DATE.isoformat(),
        "tempres_day_requested": int(TEMPRES_DAY_REQUESTED),
        "tempres_indexing_convention_detected": day_audit["tempres_indexing_convention_detected"],
        "tempres_source_used": "numeric_field_preferred",
        "tempres_field_or_png_used": f"{rel(TEMP_STACK)}[idx={selected_idx}] => z{selected_z:03d}",
        "tempres_png_reference_selected": day_audit["tempres_png_reference_selected"],
        "final_day_mapping_decision": day_audit["final_day_mapping_decision"],
        "mapping_decision_justification": day_audit["mapping_decision_justification"],
        "day_mapping_audit": day_audit,
        "inputs": {
            "temp_stack": rel(TEMP_STACK),
            "temp_scale_source": temp_scale_source,
            "planner_interface": rel(planner_path),
            "candb_source_csv": rel(CANDB_SOURCE_CSV),
            "userdirect_relative_manifest": rel(RELATIVE_KM_MANIFEST),
        },
        "temperature_projection": map_meta,
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
        "consistency_checks": check_rows,
        "run_status": "SUCCESS",
        "outputs": [rel(p) for p in outputs],
        "outputs_exist": {rel(p): bool(p.exists()) for p in outputs},
    }
    ensure_parent(OUT_CHECKS_JSON)
    OUT_CHECKS_JSON.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    report_lines = [
        "# Masked Temperature Alignment Report (day299)",
        "",
        "## 1) Previous Run Failure",
        "- The previous attempt was considered failed because it resulted in a rectangular temperature crop instead of enforcing exact planner subgrid mask equivalence.",
        "",
        "## 2) Correction Applied",
        "- For each method (`CAND_B`, `USER_DIRECT_KM`):",
        "  1. planner crop extracted",
        "  2. exact planner boolean mask extracted",
        "  3. temperature projected/interpolated to planner full grid",
        "  4. same method ROI cropped from projected temperature",
        "  5. exact planner mask applied",
        "- Explicit assertions were executed in code:",
        "  - `assert planner_crop.shape == temperature_mapped.shape`",
        "  - `assert np.array_equal(planner_mask, temperature_mask)`",
        "",
        "## 3) Day299 Mapping Audit",
        f"- planning_date_used: `{PLANNING_DATE.isoformat()}`",
        f"- tempres_day_requested: `{TEMPRES_DAY_REQUESTED}`",
        f"- tempres_indexing_convention_detected: `{day_audit['tempres_indexing_convention_detected']}`",
        f"- final_day_mapping_decision: `{day_audit['final_day_mapping_decision']}`",
        f"- mapping_decision_justification: {day_audit['mapping_decision_justification']}",
        f"- tempres reference used: `{rel(TEMP_STACK)}[idx={selected_idx}]` with PNG reference `{day_audit['tempres_png_reference_selected']}`",
        "",
        "## 4) Exact Mask/Shape Confirmation",
        f"- CAND_B: shape_match={check_rows[0]['shapes_match']}, exact_mask_match={check_rows[0]['exact_mask_match']}, valid_cells_match={check_rows[0]['valid_cells_match']}, masked_cells_match={check_rows[0]['masked_cells_match']}",
        f"- USER_DIRECT_KM: shape_match={check_rows[1]['shapes_match']}, exact_mask_match={check_rows[1]['exact_mask_match']}, valid_cells_match={check_rows[1]['valid_cells_match']}, masked_cells_match={check_rows[1]['masked_cells_match']}",
        "",
        "## 5) Outputs",
        f"- `{rel(OUT_CANDB_PLANNER_NPY)}`",
        f"- `{rel(OUT_CANDB_TEMP_NPY)}`",
        f"- `{rel(OUT_CANDB_MASK_NPY)}`",
        f"- `{rel(OUT_USER_PLANNER_NPY)}`",
        f"- `{rel(OUT_USER_TEMP_NPY)}`",
        f"- `{rel(OUT_USER_MASK_NPY)}`",
        f"- `{rel(OUT_CANDB_PLANNER_PNG)}`",
        f"- `{rel(OUT_CANDB_TEMP_PNG)}`",
        f"- `{rel(OUT_USER_PLANNER_PNG)}`",
        f"- `{rel(OUT_USER_TEMP_PNG)}`",
        f"- `{rel(OUT_PANEL_CANDB)}`",
        f"- `{rel(OUT_PANEL_USER)}`",
        f"- `{rel(OUT_PANEL_BOTH)}`",
        f"- `{rel(OUT_CHECKS_JSON)}`",
        f"- `{rel(OUT_CHECKS_CSV)}`",
    ]
    ensure_parent(OUT_REPORT)
    OUT_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# Masked Temperature Alignment Summary (day299)",
        "",
        f"- planning_date_used: `{PLANNING_DATE.isoformat()}`",
        f"- tempres_day_requested: `{TEMPRES_DAY_REQUESTED}`",
        f"- tempres_reference_used: `{rel(TEMP_STACK)}[idx={selected_idx}]` with `{day_audit['tempres_png_reference_selected']}`",
        f"- candb_pair_shape: `{candb_planner_crop.shape}` vs `{candb_temp_mapped.shape}`",
        f"- userdirect_pair_shape: `{user_planner_crop.shape}` vs `{user_temp_mapped.shape}`",
        f"- candb_exact_mask_match: `{check_rows[0]['exact_mask_match']}`",
        f"- userdirect_exact_mask_match: `{check_rows[1]['exact_mask_match']}`",
        f"- checks_json: `{rel(OUT_CHECKS_JSON)}`",
        f"- checks_csv: `{rel(OUT_CHECKS_CSV)}`",
        "- run_status: `SUCCESS`",
    ]
    ensure_parent(OUT_SUMMARY)
    OUT_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    checks_payload["outputs_exist"] = {rel(p): bool(p.exists()) for p in outputs}
    OUT_CHECKS_JSON.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    planner["ds"].close()

    print("Generated:")
    for p in outputs:
        print(rel(p))


if __name__ == "__main__":
    main()
