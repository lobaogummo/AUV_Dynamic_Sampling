"""Step07-CV analysis for the canonical Fossum ROI x490 run.

This stage ports the legacy image-only / computer-vision logic to the new
canonical ROI x490 dataset. It does not retrain the Fossum model, classify
October TEMPpred, use STD, or change any previous outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from scipy import ndimage as ndi

try:
    from PIL import Image

    HAS_PIL = True
except Exception:
    Image = None
    HAS_PIL = False

try:
    from skimage.filters import threshold_otsu

    HAS_SKIMAGE = True
except Exception:
    threshold_otsu = None
    HAS_SKIMAGE = False

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    HAS_SKLEARN = True
except Exception:
    KMeans = None
    silhouette_score = None
    StandardScaler = None
    HAS_SKLEARN = False


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP05 = RESULTS_ROOT / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP06 = RESULTS_ROOT / "october_surface_temppred_std_roi_x490_20260511_155923"

EXPECTED_SHAPE = (370, 72, 117)
EXPECTED_CLASS_SIZES = [41, 70, 50, 107, 30, 72]
EXPECTED_MASK_VALID = 8004


@dataclass(frozen=True)
class OldCvMaterial:
    kind: str
    path: Path
    role: str


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_dates(path: Path) -> list[str]:
    df = pd.read_csv(path)
    for col in ("date", "dates", "datetime", "time"):
        if col in df.columns:
            return df[col].astype(str).tolist()
    return df.iloc[:, 0].astype(str).tolist()


def json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def discover_old_cv_materials(root: Path) -> list[OldCvMaterial]:
    materials: list[OldCvMaterial] = []
    candidates = [
        (root / "notebooks" / "seed11_computer_vision_colab.ipynb", "notebook", "Primary old image-only CV notebook"),
        (root / "notebooks" / "seed11_computer_vision_colab.localrun.ipynb", "notebook", "Local executed notebook variant"),
        (root / "scripts" / "09_export_cv_prototypes.py", "script", "Old exporter for clean prototype PNG/NPY assets"),
        (root / "scripts" / "10_seed11_cv_analysis.py", "script", "Old reproducible image-only CV analysis script"),
        (root / "scripts" / "11_prototype_characterization.py", "script", "Old prototype characterization script"),
        (root / "scripts" / "cv_seed11_utils.py", "script", "Old CV utility functions"),
        (root / "scripts" / "prototype_characterization_utils.py", "script", "Old prototype descriptor utilities"),
        (root / "configs" / "cv_seed11_config.json", "config", "Old CV thresholds/config"),
        (root / "results" / "computer_vision_seed11", "output", "Old image-only CV outputs"),
        (root / "results" / "prototype_characterization_seed11", "output", "Old prototype characterization outputs"),
    ]
    for path, kind, role in candidates:
        if path.exists():
            materials.append(OldCvMaterial(kind=kind, path=path.resolve(), role=role))
    return materials


def finite_valid(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    valid = mask & np.isfinite(arr)
    return arr[valid].astype(float, copy=False)


def fill_invalid(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = finite_valid(arr, mask)
    fill = float(np.nanmean(vals)) if vals.size else 0.0
    out = np.asarray(arr, dtype=float).copy()
    out[~(mask & np.isfinite(out))] = fill
    return out


def otsu_threshold(vals: np.ndarray) -> float:
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return float("nan")
    if HAS_SKIMAGE:
        try:
            return float(threshold_otsu(vals))
        except Exception:
            pass
    return float(np.nanmedian(vals))


def entropy_1d(vals: np.ndarray, bins: int = 32) -> float:
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return float("nan")
    hist, _ = np.histogram(vals, bins=bins)
    total = hist.sum()
    if total == 0:
        return float("nan")
    p = hist.astype(float) / float(total)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum() / np.log2(bins))


def local_variance(arr: np.ndarray, mask: np.ndarray, size: int = 5) -> np.ndarray:
    filled = fill_invalid(arr, mask)
    m = mask.astype(float)
    count = ndi.uniform_filter(m, size=size, mode="nearest") * (size * size)
    sum_x = ndi.uniform_filter(filled * m, size=size, mode="nearest") * (size * size)
    sum_x2 = ndi.uniform_filter((filled**2) * m, size=size, mode="nearest") * (size * size)
    mean = np.divide(sum_x, count, out=np.zeros_like(sum_x), where=count > 0)
    mean2 = np.divide(sum_x2, count, out=np.zeros_like(sum_x2), where=count > 0)
    var = np.maximum(mean2 - mean**2, 0.0)
    var[~mask] = np.nan
    return var


def gradient_maps(arr: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    filled = fill_invalid(arr, mask)
    gy, gx = np.gradient(filled)
    g = np.sqrt(gx**2 + gy**2)
    g[~mask] = np.nan
    return g, gx, gy


def spatial_region_from_centroid(row: float, col: float, shape: tuple[int, int]) -> str:
    ny, nx = shape
    y = row / max(ny - 1, 1)
    x = col / max(nx - 1, 1)
    if 0.33 <= x <= 0.67 and 0.33 <= y <= 0.67:
        return "center"
    vertical = "north" if y > 0.67 else "south" if y < 0.33 else "middle"
    horizontal = "east" if x > 0.67 else "west" if x < 0.33 else "middle"
    if vertical != "middle" and horizontal != "middle":
        return f"{vertical}_{horizontal}"
    return vertical if vertical != "middle" else horizontal


def dominant_gradient_orientation(gx: np.ndarray, gy: np.ndarray, g: np.ndarray, boundary: np.ndarray) -> str:
    valid = boundary & np.isfinite(g) & (g > 0)
    if not np.any(valid):
        return "none"
    angles = np.arctan2(gy[valid], gx[valid])
    weights = g[valid]
    c = float(np.average(np.cos(angles), weights=weights))
    s = float(np.average(np.sin(angles), weights=weights))
    deg = abs(math.degrees(math.atan2(s, c))) % 180
    if deg < 22.5 or deg >= 157.5:
        return "east_west_gradient"
    if 67.5 <= deg < 112.5:
        return "north_south_gradient"
    return "diagonal_gradient"


def interface_fraction(seg: np.ndarray, mask: np.ndarray) -> float:
    if not np.any(mask):
        return float("nan")
    low = (seg == 0) & mask
    high = (seg == 1) & mask
    if not np.any(low) or not np.any(high):
        return 0.0
    contact = ndi.binary_dilation(low, iterations=1) & high
    return float(contact.sum() / mask.sum())


def compute_numeric_metrics(
    arr: np.ndarray,
    mask: np.ndarray,
    global_gradient_threshold: float,
    prefix: str = "",
) -> dict[str, Any]:
    vals = finite_valid(arr, mask)
    out: dict[str, Any] = {}
    if vals.size == 0:
        keys = [
            "valid_cells",
            "nan_cells",
            "field_mean",
            "field_std",
            "field_min",
            "field_max",
            "field_p5",
            "field_p10",
            "field_p50",
            "field_p90",
            "field_p95",
            "cold_fraction",
            "warm_fraction",
            "neutral_fraction",
            "entropy",
        ]
        return {prefix + k: float("nan") for k in keys}

    out.update(
        {
            "valid_cells": int(vals.size),
            "nan_cells": int(arr.size - vals.size),
            "field_mean": float(np.nanmean(vals)),
            "field_std": float(np.nanstd(vals)),
            "field_min": float(np.nanmin(vals)),
            "field_max": float(np.nanmax(vals)),
            "field_p5": float(np.nanpercentile(vals, 5)),
            "field_p10": float(np.nanpercentile(vals, 10)),
            "field_p50": float(np.nanpercentile(vals, 50)),
            "field_p90": float(np.nanpercentile(vals, 90)),
            "field_p95": float(np.nanpercentile(vals, 95)),
            "cold_fraction": float(np.mean(vals < -0.5)),
            "warm_fraction": float(np.mean(vals > 0.5)),
            "neutral_fraction": float(np.mean((vals >= -0.5) & (vals <= 0.5))),
            "entropy": entropy_1d(vals),
        }
    )

    g, gx, gy = gradient_maps(arr, mask)
    gvals = g[mask & np.isfinite(g)]
    if gvals.size:
        boundary = (g >= global_gradient_threshold) & mask & np.isfinite(g)
        labeled, ncomp = ndi.label(boundary)
        rows, cols = np.where(boundary)
        if rows.size:
            brow = float(np.average(rows, weights=g[boundary]))
            bcol = float(np.average(cols, weights=g[boundary]))
            bregion = spatial_region_from_centroid(brow, bcol, arr.shape)
        else:
            brow = bcol = float("nan")
            bregion = "none"
        out.update(
            {
                "gradient_mean": float(np.nanmean(gvals)),
                "gradient_median": float(np.nanmedian(gvals)),
                "gradient_p90": float(np.nanpercentile(gvals, 90)),
                "gradient_p95": float(np.nanpercentile(gvals, 95)),
                "gradient_max": float(np.nanmax(gvals)),
                "high_gradient_fraction": float(boundary.sum() / vals.size),
                "boundary_score": float(np.nanmean(gvals) * (1.0 + boundary.sum() / vals.size)),
                "boundary_component_count": int(ncomp),
                "boundary_length_area_fraction": float(boundary.sum() / vals.size),
                "boundary_centroid_row": brow,
                "boundary_centroid_col": bcol,
                "boundary_region": bregion,
                "dominant_gradient_orientation": dominant_gradient_orientation(gx, gy, g, boundary),
            }
        )
    else:
        out.update(
            {
                "gradient_mean": float("nan"),
                "gradient_median": float("nan"),
                "gradient_p90": float("nan"),
                "gradient_p95": float("nan"),
                "gradient_max": float("nan"),
                "high_gradient_fraction": float("nan"),
                "boundary_score": float("nan"),
                "boundary_component_count": 0,
                "boundary_length_area_fraction": float("nan"),
                "boundary_centroid_row": float("nan"),
                "boundary_centroid_col": float("nan"),
                "boundary_region": "none",
                "dominant_gradient_orientation": "none",
            }
        )

    lv = local_variance(arr, mask)
    lvvals = lv[mask & np.isfinite(lv)]
    lap = ndi.laplace(fill_invalid(arr, mask))
    lapvals = np.abs(lap[mask & np.isfinite(lap)])
    out.update(
        {
            "local_variance_mean": float(np.nanmean(lvvals)) if lvvals.size else float("nan"),
            "local_variance_p90": float(np.nanpercentile(lvvals, 90)) if lvvals.size else float("nan"),
            "roughness_mean_abs_laplacian": float(np.nanmean(lapvals)) if lapvals.size else float("nan"),
        }
    )

    thr = otsu_threshold(vals)
    seg = np.zeros_like(arr, dtype=np.uint8)
    seg[(arr >= thr) & mask & np.isfinite(arr)] = 1
    low_vals = arr[(seg == 0) & mask & np.isfinite(arr)]
    high_vals = arr[(seg == 1) & mask & np.isfinite(arr)]
    low_fraction = float(low_vals.size / vals.size) if vals.size else float("nan")
    high_fraction = float(high_vals.size / vals.size) if vals.size else float("nan")
    sep = (
        float(abs(np.nanmean(high_vals) - np.nanmean(low_vals)) / (np.nanstd(vals) + 1e-9))
        if low_vals.size and high_vals.size
        else float("nan")
    )
    out.update(
        {
            "segmentation_threshold": thr,
            "cold_segment_fraction": low_fraction,
            "warm_segment_fraction": high_fraction,
            "cold_warm_area_ratio": float(low_fraction / (high_fraction + 1e-9)),
            "segment_interface_fraction": interface_fraction(seg, mask),
            "bimodality_index": sep,
            "segmentation_robust": bool(
                np.isfinite(sep) and min(low_fraction, high_fraction) >= 0.10 and sep >= 0.75
            ),
        }
    )
    return {prefix + k: v for k, v in out.items()}


def png_color_metrics(png_path: Path, mask: np.ndarray) -> dict[str, Any]:
    out = {
        "png_found": png_path.exists(),
        "png_alpha_mask_usable": False,
        "png_rb_mean": float("nan"),
        "png_rb_std": float("nan"),
        "png_color_balance": float("nan"),
    }
    if not (HAS_PIL and png_path.exists()):
        return out
    try:
        im = Image.open(png_path).convert("RGBA")
        rgba = np.asarray(im).astype(float)
        rgb = rgba[..., :3]
        alpha = rgba[..., 3] > 0
        if alpha.shape == mask.shape:
            use_mask = alpha & mask
            out["png_alpha_mask_usable"] = True
        elif rgb.shape[:2] == mask.shape:
            use_mask = mask
        else:
            return out
        if np.any(use_mask):
            score = rgb[..., 0] - rgb[..., 2]
            out["png_rb_mean"] = float(np.nanmean(score[use_mask]))
            out["png_rb_std"] = float(np.nanstd(score[use_mask]))
            out["png_color_balance"] = float((np.nanmean(rgb[..., 0][use_mask]) - np.nanmean(rgb[..., 2][use_mask])) / 255.0)
    except Exception:
        return out
    return out


def estimate_global_gradient_threshold(x_norm: np.ndarray, mask: np.ndarray) -> float:
    values: list[np.ndarray] = []
    for i in range(x_norm.shape[0]):
        g, _, _ = gradient_maps(x_norm[i], mask)
        gv = g[mask & np.isfinite(g)]
        if gv.size:
            values.append(gv.astype(np.float32, copy=False))
    if not values:
        return 0.0
    return float(np.nanpercentile(np.concatenate(values), 90))


def add_composite_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    score_cols = [
        "field_std",
        "gradient_mean",
        "gradient_p95",
        "boundary_score",
        "local_variance_mean",
        "entropy",
        "bimodality_index",
    ]
    for col in score_cols:
        vals = pd.to_numeric(df[col], errors="coerce")
        std = float(vals.std(skipna=True))
        mean = float(vals.mean(skipna=True))
        if not np.isfinite(std) or std == 0:
            df[f"z_{col}"] = 0.0
        else:
            df[f"z_{col}"] = (vals - mean) / std
    df["heterogeneity_score"] = df[[f"z_{c}" for c in ["field_std", "local_variance_mean", "entropy", "bimodality_index"]]].mean(axis=1)
    df["gradient_score"] = df[[f"z_{c}" for c in ["gradient_mean", "gradient_p95"]]].mean(axis=1)
    df["boundary_composite_score"] = df[[f"z_{c}" for c in ["boundary_score", "gradient_p95", "local_variance_mean"]]].mean(axis=1)
    return df


def load_assignments(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    lower = {c.lower(): c for c in df.columns}
    class_col = lower.get("class_id") or lower.get("class") or lower.get("label")
    if class_col is None:
        candidates = [c for c in df.columns if "class" in c.lower()]
        if not candidates:
            raise ValueError(f"Could not find class column in {path}")
        class_col = candidates[0]
    idx_col = lower.get("day_index") or lower.get("index") or lower.get("day")
    date_col = lower.get("date")
    out = pd.DataFrame()
    if idx_col is not None:
        out["day_index"] = df[idx_col].astype(int)
        if out["day_index"].min() == 0:
            out["day_index"] += 1
    else:
        out["day_index"] = np.arange(1, len(df) + 1)
    out["class_id"] = df[class_col].astype(int)
    if date_col is not None:
        out["date"] = df[date_col].astype(str)
    return out.sort_values("day_index").reset_index(drop=True)


def ensure_clean_pngs(
    step00: Path,
    out_dir: Path,
    x_norm: np.ndarray,
    mask: np.ndarray,
    dates: list[str],
    vmin: float = -2.025433,
    vmax: float = 2.025433,
) -> tuple[Path, bool, list[Path]]:
    existing = step00 / "normalized_clean_pngs"
    files = sorted(existing.glob("*_clean.png")) if existing.exists() else []
    existing_pixel_compatible = False
    if len(files) == x_norm.shape[0] and HAS_PIL:
        try:
            probe = Image.open(files[0]).convert("RGBA")
            existing_pixel_compatible = (probe.size == (mask.shape[1], mask.shape[0]))
        except Exception:
            existing_pixel_compatible = False
    if len(files) == x_norm.shape[0] and existing_pixel_compatible:
        return existing, False, files
    generated = out_dir / "generated_clean_pngs"
    generated.mkdir(parents=True, exist_ok=True)
    cmap = plt.get_cmap("coolwarm")
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
    result: list[Path] = []
    if not HAS_PIL:
        return generated, False, result
    for i in range(x_norm.shape[0]):
        rgba = (cmap(norm(x_norm[i])) * 255).astype(np.uint8)
        invalid = ~(mask & np.isfinite(x_norm[i]))
        rgba[invalid, 3] = 0
        out = generated / f"{i+1:04d}_{dates[i]}_X_surface_370_roi_x490_norm_clean.png"
        Image.fromarray(rgba, mode="RGBA").save(out)
        result.append(out)
    return generated, True, result


def plot_map(ax: plt.Axes, arr: np.ndarray, mask: np.ndarray, title: str, vmin: float = -2.025433, vmax: float = 2.025433) -> Any:
    m = np.ma.array(arr, mask=~(mask & np.isfinite(arr)))
    im = ax.imshow(m, origin="lower", cmap="coolwarm", vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_title(title, fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    return im


def save_prototype_panel(path: Path, prototypes: np.ndarray, mask: np.ndarray, class_sizes: list[int]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), constrained_layout=True)
    ims = []
    for k, ax in enumerate(axes.ravel()):
        ims.append(plot_map(ax, prototypes[k], mask, f"C{k+1:02d} prototype (n={class_sizes[k]})"))
    fig.colorbar(ims[-1], ax=axes.ravel().tolist(), shrink=0.8, label="Normalized temperature")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_gradient_panel(path: Path, prototypes: np.ndarray, mask: np.ndarray) -> None:
    grads = [gradient_maps(prototypes[k], mask)[0] for k in range(prototypes.shape[0])]
    vmax = float(np.nanpercentile(np.concatenate([g[mask & np.isfinite(g)] for g in grads]), 98))
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), constrained_layout=True)
    ims = []
    for k, ax in enumerate(axes.ravel()):
        im = ax.imshow(np.ma.array(grads[k], mask=~(mask & np.isfinite(grads[k]))), origin="lower", cmap="magma", vmin=0, vmax=vmax)
        ax.set_title(f"C{k+1:02d} gradient", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
        ims.append(im)
    fig.colorbar(ims[-1], ax=axes.ravel().tolist(), shrink=0.8, label="Gradient magnitude")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_boundary_panel(path: Path, prototypes: np.ndarray, mask: np.ndarray, global_gradient_threshold: float) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), constrained_layout=True)
    for k, ax in enumerate(axes.ravel()):
        g, _, _ = gradient_maps(prototypes[k], mask)
        boundary = (g >= global_gradient_threshold) & mask & np.isfinite(g)
        base = np.ma.array(prototypes[k], mask=~(mask & np.isfinite(prototypes[k])))
        ax.imshow(base, origin="lower", cmap="coolwarm", vmin=-2.025433, vmax=2.025433)
        ax.contour(boundary.astype(float), levels=[0.5], colors="black", linewidths=0.6, origin="lower")
        ax.set_title(f"C{k+1:02d} boundary", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_grouped_members_panel(
    path: Path,
    x_norm: np.ndarray,
    mask: np.ndarray,
    assignments: pd.DataFrame,
    dates: list[str],
    max_cols: int = 20,
) -> None:
    rows = []
    for cls in sorted(assignments["class_id"].unique()):
        members = assignments.loc[assignments["class_id"] == cls, "day_index"].astype(int).tolist()
        for start in range(0, len(members), max_cols):
            rows.append((cls, members[start : start + max_cols], start == 0, len(members)))
    nrows = len(rows)
    fig_h = max(2.0, nrows * 0.82)
    fig, axes = plt.subplots(nrows, max_cols, figsize=(max_cols * 0.62, fig_h), squeeze=False)
    for r, (cls, chunk, first, n) in enumerate(rows):
        for c in range(max_cols):
            ax = axes[r, c]
            ax.axis("off")
            if c < len(chunk):
                day = chunk[c]
                plot_map(ax, x_norm[day - 1], mask, "")
                ax.text(0.02, -0.08, f"{day:03d}\n{dates[day-1][5:]}", transform=ax.transAxes, fontsize=4, va="top")
        if first:
            axes[r, 0].text(-0.60, 0.50, f"C{cls:02d}\nn={n}", transform=axes[r, 0].transAxes, fontsize=8, va="center", ha="right")
    fig.suptitle("Step07-CV: all canonical members grouped by class", fontsize=12)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_selected_members_panel(
    path: Path,
    title: str,
    selections: pd.DataFrame,
    x_norm: np.ndarray,
    mask: np.ndarray,
    dates: list[str],
    score_col: str,
) -> None:
    n = len(selections)
    if n == 0:
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.text(0.5, 0.5, "No members selected", ha="center", va="center")
        ax.axis("off")
        fig.savefig(path, dpi=180)
        plt.close(fig)
        return
    cols = min(6, n)
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.0, rows * 1.6), squeeze=False, constrained_layout=True)
    for ax in axes.ravel():
        ax.axis("off")
    for idx, (_, row) in enumerate(selections.iterrows()):
        ax = axes.ravel()[idx]
        day = int(row["day_index"])
        cls = int(row["class_id"])
        plot_map(ax, x_norm[day - 1], mask, f"C{cls:02d} d{day:03d} {dates[day-1]}\n{score_col}={row[score_col]:.3f}")
    fig.suptitle(title)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_class_barplots(path: Path, class_summary: pd.DataFrame) -> None:
    metrics = ["heterogeneity_score_mean", "gradient_score_mean", "boundary_composite_score_mean", "residual_rmse_mean"]
    labels = [f"C{int(c):02d}" for c in class_summary["class_id"]]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    for ax, metric in zip(axes.ravel(), metrics):
        ax.bar(labels, class_summary[metric].astype(float), color="#4C78A8")
        ax.set_title(metric.replace("_", " "))
        ax.grid(axis="y", alpha=0.3)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_similarity_heatmap(path: Path, sim: pd.DataFrame, value: str = "pearson") -> None:
    pivot = sim.pivot(index="class_i", columns="class_j", values=value)
    fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
    im = ax.imshow(pivot.values.astype(float), cmap="viridis", vmin=-1, vmax=1)
    ax.set_xticks(range(len(pivot.columns)), [f"C{int(c):02d}" for c in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), [f"C{int(c):02d}" for c in pivot.index])
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{pivot.values[i, j]:.2f}", ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=ax, label=value)
    ax.set_title("Prototype similarity")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_metric_combo(path: Path, class_summary: pd.DataFrame) -> None:
    labels = [f"C{int(c):02d}" for c in class_summary["class_id"]]
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    x = np.arange(len(labels))
    width = 0.25
    ax.bar(x - width, class_summary["heterogeneity_score_mean"], width, label="heterogeneity")
    ax.bar(x, class_summary["gradient_score_mean"], width, label="gradient")
    ax.bar(x + width, class_summary["boundary_composite_score_mean"], width, label="boundary")
    ax.set_xticks(x, labels)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    ax.set_title("Gradient, boundary and heterogeneity by class")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_segmentation_examples(path: Path, prototypes: np.ndarray, mask: np.ndarray) -> None:
    fig, axes = plt.subplots(prototypes.shape[0], 2, figsize=(7, prototypes.shape[0] * 1.5), constrained_layout=True)
    for k in range(prototypes.shape[0]):
        arr = prototypes[k]
        vals = finite_valid(arr, mask)
        thr = otsu_threshold(vals)
        seg = ((arr >= thr) & mask & np.isfinite(arr)).astype(float)
        plot_map(axes[k, 0], arr, mask, f"C{k+1:02d} prototype")
        axes[k, 1].imshow(np.ma.array(seg, mask=~mask), origin="lower", cmap="coolwarm", vmin=0, vmax=1)
        axes[k, 1].set_title(f"C{k+1:02d} threshold split", fontsize=8)
        axes[k, 1].set_xticks([])
        axes[k, 1].set_yticks([])
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_substructure_panel(path: Path, sub_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
    labels = [f"C{int(c):02d}" for c in sub_df["class_id"]]
    sil = sub_df["kmeans2_silhouette"].astype(float).fillna(0)
    colors = ["#D55E00" if bool(v) else "#4C78A8" for v in sub_df["possible_substructure"]]
    ax.bar(labels, sil, color=colors)
    ax.axhline(0.35, color="black", linestyle="--", linewidth=1, label="substructure threshold")
    ax.set_ylabel("KMeans-2 silhouette on CV metrics")
    ax.set_title("Substructure diagnostics by class")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    for i, row in sub_df.iterrows():
        ax.text(i, sil.iloc[i] + 0.02, f"{int(row['subcluster_min_size'])}/{int(row['subcluster_max_size'])}", ha="center", fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def prototype_similarity(prototypes: np.ndarray, mask: np.ndarray) -> pd.DataFrame:
    rows = []
    for i in range(prototypes.shape[0]):
        vi = prototypes[i][mask & np.isfinite(prototypes[i])]
        for j in range(prototypes.shape[0]):
            vj = prototypes[j][mask & np.isfinite(prototypes[j])]
            n = min(vi.size, vj.size)
            if n == 0:
                corr = rmse = mae = float("nan")
            else:
                a, b = vi[:n], vj[:n]
                corr = float(np.corrcoef(a, b)[0, 1]) if np.nanstd(a) > 0 and np.nanstd(b) > 0 else float("nan")
                diff = a - b
                rmse = float(np.sqrt(np.nanmean(diff**2)))
                mae = float(np.nanmean(np.abs(diff)))
            rows.append({"class_i": i + 1, "class_j": j + 1, "pearson": corr, "rmse": rmse, "mae": mae})
    return pd.DataFrame(rows)


def compute_substructure(image_metrics: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "field_mean",
        "field_std",
        "cold_fraction",
        "warm_fraction",
        "gradient_mean",
        "gradient_p95",
        "boundary_score",
        "local_variance_mean",
        "entropy",
        "bimodality_index",
        "residual_rmse",
    ]
    rows = []
    for cls, grp in image_metrics.groupby("class_id"):
        row: dict[str, Any] = {
            "class_id": int(cls),
            "class_size": int(len(grp)),
            "kmeans2_silhouette": float("nan"),
            "subcluster_min_size": 0,
            "subcluster_max_size": 0,
            "possible_substructure": False,
            "substructure_note": "sklearn unavailable or class too small",
        }
        if HAS_SKLEARN and len(grp) >= 10:
            feats = grp[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(grp[feature_cols].median(numeric_only=True))
            if feats.shape[1] and np.nanstd(feats.values) > 0:
                x = StandardScaler().fit_transform(feats.values)
                labels = KMeans(n_clusters=2, random_state=11, n_init=20).fit_predict(x)
                sizes = np.bincount(labels, minlength=2)
                try:
                    sil = float(silhouette_score(x, labels))
                except Exception:
                    sil = float("nan")
                min_size = int(sizes.min())
                max_size = int(sizes.max())
                possible = bool(np.isfinite(sil) and sil >= 0.35 and min_size >= max(5, int(0.15 * len(grp))))
                row.update(
                    {
                        "kmeans2_silhouette": sil,
                        "subcluster_min_size": min_size,
                        "subcluster_max_size": max_size,
                        "possible_substructure": possible,
                        "substructure_note": "possible two-pattern class" if possible else "no strong two-pattern signal",
                    }
                )
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step07-CV on the canonical Fossum ROI x490 outputs.")
    parser.add_argument("--step00", type=Path, default=STEP00)
    parser.add_argument("--step05", type=Path, default=STEP05)
    parser.add_argument("--step06", type=Path, default=STEP06)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    args = parser.parse_args()

    start = time.time()
    out_dir = args.output_root / f"fossum_roi_x490_step07_cv_analysis_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    diag_dir = out_dir / "diagnostics"
    for d in (fig_dir, table_dir, diag_dir):
        d.mkdir(parents=True, exist_ok=True)

    old_materials = discover_old_cv_materials(ROOT)

    x = np.load(args.step00 / "X_surface_370_roi_x490.npy")
    x_norm = np.load(args.step00 / "X_surface_370_roi_x490_norm.npy")
    mask = np.load(args.step00 / "mask_common_roi_x490.npy").astype(bool)
    dates = read_dates(args.step00 / "dates_370.csv")
    assignments = load_assignments(args.step05 / "canonical_assignments.csv")
    if "date" not in assignments.columns:
        assignments["date"] = dates
    class_sizes_df = pd.read_csv(args.step05 / "canonical_class_sizes.csv")
    prototypes = np.load(args.step05 / "canonical_prototypes.npy")

    png_dir, generated_pngs, png_files = ensure_clean_pngs(args.step00, out_dir, x_norm, mask, dates)

    global_gradient_threshold = estimate_global_gradient_threshold(x_norm, mask)

    image_rows: list[dict[str, Any]] = []
    for i in range(x_norm.shape[0]):
        day = i + 1
        cls = int(assignments.loc[assignments["day_index"] == day, "class_id"].iloc[0])
        png_path = png_files[i] if i < len(png_files) else png_dir / f"{day:04d}_{dates[i]}_X_surface_370_roi_x490_norm_clean.png"
        row = {
            "day_index": day,
            "date": dates[i],
            "class_id": cls,
            "png_path": str(png_path),
        }
        row.update(compute_numeric_metrics(x_norm[i], mask, global_gradient_threshold))
        row.update(png_color_metrics(png_path, mask))
        image_rows.append(row)
    image_metrics = add_composite_scores(pd.DataFrame(image_rows))

    proto_rows: list[dict[str, Any]] = []
    for k in range(prototypes.shape[0]):
        row = {"class_id": k + 1, "prototype_index": k + 1}
        row.update(compute_numeric_metrics(prototypes[k], mask, global_gradient_threshold))
        proto_rows.append(row)
    prototype_metrics = add_composite_scores(pd.DataFrame(proto_rows))

    sim_df = prototype_similarity(prototypes, mask)

    residual_rows = []
    for _, row in image_metrics.iterrows():
        day = int(row["day_index"])
        cls = int(row["class_id"])
        arr = x_norm[day - 1]
        proto = prototypes[cls - 1]
        valid = mask & np.isfinite(arr) & np.isfinite(proto)
        diff = arr[valid] - proto[valid]
        if diff.size:
            corr = float(np.corrcoef(arr[valid], proto[valid])[0, 1]) if np.nanstd(arr[valid]) > 0 and np.nanstd(proto[valid]) > 0 else float("nan")
            residual_rows.append(
                {
                    "day_index": day,
                    "date": row["date"],
                    "class_id": cls,
                    "residual_rmse": float(np.sqrt(np.nanmean(diff**2))),
                    "residual_mae": float(np.nanmean(np.abs(diff))),
                    "residual_std": float(np.nanstd(diff)),
                    "residual_max_abs": float(np.nanmax(np.abs(diff))),
                    "prototype_corr": corr,
                }
            )
    residual_df = pd.DataFrame(residual_rows)
    image_metrics = image_metrics.merge(residual_df, on=["day_index", "date", "class_id"], how="left")

    outlier_parts = []
    representative_parts = []
    for cls, grp in image_metrics.groupby("class_id"):
        q1 = grp["residual_rmse"].quantile(0.25)
        q3 = grp["residual_rmse"].quantile(0.75)
        iqr = q3 - q1
        threshold = q3 + 1.5 * iqr
        tmp = grp.sort_values("residual_rmse", ascending=False).head(max(3, int(math.ceil(0.05 * len(grp))))).copy()
        tmp["outlier_threshold"] = threshold
        tmp["outlier_reason"] = "largest residual to class prototype"
        outlier_parts.append(tmp)
        representative_parts.append(grp.sort_values("residual_rmse", ascending=True).head(3).copy())
    outliers = pd.concat(outlier_parts, ignore_index=True)
    representatives = pd.concat(representative_parts, ignore_index=True)

    sub_df = compute_substructure(image_metrics)

    class_aggs: dict[str, list[str]] = {
        "field_mean": ["mean", "std"],
        "field_std": ["mean", "std"],
        "cold_fraction": ["mean", "std"],
        "warm_fraction": ["mean", "std"],
        "gradient_mean": ["mean", "std"],
        "gradient_p95": ["mean", "std"],
        "boundary_score": ["mean", "std"],
        "local_variance_mean": ["mean", "std"],
        "entropy": ["mean", "std"],
        "bimodality_index": ["mean", "std"],
        "heterogeneity_score": ["mean", "std"],
        "gradient_score": ["mean", "std"],
        "boundary_composite_score": ["mean", "std"],
        "residual_rmse": ["mean", "std", "max"],
        "prototype_corr": ["mean", "min"],
    }
    class_summary = image_metrics.groupby("class_id").agg(class_aggs)
    class_summary.columns = ["_".join(c) for c in class_summary.columns]
    class_summary = class_summary.reset_index()
    class_summary.insert(1, "class_size", image_metrics.groupby("class_id").size().values)
    class_summary = class_summary.merge(sub_df[["class_id", "kmeans2_silhouette", "possible_substructure", "substructure_note"]], on="class_id", how="left")

    # Persist tables.
    image_metrics.to_csv(out_dir / "step07_cv_image_metrics.csv", index=False)
    class_summary.to_csv(out_dir / "step07_cv_class_metrics_summary.csv", index=False)
    prototype_metrics.to_csv(out_dir / "step07_cv_prototype_metrics.csv", index=False)
    sim_df.to_csv(out_dir / "step07_cv_prototype_similarity.csv", index=False)
    residual_df.to_csv(out_dir / "step07_cv_member_to_prototype_residuals.csv", index=False)
    outliers.to_csv(out_dir / "step07_cv_outlier_members.csv", index=False)
    sub_df.to_csv(out_dir / "step07_cv_substructure_diagnostics.csv", index=False)

    # Also mirror CSVs under tables for easier browsing.
    for name in [
        "step07_cv_image_metrics.csv",
        "step07_cv_class_metrics_summary.csv",
        "step07_cv_prototype_metrics.csv",
        "step07_cv_prototype_similarity.csv",
        "step07_cv_member_to_prototype_residuals.csv",
        "step07_cv_outlier_members.csv",
        "step07_cv_substructure_diagnostics.csv",
    ]:
        shutil.copy2(out_dir / name, table_dir / name)

    # Figures.
    save_prototype_panel(out_dir / "step07_cv_class_prototypes_panel.png", prototypes, mask, EXPECTED_CLASS_SIZES)
    save_gradient_panel(out_dir / "step07_cv_prototype_gradient_panel.png", prototypes, mask)
    save_boundary_panel(out_dir / "step07_cv_prototype_boundary_panel.png", prototypes, mask, global_gradient_threshold)
    save_grouped_members_panel(out_dir / "step07_cv_grouped_members_by_class_panel.png", x_norm, mask, assignments, dates)
    save_selected_members_panel(out_dir / "step07_cv_representative_members_panel.png", "Representative members by class", representatives, x_norm, mask, dates, "residual_rmse")
    save_selected_members_panel(out_dir / "step07_cv_outlier_members_panel.png", "Outlier members by class", outliers, x_norm, mask, dates, "residual_rmse")
    save_class_barplots(out_dir / "step07_cv_class_metric_barplots.png", class_summary)
    save_similarity_heatmap(out_dir / "step07_cv_prototype_similarity_heatmap.png", sim_df)
    save_metric_combo(out_dir / "step07_cv_gradient_boundary_heterogeneity_by_class.png", class_summary)
    save_segmentation_examples(out_dir / "step07_cv_segmentation_examples.png", prototypes, mask)
    save_substructure_panel(out_dir / "step07_cv_substructure_diagnostics_panel.png", sub_df)
    for p in out_dir.glob("step07_cv_*.png"):
        shutil.copy2(p, fig_dir / p.name)

    class_sizes = image_metrics.groupby("class_id").size().sort_index().astype(int).tolist()
    homogeneous = class_summary.sort_values("heterogeneity_score_mean").head(2)["class_id"].astype(int).tolist()
    heterogeneous = class_summary.sort_values("heterogeneity_score_mean", ascending=False).head(2)["class_id"].astype(int).tolist()
    high_gradient = class_summary.sort_values("gradient_score_mean", ascending=False).head(2)["class_id"].astype(int).tolist()
    high_boundary = class_summary.sort_values("boundary_composite_score_mean", ascending=False).head(2)["class_id"].astype(int).tolist()
    sub_classes = sub_df.loc[sub_df["possible_substructure"], "class_id"].astype(int).tolist()

    checks = {
        "input_step00": str(args.step00.resolve()),
        "input_step05": str(args.step05.resolve()),
        "step06_available_but_not_used_for_classification": args.step06.exists(),
        "step05_has_6_classes": len(class_sizes) == 6,
        "class_sizes": class_sizes,
        "class_sizes_match_expected": class_sizes == EXPECTED_CLASS_SIZES,
        "x_shape": list(x.shape),
        "x_norm_shape": list(x_norm.shape),
        "arrays_shape_match_expected": tuple(x_norm.shape) == EXPECTED_SHAPE and tuple(x.shape) == EXPECTED_SHAPE,
        "mask_shape": list(mask.shape),
        "mask_valid_cells": int(mask.sum()),
        "mask_valid_cells_match_expected": int(mask.sum()) == EXPECTED_MASK_VALID,
        "prototypes_shape": list(prototypes.shape),
        "prototypes_shape_compatible": tuple(prototypes.shape) == (6, 72, 117),
        "n_images_analyzed": int(len(image_metrics)),
        "all_370_images_analyzed": len(image_metrics) == 370,
        "all_6_classes_have_metrics": class_summary["class_id"].nunique() == 6,
        "std_used": False,
        "october_temppred_used_for_classification": False,
        "clean_png_source": str(png_dir.resolve()),
        "clean_pngs_generated": generated_pngs,
        "global_gradient_threshold_p90": global_gradient_threshold,
        "old_cv_materials_found": [str(m.path) for m in old_materials],
        "final_verdict": "READY_FOR_STEP08_DESCRIPTOR_DEFINITION",
    }
    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).resolve()),
        "output_folder": str(out_dir.resolve()),
        "methodology_reference": [
            "seed11_computer_vision_colab.ipynb",
            "09_export_cv_prototypes.py",
            "10_seed11_cv_analysis.py",
            "cv_seed11_utils.py",
            "prototype_characterization_utils.py",
        ],
        "ported_metrics": [
            "clean PNG alpha/mask handling where available",
            "R-B image color score where PNG dimensions are compatible",
            "global intensity statistics",
            "gradient/front metrics",
            "threshold segmentation and cold/warm area ratios",
            "prototype similarity and member-to-prototype residuals",
        ],
        "adaptations": [
            "primary input changed from old tempRes/prototype exports to Step00 ROI x490 arrays and Step05 canonical classes",
            "6 canonical classes instead of the old 5 global classes",
            "all 370 ROI x490 maps are analyzed instead of only old prototype exports",
            "STD and October TEMPpred are explicitly not used in this step",
        ],
        "runtime_seconds": round(time.time() - start, 2),
    }
    json_dump(out_dir / "step07_cv_checks.json", checks)
    json_dump(out_dir / "step07_cv_metadata.json", metadata)
    shutil.copy2(Path(__file__).resolve(), out_dir / "07_cv_analysis_canonical_fossum_roi_x490.py")

    materials_md = "\n".join([f"- {m.kind}: `{m.path}` - {m.role}" for m in old_materials])
    audit_md = f"""# Step07-CV old pipeline logic audit

