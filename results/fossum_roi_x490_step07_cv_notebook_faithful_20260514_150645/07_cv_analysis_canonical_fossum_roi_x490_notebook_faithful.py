"""Notebook-faithful Step07-CV port for canonical Fossum ROI x490.

This script follows the old notebook:
notebooks/seed11_computer_vision_colab.ipynb

It intentionally avoids the broader descriptor-ready metrics from the first
Step07-CV attempt. The old notebook logic is:
- load prototype .npy plus _mask.npy files;
- validate shape and mask convention;
- split arrays into halves/quadrants;
- extract basic features;
- run the conservative simple array-based regime analysis;
- run the image-only clean-PNG regime analysis using alpha mask and R-B score;
- keep HSL as optional/exploratory only, not as an output classifier.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from scipy import ndimage as ndi

try:
    from skimage.filters import threshold_multiotsu, threshold_otsu

    HAS_SKIMAGE = True
except Exception:
    threshold_otsu = None
    threshold_multiotsu = None
    HAS_SKIMAGE = False


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP05 = RESULTS_ROOT / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"

SEED_ID = 11
EXPECTED_VMIN = -2.025433
EXPECTED_VMAX = 2.025433
EXPECTED_CMAP = "coolwarm"
EXPECTED_MASK_TRUE_IS_VALID = True

SIMPLE_SIGMA = 1.0
SIMPLE_RULES = {
    "homogeneous_std_max": 0.18,
    "homogeneous_p90_grad_max": 0.12,
    "homogeneous_front_area_max": 0.12,
    "multi_min_region_ratio_min": 0.18,
    "multi_inter_region_diff_min": 0.45,
    "multi_coherence_min": 0.65,
    "multi_front_area_ratio_min": 0.15,
    "multi_p90_grad_min": 0.16,
}

IMAGE_ONLY_RULES = {
    "homogeneous_std_low_max": 12.0,
    "homogeneous_min_region_tiny_max": 0.12,
    "homogeneous_inter_diff_low_max": 18.0,
    "homogeneous_std_mid_max": 28.0,
    "homogeneous_min_region_mid_max": 0.34,
    "homogeneous_inter_diff_mid_min": 35.0,
    "homogeneous_inter_diff_mid_max": 60.0,
    "homogeneous_p90_grad_mid_max": 0.66,
    "multi_min_region_ratio_min": 0.18,
    "multi_inter_region_diff_min": 60.0,
    "multi_color_crossing_inter_diff_min": 40.0,
    "multi_coherence_min": 0.65,
    "multi_p90_grad_min": 0.68,
}
IMAGE_ONLY_GRAD_SIGMA = 1.0

REGIME_LABEL_TEXT = {
    "homogeneous": "HOMOGENEO",
    "single_gradient": "GRADIENTE UNICO",
    "multi_regime": "MULTI-REGIME",
}
REGIME_LABEL_COLOR = {
    "homogeneous": "#2E7D32",
    "single_gradient": "#C62828",
    "multi_regime": "#1565C0",
}


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def df_as_plain_table(df: pd.DataFrame) -> str:
    return df.to_string(index=False)


def masked_mean(arr, mask):
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return float("nan")
    return float(np.nanmean(arr[valid]))


def masked_std(arr, mask):
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return float("nan")
    return float(np.nanstd(arr[valid]))


def split_halves(arr, mask):
    h, w = arr.shape
    h_mid = h // 2
    w_mid = w // 2
    return {
        "left": (arr[:, :w_mid], mask[:, :w_mid]),
        "right": (arr[:, w_mid:], mask[:, w_mid:]),
        "top": (arr[h_mid:, :], mask[h_mid:, :]),
        "bottom": (arr[:h_mid, :], mask[:h_mid, :]),
    }


def split_quadrants(arr, mask):
    h, w = arr.shape
    h_mid = h // 2
    w_mid = w // 2
    return {
        "Q1": (arr[h_mid:, :w_mid], mask[h_mid:, :w_mid]),
        "Q2": (arr[h_mid:, w_mid:], mask[h_mid:, w_mid:]),
        "Q3": (arr[:h_mid, :w_mid], mask[:h_mid, :w_mid]),
        "Q4": (arr[:h_mid, w_mid:], mask[:h_mid, w_mid:]),
    }


def masked_plot(arr, mask, title=None, ax=None, vmin=EXPECTED_VMIN, vmax=EXPECTED_VMAX, cmap=EXPECTED_CMAP, show_colorbar=False):
    arr_plot = arr.astype(np.float32, copy=True)
    arr_plot[~mask] = np.nan
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 3.5))
    im = ax.imshow(arr_plot, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    if title is not None:
        ax.set_title(title)
    ax.axis("off")
    if show_colorbar:
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return im


def load_prototype(arr_path, mask_path):
    arr = np.load(arr_path).astype(np.float32, copy=False)
    mask = np.load(mask_path).astype(bool, copy=False)
    if arr.shape != mask.shape:
        raise ValueError(f"Shape mismatch: arr={arr.shape}, mask={mask.shape} em {arr_path}")
    return arr, mask


def infer_mask_true_is_valid(samples_dict):
    scores = []
    for item in samples_dict.values():
        arr = item["arr"]
        mask = item["mask"]
        true_finite = float(np.mean(np.isfinite(arr[mask]))) if np.any(mask) else np.nan
        false_finite = float(np.mean(np.isfinite(arr[~mask]))) if np.any(~mask) else np.nan
        if np.isfinite(true_finite) and np.isfinite(false_finite):
            scores.append(true_finite - false_finite)
    if len(scores) == 0:
        return EXPECTED_MASK_TRUE_IS_VALID, np.nan
    mean_score = float(np.mean(scores))
    inferred_true_valid = mean_score >= 0.0
    return inferred_true_valid, mean_score


def extract_basic_features(prototype_name, arr, mask):
    halves = split_halves(arr, mask)
    mean_all = masked_mean(arr, mask)
    std_all = masked_std(arr, mask)
    mean_left = masked_mean(*halves["left"])
    mean_right = masked_mean(*halves["right"])
    mean_top = masked_mean(*halves["top"])
    mean_bottom = masked_mean(*halves["bottom"])
    return {
        "prototype_name": prototype_name,
        "mean": mean_all,
        "std": std_all,
        "mean_left": mean_left,
        "mean_right": mean_right,
        "mean_top": mean_top,
        "mean_bottom": mean_bottom,
        "contrast_lr": mean_left - mean_right,
        "contrast_tb": mean_top - mean_bottom,
    }


def get_valid_values(arr, mask):
    valid = mask & np.isfinite(arr)
    return arr[valid].astype(np.float32, copy=False)


def simple_prepare(arr, mask, sigma=1.0):
    arr_f = np.asarray(arr, dtype=np.float32)
    mask_b = np.asarray(mask, dtype=bool)
    valid = mask_b & np.isfinite(arr_f)
    smoothed = np.full(arr_f.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return smoothed
    w = valid.astype(np.float32)
    arr0 = np.where(valid, arr_f, 0.0).astype(np.float32, copy=False)
    if sigma is None or sigma <= 0:
        smoothed[valid] = arr0[valid]
    else:
        num = ndi.gaussian_filter(arr0 * w, sigma=float(sigma), mode="nearest")
        den = ndi.gaussian_filter(w, sigma=float(sigma), mode="nearest")
        ok = den > 1e-6
        smoothed[ok] = (num[ok] / den[ok]).astype(np.float32, copy=False)
    smoothed[~mask_b] = np.nan
    return smoothed


def simple_global_metrics(arr_smooth, mask):
    vals = get_valid_values(arr_smooth, mask)
    if vals.size == 0:
        return {"std_temp": float("nan"), "iqr_temp": float("nan"), "range_temp": float("nan")}
    p25, p75 = np.percentile(vals, [25, 75])
    return {
        "std_temp": float(np.nanstd(vals)),
        "iqr_temp": float(p75 - p25),
        "range_temp": float(np.nanmax(vals) - np.nanmin(vals)),
    }


def otsu_segmentation(arr_smooth, mask):
    vals = get_valid_values(arr_smooth, mask)
    labels = np.full(arr_smooth.shape, -1, dtype=np.int8)
    region_low = np.zeros(arr_smooth.shape, dtype=bool)
    region_high = np.zeros(arr_smooth.shape, dtype=bool)
    if vals.size == 0:
        return {"threshold": float("nan"), "threshold_method": "empty", "labels": labels, "region_low": region_low, "region_high": region_high}
    threshold_method = "mean_fallback"
    threshold = float(np.nanmean(vals))
    if HAS_SKIMAGE and threshold_otsu is not None and np.unique(vals).size > 1:
        try:
            threshold = float(threshold_otsu(vals))
            threshold_method = "otsu"
        except Exception:
            threshold_method = "mean_fallback"
    valid = mask & np.isfinite(arr_smooth)
    region_low = valid & (arr_smooth < threshold)
    region_high = valid & (~region_low)
    labels[region_low] = 0
    labels[region_high] = 1
    return {"threshold": threshold, "threshold_method": threshold_method, "labels": labels, "region_low": region_low, "region_high": region_high}


def optional_multiotsu_thresholds(arr_smooth, mask, classes=3):
    vals = get_valid_values(arr_smooth, mask)
    if not HAS_SKIMAGE or threshold_multiotsu is None or vals.size < classes or np.unique(vals).size < classes:
        return None
    try:
        return [float(x) for x in threshold_multiotsu(vals, classes=classes)]
    except Exception:
        return None


def largest_component_ratio(binary_region):
    region = np.asarray(binary_region, dtype=bool)
    total = int(region.sum())
    if total == 0:
        return 0.0
    comp_map, n_comp = ndi.label(region)
    if n_comp == 0:
        return 0.0
    comp_sizes = np.bincount(comp_map.ravel())[1:]
    if comp_sizes.size == 0:
        return 0.0
    return float(int(comp_sizes.max()) / total)


def region_metrics(arr_smooth, mask, region_low, region_high):
    valid = mask & np.isfinite(arr_smooth)
    n_valid = int(valid.sum())
    if n_valid == 0:
        return {
            "low_ratio": float("nan"),
            "high_ratio": float("nan"),
            "min_region_ratio": float("nan"),
            "inter_region_diff": float("nan"),
            "coherence_low": float("nan"),
            "coherence_high": float("nan"),
            "coherence_min": float("nan"),
        }
    n_low = int(region_low.sum())
    n_high = int(region_high.sum())
    low_ratio = float(n_low / n_valid)
    high_ratio = float(n_high / n_valid)
    min_region_ratio = float(min(low_ratio, high_ratio))
    mean_low = float(np.nanmean(arr_smooth[region_low])) if n_low > 0 else float("nan")
    mean_high = float(np.nanmean(arr_smooth[region_high])) if n_high > 0 else float("nan")
    inter_region_diff = float(abs(mean_high - mean_low)) if np.isfinite(mean_low) and np.isfinite(mean_high) else 0.0
    coherence_low = float(largest_component_ratio(region_low))
    coherence_high = float(largest_component_ratio(region_high))
    coherence_min = float(min(coherence_low, coherence_high))
    return {
        "low_ratio": low_ratio,
        "high_ratio": high_ratio,
        "min_region_ratio": min_region_ratio,
        "inter_region_diff": inter_region_diff,
        "coherence_low": coherence_low,
        "coherence_high": coherence_high,
        "coherence_min": coherence_min,
    }


def simple_front_metrics(arr_smooth, mask):
    valid = mask & np.isfinite(arr_smooth)
    grad_mag = np.full(arr_smooth.shape, np.nan, dtype=np.float32)
    front_binary = np.zeros(arr_smooth.shape, dtype=bool)
    if not np.any(valid):
        return {"mean_grad": float("nan"), "p90_grad": float("nan"), "front_area_ratio": float("nan"), "grad_mag": grad_mag, "front_binary": front_binary}
    fill_value = float(np.nanmean(arr_smooth[valid]))
    arr_for_grad = np.where(valid, arr_smooth, fill_value).astype(np.float32, copy=False)
    gy, gx = np.gradient(arr_for_grad)
    grad = np.hypot(gx, gy).astype(np.float32, copy=False)
    grad[~valid] = np.nan
    grad_mag = grad
    gvals = grad_mag[valid]
    mean_grad = float(np.nanmean(gvals))
    p90_grad = float(np.percentile(gvals, 90))
    front_binary = valid & (grad_mag >= p90_grad)
    front_area_ratio = float(front_binary.sum() / valid.sum())
    return {"mean_grad": mean_grad, "p90_grad": p90_grad, "front_area_ratio": front_area_ratio, "grad_mag": grad_mag, "front_binary": front_binary}


def extract_simple_regime_metrics(prototype_name, arr, mask, sigma=1.0):
    arr_smooth = simple_prepare(arr, mask, sigma=sigma)
    gm = simple_global_metrics(arr_smooth, mask)
    seg = otsu_segmentation(arr_smooth, mask)
    rm = region_metrics(arr_smooth, mask, seg["region_low"], seg["region_high"])
    fm = simple_front_metrics(arr_smooth, mask)
    row = {
        "prototype_name": prototype_name,
        "sigma": float(sigma),
        "threshold": float(seg["threshold"]) if np.isfinite(seg["threshold"]) else float("nan"),
        "std_temp": gm["std_temp"],
        "iqr_temp": gm["iqr_temp"],
        "range_temp": gm["range_temp"],
        "low_ratio": rm["low_ratio"],
        "high_ratio": rm["high_ratio"],
        "min_region_ratio": rm["min_region_ratio"],
        "inter_region_diff": rm["inter_region_diff"],
        "coherence_low": rm["coherence_low"],
        "coherence_high": rm["coherence_high"],
        "coherence_min": rm["coherence_min"],
        "mean_grad": fm["mean_grad"],
        "p90_grad": fm["p90_grad"],
        "front_area_ratio": fm["front_area_ratio"],
        "threshold_method": seg["threshold_method"],
        "multiotsu_thresholds": optional_multiotsu_thresholds(arr_smooth, mask, classes=3),
    }
    aux = {
        "arr_smooth": arr_smooth,
        "labels": seg["labels"],
        "region_low": seg["region_low"],
        "region_high": seg["region_high"],
        "grad_mag": fm["grad_mag"],
        "front_binary": fm["front_binary"],
    }
    return row, aux


def decide_regime_label_simple(row, rules=SIMPLE_RULES):
    std_temp = float(row.get("std_temp", np.nan))
    p90_grad = float(row.get("p90_grad", np.nan))
    front_area_ratio = float(row.get("front_area_ratio", np.nan))
    min_region_ratio = float(row.get("min_region_ratio", np.nan))
    inter_region_diff = float(row.get("inter_region_diff", np.nan))
    coherence_min = float(row.get("coherence_min", np.nan))
    homogeneous = (
        std_temp < rules["homogeneous_std_max"]
        and p90_grad < rules["homogeneous_p90_grad_max"]
        and front_area_ratio < rules["homogeneous_front_area_max"]
    )
    if homogeneous:
        return "homogeneous"
    multi_regime = (
        min_region_ratio >= rules["multi_min_region_ratio_min"]
        and inter_region_diff >= rules["multi_inter_region_diff_min"]
        and coherence_min >= rules["multi_coherence_min"]
        and front_area_ratio >= rules["multi_front_area_ratio_min"]
        and p90_grad >= rules["multi_p90_grad_min"]
    )
    if multi_regime:
        return "multi_regime"
    return "single_gradient"


def load_clean_png_rgba(png_path):
    png_path = Path(png_path)
    img = cv2.imread(str(png_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not read PNG: {png_path}")
    if img.ndim == 2:
        rgb = np.stack([img, img, img], axis=-1)
        alpha = np.full(img.shape, 255, dtype=np.uint8)
    elif img.ndim == 3 and img.shape[2] == 4:
        rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        rgb = rgba[..., :3]
        alpha = rgba[..., 3]
    elif img.ndim == 3 and img.shape[2] == 3:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)
    else:
        raise ValueError(f"Unsupported PNG shape for {png_path}: {img.shape}")
    rgb = rgb.astype(np.float32, copy=False)
    alpha = alpha.astype(np.uint8, copy=False)
    mask = alpha > 0
    return rgb, alpha, mask


def color_score_rb(rgb, mask):
    score = rgb[..., 0].astype(np.float32) - rgb[..., 2].astype(np.float32)
    score = score.astype(np.float32, copy=False)
    score[~mask] = np.nan
    return score


def score_global_metrics(score, mask):
    vals = score[mask & np.isfinite(score)]
    if vals.size == 0:
        return {
            "std_temp": float("nan"),
            "iqr_temp": float("nan"),
            "range_temp": float("nan"),
            "score_mean": float("nan"),
            "score_min": float("nan"),
            "score_max": float("nan"),
        }
    p25, p75 = np.percentile(vals, [25, 75])
    return {
        "std_temp": float(np.nanstd(vals)),
        "iqr_temp": float(p75 - p25),
        "range_temp": float(np.nanmax(vals) - np.nanmin(vals)),
        "score_mean": float(np.nanmean(vals)),
        "score_min": float(np.nanmin(vals)),
        "score_max": float(np.nanmax(vals)),
    }


def otsu_on_color_score(score, mask):
    valid = mask & np.isfinite(score)
    vals = score[valid]
    labels = np.full(score.shape, -1, dtype=np.int8)
    region_low = np.zeros(score.shape, dtype=bool)
    region_high = np.zeros(score.shape, dtype=bool)
    if vals.size == 0:
        return {"threshold": float("nan"), "threshold_method": "empty", "labels": labels, "region_low": region_low, "region_high": region_high}
    threshold = float(np.nanmean(vals))
    threshold_method = "mean_fallback"
    if HAS_SKIMAGE and threshold_otsu is not None and np.unique(vals).size > 1:
        try:
            threshold = float(threshold_otsu(vals))
            threshold_method = "otsu"
        except Exception:
            threshold_method = "mean_fallback"
    region_low = valid & (score < threshold)
    region_high = valid & (~region_low)
    labels[region_low] = 0
    labels[region_high] = 1
    return {"threshold": threshold, "threshold_method": threshold_method, "labels": labels, "region_low": region_low, "region_high": region_high}


def region_metrics_from_score(score, mask, region_low, region_high):
    valid = mask & np.isfinite(score)
    n_valid = int(valid.sum())
    if n_valid == 0:
        return {
            "low_ratio": float("nan"),
            "high_ratio": float("nan"),
            "min_region_ratio": float("nan"),
            "inter_region_diff": float("nan"),
            "coherence_low": float("nan"),
            "coherence_high": float("nan"),
            "coherence_min": float("nan"),
        }
    n_low = int(region_low.sum())
    n_high = int(region_high.sum())
    low_ratio = float(n_low / n_valid)
    high_ratio = float(n_high / n_valid)
    min_region_ratio = float(min(low_ratio, high_ratio))
    mean_low = float(np.nanmean(score[region_low])) if n_low > 0 else float("nan")
    mean_high = float(np.nanmean(score[region_high])) if n_high > 0 else float("nan")
    inter_region_diff = float(abs(mean_high - mean_low)) if np.isfinite(mean_low) and np.isfinite(mean_high) else 0.0
    coherence_low = float(largest_component_ratio(region_low))
    coherence_high = float(largest_component_ratio(region_high))
    coherence_min = float(min(coherence_low, coherence_high))
    return {
        "low_ratio": low_ratio,
        "high_ratio": high_ratio,
        "min_region_ratio": min_region_ratio,
        "inter_region_diff": inter_region_diff,
        "coherence_low": coherence_low,
        "coherence_high": coherence_high,
        "coherence_min": coherence_min,
    }


def image_front_metrics(score, mask, grad_sigma=IMAGE_ONLY_GRAD_SIGMA):
    valid = mask & np.isfinite(score)
    grad_mag = np.full(score.shape, np.nan, dtype=np.float32)
    front_binary = np.zeros(score.shape, dtype=bool)
    if not np.any(valid):
        return {"mean_grad": float("nan"), "p90_grad": float("nan"), "front_area_ratio": float("nan"), "grad_mag": grad_mag, "front_binary": front_binary}
    score_for_grad = np.asarray(score, dtype=np.float32)
    if grad_sigma is not None and grad_sigma > 0:
        w = valid.astype(np.float32)
        s0 = np.where(valid, score_for_grad, 0.0).astype(np.float32, copy=False)
        num = ndi.gaussian_filter(s0 * w, sigma=float(grad_sigma), mode="nearest")
        den = ndi.gaussian_filter(w, sigma=float(grad_sigma), mode="nearest")
        ok = den > 1e-6
        smoothed = np.full(score.shape, np.nan, dtype=np.float32)
        smoothed[ok] = (num[ok] / den[ok]).astype(np.float32, copy=False)
        score_for_grad = smoothed
    fill_value = float(np.nanmean(score_for_grad[valid]))
    score_pad = np.where(valid, score_for_grad, fill_value).astype(np.float32, copy=False)
    gy, gx = np.gradient(score_pad)
    grad = np.hypot(gx, gy).astype(np.float32, copy=False)
    grad[~valid] = np.nan
    grad_mag = grad
    gvals = grad_mag[valid]
    mean_grad = float(np.nanmean(gvals))
    positive = gvals[gvals > 0]
    if positive.size == 0:
        p90_grad = 0.0
        front_area_ratio = 0.0
    else:
        p90_grad = float(np.percentile(positive, 90))
        front_binary = valid & (grad_mag >= p90_grad)
        front_area_ratio = float(front_binary.sum() / valid.sum())
    return {"mean_grad": mean_grad, "p90_grad": p90_grad, "front_area_ratio": front_area_ratio, "grad_mag": grad_mag, "front_binary": front_binary}


def extract_image_only_metrics(prototype_name, clean_png_path):
    rgb, alpha, mask = load_clean_png_rgba(clean_png_path)
    score = color_score_rb(rgb, mask)
    gm = score_global_metrics(score, mask)
    seg = otsu_on_color_score(score, mask)
    rm = region_metrics_from_score(score, mask, seg["region_low"], seg["region_high"])
    fm = image_front_metrics(score, mask, grad_sigma=IMAGE_ONLY_GRAD_SIGMA)
    row = {
        "prototype_name": prototype_name,
        "clean_png_path": str(clean_png_path),
        "grad_sigma": float(IMAGE_ONLY_GRAD_SIGMA),
        "threshold": float(seg["threshold"]) if np.isfinite(seg["threshold"]) else float("nan"),
        "threshold_method": seg["threshold_method"],
        "std_temp": gm["std_temp"],
        "iqr_temp": gm["iqr_temp"],
        "range_temp": gm["range_temp"],
        "score_mean": gm["score_mean"],
        "score_min": gm["score_min"],
        "score_max": gm["score_max"],
        "low_ratio": rm["low_ratio"],
        "high_ratio": rm["high_ratio"],
        "min_region_ratio": rm["min_region_ratio"],
        "inter_region_diff": rm["inter_region_diff"],
        "coherence_low": rm["coherence_low"],
        "coherence_high": rm["coherence_high"],
        "coherence_min": rm["coherence_min"],
        "mean_grad": fm["mean_grad"],
        "p90_grad": fm["p90_grad"],
        "front_area_ratio": fm["front_area_ratio"],
    }
    aux = {
        "rgb": rgb,
        "alpha": alpha,
        "mask": mask,
        "score": score,
        "labels": seg["labels"],
        "region_low": seg["region_low"],
        "region_high": seg["region_high"],
        "grad_mag": fm["grad_mag"],
        "front_binary": fm["front_binary"],
    }
    return row, aux


def decide_regime_label_image_only(row, rules=IMAGE_ONLY_RULES):
    std_temp = float(row.get("std_temp", np.nan))
    min_region_ratio = float(row.get("min_region_ratio", np.nan))
    inter_region_diff = float(row.get("inter_region_diff", np.nan))
    coherence_min = float(row.get("coherence_min", np.nan))
    p90_grad = float(row.get("p90_grad", np.nan))
    score_min = float(row.get("score_min", np.nan))
    score_max = float(row.get("score_max", np.nan))
    homogeneous_low_spread = (
        std_temp < rules["homogeneous_std_low_max"]
        and (min_region_ratio < rules["homogeneous_min_region_tiny_max"] or inter_region_diff < rules["homogeneous_inter_diff_low_max"])
    )
    homogeneous_mid_profile = (
        std_temp < rules["homogeneous_std_mid_max"]
        and min_region_ratio < rules["homogeneous_min_region_mid_max"]
        and rules["homogeneous_inter_diff_mid_min"] <= inter_region_diff <= rules["homogeneous_inter_diff_mid_max"]
        and p90_grad <= rules["homogeneous_p90_grad_mid_max"]
    )
    if homogeneous_low_spread or homogeneous_mid_profile:
        return "homogeneous"
    strong_multi_regime = (
        min_region_ratio >= rules["multi_min_region_ratio_min"]
        and inter_region_diff >= rules["multi_inter_region_diff_min"]
        and coherence_min >= rules["multi_coherence_min"]
        and p90_grad >= rules["multi_p90_grad_min"]
    )
    color_crossing_multi_regime = (
        score_min < 0.0 < score_max
        and min_region_ratio >= rules["multi_min_region_ratio_min"]
        and inter_region_diff >= rules["multi_color_crossing_inter_diff_min"]
        and coherence_min >= rules["multi_coherence_min"]
        and p90_grad >= rules["multi_p90_grad_min"]
    )
    if strong_multi_regime or color_crossing_multi_regime:
        return "multi_regime"
    return "single_gradient"


def export_prototypes_as_notebook_inputs(out_dir: Path, prototypes: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
    global_dir = out_dir / "notebook_style_exports" / "global"
    global_dir.mkdir(parents=True, exist_ok=True)
    cmap = plt.get_cmap(EXPECTED_CMAP)
    norm = plt.Normalize(vmin=EXPECTED_VMIN, vmax=EXPECTED_VMAX, clip=True)
    records = []
    for i in range(prototypes.shape[0]):
        name = f"prototype_class_{i+1:02d}"
        arr = prototypes[i].astype(np.float32, copy=False)
        arr_path = global_dir / f"{name}.npy"
        mask_path = global_dir / f"{name}_mask.npy"
        png_path = global_dir / f"{name}_clean.png"
        np.save(arr_path, arr)
        np.save(mask_path, mask.astype(bool, copy=False))
        rgba = (cmap(norm(arr)) * 255).astype(np.uint8)
        rgba[~(mask & np.isfinite(arr)), 3] = 0
        cv2.imwrite(str(png_path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        records.append({"name": name, "arr_path": arr_path, "mask_path": mask_path, "clean_png_path": png_path, "scope": "global"})
    return records


def _rgba_display(rgb, mask):
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb / 255.0, 0.0, 1.0)
    rgba[..., 3] = mask.astype(np.float32)
    return rgba


def _add_badge(ax, regime_label):
    text = REGIME_LABEL_TEXT.get(regime_label, regime_label)
    color = REGIME_LABEL_COLOR.get(regime_label, "#555555")
    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="white",
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", facecolor=color, edgecolor="none", alpha=0.92),
    )


def plot_global_prototypes(global_data: dict[str, Any], out_path: Path) -> None:
    names = sorted(global_data.keys())
    cols = min(3, len(names))
    rows = math.ceil(len(names) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.0 * cols, 3.2 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for i, name in enumerate(names):
        ax = axes.ravel()[i]
        item = global_data[name]
        masked_plot(item["arr"], item["mask"], title=name, ax=ax)
    fig.suptitle(f"Global prototypes | seed {SEED_ID}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_split_examples(global_data: dict[str, Any], out_dir: Path) -> None:
    example_name = sorted(global_data.keys())[0]
    arr = global_data[example_name]["arr"]
    mask = global_data[example_name]["mask"]
    halves = split_halves(arr, mask)
    quadrants = split_quadrants(arr, mask)
    fig, axes = plt.subplots(1, 5, figsize=(22, 4))
    masked_plot(arr, mask, title=f"{example_name} (original)", ax=axes[0])
    for ax, key in zip(axes[1:], ["left", "right", "top", "bottom"]):
        masked_plot(*halves[key], title=key, ax=ax)
    fig.tight_layout()
    fig.savefig(out_dir / "notebook_halves_example.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, key in zip(axes.ravel(), ["Q1", "Q2", "Q3", "Q4"]):
        masked_plot(*quadrants[key], title=key, ax=ax)
    fig.suptitle(f"Quadrants for {example_name}", y=1.02)
    fig.tight_layout()
    fig.savefig(out_dir / "notebook_quadrants_example.png", dpi=160)
    plt.close(fig)


def plot_simple_grid(df: pd.DataFrame, aux_dict: dict[str, Any], global_data: dict[str, Any], out_path: Path) -> None:
    keys = list(df["prototype_name"])
    n = len(keys)
    cols = min(4, max(1, n))
    row_blocks = math.ceil(n / cols)
    total_rows = row_blocks * 2
    fig, axes = plt.subplots(total_rows, cols, figsize=(4.8 * cols, 3.2 * total_rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for i, key in enumerate(keys):
        block = i // cols
        col = i % cols
        top = block * 2
        bottom = top + 1
        item = global_data[key]
        res = aux_dict[key]
        label = str(df.loc[df["prototype_name"] == key, "regime_label"].iloc[0])
        masked_plot(item["arr"], item["mask"], title=key, ax=axes[top][col])
        masked_plot(item["arr"], item["mask"], title="Simple final", ax=axes[bottom][col])
        if label == "multi_regime":
            region_map = np.full(item["mask"].shape, np.nan, dtype=np.float32)
            region_map[res["region_low"]] = 0.0
            region_map[res["region_high"]] = 1.0
            axes[bottom][col].imshow(region_map, origin="lower", cmap=ListedColormap(["#3A86FF", "#FF8C42"]), vmin=0, vmax=1, alpha=0.40, aspect="auto")
        _add_badge(axes[bottom][col], label)
    fig.suptitle(f"Simple arr+mask | global prototypes | seed {SEED_ID} | original (top) vs result (bottom)", y=1.01)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def show_image_only_original(ax, res, title):
    ax.imshow(_rgba_display(res["rgb"], res["mask"]), origin="lower", aspect="auto")
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def show_image_only_result(ax, res, title):
    rgb = res["rgb"]
    mask = res["mask"]
    regime_label = res["regime_label"]
    ax.imshow(_rgba_display(rgb, mask), origin="lower", aspect="auto")
    if regime_label == "multi_regime":
        region_map = np.full(mask.shape, np.nan, dtype=np.float32)
        region_map[res["region_low"]] = 0.0
        region_map[res["region_high"]] = 1.0
        ax.imshow(region_map, origin="lower", cmap=ListedColormap(["#3A86FF", "#FF8C42"]), vmin=0, vmax=1, alpha=0.40, aspect="auto")
    _add_badge(ax, regime_label)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def plot_image_only_grid(df, aux_dict, key_col, figure_title, out_path: Path):
    keys = list(df[key_col])
    n = len(keys)
    cols = min(4, max(1, n))
    row_blocks = math.ceil(n / cols)
    total_rows = row_blocks * 2
    fig, axes = plt.subplots(total_rows, cols, figsize=(4.8 * cols, 3.2 * total_rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for i, key in enumerate(keys):
        block = i // cols
        col = i % cols
        top = block * 2
        bottom = top + 1
        res = aux_dict[key]
        show_image_only_original(axes[top][col], res, title=str(key))
        show_image_only_result(axes[bottom][col], res, title="Image-only final")
    fig.suptitle(figure_title, y=1.01)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a notebook-faithful CV port on Step05 ROI x490 prototypes.")
    parser.add_argument("--step00", type=Path, default=STEP00)
    parser.add_argument("--step05", type=Path, default=STEP05)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    args = parser.parse_args()

    out_dir = args.output_root / f"fossum_roi_x490_step07_cv_notebook_faithful_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    figures = out_dir / "figures"
    figures.mkdir()
    tables = out_dir / "tables"
    tables.mkdir()

    prototypes = np.load(args.step05 / "canonical_prototypes.npy")
    mask = np.load(args.step00 / "mask_common_roi_x490.npy").astype(bool)
    assignments = pd.read_csv(args.step05 / "canonical_assignments.csv")
    class_sizes = assignments.groupby("class_id").size().sort_index().astype(int).tolist()

    global_records = export_prototypes_as_notebook_inputs(out_dir, prototypes, mask)
    local_records: list[dict[str, Any]] = []

    global_data = {}
    for rec in global_records:
        arr, m = load_prototype(rec["arr_path"], rec["mask_path"])
        global_data[rec["name"]] = {"arr": arr, "mask": m, "meta": rec}
    local_data = {}

    all_data = {f"global::{k}": v for k, v in global_data.items()}
    inferred_true_valid, convention_score = infer_mask_true_is_valid(all_data)
    if inferred_true_valid != EXPECTED_MASK_TRUE_IS_VALID:
        for k in global_data:
            global_data[k]["mask"] = ~global_data[k]["mask"]

    validation_rows = []
    for scope_name, dataset in [("global", global_data), ("local_class02", local_data)]:
        for key, item in dataset.items():
            arr = item["arr"]
            m = item["mask"]
            validation_rows.append(
                {
                    "scope": scope_name,
                    "name": key,
                    "arr_shape": tuple(arr.shape),
                    "mask_shape": tuple(m.shape),
                    "shape_match": tuple(arr.shape) == tuple(m.shape),
                    "mask_true_fraction": float(np.mean(m)),
                }
            )
    validation_df = pd.DataFrame(validation_rows)

    global_rows = []
    for name in sorted(global_data.keys()):
        item = global_data[name]
        row = extract_basic_features(name, item["arr"], item["mask"])
        row["seed"] = SEED_ID
        row["scope"] = "global"
        global_rows.append(row)
    features_global_df = pd.DataFrame(global_rows).sort_values("prototype_name").reset_index(drop=True)
    features_local_df = pd.DataFrame(columns=["prototype_name", "mean", "std", "mean_left", "mean_right", "mean_top", "mean_bottom", "contrast_lr", "contrast_tb", "seed", "scope", "k", "key"])

    simple_global_rows = []
    simple_global_aux = {}
    for name in sorted(global_data.keys()):
        item = global_data[name]
        row, aux = extract_simple_regime_metrics(name, item["arr"], item["mask"], sigma=SIMPLE_SIGMA)
        row["seed"] = SEED_ID
        row["scope"] = "global"
        row["regime_label"] = decide_regime_label_simple(row)
        simple_global_rows.append(row)
        aux["regime_label"] = row["regime_label"]
        simple_global_aux[name] = aux
    simple_global_df = pd.DataFrame(simple_global_rows).sort_values("prototype_name").reset_index(drop=True)
    simple_local_df = pd.DataFrame(columns=list(simple_global_df.columns) + ["k", "key"])

    image_global_rows = []
    image_global_aux = {}
    for rec in sorted(global_records, key=lambda r: r["name"]):
        row, aux = extract_image_only_metrics(rec["name"], rec["clean_png_path"])
        row["seed"] = SEED_ID
        row["scope"] = "global"
        row["regime_label"] = decide_regime_label_image_only(row)
        image_global_rows.append(row)
        aux["regime_label"] = row["regime_label"]
        aux["prototype_name"] = rec["name"]
        image_global_aux[rec["name"]] = aux
    image_global_df = pd.DataFrame(image_global_rows).sort_values("prototype_name").reset_index(drop=True)
    image_local_df = pd.DataFrame(columns=list(image_global_df.columns) + ["k", "key"])

    outputs = {
        "features_global": out_dir / f"cv_features_global_seed{SEED_ID}.csv",
        "features_local": out_dir / f"cv_features_local_class02_seed{SEED_ID}.csv",
        "validation": out_dir / f"cv_validation_seed{SEED_ID}.csv",
        "simple_global": out_dir / f"cv_features_global_seed{SEED_ID}_simple.csv",
        "simple_local": out_dir / f"cv_features_local_class02_seed{SEED_ID}_simple.csv",
        "image_global": out_dir / f"cv_features_global_seed{SEED_ID}_image_only.csv",
        "image_local": out_dir / f"cv_features_local_class02_seed{SEED_ID}_image_only.csv",
    }
    features_global_df.to_csv(outputs["features_global"], index=False)
    features_local_df.to_csv(outputs["features_local"], index=False)
    validation_df.to_csv(outputs["validation"], index=False)
    simple_global_df.to_csv(outputs["simple_global"], index=False)
    simple_local_df.to_csv(outputs["simple_local"], index=False)
    image_global_df.to_csv(outputs["image_global"], index=False)
    image_local_df.to_csv(outputs["image_local"], index=False)
    for p in outputs.values():
        shutil.copy2(p, tables / p.name)

    plot_global_prototypes(global_data, out_dir / "notebook_global_prototypes.png")
    plot_split_examples(global_data, out_dir)
    plot_simple_grid(simple_global_df, simple_global_aux, global_data, out_dir / "notebook_simple_global_original_vs_result.png")
    plot_image_only_grid(
        df=image_global_df,
        aux_dict=image_global_aux,
        key_col="prototype_name",
        figure_title=f"Image-only | global prototypes | seed {SEED_ID} | original (top) vs result (bottom)",
        out_path=out_dir / "notebook_image_only_global_original_vs_result.png",
    )
    for p in out_dir.glob("notebook_*.png"):
        shutil.copy2(p, figures / p.name)

    checks = {
        "notebook_source": str((ROOT / "notebooks" / "seed11_computer_vision_colab.ipynb").resolve()),
        "methodology": "notebook_faithful",
        "step00": str(args.step00.resolve()),
        "step05": str(args.step05.resolve()),
        "seed_id": SEED_ID,
        "n_global_prototypes": int(len(global_records)),
        "n_local_class02_prototypes": int(len(local_records)),
        "local_class02_skipped_reason": "Step05 canonical ROI x490 has only global class prototypes; no local class_02 prototype stage exists.",
        "prototype_shape": list(prototypes.shape),
        "mask_shape": list(mask.shape),
        "mask_true_is_valid_inferred": bool(inferred_true_valid),
        "mask_convention_score": convention_score,
        "features_global_created": outputs["features_global"].exists(),
        "simple_global_created": outputs["simple_global"].exists(),
        "image_only_global_created": outputs["image_global"].exists(),
        "simple_rules": SIMPLE_RULES,
        "image_only_rules": IMAGE_ONLY_RULES,
        "simple_regime_counts": simple_global_df["regime_label"].value_counts(dropna=False).to_dict(),
        "image_only_regime_counts": image_global_df["regime_label"].value_counts(dropna=False).to_dict(),
        "invented_descriptor_metrics_removed": True,
        "std_used": False,
        "temppred_october_classified": False,
        "final_verdict": "NOTEBOOK_FAITHFUL_CV_PORT_COMPLETE",
    }
    json_dump(out_dir / "step07_cv_notebook_faithful_checks.json", checks)
    json_dump(
        out_dir / "step07_cv_notebook_faithful_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": str(Path(__file__).resolve()),
            "output_folder": str(out_dir.resolve()),
            "adaptations": [
                "canonical Step05 prototypes were exported to notebook-style prototype_class_XX.npy, _mask.npy and _clean.png files",
                "local class_02 branch is empty because the current canonical Step05 has no local class_02 prototype stage",
                "all extra descriptor-ranking metrics from the earlier Step07-CV attempt were intentionally removed",
            ],
        },
    )
    shutil.copy2(Path(__file__).resolve(), out_dir / Path(__file__).name)

    audit_md = f"""# Notebook-faithful CV audit

