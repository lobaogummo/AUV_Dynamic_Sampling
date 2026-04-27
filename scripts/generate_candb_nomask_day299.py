"""Generate CAND_B day299 crop on planner grid without applying planner mask.

This script is audit/visualization only.
It does not modify solver or planner scientific core.
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
DAY_Z = 299
DAY_IDX = DAY_Z - 1

TEMP_STACK = ROOT / "results" / "plots" / "X_surface_300.npy"
CANDB_SOURCE_CSV = ROOT / "results" / "tempres_georef_candidate_transforms.csv"
PLANNER_INTERFACE_DEFAULT = (
    ROOT
    / "results"
    / "planner_baseline_scenario_c4_predmodel"
    / "inputs"
    / "30-10-2024_predModel_1_planner_interface.nc"
)

# Required script
OUT_SCRIPT = ROOT / "scripts" / "generate_candb_nomask_day299.py"

# Required arrays
NPY_CANDB_NOMASK = RESULTS / "candb_crop_nomask_day299.npy"
NPY_CANDB_MASKED = RESULTS / "candb_crop_masked_day299.npy"
NPY_CANDB_MASK = RESULTS / "candb_mask_day299.npy"
NPY_FULL_REGRID = RESULTS / "full_regridded_planner_nomask_day299.npy"

# Required figures
FIG_CANDB_NOMASK = RESULTS / "candb_crop_nomask_day299.png"
FIG_CANDB_MASKED = RESULTS / "candb_crop_masked_day299.png"
FIG_CANDB_MASK = RESULTS / "candb_mask_day299.png"
FIG_FULL_REGRID = RESULTS / "full_regridded_planner_nomask_day299.png"

# Required panels
FIG_PANEL_NOMASK_VS_MASKED = RESULTS / "comparison_candb_nomask_vs_masked_day299.png"
FIG_PANEL_PIPELINE = RESULTS / "comparison_candb_pipeline_day299.png"
FIG_PANEL_FOCUS = RESULTS / "comparison_candb_nomask_focus_day299.png"

# Required checks/metrics
JSON_CHECKS = RESULTS / "candb_nomask_checks_day299.json"
CSV_METRICS = RESULTS / "candb_nomask_metrics_day299.csv"

# Required reports
MD_REPORT = RESULTS / "candb_nomask_report_day299.md"
MD_SUMMARY = RESULTS / "candb_nomask_summary_day299.md"


@dataclass
class Roi:
    x0: int
    x1: int
    y0: int
    y1: int

    @property
    def width(self) -> int:
        return int(self.x1 - self.x0 + 1)

    @property
    def height(self) -> int:
        return int(self.y1 - self.y0 + 1)

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.height, self.width)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_dd_mm_yyyy_token(name: str) -> Optional[date]:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", name)
    if m is None:
        return None
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(yyyy, mm, dd)


def find_planner_interface(day_used: date) -> Path:
    if PLANNER_INTERFACE_DEFAULT.exists() and parse_dd_mm_yyyy_token(PLANNER_INTERFACE_DEFAULT.name) == day_used:
        return PLANNER_INTERFACE_DEFAULT
    cands = sorted((ROOT / "results").rglob("*planner_interface.nc"))
    cands = [p for p in cands if parse_dd_mm_yyyy_token(p.name) == day_used]
    if not cands:
        raise FileNotFoundError(f"No planner_interface.nc found for {day_used.isoformat()}")
    pred_pref = [p for p in cands if "predModel_1_planner_interface.nc" in p.name]
    return pred_pref[0] if pred_pref else cands[0]


def load_planner(path: Path) -> Dict[str, object]:
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
    return {
        "ds": ds,
        "lat": lat,
        "lon": lon,
        "temperr": temperr,
        "planner_mask": planner_mask.astype(bool, copy=False),
        "land": land,
    }


def load_tempres_day299_numeric(temp_stack: Path) -> np.ndarray:
    if not temp_stack.exists():
        raise FileNotFoundError(temp_stack)
    stack = np.load(temp_stack).astype(np.float64, copy=False)
    if stack.ndim != 3:
        raise RuntimeError(f"Unexpected temp stack shape: {stack.shape}")
    if DAY_IDX < 0 or DAY_IDX >= stack.shape[0]:
        raise RuntimeError(f"Requested day idx {DAY_IDX} outside stack range 0..{stack.shape[0]-1}")
    return np.asarray(stack[DAY_IDX], dtype=np.float64)


def load_candb_row(csv_path: Path) -> Dict[str, str]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found in tempres_georef_candidate_transforms.csv")
    return row


def clip_idx(v: int, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, v)))


def roi_from_candb_row(row: Dict[str, str], lon_axis: np.ndarray, lat_axis: np.ndarray) -> Tuple[Roi, Dict[str, int]]:
    raw_x0 = int(row["x0_hres_idx"])
    raw_x1 = int(row["x1_hres_idx"])
    raw_y0 = int(row["y0_hres_idx"])
    raw_y1 = int(row["y1_hres_idx"])
    x0 = clip_idx(raw_x0, 0, lon_axis.size - 1)
    x1 = clip_idx(raw_x1, 0, lon_axis.size - 1)
    y0 = clip_idx(raw_y0, 0, lat_axis.size - 1)
    y1 = clip_idx(raw_y1, 0, lat_axis.size - 1)
    x1 = max(x1, x0)
    y1 = max(y1, y0)
    return Roi(x0=x0, x1=x1, y0=y0, y1=y1), {"raw_x0": raw_x0, "raw_x1": raw_x1, "raw_y0": raw_y0, "raw_y1": raw_y1}


def map_temp_to_planner_full_grid(temp_day: np.ndarray, planner_lat: np.ndarray, planner_lon: np.ndarray) -> np.ndarray:
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
    return mapped


def crop(arr: np.ndarray, roi: Roi) -> np.ndarray:
    return np.asarray(arr[roi.y0 : roi.y1 + 1, roi.x0 : roi.x1 + 1], dtype=np.float64)


def img_vmin_vmax(arrays: List[np.ndarray]) -> Tuple[float, float]:
    vals: List[np.ndarray] = []
    for a in arrays:
        mask = np.isfinite(a)
        if np.any(mask):
            vals.append(np.asarray(a[mask], dtype=np.float64))
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


def save_field(arr: np.ndarray, out_png: Path, title: str, vmin: float, vmax: float, xlab: str, ylab: str) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(7.0, 4.9))
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


def save_mask(mask: np.ndarray, out_png: Path, title: str) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(7.0, 4.9))
    im = ax.imshow(mask.astype(np.float64), origin="lower", cmap="gray_r", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    ax.set_title(title)
    ax.set_xlabel("Local x index")
    ax.set_ylabel("Local y index")
    ax.grid(alpha=0.22)
    fig.colorbar(im, ax=ax).set_label("Mask (1=valid, 0=masked)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def panel_three(nomask: np.ndarray, mask: np.ndarray, masked: np.ndarray, out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im0 = axes[0].imshow(nomask, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0].set_title("(a) CAND_B crop sem mascara")
    axes[0].set_xlabel("x index")
    axes[0].set_ylabel("y index")
    axes[0].grid(alpha=0.22)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(mask.astype(np.float64), origin="lower", cmap="gray_r", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    axes[1].set_title("(b) Mascara isolada")
    axes[1].set_xlabel("x index")
    axes[1].set_ylabel("y index")
    axes[1].grid(alpha=0.22)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    im2 = axes[2].imshow(masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[2].set_title("(c) CAND_B crop com mascara")
    axes[2].set_xlabel("x index")
    axes[2].set_ylabel("y index")
    axes[2].grid(alpha=0.22)
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def panel_four(native: np.ndarray, full_regrid: np.ndarray, nomask: np.ndarray, masked: np.ndarray, out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.3))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    arrs = [native, full_regrid, nomask, masked]
    titles = [
        "(a) tempRes nativo",
        "(b) tempRes regridado full planner (sem mascara)",
        "(c) CAND_B crop sem mascara",
        "(d) CAND_B crop com mascara",
    ]
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


def panel_two(nomask: np.ndarray, masked: np.ndarray, out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im0 = axes[0].imshow(nomask, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0].set_title("(a) CAND_B crop sem mascara")
    axes[0].set_xlabel("x index")
    axes[0].set_ylabel("y index")
    axes[0].grid(alpha=0.22)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1].set_title("(b) CAND_B crop com mascara")
    axes[1].set_xlabel("x index")
    axes[1].set_ylabel("y index")
    axes[1].grid(alpha=0.22)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

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


def main() -> None:
    planner_path = find_planner_interface(PLANNING_DATE)
    planner = load_planner(planner_path)
    lat = planner["lat"]
    lon = planner["lon"]
    planner_mask_full = planner["planner_mask"]

    temp_day = load_tempres_day299_numeric(TEMP_STACK)
    full_regridded = map_temp_to_planner_full_grid(temp_day, planner_lat=lat, planner_lon=lon)

    candb_row = load_candb_row(CANDB_SOURCE_CSV)
    roi, roi_raw = roi_from_candb_row(candb_row, lon_axis=lon, lat_axis=lat)

    candb_crop_nomask = crop(full_regridded, roi)
    candb_mask = crop(planner_mask_full.astype(np.float64), roi).astype(bool)
    candb_crop_masked = np.where(candb_mask, candb_crop_nomask, np.nan)

    # Save arrays.
    np.save(NPY_CANDB_NOMASK, candb_crop_nomask)
    np.save(NPY_CANDB_MASKED, candb_crop_masked)
    np.save(NPY_CANDB_MASK, candb_mask.astype(bool))
    np.save(NPY_FULL_REGRID, full_regridded)

    # Save figures/panels.
    vmin, vmax = img_vmin_vmax([temp_day, full_regridded, candb_crop_nomask, candb_crop_masked])
    save_field(
        candb_crop_nomask,
        FIG_CANDB_NOMASK,
        "candb_crop_nomask_day299",
        vmin,
        vmax,
        "CAND_B local x index",
        "CAND_B local y index",
    )
    save_field(
        candb_crop_masked,
        FIG_CANDB_MASKED,
        "candb_crop_masked_day299",
        vmin,
        vmax,
        "CAND_B local x index",
        "CAND_B local y index",
    )
    save_mask(candb_mask, FIG_CANDB_MASK, "candb_mask_day299")
    save_field(
        full_regridded,
        FIG_FULL_REGRID,
        "full_regridded_planner_nomask_day299",
        vmin,
        vmax,
        "planner lon index",
        "planner lat index",
    )

    panel_three(candb_crop_nomask, candb_mask, candb_crop_masked, FIG_PANEL_NOMASK_VS_MASKED, vmin, vmax)
    panel_four(temp_day, full_regridded, candb_crop_nomask, candb_crop_masked, FIG_PANEL_PIPELINE, vmin, vmax)
    panel_two(candb_crop_nomask, candb_crop_masked, FIG_PANEL_FOCUS, vmin, vmax)

    # Checks required by user.
    full_crop_equivalent = crop(full_regridded, roi)
    same_roi_used = bool(
        roi.x0 == roi_raw["raw_x0"]
        and roi.x1 == roi_raw["raw_x1"]
        and roi.y0 == roi_raw["raw_y0"]
        and roi.y1 == roi_raw["raw_y1"]
    )
    # same bbox used: ROI lon/lat bounds match CAND_B row lon/lat.
    tol = 1e-10
    row_lon_min = float(candb_row["x0"])
    row_lon_max = float(candb_row["x1"])
    row_lat_min = float(candb_row["y0"])
    row_lat_max = float(candb_row["y1"])
    used_lon_min = float(lon[roi.x0])
    used_lon_max = float(lon[roi.x1])
    used_lat_min = float(lat[roi.y0])
    used_lat_max = float(lat[roi.y1])
    same_bbox_used = bool(
        abs(used_lon_min - row_lon_min) <= tol
        and abs(used_lon_max - row_lon_max) <= tol
        and abs(used_lat_min - row_lat_min) <= tol
        and abs(used_lat_max - row_lat_max) <= tol
    )

    same_shape_nomask_vs_masked = bool(candb_crop_nomask.shape == candb_crop_masked.shape)
    valid_cells_nomask = int(np.isfinite(candb_crop_nomask).sum())
    valid_cells_masked = int(np.isfinite(candb_crop_masked).sum())
    masked_fraction = float(1.0 - (valid_cells_masked / valid_cells_nomask)) if valid_cells_nomask > 0 else float("nan")

    cond_same_nomask_as_fullcrop = bool(np.allclose(candb_crop_nomask, full_crop_equivalent, atol=1e-12, equal_nan=True))
    cond_same_on_valid = bool(np.allclose(candb_crop_nomask[candb_mask], candb_crop_masked[candb_mask], atol=1e-12, equal_nan=True))
    cond_nan_on_masked = bool(np.all(np.isnan(candb_crop_masked[~candb_mask])))
    difference_due_to_mask_only_explained = bool(cond_same_nomask_as_fullcrop and cond_same_on_valid and cond_nan_on_masked)

    notes = (
        "CAND_B nomask and masked were generated from the same regridded planner field and identical ROI; "
        "masked differs only by setting non-valid planner-mask cells to NaN."
    )

    metric_row = {
        "day_used": f"{PLANNING_DATE.isoformat()} / z={DAY_Z}",
        "source_numeric_field_used": f"{rel(TEMP_STACK)}[idx={DAY_IDX}]",
        "full_regridded_shape": f"{full_regridded.shape[0]}x{full_regridded.shape[1]}",
        "candb_crop_nomask_shape": f"{candb_crop_nomask.shape[0]}x{candb_crop_nomask.shape[1]}",
        "candb_crop_masked_shape": f"{candb_crop_masked.shape[0]}x{candb_crop_masked.shape[1]}",
        "same_roi_used": same_roi_used,
        "same_bbox_used": same_bbox_used,
        "same_shape_nomask_vs_masked": same_shape_nomask_vs_masked,
        "masked_fraction": masked_fraction,
        "valid_cells_nomask": valid_cells_nomask,
        "valid_cells_masked": valid_cells_masked,
        "difference_due_to_mask_only_explained": difference_due_to_mask_only_explained,
        "notes": notes,
    }
    write_csv(CSV_METRICS, [metric_row])

    checks_payload = {
        "generated_at_utc": now_iso(),
        "day_used": f"{PLANNING_DATE.isoformat()} / z={DAY_Z}",
        "source_numeric_field_used": f"{rel(TEMP_STACK)}[idx={DAY_IDX}]",
        "planner_interface_used": rel(planner_path),
        "candb_source_csv": rel(CANDB_SOURCE_CSV),
        "candb_source_row": {
            "candidate_id": candb_row["candidate_id"],
            "x0_hres_idx": roi_raw["raw_x0"],
            "x1_hres_idx": roi_raw["raw_x1"],
            "y0_hres_idx": roi_raw["raw_y0"],
            "y1_hres_idx": roi_raw["raw_y1"],
            "x0_lon": row_lon_min,
            "x1_lon": row_lon_max,
            "y0_lat": row_lat_min,
            "y1_lat": row_lat_max,
        },
        "candb_roi_used": {
            "x0_hres_idx": roi.x0,
            "x1_hres_idx": roi.x1,
            "y0_hres_idx": roi.y0,
            "y1_hres_idx": roi.y1,
            "x0_lon": used_lon_min,
            "x1_lon": used_lon_max,
            "y0_lat": used_lat_min,
            "y1_lat": used_lat_max,
        },
        "full_regridded_shape": [int(full_regridded.shape[0]), int(full_regridded.shape[1])],
        "candb_crop_nomask_shape": [int(candb_crop_nomask.shape[0]), int(candb_crop_nomask.shape[1])],
        "candb_crop_masked_shape": [int(candb_crop_masked.shape[0]), int(candb_crop_masked.shape[1])],
        "same_roi_used": same_roi_used,
        "same_bbox_used": same_bbox_used,
        "same_shape_nomask_vs_masked": same_shape_nomask_vs_masked,
        "masked_fraction": masked_fraction,
        "valid_cells_nomask": valid_cells_nomask,
        "valid_cells_masked": valid_cells_masked,
        "difference_due_to_mask_only_explained": difference_due_to_mask_only_explained,
        "notes": notes,
        "validation_details": {
            "nomask_equals_full_regridded_roi_crop": cond_same_nomask_as_fullcrop,
            "nomask_equals_masked_on_valid_cells": cond_same_on_valid,
            "masked_has_nan_on_nonvalid_cells": cond_nan_on_masked,
        },
        "outputs": {
            "arrays": [rel(NPY_CANDB_NOMASK), rel(NPY_CANDB_MASKED), rel(NPY_CANDB_MASK), rel(NPY_FULL_REGRID)],
            "figures": [rel(FIG_CANDB_NOMASK), rel(FIG_CANDB_MASKED), rel(FIG_CANDB_MASK), rel(FIG_FULL_REGRID)],
            "panels": [rel(FIG_PANEL_NOMASK_VS_MASKED), rel(FIG_PANEL_PIPELINE), rel(FIG_PANEL_FOCUS)],
            "checks": [rel(JSON_CHECKS), rel(CSV_METRICS)],
            "reports": [rel(MD_REPORT), rel(MD_SUMMARY)],
        },
    }
    ensure_parent(JSON_CHECKS)
    JSON_CHECKS.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    report_lines = [
        "# CAND_B No-Mask Report (day299)",
        "",
        "## 1. objetivo desta run",
        "Gerar o equivalente ao CAND_B no dominio do planner com o mesmo ROI/bbox e mesmo subgrid, mas sem remover celulas pela mascara do planner.",
        "",
        "## 2. isolamento do efeito ROI/crop sem mascara",
        "Nesta run, o objetivo e isolar o efeito do enquadramento ROI/crop sem o efeito de remocao de celulas da mascara.",
        "",
        "## 3. como o CAND_B no-mask foi gerado",
        "1. tempRes numerico do dia z=299 carregado de `X_surface_300.npy` (idx=298).",
        "2. campo regridado para grelha completa do planner (linear + nearest fallback).",
        "3. ROI CAND_B exato carregado de `tempres_georef_candidate_transforms.csv`.",
        "4. subgrid CAND_B extraido sem aplicar mascara -> `candb_crop_nomask_day299.npy`.",
        "5. para comparacao, mascara do planner aplicada no mesmo subgrid -> `candb_crop_masked_day299.npy`.",
        "",
        "## 4. confirmacao de mesmo ROI/bbox do CAND_B",
        f"- same_roi_used: `{same_roi_used}`",
        f"- same_bbox_used: `{same_bbox_used}`",
        f"- ROI indices usados: x={roi.x0}..{roi.x1}, y={roi.y0}..{roi.y1}",
        "",
        "## 5. confirmacao de que no-mask nao aplicou mascara",
        f"- same_shape_nomask_vs_masked: `{same_shape_nomask_vs_masked}`",
        f"- valid_cells_nomask: `{valid_cells_nomask}`",
        f"- valid_cells_masked: `{valid_cells_masked}`",
        f"- masked_fraction: `{masked_fraction}`",
        f"- difference_due_to_mask_only_explained: `{difference_due_to_mask_only_explained}`",
        "",
        "## 6. outputs gerados",
        f"- `{rel(NPY_CANDB_NOMASK)}`",
        f"- `{rel(NPY_CANDB_MASKED)}`",
        f"- `{rel(NPY_CANDB_MASK)}`",
        f"- `{rel(NPY_FULL_REGRID)}`",
        f"- `{rel(FIG_CANDB_NOMASK)}`",
        f"- `{rel(FIG_CANDB_MASKED)}`",
        f"- `{rel(FIG_CANDB_MASK)}`",
        f"- `{rel(FIG_FULL_REGRID)}`",
        f"- `{rel(FIG_PANEL_NOMASK_VS_MASKED)}`",
        f"- `{rel(FIG_PANEL_PIPELINE)}`",
        f"- `{rel(FIG_PANEL_FOCUS)}`",
        f"- `{rel(JSON_CHECKS)}`",
        f"- `{rel(CSV_METRICS)}`",
        f"- `{rel(MD_REPORT)}`",
        f"- `{rel(MD_SUMMARY)}`",
        "",
    ]
    ensure_parent(MD_REPORT)
    MD_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    summary_lines = [
        "# CAND_B No-Mask Summary (day299)",
        "",
        f"- day_used: `{PLANNING_DATE.isoformat()} / z={DAY_Z}`",
        f"- source_numeric_field_used: `{rel(TEMP_STACK)}[idx={DAY_IDX}]`",
        f"- candb_crop_nomask_shape: `{candb_crop_nomask.shape}`",
        f"- candb_crop_masked_shape: `{candb_crop_masked.shape}`",
        f"- same_roi_used: `{same_roi_used}`",
        f"- same_bbox_used: `{same_bbox_used}`",
        f"- same_shape_nomask_vs_masked: `{same_shape_nomask_vs_masked}`",
        f"- difference_due_to_mask_only_explained: `{difference_due_to_mask_only_explained}`",
        "",
        "The CAND_B no-mask image uses the same ROI and planner subgrid as the original CAND_B crop, but preserves all cells before mask removal, allowing isolation of the crop effect from the mask effect.",
        "",
    ]
    ensure_parent(MD_SUMMARY)
    MD_SUMMARY.write_text("\n".join(summary_lines), encoding="utf-8")

    planner["ds"].close()

    outputs = [
        NPY_CANDB_NOMASK,
        NPY_CANDB_MASKED,
        NPY_CANDB_MASK,
        NPY_FULL_REGRID,
        FIG_CANDB_NOMASK,
        FIG_CANDB_MASKED,
        FIG_CANDB_MASK,
        FIG_FULL_REGRID,
        FIG_PANEL_NOMASK_VS_MASKED,
        FIG_PANEL_PIPELINE,
        FIG_PANEL_FOCUS,
        JSON_CHECKS,
        CSV_METRICS,
        MD_REPORT,
        MD_SUMMARY,
    ]
    print("Generated:")
    for p in outputs:
        print(rel(p))


if __name__ == "__main__":
    main()
