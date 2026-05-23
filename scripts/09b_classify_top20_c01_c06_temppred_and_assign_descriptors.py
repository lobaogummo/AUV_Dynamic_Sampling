"""Step09B: classify Step10E top20 C01/C06 TEMPpred ROI arrays.

This is a downstream-only stage:
- reads the persisted Step10E ROI x490 TEMPpred/STD arrays;
- normalizes TEMPpred with Step00 global mean/std;
- encodes with the fixed Step05 dictionary;
- reconstructs the Step05 StandardScaler from canonical features;
- classifies by nearest Step05 class centroid in scaled feature space;
- assigns Step08 descriptor maps by predicted class.

STD/variance is used only for diagnostics and overlap metrics. It is never
used for classification.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from fossum_faithful_initial_utils import FaithfulInitialConfig, build_patch_vectors, load_fixed_dictionary_model


RESULTS_ROOT = ROOT / "results"
DEFAULT_STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_STEP05 = RESULTS_ROOT / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
DEFAULT_STEP08 = RESULTS_ROOT / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
DEFAULT_STEP10E = RESULTS_ROOT / "fossum_roi_x490_step10e_top20_class01_class06_roi_x490_20260519_184636"

EXPECTED_N_DAYS = 20
EXPECTED_CLASSES = 6
EXPECTED_SHAPE = (72, 117)
EXPECTED_FEATURE_SHAPE = (20, 15288)
EXPECTED_VALID_CELLS = 8004
PATCH_H = 24
PATCH_W = 40
DICTIONARY_SIZE = 4

TEMP_VMIN = 16.1942
TEMP_VMAX = 19.6822
STD_VMIN = 0.006523
STD_VMAX = 0.203208
NORM_VLIM = 1.95039


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return None if not math.isfinite(value) else value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def class_label(class_id: int) -> str:
    return f"C{int(class_id):02d}"


def normalize_temppred(temp: np.ndarray, mask: np.ndarray, stats: dict[str, Any]) -> np.ndarray:
    mu = float(stats["mu_global"])
    sigma = float(stats["sigma_global"])
    out = ((temp.astype(np.float32) - mu) / sigma).astype(np.float32)
    out[:, ~mask] = np.nan
    return out


def encode_with_fixed_dictionary(X_norm: np.ndarray, dictionary_path: Path) -> tuple[np.ndarray, np.ndarray]:
    cfg = FaithfulInitialConfig(n_classes=EXPECTED_CLASSES)
    model, _meta = load_fixed_dictionary_model(dictionary_path, cfg=cfg, expected_dictionary_size=DICTIONARY_SIZE)
    first = build_patch_vectors(
        image_2d=X_norm[0],
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
    )
    patches_per_image = int(first.shape[0])
    feature_len = int(patches_per_image * DICTIONARY_SIZE)
    features = np.empty((X_norm.shape[0], feature_len), dtype=np.float32)
    sparse_codes = np.empty((X_norm.shape[0], patches_per_image, DICTIONARY_SIZE), dtype=np.float32)
    for i in range(X_norm.shape[0]):
        patches = build_patch_vectors(
            image_2d=X_norm[i],
            patch_h=PATCH_H,
            patch_w=PATCH_W,
            include_valid_mask=cfg.include_valid_mask,
            mask_encoding=cfg.mask_encoding,
        )
        codes = model.transform(patches).astype(np.float32, copy=False)
        sparse_codes[i] = codes
        features[i] = codes.reshape(-1)
    return features, sparse_codes


def scaler_from_canonical(canonical_features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = canonical_features.astype(np.float64).mean(axis=0)
    scale = canonical_features.astype(np.float64).std(axis=0, ddof=0)
    scale[scale == 0] = 1.0
    return mean.astype(np.float32), scale.astype(np.float32)


def masked_corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    valid = mask & np.isfinite(a) & np.isfinite(b)
    if int(valid.sum()) < 2:
        return float("nan")
    av = a[valid].astype(np.float64)
    bv = b[valid].astype(np.float64)
    av -= av.mean()
    bv -= bv.mean()
    denom = float(np.sqrt(np.sum(av * av) * np.sum(bv * bv)))
    if denom <= 1e-12:
        return float("nan")
    return float(np.sum(av * bv) / denom)


def masked_rmse(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    valid = mask & np.isfinite(a) & np.isfinite(b)
    if not np.any(valid):
        return float("nan")
    diff = a[valid].astype(np.float64) - b[valid].astype(np.float64)
    return float(np.sqrt(np.nanmean(diff * diff)))


def masked_stats(prefix: str, arr: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        return {
            f"{prefix}_min": float("nan"),
            f"{prefix}_max": float("nan"),
            f"{prefix}_mean": float("nan"),
            f"{prefix}_std": float("nan"),
            f"{prefix}_p05": float("nan"),
            f"{prefix}_p50": float("nan"),
            f"{prefix}_p95": float("nan"),
            f"{prefix}_nan_fraction": 1.0,
        }
    return {
        f"{prefix}_min": float(np.nanmin(vals)),
        f"{prefix}_max": float(np.nanmax(vals)),
        f"{prefix}_mean": float(np.nanmean(vals)),
        f"{prefix}_std": float(np.nanstd(vals)),
        f"{prefix}_p05": float(np.nanpercentile(vals, 5)),
        f"{prefix}_p50": float(np.nanpercentile(vals, 50)),
        f"{prefix}_p95": float(np.nanpercentile(vals, 95)),
        f"{prefix}_nan_fraction": float(np.mean(~np.isfinite(arr))),
    }


def minmax01(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        out[mask] = 0.0
        return out
    mn = float(np.nanmin(vals))
    mx = float(np.nanmax(vals))
    if mx - mn <= 1e-12:
        out[mask] = 0.0
    else:
        out[mask] = ((arr[mask] - mn) / (mx - mn)).astype(np.float32)
    return out


def gradient_map(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    fill = float(np.nanmean(arr[mask])) if np.any(mask & np.isfinite(arr)) else 0.0
    filled = np.where(mask & np.isfinite(arr), arr, fill).astype(np.float32)
    gy, gx = np.gradient(filled)
    grad = np.hypot(gx, gy).astype(np.float32)
    grad[~mask] = np.nan
    return grad


def local_variance_proxy(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    fill = float(np.nanmean(arr[mask])) if np.any(mask & np.isfinite(arr)) else 0.0
    x = np.where(mask & np.isfinite(arr), arr, fill).astype(np.float32)
    padded = np.pad(x, 1, mode="edge")
    sums = np.zeros_like(x, dtype=np.float64)
    sums2 = np.zeros_like(x, dtype=np.float64)
    for dy in range(3):
        for dx in range(3):
            win = padded[dy : dy + x.shape[0], dx : dx + x.shape[1]]
            sums += win
            sums2 += win * win
    mean = sums / 9.0
    var = np.maximum(sums2 / 9.0 - mean * mean, 0.0).astype(np.float32)
    var[~mask] = np.nan
    return var


def weighted_centroid(binary_or_weight: np.ndarray, x_km: np.ndarray, y_km: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    valid = mask & np.isfinite(binary_or_weight) & np.isfinite(x_km) & np.isfinite(y_km)
    if not np.any(valid):
        return float("nan"), float("nan")
    w = np.asarray(binary_or_weight[valid], dtype=np.float64)
    w = np.maximum(w, 0.0)
    if float(np.sum(w)) <= 1e-12:
        w = np.ones_like(w)
    return float(np.average(x_km[valid], weights=w)), float(np.average(y_km[valid], weights=w))


def top_overlap(a: np.ndarray, b: np.ndarray, mask: np.ndarray, percentile: float) -> float:
    valid = mask & np.isfinite(a) & np.isfinite(b)
    if not np.any(valid):
        return float("nan")
    av = a[valid]
    bv = b[valid]
    a_thr = float(np.nanpercentile(av, percentile))
    b_thr = float(np.nanpercentile(bv, percentile))
    return float(np.mean((av >= a_thr) & (bv >= b_thr)))


def entropy_score(vals: np.ndarray) -> float:
    vals = vals[np.isfinite(vals)]
    if vals.size < 2:
        return float("nan")
    hist, _ = np.histogram(vals, bins=32)
    p = hist.astype(np.float64)
    p = p[p > 0]
    p /= p.sum()
    return float(-np.sum(p * np.log(p)) / np.log(32.0))


def label_from_expected(value: Any) -> str:
    try:
        return class_label(int(value))
    except Exception:
        text = str(value).strip()
        return text if text.upper().startswith("C") else text


def save_heatmap(
    matrix: np.ndarray,
    xlabels: list[str],
    ylabels: list[str],
    title: str,
    out_path: Path,
    cmap: str = "viridis",
    annotate: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(max(8, 0.42 * len(xlabels)), max(4, 0.48 * len(ylabels))))
    im = ax.imshow(matrix, aspect="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xticks(np.arange(len(xlabels)))
    ax.set_xticklabels(xlabels, rotation=90, fontsize=7)
    ax.set_yticks(np.arange(len(ylabels)))
    ax.set_yticklabels(ylabels)
    if annotate:
        for r in range(matrix.shape[0]):
            for c in range(matrix.shape[1]):
                ax.text(c, r, str(int(matrix[r, c])), ha="center", va="center", color="white", fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_expected_predicted_timeline(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 4))
    x = np.arange(len(df))
    expected = df["expected_class"].astype(int).to_numpy()
    predicted = df["predicted_class"].astype(int).to_numpy()
    ax.plot(x, expected, marker="o", label="expected original class", color="#555555", alpha=0.7)
    ax.scatter(x, predicted, c=predicted, cmap="tab10", s=70, label="predicted Step09B", zorder=3)
    for i, ok in enumerate(df["match_expected"].astype(bool).to_numpy()):
        if not ok:
            ax.axvspan(i - 0.42, i + 0.42, color="#ffb000", alpha=0.18)
    ax.set_xticks(x)
    ax.set_xticklabels(df["date"].astype(str).str.slice(5).tolist(), rotation=90, fontsize=8)
    ax.set_yticks(range(1, EXPECTED_CLASSES + 1))
    ax.set_ylabel("class")
    ax.set_title("Step09B expected vs predicted class")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_confidence_barplot(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 4))
    colors = np.where(df["low_confidence_flag"].astype(bool), "#d62728", "#1f77b4")
    ax.bar(np.arange(len(df)), df["confidence_score"].astype(float), color=colors)
    ax.set_xticks(np.arange(len(df)))
    ax.set_xticklabels(df["date"].astype(str).str.slice(5).tolist(), rotation=90, fontsize=8)
    ax.set_ylabel("margin / second distance")
    ax.set_title("Step09B confidence margin")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_grouped_maps(
    arr: np.ndarray,
    df: pd.DataFrame,
    group_col: str,
    out_path: Path,
    title: str,
    cmap: str,
    vmin: float | None,
    vmax: float | None,
    max_cols: int = 5,
) -> None:
    groups = sorted(df[group_col].astype(int).unique().tolist())
    rows = []
    for group in groups:
        idx = df.index[df[group_col].astype(int) == group].tolist()
        rows.append((group, idx))
    nrows = len(rows)
    fig, axes = plt.subplots(nrows, max_cols, figsize=(3.0 * max_cols, 2.4 * nrows), squeeze=False)
    for r, (group, idxs) in enumerate(rows):
        for c in range(max_cols):
            ax = axes[r, c]
            if c >= len(idxs):
                ax.axis("off")
                continue
            i = idxs[c]
            ax.imshow(arr[i], origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            ax.set_title(f"{class_label(group)} {df.loc[i, 'date'][5:]}", fontsize=8)
            ax.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_temppred_prototype_panel(
    temp_norm: np.ndarray,
    prototypes: np.ndarray,
    df: pd.DataFrame,
    class_col: str,
    out_path: Path,
    title: str,
    max_days: int = 12,
) -> None:
    use_df = df.head(max_days).copy()
    n = len(use_df)
    fig, axes = plt.subplots(n, 3, figsize=(9.5, 2.5 * max(n, 1)), squeeze=False)
    for r, (_, row) in enumerate(use_df.iterrows()):
        i = int(row["row_id"])
        c = int(row[class_col]) - 1
        residual = temp_norm[i] - prototypes[c]
        maps = [temp_norm[i], prototypes[c], residual]
        titles = ["TEMPpred norm", f"prototype {class_label(c + 1)}", "residual"]
        for j in range(3):
            ax = axes[r, j]
            ax.imshow(maps[j], origin="lower", cmap="coolwarm", vmin=-NORM_VLIM, vmax=NORM_VLIM, aspect="auto")
            ax.set_title(f"{row['date']} | {titles[j]}", fontsize=8)
            ax.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_std_interest_panel(std: np.ndarray, interest: np.ndarray, df: pd.DataFrame, out_path: Path, max_days: int = 12) -> None:
    use_df = df.sort_values(["planner_score"], ascending=False).head(max_days).copy()
    n = len(use_df)
    fig, axes = plt.subplots(n, 3, figsize=(10, 2.5 * max(n, 1)), squeeze=False)
    for r, (_, row) in enumerate(use_df.iterrows()):
        i = int(row["row_id"])
        product = minmax01(std[i], np.isfinite(std[i])) * interest[i]
        maps = [std[i], interest[i], product]
        titles = ["STD variance", "assigned interest", "STD x interest"]
        cmaps = ["viridis", "inferno", "magma"]
        vmins = [STD_VMIN, 0.0, None]
        vmaxs = [STD_VMAX, 1.0, None]
        for j in range(3):
            ax = axes[r, j]
            ax.imshow(maps[j], origin="lower", cmap=cmaps[j], vmin=vmins[j], vmax=vmaxs[j], aspect="auto")
            ax.set_title(f"{row['date']} {class_label(row['predicted_class'])} | {titles[j]}", fontsize=8)
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_top_recommended_panel(temp: np.ndarray, std: np.ndarray, df: pd.DataFrame, out_path: Path, max_days: int = 8) -> None:
    use_df = df.sort_values("planner_score", ascending=False).head(max_days).copy()
    n = len(use_df)
    fig, axes = plt.subplots(n, 2, figsize=(7.5, 2.5 * max(n, 1)), squeeze=False)
    for r, (_, row) in enumerate(use_df.iterrows()):
        i = int(row["row_id"])
        for j, (arr, cmap, vmin, vmax, label) in enumerate(
            [
                (temp[i], "coolwarm", TEMP_VMIN, TEMP_VMAX, "TEMPpred"),
                (std[i], "viridis", STD_VMIN, STD_VMAX, "STD variance"),
            ]
        ):
            ax = axes[r, j]
            ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            ax.set_title(f"{row['date']} {class_label(row['predicted_class'])} score={row['planner_score']:.3f} | {label}", fontsize=8)
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_mismatch_panel(temp: np.ndarray, std: np.ndarray, df: pd.DataFrame, out_path: Path) -> None:
    mismatch = df[~df["match_expected"].astype(bool)].copy()
    if mismatch.empty:
        return
    n = len(mismatch)
    fig, axes = plt.subplots(n, 2, figsize=(7.5, 2.5 * n), squeeze=False)
    for r, (_, row) in enumerate(mismatch.iterrows()):
        i = int(row["row_id"])
        for j, (arr, cmap, vmin, vmax, label) in enumerate(
            [
                (temp[i], "coolwarm", TEMP_VMIN, TEMP_VMAX, "TEMPpred"),
                (std[i], "viridis", STD_VMIN, STD_VMAX, "STD variance"),
            ]
        ):
            ax = axes[r, j]
            ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            ax.set_title(
                f"{row['date']} expected {class_label(row['expected_class'])} -> predicted {class_label(row['predicted_class'])} | {label}",
                fontsize=8,
            )
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify Step10E top20 C01/C06 TEMPpred and assign Step08 descriptors.")
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--step05", type=Path, default=DEFAULT_STEP05)
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--step10e", type=Path, default=DEFAULT_STEP10E)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    step00 = args.step00.resolve()
    step05 = args.step05.resolve()
    step08 = args.step08.resolve()
    step10e = args.step10e.resolve()
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step09b_top20_c01_c06_temppred_classification_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir()

    mask = np.load(require(step00 / "mask_common_roi_x490.npy", "Step00 mask")).astype(bool)
    stats = read_json(require(step00 / "normalization_stats.json", "Step00 normalization stats"))
    step10e_mask = np.load(require(step10e / "MASK_top20_roi_x490.npy", "Step10E mask")).astype(bool)
    temp = np.load(require(step10e / "TEMPpred_top20_roi_x490.npy", "Step10E TEMPpred")).astype(np.float32)
    std = np.load(require(step10e / "STD_variance_top20_roi_x490.npy", "Step10E STD variance")).astype(np.float32)
    selected = pd.read_csv(require(step10e / "selected_dates_top20_class01_class06.csv", "Step10E selected dates"))
    step10e_day_metrics = pd.read_csv(require(step10e / "step10e_day_metrics.csv", "Step10E day metrics"))
    comparison_370 = pd.read_csv(require(step10e / "step10e_comparison_to_original_370.csv", "Step10E comparison to original 370"))

    x_km = np.load(require(step10e / "X_km_top20_roi_x490.npy", "Step10E X_km")).astype(np.float32)
    y_km = np.load(require(step10e / "Y_km_top20_roi_x490.npy", "Step10E Y_km")).astype(np.float32)

    prototypes = np.load(require(step05 / "canonical_prototypes.npy", "Step05 prototypes")).astype(np.float32)
    canonical_features = np.load(require(step05 / "canonical_feature_matrix.npy", "Step05 canonical features")).astype(np.float32)
    canonical_scaled = np.load(require(step05 / "canonical_scaled_feature_matrix.npy", "Step05 scaled features")).astype(np.float32)
    assignments05 = pd.read_csv(require(step05 / "canonical_assignments.csv", "Step05 assignments"))
    class_sizes05 = pd.read_csv(require(step05 / "canonical_class_sizes.csv", "Step05 class sizes"))

    descriptor_df = pd.read_csv(require(step08 / "step08_final_class_descriptors.csv", "Step08 descriptors"))
    descriptor_maps = {
        "gradient": np.load(require(step08 / "step08_descriptor_gradient_map.npy", "Step08 gradient map")).astype(np.float32),
        "boundary": np.load(require(step08 / "step08_descriptor_boundary_map.npy", "Step08 boundary map")).astype(np.float32),
        "heterogeneity": np.load(require(step08 / "step08_descriptor_heterogeneity_map.npy", "Step08 heterogeneity map")).astype(np.float32),
        "cold_region": np.load(require(step08 / "step08_descriptor_cold_region_map.npy", "Step08 cold map")).astype(np.float32),
        "warm_region": np.load(require(step08 / "step08_descriptor_warm_region_map.npy", "Step08 warm map")).astype(np.float32),
        "representative_zone": np.load(require(step08 / "step08_descriptor_representative_zone_map.npy", "Step08 representative map")).astype(np.float32),
        "interest": np.load(require(step08 / "step08_descriptor_interest_map.npy", "Step08 interest map")).astype(np.float32),
    }

    selected = selected.copy()
    selected["date"] = pd.to_datetime(selected["date"]).dt.strftime("%Y-%m-%d")
    selected["expected_class"] = selected["expected_class"].astype(int)
    selected["row_id"] = np.arange(len(selected), dtype=int)
    selected["expected_class_label"] = selected["expected_class"].map(class_label)

    if temp.shape != (EXPECTED_N_DAYS, *EXPECTED_SHAPE):
        raise ValueError(f"Unexpected TEMPpred shape: {temp.shape}")
    if std.shape != temp.shape:
        raise ValueError(f"Unexpected STD shape: {std.shape}")
    if mask.shape != EXPECTED_SHAPE or int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected Step00 mask: shape={mask.shape}, valid={int(mask.sum())}")
    if not np.array_equal(mask, step10e_mask):
        raise ValueError("Step10E mask does not match Step00 mask_common.")
    if len(selected) != EXPECTED_N_DAYS:
        raise ValueError(f"Expected 20 selected dates, found {len(selected)}")
    if dict(selected["expected_class"].value_counts().sort_index()) != {1: 10, 6: 10}:
        raise ValueError(f"Expected 10 C01 and 10 C06, found {dict(selected['expected_class'].value_counts().sort_index())}")
    for key, arr in descriptor_maps.items():
        if arr.shape != (EXPECTED_CLASSES, *EXPECTED_SHAPE):
            raise ValueError(f"Unexpected Step08 {key} map shape: {arr.shape}")

    temp[:, ~mask] = np.nan
    std[:, ~mask] = np.nan
    temp_norm = normalize_temppred(temp, mask, stats)

    features, sparse_codes = encode_with_fixed_dictionary(temp_norm, step05 / "canonical_dictionary.npz")
    scaler_mean, scaler_scale = scaler_from_canonical(canonical_features)
    scaled = ((features - scaler_mean) / scaler_scale).astype(np.float32)
    if features.shape != EXPECTED_FEATURE_SHAPE:
        raise ValueError(f"Unexpected feature matrix shape: {features.shape}")

    class_ids05 = assignments05["class_id"].astype(int).to_numpy()
    centroids = np.vstack([canonical_scaled[class_ids05 == c].mean(axis=0) for c in range(1, EXPECTED_CLASSES + 1)]).astype(np.float32)
    distances = np.sqrt(np.sum((scaled[:, None, :].astype(np.float64) - centroids[None, :, :].astype(np.float64)) ** 2, axis=2)).astype(np.float32)
    order = np.argsort(distances, axis=1)
    predicted = (order[:, 0] + 1).astype(np.int32)
    nearest = distances[np.arange(EXPECTED_N_DAYS), order[:, 0]]
    second = distances[np.arange(EXPECTED_N_DAYS), order[:, 1]]
    margin = second - nearest
    confidence = (margin / np.maximum(second, 1e-9)).astype(np.float32)

    canonical_winner_distances: dict[int, np.ndarray] = {}
    canonical_thresholds: dict[int, float] = {}
    for c in range(1, EXPECTED_CLASSES + 1):
        idx = np.where(class_ids05 == c)[0]
        d = np.sqrt(np.sum((canonical_scaled[idx].astype(np.float64) - centroids[c - 1].astype(np.float64)) ** 2, axis=1))
        canonical_winner_distances[c] = d.astype(np.float32)
        canonical_thresholds[c] = float(np.nanpercentile(d, 90))
    confidence_q25 = float(np.nanpercentile(confidence, 25))
    low_confidence = np.array(
        [
            bool(confidence[i] <= confidence_q25 or nearest[i] > canonical_thresholds[int(predicted[i])])
            for i in range(EXPECTED_N_DAYS)
        ],
        dtype=bool,
    )

    corr = np.full((EXPECTED_N_DAYS, EXPECTED_CLASSES), np.nan, dtype=np.float32)
    rmse = np.full((EXPECTED_N_DAYS, EXPECTED_CLASSES), np.nan, dtype=np.float32)
    for i in range(EXPECTED_N_DAYS):
        for c in range(EXPECTED_CLASSES):
            corr[i, c] = masked_corr(temp_norm[i], prototypes[c], mask)
            rmse[i, c] = masked_rmse(temp_norm[i], prototypes[c], mask)
    corr_best = (np.nanargmax(corr, axis=1) + 1).astype(np.int32)
    rmse_best = (np.nanargmin(rmse, axis=1) + 1).astype(np.int32)

    assigned_maps = {key: arr[predicted - 1].astype(np.float32) for key, arr in descriptor_maps.items()}

    assignment_rows = []
    confidence_rows = []
    comparison_rows = []
    similarity_rows = []
    mismatch_rows = []
    direct_rows = []
    direct_diff_rows = []
    overlap_rows = []
    ranking_rows = []

    desc_by_class = descriptor_df.copy()
    desc_by_class["class_id"] = desc_by_class["class_id"].astype(int)

    for i in range(EXPECTED_N_DAYS):
        row = selected.loc[i]
        expected = int(row["expected_class"])
        pred = int(predicted[i])
        desc = desc_by_class.loc[desc_by_class["class_id"] == pred].iloc[0].to_dict()
        expected_desc = desc_by_class.loc[desc_by_class["class_id"] == expected].iloc[0].to_dict()
        rank_text = "|".join(class_label(int(c + 1)) for c in order[i])
        temp_stats = masked_stats("TEMPpred", temp[i], mask)
        norm_stats = masked_stats("TEMPpred_norm", temp_norm[i], mask)
        std_stats = masked_stats("STD_variance", std[i], mask)
        grad = gradient_map(temp_norm[i], mask)
        locvar = local_variance_proxy(temp_norm[i], mask)
        grad_vals = grad[mask & np.isfinite(grad)]
        loc_vals = locvar[mask & np.isfinite(locvar)]
        temp_vals = temp_norm[i][mask & np.isfinite(temp_norm[i])]
        p33 = float(np.nanpercentile(temp_vals, 33.333))
        p66 = float(np.nanpercentile(temp_vals, 66.667))
        cold = temp_norm[i] <= p33
        warm = temp_norm[i] >= p66
        neutral = ~(cold | warm)
        high_grad_thr = float(np.nanpercentile(grad_vals, 90)) if grad_vals.size else float("nan")
        high_grad = (grad >= high_grad_thr) & mask if np.isfinite(high_grad_thr) else np.zeros_like(mask, dtype=bool)
        residual_pred = masked_rmse(temp_norm[i], prototypes[pred - 1], mask)
        residual_expected = masked_rmse(temp_norm[i], prototypes[expected - 1], mask)

        std_norm = minmax01(std[i], mask)
        interest = assigned_maps["interest"][i]
        boundary = assigned_maps["boundary"][i]
        gradient = assigned_maps["gradient"][i]
        std_top10 = std[i] >= np.nanpercentile(std[i][mask], 90)
        interest_top10 = interest >= np.nanpercentile(interest[mask], 90)
        x_std, y_std = weighted_centroid(std_top10.astype(np.float32), x_km, y_km, mask)
        x_int, y_int = weighted_centroid(interest_top10.astype(np.float32), x_km, y_km, mask)
        centroid_distance = float(np.sqrt((x_std - x_int) ** 2 + (y_std - y_int) ** 2)) if np.isfinite(x_std) and np.isfinite(x_int) else float("nan")
        overlap_interest10 = top_overlap(std[i], interest, mask, 90)
        overlap_interest20 = top_overlap(std[i], interest, mask, 80)
        overlap_boundary10 = top_overlap(std[i], boundary, mask, 90)
        overlap_gradient10 = top_overlap(std[i], gradient, mask, 90)

        planner_score = (
            0.30 * float(confidence[i])
            + 0.25 * float(np.nanmean(std_norm[mask]))
            + 0.20 * float(overlap_interest10 if np.isfinite(overlap_interest10) else 0.0)
            + 0.15 * float(desc.get("interest_mean", 0.0))
            + 0.10 * (1.0 if expected == pred else 0.45)
        )

        assignment_rows.append(
            {
                "row_id": i,
                "date": str(row["date"]),
                "day_index_370": int(row["day_index_370"]),
                "expected_class": expected,
                "expected_class_label": class_label(expected),
                "predicted_class": pred,
                "predicted_class_label": class_label(pred),
                "predicted_step08_class_label": str(desc.get("class_label", class_label(pred))),
                "predicted_cv_regime_label": str(desc.get("cv_regime_label", "")),
                "predicted_qualitative_regime_label": str(desc.get("qualitative_regime_label", "")),
                "match_expected": bool(expected == pred),
                "nearest_centroid_distance": float(nearest[i]),
                "second_centroid_distance": float(second[i]),
                "confidence_margin": float(margin[i]),
                "confidence_score": float(confidence[i]),
                "class_distance_rank": rank_text,
                "best_prototype_corr_class": int(corr_best[i]),
                "best_prototype_rmse_class": int(rmse_best[i]),
                "feature_vs_corr_mismatch": bool(corr_best[i] != pred),
                "feature_vs_rmse_mismatch": bool(rmse_best[i] != pred),
                "low_confidence_flag": bool(low_confidence[i]),
            }
        )
        confidence_rows.append(
            {
                "row_id": i,
                "date": str(row["date"]),
                "expected_class": expected,
                "predicted_class": pred,
                "nearest_distance": float(nearest[i]),
                "second_distance": float(second[i]),
                "margin": float(margin[i]),
                "confidence_score": float(confidence[i]),
                "confidence_q25_threshold": confidence_q25,
                "winner_distance_canonical_p90_threshold": canonical_thresholds[pred],
                "low_confidence_flag": bool(low_confidence[i]),
            }
        )
        comparison_rows.append(
            {
                "row_id": i,
                "date": str(row["date"]),
                "day_index_370": int(row["day_index_370"]),
                "expected_class": expected,
                "expected_class_label": class_label(expected),
                "predicted_class": pred,
                "predicted_class_label": class_label(pred),
                "match_expected": bool(expected == pred),
                "transition": f"{class_label(expected)}->{class_label(pred)}",
                "confidence_score": float(confidence[i]),
                "nearest_centroid_distance": float(nearest[i]),
                "notes": "preserved" if expected == pred else "changed_after_geostatistical_TEMPpred_generation",
            }
        )
        sim_row = {
            "row_id": i,
            "date": str(row["date"]),
            "expected_class": expected,
            "predicted_class": pred,
            "best_corr_class": int(corr_best[i]),
            "best_rmse_class": int(rmse_best[i]),
        }
        sim_row.update({f"corr_C{c+1:02d}": float(corr[i, c]) for c in range(EXPECTED_CLASSES)})
        sim_row.update({f"rmse_C{c+1:02d}": float(rmse[i, c]) for c in range(EXPECTED_CLASSES)})
        similarity_rows.append(sim_row)
        if expected != pred or corr_best[i] != pred or rmse_best[i] != pred:
            mismatch_rows.append(
                {
                    "row_id": i,
                    "date": str(row["date"]),
                    "expected_class": expected,
                    "predicted_class": pred,
                    "best_corr_class": int(corr_best[i]),
                    "best_rmse_class": int(rmse_best[i]),
                    "expected_vs_predicted_mismatch": bool(expected != pred),
                    "feature_vs_corr_mismatch": bool(corr_best[i] != pred),
                    "feature_vs_rmse_mismatch": bool(rmse_best[i] != pred),
                    "confidence_score": float(confidence[i]),
                }
            )
        direct_row = {
            "row_id": i,
            "date": str(row["date"]),
            "expected_class": expected,
            "predicted_class": pred,
            **temp_stats,
            **norm_stats,
            "gradient_mean": float(np.nanmean(grad_vals)) if grad_vals.size else float("nan"),
            "gradient_p90": float(np.nanpercentile(grad_vals, 90)) if grad_vals.size else float("nan"),
            "gradient_p95": float(np.nanpercentile(grad_vals, 95)) if grad_vals.size else float("nan"),
            "gradient_max": float(np.nanmax(grad_vals)) if grad_vals.size else float("nan"),
            "boundary_score": float(np.nanmean(grad_vals >= high_grad_thr)) if grad_vals.size and np.isfinite(high_grad_thr) else float("nan"),
            "heterogeneity_score": float(np.nanstd(temp_vals)) if temp_vals.size else float("nan"),
            "local_variance_mean": float(np.nanmean(loc_vals)) if loc_vals.size else float("nan"),
            "local_variance_p90": float(np.nanpercentile(loc_vals, 90)) if loc_vals.size else float("nan"),
            "entropy_score": entropy_score(temp_vals),
            "cold_fraction": float(np.mean(cold[mask])),
            "warm_fraction": float(np.mean(warm[mask])),
            "neutral_fraction": float(np.mean(neutral[mask])),
            "residual_rmse_vs_predicted_prototype": float(residual_pred),
            "residual_rmse_vs_expected_prototype": float(residual_expected),
        }
        direct_rows.append(direct_row)
        direct_diff_rows.append(
            {
                "row_id": i,
                "date": str(row["date"]),
                "expected_class": expected,
                "predicted_class": pred,
                "direct_gradient_mean_minus_assigned": direct_row["gradient_mean"] - float(desc.get("gradient_mean", np.nan)),
                "direct_boundary_score_minus_assigned": direct_row["boundary_score"] - float(desc.get("boundary_score", np.nan)),
                "direct_heterogeneity_minus_assigned": direct_row["heterogeneity_score"] - float(desc.get("heterogeneity_score", np.nan)),
                "direct_cold_fraction_minus_assigned": direct_row["cold_fraction"] - float(desc.get("cold_fraction", np.nan)),
                "direct_warm_fraction_minus_assigned": direct_row["warm_fraction"] - float(desc.get("warm_fraction", np.nan)),
                "residual_rmse_vs_predicted_prototype": float(residual_pred),
                "residual_rmse_vs_expected_prototype": float(residual_expected),
            }
        )
        overlap_rows.append(
            {
                "row_id": i,
                "date": str(row["date"]),
                "expected_class": expected,
                "predicted_class": pred,
                **std_stats,
                "overlap_top10_STD_top10_interest": float(overlap_interest10),
                "overlap_top20_STD_top20_interest": float(overlap_interest20),
                "overlap_top10_STD_top10_boundary": float(overlap_boundary10),
                "overlap_top10_STD_top10_gradient": float(overlap_gradient10),
                "std_top10_centroid_x_km": x_std,
                "std_top10_centroid_y_km": y_std,
                "interest_top10_centroid_x_km": x_int,
                "interest_top10_centroid_y_km": y_int,
                "std_interest_centroid_distance_km": centroid_distance,
            }
        )
        ranking_rows.append(
            {
                "row_id": i,
                "date": str(row["date"]),
                "day_index_370": int(row["day_index_370"]),
                "expected_class": expected,
                "predicted_class": pred,
                "match_expected": bool(expected == pred),
                "confidence_score": float(confidence[i]),
                "STD_variance_mean": std_stats["STD_variance_mean"],
                "STD_variance_max": std_stats["STD_variance_max"],
                "STD_variance_p95": std_stats["STD_variance_p95"],
                "overlap_top10_STD_top10_interest": float(overlap_interest10),
                "assigned_interest_mean": float(desc.get("interest_mean", np.nan)),
                "assigned_gradient_mean": float(desc.get("gradient_mean", np.nan)),
                "assigned_boundary_score": float(desc.get("boundary_score", np.nan)),
                "planner_score": float(planner_score),
            }
        )

    assignments_df = pd.DataFrame(assignment_rows)
    confidence_df = pd.DataFrame(confidence_rows)
    comparison_df = pd.DataFrame(comparison_rows)
    similarity_df = pd.DataFrame(similarity_rows)
    mismatch_df = pd.DataFrame(mismatch_rows)
    low_conf_df = confidence_df[confidence_df["low_confidence_flag"]].copy()
    direct_df = pd.DataFrame(direct_rows)
    direct_diff_df = pd.DataFrame(direct_diff_rows)
    overlap_df = pd.DataFrame(overlap_rows)
    ranking_df = pd.DataFrame(ranking_rows).sort_values("planner_score", ascending=False).reset_index(drop=True)
    recommended_visual = ranking_df.sort_values(["STD_variance_mean", "overlap_top10_STD_top10_interest"], ascending=False).head(12).copy()
    recommended_planner = pd.concat(
        [
            ranking_df[ranking_df["predicted_class"] == 1].head(3),
            ranking_df[ranking_df["predicted_class"] == 6].head(3),
            ranking_df.head(5),
            ranking_df[~ranking_df["match_expected"]].head(3),
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["date"]).sort_values("planner_score", ascending=False)

    assigned_desc_df = assignments_df.merge(desc_by_class, left_on="predicted_class", right_on="class_id", how="left", suffixes=("", "_descriptor"))
    transition_summary = (
        comparison_df.groupby(["expected_class", "predicted_class"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["expected_class", "predicted_class"])
    )
    transition_matrix = np.zeros((EXPECTED_CLASSES, EXPECTED_CLASSES), dtype=int)
    for _, row in transition_summary.iterrows():
        transition_matrix[int(row["expected_class"]) - 1, int(row["predicted_class"]) - 1] = int(row["count"])

    assignments_df.to_csv(out_dir / "step09b_classification_assignments.csv", index=False)
    confidence_df.to_csv(out_dir / "step09b_classification_confidence.csv", index=False)
    comparison_df.to_csv(out_dir / "step09b_expected_vs_predicted_class_comparison.csv", index=False)
    transition_summary.to_csv(out_dir / "step09b_class_transition_summary.csv", index=False)
    similarity_df.to_csv(out_dir / "step09b_prototype_similarity.csv", index=False)
    mismatch_df.to_csv(out_dir / "step09b_mismatch_diagnostics.csv", index=False)
    assigned_desc_df.to_csv(out_dir / "step09b_assigned_class_descriptors.csv", index=False)
    direct_df.to_csv(out_dir / "step09b_temppred_direct_descriptors.csv", index=False)
    direct_diff_df.to_csv(out_dir / "step09b_direct_vs_assigned_descriptor_differences.csv", index=False)
    overlap_df.to_csv(out_dir / "step09b_std_descriptor_overlap_metrics.csv", index=False)
    ranking_df.to_csv(out_dir / "step09b_recommended_days_for_planner.csv", index=False)
    recommended_visual.to_csv(out_dir / "step09b_recommended_days_for_visual_review.csv", index=False)
    low_conf_df.to_csv(out_dir / "step09b_low_confidence_days.csv", index=False)
    step10e_day_metrics.to_csv(out_dir / "step09b_input_step10e_day_metrics_copy.csv", index=False)
    comparison_370.to_csv(out_dir / "step09b_input_step10e_comparison_to_original_370_copy.csv", index=False)

    np.save(out_dir / "step09b_temppred_top20_normalized.npy", temp_norm)
    np.save(out_dir / "step09b_temppred_feature_matrix.npy", features)
    np.save(out_dir / "step09b_temppred_scaled_feature_matrix.npy", scaled)
    np.savez_compressed(out_dir / "step09b_temppred_sparse_codes.npz", sparse_codes=sparse_codes, shape=np.array(sparse_codes.shape, dtype=np.int64))
    np.save(out_dir / "step09b_predicted_classes.npy", predicted)
    np.save(out_dir / "step09b_distance_to_class_centroids.npy", distances)
    np.save(out_dir / "step09b_prototype_correlations.npy", corr)
    np.save(out_dir / "step09b_prototype_rmse.npy", rmse)
    for key, arr in assigned_maps.items():
        np.save(out_dir / f"step09b_assigned_descriptor_{key}_map.npy", arr)
    np.savez_compressed(out_dir / "step09b_all_assigned_descriptor_maps.npz", **assigned_maps, predicted_classes=predicted, expected_classes=selected["expected_class"].to_numpy(), mask=mask)

    save_expected_predicted_timeline(comparison_df, fig_dir / "step09b_expected_vs_predicted_class_timeline.png")
    save_heatmap(
        transition_matrix,
        [class_label(i) for i in range(1, EXPECTED_CLASSES + 1)],
        [class_label(i) for i in range(1, EXPECTED_CLASSES + 1)],
        "Expected vs predicted class transition matrix",
        fig_dir / "step09b_class_transition_matrix.png",
        "Blues",
        annotate=True,
    )
    save_heatmap(
        distances.T,
        selected["date"].astype(str).str.slice(5).tolist(),
        [class_label(i) for i in range(1, EXPECTED_CLASSES + 1)],
        "Distance to Step05 class centroids",
        fig_dir / "step09b_distance_to_centroids_heatmap.png",
        "magma_r",
    )
    save_heatmap(
        corr.T,
        selected["date"].astype(str).str.slice(5).tolist(),
        [class_label(i) for i in range(1, EXPECTED_CLASSES + 1)],
        "Prototype correlation",
        fig_dir / "step09b_prototype_similarity_heatmap.png",
        "viridis",
    )
    save_confidence_barplot(confidence_df.assign(date=selected["date"]), fig_dir / "step09b_confidence_margin_barplot.png")
    plot_df = comparison_df.copy()
    plot_df["date"] = selected["date"]
    save_grouped_maps(temp, plot_df, "predicted_class", fig_dir / "step09b_TEMPpred_grouped_by_predicted_class.png", "TEMPpred grouped by predicted class", "coolwarm", TEMP_VMIN, TEMP_VMAX)
    save_grouped_maps(temp, plot_df, "expected_class", fig_dir / "step09b_TEMPpred_grouped_by_expected_class.png", "TEMPpred grouped by expected class", "coolwarm", TEMP_VMIN, TEMP_VMAX)
    save_temppred_prototype_panel(temp_norm, prototypes, comparison_df, "predicted_class", fig_dir / "step09b_TEMPpred_vs_predicted_prototype_panel.png", "TEMPpred vs predicted prototype")
    save_temppred_prototype_panel(temp_norm, prototypes, comparison_df, "expected_class", fig_dir / "step09b_TEMPpred_vs_expected_prototype_panel.png", "TEMPpred vs expected prototype")
    save_std_interest_panel(std, assigned_maps["interest"], ranking_df, fig_dir / "step09b_STD_vs_assigned_interest_panel.png")
    save_top_recommended_panel(temp, std, ranking_df, fig_dir / "step09b_top_recommended_days_panel.png")
    save_mismatch_panel(temp, std, comparison_df, fig_dir / "step09b_mismatch_cases_panel.png")

    for p in fig_dir.glob("*.png"):
        shutil.copy2(p, out_dir / p.name)

    c01_preserved = int(((comparison_df["expected_class"] == 1) & (comparison_df["predicted_class"] == 1)).sum())
    c06_preserved = int(((comparison_df["expected_class"] == 6) & (comparison_df["predicted_class"] == 6)).sum())
    expected_counts = {str(k): int(v) for k, v in selected["expected_class"].value_counts().sort_index().items()}
    predicted_counts = {str(k): int(v) for k, v in assignments_df["predicted_class"].value_counts().sort_index().items()}
    mismatches_expected = comparison_df[~comparison_df["match_expected"].astype(bool)].copy()
    all_descriptor_shapes_ok = all(arr.shape == (EXPECTED_N_DAYS, *EXPECTED_SHAPE) for arr in assigned_maps.values())

    checks = {
        "top20_temppred_classified": int(len(assignments_df)) == EXPECTED_N_DAYS,
        "feature_matrix_shape": list(features.shape),
        "feature_matrix_expected": list(EXPECTED_FEATURE_SHAPE),
        "dictionary_fit_on_top20": False,
        "scaler_fit_on_top20": False,
        "scaler_reconstructed_from_step05_canonical_feature_matrix": True,
        "normalization_used_step00_stats": True,
        "classification_used_step00_mask_common": True,
        "std_used_for_classification": False,
        "std_used_only_for_diagnostics": True,
        "descriptors_from_step08": True,
        "assigned_descriptor_map_shapes": {k: list(v.shape) for k, v in assigned_maps.items()},
        "assigned_descriptor_maps_shape_ok": bool(all_descriptor_shapes_ok),
        "expected_classes_only_c01_c06": sorted(selected["expected_class"].astype(int).unique().tolist()) == [1, 6],
        "predicted_classes_in_c01_to_c06": bool(np.all((predicted >= 1) & (predicted <= EXPECTED_CLASSES))),
        "mask_valid_cells": int(mask.sum()),
        "step10e_mask_matches_step00": bool(np.array_equal(mask, step10e_mask)),
        "low_confidence_count": int(len(low_conf_df)),
        "expected_vs_predicted_mismatch_count": int(len(mismatches_expected)),
        "prototype_mismatch_diagnostic_rows": int(len(mismatch_df)),
        "c01_preserved_count": c01_preserved,
        "c06_preserved_count": c06_preserved,
        "expected_counts": expected_counts,
        "predicted_counts": predicted_counts,
        "transition_matrix": transition_matrix,
        "class_sizes_step05": class_sizes05.to_dict(orient="records"),
    }

    verdict = "READY_FOR_STEP10F_STD_DESCRIPTOR_FUSION_TOP20"
    warnings = []
    if len(mismatches_expected) > 0 or len(low_conf_df) > 0:
        verdict = "STEP09B_COMPLETED_WITH_WARNINGS_REVIEW_MISMATCHES"
    if features.shape != EXPECTED_FEATURE_SHAPE or not all_descriptor_shapes_ok:
        verdict = "STEP09B_FAILED"
    if len(mismatches_expected) > 0:
        warnings.append(f"{len(mismatches_expected)} expected-vs-predicted class changes found.")
    if len(low_conf_df) > 0:
        warnings.append(f"{len(low_conf_df)} low-confidence days found by combined margin/distance criterion.")
    if sorted(np.unique(predicted).tolist()) != sorted(np.unique(selected["expected_class"].astype(int).tolist())):
        warnings.append("Predicted classes are not limited to the originally selected C01/C06 set.")

    config = {
        "roi": "FRESNEL_PAPER_ROI_X490",
        "n_days": EXPECTED_N_DAYS,
        "classes": EXPECTED_CLASSES,
        "patch_height": PATCH_H,
        "patch_width": PATCH_W,
        "dictionary_size": DICTIONARY_SIZE,
        "classification_method": "nearest Step05 class centroid in StandardScaler-transformed sparse-code feature space",
        "std_definition": "variance",
        "std_used_for_classification": False,
        "low_confidence_rule": "confidence <= top20 Q25 OR nearest centroid distance > Step05 class p90 member-to-centroid distance",
        "figure_scales": {
            "TEMPpred_physical": {"vmin": TEMP_VMIN, "vmax": TEMP_VMAX, "cmap": "coolwarm"},
            "STD_variance": {"vmin": STD_VMIN, "vmax": STD_VMAX, "cmap": "viridis"},
            "TEMPpred_normalized": {"vmin": -NORM_VLIM, "vmax": NORM_VLIM, "cmap": "coolwarm"},
        },
    }
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "script": str(Path(__file__).resolve()),
        "inputs": {"step00": str(step00), "step05": str(step05), "step08": str(step08), "step10e": str(step10e)},
        "normalization_stats": stats,
        "outputs": {"output_dir": str(out_dir)},
        "warnings": warnings,
        "verdict": verdict,
    }
    write_json(out_dir / "step09b_config.json", config)
    write_json(out_dir / "step09b_metadata.json", metadata)
    write_json(out_dir / "step09b_checks.json", checks)

    top_global = recommended_planner.head(5)[["date", "expected_class", "predicted_class", "planner_score", "STD_variance_mean", "overlap_top10_STD_top10_interest"]]
    mismatch_lines = (
        ["- none"]
        if mismatches_expected.empty
        else [
            f"- {r.date}: {class_label(int(r.expected_class))} -> {class_label(int(r.predicted_class))}, confidence={float(r.confidence_score):.4f}"
            for r in mismatches_expected.itertuples()
        ]
    )
    low_conf_lines = (
        ["- none"]
        if low_conf_df.empty
        else [
            f"- {r.date}: predicted {class_label(int(r.predicted_class))}, confidence={float(r.confidence_score):.4f}, nearest={float(r.nearest_distance):.3f}"
            for r in low_conf_df.itertuples()
        ]
    )
    top_lines = [
        f"- {r.date}: expected {class_label(int(r.expected_class))}, predicted {class_label(int(r.predicted_class))}, score={float(r.planner_score):.3f}, STD_mean={float(r.STD_variance_mean):.4f}"
        for r in top_global.itertuples()
    ]
    transition_lines = [
        f"- {class_label(int(r.expected_class))} -> {class_label(int(r.predicted_class))}: {int(r.count)}"
        for r in transition_summary.itertuples()
    ]

    summary = [
        "# Step09B Summary",
        "",
        f"- Output: `{out_dir}`",
        f"- Verdict: **{verdict}**",
        f"- Expected counts: {expected_counts}",
        f"- Predicted counts: {predicted_counts}",
        f"- C01 preserved: {c01_preserved}/10",
        f"- C06 preserved: {c06_preserved}/10",
        f"- Expected-vs-predicted mismatches: {len(mismatches_expected)}",
        f"- Low-confidence days: {len(low_conf_df)}",
        "",
        "## Top Planner Candidates",
        *top_lines,
    ]
    (out_dir / "step09b_summary.md").write_text("\n".join(summary), encoding="utf-8")

    report = [
        "# Step09B Top20 C01/C06 TEMPpred Classification Report",
        "",
        "## Method",
        "The 20 Step10E TEMPpred ROI maps were normalized with Step00 global mean/std, encoded with the fixed Step05 dictionary, scaled with mean/std reconstructed from the Step05 canonical feature matrix, and classified by nearest canonical class centroid. STD/variance was used only for diagnostic overlap with Step08 descriptor maps.",
        "",
        "## Expected vs Predicted",
        *transition_lines,
        "",
        f"- C01 preserved: {c01_preserved}/10",
        f"- C06 preserved: {c06_preserved}/10",
        "",
        "## Mismatches",
        *mismatch_lines,
        "",
        "## Low Confidence Days",
        *low_conf_lines,
        "",
        "## Planner-Oriented Recommendations",
        *top_lines,
        "",
        "## Interpretation",
        "Class changes should be read as a diagnostic of how the geostatistical TEMPpred field moved in the Step05 sparse-code feature space, not as a new ground-truth label. Higher STD-interest overlap is useful for the next STD + descriptor fusion step.",
        "",
        "## Verdict",
        verdict,
    ]
    (out_dir / "step09b_report.md").write_text("\n".join(report), encoding="utf-8")

    next_step = [
        "# Step09B Next Step Recommendation",
        "",
        "Use the Step09B assigned descriptor maps and Step10E STD/variance maps in Step10F to test STD + descriptor fusion for the top20 C01/C06 cases. Review mismatches and low-confidence days before choosing final planner examples.",
        "",
        verdict,
    ]
    (out_dir / "step09b_next_step_recommendation.md").write_text("\n".join(next_step), encoding="utf-8")
    shutil.copy2(Path(__file__).resolve(), out_dir / Path(__file__).name)

    print(f"Step09B complete: {out_dir}")
    print(f"Predicted counts: {predicted_counts}")
    print(f"C01 preserved: {c01_preserved}/10")
    print(f"C06 preserved: {c06_preserved}/10")
    print(f"Low confidence days: {len(low_conf_df)}")
    print(f"Mismatches: {len(mismatches_expected)}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