This audit supersedes the broader Step07-CV attempt.

## Source reviewed

- `{ROOT / 'notebooks' / 'seed11_computer_vision_colab.ipynb'}`
- `{ROOT / 'notebooks' / 'seed11_computer_vision_colab.localrun.ipynb'}`

## What the old notebook actually did

1. Loaded exported seed11 prototypes as `.npy` plus `_mask.npy`.
2. Used `_clean.png` only for the image-only branch.
3. Validated `arr.shape == mask.shape`.
4. Used fixed visualization scale `vmin=-2.025433`, `vmax=2.025433`, `coolwarm`.
5. Split arrays into left/right/top/bottom and quadrants.
6. Exported basic features: mean, std, mean_left, mean_right, mean_top, mean_bottom, contrast_lr, contrast_tb.
7. Ran a conservative `simple` analysis over arrays with gaussian smoothing sigma=1, Otsu/mean threshold, region metrics, gradient p90 and rule-based labels.
8. Ran an `image-only` analysis over clean PNGs with alpha mask, score `R-B`, Otsu/mean threshold, region metrics, gradient p90 and rule-based labels.
9. Kept HSL exploration optional and explicitly outside the final CSV exports.

## What was removed relative to the previous Step07-CV attempt

- No heterogeneity ranking invented outside the notebook.
- No member-to-prototype residual outlier analysis.
- No KMeans substructure diagnostics.
- No descriptor-ready composite scores.
- No planner-facing recommendation beyond notebook labels/features.

