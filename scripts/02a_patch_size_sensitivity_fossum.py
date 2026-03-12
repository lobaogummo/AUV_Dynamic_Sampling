"""Fossum-faithful patch-size sensitivity stage (xpa selection only).

This script keeps dictionary size fixed (xds=4) and evaluates patch sizes
with multiple random seeds. ICV is computed in image/temperature space:
for each class, pixelwise variance across class members is summed over
the valid common mask.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import MiniBatchDictionaryLearning


ROOT = Path(__file__).resolve().parents[1]

IN_X_NORM = ROOT / "results" / "fossum" / "X_surface_300_norm.npy"
IN_MASK = ROOT / "results" / "fossum" / "mask_common.npy"
IN_STATS = ROOT / "results" / "fossum" / "global_stats.json"

OUT_BASE = ROOT / "results" / "fossum" / "patch_size_sensitivity_fossum"
OUT_PLOTS = OUT_BASE / "plots"
OUT_RUNS = OUT_BASE / "runs.csv"
OUT_SUMMARY = OUT_BASE / "summary.csv"
OUT_DOC = ROOT / "docs" / "PATCH_SIZE_SENSITIVITY_FOSSUM.md"

PATCH_SIZES = [
    (16, 16),
    (24, 16),
    (32, 20),
    (40, 24),
    (48, 32),
    (56, 32),
    (64, 36),
    (72, 40),
    (80, 44),
]

TARGET_SEEDS = [11, 23, 37, 53, 71]  # 5 runs per patch size
MIN_SEEDS_IF_REDUCED = 3

N_DICT = 4
N_CLASSES = 4
DICT_ALPHA = 1.0
DICT_BATCH_SIZE = 4096
DICT_SHUFFLE = True
TRANSFORM_ALGO = "omp"
TRANSFORM_NNZ = 2
MAX_CONTACT_IMAGES_PER_CLASS = 50


@dataclass
class RunResult:
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
    print(f"[patch-sens] {msg}")


def require_inputs() -> None:
    missing = [p for p in [IN_X_NORM, IN_MASK, IN_STATS] if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required input(s): "
            + ", ".join(str(p.relative_to(ROOT)).replace("\\", "/") for p in missing)
        )


def load_inputs() -> tuple[np.ndarray, np.ndarray, dict, tuple[float, float]]:
    require_inputs()
    X = np.load(IN_X_NORM).astype(np.float32, copy=False)
    mask = np.load(IN_MASK).astype(bool, copy=False)
    stats = json.loads(IN_STATS.read_text(encoding="utf-8"))

    if X.ndim != 3:
        raise RuntimeError(f"Expected 3D array (n, y, x), got {X.shape}")
    if mask.shape != X.shape[1:]:
        raise RuntimeError(f"Mask shape mismatch: {mask.shape} vs {X.shape[1:]}")

    # Ensure outside-mask values remain NaN for visuals.
    X = X.copy()
    X[:, ~mask] = np.nan

    valid_vals = X[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals), 98.0))
    if not np.isfinite(vlim) or vlim <= 0:
        vlim = 1.0
    viz_scale = (-vlim, +vlim)

    log(
        f"Loaded X={X.shape}, mask={mask.shape}, valid_fraction={float(mask.mean()):.6f}, "
        f"viz_scale=({viz_scale[0]:.4f}, {viz_scale[1]:.4f})"
    )
    return X, mask, stats, viz_scale


def patch_count(ny: int, nx: int, patch_h: int, patch_w: int) -> int:
    return int((ny - patch_h + 1) * (nx - patch_w + 1))


def valid_patch_size(ny: int, nx: int, patch_h: int, patch_w: int) -> bool:
    return patch_h > 0 and patch_w > 0 and patch_h <= ny and patch_w <= nx


def extract_patches(image_2d: np.ndarray, patch_h: int, patch_w: int) -> np.ndarray:
    clean = np.nan_to_num(image_2d, nan=0.0).astype(np.float32, copy=False)
    windows = sliding_window_view(clean, (patch_h, patch_w))
    return windows.reshape(-1, patch_h * patch_w)


def learn_dictionary(X: np.ndarray, patch_h: int, patch_w: int, seed: int) -> MiniBatchDictionaryLearning:
    model = MiniBatchDictionaryLearning(
        n_components=N_DICT,
        alpha=DICT_ALPHA,
        batch_size=DICT_BATCH_SIZE,
        random_state=seed,
        shuffle=DICT_SHUFFLE,
        transform_algorithm=TRANSFORM_ALGO,
        transform_n_nonzero_coefs=TRANSFORM_NNZ,
    )
    for i in range(X.shape[0]):
        model.partial_fit(extract_patches(X[i], patch_h, patch_w))
    return model


def encode_images(X: np.ndarray, model: MiniBatchDictionaryLearning, patch_h: int, patch_w: int) -> np.ndarray:
    # Compact embedding per image from sparse code distribution.
    n = X.shape[0]
    feats = np.zeros((n, N_DICT * 2), dtype=np.float32)
    for i in range(n):
        patches = extract_patches(X[i], patch_h, patch_w)
        codes = model.transform(patches)
        abs_codes = np.abs(codes)
        feats[i, :N_DICT] = np.mean(abs_codes, axis=0)
        feats[i, N_DICT:] = np.std(abs_codes, axis=0)
    return feats


def compute_icv_image_space(
    X: np.ndarray, labels: np.ndarray, mask: np.ndarray
) -> tuple[list[float], list[int], list[np.ndarray]]:
    icv_per_class: list[float] = []
    class_sizes: list[int] = []
    class_indices: list[np.ndarray] = []

    for class_id in sorted(np.unique(labels)):
        idx = np.where(labels == class_id)[0]
        class_indices.append(idx)
        class_sizes.append(int(idx.size))
        class_pixels = X[idx][:, mask]  # shape: (n_class, n_valid_pixels)
        pixel_var = np.var(class_pixels, axis=0, ddof=0)
        icv = float(np.sum(pixel_var))
        icv_per_class.append(icv)

    return icv_per_class, class_sizes, class_indices


def class_mean_image(class_stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    # Avoid warnings from nanmean on outside-mask pixels.
    mean_img = np.mean(np.nan_to_num(class_stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    mean_img[~mask] = np.nan
    return mean_img


def save_prototypes_for_run(
    X: np.ndarray,
    mask: np.ndarray,
    class_indices: list[np.ndarray],
    patch_w: int,
    patch_h: int,
    seed: int,
    vmin: float,
    vmax: float,
) -> None:
    out_dir = OUT_BASE / f"prototypes_w{patch_w:02d}_h{patch_h:02d}_seed{seed:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")
    protos: list[np.ndarray] = []

    for ci, idx in enumerate(class_indices, start=1):
        class_stack = X[idx]
        proto = class_mean_image(class_stack, mask=mask)
        protos.append(proto)

        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"Prototype class {ci:02d} (n={len(idx)}) [{patch_w}x{patch_h}] seed={seed}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Normalized TEMP")
        fig.tight_layout()
        fig.savefig(out_dir / f"prototype_class_{ci:02d}.png", dpi=150)
        plt.close(fig)

    fig, axes = plt.subplots(1, len(protos), figsize=(4.0 * len(protos), 4.0), squeeze=False)
    for j, (ax, proto, idx) in enumerate(zip(axes[0], protos, class_indices), start=1):
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"C{j} (n={len(idx)})")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    fig.suptitle(f"Prototypes [{patch_w}x{patch_h}] seed={seed}")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85)
    cbar.set_label("Normalized TEMP")
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.08, top=0.86, wspace=0.20)
    fig.savefig(out_dir / "prototypes_panel.png", dpi=160)
    plt.close(fig)


def save_member_contact_sheets_for_run(
    X: np.ndarray,
    mask: np.ndarray,
    class_indices: list[np.ndarray],
    patch_w: int,
    patch_h: int,
    seed: int,
    vmin: float,
    vmax: float,
) -> None:
    out_dir = OUT_BASE / f"class_members_w{patch_w:02d}_h{patch_h:02d}_seed{seed:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")

    for ci, idx in enumerate(class_indices, start=1):
        selected = np.sort(idx)[:MAX_CONTACT_IMAGES_PER_CLASS]
        n = len(selected)
        cols = 10
        rows = int(math.ceil(n / cols)) if n > 0 else 1

        fig, axes = plt.subplots(rows, cols, figsize=(cols * 1.8, rows * 1.8), squeeze=False)
        for ax in axes.ravel():
            ax.axis("off")

        for k, img_idx in enumerate(selected):
            ax = axes.ravel()[k]
            img = X[img_idx]
            im = ax.imshow(img, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            ax.set_title(f"z={img_idx + 1}", fontsize=7)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.axis("on")

        fig.suptitle(
            f"Class {ci:02d} members (n={len(idx)}, shown={n}) [{patch_w}x{patch_h}] seed={seed}",
            fontsize=11,
        )
        cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.65)
        cbar.set_label("Normalized TEMP")
        fig.subplots_adjust(left=0.02, right=0.98, bottom=0.03, top=0.90, wspace=0.05, hspace=0.20)
        fig.savefig(out_dir / f"class_{ci:02d}_members_panel.png", dpi=150)
        plt.close(fig)

        pd.DataFrame({"image_idx_0_based": selected, "image_z_1_based": selected + 1}).to_csv(
            out_dir / f"class_{ci:02d}_members_list.csv", index=False
        )


def run_single(
    X: np.ndarray,
    mask: np.ndarray,
    patch_w: int,
    patch_h: int,
    seed: int,
    vmin: float,
    vmax: float,
) -> RunResult:
    t0 = time.perf_counter()
    n, ny, nx = X.shape

    if not valid_patch_size(ny, nx, patch_h, patch_w):
        dt = time.perf_counter() - t0
        return RunResult(
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

    model = learn_dictionary(X, patch_h=patch_h, patch_w=patch_w, seed=seed)
    features = encode_images(X, model=model, patch_h=patch_h, patch_w=patch_w)

    clusterer = AgglomerativeClustering(n_clusters=N_CLASSES, linkage="ward")
    labels = clusterer.fit_predict(features)

    icv_per_class, class_sizes, class_indices = compute_icv_image_space(X=X, labels=labels, mask=mask)

    # Pad fixed columns up to 4 classes (N_CLASSES target).
    padded_icv = icv_per_class + [float("nan")] * max(0, N_CLASSES - len(icv_per_class))
    mean_icv = float(np.mean(icv_per_class))
    std_icv = float(np.std(icv_per_class))

    save_prototypes_for_run(
        X=X,
        mask=mask,
        class_indices=class_indices,
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
        vmin=vmin,
        vmax=vmax,
    )
    save_member_contact_sheets_for_run(
        X=X,
        mask=mask,
        class_indices=class_indices,
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
        vmin=vmin,
        vmax=vmax,
    )

    dt = time.perf_counter() - t0
    return RunResult(
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


def save_runs_csv(rows: Iterable[RunResult]) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_RUNS, index=False)
    return df


def build_summary(runs_df: pd.DataFrame) -> pd.DataFrame:
    grouped = runs_df.groupby(["patch_w", "patch_h"], as_index=False)
    summary = grouped.agg(
        executed_runs=("seed", "count"),
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
    summary["requested_runs"] = len(TARGET_SEEDS)
    summary["reduced_seed_count"] = summary["executed_runs"] < len(TARGET_SEEDS)
    summary = summary[
        [
            "patch_w",
            "patch_h",
            "requested_runs",
            "executed_runs",
            "reduced_seed_count",
            "patches_per_image",
            "total_patches",
            "patch_vector_length",
            "mean_icv_mean",
            "mean_icv_std",
            "std_icv_mean",
            "std_icv_std",
            "min_class_size_mean",
            "min_class_size_min",
            "mean_class_size_mean",
            "max_class_size_mean",
            "runtime_mean_seconds",
            "runtime_std_seconds",
        ]
    ]
    return summary.sort_values(["patch_w", "patch_h"]).reset_index(drop=True)


def label_from_row(row: pd.Series) -> str:
    return f"{int(row['patch_w'])}x{int(row['patch_h'])}"


def plot_boxplot_icv(runs_df: pd.DataFrame) -> None:
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)
    ordered = runs_df.sort_values(["patch_w", "patch_h"]).copy()
    labels = []
    data = []
    for (pw, ph), sub in ordered.groupby(["patch_w", "patch_h"]):
        labels.append(f"{int(pw)}x{int(ph)}")
        data.append(sub["mean_icv"].to_numpy())

    fig, ax = plt.subplots(figsize=(11.0, 5.0))
    ax.boxplot(data, labels=labels, showmeans=True)
    ax.set_title("Fig 6a style: ICV spread across runs by patch size")
    ax.set_xlabel("Patch size (w x h)")
    ax.set_ylabel("Mean ICV (image-space)")
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / "fig6a_icv_boxplot_patchsize.png", dpi=170)
    plt.close(fig)


def plot_summary_metric(
    summary_df: pd.DataFrame,
    y_col: str,
    yerr_col: str | None,
    out_name: str,
    title: str,
    ylabel: str,
) -> None:
    labels = [label_from_row(r) for _, r in summary_df.iterrows()]
    x = np.arange(len(summary_df))
    y = summary_df[y_col].to_numpy(dtype=float)
    yerr = summary_df[yerr_col].to_numpy(dtype=float) if yerr_col else None

    fig, ax = plt.subplots(figsize=(10.0, 4.8))
    if yerr_col:
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.6)
    else:
        ax.plot(x, y, marker="o", linewidth=1.8)
    ax.set_title(title)
    ax.set_xlabel("Patch size (w x h)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_PLOTS / out_name, dpi=170)
    plt.close(fig)


def make_md_table(df: pd.DataFrame, cols: list[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, r in df.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + rows)


def select_candidates(summary_df: pd.DataFrame) -> pd.DataFrame:
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


def write_doc(
    runs_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    ranked_df: pd.DataFrame,
    stats: dict,
    seeds_used: list[int],
) -> None:
    OUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    top_n = min(3, len(ranked_df))
    best = ranked_df.head(top_n)
    rejected = ranked_df.iloc[top_n:]

    summary_cols = [
        "patch_w",
        "patch_h",
        "executed_runs",
        "mean_icv_mean",
        "mean_icv_std",
        "std_icv_mean",
        "min_class_size_min",
        "runtime_mean_seconds",
    ]
    best_cols = [
        "patch_w",
        "patch_h",
        "balanced_score",
        "mean_icv_mean",
        "mean_icv_std",
        "std_icv_mean",
        "min_class_size_min",
        "runtime_mean_seconds",
    ]

    tested_sizes = ", ".join([f"({w},{h})" for w, h in PATCH_SIZES])
    seeds_txt = ", ".join(str(s) for s in seeds_used)

    reject_table = ""
    if not rejected.empty:
        reject_cols = [
            "patch_w",
            "patch_h",
            "mean_icv_mean",
            "mean_icv_std",
            "min_class_size_min",
            "runtime_mean_seconds",
        ]
        reject_table = make_md_table(rejected[reject_cols], reject_cols)

    md = f"""# PATCH_SIZE_SENSITIVITY_FOSSUM

