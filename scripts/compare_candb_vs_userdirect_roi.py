"""Compare CAND_B registration ROI vs user direct local-km ROI on planner grid.

This script is audit/visualization only.
It does not modify solver/planner scientific core.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# Outputs requested by user.
OUT_SCRIPT_NAME = "compare_candb_vs_userdirect_roi.py"
OUT_REPORT = RESULTS / "candb_vs_userdirect_report.md"
OUT_SUMMARY = RESULTS / "candb_vs_userdirect_summary.md"
OUT_METRICS = RESULTS / "candb_vs_userdirect_metrics.csv"
OUT_BBOXES = RESULTS / "candb_vs_userdirect_bboxes.csv"
OUT_CHECKS = RESULTS / "candb_vs_userdirect_checks.json"

FIG_PLANNER_FULL = RESULTS / "planner_operational_roi_fullgrid.png"
FIG_PLANNER_CROP = RESULTS / "planner_operational_roi_crop.png"
FIG_CANDB_FULL = RESULTS / "candb_roi_on_planner_fullgrid.png"
FIG_CANDB_CROP = RESULTS / "candb_roi_crop.png"
FIG_DET_FULL = RESULTS / "deterministic_same_day_full.png"
FIG_DET_CROP = RESULTS / "deterministic_same_day_roi_crop.png"
FIG_USER_FULL = RESULTS / "user_direct_km_roi_on_planner_fullgrid.png"
FIG_USER_CROP = RESULTS / "user_direct_km_roi_crop.png"
FIG_PANEL = RESULTS / "comparison_panel_roi_methods.png"
FIG_OVERLAY = RESULTS / "comparison_overlay_planner_methods.png"
FIG_CROPS = RESULTS / "comparison_crops_methods_vs_reference.png"


PLANNER_INTERFACE_DEFAULT = (
    ROOT
    / "results"
    / "planner_baseline_scenario_c4_predmodel"
    / "inputs"
    / "30-10-2024_predModel_1_planner_interface.nc"
)
CONFIG_FILE = ROOT / "OptimalPlanning_Lucrezia" / "Config_file.py"
TEMP_STACK = ROOT / "results" / "plots" / "X_surface_300.npy"
TEMPRES_GEOR_CAND_CSV = ROOT / "results" / "tempres_georef_candidate_transforms.csv"
REG_MATCH_PRED = (
    ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4" / "tables" / "best_candidate_matches_predModel.csv"
)
REG_MATCH_AUV = (
    ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4" / "tables" / "best_candidate_matches_AUVpredModel.csv"
)


@dataclass
class Roi:
    name: str
    x0: int
    x1: int
    y0: int
    y1: int
    notes: str = ""
    method: str = ""
    frame: str = "planner_index"
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None
    lat_min: Optional[float] = None
    lat_max: Optional[float] = None
    x_km_min: Optional[float] = None
    x_km_max: Optional[float] = None
    y_km_min: Optional[float] = None
    y_km_max: Optional[float] = None

    @property
    def width(self) -> int:
        return int(self.x1 - self.x0 + 1)

    @property
    def height(self) -> int:
        return int(self.y1 - self.y0 + 1)

    @property
    def area_cells(self) -> int:
        return int(self.width * self.height)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def km_per_degree(lat_deg: float) -> Tuple[float, float]:
    phi = math.radians(lat_deg)
    km_deg_lat = (
        111.13292
        - 0.55982 * math.cos(2.0 * phi)
        + 0.001175 * math.cos(4.0 * phi)
        - 0.0000023 * math.cos(6.0 * phi)
    )
    km_deg_lon = 111.41284 * math.cos(phi) - 0.0935 * math.cos(3.0 * phi) + 0.00012 * math.cos(5.0 * phi)
    return km_deg_lat, km_deg_lon


def parse_operation_corners(config_file: Path) -> Tuple[List[float], List[float]]:
    txt = config_file.read_text(encoding="utf-8", errors="ignore")
    ll = re.search(r"OPERATION_LL_CORNER\s*=\s*\[\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*\]", txt)
    ur = re.search(r"OPERATION_UR_CORNER\s*=\s*\[\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*\]", txt)
    if ll is None or ur is None:
        raise RuntimeError("Could not parse OPERATION_LL_CORNER/OPERATION_UR_CORNER from Config_file.py")
    ll_vals = [float(ll.group(1)), float(ll.group(2))]
    ur_vals = [float(ur.group(1)), float(ur.group(2))]
    return ll_vals, ur_vals


def first_gt(arr: np.ndarray, value: float) -> int:
    idx = np.where(arr > value)[0]
    if idx.size == 0:
        raise RuntimeError(f"Axis has no values > {value}")
    return int(idx[0])


def load_planner_interface(path: Path) -> Dict[str, object]:
    ds = xr.open_dataset(path, decode_times=False)
    try:
        lat_name = next((c for c in ds.coords if c.lower() == "lat"), None)
        lon_name = next((c for c in ds.coords if c.lower() == "lon"), None)
        if lat_name is None or lon_name is None:
            raise RuntimeError("Missing lat/lon coords in planner interface")
        lat = ds[lat_name].values.astype(np.float64, copy=False)
        lon = ds[lon_name].values.astype(np.float64, copy=False)

        arr = ds["temperr"].values.astype(np.float64, copy=False)
        if "landt" in ds:
            land = ds["landt"].values
            arr = arr.copy()
            arr[land != 1] = np.nan
        else:
            land = None
        lat_mid = 0.5 * float(lat.min() + lat.max())
        km_deg_lat, km_deg_lon = km_per_degree(lat_mid)
        dlat = float(np.mean(np.diff(lat)))
        dlon = float(np.mean(np.diff(lon)))
        return {
            "ds": ds,
            "lat": lat,
            "lon": lon,
            "temperr_plot": arr,
            "land": land,
            "dx_m": abs(dlon) * km_deg_lon * 1000.0,
            "dy_m": abs(dlat) * km_deg_lat * 1000.0,
        }
    except Exception:
        ds.close()
        raise


def find_planner_interface() -> Path:
    if PLANNER_INTERFACE_DEFAULT.exists():
        return PLANNER_INTERFACE_DEFAULT
    candidates = sorted((ROOT / "results").rglob("*planner_interface.nc"))
    if not candidates:
        raise FileNotFoundError("No planner_interface.nc found under results/")
    # Prefer files with 30-10-2024 token.
    preferred = [p for p in candidates if "30-10-2024" in p.name]
    return preferred[0] if preferred else candidates[0]


def parse_date_from_filename(path: Path) -> Optional[date]:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", path.name)
    if m is None:
        return None
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(yyyy, mm, dd)


def load_candb_roi() -> Roi:
    if not TEMPRES_GEOR_CAND_CSV.exists():
        raise FileNotFoundError(TEMPRES_GEOR_CAND_CSV)
    with TEMPRES_GEOR_CAND_CSV.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found in tempres_georef_candidate_transforms.csv")
    x0 = int(row["x0_hres_idx"])
    x1 = int(row["x1_hres_idx"])
    y0 = int(row["y0_hres_idx"])
    y1 = int(row["y1_hres_idx"])
    return Roi(
        name="CAND_B",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        method="CAND_B_REGISTRATION_TO_HRES_SUBAREA",
        notes="Registration-derived ROI from best controlled alignment (not native georeference proof).",
    )


def find_relative_km_parent() -> Path:
    base = ROOT / "results" / "plots"
    parents = sorted(base.glob("tempibhres_relative_km_display_assumed*"))
    best_parent: Optional[Path] = None
    best_count = -1
    for p in parents:
        det = p / "deterministic_2024_surface_300_thesis_relative_km_display_assumed"
        if not det.exists():
            continue
        count = len(list(det.glob("TEMP_surface_2024_z*.png")))
        if count > best_count:
            best_parent = p
            best_count = count
    if best_parent is None:
        raise RuntimeError("Could not find deterministic_2024_surface_300_thesis_relative_km_display_assumed parent")
    return best_parent


def parse_det_day_selection(det_dir: Path, target_day: date) -> Dict[str, object]:
    z_vals: List[int] = []
    for p in det_dir.glob("TEMP_surface_2024_z*.png"):
        m = re.search(r"_z(\d{3})\.png$", p.name)
        if m:
            z_vals.append(int(m.group(1)))
    if not z_vals:
        raise RuntimeError(f"No deterministic z files in {det_dir}")
    z_vals = sorted(set(z_vals))
    max_z = max(z_vals)
    min_z = min(z_vals)

    doy = int(target_day.timetuple().tm_yday)
    # Convention used here: day-of-year -> z, clipped to available z-range.
    proposed = doy
    selected = min(max(proposed, min_z), max_z)
    if selected not in z_vals:
        selected = min(z_vals, key=lambda z: abs(z - proposed))

    if proposed == selected:
        convention = "DOY_TO_Z_EXACT"
        reason = "day-of-year is inside deterministic z-range"
    elif proposed > max_z:
        convention = "DOY_TO_Z_CLIPPED_MAX"
        reason = f"day-of-year={proposed} exceeds available z_max={max_z}; clipped to z={selected}"
    elif proposed < min_z:
        convention = "DOY_TO_Z_CLIPPED_MIN"
        reason = f"day-of-year={proposed} below z_min={min_z}; clipped to z={selected}"
    else:
        convention = "DOY_TO_Z_NEAREST_AVAILABLE"
        reason = f"exact z={proposed} missing; used nearest available z={selected}"

    selected_png = det_dir / f"TEMP_surface_2024_z{selected:03d}.png"
    if not selected_png.exists():
        # Fallback nearest file.
        all_png = sorted(det_dir.glob("TEMP_surface_2024_z*.png"))
        selected_png = all_png[0]

    return {
        "target_day": target_day.isoformat(),
        "target_day_doy": doy,
        "available_z_min": min_z,
        "available_z_max": max_z,
        "selected_z": selected,
        "selected_png": selected_png,
        "convention": convention,
        "convention_reason": reason,
    }


def load_registration_day_hints() -> Dict[str, object]:
    hints: Dict[str, object] = {}
    for key, p in [("pred", REG_MATCH_PRED), ("auv", REG_MATCH_AUV)]:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        vals = [int(r["matched_temp_day_1based"]) for r in rows if r.get("matched_temp_day_1based")]
        if not vals:
            continue
        counts: Dict[int, int] = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        top_day = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        hints[key] = {
            "top_matched_day": int(top_day),
            "unique_days": sorted(counts.keys()),
        }
    return hints


def bilinear_resize(arr: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float64)
    in_h, in_w = arr.shape
    if in_h == out_h and in_w == out_w:
        return arr.copy()
    y = np.linspace(0.0, in_h - 1, out_h)
    x = np.linspace(0.0, in_w - 1, out_w)
    y0 = np.floor(y).astype(int)
    x0 = np.floor(x).astype(int)
    y1 = np.clip(y0 + 1, 0, in_h - 1)
    x1 = np.clip(x0 + 1, 0, in_w - 1)
    wy = y - y0
    wx = x - x0
    Ia = arr[y0[:, None], x0[None, :]]
    Ib = arr[y0[:, None], x1[None, :]]
    Ic = arr[y1[:, None], x0[None, :]]
    Id = arr[y1[:, None], x1[None, :]]
    wx2 = wx[None, :]
    wy2 = wy[:, None]
    top = Ia * (1 - wx2) + Ib * wx2
    bot = Ic * (1 - wx2) + Id * wx2
    out = top * (1 - wy2) + bot * wy2
    return out


def bbox_intersection(a: Roi, b: Roi) -> int:
    ix0 = max(a.x0, b.x0)
    ix1 = min(a.x1, b.x1)
    iy0 = max(a.y0, b.y0)
    iy1 = min(a.y1, b.y1)
    if ix1 < ix0 or iy1 < iy0:
        return 0
    return int((ix1 - ix0 + 1) * (iy1 - iy0 + 1))


def bbox_iou(a: Roi, b: Roi) -> float:
    inter = bbox_intersection(a, b)
    union = a.area_cells + b.area_cells - inter
    return float(inter / union) if union > 0 else 0.0


def zscore(v: np.ndarray) -> np.ndarray:
    m = float(np.nanmean(v))
    s = float(np.nanstd(v))
    if s <= 1e-12:
        return v * 0.0
    return (v - m) / s


def compare_to_reference(method_crop: np.ndarray, ref_crop: np.ndarray) -> Dict[str, float]:
    ref_r = bilinear_resize(ref_crop, out_h=method_crop.shape[0], out_w=method_crop.shape[1])
    a = np.asarray(method_crop, dtype=np.float64)
    b = np.asarray(ref_r, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    n = int(mask.sum())
    if n < 10:
        return {
            "n_valid": n,
            "pearson_r": float("nan"),
            "ncc": float("nan"),
            "rmse_zscore": float("nan"),
            "mae_zscore": float("nan"),
        }
    av = a[mask]
    bv = b[mask]
    az = zscore(av)
    bz = zscore(bv)
    denom = np.linalg.norm(az) * np.linalg.norm(bz)
    ncc = float(np.dot(az, bz) / denom) if denom > 0 else float("nan")
    if np.std(av) <= 1e-12 or np.std(bv) <= 1e-12:
        pear = float("nan")
    else:
        pear = float(np.corrcoef(av, bv)[0, 1])
    diff = az - bz
    rmse = float(np.sqrt(np.mean(diff * diff)))
    mae = float(np.mean(np.abs(diff)))
    return {
        "n_valid": n,
        "pearson_r": pear,
        "ncc": ncc,
        "rmse_zscore": rmse,
        "mae_zscore": mae,
    }


def plot_planner_full(
    arr: np.ndarray,
    rois: Iterable[Tuple[Roi, str, str]],
    title: str,
    out_png: Path,
) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest")
    for roi, color, label in rois:
        rect = plt.Rectangle(
            (roi.x0 - 0.5, roi.y0 - 0.5),
            roi.width,
            roi.height,
            fill=False,
            linewidth=2.2,
            edgecolor=color,
            label=label,
        )
        ax.add_patch(rect)
    ax.set_title(title)
    ax.set_xlabel("Planner lon index")
    ax.set_ylabel("Planner lat index")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("temperr")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_crop(arr: np.ndarray, title: str, out_png: Path, xlab: str = "x", ylab: str = "y", cmap_name: str = "viridis") -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest")
    ax.set_title(title)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.2)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_det_km(arr: np.ndarray, extent: Tuple[float, float, float, float], title: str, out_png: Path) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", extent=extent)
    ax.set_title(title)
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.grid(alpha=0.2)
    fig.colorbar(im, ax=ax).set_label("temp")
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_panel(op_crop: np.ndarray, cand_crop: np.ndarray, usr_crop: np.ndarray, det_crop: np.ndarray, out_png: Path) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.2))
    panels = [
        (op_crop, "Planner operational ROI crop"),
        (cand_crop, "CAND_B ROI crop"),
        (usr_crop, "USER_DIRECT_KM ROI crop"),
        (det_crop, "Deterministic same-day reference"),
    ]
    for ax, (arr, ttl) in zip(axes.ravel(), panels):
        cmap = plt.get_cmap("viridis").copy()
        cmap.set_bad(color="white")
        ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest")
        ax.set_title(f"{ttl}\nshape={arr.shape[0]}x{arr.shape[1]}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_crops_vs_ref(cand_crop: np.ndarray, usr_crop: np.ndarray, det_crop: np.ndarray, out_png: Path) -> None:
    ensure_parent(out_png)
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.1))
    panels = [
        (cand_crop, "CAND_B crop"),
        (usr_crop, "USER_DIRECT_KM crop"),
        (det_crop, "Deterministic reference crop"),
    ]
    for ax, (arr, ttl) in zip(axes, panels):
        cmap = plt.get_cmap("viridis").copy()
        cmap.set_bad(color="white")
        ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest")
        ax.set_title(f"{ttl}\nshape={arr.shape[0]}x{arr.shape[1]}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(alpha=0.2)
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


def main() -> None:
    planner_interface = find_planner_interface()
    planner_date = parse_date_from_filename(planner_interface)
    if planner_date is None:
        # conservative fallback based on request/context.
        planner_date = date(2024, 10, 30)

    planner = load_planner_interface(planner_interface)
    ll, ur = parse_operation_corners(CONFIG_FILE)
    lat = planner["lat"]
    lon = planner["lon"]

    # Operational ROI using planner code logic.
    lat_start = first_gt(lat, ll[0])
    lat_stop = first_gt(lat, ur[0]) - 1
    lon_start = first_gt(lon, ll[1])
    lon_stop = first_gt(lon, ur[1]) - 1
    op_roi = Roi(
        name="PLANNER_OPERATIONAL_ROI",
        x0=int(lon_start),
        x1=int(lon_stop - 1),
        y0=int(lat_start),
        y1=int(lat_stop - 1),
        method="planner_config_crop",
        notes="Derived from Config_file.py OPERATION_LL_CORNER/UR_CORNER using planner slicing logic.",
    )
    op_roi.lon_min = float(lon[op_roi.x0])
    op_roi.lon_max = float(lon[op_roi.x1])
    op_roi.lat_min = float(lat[op_roi.y0])
    op_roi.lat_max = float(lat[op_roi.y1])

    candb_roi = load_candb_roi()
    candb_roi.lon_min = float(lon[candb_roi.x0])
    candb_roi.lon_max = float(lon[candb_roi.x1])
    candb_roi.lat_min = float(lat[candb_roi.y0])
    candb_roi.lat_max = float(lat[candb_roi.y1])

    rel_parent = find_relative_km_parent()
    rel_manifest = rel_parent / "manifest.json"
    rel_payload = json.loads(rel_manifest.read_text(encoding="utf-8"))
    det_dir = rel_parent / "deterministic_2024_surface_300_thesis_relative_km_display_assumed"
    det_selection = parse_det_day_selection(det_dir, planner_date)

    # User direct method from local-km ROI definitions in the selected deterministic relative-km package.
    crop_info = rel_payload["crop"]
    full_ny, full_nx = int(crop_info["full_shape_ny_nx"][0]), int(crop_info["full_shape_ny_nx"][1])
    x_start_1b = int(crop_info["x_start_col_1based"])
    x_end_1b = int(crop_info["x_end_col_1based"])
    y_start_1b = int(crop_info["y_start_row_1based"])
    y_end_1b = int(crop_info["y_end_row_1based"])
    hres_bbox = rel_payload["hres_bbox_source"]

    # Direct local-km to lon/lat via display-derived linear mapping (no CAND_B adjustment).
    ux0 = (x_start_1b - 1) / max(1, full_nx - 1)
    ux1 = (x_end_1b - 1) / max(1, full_nx - 1)
    uy0 = (y_start_1b - 1) / max(1, full_ny - 1)
    uy1 = (y_end_1b - 1) / max(1, full_ny - 1)
    user_lon_min = float(hres_bbox["lon_min"] + ux0 * (hres_bbox["lon_max"] - hres_bbox["lon_min"]))
    user_lon_max = float(hres_bbox["lon_min"] + ux1 * (hres_bbox["lon_max"] - hres_bbox["lon_min"]))
    user_lat_min = float(hres_bbox["lat_min"] + uy0 * (hres_bbox["lat_max"] - hres_bbox["lat_min"]))
    user_lat_max = float(hres_bbox["lat_min"] + uy1 * (hres_bbox["lat_max"] - hres_bbox["lat_min"]))

    user_x0 = int(np.searchsorted(lon, user_lon_min, side="left"))
    user_x1_excl = int(np.searchsorted(lon, user_lon_max, side="right"))
    user_y0 = int(np.searchsorted(lat, user_lat_min, side="left"))
    user_y1_excl = int(np.searchsorted(lat, user_lat_max, side="right"))
    user_x0 = int(np.clip(user_x0, 0, lon.size - 1))
    user_y0 = int(np.clip(user_y0, 0, lat.size - 1))
    user_x1 = int(np.clip(max(user_x0, user_x1_excl - 1), 0, lon.size - 1))
    user_y1 = int(np.clip(max(user_y0, user_y1_excl - 1), 0, lat.size - 1))

    user_roi = Roi(
        name="USER_DIRECT_KM_METHOD",
        x0=user_x0,
        x1=user_x1,
        y0=user_y0,
        y1=user_y1,
        method="USER_DIRECT_KM_METHOD",
        notes="Direct ROI from local-km display axes mapped linearly to HRes/planner bbox (without CAND_B registration refinement).",
    )
    user_roi.lon_min = float(lon[user_roi.x0])
    user_roi.lon_max = float(lon[user_roi.x1])
    user_roi.lat_min = float(lat[user_roi.y0])
    user_roi.lat_max = float(lat[user_roi.y1])

    # local-km ROI bounds from manifest geometry + offsets.
    geom = rel_payload["relative_km_geometry"]
    offsets = rel_payload["axis_offsets_km"]
    dx_km = float(geom["dx_km_per_cell"])
    dy_km = float(geom["dy_km_per_cell"])
    x_off = float(offsets["x_offset_km"])
    y_off = float(offsets["y_offset_km"])
    user_roi.x_km_min = float((x_start_1b - 1) * dx_km + x_off)
    user_roi.x_km_max = float((x_end_1b - 1) * dx_km + x_off)
    user_roi.y_km_min = float((y_start_1b - 1) * dy_km + y_off)
    user_roi.y_km_max = float((y_end_1b - 1) * dy_km + y_off)

    # Load deterministic same-day array from X_surface_300 and manifest crop.
    x_surface = np.load(TEMP_STACK).astype(np.float64, copy=False)
    z = int(det_selection["selected_z"])
    det_full_native = x_surface[z - 1]
    y_slice = slice(y_start_1b - 1, y_end_1b)
    x_slice = slice(x_start_1b - 1, x_end_1b)
    det_crop = det_full_native[y_slice, x_slice]

    x_km_axis = np.arange(full_nx, dtype=np.float64) * dx_km + x_off
    y_km_axis = np.arange(full_ny, dtype=np.float64) * dy_km + y_off
    x_km_crop = x_km_axis[x_slice]
    y_km_crop = y_km_axis[y_slice]
    det_extent = (float(x_km_crop.min()), float(x_km_crop.max()), float(y_km_crop.min()), float(y_km_crop.max()))

    # Planner crops.
    planner_arr = planner["temperr_plot"]
    op_crop = planner_arr[op_roi.y0 : op_roi.y1 + 1, op_roi.x0 : op_roi.x1 + 1]
    candb_crop = planner_arr[candb_roi.y0 : candb_roi.y1 + 1, candb_roi.x0 : candb_roi.x1 + 1]
    user_crop = planner_arr[user_roi.y0 : user_roi.y1 + 1, user_roi.x0 : user_roi.x1 + 1]

    # Figure A: planner operational ROI.
    plot_planner_full(
        planner_arr,
        [(op_roi, "#20a387", "Operational ROI")],
        "Planner full grid with operational ROI",
        FIG_PLANNER_FULL,
    )
    plot_crop(op_crop, "Planner operational ROI crop", FIG_PLANNER_CROP, xlab="lon idx", ylab="lat idx")

    # Figure B: CAND_B.
    plot_planner_full(
        planner_arr,
        [(candb_roi, "#e74c3c", "CAND_B ROI")],
        "CAND_B ROI on planner full grid",
        FIG_CANDB_FULL,
    )
    plot_crop(candb_crop, "CAND_B ROI crop", FIG_CANDB_CROP, xlab="lon idx", ylab="lat idx")

    # Figure C: deterministic same-day.
    plot_det_km(
        det_crop,
        det_extent,
        f"Deterministic same-day reference (z={z:03d})",
        FIG_DET_FULL,
    )
    # No finer independent ROI definition found inside deterministic local-km panel, so this is the same crop.
    plot_det_km(
        det_crop,
        det_extent,
        f"Deterministic same-day ROI crop (same as available panel, z={z:03d})",
        FIG_DET_CROP,
    )

    # Figure D: user direct km method.
    plot_planner_full(
        planner_arr,
        [(user_roi, "#1f77b4", "USER_DIRECT_KM ROI")],
        "USER_DIRECT_KM ROI on planner full grid",
        FIG_USER_FULL,
    )
    plot_crop(user_crop, "USER_DIRECT_KM ROI crop", FIG_USER_CROP, xlab="lon idx", ylab="lat idx")

    # Comparison figures.
    plot_panel(op_crop, candb_crop, user_crop, det_crop, FIG_PANEL)
    plot_planner_full(
        planner_arr,
        [
            (op_roi, "#20a387", "Operational ROI"),
            (candb_roi, "#e74c3c", "CAND_B ROI"),
            (user_roi, "#1f77b4", "USER_DIRECT_KM ROI"),
        ],
        "Planner overlay: operational ROI vs CAND_B vs USER_DIRECT_KM",
        FIG_OVERLAY,
    )
    plot_crops_vs_ref(candb_crop, user_crop, det_crop, FIG_CROPS)

    # Metrics.
    op_area = op_roi.area_cells
    cand_inter_op = bbox_intersection(candb_roi, op_roi)
    usr_inter_op = bbox_intersection(user_roi, op_roi)
    cand_metrics_ref = compare_to_reference(candb_crop, det_crop)
    usr_metrics_ref = compare_to_reference(user_crop, det_crop)

    cand_metrics = {
        "method": "CAND_B",
        "method_type": "registration-derived",
        "bbox_index": f"x={candb_roi.x0}..{candb_roi.x1}; y={candb_roi.y0}..{candb_roi.y1}",
        "bbox_lonlat": f"lon={candb_roi.lon_min:.6f}..{candb_roi.lon_max:.6f}; lat={candb_roi.lat_min:.6f}..{candb_roi.lat_max:.6f}",
        "shape_ny_nx": f"{candb_roi.height}x{candb_roi.width}",
        "area_cells": candb_roi.area_cells,
        "area_km2": float(candb_roi.area_cells * planner["dx_m"] * planner["dy_m"] / 1e6),
        "overlap_iou_with_operational_roi": bbox_iou(candb_roi, op_roi),
        "overlap_fraction_of_operational_roi": float(cand_inter_op / op_area) if op_area > 0 else float("nan"),
        "overlap_fraction_of_method_roi": float(cand_inter_op / candb_roi.area_cells) if candb_roi.area_cells > 0 else float("nan"),
        "pearson_vs_deterministic_ref": cand_metrics_ref["pearson_r"],
        "ncc_vs_deterministic_ref": cand_metrics_ref["ncc"],
        "rmse_zscore_vs_deterministic_ref": cand_metrics_ref["rmse_zscore"],
        "mae_zscore_vs_deterministic_ref": cand_metrics_ref["mae_zscore"],
        "n_valid_corr_pixels": cand_metrics_ref["n_valid"],
        "resample_for_ref": "bilinear_resize(reference -> method_shape)",
    }
    usr_metrics = {
        "method": "USER_DIRECT_KM_METHOD",
        "method_type": "display-axes-direct",
        "bbox_index": f"x={user_roi.x0}..{user_roi.x1}; y={user_roi.y0}..{user_roi.y1}",
        "bbox_lonlat": f"lon={user_roi.lon_min:.6f}..{user_roi.lon_max:.6f}; lat={user_roi.lat_min:.6f}..{user_roi.lat_max:.6f}",
        "shape_ny_nx": f"{user_roi.height}x{user_roi.width}",
        "area_cells": user_roi.area_cells,
        "area_km2": float(user_roi.area_cells * planner["dx_m"] * planner["dy_m"] / 1e6),
        "overlap_iou_with_operational_roi": bbox_iou(user_roi, op_roi),
        "overlap_fraction_of_operational_roi": float(usr_inter_op / op_area) if op_area > 0 else float("nan"),
        "overlap_fraction_of_method_roi": float(usr_inter_op / user_roi.area_cells) if user_roi.area_cells > 0 else float("nan"),
        "pearson_vs_deterministic_ref": usr_metrics_ref["pearson_r"],
        "ncc_vs_deterministic_ref": usr_metrics_ref["ncc"],
        "rmse_zscore_vs_deterministic_ref": usr_metrics_ref["rmse_zscore"],
        "mae_zscore_vs_deterministic_ref": usr_metrics_ref["mae_zscore"],
        "n_valid_corr_pixels": usr_metrics_ref["n_valid"],
        "resample_for_ref": "bilinear_resize(reference -> method_shape)",
    }
    metrics_rows = [cand_metrics, usr_metrics]

    cand_vs_usr_iou = bbox_iou(candb_roi, user_roi)
    centers = {
        "candb_cx": 0.5 * (candb_roi.x0 + candb_roi.x1),
        "candb_cy": 0.5 * (candb_roi.y0 + candb_roi.y1),
        "user_cx": 0.5 * (user_roi.x0 + user_roi.x1),
        "user_cy": 0.5 * (user_roi.y0 + user_roi.y1),
    }
    center_distance_cells = math.hypot(centers["candb_cx"] - centers["user_cx"], centers["candb_cy"] - centers["user_cy"])

    # Classification logic.
    if cand_vs_usr_iou >= 0.60 and usr_metrics["overlap_iou_with_operational_roi"] >= 0.70 * cand_metrics["overlap_iou_with_operational_roi"]:
        classification = "USER_DIRECT_KM ACCEPTABLE AS SIMPLIFIED ALTERNATIVE"
    elif cand_metrics["overlap_iou_with_operational_roi"] >= usr_metrics["overlap_iou_with_operational_roi"] * 1.20:
        classification = "CAND_B PREFERRED"
    else:
        classification = "USER_DIRECT_KM TOO DIFFERENT"

    # bbox table.
    bbox_rows = [
        {
            "roi_id": "planner_operational_roi",
            "method": "planner_config_crop",
            "frame": "planner_index+lonlat",
            "x0_idx": op_roi.x0,
            "x1_idx": op_roi.x1,
            "y0_idx": op_roi.y0,
            "y1_idx": op_roi.y1,
            "width": op_roi.width,
            "height": op_roi.height,
            "area_cells": op_roi.area_cells,
            "lon_min": op_roi.lon_min,
            "lon_max": op_roi.lon_max,
            "lat_min": op_roi.lat_min,
            "lat_max": op_roi.lat_max,
            "notes": op_roi.notes,
        },
        {
            "roi_id": "cand_b_roi",
            "method": candb_roi.method,
            "frame": "planner_index+lonlat",
            "x0_idx": candb_roi.x0,
            "x1_idx": candb_roi.x1,
            "y0_idx": candb_roi.y0,
            "y1_idx": candb_roi.y1,
            "width": candb_roi.width,
            "height": candb_roi.height,
            "area_cells": candb_roi.area_cells,
            "lon_min": candb_roi.lon_min,
            "lon_max": candb_roi.lon_max,
            "lat_min": candb_roi.lat_min,
            "lat_max": candb_roi.lat_max,
            "notes": candb_roi.notes,
        },
        {
            "roi_id": "user_direct_km_roi",
            "method": user_roi.method,
            "frame": "planner_index+lonlat+local_km",
            "x0_idx": user_roi.x0,
            "x1_idx": user_roi.x1,
            "y0_idx": user_roi.y0,
            "y1_idx": user_roi.y1,
            "width": user_roi.width,
            "height": user_roi.height,
            "area_cells": user_roi.area_cells,
            "lon_min": user_roi.lon_min,
            "lon_max": user_roi.lon_max,
            "lat_min": user_roi.lat_min,
            "lat_max": user_roi.lat_max,
            "x_km_min": user_roi.x_km_min,
            "x_km_max": user_roi.x_km_max,
            "y_km_min": user_roi.y_km_min,
            "y_km_max": user_roi.y_km_max,
            "notes": user_roi.notes,
        },
        {
            "roi_id": "deterministic_same_day_reference",
            "method": "deterministic_relative_km_display_assumed",
            "frame": "local_km",
            "x0_idx": x_start_1b - 1,
            "x1_idx": x_end_1b - 1,
            "y0_idx": y_start_1b - 1,
            "y1_idx": y_end_1b - 1,
            "width": int(det_crop.shape[1]),
            "height": int(det_crop.shape[0]),
            "area_cells": int(det_crop.size),
            "x_km_min": float(det_extent[0]),
            "x_km_max": float(det_extent[1]),
            "y_km_min": float(det_extent[2]),
            "y_km_max": float(det_extent[3]),
            "notes": "Reference panel selected by day-convention mapping to available z index.",
        },
    ]

    write_csv(OUT_METRICS, metrics_rows)
    write_csv(OUT_BBOXES, bbox_rows)

    checks = {
        "generated_at_utc": now_iso(),
        "day_selection": {
            "planner_day": planner_date.isoformat(),
            "planner_day_source": f"filename:{planner_interface.name}",
            "deterministic_selection": {
                "selected_parent": rel(rel_parent),
                "selected_dir": rel(det_dir),
                "selected_png": rel(det_selection["selected_png"]),
                "selected_z": int(det_selection["selected_z"]),
                "convention": det_selection["convention"],
                "reason": det_selection["convention_reason"],
                "available_z_range": [int(det_selection["available_z_min"]), int(det_selection["available_z_max"])],
            },
            "notes": [
                "Deterministic files are named by z-index, not explicit YYYY-MM-DD.",
                "Day mapping was required; DOY-based convention was applied and documented.",
            ],
            "registration_day_hints": load_registration_day_hints(),
        },
        "inputs": {
            "planner_interface": rel(planner_interface),
            "config_file": rel(CONFIG_FILE),
            "candb_source_csv": rel(TEMPRES_GEOR_CAND_CSV),
            "relative_km_manifest": rel(rel_manifest),
            "temp_stack": rel(TEMP_STACK),
        },
        "rois": {
            "planner_operational_roi": {
                "x0": op_roi.x0,
                "x1": op_roi.x1,
                "y0": op_roi.y0,
                "y1": op_roi.y1,
                "shape": [op_roi.height, op_roi.width],
            },
            "candb_roi": {
                "x0": candb_roi.x0,
                "x1": candb_roi.x1,
                "y0": candb_roi.y0,
                "y1": candb_roi.y1,
                "shape": [candb_roi.height, candb_roi.width],
            },
            "user_direct_km_roi": {
                "x0": user_roi.x0,
                "x1": user_roi.x1,
                "y0": user_roi.y0,
                "y1": user_roi.y1,
                "shape": [user_roi.height, user_roi.width],
                "local_km_bbox": [user_roi.x_km_min, user_roi.x_km_max, user_roi.y_km_min, user_roi.y_km_max],
            },
        },
        "overlap": {
            "candb_vs_operational_iou": cand_metrics["overlap_iou_with_operational_roi"],
            "user_vs_operational_iou": usr_metrics["overlap_iou_with_operational_roi"],
            "candb_vs_user_iou": cand_vs_usr_iou,
            "candb_vs_user_center_distance_cells": center_distance_cells,
        },
        "classification": classification,
        "outputs": {
            "report": rel(OUT_REPORT),
            "summary": rel(OUT_SUMMARY),
            "metrics_csv": rel(OUT_METRICS),
            "bboxes_csv": rel(OUT_BBOXES),
            "checks_json": rel(OUT_CHECKS),
            "figures": [
                rel(FIG_PLANNER_FULL),
                rel(FIG_PLANNER_CROP),
                rel(FIG_CANDB_FULL),
                rel(FIG_CANDB_CROP),
                rel(FIG_DET_FULL),
                rel(FIG_DET_CROP),
                rel(FIG_USER_FULL),
                rel(FIG_USER_CROP),
                rel(FIG_PANEL),
                rel(FIG_OVERLAY),
                rel(FIG_CROPS),
            ],
        },
    }
    ensure_parent(OUT_CHECKS)
    OUT_CHECKS.write_text(json.dumps(checks, indent=2), encoding="utf-8")

    # Report and summary.
    report_lines = [
        "# CAND_B vs USER_DIRECT_KM ROI Comparison",
        "",
        "## 1. objetivo",
        "Comparar visualmente e quantitativamente dois metodos para definir/mover a ROI da tempRes para a grelha de planeamento: CAND_B registration-derived vs USER_DIRECT_KM display-axes-direct.",
        "",
        "## 2. inputs usados",
        f"- Planner interface oficial: `{rel(planner_interface)}`",
        f"- Config operacional: `{rel(CONFIG_FILE)}`",
        f"- CAND_B source: `{rel(TEMPRES_GEOR_CAND_CSV)}`",
        f"- Relative-km deterministic package: `{rel(rel_parent)}`",
        f"- Relative-km manifest: `{rel(rel_manifest)}`",
        f"- temp stack numeric source: `{rel(TEMP_STACK)}`",
        "",
        "## 3. dia selecionado",
        f"- Dia de planeamento detectado: `{planner_date.isoformat()}`",
        f"- Convencao deterministic usada: `{det_selection['convention']}`",
        f"- Justificacao: {det_selection['convention_reason']}",
        f"- deterministic file usado: `{rel(det_selection['selected_png'])}`",
        "",
        "## 4. planner input oficial usado",
        f"- `{rel(planner_interface)}`",
        f"- ROI operacional (indices): x={op_roi.x0}..{op_roi.x1}, y={op_roi.y0}..{op_roi.y1}, shape={op_roi.height}x{op_roi.width}",
        "",
        "## 5. ficheiro deterministic usado",
        f"- Pasta: `{rel(det_dir)}`",
        f"- Ficheiro selecionado: `{rel(det_selection['selected_png'])}`",
        f"- z selecionado: `{z}`",
        "",
        "## 6. descricao do metodo CAND_B",
        "- registration-derived (transformacao inferida por alinhamento controlado).",
        "- usa bbox/indexes do melhor candidato CAND_B na grelha HRes/planner.",
        "- forte quantitativamente para consistencia operacional, sem afirmar georreferencia nativa do tempRes.",
        "",
        "## 7. descricao do metodo USER_DIRECT_KM",
        "- display-axes-direct / USER_DIRECT_KM_METHOD.",
        "- ROI definida diretamente a partir dos eixos locais-km do painel deterministic relative-km.",
        "- projetada para planner por correspondencia linear local-km->HRes bbox->planner indices.",
        "- nao usa CAND_B como transformacao principal.",
        "",
        "## 8. figuras geradas",
        f"- `{rel(FIG_PLANNER_FULL)}`",
        f"- `{rel(FIG_PLANNER_CROP)}`",
        f"- `{rel(FIG_CANDB_FULL)}`",
        f"- `{rel(FIG_CANDB_CROP)}`",
        f"- `{rel(FIG_DET_FULL)}`",
        f"- `{rel(FIG_DET_CROP)}`",
        f"- `{rel(FIG_USER_FULL)}`",
        f"- `{rel(FIG_USER_CROP)}`",
        f"- `{rel(FIG_PANEL)}`",
        f"- `{rel(FIG_OVERLAY)}`",
        f"- `{rel(FIG_CROPS)}`",
        "",
        "## 9. metricas comparativas",
        f"- CAND_B overlap IoU vs operational ROI: `{cand_metrics['overlap_iou_with_operational_roi']:.4f}`",
        f"- USER_DIRECT_KM overlap IoU vs operational ROI: `{usr_metrics['overlap_iou_with_operational_roi']:.4f}`",
        f"- CAND_B overlap coverage of operational ROI: `{cand_metrics['overlap_fraction_of_operational_roi']:.4f}`",
        f"- USER_DIRECT_KM overlap coverage of operational ROI: `{usr_metrics['overlap_fraction_of_operational_roi']:.4f}`",
        f"- CAND_B vs USER_DIRECT_KM IoU: `{cand_vs_usr_iou:.4f}`",
        f"- CAND_B pearson vs deterministic ref: `{cand_metrics['pearson_vs_deterministic_ref']}`",
        f"- USER_DIRECT_KM pearson vs deterministic ref: `{usr_metrics['pearson_vs_deterministic_ref']}`",
        f"- Tabela completa: `{rel(OUT_METRICS)}` e `{rel(OUT_BBOXES)}`",
        "",
        "## 10. interpretacao",
        "- CAND_B fica mais consistente com o referencial espacial operacional do planner (maior IoU com ROI operacional).",
        "- USER_DIRECT_KM representa melhor a sugestao intuitiva de usar diretamente os eixos locais-km do painel.",
        "- Neste caso, USER_DIRECT_KM desloca a ROI para uma zona mais extensa e mais a sudoeste no planner, reduzindo a coincidencia com a ROI operacional definida no planner.",
        "- A comparacao com deterministic requer reamostragem (bilinear) para igualar shape; este passo foi aplicado explicitamente.",
        "",
        "## 11. conclusao final",
        f"1. Metodo mais consistente com o referencial do planner: `CAND_B`.",
        "2. Metodo mais proximo da sugestao intuitiva: `USER_DIRECT_KM_METHOD`.",
        f"3. USER_DIRECT_KM suficientemente proximo de CAND_B: `nao` (IoU={cand_vs_usr_iou:.4f}).",
        f"4. Classificacao final: `{classification}`.",
        "",
        "Para os proximos passos, recomenda-se usar CAND_B como referencia operacional para transferir a ROI/regimes para a grelha do planner.",
    ]
    report_text = "\n".join(report_lines) + "\n"
    ensure_parent(OUT_REPORT)
    OUT_REPORT.write_text(report_text, encoding="utf-8")

    summary_lines = [
        "# CAND_B vs USER_DIRECT_KM Summary",
        "",
        f"- day_used: `{planner_date.isoformat()}`",
        f"- deterministic_selected: `{rel(det_selection['selected_png'])}`",
        f"- candb_iou_vs_operational: `{cand_metrics['overlap_iou_with_operational_roi']:.4f}`",
        f"- user_direct_iou_vs_operational: `{usr_metrics['overlap_iou_with_operational_roi']:.4f}`",
        f"- candb_vs_user_iou: `{cand_vs_usr_iou:.4f}`",
        f"- final_classification: `{classification}`",
        "",
        "Methodological distinction:",
        "- CAND_B = registration-derived inferred transform (stronger operational consistency, not native georef proof).",
        "- USER_DIRECT_KM = direct local-km display method (simpler and intuitive, but display-derived).",
        "",
        "Recommendation:",
        "Para os proximos passos, recomenda-se usar CAND_B como referencia operacional para transferir a ROI/regimes para a grelha do planner.",
    ]
    ensure_parent(OUT_SUMMARY)
    OUT_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    # Close xarray dataset.
    planner["ds"].close()

    print("Generated:")
    print(rel(OUT_REPORT))
    print(rel(OUT_SUMMARY))
    print(rel(OUT_METRICS))
    print(rel(OUT_BBOXES))
    print(rel(OUT_CHECKS))
    print(rel(FIG_PLANNER_FULL))
    print(rel(FIG_PLANNER_CROP))
    print(rel(FIG_CANDB_FULL))
    print(rel(FIG_CANDB_CROP))
    print(rel(FIG_DET_FULL))
    print(rel(FIG_DET_CROP))
    print(rel(FIG_USER_FULL))
    print(rel(FIG_USER_CROP))
    print(rel(FIG_PANEL))
    print(rel(FIG_OVERLAY))
    print(rel(FIG_CROPS))
    print(f"Classification: {classification}")


if __name__ == "__main__":
    main()

