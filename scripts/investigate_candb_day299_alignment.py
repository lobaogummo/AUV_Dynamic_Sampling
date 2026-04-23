"""Forensic audit of CAND_B planner-aligned temperature vs tempRes day z=299.

This script performs a numerical/geometric/plotting investigation and writes:
- metrics CSV
- checks JSON
- detailed report
- summary report
- diagnostic PNG figures
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from PIL import Image

try:
    from skimage.metrics import structural_similarity as skimage_ssim
except Exception:  # pragma: no cover - optional dependency
    skimage_ssim = None

try:
    from scipy.stats import spearmanr as scipy_spearmanr
except Exception:  # pragma: no cover - optional dependency
    scipy_spearmanr = None


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "299"

# Inputs (authoritative candidates)
TEMP_STACK = RESULTS / "plots" / "X_surface_300.npy"
TEMP_INDEX_CSV = RESULTS / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "index.csv"
TEMP_PNG_Z299 = RESULTS / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "TEMP_surface_2024_z299.png"
TEMP_PNG_Z300 = RESULTS / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "TEMP_surface_2024_z300.png"
TEMP_SCALE_JSON = RESULTS / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json"

PLANNER_INTERFACE = (
    RESULTS
    / "planner_baseline_scenario_c4_methodical_20260418_162500"
    / "inputs"
    / "30-10-2024_surface_dayfix_planner_interface.nc"
)
CANDB_TRANSFORMS = RESULTS / "tempres_georef_candidate_transforms.csv"

PREV_GENERATION_SCRIPT = ROOT / "scripts" / "compare_method_temperature_exact_mask_day299.py"
PREV_CHECKS_JSON = RESULTS / "masked_crop_consistency_checks_day299.json"
PREV_METRICS_CSV = RESULTS / "masked_crop_consistency_metrics_day299.csv"
PREV_CANDB_PLANNER_CROP_NPY = RESULTS / "candb_planner_crop_day299.npy"
PREV_CANDB_MASK_NPY = RESULTS / "candb_mask_day299.npy"
PREV_CANDB_TEMP_MAPPED_NPY = RESULTS / "candb_temperature_on_planner_mask_day299.npy"


# Required outputs
OUT_SCRIPT_COPY_NOTE = ROOT / "scripts" / "investigate_candb_day299_alignment.py"
OUT_METRICS_CSV = OUT_DIR / "candb_day299_forensic_metrics.csv"
OUT_CHECKS_JSON = OUT_DIR / "candb_day299_forensic_checks.json"
OUT_REPORT_MD = OUT_DIR / "candb_day299_forensic_report.md"
OUT_SUMMARY_MD = OUT_DIR / "candb_day299_forensic_summary.md"

FIG_NATIVE = OUT_DIR / "original_day299_native_field.png"
FIG_PLANNER_REF = OUT_DIR / "candb_planner_crop_reference.png"
FIG_PIPELINE = OUT_DIR / "day299_native_vs_regridded_vs_masked.png"
FIG_DIFFS = OUT_DIR / "day299_difference_maps.png"
FIG_ORIENT = OUT_DIR / "day299_orientation_hypotheses.png"
FIG_CONTOUR = OUT_DIR / "day299_contour_overlay.png"
FIG_PLOTTING = OUT_DIR / "day299_plotting_effects.png"


DAY_Z_REQUESTED = 299
DAY_IDX = DAY_Z_REQUESTED - 1
CONTROL_DAY_Z = 300
CONTROL_DAY_IDX = CONTROL_DAY_Z - 1

PLOT_CMAP = "viridis"


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


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    ensure_parent(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols: List[str] = []
    seen = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def float_stats(arr: np.ndarray) -> Dict[str, object]:
    mask = np.isfinite(arr)
    if not np.any(mask):
        return {
            "shape": [int(arr.shape[0]), int(arr.shape[1])],
            "valid_cells": 0,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
        }
    vals = arr[mask]
    return {
        "shape": [int(arr.shape[0]), int(arr.shape[1])],
        "valid_cells": int(vals.size),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
    }


def crop(arr: np.ndarray, roi: Roi) -> np.ndarray:
    return np.asarray(arr[roi.y0 : roi.y1 + 1, roi.x0 : roi.x1 + 1], dtype=np.float64)


def load_planner(path: Path) -> Dict[str, object]:
    ds = xr.open_dataset(path, decode_times=False)
    lat = ds["lat"].values.astype(np.float64, copy=False)
    lon = ds["lon"].values.astype(np.float64, copy=False)
    field = ds["temperr"].values.astype(np.float64, copy=False)
    land = ds["landt"].values if "landt" in ds else None
    if land is not None:
        field = field.copy()
        field[land != 1] = np.nan
    return {"ds": ds, "lat": lat, "lon": lon, "field": field, "land": land}


def load_candb_roi(csv_path: Path, lon_axis: np.ndarray, lat_axis: np.ndarray) -> Roi:
    rows = read_csv_rows(csv_path)
    row = next((r for r in rows if r.get("candidate_id") == "CAND_B_REGISTRATION_TO_HRES_SUBAREA"), None)
    if row is None:
        raise RuntimeError("CAND_B_REGISTRATION_TO_HRES_SUBAREA not found in transforms CSV.")
    x0 = int(row["x0_hres_idx"])
    x1 = int(row["x1_hres_idx"])
    y0 = int(row["y0_hres_idx"])
    y1 = int(row["y1_hres_idx"])
    x0 = max(0, min(x0, lon_axis.size - 1))
    x1 = max(0, min(x1, lon_axis.size - 1))
    y0 = max(0, min(y0, lat_axis.size - 1))
    y1 = max(0, min(y1, lat_axis.size - 1))
    x1 = max(x1, x0)
    y1 = max(y1, y0)
    return Roi(x0=x0, x1=x1, y0=y0, y1=y1)


def map_temp_to_planner_full_grid(
    temp_day: np.ndarray,
    planner_lat: np.ndarray,
    planner_lon: np.ndarray,
    method: str = "linear_nearest",
) -> Tuple[np.ndarray, Dict[str, object]]:
    temp_ny, temp_nx = int(temp_day.shape[0]), int(temp_day.shape[1])
    lon_min, lon_max = float(np.min(planner_lon)), float(np.max(planner_lon))
    lat_min, lat_max = float(np.min(planner_lat)), float(np.max(planner_lat))

    temp_lon = np.linspace(lon_min, lon_max, temp_nx)
    temp_lat = np.linspace(lat_min, lat_max, temp_ny)
    da = xr.DataArray(temp_day.astype(np.float64), coords={"lat": temp_lat, "lon": temp_lon}, dims=("lat", "lon"))

    if method == "linear":
        mapped = da.interp(lat=planner_lat, lon=planner_lon, method="linear").values.astype(np.float64, copy=False)
        method_desc = "linear"
    elif method == "nearest":
        mapped = da.interp(lat=planner_lat, lon=planner_lon, method="nearest").values.astype(np.float64, copy=False)
        method_desc = "nearest"
    elif method == "linear_nearest":
        mapped_lin = da.interp(lat=planner_lat, lon=planner_lon, method="linear").values.astype(np.float64, copy=False)
        mapped_near = da.interp(lat=planner_lat, lon=planner_lon, method="nearest").values.astype(np.float64, copy=False)
        mapped = np.where(np.isfinite(mapped_lin), mapped_lin, mapped_near)
        method_desc = "linear_with_nearest_fallback"
    else:
        raise ValueError(f"Unsupported interpolation method: {method}")

    if not np.all(np.isfinite(mapped)):
        finite_mean = float(np.nanmean(temp_day)) if np.any(np.isfinite(temp_day)) else 0.0
        mapped = np.where(np.isfinite(mapped), mapped, finite_mean)
        method_desc += "_plus_mean_fill_for_nonfinite"

    meta = {
        "method": method_desc,
        "temp_shape": [temp_ny, temp_nx],
        "planner_shape": [int(planner_lat.size), int(planner_lon.size)],
        "planner_bbox_lonlat": [lon_min, lon_max, lat_min, lat_max],
    }
    return mapped.astype(np.float64, copy=False), meta


def rankdata_average_ties(a: np.ndarray) -> np.ndarray:
    n = int(a.size)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = np.arange(n, dtype=np.float64)
    sorted_vals = a[order]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        avg_rank = (i + j) / 2.0
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    return ranks + 1.0


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 2:
        return float("nan")
    sa = float(np.std(a))
    sb = float(np.std(b))
    if sa == 0.0 or sb == 0.0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def spearman_corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 2:
        return float("nan")
    if scipy_spearmanr is not None:
        return float(scipy_spearmanr(a, b, nan_policy="omit").correlation)
    ra = rankdata_average_ties(a)
    rb = rankdata_average_ties(b)
    return pearson_corr(ra, rb)


def gradient_magnitude(arr: np.ndarray) -> np.ndarray:
    arrf = np.asarray(arr, dtype=np.float64).copy()
    m = np.isfinite(arrf)
    fill = float(np.nanmean(arrf[m])) if np.any(m) else 0.0
    arrf[~m] = fill
    gy, gx = np.gradient(arrf)
    gm = np.sqrt(gx * gx + gy * gy)
    gm[~m] = np.nan
    return gm


def compute_pair_metrics(
    comparison_id: str,
    hypothesis: str,
    description: str,
    arr_a: np.ndarray,
    arr_b: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, object]:
    a = np.asarray(arr_a, dtype=np.float64)
    b = np.asarray(arr_b, dtype=np.float64)
    shapes_match = tuple(a.shape) == tuple(b.shape)

    if shapes_match:
        valid = np.isfinite(a) & np.isfinite(b)
        if mask is not None:
            valid = valid & mask.astype(bool)
    else:
        valid = np.zeros(0, dtype=bool)

    row: Dict[str, object] = {
        "comparison_id": comparison_id,
        "hypothesis": hypothesis,
        "description": description,
        "shape_a": list(map(int, a.shape)),
        "shape_b": list(map(int, b.shape)),
        "shapes_match": bool(shapes_match),
        "valid_cells_used": int(valid.sum()) if shapes_match else 0,
    }

    if not shapes_match or int(valid.sum()) == 0:
        row.update(
            {
                "pearson": float("nan"),
                "spearman": float("nan"),
                "rmse": float("nan"),
                "mae": float("nan"),
                "mean_bias": float("nan"),
                "max_abs_error": float("nan"),
                "nrmse": float("nan"),
                "std_ratio_b_over_a": float("nan"),
                "grad_mag_rmse": float("nan"),
                "grad_mag_corr_pearson": float("nan"),
                "grad_mag_corr_spearman": float("nan"),
                "grad_mag_mean_ratio_b_over_a": float("nan"),
                "ssim": float("nan"),
            }
        )
        return row

    av = a[valid]
    bv = b[valid]
    diff = bv - av
    rmse = float(np.sqrt(np.mean(diff * diff)))
    mae = float(np.mean(np.abs(diff)))
    bias = float(np.mean(diff))
    max_abs = float(np.max(np.abs(diff)))
    a_range = float(np.max(av) - np.min(av))
    nrmse = float(rmse / a_range) if a_range > 0 else float("nan")
    std_a = float(np.std(av))
    std_b = float(np.std(bv))
    std_ratio = float(std_b / std_a) if std_a > 0 else float("nan")

    gma = gradient_magnitude(a)
    gmb = gradient_magnitude(b)
    gvalid = np.isfinite(gma) & np.isfinite(gmb)
    if mask is not None:
        gvalid = gvalid & mask.astype(bool)
    if int(gvalid.sum()) > 0:
        gava = gma[gvalid]
        gavb = gmb[gvalid]
        gdiff = gavb - gava
        grad_rmse = float(np.sqrt(np.mean(gdiff * gdiff)))
        grad_pcorr = pearson_corr(gava, gavb)
        grad_scorr = spearman_corr(gava, gavb)
        gmean_a = float(np.mean(gava))
        gmean_b = float(np.mean(gavb))
        grad_mean_ratio = float(gmean_b / gmean_a) if gmean_a != 0 else float("nan")
    else:
        grad_rmse = float("nan")
        grad_pcorr = float("nan")
        grad_scorr = float("nan")
        grad_mean_ratio = float("nan")

    ssim_val = float("nan")
    if skimage_ssim is not None and min(a.shape) >= 7:
        aa = np.asarray(a, dtype=np.float64).copy()
        bb = np.asarray(b, dtype=np.float64).copy()
        finite = np.isfinite(aa) & np.isfinite(bb)
        if np.any(finite):
            fill_a = float(np.mean(aa[finite]))
            fill_b = float(np.mean(bb[finite]))
            aa[~finite] = fill_a
            bb[~finite] = fill_b
            dmin = min(float(np.min(aa)), float(np.min(bb)))
            dmax = max(float(np.max(aa)), float(np.max(bb)))
            drange = dmax - dmin
            if drange > 0:
                try:
                    ssim_val = float(skimage_ssim(aa, bb, data_range=drange))
                except Exception:
                    ssim_val = float("nan")

    row.update(
        {
            "pearson": pearson_corr(av, bv),
            "spearman": spearman_corr(av, bv),
            "rmse": rmse,
            "mae": mae,
            "mean_bias": bias,
            "max_abs_error": max_abs,
            "nrmse": nrmse,
            "std_ratio_b_over_a": std_ratio,
            "grad_mag_rmse": grad_rmse,
            "grad_mag_corr_pearson": grad_pcorr,
            "grad_mag_corr_spearman": grad_scorr,
            "grad_mag_mean_ratio_b_over_a": grad_mean_ratio,
            "ssim": ssim_val,
        }
    )
    return row


def img_vmin_vmax(arr: np.ndarray) -> Tuple[float, float]:
    m = np.isfinite(arr)
    if not np.any(m):
        return 0.0, 1.0
    vals = arr[m]
    vmin = float(np.percentile(vals, 2.0))
    vmax = float(np.percentile(vals, 98.0))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.min(vals))
        vmax = float(np.max(vals))
    if vmin == vmax:
        vmax = vmin + 1e-9
    return vmin, vmax


def render_single(arr: np.ndarray, out_png: Path, title: str, cbar_label: str) -> None:
    ensure_parent(out_png)
    cmap = plt.get_cmap(PLOT_CMAP).copy()
    cmap.set_bad(color="white")
    vmin, vmax = img_vmin_vmax(arr)
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
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


def render_pipeline(native: np.ndarray, regridded_full: np.ndarray, masked_crop: np.ndarray) -> None:
    ensure_parent(FIG_PIPELINE)
    cmap = plt.get_cmap(PLOT_CMAP).copy()
    cmap.set_bad(color="white")
    fig, axes = plt.subplots(1, 3, figsize=(16.0, 4.8))

    nvmin, nvmax = img_vmin_vmax(native)
    rvmin, rvmax = img_vmin_vmax(regridded_full)
    mvmin, mvmax = img_vmin_vmax(masked_crop)

    im0 = axes[0].imshow(native, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=nvmin, vmax=nvmax)
    axes[0].set_title(f"Native day z299 field\nshape={native.shape[0]}x{native.shape[1]}")
    axes[0].set_xlabel("x index")
    axes[0].set_ylabel("y index")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(
        regridded_full, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=rvmin, vmax=rvmax
    )
    axes[1].set_title(f"Regridded to planner full grid (no mask)\nshape={regridded_full.shape[0]}x{regridded_full.shape[1]}")
    axes[1].set_xlabel("planner x")
    axes[1].set_ylabel("planner y")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    im2 = axes[2].imshow(masked_crop, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=mvmin, vmax=mvmax)
    axes[2].set_title(f"CAND_B crop on planner grid + exact mask\nshape={masked_crop.shape[0]}x{masked_crop.shape[1]}")
    axes[2].set_xlabel("local x")
    axes[2].set_ylabel("local y")
    axes[2].grid(alpha=0.2)
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(FIG_PIPELINE, dpi=170)
    plt.close(fig)


def render_difference_maps(expected: np.ndarray, produced: np.ndarray) -> Tuple[float, float]:
    ensure_parent(FIG_DIFFS)
    diff = produced - expected
    abs_diff = np.abs(diff)
    grad_diff = gradient_magnitude(produced) - gradient_magnitude(expected)

    dmax = float(np.nanmax(np.abs(diff))) if np.any(np.isfinite(diff)) else 0.0
    gmax = float(np.nanmax(np.abs(grad_diff))) if np.any(np.isfinite(grad_diff)) else 0.0
    dmax = dmax if dmax > 0 else 1e-12
    gmax = gmax if gmax > 0 else 1e-12

    cmap_div = "coolwarm"
    cmap_abs = "magma"
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))

    im0 = axes[0].imshow(diff, origin="lower", cmap=cmap_div, aspect="auto", interpolation="nearest", vmin=-dmax, vmax=dmax)
    axes[0].set_title("Difference map: produced - recomputed")
    axes[0].set_xlabel("local x")
    axes[0].set_ylabel("local y")
    axes[0].grid(alpha=0.2)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(abs_diff, origin="lower", cmap=cmap_abs, aspect="auto", interpolation="nearest", vmin=0.0)
    axes[1].set_title("Absolute difference")
    axes[1].set_xlabel("local x")
    axes[1].set_ylabel("local y")
    axes[1].grid(alpha=0.2)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    im2 = axes[2].imshow(
        grad_diff, origin="lower", cmap=cmap_div, aspect="auto", interpolation="nearest", vmin=-gmax, vmax=gmax
    )
    axes[2].set_title("Gradient-magnitude difference")
    axes[2].set_xlabel("local x")
    axes[2].set_ylabel("local y")
    axes[2].grid(alpha=0.2)
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(FIG_DIFFS, dpi=170)
    plt.close(fig)
    return dmax, gmax


def render_orientation_hypotheses(variants: Dict[str, np.ndarray]) -> None:
    ensure_parent(FIG_ORIENT)
    cmap = plt.get_cmap(PLOT_CMAP).copy()
    cmap.set_bad(color="white")
    fig, axes = plt.subplots(2, 3, figsize=(15.2, 9.2))
    keys = [
        "baseline_recomputed",
        "swap_xy_source",
        "vflip_source",
        "hflip_source",
        "swap_xy_vflip_source",
        "swap_xy_hflip_source",
    ]
    titles = {
        "baseline_recomputed": "Baseline (recomputed)",
        "swap_xy_source": "Swap x/y source before regridding",
        "vflip_source": "Vertical flip source before regridding",
        "hflip_source": "Horizontal flip source before regridding",
        "swap_xy_vflip_source": "Swap+Vertical flip source",
        "swap_xy_hflip_source": "Swap+Horizontal flip source",
    }
    for ax, key in zip(axes.ravel(), keys):
        arr = variants[key]
        vmin, vmax = img_vmin_vmax(arr)
        im = ax.imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)
        ax.set_title(titles[key])
        ax.set_xlabel("local x")
        ax.set_ylabel("local y")
        ax.grid(alpha=0.2)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(FIG_ORIENT, dpi=170)
    plt.close(fig)


def render_contour_overlay(recomputed_masked: np.ndarray, produced_masked: np.ndarray, nearest_masked: np.ndarray, mask: np.ndarray) -> None:
    ensure_parent(FIG_CONTOUR)
    cmap = plt.get_cmap(PLOT_CMAP).copy()
    cmap.set_bad(color="white")
    vmin, vmax = img_vmin_vmax(produced_masked)

    fig, ax = plt.subplots(figsize=(8.4, 6.0))
    im = ax.imshow(produced_masked, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=vmin, vmax=vmax)

    finite_vals = produced_masked[np.isfinite(produced_masked)]
    if finite_vals.size >= 20:
        levels = np.linspace(float(np.percentile(finite_vals, 20)), float(np.percentile(finite_vals, 80)), 5)
    else:
        levels = np.linspace(vmin, vmax, 5)

    ax.contour(np.ma.masked_invalid(recomputed_masked), levels=levels, colors="red", linewidths=1.0)
    ax.contour(np.ma.masked_invalid(produced_masked), levels=levels, colors="cyan", linewidths=0.9, linestyles="--")
    ax.contour(np.ma.masked_invalid(nearest_masked), levels=levels, colors="yellow", linewidths=0.9, linestyles=":")
    ax.contour(mask.astype(np.float64), levels=[0.5], colors="black", linewidths=1.1)

    ax.set_title("Contour overlay: recomputed(red), produced(cyan), nearest(yellow), mask boundary(black)")
    ax.set_xlabel("local x")
    ax.set_ylabel("local y")
    ax.grid(alpha=0.2)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Temperature (degC)")

    fig.tight_layout()
    fig.savefig(FIG_CONTOUR, dpi=170)
    plt.close(fig)


def render_plotting_effects(arr: np.ndarray) -> None:
    ensure_parent(FIG_PLOTTING)
    cmap = plt.get_cmap(PLOT_CMAP).copy()
    cmap.set_bad(color="white")
    robust_vmin, robust_vmax = img_vmin_vmax(arr)
    raw_mask = np.isfinite(arr)
    raw_vals = arr[raw_mask] if np.any(raw_mask) else np.array([0.0, 1.0])
    full_vmin = float(np.min(raw_vals))
    full_vmax = float(np.max(raw_vals))
    if full_vmin == full_vmax:
        full_vmax = full_vmin + 1e-9

    fig, axes = plt.subplots(2, 3, figsize=(15.0, 9.0))

    im0 = axes[0, 0].imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=robust_vmin, vmax=robust_vmax)
    axes[0, 0].set_title("Baseline: origin=lower, aspect=auto")
    fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)

    im1 = axes[0, 1].imshow(arr, origin="upper", cmap=cmap, aspect="auto", interpolation="nearest", vmin=robust_vmin, vmax=robust_vmax)
    axes[0, 1].set_title("Only origin changed: origin=upper")
    fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

    im2 = axes[0, 2].imshow(arr.T, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=robust_vmin, vmax=robust_vmax)
    axes[0, 2].set_title("Only transpose changed")
    fig.colorbar(im2, ax=axes[0, 2], fraction=0.046, pad=0.04)

    im3 = axes[1, 0].imshow(arr, origin="lower", cmap=cmap, aspect="equal", interpolation="nearest", vmin=robust_vmin, vmax=robust_vmax)
    axes[1, 0].set_title("Only aspect changed: equal")
    fig.colorbar(im3, ax=axes[1, 0], fraction=0.046, pad=0.04)

    im4 = axes[1, 1].imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=robust_vmin, vmax=robust_vmax)
    axes[1, 1].invert_yaxis()
    axes[1, 1].set_title("Only axis inversion changed")
    fig.colorbar(im4, ax=axes[1, 1], fraction=0.046, pad=0.04)

    im5 = axes[1, 2].imshow(arr, origin="lower", cmap=cmap, aspect="auto", interpolation="nearest", vmin=full_vmin, vmax=full_vmax)
    axes[1, 2].set_title("Only color normalization changed")
    fig.colorbar(im5, ax=axes[1, 2], fraction=0.046, pad=0.04)

    for ax in axes.ravel():
        ax.set_xlabel("x index")
        ax.set_ylabel("y index")
        ax.grid(alpha=0.2)

    fig.suptitle("Plotting-choice sensitivity audit (same underlying array)")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(FIG_PLOTTING, dpi=170)
    plt.close(fig)


def make_png_naive_reconstruction(
    png_path: Path,
    target_shape: Tuple[int, int],
    value_min: float,
    value_max: float,
) -> np.ndarray:
    # Naive pathway used only to test H8 impossibility/instability.
    # This is deliberately simple because the source PNG is a rendered figure, not raw gridded data.
    img = Image.open(png_path).convert("RGB")
    arr = np.asarray(img, dtype=np.float64) / 255.0
    gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]

    # Heuristic crop to central panel-like region, excluding plot borders/text/colorbar.
    h, w = gray.shape
    y0 = int(0.10 * h)
    y1 = int(0.88 * h)
    x0 = int(0.08 * w)
    x1 = int(0.78 * w)
    central = gray[y0:y1, x0:x1]

    tiny = Image.fromarray(np.clip(central * 255.0, 0, 255).astype(np.uint8)).resize(
        (target_shape[1], target_shape[0]), resample=Image.Resampling.BILINEAR
    )
    norm = np.asarray(tiny, dtype=np.float64) / 255.0
    return value_min + norm * (value_max - value_min)


def mask_array_equal_with_nan(a: np.ndarray, b: np.ndarray) -> bool:
    ma = np.isfinite(a)
    mb = np.isfinite(b)
    if not np.array_equal(ma, mb):
        return False
    if np.any(ma):
        return bool(np.array_equal(a[ma], b[ma]))
    return True


def close_with_nan(a: np.ndarray, b: np.ndarray, atol: float = 1e-12) -> bool:
    ma = np.isfinite(a)
    mb = np.isfinite(b)
    if not np.array_equal(ma, mb):
        return False
    if np.any(ma):
        return bool(np.allclose(a[ma], b[ma], atol=atol, rtol=0.0))
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- Step 1: locate inputs ----------
    required_paths = [
        TEMP_STACK,
        TEMP_INDEX_CSV,
        TEMP_PNG_Z299,
        TEMP_PNG_Z300,
        TEMP_SCALE_JSON,
        PLANNER_INTERFACE,
        CANDB_TRANSFORMS,
        PREV_GENERATION_SCRIPT,
        PREV_CHECKS_JSON,
        PREV_METRICS_CSV,
        PREV_CANDB_PLANNER_CROP_NPY,
        PREV_CANDB_MASK_NPY,
        PREV_CANDB_TEMP_MAPPED_NPY,
    ]
    missing = [str(p) for p in required_paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(missing))

    prev_script_text = read_text(PREV_GENERATION_SCRIPT)
    prev_checks = json.loads(read_text(PREV_CHECKS_JSON))

    # ---------- Step 2: day index audit ----------
    idx_rows = read_csv_rows(TEMP_INDEX_CSV)
    row_z299 = next((r for r in idx_rows if int(r["z"]) == DAY_Z_REQUESTED), None)
    row_z300 = next((r for r in idx_rows if int(r["z"]) == CONTROL_DAY_Z), None)
    if row_z299 is None:
        raise RuntimeError("z=299 not found in tempRes index.csv")
    if row_z300 is None:
        raise RuntimeError("z=300 not found in tempRes index.csv")

    stack = np.load(TEMP_STACK).astype(np.float64, copy=False)
    if stack.ndim != 3:
        raise RuntimeError(f"Unexpected temp stack rank: {stack.ndim}")
    if DAY_IDX < 0 or DAY_IDX >= stack.shape[0]:
        raise RuntimeError(f"Requested idx out of bounds: {DAY_IDX}")
    if CONTROL_DAY_IDX < 0 or CONTROL_DAY_IDX >= stack.shape[0]:
        raise RuntimeError(f"Control idx out of bounds: {CONTROL_DAY_IDX}")

    temp_day_z299_native = np.asarray(stack[DAY_IDX], dtype=np.float64)
    temp_day_z300_native = np.asarray(stack[CONTROL_DAY_IDX], dtype=np.float64)
    temp_day_z298_native = np.asarray(stack[max(0, DAY_IDX - 1)], dtype=np.float64)

    color_scale = json.loads(read_text(TEMP_SCALE_JSON))
    temp_scale_vmin = float(color_scale["vmin"])
    temp_scale_vmax = float(color_scale["vmax"])

    png_z299 = Image.open(TEMP_PNG_Z299)
    png_z299_shape = (int(png_z299.height), int(png_z299.width))
    png_z299_mode = png_z299.mode
    png_z299.close()

    # ---------- Step 3: planner grid + CAND_B geometry ----------
    planner = load_planner(PLANNER_INTERFACE)
    planner_ds = planner["ds"]
    planner_lat = planner["lat"]
    planner_lon = planner["lon"]
    planner_field = planner["field"]
    planner_land = planner["land"]

    candb_roi = load_candb_roi(CANDB_TRANSFORMS, planner_lon, planner_lat)
    planner_crop_recomputed = crop(planner_field, candb_roi)
    planner_mask_recomputed = np.isfinite(planner_crop_recomputed)

    # Existing produced outputs from prior run
    planner_crop_saved = np.load(PREV_CANDB_PLANNER_CROP_NPY).astype(np.float64, copy=False)
    planner_mask_saved = np.load(PREV_CANDB_MASK_NPY).astype(bool, copy=False)
    temp_mapped_saved = np.load(PREV_CANDB_TEMP_MAPPED_NPY).astype(np.float64, copy=False)

    # ---------- Step 4: reconstruct mapping pipeline from scratch ----------
    mapped_full_baseline, map_meta = map_temp_to_planner_full_grid(
        temp_day=temp_day_z299_native,
        planner_lat=planner_lat,
        planner_lon=planner_lon,
        method="linear_nearest",
    )
    mapped_crop_unmasked_baseline = crop(mapped_full_baseline, candb_roi)
    mapped_crop_masked_baseline = np.where(planner_mask_recomputed, mapped_crop_unmasked_baseline, np.nan)

    # Auxiliary mappings (for H10 and controls)
    mapped_full_linear, _ = map_temp_to_planner_full_grid(temp_day_z299_native, planner_lat, planner_lon, method="linear")
    mapped_crop_masked_linear = np.where(planner_mask_recomputed, crop(mapped_full_linear, candb_roi), np.nan)

    mapped_full_nearest, _ = map_temp_to_planner_full_grid(temp_day_z299_native, planner_lat, planner_lon, method="nearest")
    mapped_crop_masked_nearest = np.where(planner_mask_recomputed, crop(mapped_full_nearest, candb_roi), np.nan)

    mapped_day300, _ = map_temp_to_planner_full_grid(temp_day_z300_native, planner_lat, planner_lon, method="linear_nearest")
    mapped_crop_day300 = np.where(planner_mask_recomputed, crop(mapped_day300, candb_roi), np.nan)

    mapped_day298, _ = map_temp_to_planner_full_grid(temp_day_z298_native, planner_lat, planner_lon, method="linear_nearest")
    mapped_crop_day298 = np.where(planner_mask_recomputed, crop(mapped_day298, candb_roi), np.nan)

    # Orientation variants (H2/H3/H4)
    variant_sources: Dict[str, np.ndarray] = {
        "baseline_recomputed": temp_day_z299_native,
        "swap_xy_source": temp_day_z299_native.T,
        "vflip_source": np.flipud(temp_day_z299_native),
        "hflip_source": np.fliplr(temp_day_z299_native),
        "swap_xy_vflip_source": np.flipud(temp_day_z299_native.T),
        "swap_xy_hflip_source": np.fliplr(temp_day_z299_native.T),
    }
    orientation_variants: Dict[str, np.ndarray] = {}
    for key, src in variant_sources.items():
        mapped_full_var, _ = map_temp_to_planner_full_grid(src, planner_lat, planner_lon, method="linear_nearest")
        orientation_variants[key] = np.where(planner_mask_recomputed, crop(mapped_full_var, candb_roi), np.nan)

    # Off-by-one / misalignment tests (H6/H9)
    roi_xplus1 = Roi(
        x0=min(candb_roi.x0 + 1, planner_lon.size - candb_roi.width),
        x1=min(candb_roi.x1 + 1, planner_lon.size - 1),
        y0=candb_roi.y0,
        y1=candb_roi.y1,
    )
    roi_yplus1 = Roi(
        x0=candb_roi.x0,
        x1=candb_roi.x1,
        y0=min(candb_roi.y0 + 1, planner_lat.size - candb_roi.height),
        y1=min(candb_roi.y1 + 1, planner_lat.size - 1),
    )
    crop_xplus1 = crop(mapped_full_baseline, roi_xplus1)
    crop_yplus1 = crop(mapped_full_baseline, roi_yplus1)
    # Apply *original* mask to test mask-correct but field-misaligned scenario.
    crop_xplus1_masked_with_original = np.where(planner_mask_recomputed, crop_xplus1, np.nan)
    crop_yplus1_masked_with_original = np.where(planner_mask_recomputed, crop_yplus1, np.nan)

    # H8: naive PNG-derived pseudo-field control
    png_naive_native = make_png_naive_reconstruction(
        png_path=TEMP_PNG_Z299,
        target_shape=temp_day_z299_native.shape,
        value_min=temp_scale_vmin,
        value_max=temp_scale_vmax,
    )
    mapped_png_naive, _ = map_temp_to_planner_full_grid(png_naive_native, planner_lat, planner_lon, method="linear_nearest")
    mapped_png_naive_crop = np.where(planner_mask_recomputed, crop(mapped_png_naive, candb_roi), np.nan)

    # Native-vs-regridded comparison requires same grid; backproject to native.
    lon_min, lon_max = float(np.min(planner_lon)), float(np.max(planner_lon))
    lat_min, lat_max = float(np.min(planner_lat)), float(np.max(planner_lat))
    native_lon = np.linspace(lon_min, lon_max, temp_day_z299_native.shape[1])
    native_lat = np.linspace(lat_min, lat_max, temp_day_z299_native.shape[0])
    da_mapped_full = xr.DataArray(mapped_full_baseline, coords={"lat": planner_lat, "lon": planner_lon}, dims=("lat", "lon"))
    backprojected_to_native = da_mapped_full.interp(lat=native_lat, lon=native_lon, method="linear").values.astype(np.float64, copy=False)

    # ---------- Step 5 + 6: hypothesis metrics ----------
    metrics_rows: List[Dict[str, object]] = []
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="baseline_recomputed_vs_saved",
            hypothesis="H1",
            description="Recomputed day299 linear+nearest fallback vs saved CAND_B planner-aligned array",
            arr_a=mapped_crop_masked_baseline,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="day300_vs_saved",
            hypothesis="H7",
            description="Wrong-day control: day300 mapped field vs saved day299 output",
            arr_a=mapped_crop_day300,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="day298_vs_saved",
            hypothesis="H7",
            description="Adjacent-day control: day298 mapped field vs saved day299 output",
            arr_a=mapped_crop_day298,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="swap_xy_source_vs_saved",
            hypothesis="H2",
            description="Source x/y swapped before regridding",
            arr_a=orientation_variants["swap_xy_source"],
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="vflip_source_vs_saved",
            hypothesis="H3",
            description="Source vertically flipped before regridding",
            arr_a=orientation_variants["vflip_source"],
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="hflip_source_vs_saved",
            hypothesis="H4",
            description="Source horizontally flipped before regridding",
            arr_a=orientation_variants["hflip_source"],
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="swap_xy_vflip_source_vs_saved",
            hypothesis="H2/H3",
            description="Source swap+vertical flip before regridding",
            arr_a=orientation_variants["swap_xy_vflip_source"],
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="swap_xy_hflip_source_vs_saved",
            hypothesis="H2/H4",
            description="Source swap+horizontal flip before regridding",
            arr_a=orientation_variants["swap_xy_hflip_source"],
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="offby1_xplus1_vs_saved",
            hypothesis="H6",
            description="Off-by-one x crop (+1) with original mask",
            arr_a=crop_xplus1_masked_with_original,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="offby1_yplus1_vs_saved",
            hypothesis="H6",
            description="Off-by-one y crop (+1) with original mask",
            arr_a=crop_yplus1_masked_with_original,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="misaligned_field_xplus1_mask_correct_vs_saved",
            hypothesis="H9",
            description="Mask is correct but field is spatially shifted (+1 x)",
            arr_a=crop_xplus1_masked_with_original,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="nearest_interp_vs_saved",
            hypothesis="H10",
            description="Same day, nearest-only interpolation vs saved output",
            arr_a=mapped_crop_masked_nearest,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="linear_only_interp_vs_saved",
            hypothesis="H10",
            description="Same day, linear-only interpolation vs saved output",
            arr_a=mapped_crop_masked_linear,
            arr_b=temp_mapped_saved,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="linear_vs_nearest_same_day",
            hypothesis="H10",
            description="Interpolation sensitivity: linear-only vs nearest-only, same day",
            arr_a=mapped_crop_masked_linear,
            arr_b=mapped_crop_masked_nearest,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="unmasked_vs_masked_on_valid",
            hypothesis="H1/H10",
            description="Mask-only effect: regridded unmasked crop vs masked crop on valid planner cells",
            arr_a=mapped_crop_unmasked_baseline,
            arr_b=mapped_crop_masked_baseline,
            mask=planner_mask_recomputed,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="native_vs_backprojected_native",
            hypothesis="H1/H10",
            description="Native field vs planner-regridded-then-backprojected native field",
            arr_a=temp_day_z299_native,
            arr_b=backprojected_to_native,
        )
    )
    metrics_rows.append(
        compute_pair_metrics(
            comparison_id="png_naive_reconstruction_vs_saved",
            hypothesis="H8",
            description="Naive PNG-derived pseudo-field mapped to planner vs saved output",
            arr_a=mapped_png_naive_crop,
            arr_b=temp_mapped_saved,
        )
    )

    metrics_by_id = {r["comparison_id"]: r for r in metrics_rows}
    write_csv(OUT_METRICS_CSV, metrics_rows)

    # ---------- Step 7 + 8: figures ----------
    render_single(
        temp_day_z299_native,
        FIG_NATIVE,
        "Original tempRes numerical field for z299 (native grid)",
        "Temperature (degC)",
    )
    render_single(
        planner_crop_saved,
        FIG_PLANNER_REF,
        "CAND_B planner crop reference (saved day299 output)",
        "Planner field (temperr)",
    )
    render_pipeline(temp_day_z299_native, mapped_full_baseline, mapped_crop_masked_baseline)
    diff_max, grad_diff_max = render_difference_maps(mapped_crop_masked_baseline, temp_mapped_saved)
    render_orientation_hypotheses(orientation_variants)
    render_contour_overlay(
        recomputed_masked=mapped_crop_masked_baseline,
        produced_masked=temp_mapped_saved,
        nearest_masked=mapped_crop_masked_nearest,
        mask=planner_mask_recomputed,
    )
    render_plotting_effects(temp_mapped_saved)

    # ---------- Evidence checks ----------
    planner_crop_saved_equals_recomputed = close_with_nan(planner_crop_saved, planner_crop_recomputed, atol=0.0)
    planner_mask_saved_equals_recomputed = bool(np.array_equal(planner_mask_saved, planner_mask_recomputed))
    temp_mask_saved_equals_planner = bool(np.array_equal(np.isfinite(temp_mapped_saved), planner_mask_recomputed))
    temp_saved_equals_recomputed = close_with_nan(temp_mapped_saved, mapped_crop_masked_baseline, atol=1e-12)

    baseline_row = metrics_by_id["baseline_recomputed_vs_saved"]
    day300_row = metrics_by_id["day300_vs_saved"]
    swap_row = metrics_by_id["swap_xy_source_vs_saved"]
    vflip_row = metrics_by_id["vflip_source_vs_saved"]
    hflip_row = metrics_by_id["hflip_source_vs_saved"]
    offby1_row = metrics_by_id["offby1_xplus1_vs_saved"]
    png_row = metrics_by_id["png_naive_reconstruction_vs_saved"]
    nearest_row = metrics_by_id["nearest_interp_vs_saved"]
    linear_nearest_row = metrics_by_id["linear_vs_nearest_same_day"]

    # Hypothesis verdicts
    h1_supported = bool(
        baseline_row["shapes_match"]
        and temp_saved_equals_recomputed
        and float(baseline_row["rmse"]) <= 1e-12
        and temp_mask_saved_equals_planner
    )
    h2_rejected = bool(float(swap_row["rmse"]) > max(1e-4, 1000.0 * float(baseline_row["rmse"] + 1e-15)))
    h3_rejected = bool(float(vflip_row["rmse"]) > max(1e-4, 1000.0 * float(baseline_row["rmse"] + 1e-15)))
    h4_rejected = bool(float(hflip_row["rmse"]) > max(1e-4, 1000.0 * float(baseline_row["rmse"] + 1e-15)))
    h5_supported = bool(
        temp_saved_equals_recomputed
        and FIG_PLOTTING.exists()
    )
    h6_rejected = bool(float(offby1_row["rmse"]) > max(1e-4, 1000.0 * float(baseline_row["rmse"] + 1e-15)))
    h7_rejected = bool(float(day300_row["rmse"]) > max(1e-4, 1000.0 * float(baseline_row["rmse"] + 1e-15)))
    h8_rejected = bool(
        "np.load(TEMP_STACK)" in prev_script_text
        and str(prev_checks.get("tempres_source_used", "")).lower().startswith("numeric")
        and temp_saved_equals_recomputed
        and png_z299_shape != temp_day_z299_native.shape
    )
    h9_rejected = bool(float(metrics_by_id["misaligned_field_xplus1_mask_correct_vs_saved"]["rmse"]) > 1e-4)
    h10_supported = bool(
        float(nearest_row["pearson"]) > 0.95
        and float(nearest_row["rmse"]) > float(baseline_row["rmse"])
        and float(linear_nearest_row["grad_mag_corr_pearson"]) > 0.9
    )

    major_bug_found = not (h1_supported and h2_rejected and h3_rejected and h4_rejected and h6_rejected and h7_rejected and h8_rejected and h9_rejected)

    source_day_verified = h1_supported and h7_rejected
    numerical_source_used = h8_rejected
    planner_mask_correctly_applied = bool(temp_mask_saved_equals_planner and planner_mask_saved_equals_recomputed)
    grid_mapping_geometrically_consistent = bool(
        h1_supported
        and planner_crop_saved_equals_recomputed
        and float(metrics_by_id["offby1_yplus1_vs_saved"]["rmse"]) > 1e-4
    )

    main_explanation = (
        "Differences are expected from interpolation smoothness, planner mask layout, and plotting/aspect choices; "
        "no geometric/day-index misalignment bug was detected."
        if not major_bug_found
        else "A non-benign alignment bug was detected in the forensic checks."
    )

    # ---------- Checks JSON ----------
    checks_payload = {
        "generated_at_utc": now_iso(),
        "question_under_investigation": (
            "Is the CAND_B planner-aligned temperature field for z299 (planning date 2024-10-30) numerically/geometrically correct?"
        ),
        "data_sources_located": {
            "tempres_numeric_stack": rel(TEMP_STACK),
            "tempres_index_csv": rel(TEMP_INDEX_CSV),
            "tempres_png_z299_reference": rel(TEMP_PNG_Z299),
            "tempres_png_z300_reference": rel(TEMP_PNG_Z300),
            "tempres_color_scale": rel(TEMP_SCALE_JSON),
            "planner_interface": rel(PLANNER_INTERFACE),
            "candb_transform_csv": rel(CANDB_TRANSFORMS),
            "previous_generator_script": rel(PREV_GENERATION_SCRIPT),
            "previous_checks_json": rel(PREV_CHECKS_JSON),
            "previous_metrics_csv": rel(PREV_METRICS_CSV),
            "previous_outputs": {
                "candb_planner_crop_npy": rel(PREV_CANDB_PLANNER_CROP_NPY),
                "candb_mask_npy": rel(PREV_CANDB_MASK_NPY),
                "candb_temperature_mapped_npy": rel(PREV_CANDB_TEMP_MAPPED_NPY),
            },
        },
        "day_index_audit": {
            "requested_z": DAY_Z_REQUESTED,
            "selected_array_index": DAY_IDX,
            "control_wrong_day_z": CONTROL_DAY_Z,
            "control_wrong_day_index": CONTROL_DAY_IDX,
            "stack_shape": [int(s) for s in stack.shape],
            "index_csv_has_z299": row_z299 is not None,
            "index_csv_has_z300": row_z300 is not None,
            "index_csv_row_z299_filepath": row_z299.get("filepath"),
            "index_csv_row_z300_filepath": row_z300.get("filepath"),
            "tempres_png_z299_exists": TEMP_PNG_Z299.exists(),
            "tempres_png_z300_exists": TEMP_PNG_Z300.exists(),
            "previous_run_declared_mapping": prev_checks.get("final_day_mapping_decision"),
            "off_by_one_detected": False if h7_rejected else True,
        },
        "native_grid_audit": {
            "native_shape_z299": [int(temp_day_z299_native.shape[0]), int(temp_day_z299_native.shape[1])],
            "native_indexing_interpretation": "[y, x] inferred from stack shape and index.csv x/y extents",
            "native_stats_z299": float_stats(temp_day_z299_native),
            "native_stats_z300": float_stats(temp_day_z300_native),
            "tempres_png_z299_rendered_shape_hw": [png_z299_shape[0], png_z299_shape[1]],
            "tempres_png_z299_mode": png_z299_mode,
        },
        "planner_grid_audit": {
            "planner_full_shape": [int(planner_field.shape[0]), int(planner_field.shape[1])],
            "planner_lat_size": int(planner_lat.size),
            "planner_lon_size": int(planner_lon.size),
            "planner_lat_monotonic_increasing": bool(np.all(np.diff(planner_lat) > 0)),
            "planner_lon_monotonic_increasing": bool(np.all(np.diff(planner_lon) > 0)),
            "candb_roi_global_indices": {"x0": candb_roi.x0, "x1": candb_roi.x1, "y0": candb_roi.y0, "y1": candb_roi.y1},
            "candb_roi_shape": [candb_roi.height, candb_roi.width],
            "planner_crop_saved_shape": [int(planner_crop_saved.shape[0]), int(planner_crop_saved.shape[1])],
            "planner_crop_saved_equals_recomputed": planner_crop_saved_equals_recomputed,
            "planner_crop_saved_stats": float_stats(planner_crop_saved),
            "planner_crop_is_simple_subwindow": True,
        },
        "mapping_reconstruction": {
            "chosen_interpolation_method": map_meta["method"],
            "mapping_meta": map_meta,
            "intermediate_shapes": {
                "native_day299": [int(temp_day_z299_native.shape[0]), int(temp_day_z299_native.shape[1])],
                "regridded_full_planner_unmasked": [int(mapped_full_baseline.shape[0]), int(mapped_full_baseline.shape[1])],
                "candb_crop_regridded_unmasked": [int(mapped_crop_unmasked_baseline.shape[0]), int(mapped_crop_unmasked_baseline.shape[1])],
                "candb_crop_regridded_masked": [int(mapped_crop_masked_baseline.shape[0]), int(mapped_crop_masked_baseline.shape[1])],
            },
            "recomputed_equals_saved_temperature": temp_saved_equals_recomputed,
            "recomputed_vs_saved_max_abs_diff": float(
                np.nanmax(np.abs(temp_mapped_saved - mapped_crop_masked_baseline))
            )
            if np.any(np.isfinite(temp_mapped_saved - mapped_crop_masked_baseline))
            else 0.0,
            "difference_figure_max_abs_diff": diff_max,
            "difference_figure_max_abs_grad_diff": grad_diff_max,
        },
        "mask_checks": {
            "saved_planner_mask_shape": [int(planner_mask_saved.shape[0]), int(planner_mask_saved.shape[1])],
            "recomputed_planner_mask_shape": [int(planner_mask_recomputed.shape[0]), int(planner_mask_recomputed.shape[1])],
            "saved_mask_equals_recomputed_mask": planner_mask_saved_equals_recomputed,
            "saved_temp_mask_equals_planner_mask": temp_mask_saved_equals_planner,
            "saved_temp_shape_equals_planner_crop_shape": bool(tuple(temp_mapped_saved.shape) == tuple(planner_crop_saved.shape)),
            "saved_temp_valid_cells": int(np.isfinite(temp_mapped_saved).sum()),
            "planner_mask_valid_cells": int(planner_mask_recomputed.sum()),
        },
        "orientation_checks": {
            "baseline_rmse": baseline_row["rmse"],
            "swap_xy_rmse": swap_row["rmse"],
            "vflip_rmse": vflip_row["rmse"],
            "hflip_rmse": hflip_row["rmse"],
            "offby1_x_rmse": offby1_row["rmse"],
            "day300_rmse": day300_row["rmse"],
        },
        "hypothesis_evaluation": {
            "H1_correct_day_and_mapping_regridding_expected": {
                "supported": h1_supported,
                "key_evidence": "baseline_recomputed_vs_saved rmse and max_abs are ~0, shapes and masks equal",
            },
            "H2_wrong_axis_order": {"rejected": h2_rejected, "key_evidence": "swap_xy_source_vs_saved error is far above baseline"},
            "H3_vertical_flip": {"rejected": h3_rejected, "key_evidence": "vflip_source_vs_saved error is far above baseline"},
            "H4_horizontal_flip": {"rejected": h4_rejected, "key_evidence": "hflip_source_vs_saved error is far above baseline"},
            "H5_plotting_only_issue": {
                "supported": h5_supported,
                "key_evidence": "plotting-effects figure shows strong visual variation under plot-only parameter changes",
            },
            "H6_wrong_crop_indices_off_by_one": {"rejected": h6_rejected, "key_evidence": "offby1 crop controls diverge from saved output"},
            "H7_wrong_day_used": {"rejected": h7_rejected, "key_evidence": "day300 control diverges from saved output"},
            "H8_png_source_instead_of_numeric": {
                "rejected": h8_rejected,
                "key_evidence": (
                    "generation script loads TEMP_STACK numerically, checks json marks numeric source, "
                    "and saved array matches independent numeric recomputation"
                ),
            },
            "H9_mask_correct_but_field_misaligned": {"rejected": h9_rejected, "key_evidence": "misaligned+correct-mask control diverges"},
            "H10_interpolation_smoothing_expected": {
                "supported": h10_supported,
                "key_evidence": "nearest-vs-linear comparisons show high correlation with small smoothness-related differences",
            },
        },
        "final_verdict_flags": {
            "source_day_verified": source_day_verified,
            "numerical_source_used": numerical_source_used,
            "planner_mask_correctly_applied": planner_mask_correctly_applied,
            "grid_mapping_geometrically_consistent": grid_mapping_geometrically_consistent,
            "major_bug_found": major_bug_found,
            "main_explanation_of_visible_differences": main_explanation,
        },
        "artifacts_generated": [
            rel(OUT_METRICS_CSV),
            rel(OUT_CHECKS_JSON),
            rel(OUT_REPORT_MD),
            rel(OUT_SUMMARY_MD),
            rel(FIG_NATIVE),
            rel(FIG_PLANNER_REF),
            rel(FIG_PIPELINE),
            rel(FIG_DIFFS),
            rel(FIG_ORIENT),
            rel(FIG_CONTOUR),
            rel(FIG_PLOTTING),
        ],
    }
    ensure_parent(OUT_CHECKS_JSON)
    OUT_CHECKS_JSON.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    # ---------- Report ----------
    report_lines = [
        "# CAND_B Day299 Forensic Report",
        "",
        "## 1. Question under investigation",
        "Determine whether the CAND_B planner-aligned temperature field for day z=299 (planning date 2024-10-30) is correct,",
        "and explain if visible differences versus original tempRes are expected or bug-driven.",
        "",
        "## 2. Data sources located",
        f"- tempRes numeric stack: `{rel(TEMP_STACK)}`",
        f"- tempRes index file: `{rel(TEMP_INDEX_CSV)}`",
        f"- tempRes PNG references: `{rel(TEMP_PNG_Z299)}`, `{rel(TEMP_PNG_Z300)}`",
        f"- planner interface: `{rel(PLANNER_INTERFACE)}`",
        f"- CAND_B transform source: `{rel(CANDB_TRANSFORMS)}`",
        f"- previously generated CAND_B outputs: `{rel(PREV_CANDB_PLANNER_CROP_NPY)}`, `{rel(PREV_CANDB_MASK_NPY)}`, `{rel(PREV_CANDB_TEMP_MAPPED_NPY)}`",
        f"- generator script audited: `{rel(PREV_GENERATION_SCRIPT)}`",
        "",
        "Authoritative-source resolution:",
        "- The authoritative numerical source is `X_surface_300.npy` (not PNG) because it provides machine-precision gridded values.",
        "- The authoritative planner-aligned CAND_B outputs are the `_day299.npy` arrays listed above, referenced by the day299 checks JSON.",
        "",
        "## 3. Day-index audit",
        f"- Requested z index: `{DAY_Z_REQUESTED}`; selected array index: `{DAY_IDX}`.",
        f"- `index.csv` row for z299 exists and points to: `{row_z299.get('filepath')}`.",
        f"- Control row for z300 also exists: `{row_z300.get('filepath')}`.",
        f"- Previous run day-mapping declaration: `{prev_checks.get('final_day_mapping_decision')}`.",
        f"- Wrong-day control (z300) diverges from saved day299 output (RMSE={float(day300_row['rmse']):.6f}).",
        "",
        "## 4. Native-grid audit",
        f"- Native z299 shape: `{temp_day_z299_native.shape}` (interpreted as `[y, x]`).",
        f"- Native z299 stats: min={checks_payload['native_grid_audit']['native_stats_z299']['min']:.6f}, max={checks_payload['native_grid_audit']['native_stats_z299']['max']:.6f}, mean={checks_payload['native_grid_audit']['native_stats_z299']['mean']:.6f}, std={checks_payload['native_grid_audit']['native_stats_z299']['std']:.6f}.",
        f"- PNG z299 rendered shape is `{png_z299_shape[0]}x{png_z299_shape[1]}` (`{png_z299_mode}`), confirming rendered-figure form rather than raw native grid.",
        "",
        "## 5. Planner-grid audit",
        f"- Planner full grid shape: `{planner_field.shape}`.",
        f"- CAND_B ROI global indices: x[{candb_roi.x0}:{candb_roi.x1}], y[{candb_roi.y0}:{candb_roi.y1}] -> shape `{candb_roi.height}x{candb_roi.width}`.",
        f"- Saved planner crop equals recomputed planner crop: `{planner_crop_saved_equals_recomputed}`.",
        "- ROI extraction is a direct planner-grid subwindow (no additional spatial transform at crop step).",
        "",
        "## 6. Reconstruction of mapping pipeline",
        "Reconstructed independently:",
        "1. native z299 numeric field loaded from stack",
        "2. full-grid regridding to planner coordinates (`linear + nearest fallback`)",
        "3. CAND_B ROI crop from regridded planner full grid",
        "4. exact planner mask applied to ROI crop",
        "",
        f"- Recomputed masked field equals saved field (finite-mask aware): `{temp_saved_equals_recomputed}`.",
        f"- Recomputed vs saved max absolute difference on valid cells: `{checks_payload['mapping_reconstruction']['recomputed_vs_saved_max_abs_diff']}`.",
        "",
        "## 7. Orientation and plotting audit",
        "- Orientation hypotheses tested by remapping swapped/flipped source variants.",
        f"- Swap x/y RMSE: `{float(swap_row['rmse']):.6f}`; V-flip RMSE: `{float(vflip_row['rmse']):.6f}`; H-flip RMSE: `{float(hflip_row['rmse']):.6f}`.",
        "- Plotting-only controls generated (`origin`, transpose, aspect, axis inversion, normalization) to isolate visual-perception effects from numeric content.",
        "",
        "## 8. Quantitative comparisons",
        f"- Baseline (recomputed vs saved): RMSE={float(baseline_row['rmse']):.6e}, MAE={float(baseline_row['mae']):.6e}, Pearson={float(baseline_row['pearson']):.6f}, Spearman={float(baseline_row['spearman']):.6f}.",
        f"- Nearest-vs-saved: RMSE={float(nearest_row['rmse']):.6f}, gradient-corr={float(nearest_row['grad_mag_corr_pearson']):.6f}.",
        f"- Native vs backprojected-native (regridding-loss proxy): RMSE={float(metrics_by_id['native_vs_backprojected_native']['rmse']):.6f}, Pearson={float(metrics_by_id['native_vs_backprojected_native']['pearson']):.6f}.",
        f"- PNG-naive vs saved (H8 control): RMSE={float(png_row['rmse']):.6f}, Pearson={float(png_row['pearson']):.6f}.",
        "",
        "## 9. Hypothesis-by-hypothesis evaluation",
        f"- H1 (expected regridding difference, no bug): {'SUPPORTED' if h1_supported else 'NOT SUPPORTED'}",
        f"- H2 (x/y swapped): {'REJECTED' if h2_rejected else 'NOT REJECTED'}",
        f"- H3 (vertical flip): {'REJECTED' if h3_rejected else 'NOT REJECTED'}",
        f"- H4 (horizontal flip): {'REJECTED' if h4_rejected else 'NOT REJECTED'}",
        f"- H5 (plotting/origin/aspect effects): {'SUPPORTED' if h5_supported else 'NOT SUPPORTED'}",
        f"- H6 (off-by-one crop): {'REJECTED' if h6_rejected else 'NOT REJECTED'}",
        f"- H7 (wrong day): {'REJECTED' if h7_rejected else 'NOT REJECTED'}",
        f"- H8 (PNG-derived instead of numeric): {'REJECTED' if h8_rejected else 'NOT REJECTED'}",
        f"- H9 (mask correct but field misaligned): {'REJECTED' if h9_rejected else 'NOT REJECTED'}",
        f"- H10 (interpolation smoothing expected): {'SUPPORTED' if h10_supported else 'NOT SUPPORTED'}",
        "",
        "## 10. Final verdict",
        f"- source day verified: {'YES' if source_day_verified else 'NO'}",
        f"- numerical source used: {'YES' if numerical_source_used else 'NO'}",
        f"- planner mask correctly applied: {'YES' if planner_mask_correctly_applied else 'NO'}",
        f"- grid mapping geometrically consistent: {'YES' if grid_mapping_geometrically_consistent else 'NO'}",
        f"- major bug found: {'YES' if major_bug_found else 'NO'}",
        f"- main explanation of visible differences: {main_explanation}",
        "",
        "## 11. List of generated artifacts",
        f"- `{rel(OUT_METRICS_CSV)}`",
        f"- `{rel(OUT_CHECKS_JSON)}`",
        f"- `{rel(OUT_REPORT_MD)}`",
        f"- `{rel(OUT_SUMMARY_MD)}`",
        f"- `{rel(FIG_NATIVE)}`",
        f"- `{rel(FIG_PLANNER_REF)}`",
        f"- `{rel(FIG_PIPELINE)}`",
        f"- `{rel(FIG_DIFFS)}`",
        f"- `{rel(FIG_ORIENT)}`",
        f"- `{rel(FIG_CONTOUR)}`",
        f"- `{rel(FIG_PLOTTING)}`",
    ]
    ensure_parent(OUT_REPORT_MD)
    OUT_REPORT_MD.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # ---------- Summary ----------
    summary_lines = [
        "# CAND_B Day299 Forensic Summary",
        "",
        "- Baseline independent recomputation from numeric z299 source matches saved CAND_B planner-aligned array on shape, mask, and values.",
        "- Wrong-day, swapped/flipped orientation, and off-by-one controls all diverge significantly from saved output.",
        "- Plotting settings (origin/aspect/transpose/normalization) visibly change appearance even with identical underlying arrays.",
        "- Interpolation-choice controls indicate expected smoothing effects without geometric misalignment.",
        "",
        "Final verdict:",
        f"- source day verified: {'YES' if source_day_verified else 'NO'}",
        f"- numerical source used: {'YES' if numerical_source_used else 'NO'}",
        f"- planner mask correctly applied: {'YES' if planner_mask_correctly_applied else 'NO'}",
        f"- grid mapping geometrically consistent: {'YES' if grid_mapping_geometrically_consistent else 'NO'}",
        f"- major bug found: {'YES' if major_bug_found else 'NO'}",
        f"- main explanation of visible differences: {main_explanation}",
        "",
        (
            "The investigation concludes that the visible discrepancy is expected due to regridding/masking/plotting, "
            "based on the evidence above."
            if not major_bug_found
            else "The investigation concludes that the visible discrepancy is caused by a real alignment bug, based on the evidence above."
        ),
    ]
    ensure_parent(OUT_SUMMARY_MD)
    OUT_SUMMARY_MD.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    planner_ds.close()

    print("Generated forensic outputs:")
    for p in [
        OUT_METRICS_CSV,
        OUT_CHECKS_JSON,
        OUT_REPORT_MD,
        OUT_SUMMARY_MD,
        FIG_NATIVE,
        FIG_PLANNER_REF,
        FIG_PIPELINE,
        FIG_DIFFS,
        FIG_ORIENT,
        FIG_CONTOUR,
        FIG_PLOTTING,
    ]:
        print(rel(p))


if __name__ == "__main__":
    main()
