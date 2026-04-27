"""Generate CAND_B planner-subgrid temperature crop without applying planner mask (day299).

Goal:
- Keep exact same CAND_B ROI/bbox and planner subgrid as the masked run
- Produce a no-mask crop to isolate crop effect from mask-removal effect
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
OUT_DIR = RESULTS / "299"

PLANNING_DATE = date(2024, 10, 30)
TEMPRES_DAY_REQUESTED = 299

TEMP_STACK = RESULTS / "plots" / "X_surface_300.npy"
TEMP_SCALE_JSON = RESULTS / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json"
TEMPRES_PNG_DIR = RESULTS / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes"
CANDB_SOURCE_CSV = RESULTS / "tempres_georef_candidate_transforms.csv"
PLANNER_INTERFACE_DEFAULT = (
    RESULTS
    / "planner_baseline_scenario_c4_methodical_20260418_162500"
    / "inputs"
    / "30-10-2024_surface_dayfix_planner_interface.nc"
)
PREV_DAY299_CHECKS_JSON = RESULTS / "masked_crop_consistency_checks_day299.json"
PREV_DAY299_MASKED_NPY = RESULTS / "candb_temperature_on_planner_mask_day299.npy"


# Required outputs
OUT_CANDB_NOMASK_NPY = OUT_DIR / "candb_crop_nomask_day299.npy"
OUT_CANDB_MASKED_NPY = OUT_DIR / "candb_crop_masked_day299.npy"
OUT_CANDB_MASK_NPY = OUT_DIR / "candb_mask_day299.npy"
OUT_FULL_REGRID_NPY = OUT_DIR / "full_regridded_planner_nomask_day299.npy"

OUT_CANDB_NOMASK_PNG = OUT_DIR / "candb_crop_nomask_day299.png"
OUT_CANDB_MASKED_PNG = OUT_DIR / "candb_crop_masked_day299.png"
OUT_CANDB_MASK_PNG = OUT_DIR / "candb_mask_day299.png"
OUT_FULL_REGRID_PNG = OUT_DIR / "full_regridded_planner_nomask_day299.png"

OUT_PANEL_NOMASK_VS_MASKED = OUT_DIR / "comparison_candb_nomask_vs_masked_day299.png"
OUT_PANEL_PIPELINE = OUT_DIR / "comparison_candb_pipeline_day299.png"
OUT_PANEL_FOCUS = OUT_DIR / "comparison_candb_nomask_focus_day299.png"

OUT_CHECKS_JSON = OUT_DIR / "candb_nomask_checks_day299.json"
OUT_METRICS_CSV = OUT_DIR / "candb_nomask_metrics_day299.csv"
OUT_REPORT_MD = OUT_DIR / "candb_nomask_report_day299.md"
OUT_SUMMARY_MD = OUT_DIR / "candb_nomask_summary_day299.md"


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
    n_days = int(stack.shape[0])
    stack_shape = [int(s) for s in stack.shape]
    stack_range = [0, n_days - 1]

    z_vals = parse_png_z_values(TEMPRES_PNG_DIR)
    z_min, z_max = int(min(z_vals)), int(max(z_vals))

    selected_z = int(day_requested)
    selected_idx = selected_z - 1
    if selected_z < 1 or selected_z > n_days:
        raise RuntimeError(f"Selected z={selected_z} out of range 1..{n_days}")
    if selected_z not in z_vals:
        raise RuntimeError(f"Selected z={selected_z} not present in exported PNG set")

    selected_png = TEMPRES_PNG_DIR / f"TEMP_surface_2024_z{selected_z:03d}.png"
    if not selected_png.exists():
        raise FileNotFoundError(selected_png)

    return {
        "planning_date_used": PLANNING_DATE.isoformat(),
        "tempres_day_requested": int(day_requested),
        "tempres_indexing_convention_detected": (
            f"numeric stack 0-based [{stack_range[0]}..{stack_range[1]}], "
            f"PNG labels 1-based [{z_min}..{z_max}]"
        ),
        "stack_shape": stack_shape,
        "stack_index_range": stack_range,
        "selected_z": selected_z,
        "selected_array_index": selected_idx,
        "selected_png_reference": rel(selected_png),
        "final_day_mapping_decision": f"day299 -> z299 -> idx={selected_idx}",
        "mapping_decision_justification": "Repository convention: z labels are 1-based; numpy first axis is 0-based.",
    }


def load_temp_scale(temp_field: np.ndarray) -> Tuple[float, float, str]:
    if TEMP_SCALE_JSON.exists():
        payload = json.loads(TEMP_SCALE_JSON.read_text(encoding="utf-8"))
        return float(payload["vmin"]), float(payload["vmax"]), rel(TEMP_SCALE_JSON)
    vals = temp_field[np.isfinite(temp_field)]
    if vals.size == 0:
        return 0.0, 1.0, "fallback_default_scale"
    vmin = float(np.percentile(vals, 2.0))
    vmax = float(np.percentile(vals, 98.0))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.min(vals))
        vmax = float(np.max(vals))
    if vmin == vmax:
        vmax = vmin + 1e-9
    return vmin, vmax, "computed_from_numeric_field"


def find_planner_interface_for_day(day_used: date) -> Path:
    if PLANNER_INTERFACE_DEFAULT.exists() and parse_dd_mm_yyyy_token(PLANNER_INTERFACE_DEFAULT.name) == day_used:
        return PLANNER_INTERFACE_DEFAULT
    cands = sorted((RESULTS).rglob("*planner_interface.nc"))
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
    # Keep planner mask geometry exactly as previous run.
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
    return Roi(x0=x0, x1=x1, y0=y0, y1=y1)


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


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    ensure_parent(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols: List[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                cols.append(k)
                seen.add(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def robust_vmin_vmax(arr: np.ndarray) -> Tuple[float, float]:
    vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return 0.0, 1.0
    vmin = float(np.percentile(vals, 2.0))
    vmax = float(np.percentile(vals, 98.0))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.min(vals))
        vmax = float(np.max(vals))
    if vmin == vmax:
        vmax = vmin + 1e-9
    return vmin, vmax


def render_field(arr: np.ndarray, out_png: Path, title: str, cbar_label: str, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("x index")
    ax.set_ylabel("y index")
    ax.grid(alpha=0.2)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_mask(mask: np.ndarray, out_png: Path, title: str) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    im = ax.imshow(mask.astype(np.float64), origin="lower", cmap="gray", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    ax.set_title(title)
    ax.set_xlabel("x index")
    ax.set_ylabel("y index")
    ax.grid(alpha=0.2)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Mask (1=valid, 0=masked)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_panel_nomask_vs_masked(nomask: np.ndarray, mask: np.ndarray, masked: np.ndarray, out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 3, figsize=(16.2, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im0 = axes[0].imshow(nomask, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0].set_title(f"(a) CAND_B no-mask\nshape={nomask.shape[0]}x{nomask.shape[1]}")
    axes[0].set_xlabel("local x")
    axes[0].set_ylabel("local y")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(mask.astype(np.float64), origin="lower", cmap="gray", aspect="auto", interpolation="nearest", vmin=0.0, vmax=1.0)
    axes[1].set_title(f"(b) mask only\nmasked_frac={(1.0 - float(mask.mean())):.4f}")
    axes[1].set_xlabel("local x")
    axes[1].set_ylabel("local y")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    im2 = axes[2].imshow(masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[2].set_title(f"(c) CAND_B masked\nshape={masked.shape[0]}x{masked.shape[1]}")
    axes[2].set_xlabel("local x")
    axes[2].set_ylabel("local y")
    axes[2].grid(alpha=0.2)
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_panel_pipeline(native: np.ndarray, full_regrid: np.ndarray, nomask: np.ndarray, masked: np.ndarray, out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.0))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im00 = axes[0, 0].imshow(native, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0, 0].set_title(f"(a) tempRes native z299\nshape={native.shape[0]}x{native.shape[1]}")
    axes[0, 0].set_xlabel("x")
    axes[0, 0].set_ylabel("y")
    axes[0, 0].grid(alpha=0.2)
    fig.colorbar(im00, ax=axes[0, 0], fraction=0.046, pad=0.04)

    im01 = axes[0, 1].imshow(full_regrid, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0, 1].set_title(f"(b) full planner regridded (no-mask)\nshape={full_regrid.shape[0]}x{full_regrid.shape[1]}")
    axes[0, 1].set_xlabel("planner x")
    axes[0, 1].set_ylabel("planner y")
    axes[0, 1].grid(alpha=0.2)
    fig.colorbar(im01, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im10 = axes[1, 0].imshow(nomask, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1, 0].set_title(f"(c) CAND_B crop no-mask\nshape={nomask.shape[0]}x{nomask.shape[1]}")
    axes[1, 0].set_xlabel("local x")
    axes[1, 0].set_ylabel("local y")
    axes[1, 0].grid(alpha=0.2)
    fig.colorbar(im10, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im11 = axes[1, 1].imshow(masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1, 1].set_title(f"(d) CAND_B crop masked\nshape={masked.shape[0]}x{masked.shape[1]}")
    axes[1, 1].set_xlabel("local x")
    axes[1, 1].set_ylabel("local y")
    axes[1, 1].grid(alpha=0.2)
    fig.colorbar(im11, ax=axes[1, 1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def render_panel_focus(nomask: np.ndarray, masked: np.ndarray, out_png: Path, vmin: float, vmax: float) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im0 = axes[0].imshow(nomask, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0].set_title("(a) CAND_B no-mask")
    axes[0].set_xlabel("local x")
    axes[0].set_ylabel("local y")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1].set_title("(b) CAND_B masked")
    axes[1].set_xlabel("local x")
    axes[1].set_ylabel("local y")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def arrays_equal_with_nan(a: np.ndarray, b: np.ndarray, atol: float = 0.0) -> bool:
    ma = np.isfinite(a)
    mb = np.isfinite(b)
    if not np.array_equal(ma, mb):
        return False
    if np.any(ma):
        return bool(np.allclose(a[ma], b[ma], atol=atol, rtol=0.0))
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    day_audit = audit_day299_mapping(TEMPRES_DAY_REQUESTED)
    selected_idx = int(day_audit["selected_array_index"])
    selected_z = int(day_audit["selected_z"])

    stack = np.load(TEMP_STACK).astype(np.float64, copy=False)
    temp_day_native = np.asarray(stack[selected_idx], dtype=np.float64)
    temp_vmin, temp_vmax, temp_scale_source = load_temp_scale(temp_day_native)

    planner_path = find_planner_interface_for_day(PLANNING_DATE)
    planner = load_planner_interface(planner_path)
    planner_arr = planner["arr"]
    planner_lat = planner["lat"]
    planner_lon = planner["lon"]

    candb_roi = load_candb_roi(planner_lon, planner_lat)
    full_regridded_nomask, map_meta = map_temp_to_planner_full_grid(temp_day_native, planner_lat, planner_lon)

    # Same ROI/bbox as CAND_B original; crop without applying mask.
    candb_crop_nomask = crop(full_regridded_nomask, candb_roi)

    # Build exact planner mask from same CAND_B planner crop geometry.
    candb_planner_crop = crop(planner_arr, candb_roi)
    candb_mask = np.isfinite(candb_planner_crop)
    candb_crop_masked = np.where(candb_mask, candb_crop_nomask, np.nan)

    # Hard checks
    assert candb_crop_nomask.shape == candb_crop_masked.shape
    assert np.array_equal(np.isfinite(candb_crop_masked), candb_mask)
    assert np.all(np.isfinite(candb_crop_nomask)), "No-mask crop should preserve all cells in this mapping pipeline."
    assert np.allclose(candb_crop_nomask[candb_mask], candb_crop_masked[candb_mask], atol=0.0, rtol=0.0)

    # Compare ROI/bbox against previous day299 run if available.
    same_roi_used = True
    same_bbox_used = True
    previous_roi = None
    if PREV_DAY299_CHECKS_JSON.exists():
        prev = json.loads(PREV_DAY299_CHECKS_JSON.read_text(encoding="utf-8"))
        previous_roi = (((prev.get("method_rois_planner") or {}).get("candb")) or {})
        px0 = previous_roi.get("x0")
        px1 = previous_roi.get("x1")
        py0 = previous_roi.get("y0")
        py1 = previous_roi.get("y1")
        if None not in (px0, px1, py0, py1):
            same_roi_used = bool(int(px0) == candb_roi.x0 and int(px1) == candb_roi.x1 and int(py0) == candb_roi.y0 and int(py1) == candb_roi.y1)
            same_bbox_used = same_roi_used

    masked_matches_previous_saved = None
    if PREV_DAY299_MASKED_NPY.exists():
        prev_masked = np.load(PREV_DAY299_MASKED_NPY).astype(np.float64, copy=False)
        masked_matches_previous_saved = arrays_equal_with_nan(candb_crop_masked, prev_masked, atol=1e-12)

    same_shape_nomask_vs_masked = bool(candb_crop_nomask.shape == candb_crop_masked.shape)
    total_cells = int(candb_mask.size)
    valid_cells_nomask = int(np.isfinite(candb_crop_nomask).sum())
    valid_cells_masked = int(np.isfinite(candb_crop_masked).sum())
    masked_cells = int(total_cells - valid_cells_masked)
    masked_fraction = float(masked_cells / total_cells) if total_cells > 0 else 0.0

    difference_due_to_mask_only_explained = bool(
        same_shape_nomask_vs_masked
        and same_roi_used
        and same_bbox_used
        and np.array_equal(np.isfinite(candb_crop_masked), candb_mask)
        and np.allclose(candb_crop_nomask[candb_mask], candb_crop_masked[candb_mask], atol=0.0, rtol=0.0)
    )

    notes = (
        "No-mask crop uses exact same CAND_B ROI/subgrid as masked crop; "
        "masked version is produced by applying planner-derived boolean mask only."
    )

    # Save arrays
    np.save(OUT_CANDB_NOMASK_NPY, candb_crop_nomask)
    np.save(OUT_CANDB_MASKED_NPY, candb_crop_masked)
    np.save(OUT_CANDB_MASK_NPY, candb_mask.astype(bool))
    np.save(OUT_FULL_REGRID_NPY, full_regridded_nomask)

    # Render figures
    render_field(
        arr=candb_crop_nomask,
        out_png=OUT_CANDB_NOMASK_PNG,
        title=f"CAND_B crop no-mask day299\nshape={candb_crop_nomask.shape[0]}x{candb_crop_nomask.shape[1]}",
        cbar_label="Temperature (degC)",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    render_field(
        arr=candb_crop_masked,
        out_png=OUT_CANDB_MASKED_PNG,
        title=f"CAND_B crop masked day299\nshape={candb_crop_masked.shape[0]}x{candb_crop_masked.shape[1]}",
        cbar_label="Temperature (degC)",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    render_mask(
        mask=candb_mask,
        out_png=OUT_CANDB_MASK_PNG,
        title=f"CAND_B mask day299\nshape={candb_mask.shape[0]}x{candb_mask.shape[1]}",
    )
    render_field(
        arr=full_regridded_nomask,
        out_png=OUT_FULL_REGRID_PNG,
        title=f"Full planner regridded no-mask day299\nshape={full_regridded_nomask.shape[0]}x{full_regridded_nomask.shape[1]}",
        cbar_label="Temperature (degC)",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )

    render_panel_nomask_vs_masked(
        nomask=candb_crop_nomask,
        mask=candb_mask,
        masked=candb_crop_masked,
        out_png=OUT_PANEL_NOMASK_VS_MASKED,
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    render_panel_pipeline(
        native=temp_day_native,
        full_regrid=full_regridded_nomask,
        nomask=candb_crop_nomask,
        masked=candb_crop_masked,
        out_png=OUT_PANEL_PIPELINE,
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    render_panel_focus(
        nomask=candb_crop_nomask,
        masked=candb_crop_masked,
        out_png=OUT_PANEL_FOCUS,
        vmin=temp_vmin,
        vmax=temp_vmax,
    )

    # Metrics/checks
    metric_row = {
        "day_used": PLANNING_DATE.isoformat(),
        "source_numeric_field_used": f"{rel(TEMP_STACK)}[idx={selected_idx}] => z{selected_z:03d}",
        "full_regridded_shape": [int(full_regridded_nomask.shape[0]), int(full_regridded_nomask.shape[1])],
        "candb_crop_nomask_shape": [int(candb_crop_nomask.shape[0]), int(candb_crop_nomask.shape[1])],
        "candb_crop_masked_shape": [int(candb_crop_masked.shape[0]), int(candb_crop_masked.shape[1])],
        "same_roi_used": same_roi_used,
        "same_bbox_used": same_bbox_used,
        "same_shape_nomask_vs_masked": same_shape_nomask_vs_masked,
        "masked_fraction": masked_fraction,
        "valid_cells_nomask": valid_cells_nomask,
        "valid_cells_masked": valid_cells_masked,
        "difference_due_to_mask_only_explained": difference_due_to_mask_only_explained,
        "masked_matches_previous_saved_day299": masked_matches_previous_saved,
        "notes": notes,
    }
    write_csv(OUT_METRICS_CSV, [metric_row])

    checks_payload = {
        "generated_at_utc": now_iso(),
        "day_used": PLANNING_DATE.isoformat(),
        "planning_date_used": PLANNING_DATE.isoformat(),
        "tempres_day_requested": TEMPRES_DAY_REQUESTED,
        "source_numeric_field_used": f"{rel(TEMP_STACK)}[idx={selected_idx}] => z{selected_z:03d}",
        "tempres_png_reference": day_audit["selected_png_reference"],
        "tempres_indexing_convention_detected": day_audit["tempres_indexing_convention_detected"],
        "final_day_mapping_decision": day_audit["final_day_mapping_decision"],
        "mapping_decision_justification": day_audit["mapping_decision_justification"],
        "planner_interface_used": rel(planner_path),
        "candb_source_csv": rel(CANDB_SOURCE_CSV),
        "interpolation_meta": map_meta,
        "candb_roi_bbox_indices": {
            "x0": candb_roi.x0,
            "x1": candb_roi.x1,
            "y0": candb_roi.y0,
            "y1": candb_roi.y1,
            "width": candb_roi.width,
            "height": candb_roi.height,
        },
        "candb_roi_bbox_lonlat": {
            "lon_min": float(planner_lon[candb_roi.x0]),
            "lon_max": float(planner_lon[candb_roi.x1]),
            "lat_min": float(planner_lat[candb_roi.y0]),
            "lat_max": float(planner_lat[candb_roi.y1]),
        },
        "previous_day299_roi_from_checks_json": previous_roi,
        "full_regridded_shape": [int(full_regridded_nomask.shape[0]), int(full_regridded_nomask.shape[1])],
        "candb_crop_nomask_shape": [int(candb_crop_nomask.shape[0]), int(candb_crop_nomask.shape[1])],
        "candb_crop_masked_shape": [int(candb_crop_masked.shape[0]), int(candb_crop_masked.shape[1])],
        "same_roi_used": same_roi_used,
        "same_bbox_used": same_bbox_used,
        "same_shape_nomask_vs_masked": same_shape_nomask_vs_masked,
        "masked_fraction": masked_fraction,
        "valid_cells_nomask": valid_cells_nomask,
        "valid_cells_masked": valid_cells_masked,
        "masked_cells": masked_cells,
        "mask_shape": [int(candb_mask.shape[0]), int(candb_mask.shape[1])],
        "nomask_has_all_cells_visible": bool(valid_cells_nomask == total_cells),
        "masked_boolean_equals_finite_of_masked_crop": bool(np.array_equal(candb_mask, np.isfinite(candb_crop_masked))),
        "difference_due_to_mask_only_explained": difference_due_to_mask_only_explained,
        "masked_matches_previous_saved_day299": masked_matches_previous_saved,
        "notes": notes,
        "outputs": [
            rel(OUT_CANDB_NOMASK_NPY),
            rel(OUT_CANDB_MASKED_NPY),
            rel(OUT_CANDB_MASK_NPY),
            rel(OUT_FULL_REGRID_NPY),
            rel(OUT_CANDB_NOMASK_PNG),
            rel(OUT_CANDB_MASKED_PNG),
            rel(OUT_CANDB_MASK_PNG),
            rel(OUT_FULL_REGRID_PNG),
            rel(OUT_PANEL_NOMASK_VS_MASKED),
            rel(OUT_PANEL_PIPELINE),
            rel(OUT_PANEL_FOCUS),
            rel(OUT_CHECKS_JSON),
            rel(OUT_METRICS_CSV),
            rel(OUT_REPORT_MD),
            rel(OUT_SUMMARY_MD),
        ],
    }
    ensure_parent(OUT_CHECKS_JSON)
    OUT_CHECKS_JSON.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    report_lines = [
        "# CAND_B No-Mask Report (day299)",
        "",
        "## 1) Objective Of This Run",
        "- This run isolates the effect of ROI/crop framing from the effect of planner-mask cell removal for CAND_B.",
        "",
        "## 2) Why This Run",
        "- Previous analyses mixed two visual effects: crop framing and masked-cell removal.",
        "- Here, the no-mask CAND_B crop keeps all cells in the same ROI/subgrid to isolate crop effect only.",
        "",
        "## 3) How CAND_B No-Mask Was Generated",
        "1. Loaded tempRes numerical field for day z299 (`X_surface_300.npy`, idx=298).",
        "2. Regridded to full planner grid via linear interpolation + nearest fallback.",
        "3. Extracted exact CAND_B ROI (same bbox indices as method CAND_B).",
        "4. Saved crop without applying planner mask (`candb_crop_nomask_day299`).",
        "5. Built masked counterpart only by applying the same planner mask to the same no-mask crop.",
        "",
        "## 4) ROI/BBox Consistency Confirmation",
        f"- same_roi_used: `{same_roi_used}`",
        f"- same_bbox_used: `{same_bbox_used}`",
        f"- CAND_B ROI indices: x[{candb_roi.x0}:{candb_roi.x1}], y[{candb_roi.y0}:{candb_roi.y1}]",
        f"- CAND_B ROI lon/lat bbox: lon[{float(planner_lon[candb_roi.x0]):.6f},{float(planner_lon[candb_roi.x1]):.6f}], lat[{float(planner_lat[candb_roi.y0]):.6f},{float(planner_lat[candb_roi.y1]):.6f}]",
        "",
        "## 5) Mask-Application Confirmation",
        "- No-mask version does not apply planner mask.",
        "- Masked version is created as `np.where(mask, nomask, np.nan)` using the same ROI/subgrid and same shape.",
        f"- same_shape_nomask_vs_masked: `{same_shape_nomask_vs_masked}`",
        f"- difference_due_to_mask_only_explained: `{difference_due_to_mask_only_explained}`",
        "",
        "## 6) Generated Outputs",
        f"- `{rel(OUT_CANDB_NOMASK_NPY)}`",
        f"- `{rel(OUT_CANDB_MASKED_NPY)}`",
        f"- `{rel(OUT_CANDB_MASK_NPY)}`",
        f"- `{rel(OUT_FULL_REGRID_NPY)}`",
        f"- `{rel(OUT_CANDB_NOMASK_PNG)}`",
        f"- `{rel(OUT_CANDB_MASKED_PNG)}`",
        f"- `{rel(OUT_CANDB_MASK_PNG)}`",
        f"- `{rel(OUT_FULL_REGRID_PNG)}`",
        f"- `{rel(OUT_PANEL_NOMASK_VS_MASKED)}`",
        f"- `{rel(OUT_PANEL_PIPELINE)}`",
        f"- `{rel(OUT_PANEL_FOCUS)}`",
        f"- `{rel(OUT_CHECKS_JSON)}`",
        f"- `{rel(OUT_METRICS_CSV)}`",
    ]
    ensure_parent(OUT_REPORT_MD)
    OUT_REPORT_MD.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# CAND_B No-Mask Summary (day299)",
        "",
        f"- day_used: `{PLANNING_DATE.isoformat()}`",
        f"- source_numeric_field_used: `{rel(TEMP_STACK)}[idx={selected_idx}] => z{selected_z:03d}`",
        f"- candb_crop_nomask_shape: `{candb_crop_nomask.shape}`",
        f"- candb_crop_masked_shape: `{candb_crop_masked.shape}`",
        f"- same_roi_used: `{same_roi_used}`",
        f"- same_bbox_used: `{same_bbox_used}`",
        f"- same_shape_nomask_vs_masked: `{same_shape_nomask_vs_masked}`",
        f"- masked_fraction: `{masked_fraction:.6f}`",
        f"- valid_cells_nomask: `{valid_cells_nomask}`",
        f"- valid_cells_masked: `{valid_cells_masked}`",
        f"- difference_due_to_mask_only_explained: `{difference_due_to_mask_only_explained}`",
        f"- checks_json: `{rel(OUT_CHECKS_JSON)}`",
        f"- metrics_csv: `{rel(OUT_METRICS_CSV)}`",
    ]
    ensure_parent(OUT_SUMMARY_MD)
    OUT_SUMMARY_MD.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    planner["ds"].close()

    print("Generated outputs:")
    for p in [
        OUT_CANDB_NOMASK_NPY,
        OUT_CANDB_MASKED_NPY,
        OUT_CANDB_MASK_NPY,
        OUT_FULL_REGRID_NPY,
        OUT_CANDB_NOMASK_PNG,
        OUT_CANDB_MASKED_PNG,
        OUT_CANDB_MASK_PNG,
        OUT_FULL_REGRID_PNG,
        OUT_PANEL_NOMASK_VS_MASKED,
        OUT_PANEL_PIPELINE,
        OUT_PANEL_FOCUS,
        OUT_CHECKS_JSON,
        OUT_METRICS_CSV,
        OUT_REPORT_MD,
        OUT_SUMMARY_MD,
    ]:
        print(rel(p))


if __name__ == "__main__":
    main()
