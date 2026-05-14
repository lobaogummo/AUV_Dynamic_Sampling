"""Utility helpers for seed11 computer-vision downstream analysis.

The logic in this module is derived from:
- notebooks/seed11_computer_vision_colab.localrun.ipynb (primary source)
- notebooks/seed11_computer_vision_colab.ipynb (reference)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from scipy import ndimage as ndi

try:
    import cv2

    HAS_CV2 = True
except Exception:
    cv2 = None
    HAS_CV2 = False

try:
    from skimage.filters import threshold_multiotsu, threshold_otsu

    HAS_SKIMAGE = True
except Exception:
    threshold_otsu = None
    threshold_multiotsu = None
    HAS_SKIMAGE = False


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

IMAGE_ONLY_LABEL_TEXT = {
    "homogeneous": "HOMOGENEO",
    "single_gradient": "GRADIENTE UNICO",
    "multi_regime": "MULTI-REGIME",
}

IMAGE_ONLY_LABEL_COLOR = {
    "homogeneous": "#2E7D32",
    "single_gradient": "#C62828",
    "multi_regime": "#1565C0",
}


@dataclass(frozen=True)
class SeedExportPaths:
    project_root: Path
    cv_export_root: Path
    seed_root: Path
    global_dir: Path
    local_class02_dir: Path
    manifest_path: Path


@dataclass(frozen=True)
class PrototypeRecord:
    scope: str
    name: str
    key: str
    arr_path: Path
    mask_path: Path
    clean_png_path: Path
    k: str | None = None


def load_cv_config(config_path: Path) -> Dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config must be an object: {config_path}")
    return data


def _resolve_seed_root(cv_export_root: Path, seed_id: int) -> Path:
    candidates = [cv_export_root / f"seed{seed_id:02d}", cv_export_root / f"seed{seed_id}"]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()
    raise FileNotFoundError(
        f"Could not find seed folder for seed={seed_id} under {cv_export_root}. "
        f"Expected one of: {[str(c) for c in candidates]}"
    )


def discover_cv_export_root(project_root: Path, seed_id: int, explicit: Path | None = None) -> Path:
    if explicit is not None:
        root = explicit.resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"cv export root does not exist: {root}")
        _ = _resolve_seed_root(root, seed_id)
        return root

    results_root = (project_root / "results").resolve()
    if not results_root.exists():
        raise FileNotFoundError(f"Expected results directory at: {results_root}")

    candidates: list[Path] = []
    for p in results_root.rglob("computer_vision_exports*"):
        if not p.is_dir():
            continue
        try:
            _ = _resolve_seed_root(p.resolve(), seed_id)
        except FileNotFoundError:
            continue
        candidates.append(p.resolve())

    if not candidates:
        raise FileNotFoundError(
            f"Could not discover computer_vision_exports* containing seed{seed_id} under {results_root}"
        )

    def score(path: Path) -> Tuple[int, int, int, float]:
        lower = str(path).lower()
        official = int("official_fixed_dictionary" in lower)
        exact_name = int(path.name.lower() == f"computer_vision_exports_seed{seed_id}")
        fossil = int(
            "results\\fossum\\final_working_pipeline" in lower
            or "results/fossum/final_working_pipeline" in lower
        )
        return (official, exact_name, fossil, path.stat().st_mtime)

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def resolve_seed_export_paths(
    project_root: Path, seed_id: int, cv_export_root: Path | None = None
) -> SeedExportPaths:
    export_root = discover_cv_export_root(
        project_root=project_root,
        seed_id=seed_id,
        explicit=cv_export_root,
    )
    seed_root = _resolve_seed_root(export_root, seed_id)
    global_dir = (seed_root / "global").resolve()
    local_dir = (seed_root / "local_class02").resolve()
    if not global_dir.exists():
        raise FileNotFoundError(f"Missing global dir: {global_dir}")
    if not local_dir.exists():
        raise FileNotFoundError(f"Missing local class_02 dir: {local_dir}")
    manifest_path = (export_root / "manifest_cv_exports.json").resolve()
    return SeedExportPaths(
        project_root=project_root.resolve(),
        cv_export_root=export_root.resolve(),
        seed_root=seed_root,
        global_dir=global_dir,
        local_class02_dir=local_dir,
        manifest_path=manifest_path,
    )


def discover_global_prototypes(global_dir: Path) -> list[PrototypeRecord]:
    records: list[PrototypeRecord] = []
    for arr_path in sorted(global_dir.glob("prototype_class_*.npy")):
        if arr_path.name.endswith("_mask.npy"):
            continue
        base = arr_path.stem
        rec = PrototypeRecord(
            scope="global",
            name=base,
            key=base,
            arr_path=arr_path.resolve(),
            mask_path=arr_path.with_name(f"{base}_mask.npy").resolve(),
            clean_png_path=arr_path.with_name(f"{base}_clean.png").resolve(),
            k=None,
        )
        records.append(rec)
    return records


def discover_local_class02_prototypes(local_class02_dir: Path) -> list[PrototypeRecord]:
    records: list[PrototypeRecord] = []
    for k_dir in sorted(local_class02_dir.glob("k*")):
        if not k_dir.is_dir():
            continue
        for arr_path in sorted(k_dir.glob("subclass_prototype_*.npy")):
            if arr_path.name.endswith("_mask.npy"):
                continue
            base = arr_path.stem
            key = f"{k_dir.name}::{base}"
            rec = PrototypeRecord(
                scope="local_class02",
                name=base,
                key=key,
                arr_path=arr_path.resolve(),
                mask_path=arr_path.with_name(f"{base}_mask.npy").resolve(),
                clean_png_path=arr_path.with_name(f"{base}_clean.png").resolve(),
                k=k_dir.name,
            )
            records.append(rec)
    return records


def validate_record_files(records: Sequence[PrototypeRecord], require_clean_png: bool = True) -> None:
    missing: list[str] = []
    for rec in records:
        if not rec.arr_path.exists():
            missing.append(f"Missing arr: {rec.arr_path}")
        if not rec.mask_path.exists():
            missing.append(f"Missing mask: {rec.mask_path}")
        if require_clean_png and not rec.clean_png_path.exists():
            missing.append(f"Missing clean PNG: {rec.clean_png_path}")
    if missing:
        raise FileNotFoundError("\n".join(missing[:50]))


def load_prototype(arr_path: Path, mask_path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.load(arr_path).astype(np.float32, copy=False)
    mask = np.load(mask_path).astype(bool, copy=False)
    if arr.shape != mask.shape:
        raise ValueError(f"Shape mismatch arr={arr.shape}, mask={mask.shape} for {arr_path}")
    return arr, mask


def masked_mean(arr: np.ndarray, mask: np.ndarray) -> float:
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return float("nan")
    return float(np.nanmean(arr[valid]))


def masked_std(arr: np.ndarray, mask: np.ndarray) -> float:
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return float("nan")
    return float(np.nanstd(arr[valid]))


def split_halves(arr: np.ndarray, mask: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    h, w = arr.shape
    h_mid = h // 2
    w_mid = w // 2
    return {
        "left": (arr[:, :w_mid], mask[:, :w_mid]),
        "right": (arr[:, w_mid:], mask[:, w_mid:]),
        "top": (arr[h_mid:, :], mask[h_mid:, :]),
        "bottom": (arr[:h_mid, :], mask[:h_mid, :]),
    }


def split_quadrants(arr: np.ndarray, mask: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    h, w = arr.shape
    h_mid = h // 2
    w_mid = w // 2
    return {
        "Q1": (arr[h_mid:, :w_mid], mask[h_mid:, :w_mid]),
        "Q2": (arr[h_mid:, w_mid:], mask[h_mid:, w_mid:]),
        "Q3": (arr[:h_mid, :w_mid], mask[:h_mid, :w_mid]),
        "Q4": (arr[:h_mid, w_mid:], mask[:h_mid, w_mid:]),
    }


def infer_mask_true_is_valid(
    samples: Mapping[str, Mapping[str, Any]],
    expected_default: bool,
) -> tuple[bool, float]:
    scores: list[float] = []
    for item in samples.values():
        arr = np.asarray(item["arr"], dtype=np.float32)
        mask = np.asarray(item["mask"], dtype=bool)
        true_finite = float(np.mean(np.isfinite(arr[mask]))) if np.any(mask) else float("nan")
        false_finite = float(np.mean(np.isfinite(arr[~mask]))) if np.any(~mask) else float("nan")
        if np.isfinite(true_finite) and np.isfinite(false_finite):
            scores.append(true_finite - false_finite)

    if not scores:
        return expected_default, float("nan")
    mean_score = float(np.mean(scores))
    inferred = mean_score >= 0.0
    return inferred, mean_score


def load_datasets_with_validation(
    global_records: Sequence[PrototypeRecord],
    local_records: Sequence[PrototypeRecord],
    expected_mask_true_is_valid: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    global_data: dict[str, dict[str, Any]] = {}
    local_data: dict[str, dict[str, Any]] = {}

    for rec in global_records:
        arr, mask = load_prototype(rec.arr_path, rec.mask_path)
        global_data[rec.name] = {"arr": arr, "mask": mask, "meta": rec}

    for rec in local_records:
        arr, mask = load_prototype(rec.arr_path, rec.mask_path)
        local_data[rec.key] = {"arr": arr, "mask": mask, "meta": rec}

    all_data: dict[str, dict[str, Any]] = {}
    all_data.update({f"global::{k}": v for k, v in global_data.items()})
    all_data.update({f"local::{k}": v for k, v in local_data.items()})

    inferred_true_valid, convention_score = infer_mask_true_is_valid(
        samples=all_data,
        expected_default=expected_mask_true_is_valid,
    )
    flipped_masks = bool(inferred_true_valid != expected_mask_true_is_valid)
    if flipped_masks:
        for dataset in (global_data, local_data):
            for key in dataset:
                dataset[key]["mask"] = ~dataset[key]["mask"]

    validation_rows: list[dict[str, Any]] = []
    for scope_name, dataset in (("global", global_data), ("local_class02", local_data)):
        for key, item in dataset.items():
            arr = np.asarray(item["arr"])
            mask = np.asarray(item["mask"])
            validation_rows.append(
                {
                    "scope": scope_name,
                    "name": key,
                    "arr_shape": tuple(int(v) for v in arr.shape),
                    "mask_shape": tuple(int(v) for v in mask.shape),
                    "shape_match": bool(tuple(arr.shape) == tuple(mask.shape)),
                    "mask_true_fraction": float(np.mean(mask)),
                }
            )
    validation_df = pd.DataFrame(validation_rows)
    if not validation_df["shape_match"].all():
        raise RuntimeError("At least one prototype has mismatched arr/mask shape.")

    meta = {
        "expected_mask_true_is_valid": bool(expected_mask_true_is_valid),
        "inferred_mask_true_is_valid": bool(inferred_true_valid),
        "convention_score": float(convention_score),
        "flipped_masks": flipped_masks,
        "global_count": int(len(global_data)),
        "local_count": int(len(local_data)),
    }
    return global_data, local_data, validation_df, meta


def extract_basic_features(prototype_name: str, arr: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
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


def build_basic_feature_tables(
    global_data: Mapping[str, Mapping[str, Any]],
    local_data: Mapping[str, Mapping[str, Any]],
    seed_id: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    global_rows: list[dict[str, Any]] = []
    for name in sorted(global_data.keys()):
        item = global_data[name]
        row = extract_basic_features(name, np.asarray(item["arr"]), np.asarray(item["mask"]))
        row["seed"] = int(seed_id)
        row["scope"] = "global"
        global_rows.append(row)
    features_global_df = pd.DataFrame(global_rows).sort_values("prototype_name").reset_index(drop=True)

    local_rows: list[dict[str, Any]] = []
    for key in sorted(local_data.keys()):
        item = local_data[key]
        rec: PrototypeRecord = item["meta"]
        row = extract_basic_features(rec.name, np.asarray(item["arr"]), np.asarray(item["mask"]))
        row["seed"] = int(seed_id)
        row["scope"] = "local_class02"
        row["k"] = rec.k or ""
        row["key"] = key
        local_rows.append(row)
    features_local_df = pd.DataFrame(local_rows).sort_values(["k", "prototype_name"]).reset_index(drop=True)
    return features_global_df, features_local_df


def get_valid_values(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    valid = mask & np.isfinite(arr)
    return arr[valid].astype(np.float32, copy=False)


def simple_prepare(arr: np.ndarray, mask: np.ndarray, sigma: float = 1.0) -> np.ndarray:
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


def simple_global_metrics(arr_smooth: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    vals = get_valid_values(arr_smooth, mask)
    if vals.size == 0:
        return {"std_temp": float("nan"), "iqr_temp": float("nan"), "range_temp": float("nan")}
    p25, p75 = np.percentile(vals, [25, 75])
    return {
        "std_temp": float(np.nanstd(vals)),
        "iqr_temp": float(p75 - p25),
        "range_temp": float(np.nanmax(vals) - np.nanmin(vals)),
    }


def otsu_segmentation(arr_smooth: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    vals = get_valid_values(arr_smooth, mask)
    labels = np.full(arr_smooth.shape, -1, dtype=np.int8)
    region_low = np.zeros(arr_smooth.shape, dtype=bool)
    region_high = np.zeros(arr_smooth.shape, dtype=bool)
    if vals.size == 0:
        return {
            "threshold": float("nan"),
            "threshold_method": "empty",
            "labels": labels,
            "region_low": region_low,
            "region_high": region_high,
        }

    threshold = float(np.nanmean(vals))
    threshold_method = "mean_fallback"
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
    return {
        "threshold": threshold,
        "threshold_method": threshold_method,
        "labels": labels,
        "region_low": region_low,
        "region_high": region_high,
    }


def optional_multiotsu_thresholds(
    arr_smooth: np.ndarray,
    mask: np.ndarray,
    classes: int = 3,
) -> list[float] | None:
    vals = get_valid_values(arr_smooth, mask)
    if not HAS_SKIMAGE or threshold_multiotsu is None:
        return None
    if vals.size < classes:
        return None
    if np.unique(vals).size < classes:
        return None
    try:
        thresholds = threshold_multiotsu(vals, classes=classes)
    except Exception:
        return None
    return [float(v) for v in thresholds]


def largest_component_ratio(binary_region: np.ndarray) -> float:
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
    largest = int(comp_sizes.max())
    return float(largest / total)


def region_metrics(
    arr_smooth: np.ndarray,
    mask: np.ndarray,
    region_low: np.ndarray,
    region_high: np.ndarray,
) -> dict[str, float]:
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
    if np.isfinite(mean_low) and np.isfinite(mean_high):
        inter_region_diff = float(abs(mean_high - mean_low))
    else:
        inter_region_diff = 0.0

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


def simple_front_metrics(arr_smooth: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    valid = mask & np.isfinite(arr_smooth)
    grad_mag = np.full(arr_smooth.shape, np.nan, dtype=np.float32)
    front_binary = np.zeros(arr_smooth.shape, dtype=bool)
    if not np.any(valid):
        return {
            "mean_grad": float("nan"),
            "p90_grad": float("nan"),
            "front_area_ratio": float("nan"),
            "grad_mag": grad_mag,
            "front_binary": front_binary,
        }

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
    return {
        "mean_grad": mean_grad,
        "p90_grad": p90_grad,
        "front_area_ratio": front_area_ratio,
        "grad_mag": grad_mag,
        "front_binary": front_binary,
    }


def extract_simple_regime_metrics(
    prototype_name: str,
    arr: np.ndarray,
    mask: np.ndarray,
    sigma: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    arr_smooth = simple_prepare(arr, mask, sigma=float(sigma))
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


def decide_regime_label_simple(row: Mapping[str, Any], rules: Mapping[str, float]) -> str:
    std_temp = float(row.get("std_temp", np.nan))
    p90_grad = float(row.get("p90_grad", np.nan))
    front_area_ratio = float(row.get("front_area_ratio", np.nan))
    min_region_ratio = float(row.get("min_region_ratio", np.nan))
    inter_region_diff = float(row.get("inter_region_diff", np.nan))
    coherence_min = float(row.get("coherence_min", np.nan))

    homogeneous = (
        std_temp < float(rules["homogeneous_std_max"])
        and p90_grad < float(rules["homogeneous_p90_grad_max"])
        and front_area_ratio < float(rules["homogeneous_front_area_max"])
    )
    if homogeneous:
        return "homogeneous"

    multi_regime = (
        min_region_ratio >= float(rules["multi_min_region_ratio_min"])
        and inter_region_diff >= float(rules["multi_inter_region_diff_min"])
        and coherence_min >= float(rules["multi_coherence_min"])
        and front_area_ratio >= float(rules["multi_front_area_ratio_min"])
        and p90_grad >= float(rules["multi_p90_grad_min"])
    )
    if multi_regime:
        return "multi_regime"
    return "single_gradient"


def run_simple_analysis(
    global_data: Mapping[str, Mapping[str, Any]],
    local_data: Mapping[str, Mapping[str, Any]],
    seed_id: int,
    sigma: float,
    rules: Mapping[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    simple_global_rows: list[dict[str, Any]] = []
    simple_global_aux: dict[str, dict[str, Any]] = {}
    for name in sorted(global_data.keys()):
        item = global_data[name]
        row, aux = extract_simple_regime_metrics(
            prototype_name=name,
            arr=np.asarray(item["arr"]),
            mask=np.asarray(item["mask"]),
            sigma=float(sigma),
        )
        row["seed"] = int(seed_id)
        row["scope"] = "global"
        row["regime_label"] = decide_regime_label_simple(row, rules=rules)
        simple_global_rows.append(row)
        simple_global_aux[name] = aux
    simple_global_df = pd.DataFrame(simple_global_rows).sort_values("prototype_name").reset_index(drop=True)

    simple_local_rows: list[dict[str, Any]] = []
    simple_local_aux: dict[str, dict[str, Any]] = {}
    for key in sorted(local_data.keys()):
        item = local_data[key]
        rec: PrototypeRecord = item["meta"]
        row, aux = extract_simple_regime_metrics(
            prototype_name=rec.name,
            arr=np.asarray(item["arr"]),
            mask=np.asarray(item["mask"]),
            sigma=float(sigma),
        )
        row["seed"] = int(seed_id)
        row["scope"] = "local_class02"
        row["k"] = rec.k or ""
        row["key"] = key
        row["regime_label"] = decide_regime_label_simple(row, rules=rules)
        simple_local_rows.append(row)
        simple_local_aux[key] = aux
    simple_local_df = pd.DataFrame(simple_local_rows).sort_values(["k", "prototype_name"]).reset_index(drop=True)
    return simple_global_df, simple_local_df, simple_global_aux, simple_local_aux


def load_clean_png_rgba(png_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not HAS_CV2 or cv2 is None:
        raise RuntimeError("OpenCV not available. Install opencv-python-headless.")
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


def color_score_rb(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    score = rgb[..., 0].astype(np.float32) - rgb[..., 2].astype(np.float32)
    score = score.astype(np.float32, copy=False)
    score[~mask] = np.nan
    return score


def score_global_metrics(score: np.ndarray, mask: np.ndarray) -> dict[str, float]:
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


def otsu_on_color_score(score: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    valid = mask & np.isfinite(score)
    vals = score[valid]
    labels = np.full(score.shape, -1, dtype=np.int8)
    region_low = np.zeros(score.shape, dtype=bool)
    region_high = np.zeros(score.shape, dtype=bool)
    if vals.size == 0:
        return {
            "threshold": float("nan"),
            "threshold_method": "empty",
            "labels": labels,
            "region_low": region_low,
            "region_high": region_high,
        }

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
    return {
        "threshold": threshold,
        "threshold_method": threshold_method,
        "labels": labels,
        "region_low": region_low,
        "region_high": region_high,
    }


def region_metrics_from_score(
    score: np.ndarray,
    mask: np.ndarray,
    region_low: np.ndarray,
    region_high: np.ndarray,
) -> dict[str, float]:
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
    if np.isfinite(mean_low) and np.isfinite(mean_high):
        inter_region_diff = float(abs(mean_high - mean_low))
    else:
        inter_region_diff = 0.0

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


def image_front_metrics(score: np.ndarray, mask: np.ndarray, grad_sigma: float) -> dict[str, Any]:
    valid = mask & np.isfinite(score)
    grad_mag = np.full(score.shape, np.nan, dtype=np.float32)
    front_binary = np.zeros(score.shape, dtype=bool)
    if not np.any(valid):
        return {
            "mean_grad": float("nan"),
            "p90_grad": float("nan"),
            "front_area_ratio": float("nan"),
            "grad_mag": grad_mag,
            "front_binary": front_binary,
        }

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

    return {
        "mean_grad": mean_grad,
        "p90_grad": p90_grad,
        "front_area_ratio": front_area_ratio,
        "grad_mag": grad_mag,
        "front_binary": front_binary,
    }


def extract_image_only_metrics(
    prototype_name: str,
    clean_png_path: Path,
    grad_sigma: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rgb, alpha, mask = load_clean_png_rgba(clean_png_path)
    score = color_score_rb(rgb, mask)
    gm = score_global_metrics(score, mask)
    seg = otsu_on_color_score(score, mask)
    rm = region_metrics_from_score(score, mask, seg["region_low"], seg["region_high"])
    fm = image_front_metrics(score, mask, grad_sigma=grad_sigma)
    row = {
        "prototype_name": prototype_name,
        "clean_png_path": str(clean_png_path),
        "grad_sigma": float(grad_sigma),
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


def decide_regime_label_image_only(row: Mapping[str, Any], rules: Mapping[str, float]) -> str:
    std_temp = float(row.get("std_temp", np.nan))
    min_region_ratio = float(row.get("min_region_ratio", np.nan))
    inter_region_diff = float(row.get("inter_region_diff", np.nan))
    coherence_min = float(row.get("coherence_min", np.nan))
    p90_grad = float(row.get("p90_grad", np.nan))
    score_min = float(row.get("score_min", np.nan))
    score_max = float(row.get("score_max", np.nan))

    homogeneous_low_spread = (
        std_temp < float(rules["homogeneous_std_low_max"])
        and (
            min_region_ratio < float(rules["homogeneous_min_region_tiny_max"])
            or inter_region_diff < float(rules["homogeneous_inter_diff_low_max"])
        )
    )
    homogeneous_mid_profile = (
        std_temp < float(rules["homogeneous_std_mid_max"])
        and min_region_ratio < float(rules["homogeneous_min_region_mid_max"])
        and float(rules["homogeneous_inter_diff_mid_min"])
        <= inter_region_diff
        <= float(rules["homogeneous_inter_diff_mid_max"])
        and p90_grad <= float(rules["homogeneous_p90_grad_mid_max"])
    )
    if homogeneous_low_spread or homogeneous_mid_profile:
        return "homogeneous"

    strong_multi_regime = (
        min_region_ratio >= float(rules["multi_min_region_ratio_min"])
        and inter_region_diff >= float(rules["multi_inter_region_diff_min"])
        and coherence_min >= float(rules["multi_coherence_min"])
        and p90_grad >= float(rules["multi_p90_grad_min"])
    )
    color_crossing_multi_regime = (
        score_min < 0.0 < score_max
        and min_region_ratio >= float(rules["multi_min_region_ratio_min"])
        and inter_region_diff >= float(rules["multi_color_crossing_inter_diff_min"])
        and coherence_min >= float(rules["multi_coherence_min"])
        and p90_grad >= float(rules["multi_p90_grad_min"])
    )
    if strong_multi_regime or color_crossing_multi_regime:
        return "multi_regime"
    return "single_gradient"


def run_image_only_analysis(
    global_records: Sequence[PrototypeRecord],
    local_records: Sequence[PrototypeRecord],
    seed_id: int,
    grad_sigma: float,
    rules: Mapping[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not HAS_CV2:
        raise RuntimeError("OpenCV is required for image-only analysis.")

    image_global_rows: list[dict[str, Any]] = []
    image_global_aux: dict[str, dict[str, Any]] = {}
    for rec in sorted(global_records, key=lambda r: r.name):
        row, aux = extract_image_only_metrics(rec.name, rec.clean_png_path, grad_sigma=float(grad_sigma))
        row["seed"] = int(seed_id)
        row["scope"] = "global"
        row["regime_label"] = decide_regime_label_image_only(row, rules=rules)
        image_global_rows.append(row)
        aux["regime_label"] = row["regime_label"]
        aux["prototype_name"] = rec.name
        image_global_aux[rec.name] = aux
    image_global_df = pd.DataFrame(image_global_rows).sort_values("prototype_name").reset_index(drop=True)

    image_local_rows: list[dict[str, Any]] = []
    image_local_aux: dict[str, dict[str, Any]] = {}
    for rec in sorted(local_records, key=lambda r: ((r.k or ""), r.name)):
        row, aux = extract_image_only_metrics(rec.name, rec.clean_png_path, grad_sigma=float(grad_sigma))
        row["seed"] = int(seed_id)
        row["scope"] = "local_class02"
        row["k"] = rec.k or ""
        row["key"] = rec.key
        row["regime_label"] = decide_regime_label_image_only(row, rules=rules)
        image_local_rows.append(row)
        aux["regime_label"] = row["regime_label"]
        aux["prototype_name"] = rec.name
        image_local_aux[rec.key] = aux
    image_local_df = pd.DataFrame(image_local_rows).sort_values(["k", "prototype_name"]).reset_index(drop=True)
    return image_global_df, image_local_df, image_global_aux, image_local_aux


def masked_plot(
    arr: np.ndarray,
    mask: np.ndarray,
    title: str | None,
    ax: Any,
    vmin: float,
    vmax: float,
    cmap: str,
    show_colorbar: bool = False,
) -> Any:
    arr_plot = arr.astype(np.float32, copy=True)
    arr_plot[~mask] = np.nan
    im = ax.imshow(arr_plot, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    if title:
        ax.set_title(title)
    ax.axis("off")
    if show_colorbar:
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return im


def build_masked_overview_figure(
    data: Mapping[str, Mapping[str, Any]],
    title: str,
    cols_max: int,
    vmin: float,
    vmax: float,
    cmap: str,
) -> plt.Figure:
    keys = sorted(data.keys())
    n = len(keys)
    cols = min(cols_max, max(1, n))
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5.0 * cols, 3.0 * rows), squeeze=False)
    for i, key in enumerate(keys):
        r, c = divmod(i, cols)
        item = data[key]
        masked_plot(np.asarray(item["arr"]), np.asarray(item["mask"]), key, axes[r][c], vmin=vmin, vmax=vmax, cmap=cmap)
    for j in range(n, rows * cols):
        r, c = divmod(j, cols)
        axes[r][c].axis("off")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    return fig


def build_example_splits_figure(
    global_data: Mapping[str, Mapping[str, Any]],
    vmin: float,
    vmax: float,
    cmap: str,
) -> tuple[plt.Figure, plt.Figure]:
    example_name = sorted(global_data.keys())[0]
    example_arr = np.asarray(global_data[example_name]["arr"])
    example_mask = np.asarray(global_data[example_name]["mask"])
    halves = split_halves(example_arr, example_mask)
    quadrants = split_quadrants(example_arr, example_mask)

    fig_halves, axes = plt.subplots(1, 5, figsize=(22, 4))
    masked_plot(example_arr, example_mask, f"{example_name} (original)", axes[0], vmin=vmin, vmax=vmax, cmap=cmap)
    masked_plot(*halves["left"], "left", axes[1], vmin=vmin, vmax=vmax, cmap=cmap)
    masked_plot(*halves["right"], "right", axes[2], vmin=vmin, vmax=vmax, cmap=cmap)
    masked_plot(*halves["top"], "top", axes[3], vmin=vmin, vmax=vmax, cmap=cmap)
    masked_plot(*halves["bottom"], "bottom", axes[4], vmin=vmin, vmax=vmax, cmap=cmap)
    fig_halves.tight_layout()

    fig_quads, axes2 = plt.subplots(2, 2, figsize=(10, 7))
    for ax, qname in zip(axes2.flat, ["Q1", "Q2", "Q3", "Q4"]):
        masked_plot(*quadrants[qname], qname, ax, vmin=vmin, vmax=vmax, cmap=cmap)
    fig_quads.suptitle(f"Quadrants for {example_name}", y=1.02)
    fig_quads.tight_layout()
    return fig_halves, fig_quads


def _show_original(ax: Any, arr: np.ndarray, mask: np.ndarray, title: str, vmin: float, vmax: float, cmap: str) -> None:
    arr_plot = arr.astype(np.float32, copy=True)
    arr_plot[~mask] = np.nan
    ax.imshow(arr_plot, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def _add_badge(ax: Any, regime_label: str) -> None:
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
        bbox={"boxstyle": "round,pad=0.25", "facecolor": color, "edgecolor": "none", "alpha": 0.92},
    )


def _show_simple_final_cv(
    ax: Any,
    arr: np.ndarray,
    mask: np.ndarray,
    aux: Mapping[str, Any],
    regime_label: str,
    title: str,
    vmin: float,
    vmax: float,
    cmap: str,
) -> None:
    arr_plot = arr.astype(np.float32, copy=True)
    arr_plot[~mask] = np.nan
    ax.imshow(arr_plot, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    if regime_label == "single_gradient":
        front = aux.get("front_binary")
        if front is not None and np.any(front):
            front_overlay = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.float32)
            front_overlay[..., 0] = 1.0
            front_overlay[..., 3] = np.asarray(front, dtype=np.float32) * 0.55
            ax.imshow(front_overlay, origin="lower", aspect="auto")
    elif regime_label == "multi_regime":
        low = aux.get("region_low")
        high = aux.get("region_high")
        if low is not None and high is not None:
            region_map = np.full(arr.shape, np.nan, dtype=np.float32)
            region_map[np.asarray(low, dtype=bool)] = 0.0
            region_map[np.asarray(high, dtype=bool)] = 1.0
            ax.imshow(
                region_map,
                origin="lower",
                cmap=ListedColormap(["#3A86FF", "#FF8C42"]),
                vmin=0,
                vmax=1,
                alpha=0.45,
                aspect="auto",
            )
    _add_badge(ax, regime_label)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def build_simple_cv_grid_figure(
    df: pd.DataFrame,
    data_dict: Mapping[str, Mapping[str, Any]],
    aux_dict: Mapping[str, Mapping[str, Any]],
    key_col: str,
    figure_title: str,
    vmin: float,
    vmax: float,
    cmap: str,
) -> plt.Figure | None:
    if df.empty:
        return None
    keys = list(df[key_col])
    n = len(keys)
    cols = min(4, max(1, n))
    row_blocks = int(math.ceil(n / cols))
    total_rows = row_blocks * 2

    fig, axes = plt.subplots(total_rows, cols, figsize=(4.8 * cols, 3.2 * total_rows), squeeze=False)
    lookup = {row[key_col]: row for _, row in df.iterrows()}
    for i, key in enumerate(keys):
        block = i // cols
        col = i % cols
        r_top = block * 2
        r_bottom = r_top + 1
        item = data_dict[key]
        row = lookup[key]
        label = str(row["regime_label"])
        _show_original(
            axes[r_top][col],
            np.asarray(item["arr"]),
            np.asarray(item["mask"]),
            str(key),
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
        )
        _show_simple_final_cv(
            axes[r_bottom][col],
            np.asarray(item["arr"]),
            np.asarray(item["mask"]),
            aux_dict[key],
            label,
            "CV final",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
        )
    for j in range(n, row_blocks * cols):
        block = j // cols
        col = j % cols
        axes[block * 2][col].axis("off")
        axes[block * 2 + 1][col].axis("off")
    fig.suptitle(figure_title, y=1.01)
    fig.tight_layout()
    return fig


def _rgba_display(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb / 255.0, 0.0, 1.0)
    rgba[..., 3] = mask.astype(np.float32)
    return rgba


def _add_image_only_badge(ax: Any, regime_label: str) -> None:
    text = IMAGE_ONLY_LABEL_TEXT.get(regime_label, regime_label)
    color = IMAGE_ONLY_LABEL_COLOR.get(regime_label, "#555555")
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
        bbox={"boxstyle": "round,pad=0.25", "facecolor": color, "edgecolor": "none", "alpha": 0.92},
    )


def _show_image_only_original(ax: Any, res: Mapping[str, Any], title: str) -> None:
    ax.imshow(_rgba_display(np.asarray(res["rgb"]), np.asarray(res["mask"])), origin="lower", aspect="auto")
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def _show_image_only_result(ax: Any, res: Mapping[str, Any], title: str) -> None:
    rgb = np.asarray(res["rgb"])
    mask = np.asarray(res["mask"])
    regime_label = str(res["regime_label"])
    ax.imshow(_rgba_display(rgb, mask), origin="lower", aspect="auto")
    if regime_label == "multi_regime":
        region_map = np.full(mask.shape, np.nan, dtype=np.float32)
        region_map[np.asarray(res["region_low"], dtype=bool)] = 0.0
        region_map[np.asarray(res["region_high"], dtype=bool)] = 1.0
        ax.imshow(
            region_map,
            origin="lower",
            cmap=ListedColormap(["#3A86FF", "#FF8C42"]),
            vmin=0,
            vmax=1,
            alpha=0.40,
            aspect="auto",
        )
    _add_image_only_badge(ax, regime_label)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def build_image_only_grid_figure(
    df: pd.DataFrame,
    aux_dict: Mapping[str, Mapping[str, Any]],
    key_col: str,
    figure_title: str,
) -> plt.Figure | None:
    if df.empty:
        return None
    keys = list(df[key_col])
    n = len(keys)
    cols = min(4, max(1, n))
    row_blocks = int(math.ceil(n / cols))
    total_rows = row_blocks * 2
    fig, axes = plt.subplots(total_rows, cols, figsize=(4.8 * cols, 3.2 * total_rows), squeeze=False)
    for i, key in enumerate(keys):
        block = i // cols
        col = i % cols
        r_top = block * 2
        r_bottom = r_top + 1
        res = aux_dict[key]
        _show_image_only_original(axes[r_top][col], res, str(key))
        _show_image_only_result(axes[r_bottom][col], res, "Image-only final")
    for j in range(n, row_blocks * cols):
        block = j // cols
        col = j % cols
        axes[block * 2][col].axis("off")
        axes[block * 2 + 1][col].axis("off")
    fig.suptitle(figure_title, y=1.01)
    fig.tight_layout()
    return fig


def build_optional_hsl_figure(
    records: Sequence[PrototypeRecord],
    max_items: int,
) -> tuple[plt.Figure | None, dict[str, Any]]:
    if not HAS_CV2 or cv2 is None:
        return None, {"status": "skipped", "reason": "opencv_not_available"}
    selected = [r for r in records if r.clean_png_path.exists()][: int(max_items)]
    if not selected:
        return None, {"status": "skipped", "reason": "no_clean_png"}
    fig, axes = plt.subplots(len(selected), 3, figsize=(12, 3.5 * len(selected)), squeeze=False)
    for i, rec in enumerate(selected):
        img_bgr = cv2.imread(str(rec.clean_png_path))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_hls = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HLS)
        h_ch = img_hls[:, :, 0]
        l_ch = img_hls[:, :, 1]
        axes[i][0].imshow(img_rgb)
        axes[i][0].set_title(f"{rec.name} | clean PNG")
        axes[i][0].axis("off")
        axes[i][1].imshow(h_ch, cmap="hsv")
        axes[i][1].set_title("H channel (exploratory)")
        axes[i][1].axis("off")
        axes[i][2].imshow(l_ch, cmap="gray")
        axes[i][2].set_title("L channel (exploratory)")
        axes[i][2].axis("off")
    fig.suptitle("Optional HSL exploration on clean PNGs (not used in classification)", y=1.01)
    fig.tight_layout()
    return fig, {"status": "executed", "n_items": int(len(selected))}


def ensure_output_dir(
    output_root: Path,
    run_tag: str | None,
    seed_id: int,
    allow_overwrite: bool,
) -> Path:
    if run_tag is None or not run_tag.strip():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_tag = f"seed{seed_id:02d}_cv_{ts}"
    out_dir = (output_root / run_tag).resolve()
    if out_dir.exists() and any(out_dir.iterdir()) and not allow_overwrite:
        raise FileExistsError(f"Output dir already exists and is not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _safe_write_guard(path: Path, allow_overwrite: bool) -> None:
    if path.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")


def write_csv(df: pd.DataFrame, path: Path, allow_overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_write_guard(path, allow_overwrite=allow_overwrite)
    df.to_csv(path, index=False)


def write_json(payload: Mapping[str, Any], path: Path, allow_overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_write_guard(path, allow_overwrite=allow_overwrite)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(text: str, path: Path, allow_overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_write_guard(path, allow_overwrite=allow_overwrite)
    path.write_text(text, encoding="utf-8")


def save_figure(fig: plt.Figure | None, path: Path, allow_overwrite: bool) -> None:
    if fig is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_write_guard(path, allow_overwrite=allow_overwrite)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def value_counts_safe(df: pd.DataFrame, col: str) -> dict[str, int]:
    if col not in df.columns:
        return {}
    counts = df[col].value_counts(dropna=False)
    return {str(k): int(v) for k, v in counts.items()}


def build_manifest(
    *,
    seed_id: int,
    config_path: Path,
    cv_paths: SeedExportPaths,
    output_dir: Path,
    csv_paths: Mapping[str, Path],
    figure_paths: Mapping[str, Path],
    data_meta: Mapping[str, Any],
    simple_sigma: float,
    simple_rules: Mapping[str, Any],
    image_grad_sigma: float,
    image_rules: Mapping[str, Any],
    optional_hsl_meta: Mapping[str, Any],
    simple_global_df: pd.DataFrame,
    simple_local_df: pd.DataFrame,
    image_global_df: pd.DataFrame,
    image_local_df: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_id": int(seed_id),
        "config_path": str(config_path.resolve()),
        "source": {
            "project_root": str(cv_paths.project_root.resolve()),
            "cv_export_root": str(cv_paths.cv_export_root.resolve()),
            "seed_root": str(cv_paths.seed_root.resolve()),
            "global_dir": str(cv_paths.global_dir.resolve()),
            "local_class02_dir": str(cv_paths.local_class02_dir.resolve()),
            "manifest_cv_exports_path": str(cv_paths.manifest_path.resolve()),
        },
        "analysis": {
            "simple_sigma": float(simple_sigma),
            "simple_rules": dict(simple_rules),
            "image_only_grad_sigma": float(image_grad_sigma),
            "image_only_rules": dict(image_rules),
            "optional_hsl": dict(optional_hsl_meta),
            "mask_convention": dict(data_meta),
        },
        "counts": {
            "simple_global_labels": value_counts_safe(simple_global_df, "regime_label"),
            "simple_local_labels": value_counts_safe(simple_local_df, "regime_label"),
            "image_global_labels": value_counts_safe(image_global_df, "regime_label"),
            "image_local_labels": value_counts_safe(image_local_df, "regime_label"),
        },
        "outputs": {
            "output_dir": str(output_dir.resolve()),
            "csv": {k: str(v.resolve()) for k, v in csv_paths.items()},
            "figures": {k: str(v.resolve()) for k, v in figure_paths.items()},
            "report_md": str((output_dir / "run_report.md").resolve()),
            "manifest_json": str((output_dir / "manifest.json").resolve()),
        },
        "notes": [
            "Downstream-only CV step. No clustering or prototype regeneration is performed here.",
            "Reads official exported prototype assets (*.npy, *_mask.npy, *_clean.png).",
            "Outputs are written to a new run directory and protected against accidental overwrite by default.",
        ],
    }


def build_run_report_markdown(
    *,
    seed_id: int,
    cv_paths: SeedExportPaths,
    output_dir: Path,
    validation_df: pd.DataFrame,
    simple_global_df: pd.DataFrame,
    simple_local_df: pd.DataFrame,
    image_global_df: pd.DataFrame,
    image_local_df: pd.DataFrame,
    data_meta: Mapping[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Seed11 Computer Vision Run Report")
    lines.append("")
    lines.append(f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Seed: {seed_id}")
    lines.append(f"- Source export root: `{cv_paths.cv_export_root}`")
    lines.append(f"- Output dir: `{output_dir}`")
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append(f"- Global prototypes loaded: {int(data_meta.get('global_count', 0))}")
    lines.append(f"- Local class_02 prototypes loaded: {int(data_meta.get('local_count', 0))}")
    lines.append(f"- Inferred mask true-is-valid: {bool(data_meta.get('inferred_mask_true_is_valid', False))}")
    lines.append(f"- Expected mask true-is-valid: {bool(data_meta.get('expected_mask_true_is_valid', False))}")
    lines.append(f"- Masks flipped for analysis: {bool(data_meta.get('flipped_masks', False))}")
    score = float(data_meta.get("convention_score", float("nan")))
    lines.append(f"- Convention score: {score:.6f}" if np.isfinite(score) else "- Convention score: nan")
    lines.append(f"- Validation rows: {len(validation_df)}")
    lines.append("")
    lines.append("## Label Summary")
    lines.append("")
    lines.append(f"- Simple global: {value_counts_safe(simple_global_df, 'regime_label')}")
    lines.append(f"- Simple local: {value_counts_safe(simple_local_df, 'regime_label')}")
    lines.append(f"- Image-only global: {value_counts_safe(image_global_df, 'regime_label')}")
    lines.append(f"- Image-only local: {value_counts_safe(image_local_df, 'regime_label')}")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append("- `cv_features_global_seedXX.csv`")
    lines.append("- `cv_features_local_class02_seedXX.csv`")
    lines.append("- `cv_validation_seedXX.csv`")
    lines.append("- `cv_features_global_seedXX_simple.csv`")
    lines.append("- `cv_features_local_class02_seedXX_simple.csv`")
    lines.append("- `cv_features_global_seedXX_image_only.csv`")
    lines.append("- `cv_features_local_class02_seedXX_image_only.csv`")
    lines.append("- `manifest.json`")
    lines.append("- `run_report.md`")
    return "\n".join(lines) + "\n"


def dict_without_none(items: Mapping[str, Path | None]) -> dict[str, Path]:
    return {k: v for k, v in items.items() if v is not None}


def close_figures(figs: Iterable[plt.Figure | None]) -> None:
    for fig in figs:
        if fig is None:
            continue
        plt.close(fig)
