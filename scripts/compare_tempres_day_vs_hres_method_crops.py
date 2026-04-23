"""Correct and expand CAND_B vs USER_DIRECT_KM visual comparison.

This script is audit/visualization only.
It does not modify the planner scientific core.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

OUT_FULL_DAY_TEMPRES = RESULTS / "temperature_full_day_tempres.png"
OUT_CANDB_HRES = RESULTS / "candb_hres_crop.png"
OUT_USER_HRES = RESULTS / "userdirect_hres_crop.png"
OUT_CANDB_TEMP = RESULTS / "candb_temperature_crop.png"
OUT_USER_TEMP = RESULTS / "userdirect_temperature_crop.png"
OUT_CANDB_PLANNER = RESULTS / "candb_planner_crop.png"
OUT_USER_PLANNER = RESULTS / "userdirect_planner_crop.png"
OUT_PANEL_TEMP = RESULTS / "comparison_panel_temperature_methods.png"
OUT_PANEL_HRES = RESULTS / "comparison_panel_hres_methods.png"
OUT_PANEL_ALL = RESULTS / "comparison_panel_all.png"
OUT_METRICS = RESULTS / "method_crop_metrics.csv"
OUT_BBOXES = RESULTS / "method_crop_bboxes.csv"
OUT_CHECKS = RESULTS / "method_crop_checks.json"
OUT_REPORT = RESULTS / "corrected_method_crop_report.md"
OUT_SUMMARY = RESULTS / "corrected_method_crop_summary.md"

TEMP_STACK = ROOT / "results" / "plots" / "X_surface_300.npy"
CANDB_SOURCE_CSV = ROOT / "results" / "tempres_georef_candidate_transforms.csv"
PREV_SUMMARY = ROOT / "results" / "candb_vs_userdirect_summary.md"
PREV_CHECKS = ROOT / "results" / "candb_vs_userdirect_checks.json"
CONFIG_FILE = ROOT / "OptimalPlanning_Lucrezia" / "Config_file.py"

PREFERRED_TEMPRES_FULL_DIR = ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes"
PREFERRED_REL_MANIFEST = (
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1" / "manifest.json"
)
PREFERRED_PLANNER_IFACE = (
    ROOT
    / "results"
    / "planner_baseline_scenario_c4_methodical_20260418_162500"
    / "inputs"
    / "30-10-2024_surface_dayfix_planner_interface.nc"
)


@dataclass
class Roi:
    name: str
    x0: int
    x1: int
    y0: int
    y1: int
    domain: str
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


def parse_dd_mm_yyyy_token(name: str) -> Optional[date]:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", name)
    if m is None:
        return None
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(yyyy, mm, dd)


def detect_previous_comparison_day() -> Tuple[date, str]:
    if PREV_SUMMARY.exists():
        txt = PREV_SUMMARY.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"day_used:\s*`?(\d{4}-\d{2}-\d{2})`?", txt)
        if m is not None:
            y, mo, d = [int(v) for v in m.group(1).split("-")]
            return date(y, mo, d), f"summary:{rel(PREV_SUMMARY)}"
    if PREV_CHECKS.exists():
        payload = json.loads(PREV_CHECKS.read_text(encoding="utf-8"))
        day_txt = payload.get("day_selection", {}).get("planner_day")
        if isinstance(day_txt, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day_txt):
            y, mo, d = [int(v) for v in day_txt.split("-")]
            return date(y, mo, d), f"checks:{rel(PREV_CHECKS)}"
    return date(2024, 10, 30), "fallback:hardcoded_2024-10-30"


def find_tempres_full_dir() -> Path:
    if PREFERRED_TEMPRES_FULL_DIR.exists():
        files = list(PREFERRED_TEMPRES_FULL_DIR.glob("TEMP_surface_2024_z*.png"))
        if len(files) >= 300:
            return PREFERRED_TEMPRES_FULL_DIR
    best_dir: Optional[Path] = None
    best_count = -1
    for d in sorted((ROOT / "results" / "plots").glob("*")):
        if not d.is_dir():
            continue
        if "relative_km" in d.name.lower():
            continue
        count = len(list(d.glob("TEMP_surface_2024_z*.png")))
        if count > best_count:
            best_count = count
            best_dir = d
    if best_dir is None or best_count <= 0:
        raise FileNotFoundError("Could not find existing full-day tempRes PNG set.")
    return best_dir


def find_relative_manifest() -> Path:
    if PREFERRED_REL_MANIFEST.exists():
        return PREFERRED_REL_MANIFEST
    manifests = sorted((ROOT / "results" / "plots").glob("tempibhres_relative_km_display_assumed*/manifest.json"))
    if not manifests:
        raise FileNotFoundError("Could not find tempibhres_relative_km_display_assumed manifest.json")
    best: Optional[Path] = None
    best_score = -1.0
    for m in manifests:
        try:
            payload = json.loads(m.read_text(encoding="utf-8"))
            count = int(payload.get("counts", {}).get("deterministic_pngs", 0))
            crop = payload.get("crop", {})
            full = crop.get("full_shape_ny_nx", [0, 0])
            cropped = crop.get("cropped_shape_ny_nx", [0, 0])
            has_crop = (cropped[0] > 0 and cropped[1] > 0 and (cropped[0] < full[0] or cropped[1] < full[1]))
            score = count + (2000 if has_crop else 0)
            if "filipa_xy_km_cropped_v1" in str(m).lower():
                score += 5000
            if score > best_score:
                best_score = score
                best = m
        except Exception:
            continue
    if best is None:
        raise RuntimeError("Could not choose a valid relative-km manifest.")
    return best


def extract_available_z_values(tempres_dir: Path) -> List[int]:
    vals: List[int] = []
    for p in tempres_dir.glob("TEMP_surface_2024_z*.png"):
        m = re.search(r"_z(\d{3})\.png$", p.name)
        if m is not None:
            vals.append(int(m.group(1)))
    if not vals:
        raise RuntimeError(f"No z-indexed tempRes PNG files found in {tempres_dir}")
    return sorted(set(vals))


def select_z_for_day(target_day: date, available_z: List[int]) -> Dict[str, object]:
    proposed = int(target_day.timetuple().tm_yday)
    z_min, z_max = int(min(available_z)), int(max(available_z))
    selected = min(max(proposed, z_min), z_max)
    if selected not in available_z:
        selected = min(available_z, key=lambda z: abs(z - proposed))
    if selected == proposed:
        convention = "DOY_TO_Z_EXACT"
        reason = "day-of-year falls inside available z-range."
    elif proposed > z_max:
        convention = "DOY_TO_Z_CLIPPED_MAX"
        reason = f"day-of-year={proposed} exceeds z_max={z_max}; clipped to z={selected}."
    elif proposed < z_min:
        convention = "DOY_TO_Z_CLIPPED_MIN"
        reason = f"day-of-year={proposed} is below z_min={z_min}; clipped to z={selected}."
    else:
        convention = "DOY_TO_Z_NEAREST_AVAILABLE"
        reason = f"z={proposed} missing; nearest available z={selected} selected."
    return {
        "target_day": target_day.isoformat(),
        "target_day_doy": proposed,
        "available_z_min": z_min,
        "available_z_max": z_max,
        "selected_z": selected,
        "convention": convention,
        "reason": reason,
    }


def build_full_day_reference_from_existing_png(
    src_png: Path,
    out_png: Path,
    day_used: date,
    selected_z: int,
    convention: str,
) -> None:
    ensure_parent(out_png)
    try:
        im = Image.open(src_png).convert("RGBA")
        pad = 74
        canvas = Image.new("RGBA", (im.width, im.height + pad), (255, 255, 255, 255))
        canvas.paste(im, (0, pad))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        line1 = f"Temperature full-day reference from existing tempRes PNG set | day={day_used.isoformat()} | z={selected_z:03d}"
        line2 = f"Mapping convention: {convention} | source: {rel(src_png)}"
        draw.text((16, 12), line1, fill=(0, 0, 0, 255), font=font)
        draw.text((16, 36), line2, fill=(0, 0, 0, 255), font=font)
        canvas.save(out_png)
    except Exception:
        shutil.copy2(src_png, out_png)


def find_planner_interface_for_day(target_day: date) -> Path:
    if PREFERRED_PLANNER_IFACE.exists() and parse_dd_mm_yyyy_token(PREFERRED_PLANNER_IFACE.name) == target_day:
        return PREFERRED_PLANNER_IFACE
    candidates = sorted((ROOT / "results").rglob("*planner_interface.nc"))
    if not candidates:
        raise FileNotFoundError("No planner_interface.nc files found.")
    exact = [p for p in candidates if parse_dd_mm_yyyy_token(p.name) == target_day]
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
        if "30-10-2024" in path.name:
            score += 3
        return score, -len(s)

    return sorted(pool, key=rank, reverse=True)[0]


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


def load_planner_interface(path: Path) -> Dict[str, object]:
    ds = xr.open_dataset(path, decode_times=False)
    lat = ds["lat"].values.astype(np.float64, copy=False)
    lon = ds["lon"].values.astype(np.float64, copy=False)
    arr = ds["temperr"].values.astype(np.float64, copy=False)
    if "landt" in ds:
        land = ds["landt"].values
        arr = arr.copy()
        arr[land != 1] = np.nan
    lat_mid = 0.5 * float(np.nanmin(lat) + np.nanmax(lat))
    km_deg_lat, km_deg_lon = km_per_degree(lat_mid)
    dlat = float(np.mean(np.diff(lat)))
    dlon = float(np.mean(np.diff(lon)))
    return {
        "ds": ds,
        "lat": lat,
        "lon": lon,
        "arr": arr,
        "dx_m": abs(dlon) * km_deg_lon * 1000.0,
        "dy_m": abs(dlat) * km_deg_lat * 1000.0,
    }


def clip_idx(v: int, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, v)))


def load_candb_planner_roi(lon_axis: np.ndarray, lat_axis: np.ndarray) -> Roi:
    if not CANDB_SOURCE_CSV.exists():
        raise FileNotFoundError(CANDB_SOURCE_CSV)
    with CANDB_SOURCE_CSV.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found in tempres_georef_candidate_transforms.csv")

    if row.get("x0_hres_idx") and row.get("x1_hres_idx") and row.get("y0_hres_idx") and row.get("y1_hres_idx"):
        x0 = int(row["x0_hres_idx"])
        x1 = int(row["x1_hres_idx"])
        y0 = int(row["y0_hres_idx"])
        y1 = int(row["y1_hres_idx"])
    else:
        lon_min = float(row["x0"])
        lon_max = float(row["x1"])
        lat_min = float(row["y0"])
        lat_max = float(row["y1"])
        x0 = int(np.searchsorted(lon_axis, lon_min, side="left"))
        x1 = int(np.searchsorted(lon_axis, lon_max, side="right")) - 1
        y0 = int(np.searchsorted(lat_axis, lat_min, side="left"))
        y1 = int(np.searchsorted(lat_axis, lat_max, side="right")) - 1

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
        domain="planner_compatible_hres",
        method="CAND_B_REGISTRATION_TO_HRES_SUBAREA",
        notes="Registration-derived ROI from controlled alignment.",
    )
    roi.lon_min = float(lon_axis[roi.x0])
    roi.lon_max = float(lon_axis[roi.x1])
    roi.lat_min = float(lat_axis[roi.y0])
    roi.lat_max = float(lat_axis[roi.y1])
    return roi


def load_user_direct_planner_roi(
    manifest: Dict[str, object],
    lon_axis: np.ndarray,
    lat_axis: np.ndarray,
) -> Tuple[Roi, Dict[str, object]]:
    crop = manifest["crop"]
    full_ny = int(crop["full_shape_ny_nx"][0])
    full_nx = int(crop["full_shape_ny_nx"][1])
    x_start_1b = int(crop["x_start_col_1based"])
    x_end_1b = int(crop["x_end_col_1based"])
    y_start_1b = int(crop["y_start_row_1based"])
    y_end_1b = int(crop["y_end_row_1based"])
    bbox = manifest["hres_bbox_source"]

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
        domain="planner_compatible_hres",
        method="USER_DIRECT_KM_METHOD",
        notes="Direct local-km ROI mapped to planner-compatible grid via manifest HRes bbox.",
    )
    roi.lon_min = float(lon_axis[roi.x0])
    roi.lon_max = float(lon_axis[roi.x1])
    roi.lat_min = float(lat_axis[roi.y0])
    roi.lat_max = float(lat_axis[roi.y1])

    extra = {
        "full_nx": full_nx,
        "full_ny": full_ny,
        "x_start_1b": x_start_1b,
        "x_end_1b": x_end_1b,
        "y_start_1b": y_start_1b,
        "y_end_1b": y_end_1b,
        "bbox_lon_min": float(bbox["lon_min"]),
        "bbox_lon_max": float(bbox["lon_max"]),
        "bbox_lat_min": float(bbox["lat_min"]),
        "bbox_lat_max": float(bbox["lat_max"]),
    }
    return roi, extra


def map_lonlat_roi_to_tempres(
    roi: Roi,
    temp_nx: int,
    temp_ny: int,
    full_lon_min: float,
    full_lon_max: float,
    full_lat_min: float,
    full_lat_max: float,
    notes: str,
) -> Roi:
    def norm(v: float, lo: float, hi: float) -> float:
        if hi == lo:
            return 0.0
        return (v - lo) / (hi - lo)

    u0 = norm(float(min(roi.lon_min, roi.lon_max)), full_lon_min, full_lon_max)
    u1 = norm(float(max(roi.lon_min, roi.lon_max)), full_lon_min, full_lon_max)
    v0 = norm(float(min(roi.lat_min, roi.lat_max)), full_lat_min, full_lat_max)
    v1 = norm(float(max(roi.lat_min, roi.lat_max)), full_lat_min, full_lat_max)

    x0 = int(math.floor(u0 * (temp_nx - 1)))
    x1 = int(math.ceil(u1 * (temp_nx - 1)))
    y0 = int(math.floor(v0 * (temp_ny - 1)))
    y1 = int(math.ceil(v1 * (temp_ny - 1)))
    x0 = clip_idx(x0, 0, temp_nx - 1)
    x1 = clip_idx(max(x1, x0), 0, temp_nx - 1)
    y0 = clip_idx(y0, 0, temp_ny - 1)
    y1 = clip_idx(max(y1, y0), 0, temp_ny - 1)

    out = Roi(
        name=roi.name,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        domain="tempres_indexed_grid",
        method=roi.method,
        notes=notes,
    )
    lon_axis = np.linspace(full_lon_min, full_lon_max, temp_nx)
    lat_axis = np.linspace(full_lat_min, full_lat_max, temp_ny)
    out.lon_min = float(lon_axis[out.x0])
    out.lon_max = float(lon_axis[out.x1])
    out.lat_min = float(lat_axis[out.y0])
    out.lat_max = float(lat_axis[out.y1])
    return out


def crop2d(arr: np.ndarray, roi: Roi) -> np.ndarray:
    return np.asarray(arr[roi.y0 : roi.y1 + 1, roi.x0 : roi.x1 + 1], dtype=np.float64)


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
    union = a.area + b.area - inter
    return float(inter / union) if union > 0 else 0.0


def roi_center_distance(a: Roi, b: Roi) -> float:
    ax = 0.5 * (a.x0 + a.x1)
    ay = 0.5 * (a.y0 + a.y1)
    bx = 0.5 * (b.x0 + b.x1)
    by = 0.5 * (b.y0 + b.y1)
    return float(math.hypot(ax - bx, ay - by))


def array_stats(arr: np.ndarray) -> Dict[str, float]:
    a = np.asarray(arr, dtype=np.float64)
    m = np.isfinite(a)
    if int(m.sum()) == 0:
        return {"n_valid": 0, "mean": float("nan"), "std": float("nan"), "min": float("nan"), "max": float("nan")}
    v = a[m]
    return {
        "n_valid": int(v.size),
        "mean": float(np.mean(v)),
        "std": float(np.std(v)),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
    }


def load_temp_scale(tempres_dir: Path, fallback_field: np.ndarray) -> Tuple[float, float, str]:
    scale_path = tempres_dir / "color_scale.json"
    if scale_path.exists():
        payload = json.loads(scale_path.read_text(encoding="utf-8"))
        return float(payload["vmin"]), float(payload["vmax"]), rel(scale_path)
    vmin = float(np.nanpercentile(fallback_field, 2.0))
    vmax = float(np.nanpercentile(fallback_field, 98.0))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin, vmax = float(np.nanmin(fallback_field)), float(np.nanmax(fallback_field))
    return vmin, vmax, "computed:p2_p98_of_selected_tempres_day"


def plot_crop(
    arr: np.ndarray,
    out_png: Path,
    title: str,
    x_label: str,
    y_label: str,
    cbar_label: str,
    cmap_name: str,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(alpha=0.2)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_temperature_panel(
    reference_png: Path,
    day_used: date,
    selected_z: int,
    cand_temp_crop: np.ndarray,
    user_temp_crop: np.ndarray,
    vmin: float,
    vmax: float,
    out_png: Path,
) -> None:
    ensure_parent(out_png)
    img = plt.imread(reference_png)
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.1))
    axes[0].imshow(img)
    axes[0].set_title(f"TempRes full day (existing PNG)\n{day_used.isoformat()} | z={selected_z:03d}")
    axes[0].axis("off")

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    im1 = axes[1].imshow(
        cand_temp_crop,
        origin="lower",
        cmap=cmap,
        aspect="auto",
        interpolation="nearest",
        vmin=vmin,
        vmax=vmax,
    )
    axes[1].set_title(f"CAND_B temperature crop\nshape={cand_temp_crop.shape[0]}x{cand_temp_crop.shape[1]}")
    axes[1].set_xlabel("X index (tempRes)")
    axes[1].set_ylabel("Y index (tempRes)")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    im2 = axes[2].imshow(
        user_temp_crop,
        origin="lower",
        cmap=cmap,
        aspect="auto",
        interpolation="nearest",
        vmin=vmin,
        vmax=vmax,
    )
    axes[2].set_title(f"USER_DIRECT_KM temperature crop\nshape={user_temp_crop.shape[0]}x{user_temp_crop.shape[1]}")
    axes[2].set_xlabel("X index (tempRes)")
    axes[2].set_ylabel("Y index (tempRes)")
    axes[2].grid(alpha=0.2)
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def plot_hres_panel(cand_crop: np.ndarray, user_crop: np.ndarray, out_png: Path) -> Tuple[float, float]:
    ensure_parent(out_png)
    stack = np.concatenate([cand_crop[np.isfinite(cand_crop)], user_crop[np.isfinite(user_crop)]])
    if stack.size > 0:
        vmin = float(np.percentile(stack, 2.0))
        vmax = float(np.percentile(stack, 98.0))
    else:
        vmin, vmax = float("nan"), float("nan")

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")
    im1 = axes[0].imshow(cand_crop, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[0].set_title(f"CAND_B planner-compatible HRes crop\nshape={cand_crop.shape[0]}x{cand_crop.shape[1]}")
    axes[0].set_xlabel("Planner lon index")
    axes[0].set_ylabel("Planner lat index")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)

    im2 = axes[1].imshow(user_crop, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
    axes[1].set_title(f"USER_DIRECT_KM planner-compatible HRes crop\nshape={user_crop.shape[0]}x{user_crop.shape[1]}")
    axes[1].set_xlabel("Planner lon index")
    axes[1].set_ylabel("Planner lat index")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)
    return vmin, vmax


def plot_all_panel(
    reference_png: Path,
    day_used: date,
    selected_z: int,
    cand_temp_crop: np.ndarray,
    user_temp_crop: np.ndarray,
    cand_planner_crop: np.ndarray,
    user_planner_crop: np.ndarray,
    planner_full: np.ndarray,
    cand_planner_roi: Roi,
    user_planner_roi: Roi,
    temp_vmin: float,
    temp_vmax: float,
    planner_vmin: float,
    planner_vmax: float,
    out_png: Path,
) -> None:
    ensure_parent(out_png)
    img = plt.imread(reference_png)
    fig, axes = plt.subplots(2, 3, figsize=(17.2, 9.8))

    axes[0, 0].imshow(img)
    axes[0, 0].set_title(f"1) TempRes full day (existing PNG)\n{day_used.isoformat()} | z={selected_z:03d}")
    axes[0, 0].axis("off")

    cmap_t = plt.get_cmap("viridis").copy()
    cmap_t.set_bad(color="white")
    im_t1 = axes[0, 1].imshow(
        cand_temp_crop,
        origin="lower",
        cmap=cmap_t,
        aspect="auto",
        interpolation="nearest",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    axes[0, 1].set_title(f"2) CAND_B temperature crop\nshape={cand_temp_crop.shape[0]}x{cand_temp_crop.shape[1]}")
    axes[0, 1].set_xlabel("X index")
    axes[0, 1].set_ylabel("Y index")
    axes[0, 1].grid(alpha=0.2)
    fig.colorbar(im_t1, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im_t2 = axes[0, 2].imshow(
        user_temp_crop,
        origin="lower",
        cmap=cmap_t,
        aspect="auto",
        interpolation="nearest",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    axes[0, 2].set_title(f"3) USER_DIRECT_KM temperature crop\nshape={user_temp_crop.shape[0]}x{user_temp_crop.shape[1]}")
    axes[0, 2].set_xlabel("X index")
    axes[0, 2].set_ylabel("Y index")
    axes[0, 2].grid(alpha=0.2)
    fig.colorbar(im_t2, ax=axes[0, 2], fraction=0.046, pad=0.04)

    cmap_p = plt.get_cmap("viridis").copy()
    cmap_p.set_bad(color="white")
    im_p1 = axes[1, 0].imshow(
        cand_planner_crop,
        origin="lower",
        cmap=cmap_p,
        aspect="auto",
        interpolation="nearest",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    axes[1, 0].set_title(f"4) CAND_B planner crop\nshape={cand_planner_crop.shape[0]}x{cand_planner_crop.shape[1]}")
    axes[1, 0].set_xlabel("Planner lon idx")
    axes[1, 0].set_ylabel("Planner lat idx")
    axes[1, 0].grid(alpha=0.2)
    fig.colorbar(im_p1, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im_p2 = axes[1, 1].imshow(
        user_planner_crop,
        origin="lower",
        cmap=cmap_p,
        aspect="auto",
        interpolation="nearest",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    axes[1, 1].set_title(f"5) USER_DIRECT_KM planner crop\nshape={user_planner_crop.shape[0]}x{user_planner_crop.shape[1]}")
    axes[1, 1].set_xlabel("Planner lon idx")
    axes[1, 1].set_ylabel("Planner lat idx")
    axes[1, 1].grid(alpha=0.2)
    fig.colorbar(im_p2, ax=axes[1, 1], fraction=0.046, pad=0.04)

    im_ov = axes[1, 2].imshow(
        planner_full,
        origin="lower",
        cmap=cmap_p,
        aspect="auto",
        interpolation="nearest",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    rect_c = plt.Rectangle(
        (cand_planner_roi.x0 - 0.5, cand_planner_roi.y0 - 0.5),
        cand_planner_roi.width,
        cand_planner_roi.height,
        fill=False,
        linewidth=2.0,
        edgecolor="#e74c3c",
        label="CAND_B",
    )
    rect_u = plt.Rectangle(
        (user_planner_roi.x0 - 0.5, user_planner_roi.y0 - 0.5),
        user_planner_roi.width,
        user_planner_roi.height,
        fill=False,
        linewidth=2.0,
        edgecolor="#1f77b4",
        label="USER_DIRECT_KM",
    )
    axes[1, 2].add_patch(rect_c)
    axes[1, 2].add_patch(rect_u)
    axes[1, 2].set_title("6) Overlay on planner-compatible grid")
    axes[1, 2].set_xlabel("Planner lon idx")
    axes[1, 2].set_ylabel("Planner lat idx")
    axes[1, 2].legend(loc="upper right", fontsize=8)
    axes[1, 2].grid(alpha=0.2)
    fig.colorbar(im_ov, ax=axes[1, 2], fraction=0.046, pad=0.04)

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
    day_used, day_source = detect_previous_comparison_day()

    tempres_full_dir = find_tempres_full_dir()
    z_values = extract_available_z_values(tempres_full_dir)
    z_sel = select_z_for_day(day_used, z_values)
    z = int(z_sel["selected_z"])
    tempres_full_png_src = tempres_full_dir / f"TEMP_surface_2024_z{z:03d}.png"
    if not tempres_full_png_src.exists():
        raise FileNotFoundError(tempres_full_png_src)
    build_full_day_reference_from_existing_png(
        src_png=tempres_full_png_src,
        out_png=OUT_FULL_DAY_TEMPRES,
        day_used=day_used,
        selected_z=z,
        convention=str(z_sel["convention"]),
    )

    if not TEMP_STACK.exists():
        raise FileNotFoundError(TEMP_STACK)
    temp_stack = np.load(TEMP_STACK).astype(np.float64, copy=False)
    if z < 1 or z > temp_stack.shape[0]:
        raise RuntimeError(f"Selected z={z} out of TEMP stack range 1..{temp_stack.shape[0]}")
    temp_day = temp_stack[z - 1]
    temp_ny, temp_nx = int(temp_day.shape[0]), int(temp_day.shape[1])
    temp_vmin, temp_vmax, temp_scale_source = load_temp_scale(tempres_full_dir, temp_day)

    planner_path = find_planner_interface_for_day(day_used)
    planner = load_planner_interface(planner_path)
    planner_arr = planner["arr"]
    lat = planner["lat"]
    lon = planner["lon"]

    candb_planner_roi = load_candb_planner_roi(lon_axis=lon, lat_axis=lat)
    rel_manifest_path = find_relative_manifest()
    rel_manifest = json.loads(rel_manifest_path.read_text(encoding="utf-8"))
    user_planner_roi, user_extra = load_user_direct_planner_roi(manifest=rel_manifest, lon_axis=lon, lat_axis=lat)

    full_lon_min = float(np.min(lon))
    full_lon_max = float(np.max(lon))
    full_lat_min = float(np.min(lat))
    full_lat_max = float(np.max(lat))
    mapping_note = (
        "Linear lon/lat normalization from planner-compatible full bbox "
        "to tempRes indexed grid (112x64 equivalent), preserving bbox corner order."
    )
    candb_temp_roi = map_lonlat_roi_to_tempres(
        roi=candb_planner_roi,
        temp_nx=temp_nx,
        temp_ny=temp_ny,
        full_lon_min=full_lon_min,
        full_lon_max=full_lon_max,
        full_lat_min=full_lat_min,
        full_lat_max=full_lat_max,
        notes=mapping_note,
    )
    user_temp_roi = map_lonlat_roi_to_tempres(
        roi=user_planner_roi,
        temp_nx=temp_nx,
        temp_ny=temp_ny,
        full_lon_min=full_lon_min,
        full_lon_max=full_lon_max,
        full_lat_min=full_lat_min,
        full_lat_max=full_lat_max,
        notes=mapping_note,
    )

    candb_temp_crop = crop2d(temp_day, candb_temp_roi)
    user_temp_crop = crop2d(temp_day, user_temp_roi)
    candb_planner_crop = crop2d(planner_arr, candb_planner_roi)
    user_planner_crop = crop2d(planner_arr, user_planner_roi)

    planner_valid = planner_arr[np.isfinite(planner_arr)]
    if planner_valid.size > 0:
        planner_vmin = float(np.percentile(planner_valid, 2.0))
        planner_vmax = float(np.percentile(planner_valid, 98.0))
    else:
        planner_vmin = float("nan")
        planner_vmax = float("nan")

    plot_crop(
        candb_planner_crop,
        OUT_CANDB_HRES,
        f"CAND_B crop on planner-compatible HRes domain\nshape={candb_planner_crop.shape[0]}x{candb_planner_crop.shape[1]}",
        x_label="Planner lon index",
        y_label="Planner lat index",
        cbar_label="temperr",
        cmap_name="viridis",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    plot_crop(
        user_planner_crop,
        OUT_USER_HRES,
        f"USER_DIRECT_KM crop on planner-compatible HRes domain\nshape={user_planner_crop.shape[0]}x{user_planner_crop.shape[1]}",
        x_label="Planner lon index",
        y_label="Planner lat index",
        cbar_label="temperr",
        cmap_name="viridis",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    plot_crop(
        candb_temp_crop,
        OUT_CANDB_TEMP,
        f"CAND_B temperature crop (same day)\nshape={candb_temp_crop.shape[0]}x{candb_temp_crop.shape[1]}",
        x_label="X index (tempRes)",
        y_label="Y index (tempRes)",
        cbar_label="Temperature (degC)",
        cmap_name="viridis",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    plot_crop(
        user_temp_crop,
        OUT_USER_TEMP,
        f"USER_DIRECT_KM temperature crop (same day)\nshape={user_temp_crop.shape[0]}x{user_temp_crop.shape[1]}",
        x_label="X index (tempRes)",
        y_label="Y index (tempRes)",
        cbar_label="Temperature (degC)",
        cmap_name="viridis",
        vmin=temp_vmin,
        vmax=temp_vmax,
    )
    plot_crop(
        candb_planner_crop,
        OUT_CANDB_PLANNER,
        f"CAND_B planner crop\nshape={candb_planner_crop.shape[0]}x{candb_planner_crop.shape[1]}",
        x_label="Planner lon index",
        y_label="Planner lat index",
        cbar_label="temperr",
        cmap_name="viridis",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )
    plot_crop(
        user_planner_crop,
        OUT_USER_PLANNER,
        f"USER_DIRECT_KM planner crop\nshape={user_planner_crop.shape[0]}x{user_planner_crop.shape[1]}",
        x_label="Planner lon index",
        y_label="Planner lat index",
        cbar_label="temperr",
        cmap_name="viridis",
        vmin=planner_vmin,
        vmax=planner_vmax,
    )

    plot_temperature_panel(
        reference_png=OUT_FULL_DAY_TEMPRES,
        day_used=day_used,
        selected_z=z,
        cand_temp_crop=candb_temp_crop,
        user_temp_crop=user_temp_crop,
        vmin=temp_vmin,
        vmax=temp_vmax,
        out_png=OUT_PANEL_TEMP,
    )
    panel_hres_vmin, panel_hres_vmax = plot_hres_panel(candb_planner_crop, user_planner_crop, OUT_PANEL_HRES)
    plot_all_panel(
        reference_png=OUT_FULL_DAY_TEMPRES,
        day_used=day_used,
        selected_z=z,
        cand_temp_crop=candb_temp_crop,
        user_temp_crop=user_temp_crop,
        cand_planner_crop=candb_planner_crop,
        user_planner_crop=user_planner_crop,
        planner_full=planner_arr,
        cand_planner_roi=candb_planner_roi,
        user_planner_roi=user_planner_roi,
        temp_vmin=temp_vmin,
        temp_vmax=temp_vmax,
        planner_vmin=panel_hres_vmin,
        planner_vmax=panel_hres_vmax,
        out_png=OUT_PANEL_ALL,
    )

    cand_temp_stats = array_stats(candb_temp_crop)
    user_temp_stats = array_stats(user_temp_crop)
    cand_plan_stats = array_stats(candb_planner_crop)
    user_plan_stats = array_stats(user_planner_crop)
    iou_planner = bbox_iou(candb_planner_roi, user_planner_roi)
    iou_temp = bbox_iou(candb_temp_roi, user_temp_roi)
    center_dist_planner = roi_center_distance(candb_planner_roi, user_planner_roi)
    center_dist_temp = roi_center_distance(candb_temp_roi, user_temp_roi)

    metrics_rows = [
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "method": "CAND_B",
            "domain": "tempres",
            "shape_ny_nx": f"{candb_temp_roi.height}x{candb_temp_roi.width}",
            "area_cells": candb_temp_roi.area,
            "mean": cand_temp_stats["mean"],
            "std": cand_temp_stats["std"],
            "min": cand_temp_stats["min"],
            "max": cand_temp_stats["max"],
            "n_valid": cand_temp_stats["n_valid"],
            "vmin_visual": temp_vmin,
            "vmax_visual": temp_vmax,
            "transformation": mapping_note,
            "orientation": "origin=lower",
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "method": "USER_DIRECT_KM",
            "domain": "tempres",
            "shape_ny_nx": f"{user_temp_roi.height}x{user_temp_roi.width}",
            "area_cells": user_temp_roi.area,
            "mean": user_temp_stats["mean"],
            "std": user_temp_stats["std"],
            "min": user_temp_stats["min"],
            "max": user_temp_stats["max"],
            "n_valid": user_temp_stats["n_valid"],
            "vmin_visual": temp_vmin,
            "vmax_visual": temp_vmax,
            "transformation": mapping_note,
            "orientation": "origin=lower",
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "method": "CAND_B",
            "domain": "planner_compatible_hres",
            "shape_ny_nx": f"{candb_planner_roi.height}x{candb_planner_roi.width}",
            "area_cells": candb_planner_roi.area,
            "mean": cand_plan_stats["mean"],
            "std": cand_plan_stats["std"],
            "min": cand_plan_stats["min"],
            "max": cand_plan_stats["max"],
            "n_valid": cand_plan_stats["n_valid"],
            "vmin_visual": panel_hres_vmin,
            "vmax_visual": panel_hres_vmax,
            "transformation": "native planner-compatible grid crop",
            "orientation": "origin=lower",
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "method": "USER_DIRECT_KM",
            "domain": "planner_compatible_hres",
            "shape_ny_nx": f"{user_planner_roi.height}x{user_planner_roi.width}",
            "area_cells": user_planner_roi.area,
            "mean": user_plan_stats["mean"],
            "std": user_plan_stats["std"],
            "min": user_plan_stats["min"],
            "max": user_plan_stats["max"],
            "n_valid": user_plan_stats["n_valid"],
            "vmin_visual": panel_hres_vmin,
            "vmax_visual": panel_hres_vmax,
            "transformation": "native planner-compatible grid crop",
            "orientation": "origin=lower",
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "method": "CAND_B_vs_USER_DIRECT_KM",
            "domain": "comparison",
            "planner_bbox_iou": iou_planner,
            "tempres_bbox_iou": iou_temp,
            "planner_center_distance_cells": center_dist_planner,
            "tempres_center_distance_cells": center_dist_temp,
            "notes": "Higher IoU indicates more similar spatial focus between methods.",
        },
    ]

    bbox_rows = [
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "roi_id": "candb_planner",
            "method": "CAND_B",
            "domain": candb_planner_roi.domain,
            "x0": candb_planner_roi.x0,
            "x1": candb_planner_roi.x1,
            "y0": candb_planner_roi.y0,
            "y1": candb_planner_roi.y1,
            "width": candb_planner_roi.width,
            "height": candb_planner_roi.height,
            "area_cells": candb_planner_roi.area,
            "lon_min": candb_planner_roi.lon_min,
            "lon_max": candb_planner_roi.lon_max,
            "lat_min": candb_planner_roi.lat_min,
            "lat_max": candb_planner_roi.lat_max,
            "transformation_or_source": "direct from CAND_B registration row + planner interface axes",
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "roi_id": "userdirect_planner",
            "method": "USER_DIRECT_KM",
            "domain": user_planner_roi.domain,
            "x0": user_planner_roi.x0,
            "x1": user_planner_roi.x1,
            "y0": user_planner_roi.y0,
            "y1": user_planner_roi.y1,
            "width": user_planner_roi.width,
            "height": user_planner_roi.height,
            "area_cells": user_planner_roi.area,
            "lon_min": user_planner_roi.lon_min,
            "lon_max": user_planner_roi.lon_max,
            "lat_min": user_planner_roi.lat_min,
            "lat_max": user_planner_roi.lat_max,
            "transformation_or_source": f"direct from relative-km manifest mapped to planner axes ({rel(rel_manifest_path)})",
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "roi_id": "candb_tempres",
            "method": "CAND_B",
            "domain": candb_temp_roi.domain,
            "x0": candb_temp_roi.x0,
            "x1": candb_temp_roi.x1,
            "y0": candb_temp_roi.y0,
            "y1": candb_temp_roi.y1,
            "width": candb_temp_roi.width,
            "height": candb_temp_roi.height,
            "area_cells": candb_temp_roi.area,
            "lon_min": candb_temp_roi.lon_min,
            "lon_max": candb_temp_roi.lon_max,
            "lat_min": candb_temp_roi.lat_min,
            "lat_max": candb_temp_roi.lat_max,
            "transformation_or_source": mapping_note,
        },
        {
            "day_used": day_used.isoformat(),
            "tempres_reference_png": rel(tempres_full_png_src),
            "roi_id": "userdirect_tempres",
            "method": "USER_DIRECT_KM",
            "domain": user_temp_roi.domain,
            "x0": user_temp_roi.x0,
            "x1": user_temp_roi.x1,
            "y0": user_temp_roi.y0,
            "y1": user_temp_roi.y1,
            "width": user_temp_roi.width,
            "height": user_temp_roi.height,
            "area_cells": user_temp_roi.area,
            "lon_min": user_temp_roi.lon_min,
            "lon_max": user_temp_roi.lon_max,
            "lat_min": user_temp_roi.lat_min,
            "lat_max": user_temp_roi.lat_max,
            "transformation_or_source": mapping_note,
        },
    ]

    write_csv(OUT_METRICS, metrics_rows)
    write_csv(OUT_BBOXES, bbox_rows)

    outputs = [
        OUT_FULL_DAY_TEMPRES,
        OUT_CANDB_HRES,
        OUT_USER_HRES,
        OUT_CANDB_TEMP,
        OUT_USER_TEMP,
        OUT_CANDB_PLANNER,
        OUT_USER_PLANNER,
        OUT_PANEL_TEMP,
        OUT_PANEL_HRES,
        OUT_PANEL_ALL,
        OUT_METRICS,
        OUT_BBOXES,
        OUT_CHECKS,
        OUT_REPORT,
        OUT_SUMMARY,
    ]

    checks = {
        "generated_at_utc": now_iso(),
        "day_used": day_used.isoformat(),
        "day_source": day_source,
        "full_day_tempres_reference": {
            "source_existing_png_set": rel(tempres_full_dir),
            "source_png": rel(tempres_full_png_src),
            "output_png": rel(OUT_FULL_DAY_TEMPRES),
            "selected_z": z,
            "mapping_convention": z_sel["convention"],
            "mapping_reason": z_sel["reason"],
            "used_existing_png_without_regenerating_field": True,
        },
        "domains": {
            "method_crop_domain_selected": "planner_compatible_hres",
            "domain_selection_justification": (
                "Planner-compatible HRes grid was chosen for method crops because it is operationally consistent "
                "with planner inputs and preserves direct link to planning descriptors/regimes."
            ),
            "temperature_domain": "tempres_indexed_grid",
            "cross_domain_mapping": mapping_note,
        },
        "inputs": {
            "temp_stack": rel(TEMP_STACK),
            "candb_source_csv": rel(CANDB_SOURCE_CSV),
            "relative_km_manifest": rel(rel_manifest_path),
            "planner_interface": rel(planner_path),
            "config_file": rel(CONFIG_FILE),
            "temp_scale_source": temp_scale_source,
        },
        "rois": {
            "candb_planner": {
                "x0": candb_planner_roi.x0,
                "x1": candb_planner_roi.x1,
                "y0": candb_planner_roi.y0,
                "y1": candb_planner_roi.y1,
                "shape": [candb_planner_roi.height, candb_planner_roi.width],
            },
            "userdirect_planner": {
                "x0": user_planner_roi.x0,
                "x1": user_planner_roi.x1,
                "y0": user_planner_roi.y0,
                "y1": user_planner_roi.y1,
                "shape": [user_planner_roi.height, user_planner_roi.width],
                "relative_manifest_crop_1based": {
                    "x_start": user_extra["x_start_1b"],
                    "x_end": user_extra["x_end_1b"],
                    "y_start": user_extra["y_start_1b"],
                    "y_end": user_extra["y_end_1b"],
                },
            },
            "candb_tempres": {
                "x0": candb_temp_roi.x0,
                "x1": candb_temp_roi.x1,
                "y0": candb_temp_roi.y0,
                "y1": candb_temp_roi.y1,
                "shape": [candb_temp_roi.height, candb_temp_roi.width],
            },
            "userdirect_tempres": {
                "x0": user_temp_roi.x0,
                "x1": user_temp_roi.x1,
                "y0": user_temp_roi.y0,
                "y1": user_temp_roi.y1,
                "shape": [user_temp_roi.height, user_temp_roi.width],
            },
        },
        "bbox_comparison": {
            "planner_iou_candb_vs_userdirect": iou_planner,
            "tempres_iou_candb_vs_userdirect": iou_temp,
            "planner_center_distance_cells": center_dist_planner,
            "tempres_center_distance_cells": center_dist_temp,
        },
        "visual_standardization": {
            "temperature_colormap": "viridis",
            "temperature_vmin": temp_vmin,
            "temperature_vmax": temp_vmax,
            "planner_colormap": "viridis",
            "orientation": "origin=lower for array-rendered crops and panels",
        },
        "outputs": [rel(p) for p in outputs],
        "output_exists_check": {rel(p): bool(p.exists()) for p in outputs},
    }
    ensure_parent(OUT_CHECKS)
    OUT_CHECKS.write_text(json.dumps(checks, indent=2), encoding="utf-8")

    report_lines = [
        "# Corrected Method Crop Report",
        "",
        "## Objective",
        "This report corrects and expands the previous visual comparison between `CAND_B` and `USER_DIRECT_KM` without changing planner scientific logic.",
        "",
        "## Day And Reference",
        f"- Day used (same as previous comparison): `{day_used.isoformat()}` (source: `{day_source}`)",
        f"- Existing tempRes PNG set used as primary full-day reference: `{rel(tempres_full_dir)}`",
        f"- Selected reference image: `{rel(tempres_full_png_src)}`",
        f"- Day-to-z mapping convention: `{z_sel['convention']}` (`{z_sel['reason']}`)",
        f"- Output full-day image: `{rel(OUT_FULL_DAY_TEMPRES)}`",
        "",
        "## Domain Choice For Method Crops",
        "- Method crops were generated in the **planner-compatible HRes domain** (planner interface grid).",
        "- This is methodologically the most consistent operational option for linking regimes/descriptors to planning inputs.",
        "- Temperature crops were generated on the tempRes indexed grid for the same day and mapped using documented linear lon/lat normalization.",
        "",
        "## Generated Visual Outputs",
        f"- `{rel(OUT_FULL_DAY_TEMPRES)}` (full tempRes day reference from existing PNG set)",
        f"- `{rel(OUT_CANDB_HRES)}` and `{rel(OUT_USER_HRES)}` (method crops in planner-compatible HRes domain)",
        f"- `{rel(OUT_CANDB_TEMP)}` and `{rel(OUT_USER_TEMP)}` (same-day temperature crops in tempRes domain)",
        f"- `{rel(OUT_CANDB_PLANNER)}` and `{rel(OUT_USER_PLANNER)}` (planner-domain method crops)",
        f"- `{rel(OUT_PANEL_TEMP)}`",
        f"- `{rel(OUT_PANEL_HRES)}`",
        f"- `{rel(OUT_PANEL_ALL)}`",
        "",
        "## Grid Mapping And Orientation",
        "- No orientation inversion was applied in array-based figures (`origin=lower` used explicitly).",
        "- Cross-domain mapping applied for tempRes method crops: linear lon/lat normalization from planner-compatible full bbox to tempRes indexed grid.",
        f"- Mapping note: {mapping_note}",
        "",
        "## Visual Differences Between Methods",
        f"- Planner-domain IoU (`CAND_B` vs `USER_DIRECT_KM`): `{iou_planner:.4f}`",
        f"- TempRes-domain IoU (`CAND_B` vs `USER_DIRECT_KM`): `{iou_temp:.4f}`",
        f"- Planner center-distance in cells: `{center_dist_planner:.3f}`",
        f"- TempRes center-distance in cells: `{center_dist_temp:.3f}`",
        f"- `CAND_B` planner crop shape: `{candb_planner_roi.height}x{candb_planner_roi.width}`; `USER_DIRECT_KM` planner crop shape: `{user_planner_roi.height}x{user_planner_roi.width}`",
        f"- `CAND_B` temp crop shape: `{candb_temp_roi.height}x{candb_temp_roi.width}`; `USER_DIRECT_KM` temp crop shape: `{user_temp_roi.height}x{user_temp_roi.width}`",
        "",
        "## Tables And Checks",
        f"- Metrics table: `{rel(OUT_METRICS)}`",
        f"- Bounding boxes table: `{rel(OUT_BBOXES)}`",
        f"- Detailed checks and provenance: `{rel(OUT_CHECKS)}`",
        "",
        "## Conclusion",
        f"- The corrected comparison now includes the full-day tempRes image for `{day_used.isoformat()}` from the existing 300-image set,",
        "- plus both temperature-domain and planner-compatible HRes/planner-domain method crops for `CAND_B` and `USER_DIRECT_KM`.",
    ]
    ensure_parent(OUT_REPORT)
    OUT_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# Corrected Method Crop Summary",
        "",
        f"- day_used: `{day_used.isoformat()}`",
        f"- tempres_reference_png_used: `{rel(tempres_full_png_src)}`",
        "- method_crop_domain: `planner_compatible_hres`",
        f"- candb_vs_user_planner_iou: `{iou_planner:.4f}`",
        f"- candb_vs_user_tempres_iou: `{iou_temp:.4f}`",
        f"- generated_metrics_csv: `{rel(OUT_METRICS)}`",
        f"- generated_bboxes_csv: `{rel(OUT_BBOXES)}`",
        f"- generated_checks_json: `{rel(OUT_CHECKS)}`",
        "",
        "Confirmed outputs include:",
        f"- full-day tempRes image: `{rel(OUT_FULL_DAY_TEMPRES)}`",
        f"- CAND_B temperature crop: `{rel(OUT_CANDB_TEMP)}`",
        f"- USER_DIRECT_KM temperature crop: `{rel(OUT_USER_TEMP)}`",
        f"- CAND_B planner/HRes crop: `{rel(OUT_CANDB_PLANNER)}`",
        f"- USER_DIRECT_KM planner/HRes crop: `{rel(OUT_USER_PLANNER)}`",
    ]
    ensure_parent(OUT_SUMMARY)
    OUT_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    checks["output_exists_check"] = {rel(p): bool(p.exists()) for p in outputs}
    OUT_CHECKS.write_text(json.dumps(checks, indent=2), encoding="utf-8")

    planner["ds"].close()

    print("Generated files:")
    for p in outputs:
        print(rel(p))


if __name__ == "__main__":
    main()
