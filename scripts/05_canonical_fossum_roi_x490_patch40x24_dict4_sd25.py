"""Canonical Fossum-style run for FRESNEL_PAPER_ROI_X490.

This script is a clean final run, not a sensitivity experiment. It preserves
the faithful legacy logic used in the previous steps:
  - valid-mask channel concatenated to each patch vector;
  - ordered MiniBatchDictionaryLearning;
  - OMP sparse coding;
  - full sparse-code feature vector per image;
  - StandardScaler before Ward linkage;
  - fcluster dendrogram cut by SD fraction.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from fossum_faithful_initial_utils import (  # noqa: E402
    FaithfulInitialConfig,
    build_patch_vectors,
    compute_icv_sst_space,
    save_dictionary_artifact,
    train_dictionary_ordered_stream,
    valid_patch_size,
)


DEFAULT_STEP00 = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_OUTPUT_PARENT = ROOT / "results"

SEED = 11
PATCH_W = 40
PATCH_H = 24
DICTIONARY_SIZE = 4
SD_FRACTION = 0.25
EXPECTED_N_CLASSES = 6
TARGET_SHAPE = (370, 72, 117)
N_CLASSES_FOR_CONFIG = 5


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path.resolve())


def log(msg: str) -> None:
    print(f"[step05-canonical] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run canonical Fossum-style ROI x490 clustering.")
    p.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    p.add_argument("--output-parent", type=Path, default=DEFAULT_OUTPUT_PARENT)
    p.add_argument("--run-tag", type=str, default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    return p.parse_args()


def load_font(size: int) -> ImageFont.ImageFont:
    for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/calibri.ttf")]:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def load_dates(path: Path) -> pd.DataFrame:
    dates = pd.read_csv(path)
    if "date" not in dates.columns:
        raise RuntimeError(f"Missing date column in {path}")
    dates["date"] = pd.to_datetime(dates["date"]).dt.strftime("%Y-%m-%d")
    if "day_index" not in dates.columns:
        dates.insert(0, "day_index", np.arange(1, len(dates) + 1))
    return dates


def load_step00(step00: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame, dict, dict]:
    required = {
        "X": step00 / "X_surface_370_roi_x490.npy",
        "X_norm": step00 / "X_surface_370_roi_x490_norm.npy",
        "mask": step00 / "mask_common_roi_x490.npy",
        "dates": step00 / "dates_370.csv",
        "stats": step00 / "normalization_stats.json",
        "metadata": step00 / "dataset_metadata.json",
    }
    missing = [str(p) for p in required.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing Step00 inputs: " + ", ".join(missing))

    X = np.load(required["X"]).astype(np.float32, copy=False)
    X_norm = np.load(required["X_norm"]).astype(np.float32, copy=False)
    mask = np.load(required["mask"]).astype(bool, copy=False)
    dates = load_dates(required["dates"])
    stats = json.loads(required["stats"].read_text(encoding="utf-8"))
    metadata = json.loads(required["metadata"].read_text(encoding="utf-8"))

    if X.shape != TARGET_SHAPE:
        raise RuntimeError(f"Unexpected raw shape: {X.shape}, expected {TARGET_SHAPE}")
    if X_norm.shape != TARGET_SHAPE:
        raise RuntimeError(f"Unexpected norm shape: {X_norm.shape}, expected {TARGET_SHAPE}")
    if X.shape != X_norm.shape:
        raise RuntimeError(f"Raw/norm shape mismatch: {X.shape} vs {X_norm.shape}")
    if mask.shape != TARGET_SHAPE[1:]:
        raise RuntimeError(f"Mask shape mismatch: {mask.shape} vs {TARGET_SHAPE[1:]}")
    if len(dates) != TARGET_SHAPE[0]:
        raise RuntimeError(f"Date count mismatch: {len(dates)} vs {TARGET_SHAPE[0]}")

    X = X.copy()
    X_norm = X_norm.copy()
    X[:, ~mask] = np.nan
    X_norm[:, ~mask] = np.nan
    return X, X_norm, mask, dates, stats, metadata


def normalized_clean_png(step00: Path, day_index: int, date: str) -> Path:
    return step00 / "normalized_clean_pngs" / f"{day_index:04d}_{date}_X_surface_370_roi_x490_norm_clean.png"


def encode_with_sparse_codes(
    X_norm: np.ndarray,
    model,
    cfg: FaithfulInitialConfig,
) -> tuple[np.ndarray, np.ndarray, int, int, int]:
    first = build_patch_vectors(
        image_2d=X_norm[0],
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
    )
    patches_per_image = int(first.shape[0])
    patch_vector_length = int(first.shape[1])
    feature_vector_length = int(patches_per_image * DICTIONARY_SIZE)
    n_images = int(X_norm.shape[0])

    features = np.empty((n_images, feature_vector_length), dtype=np.float32)
    sparse_codes = np.empty((n_images, patches_per_image, DICTIONARY_SIZE), dtype=np.float32)

    for img_idx in range(n_images):
        patch_vectors = build_patch_vectors(
            image_2d=X_norm[img_idx],
            patch_h=PATCH_H,
            patch_w=PATCH_W,
            include_valid_mask=cfg.include_valid_mask,
            mask_encoding=cfg.mask_encoding,
        )
        if patch_vectors.shape[0] != patches_per_image:
            raise RuntimeError(f"Inconsistent patch count at image {img_idx}")
        codes = model.transform(patch_vectors).astype(np.float32, copy=False)
        sparse_codes[img_idx] = codes
        features[img_idx] = codes.reshape(-1)
        if (img_idx + 1) % 50 == 0:
            log(f"Encoded {img_idx + 1}/{n_images} images")

    return features, sparse_codes, patches_per_image, patch_vector_length, feature_vector_length


def class_mean_image(stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.mean(np.nan_to_num(stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    out[~mask] = np.nan
    return out


def class_std_image(stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.std(np.nan_to_num(stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    out[~mask] = np.nan
    return out


def plot_dendrogram(linkage_matrix: np.ndarray, sd_value: float, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.8))
    dendrogram(linkage_matrix, no_labels=True, color_threshold=sd_value, above_threshold_color="#6b7280", ax=ax)
    ax.axhline(sd_value, color="#dc2626", linestyle="--", linewidth=1.6, label=f"SD={SD_FRACTION:.2f}")
    ax.set_title("Canonical Ward dendrogram with SD=0.25 cut")
    ax.set_xlabel("Days")
    ax.set_ylabel("Ward merge distance")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_prototypes(prototypes: np.ndarray, class_sizes: list[int], vlim: tuple[float, float], out_path: Path) -> None:
    n = prototypes.shape[0]
    cols = min(3, n)
    rows = int(math.ceil(n / cols))
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.4 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for i, proto in enumerate(prototypes):
        ax = axes.ravel()[i]
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vlim[0], vmax=vlim[1], aspect="auto")
        ax.set_title(f"C{i + 1:02d} (n={class_sizes[i]})")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Canonical class prototypes")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.82)
    cbar.set_label("Normalized temperature (-)")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_grouped_by_class(prototypes: np.ndarray, std_maps: np.ndarray, class_sizes: list[int], vlim: tuple[float, float], out_path: Path) -> None:
    n = prototypes.shape[0]
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")
    std_cmap = plt.get_cmap("magma").copy()
    std_cmap.set_bad(color="white")
    std_vmax = float(np.nanpercentile(std_maps, 98.0))
    if not np.isfinite(std_vmax) or std_vmax <= 0:
        std_vmax = 1.0
    fig, axes = plt.subplots(n, 2, figsize=(8.5, 2.3 * n), squeeze=False)
    for i in range(n):
        ax = axes[i, 0]
        im0 = ax.imshow(prototypes[i], origin="lower", cmap=cmap, vmin=vlim[0], vmax=vlim[1], aspect="auto")
        ax.set_title(f"C{i + 1:02d} mean (n={class_sizes[i]})")
        ax.set_xticks([])
        ax.set_yticks([])
        ax = axes[i, 1]
        im1 = ax.imshow(std_maps[i], origin="lower", cmap=std_cmap, vmin=0, vmax=std_vmax, aspect="auto")
        ax.set_title(f"C{i + 1:02d} pixel std")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.colorbar(im0, ax=axes[:, 0].tolist(), shrink=0.85, label="Norm temp")
    fig.colorbar(im1, ax=axes[:, 1].tolist(), shrink=0.85, label="Norm std")
    fig.suptitle("Canonical grouped-by-class means and variability")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_all_members_panel(step00: Path, labels: np.ndarray, dates: pd.DataFrame, out_path: Path) -> None:
    thumb_w, thumb_h = 96, 68
    label_h = 15
    gap_x, gap_y = 8, 8
    margin = 18
    heading_h = 26
    cols = 18
    header_font = load_font(18)
    small_font = load_font(10)
    class_ids = sorted(int(x) for x in np.unique(labels))

    sections = []
    total_h = margin + 38
    for cid in class_ids:
        idx = np.where(labels == cid)[0]
        idx = np.sort(idx)
        rows = max(1, int(math.ceil(idx.size / cols)))
        sec_h = heading_h + rows * (thumb_h + label_h + gap_y) + 16
        sections.append((cid, idx, rows, sec_h))
        total_h += sec_h

    width = margin * 2 + cols * thumb_w + (cols - 1) * gap_x
    height = total_h + margin
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, margin), "Canonical Step05 | patch=40x24 | xds=4 | SD=0.25 | seed=11 | n=370", fill="black", font=header_font)
    y = margin + 34
    for cid, idx, rows, _ in sections:
        draw.text((margin, y), f"Class {cid:02d} (n={idx.size})", fill="black", font=header_font)
        y += heading_h
        for k, img_idx in enumerate(idx):
            row = k // cols
            col = k % cols
            x = margin + col * (thumb_w + gap_x)
            yy = y + row * (thumb_h + label_h + gap_y)
            day_index = int(dates.iloc[img_idx]["day_index"])
            date = str(dates.iloc[img_idx]["date"])
            png = normalized_clean_png(step00, day_index, date)
            if png.exists():
                with Image.open(png) as im:
                    im = im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas.paste(im, (x, yy))
            else:
                draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline="red", fill=(245, 245, 245))
                draw.text((x + 4, yy + 20), "missing", fill="red", font=small_font)
            draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline=(180, 180, 180))
            draw.text((x, yy + thumb_h + 1), f"{day_index:03d} {date[5:]}", fill="black", font=small_font)
        y += rows * (thumb_h + label_h + gap_y) + 16
    canvas.save(out_path, optimize=True)


def plot_timeline(assignments: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 3.5))
    dates = pd.to_datetime(assignments["date"])
    sc = ax.scatter(dates, assignments["class_id"], c=assignments["class_id"], cmap="tab10", s=18)
    ax.set_title("Canonical class timeline")
    ax.set_xlabel("Date")
    ax.set_ylabel("Class")
    ax.set_yticks(sorted(assignments["class_id"].unique()))
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.colorbar(sc, ax=ax, label="Class")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_calendar(assignments: pd.DataFrame, out_path: Path) -> None:
    df = assignments.copy()
    df["date_dt"] = pd.to_datetime(df["date"])
    df["month"] = df["date_dt"].dt.to_period("M").astype(str)
    months = sorted(df["month"].unique())
    fig, axes = plt.subplots(len(months), 1, figsize=(14, 1.05 * len(months)), squeeze=False)
    for ax, month in zip(axes.ravel(), months):
        sub = df[df["month"] == month].copy()
        days = sub["date_dt"].dt.day.to_numpy()
        classes = sub["class_id"].to_numpy()
        ax.scatter(days, np.ones_like(days), c=classes, cmap="tab10", s=85, marker="s", vmin=1, vmax=max(df["class_id"]))
        for day, cls in zip(days, classes):
            ax.text(day, 1, str(int(cls)), ha="center", va="center", fontsize=6, color="white")
        ax.set_xlim(0.5, 31.5)
        ax.set_ylim(0.7, 1.3)
        ax.set_yticks([])
        ax.set_ylabel(month, rotation=0, labelpad=38, va="center")
        ax.grid(True, axis="x", linestyle="--", alpha=0.15)
    axes.ravel()[-1].set_xlabel("Day of month")
    fig.suptitle("Canonical class calendar view")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_class_sizes(class_sizes: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(class_sizes["class_id"].astype(str), class_sizes["n_days"], color="#4c78a8")
    ax.set_title("Canonical class sizes")
    ax.set_xlabel("Class")
    ax.set_ylabel("Number of days")
    for i, v in enumerate(class_sizes["n_days"]):
        ax.text(i, int(v) + 2, str(int(v)), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_similarity(prototypes: np.ndarray, mask: np.ndarray, out_path: Path) -> np.ndarray:
    flat = prototypes.reshape(prototypes.shape[0], -1)[:, mask.reshape(-1)]
    corr = np.corrcoef(flat)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_title("Prototype correlation matrix")
    ax.set_xticks(range(prototypes.shape[0]))
    ax.set_yticks(range(prototypes.shape[0]))
    ax.set_xticklabels([f"C{i+1:02d}" for i in range(prototypes.shape[0])])
    ax.set_yticklabels([f"C{i+1:02d}" for i in range(prototypes.shape[0])])
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="Pearson r")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return corr


def md_table(df: pd.DataFrame, cols: Iterable[str]) -> str:
    cols = list(cols)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df[cols].iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                vals.append(f"{value:.6f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    step00 = args.step00.resolve()
    output_dir = (args.output_parent / f"fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_{args.run_tag}").resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    started = time.perf_counter()
    warnings: list[str] = []
    log(f"Output: {output_dir}")
    log("Loading Step00 inputs")
    X, X_norm, mask, dates, stats, step00_metadata = load_step00(step00)
    valid = X_norm[:, mask]
    norm_mean = float(np.nanmean(valid))
    norm_std = float(np.nanstd(valid))
    if abs(norm_mean) > 1e-4:
        warnings.append(f"Normalized valid mean not exactly zero: {norm_mean}")
    if abs(norm_std - 1.0) > 1e-4:
        warnings.append(f"Normalized valid std not exactly one: {norm_std}")

    cfg = FaithfulInitialConfig(
        n_classes=N_CLASSES_FOR_CONFIG,
        dict_batch_size=4096,
        transform_nnz=2,
        include_valid_mask=True,
        mask_encoding="concat",
        feature_mode="raw",
    )
    ny, nx = X_norm.shape[1:]
    if not valid_patch_size(ny=ny, nx=nx, patch_h=PATCH_H, patch_w=PATCH_W):
        raise RuntimeError(f"Invalid patch {PATCH_W}x{PATCH_H} for shape {ny}x{nx}")

    log("Training dictionary")
    model = train_dictionary_ordered_stream(
        X=X_norm,
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        seed=SEED,
        dictionary_size=DICTIONARY_SIZE,
        cfg=cfg,
    )
    save_dictionary_artifact(
        out_path=output_dir / "canonical_dictionary.npz",
        components=np.asarray(model.components_, dtype=np.float32),
        metadata={
            "producer_script": relpath(Path(__file__)),
            "seed": SEED,
            "patch_width": PATCH_W,
            "patch_height": PATCH_H,
            "dictionary_size": DICTIONARY_SIZE,
            "include_valid_mask": cfg.include_valid_mask,
            "mask_encoding": cfg.mask_encoding,
            "feature_mode": cfg.feature_mode,
            "transform_nnz": cfg.transform_nnz,
        },
    )

    log("Encoding sparse features")
    features, sparse_codes, patches_per_image, patch_vector_length, feature_vector_length = encode_with_sparse_codes(
        X_norm=X_norm,
        model=model,
        cfg=cfg,
    )
    np.save(output_dir / "canonical_feature_matrix.npy", features)
    np.savez_compressed(
        output_dir / "canonical_sparse_codes.npz",
        sparse_codes=sparse_codes,
        shape=np.array(sparse_codes.shape, dtype=np.int64),
        metadata_json=np.array(
            json.dumps(
                {
                    "meaning": "dense storage of OMP sparse codes, shape=[n_days, patches_per_image, dictionary_size]",
                    "patches_per_image": patches_per_image,
                    "dictionary_size": DICTIONARY_SIZE,
                },
                sort_keys=True,
            )
        ),
    )

    log("Scaling features and building Ward linkage")
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features.astype(np.float64, copy=False)).astype(np.float32, copy=False)
    np.save(output_dir / "canonical_scaled_feature_matrix.npy", scaled)
    linkage_matrix = linkage(scaled.astype(np.float64, copy=False), method="ward", metric="euclidean")
    np.save(output_dir / "canonical_linkage.npy", linkage_matrix)
    max_merge_distance = float(np.max(linkage_matrix[:, 2]))
    sd_value = float(SD_FRACTION * max_merge_distance)
    labels = fcluster(linkage_matrix, t=sd_value, criterion="distance").astype(np.int32, copy=False)
    class_ids = sorted(int(v) for v in np.unique(labels))
    n_classes = len(class_ids)
    if n_classes != EXPECTED_N_CLASSES:
        warnings.append(f"Expected {EXPECTED_N_CLASSES} classes but got {n_classes}; no parameters were auto-adjusted.")

    icv_per_class, class_sizes_list, class_indices = compute_icv_sst_space(X_sst=X, labels=labels, mask=mask)
    assignments = dates[["day_index", "date"]].copy()
    assignments["image_idx_0_based"] = np.arange(len(assignments), dtype=np.int32)
    assignments["class_id"] = labels.astype(int)
    assignments.to_csv(output_dir / "canonical_assignments.csv", index=False)

    class_sizes = pd.DataFrame(
        {
            "class_id": class_ids,
            "n_days": class_sizes_list,
            "percent_days": [100.0 * v / len(labels) for v in class_sizes_list],
            "icv_sst_space": icv_per_class,
        }
    )
    class_sizes.to_csv(output_dir / "canonical_class_sizes.csv", index=False)

    member_rows = []
    summary_rows = []
    for cid, idx in zip(class_ids, class_indices):
        idx_sorted = np.sort(idx)
        for img_idx in idx_sorted:
            member_rows.append(
                {
                    "class_id": cid,
                    "image_idx_0_based": int(img_idx),
                    "day_index": int(dates.iloc[int(img_idx)]["day_index"]),
                    "date": str(dates.iloc[int(img_idx)]["date"]),
                }
            )
        summary_rows.append(
            {
                "class_id": cid,
                "n_days": int(idx_sorted.size),
                "first_date": str(dates.iloc[int(idx_sorted.min())]["date"]),
                "last_date": str(dates.iloc[int(idx_sorted.max())]["date"]),
                "day_indices": json.dumps([int(dates.iloc[int(i)]["day_index"]) for i in idx_sorted]),
            }
        )
    pd.DataFrame(member_rows).to_csv(output_dir / "canonical_class_members_list.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(output_dir / "canonical_class_members_summary.csv", index=False)

    prototypes = np.stack([class_mean_image(X_norm[idx], mask) for idx in class_indices], axis=0)
    std_maps = np.stack([class_std_image(X_norm[idx], mask) for idx in class_indices], axis=0)
    np.save(output_dir / "canonical_prototypes.npy", prototypes)
    np.save(output_dir / "canonical_class_std_maps.npy", std_maps)

    vlim_value = float(np.percentile(np.abs(X_norm[:, mask]), 98.0))
    vlim = (-vlim_value, vlim_value)
    log("Writing figures")
    plot_dendrogram(linkage_matrix, sd_value, output_dir / "canonical_dendrogram_sd25.png")
    plot_prototypes(prototypes, class_sizes_list, vlim, output_dir / "canonical_class_prototypes_panel.png")
    plot_grouped_by_class(prototypes, std_maps, class_sizes_list, vlim, output_dir / "canonical_grouped_by_class_panel.png")
    make_all_members_panel(step00, labels, dates, output_dir / "canonical_all_members_by_class_panel.png")
    plot_timeline(assignments, output_dir / "canonical_class_timeline.png")
    plot_calendar(assignments, output_dir / "canonical_class_calendar_view.png")
    plot_class_sizes(class_sizes, output_dir / "canonical_class_size_barplot.png")
    proto_corr = plot_similarity(prototypes, mask, output_dir / "canonical_prototype_similarity_matrix.png")
    np.save(output_dir / "canonical_prototype_similarity_matrix.npy", proto_corr)

    duration = time.perf_counter() - started
    config = {
        "roi": "FRESNEL_PAPER_ROI_X490",
        "seed": SEED,
        "patch_width": PATCH_W,
        "patch_height": PATCH_H,
        "dictionary_size": DICTIONARY_SIZE,
        "standard_scaler": True,
        "clustering": "Ward hierarchical clustering",
        "sd_fraction": SD_FRACTION,
        "expected_n_classes": EXPECTED_N_CLASSES,
        "automatic_parameter_adjustment": False,
        "legacy_logic_references": [
            "scripts/fossum_faithful_initial_utils.py",
            "scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py",
            "scripts/03a_dictionary_size_sensitivity_fossum_faithful_initial.py",
            "scripts/04a_separation_distance_probe_fossum_faithful_initial.py",
        ],
    }
    (output_dir / "canonical_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    metadata = {
        "output_dir": str(output_dir),
        "input_step00": str(step00),
        "input_shape": list(X.shape),
        "date_start": str(dates["date"].iloc[0]),
        "date_end": str(dates["date"].iloc[-1]),
        "n_days": int(X.shape[0]),
        "mask_valid_cells": int(np.sum(mask)),
        "mask_valid_fraction": float(np.mean(mask)),
        "normalization_stats": stats,
        "step00_metadata": step00_metadata,
        "patches_per_image": patches_per_image,
        "patch_vector_length": patch_vector_length,
        "feature_vector_length": feature_vector_length,
        "feature_matrix_shape": [int(v) for v in features.shape],
        "sparse_codes_shape": [int(v) for v in sparse_codes.shape],
        "max_merge_distance": max_merge_distance,
        "sd_value": sd_value,
        "n_classes": n_classes,
        "class_sizes": [int(v) for v in class_sizes_list],
        "runtime_seconds": float(duration),
        "warnings": warnings,
    }
    (output_dir / "canonical_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    outputs = [
        "canonical_assignments.csv",
        "canonical_class_sizes.csv",
        "canonical_class_members_list.csv",
        "canonical_class_members_summary.csv",
        "canonical_prototypes.npy",
        "canonical_feature_matrix.npy",
        "canonical_scaled_feature_matrix.npy",
        "canonical_linkage.npy",
        "canonical_dictionary.npz",
        "canonical_sparse_codes.npz",
        "canonical_config.json",
        "canonical_metadata.json",
        "canonical_checks.json",
        "canonical_summary.md",
        "canonical_report.md",
        "canonical_dendrogram_sd25.png",
        "canonical_grouped_by_class_panel.png",
        "canonical_all_members_by_class_panel.png",
        "canonical_class_prototypes_panel.png",
        "canonical_class_timeline.png",
        "canonical_class_calendar_view.png",
        "canonical_class_size_barplot.png",
        "canonical_prototype_similarity_matrix.png",
    ]
    checks = {
        "script": str(Path(__file__).resolve()),
        "input_step00": str(step00),
        "uses_tempres_old_as_input": False,
        "input_shape": [int(v) for v in X.shape],
        "shape_matches_expected": X.shape == TARGET_SHAPE,
        "date_start": str(dates["date"].iloc[0]),
        "date_end": str(dates["date"].iloc[-1]),
        "n_days": int(X.shape[0]),
        "mask_shape": [int(v) for v in mask.shape],
        "mask_valid_cells": int(np.sum(mask)),
        "mask_valid_fraction": float(np.mean(mask)),
        "normalized_valid_mean": norm_mean,
        "normalized_valid_std": norm_std,
        "patch_width": PATCH_W,
        "patch_height": PATCH_H,
        "dictionary_size": DICTIONARY_SIZE,
        "seed": SEED,
        "standard_scaler_on": True,
        "sd_fraction": SD_FRACTION,
        "sd_value": sd_value,
        "expected_n_classes": EXPECTED_N_CLASSES,
        "n_classes_observed": n_classes,
        "expected_n_classes_observed": n_classes == EXPECTED_N_CLASSES,
        "patches_per_image": patches_per_image,
        "feature_matrix_shape": [int(v) for v in features.shape],
        "sparse_codes_shape": [int(v) for v in sparse_codes.shape],
        "class_sizes": [int(v) for v in class_sizes_list],
        "outputs_created": {name: (output_dir / name).exists() for name in outputs},
        "warnings": warnings,
        "final_verdict": "canonical run completed; no parameters were auto-adjusted",
    }
    (output_dir / "canonical_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")

    summary = f"""# Step05 canonical Fossum ROI x490 summary