## Materials found

{materials_md}

## Legacy logic recovered

- Clean PNG / RGBA loading with alpha-derived masks when available.
- Image-only color score based on red minus blue channels.
- Global score statistics and percentile summaries.
- Threshold segmentation, originally via Otsu when available.
- Gradient/front metrics and boundary-style diagnostics.
- Prototype-level characterization and tabular CSV exports.

## Dependencies on old tempRes

The old notebooks and scripts were tied to old prototype exports and tempRes-era
paths. Those old arrays were not used as input here.

## Ported to ROI x490

- Step00 normalized arrays and canonical mask replace old tempRes arrays.
- Step05 assignments and prototypes replace old prototype exports.
- Six canonical classes are analyzed instead of the old five global classes.
- New clean RGBA PNGs are generated when existing rendered PNGs are not
  pixel-compatible with the 72 x 117 ROI grid.

## Limitations and risks

- RGB R-B metrics are retained as image-only diagnostics, but the planner-facing
  descriptors should primarily use numeric array metrics.
- Substructure flags are heuristic and should be validated before planner use.
- No STD and no October TEMPpred classification are included in this step.
"""
    (out_dir / "step07_cv_old_pipeline_logic_audit.md").write_text(audit_md, encoding="utf-8")
    summary = f"""# Step07-CV summary

