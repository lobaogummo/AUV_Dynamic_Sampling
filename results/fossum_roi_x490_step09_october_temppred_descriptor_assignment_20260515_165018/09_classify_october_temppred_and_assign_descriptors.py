"""Step09: classify October TEMPpred into canonical ROI x490 classes.

Downstream-only stage:
- reads Step06 October TEMPpred/STD;
- normalizes TEMPpred with Step00 stats;
- encodes with the fixed Step05 dictionary;
- reconstructs StandardScaler from Step05 canonical features;
- classifies by nearest Step05 class centroid in scaled feature space;
- assigns Step08 descriptor maps by predicted class.

STD is loaded only for diagnostic overlap metrics and figures, never for
classification.
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
DEFAULT_STEP06 = RESULTS_ROOT / "october_surface_temppred_std_roi_x490_20260511_155923"
DEFAULT_STEP08 = RESULTS_ROOT / "fossum_roi_x490_step08_final_descriptors_20260514_164854"

EXPECTED_N_DAYS = 31
EXPECTED_CLASSES = 6
EXPECTED_SHAPE = (72, 117)
EXPECTED_FEATURE_SHAPE = (31, 15288)
EXPECTED_VALID_CELLS = 8004
PATCH_H = 24
PATCH_W = 40
DICTIONARY_SIZE = 4


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
    av = a[mask & np.isfinite(a) & np.isfinite(b)].astype(np.float64)
    bv = b[mask & np.isfinite(a) & np.isfinite(b)].astype(np.float64)
    if av.size < 2:
        return float("nan")
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
    diff = a[valid] - b[valid]
    return float(np.sqrt(np.nanmean(diff * diff)))


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


def direct_descriptor_rows(X_norm: np.ndarray, assigned: np.ndarray, mask: np.ndarray, dates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, arr in enumerate(X_norm):
        fill = float(np.nanmean(arr[mask]))
        filled = np.where(mask, arr, fill).astype(np.float32)
        gy, gx = np.gradient(filled)
        grad = np.hypot(gx, gy).astype(np.float32)
        grad[~mask] = np.nan
        vals = arr[mask]
        rows.append(
            {
                "day_index": int(dates.loc[i, "day_index"]),
                "date": str(dates.loc[i, "date"]),
                "assigned_class_id": int(assigned[i]),
                "temppred_norm_mean": float(np.nanmean(vals)),
                "temppred_norm_std": float(np.nanstd(vals)),
                "temppred_norm_p05": float(np.nanpercentile(vals, 5)),
                "temppred_norm_p50": float(np.nanpercentile(vals, 50)),
                "temppred_norm_p95": float(np.nanpercentile(vals, 95)),
                "direct_gradient_mean": float(np.nanmean(grad[mask])),
                "direct_gradient_p90": float(np.nanpercentile(grad[mask], 90)),
                "direct_gradient_p95": float(np.nanpercentile(grad[mask], 95)),
            }
        )
    return pd.DataFrame(rows)


def save_heatmap(matrix: np.ndarray, xlabels: list[str], ylabels: list[str], title: str, out_path: Path, cmap: str = "viridis") -> None:
    fig, ax = plt.subplots(figsize=(max(8, 0.34 * len(xlabels)), max(4, 0.45 * len(ylabels))))
    im = ax.imshow(matrix, aspect="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xticks(np.arange(len(xlabels)))
    ax.set_xticklabels(xlabels, rotation=90, fontsize=7)
    ax.set_yticks(np.arange(len(ylabels)))
    ax.set_yticklabels(ylabels)
    plt.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_timeline(assignments: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 3.6))
    x = np.arange(len(assignments))
    y = assignments["assigned_class_id"].astype(int).to_numpy()
    ax.scatter(x, y, c=y, cmap="tab10", s=55)
    ax.plot(x, y, color="#555555", alpha=0.35)
    ax.set_xticks(x)
    ax.set_xticklabels(assignments["date"].astype(str).str.slice(5).tolist(), rotation=90, fontsize=8)
    ax.set_yticks(range(1, EXPECTED_CLASSES + 1))
    ax.set_ylabel("class")
    ax.set_title("October TEMPpred assigned canonical class")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_grouped_temppred(X_norm: np.ndarray, assigned: np.ndarray, dates: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(EXPECTED_CLASSES, 6, figsize=(15, 2.5 * EXPECTED_CLASSES), squeeze=False)
    for c in range(1, EXPECTED_CLASSES + 1):
        idx = np.where(assigned == c)[0]
        for j in range(6):
            ax = axes[c - 1, j]
            if j >= len(idx):
                ax.axis("off")
                continue
            i = int(idx[j])
            ax.imshow(X_norm[i], origin="lower", cmap="coolwarm", aspect="auto")
            ax.set_title(f"C{c:02d} {dates.loc[i, 'date']}", fontsize=9)
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_day_panels(
    X_norm: np.ndarray,
    prototypes: np.ndarray,
    std: np.ndarray,
    interest: np.ndarray,
    assigned: np.ndarray,
    dates: pd.DataFrame,
    out_path: Path,
    max_days: int = 12,
) -> None:
    n = min(max_days, X_norm.shape[0])
    fig, axes = plt.subplots(n, 5, figsize=(15, 2.6 * n), squeeze=False)
    for r in range(n):
        c = int(assigned[r]) - 1
        residual = X_norm[r] - prototypes[c]
        maps = [X_norm[r], prototypes[c], residual, std[r], interest[r]]
        titles = ["TEMPpred norm", f"prototype C{c+1:02d}", "residual", "STD diag", "assigned interest"]
        cmaps = ["coolwarm", "coolwarm", "coolwarm", "magma", "inferno"]
        for col in range(5):
            ax = axes[r, col]
            ax.imshow(maps[col], origin="lower", cmap=cmaps[col], aspect="auto")
            ax.set_title(f"{dates.loc[r, 'date']} | {titles[col]}", fontsize=8)
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_assigned_maps_panel(maps: np.ndarray, dates: pd.DataFrame, out_path: Path, title: str, cmap: str) -> None:
    n = maps.shape[0]
    cols = 7
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(2.4 * cols, 2.1 * rows), squeeze=False)
    for i, ax in enumerate(axes.ravel()):
        if i >= n:
            ax.axis("off")
            continue
        ax.imshow(maps[i], origin="lower", cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_title(str(dates.loc[i, "date"])[5:], fontsize=8)
        ax.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify October TEMPpred and assign Step08 descriptor maps.")
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--step05", type=Path, default=DEFAULT_STEP05)
    parser.add_argument("--step06", type=Path, default=DEFAULT_STEP06)
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    step00 = args.step00.resolve()
    step05 = args.step05.resolve()
    step06 = args.step06.resolve()
    step08 = args.step08.resolve()
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step09_october_temppred_descriptor_assignment_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir()

    mask = np.load(require(step00 / "mask_common_roi_x490.npy", "Step00 mask")).astype(bool)
    stats = read_json(require(step00 / "normalization_stats.json", "Step00 normalization stats"))
    temp = np.load(require(step06 / "TEMPpred_october_surface_roi_x490.npy", "Step06 TEMPpred")).astype(np.float32)
    std = np.load(require(step06 / "STD_october_surface_roi_x490.npy", "Step06 STD")).astype(np.float32)
    dates = pd.read_csv(require(step06 / "dates_october.csv", "Step06 dates"))
    if "day_index" not in dates.columns:
        dates.insert(0, "day_index", np.arange(1, len(dates) + 1))
    dates["date"] = pd.to_datetime(dates["date"]).dt.strftime("%Y-%m-%d")

    prototypes = np.load(require(step05 / "canonical_prototypes.npy", "Step05 prototypes")).astype(np.float32)
    canonical_features = np.load(require(step05 / "canonical_feature_matrix.npy", "Step05 canonical features")).astype(np.float32)
    canonical_scaled = np.load(require(step05 / "canonical_scaled_feature_matrix.npy", "Step05 scaled features")).astype(np.float32)
    assignments05 = pd.read_csv(require(step05 / "canonical_assignments.csv", "Step05 assignments"))
    descriptor_df = pd.read_csv(require(step08 / "step08_final_class_descriptors.csv", "Step08 descriptors"))
    descriptor_maps = {
        "gradient": np.load(require(step08 / "step08_descriptor_gradient_map.npy", "Step08 gradient map")),
        "boundary": np.load(require(step08 / "step08_descriptor_boundary_map.npy", "Step08 boundary map")),
        "heterogeneity": np.load(require(step08 / "step08_descriptor_heterogeneity_map.npy", "Step08 heterogeneity map")),
        "cold_region": np.load(require(step08 / "step08_descriptor_cold_region_map.npy", "Step08 cold map")),
        "warm_region": np.load(require(step08 / "step08_descriptor_warm_region_map.npy", "Step08 warm map")),
        "representative_zone": np.load(require(step08 / "step08_descriptor_representative_zone_map.npy", "Step08 representative map")),
        "interest": np.load(require(step08 / "step08_descriptor_interest_map.npy", "Step08 interest map")),
    }

    if temp.shape != (EXPECTED_N_DAYS, *EXPECTED_SHAPE):
        raise ValueError(f"Unexpected TEMPpred shape: {temp.shape}")
    if std.shape != temp.shape:
        raise ValueError(f"Unexpected STD shape: {std.shape}")
    if int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected mask valid cells: {int(mask.sum())}")

    temp_norm = normalize_temppred(temp, mask, stats)
    features, sparse_codes = encode_with_fixed_dictionary(temp_norm, step05 / "canonical_dictionary.npz")
    scaler_mean, scaler_scale = scaler_from_canonical(canonical_features)
    scaled = ((features - scaler_mean) / scaler_scale).astype(np.float32)

    if features.shape != EXPECTED_FEATURE_SHAPE:
        raise ValueError(f"Unexpected feature matrix shape: {features.shape}")

    centroids = np.vstack(
        [
            canonical_scaled[assignments05["class_id"].astype(int).to_numpy() == c].mean(axis=0)
            for c in range(1, EXPECTED_CLASSES + 1)
        ]
    ).astype(np.float32)
    diff = scaled[:, None, :] - centroids[None, :, :]
    distances = np.sqrt(np.sum(diff.astype(np.float64) ** 2, axis=2)).astype(np.float32)
    order = np.argsort(distances, axis=1)
    assigned = (order[:, 0] + 1).astype(np.int32)
    nearest = distances[np.arange(EXPECTED_N_DAYS), order[:, 0]]
    second = distances[np.arange(EXPECTED_N_DAYS), order[:, 1]]
    margin = second - nearest
    confidence = (margin / np.maximum(second, 1e-9)).astype(np.float32)

    corr = np.full((EXPECTED_N_DAYS, EXPECTED_CLASSES), np.nan, dtype=np.float32)
    rmse = np.full((EXPECTED_N_DAYS, EXPECTED_CLASSES), np.nan, dtype=np.float32)
    for i in range(EXPECTED_N_DAYS):
        for c in range(EXPECTED_CLASSES):
            corr[i, c] = masked_corr(temp_norm[i], prototypes[c], mask)
            rmse[i, c] = masked_rmse(temp_norm[i], prototypes[c], mask)
    corr_best = (np.nanargmax(corr, axis=1) + 1).astype(np.int32)
    rmse_best = (np.nanargmin(rmse, axis=1) + 1).astype(np.int32)

    assigned_maps = {k: v[assigned - 1].astype(np.float32) for k, v in descriptor_maps.items()}

    assign_rows = []
    confidence_rows = []
    mismatch_rows = []
    overlap_rows = []
    for i in range(EXPECTED_N_DAYS):
        class_id = int(assigned[i])
        desc = descriptor_df.loc[descriptor_df["class_id"].astype(int) == class_id].iloc[0].to_dict()
        assign_rows.append(
            {
                "day_index": int(dates.loc[i, "day_index"]),
                "date": str(dates.loc[i, "date"]),
                "assigned_class_id": class_id,
                "assigned_class_label": str(desc["class_label"]),
                "assigned_cv_regime_label": str(desc["cv_regime_label"]),
                "nearest_centroid_distance": float(nearest[i]),
                "second_centroid_distance": float(second[i]),
                "confidence_margin": float(margin[i]),
                "confidence_score": float(confidence[i]),
                "best_prototype_corr_class": int(corr_best[i]),
                "best_prototype_rmse_class": int(rmse_best[i]),
                "feature_vs_corr_mismatch": bool(corr_best[i] != class_id),
                "feature_vs_rmse_mismatch": bool(rmse_best[i] != class_id),
            }
        )
        confidence_rows.append(
            {
                "day_index": int(dates.loc[i, "day_index"]),
                "date": str(dates.loc[i, "date"]),
                "assigned_class_id": class_id,
                "nearest_distance": float(nearest[i]),
                "second_distance": float(second[i]),
                "margin": float(margin[i]),
                "confidence_score": float(confidence[i]),
                "low_confidence_flag": bool(confidence[i] < 0.05),
            }
        )
        if corr_best[i] != class_id or rmse_best[i] != class_id:
            mismatch_rows.append(assign_rows[-1])
        std_i = std[i].copy()
        std_i[~mask] = np.nan
        std_norm = minmax01(std_i, mask)
        for map_name in ["interest", "boundary", "gradient"]:
            m = assigned_maps[map_name][i]
            valid = mask & np.isfinite(m) & np.isfinite(std_norm)
            overlap_rows.append(
                {
                    "day_index": int(dates.loc[i, "day_index"]),
                    "date": str(dates.loc[i, "date"]),
                    "assigned_class_id": class_id,
                    "descriptor_map": map_name,
                    "std_mean": float(np.nanmean(std_i[mask])),
                    "descriptor_mean": float(np.nanmean(m[mask])),
                    "std_descriptor_product_mean": float(np.nanmean(std_norm[valid] * m[valid])) if np.any(valid) else float("nan"),
                    "top20_std_top20_descriptor_overlap_fraction": float(
                        np.mean(
                            (std_norm[valid] >= np.nanpercentile(std_norm[valid], 80))
                            & (m[valid] >= np.nanpercentile(m[valid], 80))
                        )
                    )
                    if np.any(valid)
                    else float("nan"),
                }
            )

    assignments_df = pd.DataFrame(assign_rows)
    confidence_df = pd.DataFrame(confidence_rows)
    mismatch_df = pd.DataFrame(mismatch_rows)
    low_conf_df = confidence_df[confidence_df["low_confidence_flag"]].copy()
    overlap_df = pd.DataFrame(overlap_rows)
    direct_df = direct_descriptor_rows(temp_norm, assigned, mask, dates)
    assigned_desc_df = assignments_df.merge(descriptor_df, left_on="assigned_class_id", right_on="class_id", how="left")
    similarity_df = pd.DataFrame(
        [
            {
                "day_index": int(dates.loc[i, "day_index"]),
                "date": str(dates.loc[i, "date"]),
                **{f"corr_C{c+1:02d}": float(corr[i, c]) for c in range(EXPECTED_CLASSES)},
                **{f"rmse_C{c+1:02d}": float(rmse[i, c]) for c in range(EXPECTED_CLASSES)},
            }
            for i in range(EXPECTED_N_DAYS)
        ]
    )

    assignments_df.to_csv(out_dir / "step09_temppred_classification_assignments.csv", index=False)
    confidence_df.to_csv(out_dir / "step09_temppred_classification_confidence.csv", index=False)
    similarity_df.to_csv(out_dir / "step09_temppred_prototype_similarity.csv", index=False)
    direct_df.to_csv(out_dir / "step09_temppred_direct_descriptors.csv", index=False)
    assigned_desc_df.to_csv(out_dir / "step09_assigned_class_descriptors.csv", index=False)
    overlap_df.to_csv(out_dir / "step09_std_descriptor_overlap_metrics.csv", index=False)
    low_conf_df.to_csv(out_dir / "step09_low_confidence_days.csv", index=False)
    mismatch_df.to_csv(out_dir / "step09_mismatch_diagnostics.csv", index=False)

    np.save(out_dir / "step09_temppred_normalized.npy", temp_norm)
    np.save(out_dir / "step09_temppred_feature_matrix.npy", features)
    np.save(out_dir / "step09_temppred_scaled_feature_matrix.npy", scaled)
    np.savez_compressed(out_dir / "step09_temppred_sparse_codes.npz", sparse_codes=sparse_codes, shape=np.array(sparse_codes.shape, dtype=np.int64))
    np.save(out_dir / "step09_temppred_assigned_classes.npy", assigned)
    np.save(out_dir / "step09_distance_to_class_centroids.npy", distances)
    np.save(out_dir / "step09_prototype_correlations.npy", corr)
    np.save(out_dir / "step09_prototype_rmse.npy", rmse)
    for key, arr in assigned_maps.items():
        np.save(out_dir / f"step09_assigned_descriptor_{key}_map.npy", arr)
    np.savez_compressed(out_dir / "step09_all_assigned_descriptor_maps.npz", **assigned_maps, assigned_classes=assigned, mask=mask)

    save_timeline(assignments_df, fig_dir / "step09_october_class_timeline.png")
    save_heatmap(distances.T, [str(d)[5:] for d in dates["date"]], [f"C{i:02d}" for i in range(1, 7)], "Distance to class centroids", fig_dir / "step09_distance_to_centroids_heatmap.png", "magma_r")
    save_heatmap(corr.T, [str(d)[5:] for d in dates["date"]], [f"C{i:02d}" for i in range(1, 7)], "Prototype correlation", fig_dir / "step09_prototype_similarity_heatmap.png", "viridis")
    save_grouped_temppred(temp_norm, assigned, dates, fig_dir / "step09_temppred_grouped_by_assigned_class.png")
    save_assigned_maps_panel(assigned_maps["interest"], dates, fig_dir / "step09_assigned_interest_maps_panel.png", "Assigned interest maps", "inferno")
    save_assigned_maps_panel(assigned_maps["boundary"], dates, fig_dir / "step09_assigned_boundary_maps_panel.png", "Assigned boundary maps", "magma")
    save_day_panels(temp_norm, prototypes, std, assigned_maps["interest"], assigned, dates, fig_dir / "step09_per_day_temppred_prototype_std_interest_panels.png")
    fig, ax = plt.subplots(figsize=(12, 3.8))
    ax.plot(dates["date"], confidence, marker="o")
    ax.axhline(0.05, color="red", linestyle="--", linewidth=1)
    ax.set_title("Confidence margin timeline")
    ax.set_ylabel("margin / second distance")
    ax.tick_params(axis="x", rotation=90)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(fig_dir / "step09_confidence_margin_timeline.png", dpi=170)
    plt.close(fig)
    for p in fig_dir.glob("*.png"):
        shutil.copy2(p, out_dir / p.name)

    counts = assignments_df["assigned_class_id"].value_counts().sort_index().to_dict()
    checks = {
        "all_31_temppred_classified": int(len(assignments_df)) == EXPECTED_N_DAYS,
        "feature_matrix_shape": list(features.shape),
        "feature_matrix_expected": list(EXPECTED_FEATURE_SHAPE),
        "dictionary_fit_on_october": False,
        "scaler_fit_on_october": False,
        "normalization_used_step00_stats": True,
        "classification_used_step00_mask_common": True,
        "std_used_for_classification": False,
        "std_used_only_for_diagnostics": True,
        "descriptors_from_step08": True,
        "assigned_descriptor_map_shapes": {k: list(v.shape) for k, v in assigned_maps.items()},
        "mask_valid_cells": int(mask.sum()),
        "low_confidence_count": int(len(low_conf_df)),
        "mismatch_count": int(len(mismatch_df)),
        "class_counts": {str(k): int(v) for k, v in counts.items()},
    }
    verdict = "READY_FOR_STD_DESCRIPTOR_FUSION_FOR_OCTOBER"
    if not checks["all_31_temppred_classified"] or features.shape != EXPECTED_FEATURE_SHAPE:
        verdict = "NOT_READY_FOR_STD_DESCRIPTOR_FUSION_FOR_OCTOBER"
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "script": str(Path(__file__).resolve()),
        "inputs": {"step00": str(step00), "step05": str(step05), "step06": str(step06), "step08": str(step08)},
        "normalization_stats": stats,
        "classification": {
            "method": "nearest Step05 class centroid in StandardScaler-transformed sparse-code feature space",
            "dictionary_fit_on_october": False,
            "scaler_fit_on_october": False,
            "std_used_for_classification": False,
        },
        "outputs": {"output_dir": str(out_dir)},
        "verdict": verdict,
    }
    write_json(out_dir / "step09_metadata.json", metadata)
    write_json(out_dir / "step09_checks.json", checks)

    summary = [
        "# Step09 Summary",
        "",
        f"- Output: `{out_dir}`",
        f"- Verdict: **{verdict}**",
        f"- Class counts: {counts}",
        f"- Low confidence days: {len(low_conf_df)}",
        f"- Feature/prototype mismatch diagnostics rows: {len(mismatch_df)}",
    ]
    (out_dir / "step09_summary.md").write_text("\n".join(summary), encoding="utf-8")
    report = [
        "# Step09 TEMPpred Classification Report",
        "",
        "## Method",
        "October TEMPpred was normalized with Step00 global mean/std, encoded with the fixed Step05 dictionary, scaled with mean/std reconstructed from Step05 canonical features, and classified by nearest class centroid. STD was used only for diagnostic overlap metrics.",
        "",
        "## Class Counts",
    ]
    report.extend([f"- C{int(k):02d}: {int(v)} days" for k, v in counts.items()])
    report.extend(
        [
            "",
            "## Diagnostics",
            f"- Low confidence days: {len(low_conf_df)}",
            f"- Feature-space vs prototype-similarity mismatches: {len(mismatch_df)}",
            "",
            "## Verdict",
            verdict,
        ]
    )
    (out_dir / "step09_report.md").write_text("\n".join(report), encoding="utf-8")
    next_step = [
        "# Step09 Next Step Recommendation",
        "",
        "Use these assignments to test STD + descriptor fusion for the 31 October days, or use Step10A/10B to expand TEMPpred/STD coverage for high-interest C01/C06 days.",
        "",
        verdict,
    ]
    (out_dir / "step09_next_step_recommendation.md").write_text("\n".join(next_step), encoding="utf-8")
    shutil.copy2(Path(__file__).resolve(), out_dir / Path(__file__).name)
    print(f"Step09 complete: {out_dir}")
    print(f"Class counts: {counts}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