## Scope
- Stage purpose: select best patch size `xpa` only.
- Dictionary size fixed: `xds = {N_DICT}`.
- Initial clustering target: `{N_CLASSES}` classes (Ward linkage).
- Patch extraction: stride = 1, all possible patches.

## Inputs
- `results/fossum/X_surface_300_norm.npy`
- `results/fossum/mask_common.npy`
- `results/fossum/global_stats.json`
- Image shape from inputs: `{runs_df.shape[0]} run rows`, source n_images=`{int(stats.get("n_images", 300))}`

## What Was Tested
- Patch sizes (w,h): {tested_sizes}
- Seeds used per patch size: {seeds_txt}
- ICV definition (Fossum image-space): for each class, pixelwise variance across images, summed over valid mask.

## Summary Table
{make_md_table(summary_df[summary_cols], summary_cols)}

## Candidate Ranking (Balanced)
{make_md_table(best[best_cols], best_cols)}

## Why Top Candidates
- Low mean ICV across runs.
- Low run-to-run ICV spread (stability).
- Better minimum class sizes (avoid degenerate tiny classes).
- Reasonable runtime.
- Visual inspection enabled by:
  - `results/fossum/patch_size_sensitivity_fossum/prototypes_wXX_hYY_seedSS/`
  - `results/fossum/patch_size_sensitivity_fossum/class_members_wXX_hYY_seedSS/`