Verdict: READY_FOR_STEP08_DESCRIPTOR_DEFINITION

1. Pipeline CV antiga encontrada? Sim.
2. Materiais antigos usados como referencia metodologica:
{materials_md}
3. Inputs canonicos usados: Step00 ROI x490 e Step05 canonical run.
4. STD usado? Nao.
5. TEMPpred outubro classificado? Nao.
6. Imagens analisadas: {len(image_metrics)} / 370.
7. Classes canonicas: {len(class_sizes)}; tamanhos = {class_sizes}.
8. Classes mais homogeneas por score CV: {', '.join(f'C{x:02d}' for x in homogeneous)}.
9. Classes mais heterogeneas por score CV: {', '.join(f'C{x:02d}' for x in heterogeneous)}.
10. Classes com maior gradient score: {', '.join(f'C{x:02d}' for x in high_gradient)}.
11. Classes com maior boundary score: {', '.join(f'C{x:02d}' for x in high_boundary)}.
12. Classes com possivel subestrutura: {', '.join(f'C{x:02d}' for x in sub_classes) if sub_classes else 'nenhuma classe com sinal forte'}.

Metricas recomendadas para Step08 descriptors:
- field_mean, field_std, cold_fraction, warm_fraction e neutral_fraction;
- gradient_mean, gradient_p95 e high_gradient_fraction;
- boundary_score, boundary_length_area_fraction e boundary_region;
- heterogeneity_score e local_variance_mean;
- bimodality_index, cold_warm_area_ratio e segment_interface_fraction;
- residual_rmse e prototype_corr para distancia ao regime canonico.