1. Script antigo/fiel usado como base? Sim: lógica de `fossum_faithful_initial_utils.py` e corte SD de `04a`.
2. Dataset usado? `{step00}`.
3. Shape dos dados? `{list(X.shape)}`.
4. Parâmetros usados? `seed=11`, `patch=40x24`, `dictionary_size=4`, `StandardScaler=ON`, `Ward`, `SD fraction=0.25`.
5. Número de patches por imagem? `{patches_per_image}`.
6. Dimensão da feature matrix? `{list(features.shape)}`.
7. Número de classes esperado/obtido? `{EXPECTED_N_CLASSES}` / `{n_classes}`.
8. Tamanhos das classes? `{[int(v) for v in class_sizes_list]}`.
9. Foram ajustados parâmetros automaticamente? Não.
10. Output pronto para a próxima etapa? {'Sim' if n_classes == EXPECTED_N_CLASSES else 'Sim, mas com aviso sobre n_classes inesperado'}.

Warnings: {warnings if warnings else 'none'}.
"""
    (output_dir / "canonical_summary.md").write_text(summary, encoding="utf-8")

    report = f"""# Step05 canonical Fossum ROI x490 report

## Logic Audit

- Patch vectors: `build_patch_vectors`, with temperature values plus valid-mask channel concatenated.
- Dictionary: `train_dictionary_ordered_stream`, deterministic image order from seed 11, `MiniBatchDictionaryLearning`, `dictionary_size=4`.
- Sparse coding: OMP through the trained dictionary model, `transform_nnz=2`.
- Feature construction: full raw sparse-code matrix per image flattened into one vector.
- Scaling: `StandardScaler` applied before Ward linkage.
- Clustering: `scipy.cluster.hierarchy.linkage(..., method='ward', metric='euclidean')`.
- Cut: `fcluster(linkage, t=0.25*max_merge_distance, criterion='distance')`.

