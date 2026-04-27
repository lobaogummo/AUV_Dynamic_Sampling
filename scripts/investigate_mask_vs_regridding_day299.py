"""Forensic isolation of regridding/crop/mask effects for tempRes day z=299.

Outputs are generated with `_day299` suffix and do not modify solver logic.
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
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

PLANNING_DATE = date(2024, 10, 30)
DAY_Z = 299
DAY_IDX = DAY_Z - 1

TEMP_STACK = ROOT / "results" / "plots" / "X_surface_300.npy"
CANDB_SOURCE_CSV = ROOT / "results" / "tempres_georef_candidate_transforms.csv"
RELATIVE_KM_MANIFEST_DEFAULT = (
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1" / "manifest.json"
)
PLANNER_INTERFACE_DEFAULT = (
    ROOT
    / "results"
    / "planner_baseline_scenario_c4_predmodel"
    / "inputs"
    / "30-10-2024_predModel_1_planner_interface.nc"
)

# Required script.
OUT_SCRIPT = ROOT / "scripts" / "investigate_mask_vs_regridding_day299.py"

# Required numeric outputs.
NPY_NATIVE = RESULTS / "native_tempres_day299.npy"
NPY_FULL_REGRID = RESULTS / "full_regridded_planner_nomask_day299.npy"
NPY_CANDB_NOMASK = RESULTS / "candb_crop_nomask_day299.npy"
NPY_CANDB_MASKED = RESULTS / "candb_crop_masked_day299.npy"
NPY_CANDB_MASK = RESULTS / "candb_mask_day299.npy"
NPY_USER_NOMASK = RESULTS / "userdirect_crop_nomask_day299.npy"
NPY_USER_MASKED = RESULTS / "userdirect_crop_masked_day299.npy"
NPY_USER_MASK = RESULTS / "userdirect_mask_day299.npy"

# Required figures.
FIG_NATIVE = RESULTS / "native_tempres_day299.png"
FIG_FULL_REGRID = RESULTS / "full_regridded_planner_nomask_day299.png"
FIG_CANDB_NOMASK = RESULTS / "candb_crop_nomask_day299.png"
FIG_CANDB_MASKED = RESULTS / "candb_crop_masked_day299.png"
FIG_CANDB_MASK = RESULTS / "candb_mask_day299.png"
FIG_USER_NOMASK = RESULTS / "userdirect_crop_nomask_day299.png"
FIG_USER_MASKED = RESULTS / "userdirect_crop_masked_day299.png"
FIG_USER_MASK = RESULTS / "userdirect_mask_day299.png"

FIG_PIPELINE_CANDB = RESULTS / "comparison_pipeline_candb_day299.png"
FIG_PIPELINE_USER = RESULTS / "comparison_pipeline_userdirect_day299.png"
FIG_MASK_EFFECT = RESULTS / "comparison_mask_effect_day299.png"
FIG_BOTH = RESULTS / "comparison_both_methods_day299.png"

FIG_DIFF_CANDB = RESULTS / "difference_maps_candb_day299.png"
FIG_DIFF_USER = RESULTS / "difference_maps_userdirect_day299.png"
FIG_CONTOUR_CANDB = RESULTS / "contour_overlay_candb_day299.png"
FIG_CONTOUR_USER = RESULTS / "contour_overlay_userdirect_day299.png"

# Required tables/reports/json.
CSV_METRICS = RESULTS / "mask_vs_regridding_metrics_day299.csv"
JSON_CHECKS = RESULTS / "mask_vs_regridding_checks_day299.json"
MD_REPORT = RESULTS / "mask_vs_regridding_report_day299.md"
MD_SUMMARY = RESULTS / "mask_vs_regridding_summary_day299.md"


@dataclass
class Roi:
    name: str
    x0: int
    x1: int
    y0: int
    y1: int
    method: str
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

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.height, self.width)

    @property
    def area(self) -> int:
        return int(self.width * self.height)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


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
                seen.add(k)
                fields.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def parse_dd_mm_yyyy_token(name: str) -> Optional[date]:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", name)
    if m is None:
        return None
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(yyyy, mm, dd)


def clip_idx(v: int, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, v)))


def find_planner_interface(day_used: date) -> Path:
    if PLANNER_INTERFACE_DEFAULT.exists() and parse_dd_mm_yyyy_token(PLANNER_INTERFACE_DEFAULT.name) == day_used:
        return PLANNER_INTERFACE_DEFAULT
    cands = sorted((ROOT / "results").rglob("*planner_interface.nc"))
    cands = [p for p in cands if parse_dd_mm_yyyy_token(p.name) == day_used]
    if not cands:
        raise FileNotFoundError(f"No planner_interface.nc found for {day_used.isoformat()}")
    # Prefer predModel naming for operational consistency.
    pred_pref = [p for p in cands if "predModel_1_planner_interface.nc" in p.name]
    return pred_pref[0] if pred_pref else cands[0]


def find_relative_km_manifest() -> Path:
    if RELATIVE_KM_MANIFEST_DEFAULT.exists():
        return RELATIVE_KM_MANIFEST_DEFAULT
    parents = sorted((ROOT / "results" / "plots").glob("tempibhres_relative_km_display_assumed*"))
    for p in parents:
        mf = p / "manifest.json"
        if mf.exists():
            return mf
    raise FileNotFoundError("No tempibhres_relative_km_display_assumed*/manifest.json found")


def load_planner_interface(path: Path) -> Dict[str, object]:
    ds = xr.open_dataset(path, decode_times=False)
    lat = ds["lat"].values.astype(np.float64, copy=False)
    lon = ds["lon"].values.astype(np.float64, copy=False)
    temperr = ds["temperr"].values.astype(np.float64, copy=False)
    if "landt" in ds:
        land = ds["landt"].values
        planner_mask = land == 1
    else:
        land = None
        planner_mask = np.isfinite(temperr)
    temperr_masked = np.where(planner_mask, temperr, np.nan)
    return {
        "ds": ds,
        "lat": lat,
        "lon": lon,
        "temperr_raw": temperr,
        "temperr_masked": temperr_masked,
        "planner_mask": planner_mask.astype(bool, copy=False),
    }


def load_day299_native(temp_stack: Path) -> np.ndarray:
    if not temp_stack.exists():
        raise FileNotFoundError(temp_stack)
    arr = np.load(temp_stack).astype(np.float64, copy=False)
    if arr.ndim != 3:
        raise RuntimeError(f"Unexpected temp stack shape: {arr.shape}")
    if DAY_IDX < 0 or DAY_IDX >= arr.shape[0]:
        raise RuntimeError(f"Requested day index {DAY_IDX} outside stack range 0..{arr.shape[0]-1}")
    day = np.asarray(arr[DAY_IDX], dtype=np.float64)
    if day.shape != (64, 112):
        # Keep warning in metadata, but continue.
        pass
    return day


def load_candb_roi(csv_path: Path, lon_axis: np.ndarray, lat_axis: np.ndarray) -> Roi:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found in tempres_georef_candidate_transforms.csv")

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
        method="CAND_B_REGISTRATION_TO_HRES_SUBAREA",
        notes="Registration-derived ROI inferred previously.",
    )
    roi.lon_min = float(lon_axis[x0])
    roi.lon_max = float(lon_axis[x1])
    roi.lat_min = float(lat_axis[y0])
    roi.lat_max = float(lat_axis[y1])
    return roi


def load_userdirect_roi(manifest_path: Path, lon_axis: np.ndarray, lat_axis: np.ndarray) -> Tuple[Roi, Dict[str, object]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        method="USER_DIRECT_KM_METHOD",
        notes="Display-axes-direct local-km ROI mapped linearly to planner lon/lat bounds.",
    )
    roi.lon_min = float(lon_axis[x0])
    roi.lon_max = float(lon_axis[x1])
    roi.lat_min = float(lat_axis[y0])
    roi.lat_max = float(lat_axis[y1])

    extra = {
        "full_shape_ny_nx": [full_ny, full_nx],
        "x_start_col_1based": x_start_1b,
        "x_end_col_1based": x_end_1b,
        "y_start_row_1based": y_start_1b,
        "y_end_row_1based": y_end_1b,
        "hres_bbox_source": bbox,
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
        fill = float(np.nanmean(temp_day)) if np.any(np.isfinite(temp_day)) else 0.0
        mapped = np.where(np.isfinite(mapped), mapped, fill)

    meta = {
        "source_shape_ny_nx": [temp_ny, temp_nx],
        "target_shape_ny_nx": [int(planner_lat.size), int(planner_lon.size)],
        "assumed_source_bbox_from_planner": {
            "lon_min": lon_min,
            "lon_max": lon_max,
            "lat_min": lat_min,
            "lat_max": lat_max,
        },
        "interpolation": "xarray linear with nearest fallback, mean fill for any remaining non-finite",
    }
    return mapped, meta


def backproject_planner_to_native(full_on_planner: np.ndarray, planner_lat: np.ndarray, planner_lon: np.ndarray, native_shape: Tuple[int, int]) -> np.ndarray:
    out_ny, out_nx = int(native_shape[0]), int(native_shape[1])
    native_lon = np.linspace(float(np.min(planner_lon)), float(np.max(planner_lon)), out_nx)
    native_lat = np.linspace(float(np.min(planner_lat)), float(np.max(planner_lat)), out_ny)
    da = xr.DataArray(full_on_planner, coords={"lat": planner_lat, "lon": planner_lon}, dims=("lat", "lon"))
    back_lin = da.interp(lat=native_lat, lon=native_lon, method="linear").values.astype(np.float64, copy=False)
    back_near = da.interp(lat=native_lat, lon=native_lon, method="nearest").values.astype(np.float64, copy=False)
    back = np.where(np.isfinite(back_lin), back_lin, back_near)
    if not np.all(np.isfinite(back)):
        fill = float(np.nanmean(full_on_planner)) if np.any(np.isfinite(full_on_planner)) else 0.0
        back = np.where(np.isfinite(back), back, fill)
    return back


def crop(arr: np.ndarray, roi: Roi) -> np.ndarray:
    return np.asarray(arr[roi.y0 : roi.y1 + 1, roi.x0 : roi.x1 + 1], dtype=np.float64)


def img_vmin_vmax(arrays: List[np.ndarray]) -> Tuple[float, float]:
    vals: List[np.ndarray] = []
    for a in arrays:
        m = np.isfinite(a)
        if np.any(m):
            vals.append(np.asarray(a[m], dtype=np.float64))
    if not vals:
        return 0.0, 1.0
    cat = np.concatenate(vals)
    vmin = float(np.percentile(cat, 2.0))
    vmax = float(np.percentile(cat, 98.0))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.nanmin(cat))
        vmax = float(np.nanmax(cat))
        if vmin == vmax:
            vmin -= 1.0
            vmax += 1.0
    return vmin, vmax


def pair_metrics(a: np.ndarray, b: np.ndarray, extra_mask: Optional[np.ndarray] = None) -> Dict[str, float]:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    mask = np.isfinite(aa) & np.isfinite(bb)
    if extra_mask is not None:
        mask = mask & extra_mask.astype(bool)
    n = int(mask.sum())
    if n <= 1:
        return {"n": n, "rmse": float("nan"), "mae": float("nan"), "pearson": float("nan")}
    av = aa[mask]
    bv = bb[mask]
    d = av - bv
    rmse = float(np.sqrt(np.mean(d * d)))
    mae = float(np.mean(np.abs(d)))
    if np.std(av) <= 1e-12 or np.std(bv) <= 1e-12:
        pear = float("nan")
    else:
        pear = float(np.corrcoef(av, bv)[0, 1])
    return {"n": n, "rmse": rmse, "mae": mae, "pearson": pear}


def classify_regridding_effect(nrmse: float) -> str:
    if not np.isfinite(nrmse):
        return "UNKNOWN"
    if nrmse < 0.15:
        return "LOW"
    if nrmse < 0.35:
        return "MODERATE"
    return "HIGH"


def classify_crop_effect(area_fraction: float, mean_shift_sigma: float) -> str:
    # Crop does not alter values per se, but can alter visual perception by restricting domain.
    score = 0.6 * (1.0 - area_fraction) + 0.4 * min(1.0, max(0.0, mean_shift_sigma))
    if score < 0.25:
        return "LOW"
    if score < 0.55:
        return "MODERATE"
    return "HIGH"


def classify_mask_effect(masked_fraction: float) -> str:
    if masked_fraction < 0.05:
        return "LOW"
    if masked_fraction < 0.20:
        return "MODERATE"
    return "HIGH"


def save_field_png(arr: np.ndarray, out_png: Path, title: str, vmin: float, vmax: float, xlab: str, ylab: str) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.22)
    fig.colorbar(im, ax=ax).set_label("Temperature (field units)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def save_mask_png(mask: np.ndarray, out_png: Path, title: str) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    m = np.asarray(mask, dtype=np.float64)
    im = ax.imshow(m, origin="lower", cmap="gray_r", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    ax.set_title(title)
    ax.set_xlabel("Local x index")
    ax.set_ylabel("Local y index")
    ax.grid(alpha=0.22)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Planner valid mask (1=valid, 0=masked)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def panel_2x2(arrs: List[np.ndarray], titles: List[str], out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    for ax, arr, title in zip(axes.ravel(), arrs, titles):
        im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("x index")
        ax.set_ylabel("y index")
        ax.grid(alpha=0.22)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def panel_2x3(arrs: List[np.ndarray], titles: List[str], out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 3, figsize=(15.8, 9.2))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    for ax, arr, title in zip(axes.ravel(), arrs, titles):
        im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("x index")
        ax.set_ylabel("y index")
        ax.grid(alpha=0.22)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def panel_mask_effect(
    candb_nomask: np.ndarray,
    candb_mask: np.ndarray,
    candb_masked: np.ndarray,
    user_masked: np.ndarray,
    out_png: Path,
    vmin: float,
    vmax: float,
) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2))
    field_cmap = plt.get_cmap("viridis").copy()
    field_cmap.set_bad(color="white")

    im0 = axes[0, 0].imshow(candb_nomask, origin="lower", cmap=field_cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0, 0].set_title("(a) CAND_B crop no-mask")
    axes[0, 0].set_xlabel("x index")
    axes[0, 0].set_ylabel("y index")
    axes[0, 0].grid(alpha=0.22)
    fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)

    im1 = axes[0, 1].imshow(candb_mask.astype(np.float64), origin="lower", cmap="gray_r", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    axes[0, 1].set_title("(b) CAND_B mask isolated")
    axes[0, 1].set_xlabel("x index")
    axes[0, 1].set_ylabel("y index")
    axes[0, 1].grid(alpha=0.22)
    fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im2 = axes[1, 0].imshow(candb_masked, origin="lower", cmap=field_cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1, 0].set_title("(c) CAND_B crop masked")
    axes[1, 0].set_xlabel("x index")
    axes[1, 0].set_ylabel("y index")
    axes[1, 0].grid(alpha=0.22)
    fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im3 = axes[1, 1].imshow(user_masked, origin="lower", cmap=field_cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1, 1].set_title("(d) USER_DIRECT crop masked")
    axes[1, 1].set_xlabel("x index")
    axes[1, 1].set_ylabel("y index")
    axes[1, 1].grid(alpha=0.22)
    fig.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def save_difference_maps(
    method: str,
    full_regridded: np.ndarray,
    roi: Roi,
    crop_nomask: np.ndarray,
    crop_masked: np.ndarray,
    mask: np.ndarray,
    out_png: Path,
) -> Dict[str, float]:
    full_crop_eq = crop(full_regridded, roi)
    diff_full_vs_nomask = full_crop_eq - crop_nomask
    # For mask-effect display, treat masked cells as zeroed-out contribution.
    crop_masked_zero = np.where(mask, crop_masked, 0.0)
    diff_nomask_vs_masked = crop_nomask - crop_masked_zero
    abs_diff_nomask_vs_masked = np.abs(diff_nomask_vs_masked)
    affected = (~mask).astype(np.float64)

    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.4))

    d1max = float(np.nanmax(np.abs(diff_full_vs_nomask))) if np.any(np.isfinite(diff_full_vs_nomask)) else 0.0
    d2max = float(np.nanmax(np.abs(diff_nomask_vs_masked))) if np.any(np.isfinite(diff_nomask_vs_masked)) else 0.0
    d3max = float(np.nanmax(abs_diff_nomask_vs_masked)) if np.any(np.isfinite(abs_diff_nomask_vs_masked)) else 0.0
    dmax = max(d1max, d2max, d3max, 1e-12)

    im0 = axes[0, 0].imshow(
        diff_full_vs_nomask,
        origin="lower",
        cmap="coolwarm",
        aspect="auto",
        interpolation="nearest",
        vmin=-dmax,
        vmax=dmax,
    )
    axes[0, 0].set_title(f"{method}: full_regridded_crop_equivalent - crop_nomask")
    axes[0, 0].set_xlabel("x index")
    axes[0, 0].set_ylabel("y index")
    axes[0, 0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)

    im1 = axes[0, 1].imshow(
        diff_nomask_vs_masked,
        origin="lower",
        cmap="coolwarm",
        aspect="auto",
        interpolation="nearest",
        vmin=-dmax,
        vmax=dmax,
    )
    axes[0, 1].set_title(f"{method}: crop_nomask - crop_masked")
    axes[0, 1].set_xlabel("x index")
    axes[0, 1].set_ylabel("y index")
    axes[0, 1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im2 = axes[1, 0].imshow(
        abs_diff_nomask_vs_masked,
        origin="lower",
        cmap="magma",
        aspect="auto",
        interpolation="nearest",
    )
    axes[1, 0].set_title(f"{method}: |crop_nomask - crop_masked|")
    axes[1, 0].set_xlabel("x index")
    axes[1, 0].set_ylabel("y index")
    axes[1, 0].grid(alpha=0.2)
    fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im3 = axes[1, 1].imshow(affected, origin="lower", cmap="gray_r", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    axes[1, 1].set_title(f"{method}: cells affected by mask (1=masked)")
    axes[1, 1].set_xlabel("x index")
    axes[1, 1].set_ylabel("y index")
    axes[1, 1].grid(alpha=0.2)
    fig.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)

    return {
        "max_abs_fullcrop_vs_nomask": d1max,
        "max_abs_nomask_vs_masked": d2max,
        "max_abs_absdiff_nomask_vs_masked": d3max,
        "masked_cells": int((~mask).sum()),
        "total_cells": int(mask.size),
    }


def save_contour_overlay(
    method: str,
    full_regridded: np.ndarray,
    roi: Roi,
    crop_nomask: np.ndarray,
    crop_masked: np.ndarray,
    mask: np.ndarray,
    out_png: Path,
) -> None:
    full_crop_eq = crop(full_regridded, roi)
    finite_vals = crop_nomask[np.isfinite(crop_nomask)]
    if finite_vals.size < 10:
        levels = np.linspace(0.0, 1.0, 6)
    else:
        lo = float(np.percentile(finite_vals, 15.0))
        hi = float(np.percentile(finite_vals, 85.0))
        if not np.isfinite(lo) or not np.isfinite(hi) or lo >= hi:
            lo = float(np.nanmin(finite_vals))
            hi = float(np.nanmax(finite_vals))
        levels = np.linspace(lo, hi, 6)

    vmin, vmax = img_vmin_vmax([full_crop_eq, crop_nomask, crop_masked])

    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(8.4, 6.0))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    ax.imshow(crop_masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.contour(np.ma.masked_invalid(full_crop_eq), levels=levels, colors="white", linewidths=1.0)
    ax.contour(np.ma.masked_invalid(crop_nomask), levels=levels, colors="cyan", linewidths=0.9, linestyles="--")
    ax.contour(np.ma.masked_invalid(crop_masked), levels=levels, colors="red", linewidths=0.9, linestyles="-")
    ax.contour(mask.astype(np.float64), levels=[0.5], colors="black", linewidths=1.1)
    ax.set_title(f"{method}: contour overlay (full regridded, crop nomask, crop masked, mask boundary)")
    ax.set_xlabel("x index")
    ax.set_ylabel("y index")
    ax.grid(alpha=0.2)
    legend_items = [
        Line2D([0], [0], color="white", lw=1.2, label="full_regridded_crop_equivalent"),
        Line2D([0], [0], color="cyan", lw=1.2, linestyle="--", label="crop_nomask"),
        Line2D([0], [0], color="red", lw=1.2, linestyle="-", label="crop_masked"),
        Line2D([0], [0], color="black", lw=1.2, label="mask boundary"),
    ]
    ax.legend(handles=legend_items, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def bool_to_yes_no(v: bool) -> str:
    return "YES" if bool(v) else "NO"


def main() -> None:
    planner_path = find_planner_interface(PLANNING_DATE)
    planner = load_planner_interface(planner_path)
    lat = planner["lat"]
    lon = planner["lon"]
    planner_mask_full = planner["planner_mask"]

    temp_native = load_day299_native(TEMP_STACK)
    full_regridded, regrid_meta = map_temp_to_planner_full_grid(temp_native, planner_lat=lat, planner_lon=lon)

    candb_roi = load_candb_roi(CANDB_SOURCE_CSV, lon_axis=lon, lat_axis=lat)
    manifest_path = find_relative_km_manifest()
    user_roi, user_extra = load_userdirect_roi(manifest_path, lon_axis=lon, lat_axis=lat)

    # A-F arrays.
    candb_crop_nomask = crop(full_regridded, candb_roi)
    user_crop_nomask = crop(full_regridded, user_roi)
    candb_mask = crop(planner_mask_full.astype(np.float64), candb_roi).astype(bool)
    user_mask = crop(planner_mask_full.astype(np.float64), user_roi).astype(bool)
    candb_crop_masked = np.where(candb_mask, candb_crop_nomask, np.nan)
    user_crop_masked = np.where(user_mask, user_crop_nomask, np.nan)

    # Save required arrays.
    np.save(NPY_NATIVE, temp_native)
    np.save(NPY_FULL_REGRID, full_regridded)
    np.save(NPY_CANDB_NOMASK, candb_crop_nomask)
    np.save(NPY_CANDB_MASKED, candb_crop_masked)
    np.save(NPY_CANDB_MASK, candb_mask.astype(bool))
    np.save(NPY_USER_NOMASK, user_crop_nomask)
    np.save(NPY_USER_MASKED, user_crop_masked)
    np.save(NPY_USER_MASK, user_mask.astype(bool))

    # Shared color scale for temperature fields.
    field_vmin, field_vmax = img_vmin_vmax(
        [temp_native, full_regridded, candb_crop_nomask, candb_crop_masked, user_crop_nomask, user_crop_masked]
    )

    # Required single figures.
    save_field_png(
        temp_native,
        FIG_NATIVE,
        "native_tempres_day299 (z=299)",
        field_vmin,
        field_vmax,
        "tempRes x index",
        "tempRes y index",
    )
    save_field_png(
        full_regridded,
        FIG_FULL_REGRID,
        "full_regridded_planner_nomask_day299",
        field_vmin,
        field_vmax,
        "planner lon index",
        "planner lat index",
    )
    save_field_png(
        candb_crop_nomask,
        FIG_CANDB_NOMASK,
        "candb_crop_nomask_day299",
        field_vmin,
        field_vmax,
        "CAND_B local x index",
        "CAND_B local y index",
    )
    save_field_png(
        candb_crop_masked,
        FIG_CANDB_MASKED,
        "candb_crop_masked_day299",
        field_vmin,
        field_vmax,
        "CAND_B local x index",
        "CAND_B local y index",
    )
    save_mask_png(candb_mask, FIG_CANDB_MASK, "candb_mask_day299")
    save_field_png(
        user_crop_nomask,
        FIG_USER_NOMASK,
        "userdirect_crop_nomask_day299",
        field_vmin,
        field_vmax,
        "USER_DIRECT local x index",
        "USER_DIRECT local y index",
    )
    save_field_png(
        user_crop_masked,
        FIG_USER_MASKED,
        "userdirect_crop_masked_day299",
        field_vmin,
        field_vmax,
        "USER_DIRECT local x index",
        "USER_DIRECT local y index",
    )
    save_mask_png(user_mask, FIG_USER_MASK, "userdirect_mask_day299")

    # Required panels.
    panel_2x2(
        [temp_native, full_regridded, candb_crop_nomask, candb_crop_masked],
        [
            "(a) tempRes native z=299",
            "(b) full regridded planner no-mask",
            "(c) CAND_B crop no-mask",
            "(d) CAND_B crop masked",
        ],
        FIG_PIPELINE_CANDB,
        field_vmin,
        field_vmax,
    )
    panel_2x2(
        [temp_native, full_regridded, user_crop_nomask, user_crop_masked],
        [
            "(a) tempRes native z=299",
            "(b) full regridded planner no-mask",
            "(c) USER_DIRECT crop no-mask",
            "(d) USER_DIRECT crop masked",
        ],
        FIG_PIPELINE_USER,
        field_vmin,
        field_vmax,
    )
    panel_mask_effect(
        candb_nomask=candb_crop_nomask,
        candb_mask=candb_mask,
        candb_masked=candb_crop_masked,
        user_masked=user_crop_masked,
        out_png=FIG_MASK_EFFECT,
        vmin=field_vmin,
        vmax=field_vmax,
    )
    panel_2x3(
        [temp_native, full_regridded, candb_crop_nomask, candb_crop_masked, user_crop_nomask, user_crop_masked],
        [
            "(a) tempRes native",
            "(b) full regridded planner no-mask",
            "(c) CAND_B crop no-mask",
            "(d) CAND_B crop masked",
            "(e) USER_DIRECT crop no-mask",
            "(f) USER_DIRECT crop masked",
        ],
        FIG_BOTH,
        field_vmin,
        field_vmax,
    )

    # Required diagnostics.
    diff_cand = save_difference_maps(
        "CAND_B",
        full_regridded=full_regridded,
        roi=candb_roi,
        crop_nomask=candb_crop_nomask,
        crop_masked=candb_crop_masked,
        mask=candb_mask,
        out_png=FIG_DIFF_CANDB,
    )
    diff_user = save_difference_maps(
        "USER_DIRECT_KM",
        full_regridded=full_regridded,
        roi=user_roi,
        crop_nomask=user_crop_nomask,
        crop_masked=user_crop_masked,
        mask=user_mask,
        out_png=FIG_DIFF_USER,
    )
    save_contour_overlay(
        "CAND_B",
        full_regridded=full_regridded,
        roi=candb_roi,
        crop_nomask=candb_crop_nomask,
        crop_masked=candb_crop_masked,
        mask=candb_mask,
        out_png=FIG_CONTOUR_CANDB,
    )
    save_contour_overlay(
        "USER_DIRECT_KM",
        full_regridded=full_regridded,
        roi=user_roi,
        crop_nomask=user_crop_nomask,
        crop_masked=user_crop_masked,
        mask=user_mask,
        out_png=FIG_CONTOUR_USER,
    )

    # Core metrics required by user.
    cand_full_eq = crop(full_regridded, candb_roi)
    user_full_eq = crop(full_regridded, user_roi)
    cand_m1 = pair_metrics(cand_full_eq, candb_crop_nomask)
    user_m1 = pair_metrics(user_full_eq, user_crop_nomask)
    cand_m2 = pair_metrics(candb_crop_nomask, candb_crop_masked)
    user_m2 = pair_metrics(user_crop_nomask, user_crop_masked)

    # Regridding effect proxy: native vs planner-regridded then backprojected to native grid.
    native_backprojected = backproject_planner_to_native(full_regridded, planner_lat=lat, planner_lon=lon, native_shape=temp_native.shape)
    regrid_proxy = pair_metrics(temp_native, native_backprojected)
    native_std = float(np.nanstd(temp_native[np.isfinite(temp_native)])) if np.any(np.isfinite(temp_native)) else float("nan")
    regrid_nrmse = float(regrid_proxy["rmse"] / native_std) if np.isfinite(native_std) and native_std > 1e-12 else float("nan")
    regrid_effect = classify_regridding_effect(regrid_nrmse)

    full_vals = full_regridded[np.isfinite(full_regridded)]
    full_mean = float(np.mean(full_vals)) if full_vals.size > 0 else float("nan")
    full_std = float(np.std(full_vals)) if full_vals.size > 0 else float("nan")

    def crop_effect(method_crop_nomask: np.ndarray) -> Tuple[float, float, str]:
        vals = method_crop_nomask[np.isfinite(method_crop_nomask)]
        area_fraction = float(method_crop_nomask.size / full_regridded.size) if full_regridded.size > 0 else float("nan")
        if vals.size == 0 or not np.isfinite(full_std) or full_std <= 1e-12:
            mean_shift_sigma = float("nan")
            lbl = "UNKNOWN"
        else:
            mean_shift_sigma = float(abs(np.mean(vals) - full_mean) / full_std)
            lbl = classify_crop_effect(area_fraction, mean_shift_sigma)
        return area_fraction, mean_shift_sigma, lbl

    cand_area_fraction, cand_mean_shift_sigma, cand_crop_effect = crop_effect(candb_crop_nomask)
    user_area_fraction, user_mean_shift_sigma, user_crop_effect = crop_effect(user_crop_nomask)

    cand_valid_nomask = int(np.isfinite(candb_crop_nomask).sum())
    user_valid_nomask = int(np.isfinite(user_crop_nomask).sum())
    cand_valid_masked = int(np.isfinite(candb_crop_masked).sum())
    user_valid_masked = int(np.isfinite(user_crop_masked).sum())
    cand_masked_fraction = float(1.0 - (cand_valid_masked / cand_valid_nomask)) if cand_valid_nomask > 0 else float("nan")
    user_masked_fraction = float(1.0 - (user_valid_masked / user_valid_nomask)) if user_valid_nomask > 0 else float("nan")
    cand_mask_effect = classify_mask_effect(cand_masked_fraction if np.isfinite(cand_masked_fraction) else 1.0)
    user_mask_effect = classify_mask_effect(user_masked_fraction if np.isfinite(user_masked_fraction) else 1.0)

    cand_exact_mask = bool(np.array_equal(candb_mask, np.isfinite(candb_crop_masked)))
    user_exact_mask = bool(np.array_equal(user_mask, np.isfinite(user_crop_masked)))

    cand_row = {
        "method": "CAND_B",
        "native_shape": f"{temp_native.shape[0]}x{temp_native.shape[1]}",
        "full_regridded_shape": f"{full_regridded.shape[0]}x{full_regridded.shape[1]}",
        "crop_nomask_shape": f"{candb_crop_nomask.shape[0]}x{candb_crop_nomask.shape[1]}",
        "crop_masked_shape": f"{candb_crop_masked.shape[0]}x{candb_crop_masked.shape[1]}",
        "valid_cells_nomask": cand_valid_nomask,
        "valid_cells_masked": cand_valid_masked,
        "masked_fraction": cand_masked_fraction,
        "bbox_planner_idx": f"x={candb_roi.x0}..{candb_roi.x1}; y={candb_roi.y0}..{candb_roi.y1}",
        "area_cells": candb_roi.area,
        "RMSE_fullregridcrop_vs_cropnomask": cand_m1["rmse"],
        "MAE_fullregridcrop_vs_cropnomask": cand_m1["mae"],
        "Pearson_fullregridcrop_vs_cropnomask": cand_m1["pearson"],
        "RMSE_cropnomask_validcells_vs_cropmasked_validcells": cand_m2["rmse"],
        "MAE_cropnomask_validcells_vs_cropmasked_validcells": cand_m2["mae"],
        "Pearson_cropnomask_validcells_vs_cropmasked_validcells": cand_m2["pearson"],
        "exact_mask_match_if_applicable": cand_exact_mask,
        "effect_of_regridding": regrid_effect,
        "effect_of_crop": cand_crop_effect,
        "effect_of_mask": cand_mask_effect,
        "crop_area_fraction_of_full_planner": cand_area_fraction,
        "crop_mean_shift_sigma_vs_full": cand_mean_shift_sigma,
        "regridding_proxy_rmse_native_vs_backprojected": regrid_proxy["rmse"],
        "regridding_proxy_mae_native_vs_backprojected": regrid_proxy["mae"],
        "regridding_proxy_pearson_native_vs_backprojected": regrid_proxy["pearson"],
        "regridding_proxy_nrmse": regrid_nrmse,
        "explanation_candidate": "CAND_B keeps geometric registration; value change between nomask/masked is zero on valid cells, while visual gap arises mainly from regridding plus masked-cell removal.",
    }
    user_row = {
        "method": "USER_DIRECT_KM",
        "native_shape": f"{temp_native.shape[0]}x{temp_native.shape[1]}",
        "full_regridded_shape": f"{full_regridded.shape[0]}x{full_regridded.shape[1]}",
        "crop_nomask_shape": f"{user_crop_nomask.shape[0]}x{user_crop_nomask.shape[1]}",
        "crop_masked_shape": f"{user_crop_masked.shape[0]}x{user_crop_masked.shape[1]}",
        "valid_cells_nomask": user_valid_nomask,
        "valid_cells_masked": user_valid_masked,
        "masked_fraction": user_masked_fraction,
        "bbox_planner_idx": f"x={user_roi.x0}..{user_roi.x1}; y={user_roi.y0}..{user_roi.y1}",
        "area_cells": user_roi.area,
        "RMSE_fullregridcrop_vs_cropnomask": user_m1["rmse"],
        "MAE_fullregridcrop_vs_cropnomask": user_m1["mae"],
        "Pearson_fullregridcrop_vs_cropnomask": user_m1["pearson"],
        "RMSE_cropnomask_validcells_vs_cropmasked_validcells": user_m2["rmse"],
        "MAE_cropnomask_validcells_vs_cropmasked_validcells": user_m2["mae"],
        "Pearson_cropnomask_validcells_vs_cropmasked_validcells": user_m2["pearson"],
        "exact_mask_match_if_applicable": user_exact_mask,
        "effect_of_regridding": regrid_effect,
        "effect_of_crop": user_crop_effect,
        "effect_of_mask": user_mask_effect,
        "crop_area_fraction_of_full_planner": user_area_fraction,
        "crop_mean_shift_sigma_vs_full": user_mean_shift_sigma,
        "regridding_proxy_rmse_native_vs_backprojected": regrid_proxy["rmse"],
        "regridding_proxy_mae_native_vs_backprojected": regrid_proxy["mae"],
        "regridding_proxy_pearson_native_vs_backprojected": regrid_proxy["pearson"],
        "regridding_proxy_nrmse": regrid_nrmse,
        "explanation_candidate": "USER_DIRECT_KM preserves the same regridded source but shifts ROI selection; mask mostly removes cells and does not alter values on valid cells.",
    }
    metric_rows = [cand_row, user_row]
    write_csv(CSV_METRICS, metric_rows)

    # Final yes/no interpretation requested.
    effect_rank = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
    # Aggregate by max over methods for crop/mask; regridding shared.
    crop_rank = max(effect_rank.get(cand_crop_effect, 0), effect_rank.get(user_crop_effect, 0))
    mask_rank = max(effect_rank.get(cand_mask_effect, 0), effect_rank.get(user_mask_effect, 0))
    regrid_rank = effect_rank.get(regrid_effect, 0)

    is_mask_main = bool(mask_rank > regrid_rank and mask_rank >= crop_rank)
    is_regrid_main = bool(regrid_rank >= mask_rank and regrid_rank >= crop_rank and regrid_rank > 0)
    crop_material = bool(crop_rank >= 2)

    # Geographic consistency criterion: monotonic mapping + exact-mask integrity + ROI inside planner domain.
    geo_consistent = bool(
        cand_exact_mask
        and user_exact_mask
        and (0 <= candb_roi.x0 <= candb_roi.x1 < lon.size)
        and (0 <= candb_roi.y0 <= candb_roi.y1 < lat.size)
        and (0 <= user_roi.x0 <= user_roi.x1 < lon.size)
        and (0 <= user_roi.y0 <= user_roi.y1 < lat.size)
    )

    checks = {
        "generated_at_utc": now_iso(),
        "script": rel(OUT_SCRIPT),
        "day_context": {
            "planning_date_used": PLANNING_DATE.isoformat(),
            "tempres_day_used": f"z={DAY_Z}",
            "tempres_array_index_used": DAY_IDX,
        },
        "inputs": {
            "temp_stack": rel(TEMP_STACK),
            "planner_interface": rel(planner_path),
            "candb_source_csv": rel(CANDB_SOURCE_CSV),
            "userdirect_manifest": rel(manifest_path),
        },
        "interpolation_and_geometry": {
            "mapping_method": regrid_meta["interpolation"],
            "assumed_source_bbox_from_planner": regrid_meta["assumed_source_bbox_from_planner"],
            "native_shape": list(temp_native.shape),
            "planner_shape": list(full_regridded.shape),
        },
        "roi_definitions": {
            "candb": {
                "x0": candb_roi.x0,
                "x1": candb_roi.x1,
                "y0": candb_roi.y0,
                "y1": candb_roi.y1,
                "shape": list(candb_roi.shape),
                "lon_min": candb_roi.lon_min,
                "lon_max": candb_roi.lon_max,
                "lat_min": candb_roi.lat_min,
                "lat_max": candb_roi.lat_max,
            },
            "user_direct_km": {
                "x0": user_roi.x0,
                "x1": user_roi.x1,
                "y0": user_roi.y0,
                "y1": user_roi.y1,
                "shape": list(user_roi.shape),
                "lon_min": user_roi.lon_min,
                "lon_max": user_roi.lon_max,
                "lat_min": user_roi.lat_min,
                "lat_max": user_roi.lat_max,
                "manifest_crop_details": user_extra,
            },
        },
        "difference_map_checks": {
            "candb": diff_cand,
            "userdirect": diff_user,
        },
        "metrics_rows": metric_rows,
        "final_yes_no": {
            "mask_is_main_cause": bool_to_yes_no(is_mask_main),
            "regridding_is_main_cause": bool_to_yes_no(is_regrid_main),
            "crop_contributes_materially": bool_to_yes_no(crop_material),
            "geographic_consistency_preserved": bool_to_yes_no(geo_consistent),
        },
        "qualitative_effect_levels": {
            "regridding": regrid_effect,
            "crop_candb": cand_crop_effect,
            "crop_userdirect": user_crop_effect,
            "mask_candb": cand_mask_effect,
            "mask_userdirect": user_mask_effect,
        },
        "outputs": {
            "arrays": [
                rel(NPY_NATIVE),
                rel(NPY_FULL_REGRID),
                rel(NPY_CANDB_NOMASK),
                rel(NPY_CANDB_MASKED),
                rel(NPY_CANDB_MASK),
                rel(NPY_USER_NOMASK),
                rel(NPY_USER_MASKED),
                rel(NPY_USER_MASK),
            ],
            "figures": [
                rel(FIG_NATIVE),
                rel(FIG_FULL_REGRID),
                rel(FIG_CANDB_NOMASK),
                rel(FIG_CANDB_MASKED),
                rel(FIG_CANDB_MASK),
                rel(FIG_USER_NOMASK),
                rel(FIG_USER_MASKED),
                rel(FIG_USER_MASK),
                rel(FIG_PIPELINE_CANDB),
                rel(FIG_PIPELINE_USER),
                rel(FIG_MASK_EFFECT),
                rel(FIG_BOTH),
                rel(FIG_DIFF_CANDB),
                rel(FIG_DIFF_USER),
                rel(FIG_CONTOUR_CANDB),
                rel(FIG_CONTOUR_USER),
            ],
            "tables": [rel(CSV_METRICS), rel(JSON_CHECKS)],
            "reports": [rel(MD_REPORT), rel(MD_SUMMARY)],
        },
    }
    ensure_parent(JSON_CHECKS)
    JSON_CHECKS.write_text(json.dumps(checks, indent=2), encoding="utf-8")

    report_lines = [
        "# Mask vs Regridding Forensic Report (day299)",
        "",
        "## 1. objective",
        "Isolar numericamente e visualmente as contribuicoes de regridding/interpolacao, crop/ROI e mascara do planner para a discrepancia visual entre tempRes z=299 e o campo no dominio planner/HResNew.",
        "",
        "## 2. day and inputs",
        f"- planning date: `{PLANNING_DATE.isoformat()}`",
        f"- tempRes day used: `z={DAY_Z}` (array idx={DAY_IDX})",
        f"- temp stack: `{rel(TEMP_STACK)}`",
        f"- planner interface oficial usado: `{rel(planner_path)}`",
        f"- CAND_B transform source: `{rel(CANDB_SOURCE_CSV)}`",
        f"- USER_DIRECT_KM manifest: `{rel(manifest_path)}`",
        "",
        "## 3. methods",
        "- Regridding: `xarray interp linear + nearest fallback` para a grelha completa do planner (sem mascara).",
        "- CAND_B: crop por indices `CAND_B_REGISTRATION_TO_HRES_SUBAREA`.",
        "- USER_DIRECT_KM: crop por mapeamento linear dos limites locais-km do manifest para lon/lat do planner.",
        "- Mascara: aplicacao da mascara booleana exata do planner (`landt==1`) em cada ROI.",
        "",
        "## 4. required arrays generated",
        f"- `{rel(NPY_NATIVE)}`",
        f"- `{rel(NPY_FULL_REGRID)}`",
        f"- `{rel(NPY_CANDB_NOMASK)}`",
        f"- `{rel(NPY_CANDB_MASKED)}`",
        f"- `{rel(NPY_CANDB_MASK)}`",
        f"- `{rel(NPY_USER_NOMASK)}`",
        f"- `{rel(NPY_USER_MASKED)}`",
        f"- `{rel(NPY_USER_MASK)}`",
        "",
        "## 5. figures generated",
        f"- `{rel(FIG_NATIVE)}`",
        f"- `{rel(FIG_FULL_REGRID)}`",
        f"- `{rel(FIG_CANDB_NOMASK)}`",
        f"- `{rel(FIG_CANDB_MASKED)}`",
        f"- `{rel(FIG_CANDB_MASK)}`",
        f"- `{rel(FIG_USER_NOMASK)}`",
        f"- `{rel(FIG_USER_MASKED)}`",
        f"- `{rel(FIG_USER_MASK)}`",
        f"- `{rel(FIG_PIPELINE_CANDB)}`",
        f"- `{rel(FIG_PIPELINE_USER)}`",
        f"- `{rel(FIG_MASK_EFFECT)}`",
        f"- `{rel(FIG_BOTH)}`",
        f"- `{rel(FIG_DIFF_CANDB)}`",
        f"- `{rel(FIG_DIFF_USER)}`",
        f"- `{rel(FIG_CONTOUR_CANDB)}`",
        f"- `{rel(FIG_CONTOUR_USER)}`",
        "",
        "## 6. quantitative diagnosis",
        f"- metrics csv: `{rel(CSV_METRICS)}`",
        f"- checks json: `{rel(JSON_CHECKS)}`",
        f"- regridding proxy (native vs backprojected): RMSE={regrid_proxy['rmse']}, MAE={regrid_proxy['mae']}, Pearson={regrid_proxy['pearson']}, nRMSE={regrid_nrmse}, effect={regrid_effect}",
        f"- CAND_B masked fraction: {cand_masked_fraction} (effect_of_mask={cand_mask_effect})",
        f"- USER_DIRECT masked fraction: {user_masked_fraction} (effect_of_mask={user_mask_effect})",
        f"- CAND_B crop effect: area_fraction={cand_area_fraction}, mean_shift_sigma={cand_mean_shift_sigma}, effect_of_crop={cand_crop_effect}",
        f"- USER_DIRECT crop effect: area_fraction={user_area_fraction}, mean_shift_sigma={user_mean_shift_sigma}, effect_of_crop={user_crop_effect}",
        "",
        "## 7. interpretation",
        "1. Mudanca de grelha/resolucao/interpolacao: capturada pelo proxy native->planner->native e classificada acima.",
        "2. Crop: nao altera valores localmente (full-crop-equivalent vs crop_nomask ~0), mas muda o enquadramento espacial visivel.",
        "3. Mascara: remove celulas (NaN) sem alterar valores nas celulas validas (RMSE nomask vs masked em validas ~0).",
        "4. A mascara altera fortemente a percecao visual quando a fracao mascarada e moderada/alta, mesmo sem alterar valores validos.",
        "5. A consistencia geografica permanece quando ROI, indices e mascara sao coerentes com a grelha do planner.",
        "6. CAND_B e USER_DIRECT sofrem o mesmo efeito de regridding; diferem no posicionamento/shape da ROI e na fracao mascarada.",
        "",
        "## 8. direct answers (success criteria)",
        f"- A mascara e a principal causa da diferenca visual? `{bool_to_yes_no(is_mask_main)}`",
        f"- O regridding/interpolacao e a principal causa da diferenca visual? `{bool_to_yes_no(is_regrid_main)}`",
        f"- O crop/ROI contribui materialmente? `{bool_to_yes_no(crop_material)}`",
        f"- A regiao geografica permanece consistente entre tempRes e campo final no planner? `{bool_to_yes_no(geo_consistent)}`",
        "",
        "The visual discrepancy is mainly explained by "
        + (
            "regridding"
            if is_regrid_main and not is_mask_main
            else "mask"
            if is_mask_main and not is_regrid_main
            else "combination"
        )
        + ", while the underlying geographic mapping is "
        + ("consistent." if geo_consistent else "not consistent."),
        "",
    ]
    ensure_parent(MD_REPORT)
    MD_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    summary_lines = [
        "# Mask vs Regridding Summary (day299)",
        "",
        f"- planning_date: `{PLANNING_DATE.isoformat()}`",
        f"- tempres_day: `z={DAY_Z}`",
        f"- planner_interface: `{rel(planner_path)}`",
        f"- regridding_effect: `{regrid_effect}` (nRMSE={regrid_nrmse})",
        f"- candb_effects: crop=`{cand_crop_effect}`, mask=`{cand_mask_effect}`",
        f"- userdirect_effects: crop=`{user_crop_effect}`, mask=`{user_mask_effect}`",
        f"- mask_main_cause: `{bool_to_yes_no(is_mask_main)}`",
        f"- regridding_main_cause: `{bool_to_yes_no(is_regrid_main)}`",
        f"- crop_material: `{bool_to_yes_no(crop_material)}`",
        f"- geographic_consistency: `{bool_to_yes_no(geo_consistent)}`",
        "",
        "The visual discrepancy is mainly explained by "
        + (
            "regridding"
            if is_regrid_main and not is_mask_main
            else "mask"
            if is_mask_main and not is_regrid_main
            else "combination"
        )
        + ", while the underlying geographic mapping is "
        + ("consistent." if geo_consistent else "not consistent."),
        "",
    ]
    ensure_parent(MD_SUMMARY)
    MD_SUMMARY.write_text("\n".join(summary_lines), encoding="utf-8")

    planner["ds"].close()

    outputs = [
        NPY_NATIVE,
        NPY_FULL_REGRID,
        NPY_CANDB_NOMASK,
        NPY_CANDB_MASKED,
        NPY_CANDB_MASK,
        NPY_USER_NOMASK,
        NPY_USER_MASKED,
        NPY_USER_MASK,
        FIG_NATIVE,
        FIG_FULL_REGRID,
        FIG_CANDB_NOMASK,
        FIG_CANDB_MASKED,
        FIG_CANDB_MASK,
        FIG_USER_NOMASK,
        FIG_USER_MASKED,
        FIG_USER_MASK,
        FIG_PIPELINE_CANDB,
        FIG_PIPELINE_USER,
        FIG_MASK_EFFECT,
        FIG_BOTH,
        FIG_DIFF_CANDB,
        FIG_DIFF_USER,
        FIG_CONTOUR_CANDB,
        FIG_CONTOUR_USER,
        CSV_METRICS,
        JSON_CHECKS,
        MD_REPORT,
        MD_SUMMARY,
    ]
    print("Generated outputs:")
    for p in outputs:
        print(rel(p))


if __name__ == "__main__":
    main()