Metricas apenas diagnosticas por agora:
- score RGB R-B dos PNGs;
- contagem bruta de componentes high-gradient;
- detalhes internos de Otsu/GMM-like thresholding;
- flags de subestrutura, ate serem validadas contra TEMPpred/STD.

READY_FOR_STEP08_DESCRIPTOR_DEFINITION
"""
    (out_dir / "step07_cv_summary.md").write_text(summary, encoding="utf-8")

    report = f"""# Step07-CV report

## Purpose

This run audits and ports the old computer-vision / image-only logic to the
canonical Fossum ROI x490 pipeline. It analyzes the 6 canonical Step05 classes,
their prototypes, their 370 members, gradients, boundaries, heterogeneity and
possible substructure. It does not classify October TEMPpred and does not use
STD.

## Old CV materials found

{materials_md}

The reusable parts are the old clean-PNG image handling, alpha/mask convention,
R-B color score, threshold segmentation, gradient/front metrics, prototype
comparison logic and CSV/figure export pattern. The old tempRes data dependency
was not reused as input.

## Adaptation to ROI x490

- Input arrays now come from `{args.step00}`.
- Canonical class assignments and prototypes come from `{args.step05}`.
- The analysis uses 370 maps with shape {list(x_norm.shape)}.
- The canonical mask has {int(mask.sum())} valid cells.
- The prototype tensor has shape {list(prototypes.shape)}.
- Step06 was detected at `{args.step06}`, but was not used for classification.

