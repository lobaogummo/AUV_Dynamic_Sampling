"""Automatic separation-distance probing for faithful Fossum initial pipeline.

This script is intentionally isolated from historical baseline scripts and from
the existing faithful patch/dictionary sweeps. It runs a fixed configuration:
  - patch size: 72x40
  - dictionary size: 4
  - StandardScaler before Ward linkage: ON by default
  - provisional working SD fraction: 0.30 (current 5-class choice)
Then it builds a Ward dendrogram, derives SD cuts from fractions of the
observed maximum merge distance, and evaluates each SD cut.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from fossum_faithful_initial_utils import (
    ROOT,
    FaithfulInitialConfig,
    compute_icv_sst_space,
    deterministic_spread_order,
    encode_images_with_full_sparse_features,
    image_icv_proxy,
    load_fixed_dictionary_model,
    save_dictionary_artifact,
    train_dictionary_ordered_stream,
    valid_patch_size,
)

DEFAULT_OUT_BASE = ROOT / "results" / "fossum" / "faithful_initial_sd_autoprobe"
DEFAULT_WORKING_SD_FRACTION = 0.30
DEFAULT_FRACTIONS = [DEFAULT_WORKING_SD_FRACTION]
DEFAULT_FIXED_PATCH_W = 72
DEFAULT_FIXED_PATCH_H = 40
DEFAULT_FIXED_DICTIONARY_SIZE = 4
DEFAULT_SEED = 11
DEFAULT_APPLY_STANDARD_SCALER = True
DEFAULT_RANKING_TARGET_CLASSES = 5
MAX_CONTACT_IMAGES_PER_CLASS = 50
MAX_DISTANCE_PANEL_IMAGES = 30


@dataclass
class SDRunResult:
    separation_distance: float
    sd_fraction_of_max: float
    max_merge_distance: float
    number_of_classes: int
    class_sizes: str
    min_class_size: int
    mean_class_size: float
    max_class_size: int
    singleton_count: int
    mean_icv: float
    std_icv: float
    icv_per_class: str
    behavior_label: str
    behavior_reason: str
    output_dir: str


def log(msg: str) -> None:
    print(f"[faithful-sd-probe] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Automatic SD probe for faithful Fossum initial clustering.")
    p.add_argument("--out-base", type=Path, default=DEFAULT_OUT_BASE)
    p.add_argument(
        "--run-tag",
        type=str,
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Suffix used to keep outputs isolated and avoid overwriting old runs.",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--patch-w", type=int, default=DEFAULT_FIXED_PATCH_W)
    p.add_argument("--patch-h", type=int, default=DEFAULT_FIXED_PATCH_H)
    p.add_argument("--dictionary-size", type=int, default=DEFAULT_FIXED_DICTIONARY_SIZE)
    p.add_argument("--fractions", nargs="*", type=float, default=None)
    p.add_argument("--dict-batch-size", type=int, default=4096)
    p.add_argument("--transform-nnz", type=int, default=2)
    p.add_argument("--feature-mode", choices=["raw", "abs"], default="raw")
    p.add_argument("--mask-encoding", choices=["concat"], default="concat")
    p.add_argument("--no-valid-mask", action="store_true")
    scaler_group = p.add_mutually_exclusive_group()
    scaler_group.add_argument(
        "--apply-standard-scaler",
        dest="apply_standard_scaler",
        action="store_true",
        help="Apply StandardScaler before Ward linkage (default).",
    )
    scaler_group.add_argument(
        "--no-standard-scaler",
        dest="apply_standard_scaler",
        action="store_false",
        help="Disable StandardScaler before Ward linkage.",
    )
    p.set_defaults(apply_standard_scaler=DEFAULT_APPLY_STANDARD_SCALER)
    p.add_argument("--ranking-target-classes", type=int, default=DEFAULT_RANKING_TARGET_CLASSES)
    p.add_argument("--no-pca", action="store_true", help="Skip PCA 2D visual per SD.")
    p.add_argument(
        "--use-fixed-dictionary",
        action="store_true",
        help="Load a pre-saved dictionary artifact instead of training a new dictionary for this run.",
    )
    p.add_argument(
        "--dictionary-path",
        type=Path,
        default=None,
        help="Path to dictionary artifact (.npz) used when --use-fixed-dictionary is enabled.",
    )
    p.add_argument(
        "--save-dictionary-path",
        type=Path,
        default=None,
        help="Optional output path to save the trained dictionary artifact (.npz). Ignored in fixed mode.",
    )
    return p.parse_args()


def validate_fractions(values: Sequence[float] | None) -> List[float]:
    vals = list(DEFAULT_FRACTIONS if values is None or len(values) == 0 else values)
    out: List[float] = []
    seen = set()
    for v in vals:
        vf = float(v)
        if vf <= 0.0 or vf >= 1.0:
            raise ValueError(f"Invalid SD fraction '{vf}'. Use values in (0, 1).")
        key = round(vf, 12)
        if key not in seen:
            seen.add(key)
            out.append(vf)
    out.sort()
    return out


def _first_existing_file(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _first_existing_dir(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return None


def resolve_probe_input_paths() -> dict[str, Path]:
    paths = {
        "X_sst": _first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300.npy",
                ROOT / "results" / "plots" / "X_surface_300.npy",
            ]
        ),
        "X_norm": _first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
                ROOT / "results" / "plots" / "X_surface_300_norm.npy",
            ]
        ),
        "mask": _first_existing_file(
            [
                ROOT / "results" / "fossum" / "mask_common.npy",
                ROOT / "results" / "plots" / "mask_common.npy",
            ]
        ),
        "png_dir": _first_existing_dir(
            [
                ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis",
                ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis",
            ]
        ),
    }
    missing = [k for k, v in paths.items() if v is None]
    if missing:
        raise FileNotFoundError(f"Missing required inputs for SD probe: {', '.join(missing)}")
    return {k: v for k, v in paths.items() if v is not None}


def load_probe_numeric_inputs(paths: dict[str, Path]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[float, float]]:
    X_sst = np.load(paths["X_sst"]).astype(np.float32, copy=False)
    X_norm = np.load(paths["X_norm"]).astype(np.float32, copy=False)
    mask = np.load(paths["mask"]).astype(bool, copy=False)

    if X_sst.ndim != 3 or X_norm.ndim != 3:
        raise RuntimeError(f"Expected 3D arrays, got X_sst={X_sst.shape}, X_norm={X_norm.shape}")
    if X_sst.shape != X_norm.shape:
        raise RuntimeError(f"Shape mismatch: X_sst={X_sst.shape} vs X_norm={X_norm.shape}")
    if mask.shape != X_norm.shape[1:]:
        raise RuntimeError(f"Mask mismatch: {mask.shape} vs {X_norm.shape[1:]}")

    X_sst = X_sst.copy()
    X_norm = X_norm.copy()
    X_sst[:, ~mask] = np.nan
    X_norm[:, ~mask] = np.nan

    valid_vals = X_norm[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals), 98.0))
    if not np.isfinite(vlim) or vlim <= 0.0:
        vlim = 1.0
    return X_sst, X_norm, mask, (-vlim, +vlim)


def build_png_map_from_dir(png_dir: Path) -> dict[int, Path]:
    files = sorted(png_dir.glob("X_surface_norm_z*.png"))
    if not files:
        raise RuntimeError(f"No PNGs found in {png_dir}")
    out: dict[int, Path] = {}
    for p in files:
        stem = p.stem.lower()
        if "_z" not in stem:
            continue
        try:
            z_str = stem.split("_z")[-1]
            z = int(z_str)
        except Exception:
            continue
        out[z] = p
    return out


def class_mean_image(class_stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    mean_img = np.mean(np.nan_to_num(class_stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    mean_img[~mask] = np.nan
    return mean_img


def class_std_image(class_stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    std_img = np.std(np.nan_to_num(class_stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    std_img[~mask] = np.nan
    return std_img


def compute_member_distances_to_prototype(
    class_stack: np.ndarray,
    prototype: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    valid = mask.reshape(-1)
    members_flat = class_stack.reshape(class_stack.shape[0], -1)[:, valid]
    proto_flat = prototype.reshape(-1)[valid]
    diffs = members_flat - proto_flat[np.newaxis, :]
    # RMSE on normalized domain (same domain used to build prototypes).
    return np.sqrt(np.nanmean(diffs * diffs, axis=1)).astype(np.float64, copy=False)


def make_contact_sheet_from_pngs(
    png_paths: List[Path],
    labels: List[str],
    out_path: Path,
    title: str,
    cols: int = 10,
    thumb_size: Tuple[int, int] = (180, 120),
) -> None:
    n = len(png_paths)
    rows = int(math.ceil(n / cols)) if n > 0 else 1
    pad = 8
    title_h = 28
    label_h = 14
    cell_w = thumb_size[0]
    cell_h = thumb_size[1] + label_h
    w = pad + cols * (cell_w + pad)
    h = title_h + pad + rows * (cell_h + pad) + pad

    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    tw = draw.textlength(title, font=font)
    draw.text(((w - tw) / 2, 6), title, fill=(0, 0, 0), font=font)

    for i, (png_path, label) in enumerate(zip(png_paths, labels)):
        r = i // cols
        c = i % cols
        x = pad + c * (cell_w + pad)
        y = title_h + pad + r * (cell_h + pad)
        with Image.open(png_path) as im:
            rgb = im.convert("RGB").resize(thumb_size, Image.Resampling.BILINEAR)
        canvas.paste(rgb, (x, y))
        draw.rectangle([x, y, x + thumb_size[0], y + thumb_size[1]], outline=(120, 120, 120), width=1)
        draw.text((x, y + thumb_size[1] + 1), label, fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")


def save_member_contact_sheets(
    out_dir: Path,
    png_map: dict[int, Path],
    class_indices: List[np.ndarray],
    image_proxy: np.ndarray,
    separation_distance: float,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ci, idx in enumerate(class_indices, start=1):
        ordered = deterministic_spread_order(indices=idx, proxy_values=image_proxy)[:MAX_CONTACT_IMAGES_PER_CLASS]
        rows = []
        panel_pngs: List[Path] = []
        panel_labels: List[str] = []
        for img_idx in ordered:
            z = int(img_idx) + 1
            png_path = png_map.get(z)
            if png_path is None:
                continue
            panel_pngs.append(png_path)
            panel_labels.append(f"z={z:03d}")
            rows.append(
                {
                    "image_idx_0_based": int(img_idx),
                    "image_z_1_based": z,
                    "image_icv_proxy": float(image_proxy[int(img_idx)]),
                    "png_path": str(png_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
        pd.DataFrame(rows).to_csv(out_dir / f"class_{ci:02d}_members_list.csv", index=False)
        title = f"SD={separation_distance:.6f} class {ci:02d} (n={len(idx)}, shown={len(panel_pngs)})"
        make_contact_sheet_from_pngs(
            png_paths=panel_pngs,
            labels=panel_labels,
            out_path=out_dir / f"class_{ci:02d}_members_panel.png",
            title=title,
            cols=10,
            thumb_size=(180, 120),
        )


def save_prototypes(
    out_dir: Path,
    X_norm: np.ndarray,
    mask: np.ndarray,
    class_indices: List[np.ndarray],
    separation_distance: float,
    vmin: float,
    vmax: float,
) -> List[np.ndarray]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")
    protos: List[np.ndarray] = []
    for ci, idx in enumerate(class_indices, start=1):
        proto = class_mean_image(X_norm[idx], mask=mask)
        protos.append(proto)
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"Prototype class {ci:02d} (n={len(idx)}) | SD={separation_distance:.6f}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Normalized temperature (-)")
        fig.tight_layout()
        fig.savefig(out_dir / f"prototype_class_{ci:02d}.png", dpi=150)
        plt.close(fig)

    fig, axes = plt.subplots(1, len(protos), figsize=(4.0 * len(protos), 4.0), squeeze=False)
    for j, (ax, proto, idx) in enumerate(zip(axes[0], protos, class_indices), start=1):
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"C{j} (n={len(idx)})")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    fig.suptitle(f"Class prototypes | SD={separation_distance:.6f}")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85)
    cbar.set_label("Normalized temperature (-)")
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.08, top=0.86, wspace=0.20)
    fig.savefig(out_dir / "prototypes_panel.png", dpi=160)
    plt.close(fig)
    return protos


def save_class_homogeneity_artifacts(
    out_dir: Path,
    X_norm: np.ndarray,
    mask: np.ndarray,
    class_indices: List[np.ndarray],
    class_prototypes: Sequence[np.ndarray],
    png_map: dict[int, Path],
    separation_distance: float,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    std_maps: List[np.ndarray] = []
    std_values: List[np.ndarray] = []
    for idx in class_indices:
        std_map = class_std_image(X_norm[idx], mask=mask)
        std_maps.append(std_map)
        vals = std_map[mask]
        if vals.size > 0:
            std_values.append(vals.astype(np.float64, copy=False))

    if std_values:
        std_vmax = float(np.percentile(np.concatenate(std_values), 98.0))
    else:
        std_vmax = 1.0
    if not np.isfinite(std_vmax) or std_vmax <= 0.0:
        std_vmax = 1.0

    std_cmap = plt.get_cmap("magma").copy()
    std_cmap.set_bad(color="white")

    for ci, (idx, proto, std_map) in enumerate(zip(class_indices, class_prototypes, std_maps), start=1):
        class_stack = X_norm[idx]
        distances = compute_member_distances_to_prototype(class_stack=class_stack, prototype=proto, mask=mask)
        order_asc = np.argsort(distances)

        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        im = ax.imshow(std_map, origin="lower", cmap=std_cmap, vmin=0.0, vmax=std_vmax, aspect="auto")
        ax.set_title(f"Pixelwise std class {ci:02d} (n={len(idx)}) | SD={separation_distance:.6f}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Std on normalized temperature (-)")
        fig.tight_layout()
        fig.savefig(out_dir / f"class_{ci:02d}_pixel_std_map.png", dpi=150)
        plt.close(fig)

        rows = []
        for rank_pos, local_pos in enumerate(order_asc, start=1):
            img_idx = int(idx[int(local_pos)])
            z = img_idx + 1
            png_path = png_map.get(z)
            rows.append(
                {
                    "distance_rank_asc": int(rank_pos),
                    "image_idx_0_based": img_idx,
                    "image_z_1_based": z,
                    "distance_to_prototype_rmse_norm": float(distances[int(local_pos)]),
                    "png_path": str(png_path.relative_to(ROOT)).replace("\\", "/") if png_path is not None else "",
                }
            )
        pd.DataFrame(rows).to_csv(out_dir / f"class_{ci:02d}_distance_to_prototype.csv", index=False)

        def build_panel_inputs(local_positions: np.ndarray) -> Tuple[List[Path], List[str]]:
            panel_pngs: List[Path] = []
            panel_labels: List[str] = []
            for local_pos in local_positions:
                img_idx = int(idx[int(local_pos)])
                z = img_idx + 1
                png_path = png_map.get(z)
                if png_path is None:
                    continue
                panel_pngs.append(png_path)
                panel_labels.append(f"z={z:03d} d={float(distances[int(local_pos)]):.4f}")
            return panel_pngs, panel_labels

        closest_local = order_asc[:MAX_DISTANCE_PANEL_IMAGES]
        farthest_local = order_asc[::-1][:MAX_DISTANCE_PANEL_IMAGES]
        closest_pngs, closest_labels = build_panel_inputs(closest_local)
        farthest_pngs, farthest_labels = build_panel_inputs(farthest_local)

        make_contact_sheet_from_pngs(
            png_paths=closest_pngs,
            labels=closest_labels,
            out_path=out_dir / f"class_{ci:02d}_closest_to_prototype_panel.png",
            title=f"SD={separation_distance:.6f} class {ci:02d} closest to prototype",
            cols=8,
            thumb_size=(180, 120),
        )
        make_contact_sheet_from_pngs(
            png_paths=farthest_pngs,
            labels=farthest_labels,
            out_path=out_dir / f"class_{ci:02d}_farthest_from_prototype_panel.png",
            title=f"SD={separation_distance:.6f} class {ci:02d} farthest from prototype",
            cols=8,
            thumb_size=(180, 120),
        )


def plot_dendrogram_with_cut(
    linkage_matrix: np.ndarray,
    separation_distance: float,
    out_path: Path,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 4.8))
    dendrogram(
        linkage_matrix,
        no_labels=True,
        color_threshold=float(separation_distance),
        above_threshold_color="#6b7280",
        ax=ax,
    )
    ax.axhline(float(separation_distance), color="#dc2626", linestyle="--", linewidth=1.6, label="SD cut")
    ax.set_title(title)
    ax.set_xlabel("Samples")
    ax.set_ylabel("Merge distance")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def plot_pca_classes(
    coords: np.ndarray,
    labels: np.ndarray,
    separation_distance: float,
    out_path: Path,
) -> None:
    unique_labels = np.unique(labels)
    cmap = plt.get_cmap("tab20")
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    for i, cls in enumerate(unique_labels):
        idx = labels == cls
        ax.scatter(
            coords[idx, 0],
            coords[idx, 1],
            s=22,
            alpha=0.85,
            color=cmap(i % 20),
            label=f"C{int(cls):02d} (n={int(np.sum(idx))})",
        )
    ax.set_title(f"PCA 2D features | SD={separation_distance:.6f}")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="best", fontsize=8, frameon=True)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def classify_behavior(
    number_of_classes: int,
    class_sizes: Sequence[int],
    singleton_count: int,
    total_images: int,
) -> Tuple[str, str]:
    max_class = int(np.max(class_sizes))
    min_class = int(np.min(class_sizes))
    frag_flags = 0
    mix_flags = 0
    reasons: List[str] = []

    if number_of_classes >= 8:
        frag_flags += 1
        reasons.append("n_classes alto")
    if singleton_count >= max(3, int(round(0.05 * total_images))):
        frag_flags += 1
        reasons.append("muitos singletons")
    if min_class <= 2:
        frag_flags += 1
        reasons.append("classe minima muito pequena")

    if number_of_classes <= 2:
        mix_flags += 1
        reasons.append("n_classes baixo")
    if max_class >= int(round(0.70 * total_images)):
        mix_flags += 1
        reasons.append("classe dominante muito grande")

    if frag_flags > mix_flags and frag_flags > 0:
        return "fragmenta demais", "; ".join(reasons)
    if mix_flags > frag_flags and mix_flags > 0:
        return "mistura demais", "; ".join(reasons)
    return "plausivel", "; ".join(reasons) if reasons else "sem sinais fortes de fragmentacao/mistura"


def rank_sd_candidates(runs_df: pd.DataFrame, target_classes: int = DEFAULT_RANKING_TARGET_CLASSES) -> pd.DataFrame:
    if int(target_classes) <= 0:
        raise ValueError("target_classes must be > 0")
    d = runs_df.copy()
    d["classes_distance_from_target"] = (d["number_of_classes"] - int(target_classes)).abs()
    d["rank_mean_icv"] = d["mean_icv"].rank(method="min", ascending=True)
    d["rank_singletons"] = d["singleton_count"].rank(method="min", ascending=True)
    d["rank_min_class"] = d["min_class_size"].rank(method="min", ascending=False)
    d["rank_classes_balance"] = d["classes_distance_from_target"].rank(method="min", ascending=True)
    d["balanced_score"] = (
        0.35 * d["rank_mean_icv"]
        + 0.25 * d["rank_singletons"]
        + 0.20 * d["rank_min_class"]
        + 0.20 * d["rank_classes_balance"]
    )
    return d.sort_values(["balanced_score", "sd_fraction_of_max"]).reset_index(drop=True)


def save_runs_csv(rows: Iterable[SDRunResult], out_runs: Path) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    out_runs.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_runs, index=False)
    return df


def dataframe_to_md_table(df: pd.DataFrame, cols: Sequence[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body: List[str] = []
    for _, row in df.iterrows():
        vals: List[str] = []
        for col in cols:
            value = row[col]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{float(value):.6f}")
            else:
                vals.append(str(value))
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + body)


def build_markdown_report(
    report_path: Path,
    out_base: Path,
    runs_df: pd.DataFrame,
    ranked_df: pd.DataFrame,
    fractions: Sequence[float],
    cfg: FaithfulInitialConfig,
    seed: int,
    patch_w: int,
    patch_h: int,
    dictionary_size: int,
    ranking_target_classes: int,
    standard_scaler_applied: bool,
    max_merge_distance: float,
    dictionary_mode: str,
    dictionary_path: str | None,
) -> None:
    top = ranked_df.head(min(3, len(ranked_df)))
    cols = [
        "sd_fraction_of_max",
        "separation_distance",
        "number_of_classes",
        "min_class_size",
        "mean_class_size",
        "max_class_size",
        "singleton_count",
        "mean_icv",
        "std_icv",
        "behavior_label",
    ]
    md = [
        "# SEPARATION_DISTANCE_PROBE_FOSSUM_FAITHFUL_INITIAL",
        "",
        "## Scope",
        "- Dedicated SD auto-probe for faithful pipeline only.",
        "- Historical baseline scripts were not modified.",
        "",
        "## Fixed configuration lock",
        f"- patch size: ({patch_w},{patch_h})",
        f"- dictionary size: {dictionary_size}",
        f"- seed: {seed}",
        f"- include_valid_mask={cfg.include_valid_mask}",
        f"- mask_encoding={cfg.mask_encoding}",
        f"- feature_mode={cfg.feature_mode}",
        f"- StandardScaler applied before Ward: {standard_scaler_applied}",
        f"- ranking target classes: {ranking_target_classes}",
        f"- default provisional SD fraction in this script: {DEFAULT_WORKING_SD_FRACTION:.2f}",
        f"- dictionary mode: {dictionary_mode}",
        f"- dictionary artifact path: {dictionary_path if dictionary_path is not None else 'trained in this run'}",
        "",
        "## Dendrogram-driven SD generation",
        f"- max merge distance observed: {max_merge_distance:.6f}",
        f"- fractions used: {', '.join(f'{f:.2f}' for f in fractions)}",
        "- SD values computed as: `fraction * max_merge_distance`",
        "",
        "## Summary table",
        dataframe_to_md_table(runs_df[cols], cols),
        "",
        "## Ranking (balanced score, with target-class proximity)",
        (
            "- score = 0.35*rank(mean_icv) + 0.25*rank(singleton_count) + "
            "0.20*rank(min_class_size, descending) + 0.20*rank(|n_classes-target|)"
        ),
        dataframe_to_md_table(
            top[
                [
                    "sd_fraction_of_max",
                    "separation_distance",
                    "balanced_score",
                    "number_of_classes",
                    "singleton_count",
                    "mean_icv",
                    "std_icv",
                    "behavior_label",
                ]
            ],
            [
                "sd_fraction_of_max",
                "separation_distance",
                "balanced_score",
                "number_of_classes",
                "singleton_count",
                "mean_icv",
                "std_icv",
                "behavior_label",
            ],
        ),
        "",
        "## Output locations",
        f"- root: `{out_base.relative_to(ROOT).as_posix()}`",
        f"- runs: `{(out_base / 'runs.csv').relative_to(ROOT).as_posix()}`",
        f"- ranking: `{(out_base / 'ranking.csv').relative_to(ROOT).as_posix()}`",
        f"- dendrogram diagnostics: `{(out_base / 'dendrogram').relative_to(ROOT).as_posix()}`",
        (
            "- per-SD folders: `sd_XXpct/` (members lists/panels, prototypes, "
            "pixel-std maps, prototype-distance CSVs, closest/farthest panels, dendrogram cut, PCA)."
        ),
    ]
    report_path.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    args = parse_args()
    fractions = validate_fractions(args.fractions)

    patch_w = int(args.patch_w)
    patch_h = int(args.patch_h)
    dictionary_size = int(args.dictionary_size)
    seed = int(args.seed)
    ranking_target_classes = int(args.ranking_target_classes)

    if patch_w != DEFAULT_FIXED_PATCH_W or patch_h != DEFAULT_FIXED_PATCH_H:
        raise ValueError(
            f"This probe is locked to patch={DEFAULT_FIXED_PATCH_W}x{DEFAULT_FIXED_PATCH_H}. "
            f"Received {patch_w}x{patch_h}."
        )
    if dictionary_size != DEFAULT_FIXED_DICTIONARY_SIZE:
        raise ValueError(
            f"This probe is locked to dictionary_size={DEFAULT_FIXED_DICTIONARY_SIZE}. "
            f"Received {dictionary_size}."
        )
    if args.transform_nnz <= 0:
        raise ValueError("--transform-nnz must be > 0")
    if ranking_target_classes <= 0:
        raise ValueError("--ranking-target-classes must be > 0")
    use_fixed_dictionary = bool(args.use_fixed_dictionary)
    if args.dictionary_path is not None and not use_fixed_dictionary:
        # Backward-compatible convenience: passing dictionary-path implies fixed mode.
        use_fixed_dictionary = True
    if use_fixed_dictionary and args.dictionary_path is None:
        raise ValueError("--dictionary-path is required when --use-fixed-dictionary is enabled.")

    cfg = FaithfulInitialConfig(
        n_classes=ranking_target_classes,
        dict_batch_size=int(args.dict_batch_size),
        transform_nnz=int(args.transform_nnz),
        include_valid_mask=not bool(args.no_valid_mask),
        mask_encoding=str(args.mask_encoding),
        feature_mode=str(args.feature_mode),
    )

    in_paths = resolve_probe_input_paths()
    X_sst, X_norm, mask, vlim = load_probe_numeric_inputs(in_paths)
    png_map = build_png_map_from_dir(in_paths["png_dir"])
    image_proxy = image_icv_proxy(X_sst=X_sst, mask=mask)

    n_images, ny, nx = X_norm.shape
    if not valid_patch_size(ny, nx, patch_h=patch_h, patch_w=patch_w):
        raise ValueError(f"Invalid patch size ({patch_w},{patch_h}) for grid ({nx},{ny}).")

    out_root = args.out_base.resolve()
    scaler_tag = "scalerON" if bool(args.apply_standard_scaler) else "scalerOFF"
    run_name = f"w{patch_w:02d}_h{patch_h:02d}_xds{dictionary_size:02d}_seed{seed:02d}_{scaler_tag}_{args.run_tag}"
    out_base = out_root / run_name
    out_base.mkdir(parents=True, exist_ok=True)
    out_dendro = out_base / "dendrogram"
    out_dendro.mkdir(parents=True, exist_ok=True)

    log(f"Output root: {out_base}")
    log(
        "Input paths: "
        f"X_sst={in_paths['X_sst']}, X_norm={in_paths['X_norm']}, mask={in_paths['mask']}, "
        f"png_dir={in_paths['png_dir']}"
    )
    log(
        "Config lock: "
        f"patch={patch_w}x{patch_h}, xds={dictionary_size}, seed={seed}, "
        f"apply_standard_scaler={bool(args.apply_standard_scaler)}, "
        f"ranking_target_classes={ranking_target_classes}"
    )

    t0 = time.perf_counter()
    dictionary_mode = "fixed" if use_fixed_dictionary else "trained"
    dictionary_path_for_report: str | None = None
    dictionary_metadata: dict = {}
    if use_fixed_dictionary and args.save_dictionary_path is not None:
        log("--save-dictionary-path ignored in fixed-dictionary mode.")
    if use_fixed_dictionary:
        dictionary_path = Path(args.dictionary_path).resolve()
        model, dictionary_metadata = load_fixed_dictionary_model(
            dictionary_path=dictionary_path,
            cfg=cfg,
            expected_dictionary_size=dictionary_size,
        )
        dictionary_path_for_report = str(dictionary_path)
        meta_patch_w = dictionary_metadata.get("patch_w")
        meta_patch_h = dictionary_metadata.get("patch_h")
        if meta_patch_w is not None and int(meta_patch_w) != patch_w:
            raise RuntimeError(f"Dictionary patch_w mismatch: artifact={meta_patch_w}, requested={patch_w}")
        if meta_patch_h is not None and int(meta_patch_h) != patch_h:
            raise RuntimeError(f"Dictionary patch_h mismatch: artifact={meta_patch_h}, requested={patch_h}")
        log(f"Loaded fixed dictionary from: {dictionary_path}")
    else:
        model = train_dictionary_ordered_stream(
            X=X_norm,
            patch_h=patch_h,
            patch_w=patch_w,
            seed=seed,
            dictionary_size=dictionary_size,
            cfg=cfg,
        )
        log("Trained dictionary in this run.")
    features, patches_per_image, patch_vector_length, feature_vector_length = encode_images_with_full_sparse_features(
        X=X_norm,
        model=model,
        patch_h=patch_h,
        patch_w=patch_w,
        dictionary_size=dictionary_size,
        cfg=cfg,
    )
    log(
        f"Feature extraction done: features={features.shape}, patches_per_image={patches_per_image}, "
        f"patch_vector_length={patch_vector_length}, feature_vector_length={feature_vector_length}"
    )
    if not use_fixed_dictionary and args.save_dictionary_path is not None:
        save_path = Path(args.save_dictionary_path).resolve()
        save_dictionary_artifact(
            out_path=save_path,
            components=np.asarray(model.components_, dtype=np.float32),
            metadata={
                "schema_version": 1,
                "producer_script": "04a_separation_distance_probe_fossum_faithful_initial.py",
                "seed": int(seed),
                "patch_w": int(patch_w),
                "patch_h": int(patch_h),
                "dictionary_size": int(dictionary_size),
                "dict_alpha": float(cfg.dict_alpha),
                "dict_batch_size": int(cfg.dict_batch_size),
                "transform_algo": str(cfg.transform_algo),
                "transform_nnz": int(cfg.transform_nnz),
                "feature_mode": str(cfg.feature_mode),
                "include_valid_mask": bool(cfg.include_valid_mask),
                "mask_encoding": str(cfg.mask_encoding),
                "patches_per_image": int(patches_per_image),
                "patch_vector_length": int(patch_vector_length),
                "feature_vector_length": int(feature_vector_length),
                "apply_standard_scaler": bool(args.apply_standard_scaler),
                "source_paths": {k: str(v) for k, v in in_paths.items()},
            },
        )
        log(f"Saved trained dictionary artifact to: {save_path}")

    features_for_tree = features.astype(np.float64, copy=False)
    if args.apply_standard_scaler:
        scaler = StandardScaler()
        features_for_tree = scaler.fit_transform(features_for_tree)
        log("Applied StandardScaler before Ward linkage.")
    else:
        log("StandardScaler not applied (faithful current behavior).")

    linkage_matrix = linkage(features_for_tree, method="ward", metric="euclidean")
    merge_distances = linkage_matrix[:, 2].astype(np.float64, copy=False)
    max_merge_distance = float(np.max(merge_distances))
    min_merge_distance = float(np.min(merge_distances))

    plot_dendrogram_with_cut(
        linkage_matrix=linkage_matrix,
        separation_distance=max_merge_distance * 0.50,
        out_path=out_dendro / "dendrogram_reference.png",
        title="Ward dendrogram (reference cut at 50% of max distance)",
    )
    pd.DataFrame({"merge_distance": merge_distances}).to_csv(out_dendro / "merge_distances.csv", index=False)
    (out_dendro / "tree_info.json").write_text(
        json.dumps(
            {
                "n_images": int(n_images),
                "min_merge_distance": min_merge_distance,
                "max_merge_distance": max_merge_distance,
                "fractions": [float(v) for v in fractions],
                "sd_values": [float(v * max_merge_distance) for v in fractions],
                "patch_w": patch_w,
                "patch_h": patch_h,
                "dictionary_size": dictionary_size,
                "seed": seed,
                "feature_mode": cfg.feature_mode,
                "include_valid_mask": cfg.include_valid_mask,
                "mask_encoding": cfg.mask_encoding,
                "standard_scaler_applied": bool(args.apply_standard_scaler),
                "ranking_target_classes": ranking_target_classes,
                "default_working_sd_fraction": float(DEFAULT_WORKING_SD_FRACTION),
                "dictionary_mode": dictionary_mode,
                "dictionary_path": dictionary_path_for_report,
                "dictionary_metadata": dictionary_metadata,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    pca_coords = None
    if not args.no_pca:
        pca_coords = PCA(n_components=2, random_state=0).fit_transform(features_for_tree)

    runs: List[SDRunResult] = []
    for frac in fractions:
        sd_value = float(frac * max_merge_distance)
        sd_slug = f"sd_{int(round(frac * 100)):02d}pct"
        sd_dir = out_base / sd_slug
        sd_dir.mkdir(parents=True, exist_ok=True)

        labels = fcluster(linkage_matrix, t=sd_value, criterion="distance").astype(np.int32, copy=False)
        unique_labels = np.unique(labels)
        icv_per_class, class_sizes, class_indices = compute_icv_sst_space(X_sst=X_sst, labels=labels, mask=mask)

        singleton_count = int(np.sum(np.asarray(class_sizes, dtype=np.int32) == 1))
        mean_icv = float(np.mean(icv_per_class))
        std_icv = float(np.std(icv_per_class))
        behavior_label, behavior_reason = classify_behavior(
            number_of_classes=int(len(unique_labels)),
            class_sizes=class_sizes,
            singleton_count=singleton_count,
            total_images=int(n_images),
        )

        save_member_contact_sheets(
            out_dir=sd_dir,
            png_map=png_map,
            class_indices=class_indices,
            image_proxy=image_proxy,
            separation_distance=sd_value,
        )
        class_prototypes = save_prototypes(
            out_dir=sd_dir,
            X_norm=X_norm,
            mask=mask,
            class_indices=class_indices,
            separation_distance=sd_value,
            vmin=float(vlim[0]),
            vmax=float(vlim[1]),
        )
        save_class_homogeneity_artifacts(
            out_dir=sd_dir,
            X_norm=X_norm,
            mask=mask,
            class_indices=class_indices,
            class_prototypes=class_prototypes,
            png_map=png_map,
            separation_distance=sd_value,
        )
        plot_dendrogram_with_cut(
            linkage_matrix=linkage_matrix,
            separation_distance=sd_value,
            out_path=sd_dir / "dendrogram_cut.png",
            title=f"Ward dendrogram with SD cut ({frac:.0%} of max distance)",
        )
        if pca_coords is not None:
            plot_pca_classes(
                coords=pca_coords,
                labels=labels,
                separation_distance=sd_value,
                out_path=sd_dir / "pca2d_classes.png",
            )

        runs.append(
            SDRunResult(
                separation_distance=sd_value,
                sd_fraction_of_max=float(frac),
                max_merge_distance=max_merge_distance,
                number_of_classes=int(len(unique_labels)),
                class_sizes=json.dumps([int(v) for v in class_sizes]),
                min_class_size=int(np.min(class_sizes)),
                mean_class_size=float(np.mean(class_sizes)),
                max_class_size=int(np.max(class_sizes)),
                singleton_count=singleton_count,
                mean_icv=mean_icv,
                std_icv=std_icv,
                icv_per_class=json.dumps([float(v) for v in icv_per_class]),
                behavior_label=behavior_label,
                behavior_reason=behavior_reason,
                output_dir=str(sd_dir.relative_to(ROOT)).replace("\\", "/"),
            )
        )
        log(
            f"SD {frac:.0%} ({sd_value:.6f}) -> classes={len(unique_labels)} "
            f"min/mean/max={int(np.min(class_sizes))}/{float(np.mean(class_sizes)):.2f}/{int(np.max(class_sizes))} "
            f"singletons={singleton_count} mean_icv={mean_icv:.6f} [{behavior_label}]"
        )

    runs_df = save_runs_csv(runs, out_base / "runs.csv").sort_values("sd_fraction_of_max").reset_index(drop=True)
    ranked_df = rank_sd_candidates(runs_df, target_classes=ranking_target_classes)
    ranked_df.to_csv(out_base / "ranking.csv", index=False)

    build_markdown_report(
        report_path=out_base / "REPORT.md",
        out_base=out_base,
        runs_df=runs_df,
        ranked_df=ranked_df,
        fractions=fractions,
        cfg=cfg,
        seed=seed,
        patch_w=patch_w,
        patch_h=patch_h,
        dictionary_size=dictionary_size,
        ranking_target_classes=ranking_target_classes,
        standard_scaler_applied=bool(args.apply_standard_scaler),
        max_merge_distance=max_merge_distance,
        dictionary_mode=dictionary_mode,
        dictionary_path=dictionary_path_for_report,
    )

    elapsed = time.perf_counter() - t0
    top = ranked_df.head(min(3, len(ranked_df)))
    log(f"Top SD candidates (balanced, target classes={ranking_target_classes}):")
    for i, row in top.iterrows():
        log(
            f"  #{i+1} frac={row['sd_fraction_of_max']:.2f} sd={row['separation_distance']:.6f} "
            f"score={row['balanced_score']:.4f} classes={int(row['number_of_classes'])} "
            f"singletons={int(row['singleton_count'])} behavior={row['behavior_label']}"
        )
    log(f"Wrote runs: {out_base / 'runs.csv'}")
    log(f"Wrote ranking: {out_base / 'ranking.csv'}")
    log(f"Wrote report: {out_base / 'REPORT.md'}")
    log(f"Done in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