## Rejected Patch Sizes
{reject_table if reject_table else "- none"}

## Key Outputs
- Runs: `results/fossum/patch_size_sensitivity_fossum/runs.csv`
- Summary: `results/fossum/patch_size_sensitivity_fossum/summary.csv`
- Fig 6a boxplot: `results/fossum/patch_size_sensitivity_fossum/plots/fig6a_icv_boxplot_patchsize.png`
"""
    OUT_DOC.write_text(md, encoding="utf-8")


def main() -> None:
    X, mask, stats, (vmin, vmax) = load_inputs()
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)

    runs: list[RunResult] = []
    active_seeds = TARGET_SEEDS.copy()

    # Keep requested 5 seeds by default; if manually reduced in future, enforce >= 3.
    if len(active_seeds) < MIN_SEEDS_IF_REDUCED:
        raise RuntimeError(f"Need at least {MIN_SEEDS_IF_REDUCED} seeds.")

    for patch_w, patch_h in PATCH_SIZES:
        log(f"Patch size {patch_w}x{patch_h} -> seeds={active_seeds}")
        for seed in active_seeds:
            log(f"Run start patch={patch_w}x{patch_h} seed={seed}")
            result = run_single(
                X=X,
                mask=mask,
                patch_w=patch_w,
                patch_h=patch_h,
                seed=seed,
                vmin=vmin,
                vmax=vmax,
            )
            runs.append(result)
            save_runs_csv(runs)
            log(
                f"Run done patch={patch_w}x{patch_h} seed={seed}: "
                f"mean_icv={result.mean_icv:.6f}, std_icv={result.std_icv:.6f}, "
                f"class_min={result.min_class_size}, runtime={result.runtime_seconds:.2f}s"
            )

    runs_df = save_runs_csv(runs)
    valid_runs = runs_df[runs_df["notes"] == "ok"].copy()

    summary_df = build_summary(valid_runs)
    summary_df.to_csv(OUT_SUMMARY, index=False)

    plot_boxplot_icv(valid_runs)
    plot_summary_metric(
        summary_df,
        y_col="mean_icv_mean",
        yerr_col="mean_icv_std",
        out_name="icv_mean_vs_patchsize.png",
        title="Mean ICV vs Patch Size (error bars: run std)",
        ylabel="Mean ICV (image-space)",
    )
    plot_summary_metric(
        summary_df,
        y_col="std_icv_mean",
        yerr_col="std_icv_std",
        out_name="icv_std_vs_patchsize.png",
        title="Std(ICV across classes) vs Patch Size",
        ylabel="Std ICV",
    )
    plot_summary_metric(
        summary_df,
        y_col="min_class_size_mean",
        yerr_col=None,
        out_name="min_class_size_vs_patchsize.png",
        title="Minimum Class Size vs Patch Size",
        ylabel="Min class size (mean over runs)",
    )

    ranked = select_candidates(summary_df)
    write_doc(valid_runs, summary_df, ranked_df=ranked, stats=stats, seeds_used=active_seeds)

    top_n = min(3, len(ranked))
    log("Top patch-size candidates (balanced):")
    for i, row in ranked.head(top_n).iterrows():
        log(
            f"  #{i+1} {int(row['patch_w'])}x{int(row['patch_h'])} "
            f"score={row['balanced_score']:.4f} "
            f"mean_icv={row['mean_icv_mean']:.6f} "
            f"icv_spread={row['mean_icv_std']:.6f} "
            f"min_class={int(row['min_class_size_min'])} "
            f"runtime={row['runtime_mean_seconds']:.2f}s"
        )

    log(f"Wrote runs: {OUT_RUNS}")
    log(f"Wrote summary: {OUT_SUMMARY}")
    log(f"Wrote plots: {OUT_PLOTS}")
    log(f"Wrote doc: {OUT_DOC}")


if __name__ == "__main__":
    main()