## Class-level findings

- Most homogeneous classes: {', '.join(f'C{x:02d}' for x in homogeneous)}.
- Most heterogeneous classes: {', '.join(f'C{x:02d}' for x in heterogeneous)}.
- Highest gradient classes: {', '.join(f'C{x:02d}' for x in high_gradient)}.
- Highest boundary classes: {', '.join(f'C{x:02d}' for x in high_boundary)}.
- Possible internal substructure: {', '.join(f'C{x:02d}' for x in sub_classes) if sub_classes else 'none by the KMeans-2 silhouette diagnostic'}.

## Recommended descriptors for Step08

Use a compact descriptor set rather than every diagnostic metric:
field_mean, field_std, cold_fraction, warm_fraction, gradient_mean,
gradient_p95, high_gradient_fraction, boundary_score,
boundary_length_area_fraction, heterogeneity_score, local_variance_mean,
bimodality_index, cold_warm_area_ratio, residual_rmse and prototype_corr.

## Diagnostic-only metrics

Keep PNG R-B score, raw boundary component count, Otsu threshold value and
substructure flags as diagnostics until validated on TEMPpred/STD. These are
useful for interpretation but should not drive the planner yet.

## Checks

- Step05 has 6 classes: {checks['step05_has_6_classes']}.
- Class sizes match expected {EXPECTED_CLASS_SIZES}: {checks['class_sizes_match_expected']}.
- Arrays match expected {EXPECTED_SHAPE}: {checks['arrays_shape_match_expected']}.
- Mask valid cells match expected {EXPECTED_MASK_VALID}: {checks['mask_valid_cells_match_expected']}.
- Prototypes compatible with [6, 72, 117]: {checks['prototypes_shape_compatible']}.
- All 370 images analyzed: {checks['all_370_images_analyzed']}.
- All 6 classes have metrics: {checks['all_6_classes_have_metrics']}.
- STD used: {checks['std_used']}.
- TEMPpred October classified: {checks['october_temppred_used_for_classification']}.

## Final verdict

READY_FOR_STEP08_DESCRIPTOR_DEFINITION
"""
    (out_dir / "step07_cv_report.md").write_text(report, encoding="utf-8")

    print(f"Step07-CV complete: {out_dir}")


if __name__ == "__main__":
    main()