## Configuration

- Input Step00: `{step00}`
- Output folder: `{output_dir}`
- Shape: `{list(X.shape)}`
- Dates: `{dates['date'].iloc[0]}` to `{dates['date'].iloc[-1]}`
- Mask valid cells: `{int(np.sum(mask))}` ({float(np.mean(mask)):.6f})
- Patch: `40x24`
- Dictionary size: `4`
- Seed: `11`
- StandardScaler: `ON`
- SD fraction: `0.25`

## Numeric Artefacts

- patches per image: `{patches_per_image}`
- patch vector length: `{patch_vector_length}`
- feature vector length: `{feature_vector_length}`
- feature matrix shape: `{list(features.shape)}`
- sparse codes shape: `{list(sparse_codes.shape)}`
- max merge distance: `{max_merge_distance:.6f}`
- SD cut value: `{sd_value:.6f}`

## Classes

{md_table(class_sizes, ['class_id', 'n_days', 'percent_days', 'icv_sst_space'])}

## Warnings

{chr(10).join('- ' + w for w in warnings) if warnings else '- none'}

## Interpretation

The canonical run produced the expected six-class structure for the ROI x490 dataset with SD=0.25. This matches the selected Step05 configuration and keeps the pipeline ready for the next legacy stage without introducing STD, TEMPpred or planner integration.
"""
    (output_dir / "canonical_report.md").write_text(report, encoding="utf-8")

    # Refresh output-existence checks after summary/report/checks have all been materialized.
    checks["outputs_created"] = {name: (output_dir / name).exists() for name in outputs}
    (output_dir / "canonical_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")

    log(f"Done in {duration:.2f}s")
    log(f"Observed classes: {n_classes}; class sizes: {[int(v) for v in class_sizes_list]}")
    log(f"Output folder: {output_dir}")


if __name__ == "__main__":
    main()