## Adaptation to ROI x490

The canonical Step05 prototypes were exported into notebook-style inputs:
`notebook_style_exports/global/prototype_class_XX.npy`,
`prototype_class_XX_mask.npy`, and `prototype_class_XX_clean.png`.

The local `class_02` branch is empty because the current canonical run has no
local class_02 prototype stage.
"""
    (out_dir / "step07_cv_notebook_faithful_audit.md").write_text(audit_md, encoding="utf-8")

    summary_md = f"""# Step07-CV notebook-faithful summary

1. Notebook antigo revisto? Sim: `seed11_computer_vision_colab.ipynb`.
2. Logica antiga preservada? Sim: features basicas, simple arr+mask e image-only clean PNG.
3. Metricas inventadas removidas? Sim.
4. Prototipos globais analisados: {len(global_records)}.
5. Prototipos locais class_02: 0, porque nao existem no Step05 canonico atual.
6. Simple labels: {simple_global_df['regime_label'].value_counts(dropna=False).to_dict()}.
7. Image-only labels: {image_global_df['regime_label'].value_counts(dropna=False).to_dict()}.
8. STD usado? Nao.
9. TEMPpred outubro classificado? Nao.
10. Veredito: NOTEBOOK_FAITHFUL_CV_PORT_COMPLETE.
"""
    (out_dir / "step07_cv_notebook_faithful_summary.md").write_text(summary_md, encoding="utf-8")

    simple_table = df_as_plain_table(
        simple_global_df[
            [
                "prototype_name",
                "regime_label",
                "std_temp",
                "min_region_ratio",
                "inter_region_diff",
                "coherence_min",
                "p90_grad",
                "front_area_ratio",
            ]
        ]
    )
    image_table = df_as_plain_table(
        image_global_df[
            [
                "prototype_name",
                "regime_label",
                "std_temp",
                "min_region_ratio",
                "inter_region_diff",
                "coherence_min",
                "p90_grad",
            ]
        ]
    )

    report_md = f"""# Step07-CV notebook-faithful report

The previous Step07-CV run added descriptor-oriented metrics that were not in
the original notebook. This run corrects that by following the notebook
structure directly.

## Main outputs

- `{outputs['features_global'].name}`
- `{outputs['validation'].name}`
- `{outputs['simple_global'].name}`
- `{outputs['image_global'].name}`
- empty local class02 CSVs for structural compatibility
- notebook-style figures for prototypes, splits, simple labels and image-only labels

## Regime labels

Simple arr+mask:

```text
{simple_table}
```

Image-only clean PNG:

```text
{image_table}
```

## Final verdict

NOTEBOOK_FAITHFUL_CV_PORT_COMPLETE
"""
    (out_dir / "step07_cv_notebook_faithful_report.md").write_text(report_md, encoding="utf-8")

    print(f"Notebook-faithful Step07-CV complete: {out_dir}")


if __name__ == "__main__":
    main()
