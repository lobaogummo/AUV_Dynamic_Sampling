"""Dictionary-size sensitivity for Fossum initial classification with fixed patch size."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageDraw, ImageFont
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import MiniBatchDictionaryLearning

ROOT = Path(__file__).resolve().parents[1]

IN_X_NORM = ROOT / "results" / "fossum" / "X_surface_300_norm.npy"
IN_X_SST = ROOT / "results" / "fossum" / "X_surface_300.npy"
IN_MASK = ROOT / "results" / "fossum" / "mask_common.npy"
IN_STATS = ROOT / "results" / "fossum" / "global_stats.json"
IN_PNG_DIR = ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis"

DEFAULT_OUT_BASE = ROOT / "results" / "fossum" / "dictionary_size_sensitivity_fossum"
DEFAULT_DOC = ROOT / "docs" / "DICTIONARY_SIZE_SENSITIVITY_FOSSUM.md"

FIXED_PATCH_W = 72
FIXED_PATCH_H = 40
DEFAULT_XDS_VALUES = list(range(2, 13))
DEFAULT_SEEDS = [11, 23, 37, 53, 71]

N_CLASSES = 4
DICT_ALPHA = 1.0
DICT_BATCH_SIZE = 4096
TRANSFORM_ALGO = "omp"
TRANSFORM_NNZ = 2
MAX_CONTACT_IMAGES_PER_CLASS = 50


@dataclass
class RunResult:
    dictionary_size: int
    patch_w: int
    patch_h: int
    seed: int
    patches_per_image: int
    total_patches: int
    patch_vector_length: int
    number_of_classes: int
    class_sizes: str
    icv_class_01: float
    icv_class_02: float
    icv_class_03: float
    icv_class_04: float
    mean_icv: float
    std_icv: float
    min_class_size: int
    mean_class_size: float
    max_class_size: int
    runtime_seconds: float
    notes: str


def log(msg: str) -> None:
    print(f"[dictionary-size] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fossum dictionary-size sensitivity with fixed patch size.")
    p.add_argument("--out-base", type=Path, default=DEFAULT_OUT_BASE)
    p.add_argument("--doc-path", type=Path, default=DEFAULT_DOC)
    p.add_argument("--xds-values", nargs="*", type=int, default=None)
    p.add_argument("--seeds", nargs="*", type=int, default=None)
    p.add_argument("--no-resume", action="store_true")
    return p.parse_args()


def parse_xds_values(values: Sequence[int] | None) -> List[int]:
    if not values:
        return DEFAULT_XDS_VALUES.copy()
    out: List[int] = []
    for v in values:
        if int(v) <= 0:
            raise ValueError(f"Invalid dictionary size '{v}'. Must be > 0.")
        out.append(int(v))
    uniq: List[int] = []
    seen = set()
    for v in out:
        if v not in seen:
            uniq.append(v)
            seen.add(v)
    return uniq


def ensure_inputs() -> None:
    missing = [p for p in [IN_X_SST, IN_X_NORM, IN_MASK, IN_STATS, IN_PNG_DIR] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing inputs: " + ", ".join(str(x) for x in missing))


def load_numeric_inputs() -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict, Tuple[float, float]]:
    X_sst = np.load(IN_X_SST).astype(np.float32, copy=False)
    X_norm = np.load(IN_X_NORM).astype(np.float32, copy=False)
    mask = np.load(IN_MASK).astype(bool, copy=False)
    stats = json.loads(IN_STATS.read_text(encoding="utf-8"))
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
    return X_sst, X_norm, mask, stats, (-vlim, +vlim)


def build_png_map() -> Dict[int, Path]:
    files = sorted(IN_PNG_DIR.glob("X_surface_norm_z*.png"))
    if not files:
        raise RuntimeError(f"No class-panel PNGs found in {IN_PNG_DIR}")
    out: Dict[int, Path] = {}
    rx = re.compile(r"_z(\d+)\.png$", re.IGNORECASE)
    for p in files:
        m = rx.search(p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def patch_count(ny: int, nx: int, patch_h: int, patch_w: int) -> int:
    return int((ny - patch_h + 1) * (nx - patch_w + 1))


def valid_patch_size(ny: int, nx: int, patch_h: int, patch_w: int) -> bool:
    return patch_h > 0 and patch_w > 0 and patch_h <= ny and patch_w <= nx


def extract_patches(image_2d: np.ndarray, patch_h: int, patch_w: int) -> np.ndarray:
    clean = np.nan_to_num(image_2d, nan=0.0).astype(np.float32, copy=False)
    windows = sliding_window_view(clean, (patch_h, patch_w))
    return windows.reshape(-1, patch_h * patch_w)


def train_dictionary_seeded_stream(
    X: np.ndarray,
    patch_h: int,
    patch_w: int,
    seed: int,
    n_dict: int,
) -> MiniBatchDictionaryLearning:
    rng = np.random.default_rng(seed)
    model = MiniBatchDictionaryLearning(
        n_components=n_dict,
        alpha=DICT_ALPHA,
        batch_size=DICT_BATCH_SIZE,
        random_state=seed,
        shuffle=True,
        transform_algorithm=TRANSFORM_ALGO,
        transform_n_nonzero_coefs=min(TRANSFORM_NNZ, n_dict),
    )
    image_order = rng.permutation(X.shape[0])
    for img_idx in image_order:
        patches = extract_patches(X[img_idx], patch_h, patch_w)
        patch_order = rng.permutation(patches.shape[0])
        shuffled = patches[patch_order]
        for start in range(0, shuffled.shape[0], DICT_BATCH_SIZE):
            model.partial_fit(shuffled[start : start + DICT_BATCH_SIZE])
    return model


def encode_images(
    X: np.ndarray,
    model: MiniBatchDictionaryLearning,
    patch_h: int,
    patch_w: int,
    n_dict: int,
) -> np.ndarray:
    n = X.shape[0]
    feats = np.zeros((n, n_dict * 2), dtype=np.float32)
    for i in range(n):
        patches = extract_patches(X[i], patch_h, patch_w)
        codes = model.transform(patches)
        abs_codes = np.abs(codes)
        feats[i, :n_dict] = np.mean(abs_codes, axis=0)
        feats[i, n_dict:] = np.std(abs_codes, axis=0)
    return feats


def compute_icv_sst_space(
    X_sst: np.ndarray, labels: np.ndarray, mask: np.ndarray
) -> Tuple[List[float], List[int], List[np.ndarray]]:
    icv_per_class: List[float] = []
    class_sizes: List[int] = []
    class_indices: List[np.ndarray] = []
    for class_id in sorted(np.unique(labels)):
        idx = np.where(labels == class_id)[0]
        class_indices.append(idx)
        class_sizes.append(int(idx.size))
        class_pixels = X_sst[idx][:, mask]
        pixel_var = np.var(class_pixels, axis=0, ddof=0)
        icv_per_class.append(float(np.sum(pixel_var)))
    return icv_per_class, class_sizes, class_indices


def class_mean_image(class_stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    mean_img = np.mean(np.nan_to_num(class_stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    mean_img[~mask] = np.nan
    return mean_img


def save_prototypes_for_run(
    out_base: Path,
    X: np.ndarray,
    mask: np.ndarray,
    class_indices: List[np.ndarray],
    dictionary_size: int,
    patch_w: int,
    patch_h: int,
    seed: int,
    vmin: float,
    vmax: float,
) -> None:
    out_dir = out_base / f"prototypes_xds{dictionary_size:02d}_seed{seed:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")
    protos: List[np.ndarray] = []
    for ci, idx in enumerate(class_indices, start=1):
        proto = class_mean_image(X[idx], mask=mask)
        protos.append(proto)
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(
            f"Prototype class {ci:02d} (n={len(idx)}) [xds={dictionary_size}, patch={patch_w}x{patch_h}] seed={seed}"
        )
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
    fig.suptitle(f"Prototypes [xds={dictionary_size}, patch={patch_w}x{patch_h}] seed={seed}")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85)
    cbar.set_label("Normalized temperature (-)")
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.08, top=0.86, wspace=0.20)
    fig.savefig(out_dir / "prototypes_panel.png", dpi=160)
    plt.close(fig)


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


def save_member_contact_sheets_from_png_source(
    out_base: Path,
    png_map: Dict[int, Path],
    class_indices: List[np.ndarray],
    dictionary_size: int,
    patch_w: int,
    patch_h: int,
    seed: int,
) -> None:
    out_dir = out_base / f"class_members_xds{dictionary_size:02d}_seed{seed:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for ci, idx in enumerate(class_indices, start=1):
        selected = np.sort(idx)[:MAX_CONTACT_IMAGES_PER_CLASS]
        rows = []
        panel_pngs: List[Path] = []
        panel_labels: List[str] = []
        for img_idx in selected:
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
                    "png_path": str(png_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )

        pd.DataFrame(rows).to_csv(out_dir / f"class_{ci:02d}_members_list.csv", index=False)
        title = (
            f"Class {ci:02d} members (n={len(idx)}, shown={len(panel_pngs)}) "
            f"[xds={dictionary_size}, patch={patch_w}x{patch_h}] seed={seed}"
        )
        make_contact_sheet_from_pngs(
            png_paths=panel_pngs,
            labels=panel_labels,
            out_path=out_dir / f"class_{ci:02d}_members_panel.png",
            title=title,
            cols=10,
            thumb_size=(180, 120),
        )


def run_single(
    out_base: Path,
    X_norm: np.ndarray,
    X_sst: np.ndarray,
    mask: np.ndarray,
    png_map: Dict[int, Path],
    dictionary_size: int,
    seed: int,
    vmin: float,
    vmax: float,
) -> RunResult:
    t0 = time.perf_counter()
    n, ny, nx = X_norm.shape
    patch_w = FIXED_PATCH_W
    patch_h = FIXED_PATCH_H

    if not valid_patch_size(ny, nx, patch_h, patch_w):
        dt = time.perf_counter() - t0
        return RunResult(
            dictionary_size=dictionary_size,
            patch_w=patch_w,
            patch_h=patch_h,
            seed=seed,
            patches_per_image=0,
            total_patches=0,
            patch_vector_length=patch_w * patch_h,
            number_of_classes=0,
            class_sizes="[]",
            icv_class_01=float("nan"),
            icv_class_02=float("nan"),
            icv_class_03=float("nan"),
            icv_class_04=float("nan"),
            mean_icv=float("nan"),
            std_icv=float("nan"),
            min_class_size=0,
            mean_class_size=float("nan"),
            max_class_size=0,
            runtime_seconds=dt,
            notes="skipped invalid patch size",
        )

    patches_per_image = patch_count(ny, nx, patch_h, patch_w)
    total_patches = patches_per_image * n
    patch_vector_length = patch_w * patch_h

    model = train_dictionary_seeded_stream(
        X_norm,
        patch_h=patch_h,
        patch_w=patch_w,
        seed=seed,
        n_dict=dictionary_size,
    )
    features = encode_images(
        X_norm,
        model=model,
        patch_h=patch_h,
        patch_w=patch_w,
        n_dict=dictionary_size,
    )
    labels = AgglomerativeClustering(n_clusters=N_CLASSES, linkage="ward").fit_predict(features)
    icv_per_class, class_sizes, class_indices = compute_icv_sst_space(X_sst=X_sst, labels=labels, mask=mask)

    padded_icv = icv_per_class + [float("nan")] * max(0, N_CLASSES - len(icv_per_class))
    mean_icv = float(np.mean(icv_per_class))
    std_icv = float(np.std(icv_per_class))

    save_prototypes_for_run(
        out_base=out_base,
        X=X_norm,
        mask=mask,
        class_indices=class_indices,
        dictionary_size=dictionary_size,
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
        vmin=vmin,
        vmax=vmax,
    )
    save_member_contact_sheets_from_png_source(
        out_base=out_base,
        png_map=png_map,
        class_indices=class_indices,
        dictionary_size=dictionary_size,
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
    )

    dt = time.perf_counter() - t0
    return RunResult(
        dictionary_size=dictionary_size,
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
        patches_per_image=patches_per_image,
        total_patches=total_patches,
        patch_vector_length=patch_vector_length,
        number_of_classes=int(len(class_sizes)),
        class_sizes=json.dumps(class_sizes),
        icv_class_01=float(padded_icv[0]),
        icv_class_02=float(padded_icv[1]),
        icv_class_03=float(padded_icv[2]),
        icv_class_04=float(padded_icv[3]),
        mean_icv=mean_icv,
        std_icv=std_icv,
        min_class_size=int(np.min(class_sizes)),
        mean_class_size=float(np.mean(class_sizes)),
        max_class_size=int(np.max(class_sizes)),
        runtime_seconds=float(dt),
        notes="ok",
    )


def save_runs_csv(rows: Iterable[RunResult], out_runs: Path) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    out_runs.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_runs, index=False)
    return df


def build_summary(runs_df: pd.DataFrame, requested_runs: int) -> pd.DataFrame:
    grouped = runs_df.groupby(["dictionary_size"], as_index=False)
    summary = grouped.agg(
        executed_runs=("seed", "count"),
        patch_w=("patch_w", "first"),
        patch_h=("patch_h", "first"),
        patches_per_image=("patches_per_image", "first"),
        total_patches=("total_patches", "first"),
        patch_vector_length=("patch_vector_length", "first"),
        mean_icv_mean=("mean_icv", "mean"),
        mean_icv_std=("mean_icv", "std"),
        std_icv_mean=("std_icv", "mean"),
        std_icv_std=("std_icv", "std"),
        min_class_size_mean=("min_class_size", "mean"),
        min_class_size_min=("min_class_size", "min"),
        mean_class_size_mean=("mean_class_size", "mean"),
        max_class_size_mean=("max_class_size", "mean"),
        runtime_mean_seconds=("runtime_seconds", "mean"),
        runtime_std_seconds=("runtime_seconds", "std"),
    )
    summary["requested_runs"] = requested_runs
    summary["reduced_seed_count"] = summary["executed_runs"] < requested_runs
    return summary.sort_values(["dictionary_size"]).reset_index(drop=True)


def label_from_xds(xds: int) -> str:
    return f"xds={int(xds)}"


def plot_boxplot_icv(runs_df: pd.DataFrame, out_plots: Path) -> None:
    out_plots.mkdir(parents=True, exist_ok=True)
    ordered = runs_df.sort_values(["dictionary_size"]).copy()
    labels = []
    data = []
    for xds, sub in ordered.groupby("dictionary_size"):
        labels.append(label_from_xds(int(xds)))
        data.append(sub["mean_icv"].to_numpy())

    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.boxplot(data, labels=labels, showmeans=True)
    ax.set_title("Fig 6b style: ICV spread across runs by dictionary size")
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel("Mean ICV (SST/original space)")
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_plots / "fig6b_icv_boxplot_dictionarysize.png", dpi=170)
    plt.close(fig)


def plot_boxplot_zoom_centered(runs_df: pd.DataFrame, out_plots: Path) -> None:
    ordered = runs_df.sort_values(["dictionary_size"]).copy()
    labels = []
    centered = []
    for xds, sub in ordered.groupby("dictionary_size"):
        vals = sub["mean_icv"].to_numpy(dtype=float)
        labels.append(label_from_xds(int(xds)))
        centered.append(vals - np.mean(vals))

    all_vals = np.concatenate(centered) if centered else np.array([0.0])
    lim = max(2.0, float(np.percentile(np.abs(all_vals), 95.0)) * 1.25)

    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.boxplot(centered, labels=labels, showmeans=True)
    ax.set_ylim(-lim, +lim)
    ax.set_title("Fig 6b zoom: centered mean ICV by dictionary size")
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel("mean_icv - dictionary_size_mean_icv")
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_plots / "fig6b_icv_boxplot_dictionarysize_zoom.png", dpi=170)
    plt.close(fig)


def build_variance_table(runs_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for xds, sub in runs_df.groupby("dictionary_size"):
        vals = sub.sort_values("seed")["mean_icv"].to_numpy(dtype=float)
        mn = float(np.min(vals))
        mx = float(np.max(vals))
        mean_val = float(np.mean(vals))
        spread = float(mx - mn)
        rel = spread / mean_val if mean_val != 0 else np.nan
        rows.append(
            {
                "dictionary_size": int(xds),
                "xds_label": label_from_xds(int(xds)),
                "mean_icv_min": mn,
                "mean_icv_max": mx,
                "absolute_spread": spread,
                "relative_spread": rel,
                "relative_spread_pct": rel * 100.0 if np.isfinite(rel) else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["dictionary_size"]).reset_index(drop=True)


def plot_seed_points(runs_df: pd.DataFrame, out_plots: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ordered = runs_df.sort_values(["dictionary_size", "seed"])
    groups = list(ordered.groupby("dictionary_size"))
    x = np.arange(len(groups))
    labels = []
    for i, (xds, sub) in enumerate(groups):
        labels.append(label_from_xds(int(xds)))
        vals = sub["mean_icv"].to_numpy(dtype=float)
        jit = np.linspace(-0.12, 0.12, len(vals)) if len(vals) > 1 else np.array([0.0])
        ax.scatter(np.full_like(vals, x[i], dtype=float) + jit, vals, s=28)
        ax.plot([x[i] - 0.18, x[i] + 0.18], [np.mean(vals), np.mean(vals)], color="black", linewidth=1.4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("ICV seed points by dictionary size")
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel("Mean ICV (SST/original space)")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_plots / "icv_seed_points_by_dictionarysize.png", dpi=170)
    plt.close(fig)


def plot_line_metric(df: pd.DataFrame, y_col: str, out_path: Path, title: str, ylabel: str) -> None:
    labels = df["xds_label"].tolist()
    x = np.arange(len(df))
    y = df[y_col].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.plot(x, y, marker="o", linewidth=1.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def plot_summary_metric(summary_df: pd.DataFrame, y_col: str, yerr_col: str | None, out_path: Path, title: str, ylabel: str) -> None:
    labels = [label_from_xds(int(r["dictionary_size"])) for _, r in summary_df.iterrows()]
    x = np.arange(len(summary_df))
    y = summary_df[y_col].to_numpy(dtype=float)
    yerr = summary_df[yerr_col].to_numpy(dtype=float) if yerr_col else None

    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    if yerr_col:
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.6)
    else:
        ax.plot(x, y, marker="o", linewidth=1.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def make_md_table(df: pd.DataFrame, cols: List[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for _, r in df.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + body)


def build_ranking(summary_df: pd.DataFrame) -> pd.DataFrame:
    d = summary_df.copy()
    d["rank_mean_icv"] = d["mean_icv_mean"].rank(method="min", ascending=True)
    d["rank_icv_spread"] = d["mean_icv_std"].rank(method="min", ascending=True)
    d["rank_std_icv"] = d["std_icv_mean"].rank(method="min", ascending=True)
    d["rank_min_class"] = d["min_class_size_min"].rank(method="min", ascending=False)
    d["rank_runtime"] = d["runtime_mean_seconds"].rank(method="min", ascending=True)
    d["balanced_score"] = (
        0.30 * d["rank_mean_icv"]
        + 0.20 * d["rank_icv_spread"]
        + 0.20 * d["rank_std_icv"]
        + 0.20 * d["rank_min_class"]
        + 0.10 * d["rank_runtime"]
    )
    return d.sort_values("balanced_score").reset_index(drop=True)


def write_report(
    doc_path: Path,
    out_base: Path,
    summary_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    xds_values: List[int],
    seeds: List[int],
) -> None:
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    top_n = min(3, len(ranking_df))
    top = ranking_df.head(top_n)
    nonzero_spread = int(np.sum(np.nan_to_num(summary_df["mean_icv_std"].to_numpy(dtype=float), nan=0.0) > 0.0))

    xds4_note = "xds=4 nao foi testado nesta execucao."
    if np.any(ranking_df["dictionary_size"].to_numpy(dtype=int) == 4):
        idx = np.where(ranking_df["dictionary_size"].to_numpy(dtype=int) == 4)[0][0]
        pos = int(idx + 1)
        xds4_note = "xds=4 continua a melhor escolha." if pos == 1 else f"xds=4 deixou de ser a melhor escolha (posicao {pos})."

    md = [
        "# DICTIONARY_SIZE_SENSITIVITY_FOSSUM",
        "",
        "## Correcoes aplicadas",
        "- random_state=seed no MiniBatchDictionaryLearning",
        "- shuffle=True no dicionario",
        "- ordem das imagens embaralhada por seed",
        "- ordem dos patches embaralhada por seed",
        "- partial_fit em mini-batches",
        "",
        "## Inputs numericos",
        f"- `{IN_X_SST.relative_to(ROOT).as_posix()}` (SST/original, usado para ICV)",
        f"- `{IN_X_NORM.relative_to(ROOT).as_posix()}`",
        f"- `{IN_MASK.relative_to(ROOT).as_posix()}`",
        "",
        "## Distincao metodologica",
        "- dictionary learning, sparse coding e clustering: feitos em `X_surface_300_norm.npy`",
        "- ICV: calculada em `X_surface_300.npy` (temperatura SST/original) usando os labels do clustering em normalizado",
        "- definicao ICV por classe: soma da variancia pixel-a-pixel sobre a mascara valida",
        "",
        "## PNGs",
        "- PNGs nao foram usados para calculo numerico.",
        f"- PNGs usados apenas para paineis de classe: `{IN_PNG_DIR.relative_to(ROOT).as_posix()}`",
        "",
        "## Configuracao",
        f"- patch size fixo: ({FIXED_PATCH_W},{FIXED_PATCH_H})",
        f"- dictionary sizes (xds): {', '.join(str(x) for x in xds_values)}",
        f"- seeds: {', '.join(str(s) for s in seeds)}",
        "",
        "## Variabilidade entre seeds",
        f"- dictionary sizes com mean_icv_std > 0: {nonzero_spread} / {len(summary_df)}",
        "",
        "## Summary",
        make_md_table(
            summary_df[
                [
                    "dictionary_size",
                    "executed_runs",
                    "mean_icv_mean",
                    "mean_icv_std",
                    "std_icv_mean",
                    "min_class_size_min",
                    "runtime_mean_seconds",
                ]
            ],
            ["dictionary_size", "executed_runs", "mean_icv_mean", "mean_icv_std", "std_icv_mean", "min_class_size_min", "runtime_mean_seconds"],
        ),
        "",
        "## Ranking atualizado (balanced)",
        make_md_table(
            ranking_df[
                [
                    "dictionary_size",
                    "balanced_score",
                    "mean_icv_mean",
                    "mean_icv_std",
                    "std_icv_mean",
                    "min_class_size_min",
                    "runtime_mean_seconds",
                ]
            ],
            ["dictionary_size", "balanced_score", "mean_icv_mean", "mean_icv_std", "std_icv_mean", "min_class_size_min", "runtime_mean_seconds"],
        ),
        "",
        "## Melhores candidatos finais",
        make_md_table(
            top[["dictionary_size", "balanced_score", "mean_icv_mean", "mean_icv_std", "min_class_size_min", "runtime_mean_seconds"]],
            ["dictionary_size", "balanced_score", "mean_icv_mean", "mean_icv_std", "min_class_size_min", "runtime_mean_seconds"],
        ),
        "",
        "## Check xds=4",
        f"- {xds4_note}",
        "",
        "## Caminhos de outputs",
        f"- runs: `{(out_base / 'runs.csv').relative_to(ROOT).as_posix()}`",
        f"- summary: `{(out_base / 'summary.csv').relative_to(ROOT).as_posix()}`",
        f"- plots: `{(out_base / 'plots').relative_to(ROOT).as_posix()}`",
        f"- prototipos: `{(out_base / 'prototypes_xdsXX_seedSS').relative_to(ROOT).as_posix()}`",
        f"- paineis de classe: `{(out_base / 'class_members_xdsXX_seedSS').relative_to(ROOT).as_posix()}`",
    ]
    doc_path.write_text("\n".join(md), encoding="utf-8")


def load_existing_runs(out_runs: Path) -> List[RunResult]:
    if not out_runs.exists():
        return []
    df = pd.read_csv(out_runs)
    rows: List[RunResult] = []
    for _, r in df.iterrows():
        rows.append(
            RunResult(
                dictionary_size=int(r["dictionary_size"]),
                patch_w=int(r["patch_w"]),
                patch_h=int(r["patch_h"]),
                seed=int(r["seed"]),
                patches_per_image=int(r["patches_per_image"]),
                total_patches=int(r["total_patches"]),
                patch_vector_length=int(r["patch_vector_length"]),
                number_of_classes=int(r["number_of_classes"]),
                class_sizes=str(r["class_sizes"]),
                icv_class_01=float(r["icv_class_01"]),
                icv_class_02=float(r["icv_class_02"]),
                icv_class_03=float(r["icv_class_03"]),
                icv_class_04=float(r["icv_class_04"]),
                mean_icv=float(r["mean_icv"]),
                std_icv=float(r["std_icv"]),
                min_class_size=int(r["min_class_size"]),
                mean_class_size=float(r["mean_class_size"]),
                max_class_size=int(r["max_class_size"]),
                runtime_seconds=float(r["runtime_seconds"]),
                notes=str(r["notes"]),
            )
        )
    return rows


def main() -> None:
    args = parse_args()
    xds_values = parse_xds_values(args.xds_values)
    seeds = args.seeds if args.seeds else DEFAULT_SEEDS.copy()

    ensure_inputs()
    X_sst, X_norm, mask, _stats, (vmin, vmax) = load_numeric_inputs()
    png_map = build_png_map()

    out_base = args.out_base.resolve()
    out_runs = out_base / "runs.csv"
    out_summary = out_base / "summary.csv"
    out_plots = out_base / "plots"
    out_base.mkdir(parents=True, exist_ok=True)
    out_plots.mkdir(parents=True, exist_ok=True)

    runs = [] if args.no_resume else load_existing_runs(out_runs)
    done = {(r.dictionary_size, r.seed) for r in runs if r.notes == "ok"}

    log(
        f"Clustering inputs (normalized): "
        f"{IN_X_NORM.relative_to(ROOT).as_posix()} + {IN_MASK.relative_to(ROOT).as_posix()}"
    )
    log(
        f"ICV inputs (SST/original): "
        f"{IN_X_SST.relative_to(ROOT).as_posix()} + {IN_MASK.relative_to(ROOT).as_posix()}"
    )
    log(f"PNG visual source only: {IN_PNG_DIR.relative_to(ROOT).as_posix()}")
    log(f"Fixed patch size={FIXED_PATCH_W}x{FIXED_PATCH_H}")
    log(f"Dictionary sizes={xds_values}")
    log(f"Seeds={seeds}")
    log(f"Resume={not args.no_resume}; existing_ok_runs={len(done)}")

    for xds in xds_values:
        log(f"Dictionary size xds={xds}")
        for seed in seeds:
            key = (xds, seed)
            if key in done:
                log(f"  skip existing xds={xds} seed={seed}")
                continue
            log(f"  run start xds={xds} seed={seed}")
            result = run_single(
                out_base=out_base,
                X_norm=X_norm,
                X_sst=X_sst,
                mask=mask,
                png_map=png_map,
                dictionary_size=xds,
                seed=seed,
                vmin=vmin,
                vmax=vmax,
            )
            runs.append(result)
            save_runs_csv(runs, out_runs)
            log(
                f"  run done xds={xds} seed={seed}: "
                f"mean_icv={result.mean_icv:.6f} std_icv={result.std_icv:.6f} "
                f"min_class={result.min_class_size} runtime={result.runtime_seconds:.2f}s"
            )

    runs_df = save_runs_csv(runs, out_runs)
    valid_runs = runs_df[runs_df["notes"] == "ok"].copy()
    summary_df = build_summary(valid_runs, requested_runs=len(seeds))
    summary_df.to_csv(out_summary, index=False)

    plot_boxplot_icv(valid_runs, out_plots)
    plot_boxplot_zoom_centered(valid_runs, out_plots)
    plot_seed_points(valid_runs, out_plots)
    spread_df = build_variance_table(valid_runs)
    plot_line_metric(
        spread_df,
        y_col="absolute_spread",
        out_path=out_plots / "icv_absolute_spread_vs_dictionarysize.png",
        title="Absolute spread of mean ICV (SST/original) across seeds",
        ylabel="Absolute spread (max - min)",
    )
    plot_line_metric(
        spread_df,
        y_col="relative_spread_pct",
        out_path=out_plots / "icv_relative_spread_vs_dictionarysize.png",
        title="Relative spread of mean ICV (SST/original) across seeds",
        ylabel="Relative spread (%)",
    )
    plot_summary_metric(
        summary_df,
        y_col="mean_icv_mean",
        yerr_col="mean_icv_std",
        out_path=out_plots / "icv_mean_vs_dictionarysize.png",
        title="Mean ICV (SST/original) vs Dictionary Size (error bars: run std)",
        ylabel="Mean ICV (SST/original space)",
    )
    plot_summary_metric(
        summary_df,
        y_col="std_icv_mean",
        yerr_col="std_icv_std",
        out_path=out_plots / "icv_std_vs_dictionarysize.png",
        title="Std(ICV across classes, SST/original) vs Dictionary Size",
        ylabel="Std ICV (SST/original space)",
    )
    plot_summary_metric(
        summary_df,
        y_col="min_class_size_mean",
        yerr_col=None,
        out_path=out_plots / "min_class_size_vs_dictionarysize.png",
        title="Minimum class size vs Dictionary Size",
        ylabel="Min class size (mean over runs)",
    )
    plot_summary_metric(
        summary_df,
        y_col="runtime_mean_seconds",
        yerr_col="runtime_std_seconds",
        out_path=out_plots / "runtime_vs_dictionarysize.png",
        title="Runtime vs Dictionary Size",
        ylabel="Runtime (seconds)",
    )

    ranking = build_ranking(summary_df)
    write_report(
        doc_path=args.doc_path.resolve(),
        out_base=out_base,
        summary_df=summary_df,
        ranking_df=ranking,
        xds_values=xds_values,
        seeds=seeds,
    )

    top_n = min(3, len(ranking))
    log("Top dictionary-size candidates (balanced):")
    for i, row in ranking.head(top_n).iterrows():
        log(
            f"  #{i+1} xds={int(row['dictionary_size'])} "
            f"score={row['balanced_score']:.4f} mean_icv={row['mean_icv_mean']:.6f} "
            f"spread={row['mean_icv_std']:.6f} min_class={int(row['min_class_size_min'])} "
            f"runtime={row['runtime_mean_seconds']:.2f}s"
        )
    log(f"Wrote runs: {out_runs}")
    log(f"Wrote summary: {out_summary}")
    log(f"Wrote plots: {out_plots}")
    log(f"Wrote doc: {args.doc_path.resolve()}")


if __name__ == "__main__":
    main()
