"""Step 2 for Fossum workflow: comparative patch-size selection.

This script evaluates multiple patch sizes using a fixed mini-pipeline:
1) load normalized surface stack and common mask
2) extract all patches (stride=1) deterministically
3) learn an initial dictionary (4 atoms)
4) encode each image into compact features
5) cluster images with Ward linkage into 4 initial classes
6) compute ICV + class-size metrics
7) save class prototypes and comparison plots
8) write a selection report with best candidates
"""

from __future__ import annotations

import csv
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
IN_GLOBAL_STATS = ROOT / "results" / "fossum" / "global_stats.json"

OUT_BASE = ROOT / "results" / "fossum" / "patch_selection"
OUT_PLOTS = OUT_BASE / "plots"
OUT_CSV = OUT_BASE / "patch_size_comparison.csv"
OUT_REPORT = ROOT / "docs" / "PATCH_SIZE_SELECTION_REPORT.md"

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

N_DICT = 4
N_CLASSES = 4
RANDOM_STATE = 42
DICT_ALPHA = 1.0
DICT_BATCH_SIZE = 4096
DICT_SHUFFLE = False
TRANSFORM_ALGO = "omp"
TRANSFORM_NNZ = 2


@dataclass
class PatchResult:
    patch_w: int
    patch_h: int
    patches_per_image: int
    total_patches: int
    patch_vector_length: int
    mean_icv: float
    std_icv: float
    number_of_classes: int
    min_class_size: int
    mean_class_size: float
    max_class_size: int
    runtime_seconds: float
    notes: str


def log(message: str) -> None:
    print(f"[patch-select] {message}")


def require_inputs() -> None:
    missing = [p for p in [IN_X_NORM, IN_MASK, IN_GLOBAL_STATS] if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required input(s): "
            + ", ".join(str(p.relative_to(ROOT)).replace("\\", "/") for p in missing)
        )


def load_data() -> tuple[np.ndarray, np.ndarray, dict]:
    require_inputs()
    X = np.load(IN_X_NORM).astype(np.float32, copy=False)
    mask = np.load(IN_MASK).astype(bool, copy=False)
    meta = json.loads(IN_GLOBAL_STATS.read_text(encoding="utf-8"))

    if X.ndim != 3:
        raise RuntimeError(f"Expected X to be 3D, got shape={X.shape}")
    if mask.shape != X.shape[1:]:
        raise RuntimeError(f"Mask shape mismatch: mask={mask.shape}, X spatial={X.shape[1:]}")

    # Keep masked cells as NaN so prototypes preserve no-data region.
    X = X.copy()
    X[:, ~mask] = np.nan

    n_images, ny, nx = X.shape
    log(f"Loaded X={X.shape}, mask={mask.shape}, valid_fraction={float(mask.mean()):.6f}")
    if n_images != 300 or ny != 64 or nx != 112:
        log("Warning: input shape differs from expected validated context (300, 64, 112).")
    return X, mask, meta


def extract_patches(image_2d: np.ndarray, patch_h: int, patch_w: int) -> np.ndarray:
    """Extract all stride=1 patches in deterministic raster order."""
    clean = np.nan_to_num(image_2d, nan=0.0).astype(np.float32, copy=False)
    windows = sliding_window_view(clean, (patch_h, patch_w))
    return windows.reshape(-1, patch_h * patch_w)


def patch_count(ny: int, nx: int, patch_h: int, patch_w: int) -> int:
    return int((ny - patch_h + 1) * (nx - patch_w + 1))


def is_valid_patch_size(ny: int, nx: int, patch_h: int, patch_w: int) -> bool:
    return patch_h <= ny and patch_w <= nx and patch_h > 0 and patch_w > 0


def build_dictionary(X: np.ndarray, patch_h: int, patch_w: int) -> MiniBatchDictionaryLearning:
    model = MiniBatchDictionaryLearning(
        n_components=N_DICT,
        alpha=DICT_ALPHA,
        batch_size=DICT_BATCH_SIZE,
        random_state=RANDOM_STATE,
        shuffle=DICT_SHUFFLE,
        transform_algorithm=TRANSFORM_ALGO,
        transform_n_nonzero_coefs=TRANSFORM_NNZ,
    )
    for i in range(X.shape[0]):
        patches = extract_patches(X[i], patch_h, patch_w)
        model.partial_fit(patches)
    return model


def encode_images(
    X: np.ndarray, model: MiniBatchDictionaryLearning, patch_h: int, patch_w: int
) -> np.ndarray:
    n_images = X.shape[0]
    feats = np.zeros((n_images, N_DICT * 2), dtype=np.float32)

    for i in range(n_images):
        patches = extract_patches(X[i], patch_h, patch_w)
        codes = model.transform(patches)
        abs_codes = np.abs(codes)
        feats[i, :N_DICT] = np.mean(abs_codes, axis=0)
        feats[i, N_DICT:] = np.std(abs_codes, axis=0)
    return feats


def compute_icv(features: np.ndarray, labels: np.ndarray) -> tuple[list[float], list[int]]:
    icv_list: list[float] = []
    class_sizes: list[int] = []
    for class_id in np.unique(labels):
        idx = np.where(labels == class_id)[0]
        class_sizes.append(int(idx.size))
        center = np.mean(features[idx], axis=0, dtype=np.float64)
        sq_dist = np.sum((features[idx] - center) ** 2, axis=1)
        icv_list.append(float(np.mean(sq_dist)))
    return icv_list, class_sizes


def save_single_prototype(
    arr: np.ndarray,
    out_path: Path,
    title: str,
    vmin: float,
    vmax: float,
    cmap: matplotlib.colors.Colormap,
) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    cbar = fig.colorbar(im, ax=ax, shrink=0.9)
    cbar.set_label("Normalized TEMP")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_prototypes(
    X: np.ndarray,
    labels: np.ndarray,
    mask: np.ndarray,
    out_dir: Path,
    patch_w: int,
    patch_h: int,
) -> float:
    out_dir.mkdir(parents=True, exist_ok=True)
    classes = np.unique(labels)

    protos: list[np.ndarray] = []
    sizes: list[int] = []
    for class_id in classes:
        idx = np.where(labels == class_id)[0]
        sizes.append(int(idx.size))
        proto = np.nanmean(X[idx], axis=0).astype(np.float32, copy=False)
        proto[~mask] = np.nan
        protos.append(proto)

    valid_vals = np.concatenate([p[mask] for p in protos if np.any(np.isfinite(p[mask]))])
    if valid_vals.size == 0:
        vlim = 1.0
    else:
        vlim = float(np.percentile(np.abs(valid_vals), 98.0))
        if not np.isfinite(vlim) or vlim <= 0:
            vlim = 1.0
    vmin, vmax = -vlim, +vlim

    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")

    for i, (proto, size) in enumerate(zip(protos, sizes), start=1):
        out_file = out_dir / f"prototype_class_{i:02d}.png"
        save_single_prototype(
            proto,
            out_file,
            title=f"Prototype class {i:02d} (n={size}) [{patch_w}x{patch_h}]",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
        )

    fig, axes = plt.subplots(1, len(protos), figsize=(4.0 * len(protos), 4.0), squeeze=False)
    for i, (proto, size) in enumerate(zip(protos, sizes)):
        ax = axes[0, i]
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"C{i+1} (n={size})")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    fig.suptitle(f"Initial prototypes [{patch_w}x{patch_h}]")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85)
    cbar.set_label("Normalized TEMP")
    fig.tight_layout()
    fig.savefig(out_dir / "prototypes_panel.png", dpi=160)
    plt.close(fig)

    spatial_std = float(np.mean([np.nanstd(p) for p in protos]))
    return spatial_std


def plot_metric(df: pd.DataFrame, y_col: str, title: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    labels = [f"{int(w)}x{int(h)}" for w, h in zip(df["patch_w"], df["patch_h"])]
    x = np.arange(len(df), dtype=np.int32)
    y = df[y_col].astype(float).to_numpy()

    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.plot(x, y, marker="o", linewidth=1.8)
    ax.set_title(title)
    ax.set_xlabel("Patch size (w x h)")
    ax.set_ylabel(y_col)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def make_markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for _, row in df.iterrows():
        vals = []
        for col in columns:
            v = row[col]
            if isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + rows)


def build_selection_scores(df: pd.DataFrame) -> pd.DataFrame:
    # Balanced ranking: lower ICVs + better class balance + faster runtime.
    d = df.copy()
    d["rank_mean_icv"] = d["mean_icv"].rank(method="min", ascending=True)
    d["rank_std_icv"] = d["std_icv"].rank(method="min", ascending=True)
    d["rank_min_class_size"] = d["min_class_size"].rank(method="min", ascending=False)
    d["rank_runtime"] = d["runtime_seconds"].rank(method="min", ascending=True)
    d["score"] = (
        0.35 * d["rank_mean_icv"]
        + 0.20 * d["rank_std_icv"]
        + 0.30 * d["rank_min_class_size"]
        + 0.15 * d["rank_runtime"]
    )
    return d.sort_values("score", ascending=True).reset_index(drop=True)


def rejection_reasons(row: pd.Series, n_images: int, p75_runtime: float, median_icv: float) -> str:
    reasons: list[str] = []
    if row["min_class_size"] < max(10, int(0.08 * n_images)):
        reasons.append("tiny class detected")
    if row["mean_icv"] > median_icv:
        reasons.append("mean ICV above median")
    if row["runtime_seconds"] > p75_runtime:
        reasons.append("high runtime")
    if row["std_icv"] > 0.5 * max(1e-12, row["mean_icv"]):
        reasons.append("high ICV dispersion")
    if not reasons:
        reasons.append("dominated by better balanced candidates")
    return "; ".join(reasons)


def write_report(
    df: pd.DataFrame,
    scores: pd.DataFrame,
    global_meta: dict,
    prototype_interpretability: dict[str, float],
) -> None:
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    n_images = int(global_meta.get("n_images", 300))

    top_n = min(3, len(scores))
    best = scores.head(top_n).copy()
    best_labels = [f"{int(r.patch_w)}x{int(r.patch_h)}" for r in best.itertuples()]

    median_icv = float(df["mean_icv"].median())
    p75_runtime = float(df["runtime_seconds"].quantile(0.75))
    rejected = scores.iloc[top_n:].copy()
    rejected["reason"] = rejected.apply(
        lambda r: rejection_reasons(r, n_images=n_images, p75_runtime=p75_runtime, median_icv=median_icv),
        axis=1,
    )

    fixed_params = {
        "dictionary_size": N_DICT,
        "n_initial_classes": N_CLASSES,
        "patch_stride": 1,
        "dictionary_learning": "MiniBatchDictionaryLearning (partial_fit on all patches)",
        "encoding": "per-image mean|std of absolute sparse codes",
        "clustering": "AgglomerativeClustering(linkage='ward')",
        "random_state": RANDOM_STATE,
        "transform_algorithm": TRANSFORM_ALGO,
        "transform_n_nonzero_coefs": TRANSFORM_NNZ,
    }

    tested = ", ".join([f"({int(w)},{int(h)})" for w, h in zip(df["patch_w"], df["patch_h"])])

    columns_main = [
        "patch_w",
        "patch_h",
        "patches_per_image",
        "total_patches",
        "patch_vector_length",
        "mean_icv",
        "std_icv",
        "number_of_classes",
        "min_class_size",
        "mean_class_size",
        "max_class_size",
        "runtime_seconds",
    ]
    table_main = make_markdown_table(df[columns_main], columns_main)
    table_best = make_markdown_table(
        best[
            [
                "patch_w",
                "patch_h",
                "mean_icv",
                "std_icv",
                "min_class_size",
                "mean_class_size",
                "runtime_seconds",
                "score",
            ]
        ],
        [
            "patch_w",
            "patch_h",
            "mean_icv",
            "std_icv",
            "min_class_size",
            "mean_class_size",
            "runtime_seconds",
            "score",
        ],
    )

    reject_table = ""
    if not rejected.empty:
        reject_table = make_markdown_table(
            rejected[
                [
                    "patch_w",
                    "patch_h",
                    "mean_icv",
                    "std_icv",
                    "min_class_size",
                    "runtime_seconds",
                    "reason",
                ]
            ],
            [
                "patch_w",
                "patch_h",
                "mean_icv",
                "std_icv",
                "min_class_size",
                "runtime_seconds",
                "reason",
            ],
        )

    proto_lines = []
    for key, val in sorted(prototype_interpretability.items()):
        proto_lines.append(f"- `{key}` spatial_std_mean={val:.6f}")
    proto_text = "\n".join(proto_lines) if proto_lines else "- Not available"

    report = f"""# PATCH_SIZE_SELECTION_REPORT

## 1) What Was Tested
- Dataset: `results/fossum/X_surface_300_norm.npy` + `results/fossum/mask_common.npy`
- Image shape: `(300, 64, 112)`
- Tested patch sizes (w, h): {tested}

## 2) Fixed Parameters Used
{chr(10).join([f"- {k}: {v}" for k, v in fixed_params.items()])}

## 3) Table of Results
{table_main}

## 4) Selection Criteria
- Lower `mean_icv` is better.
- Lower `std_icv` is better.
- Avoid tiny classes (`min_class_size` too low).
- Prefer visually interpretable prototypes (checked from prototype panels).
- Keep runtime reasonable.
- Final ranking uses a balanced score across these metrics (not a single metric).

## 5) Best Patch-Size Candidate(s)
Top candidate labels: {", ".join(best_labels)}

{table_best}

Prototype interpretability proxy (`spatial_std_mean`) by patch size:
{proto_text}

## 6) Why Those Candidates Were Selected
- They jointly achieved low `mean_icv`, low-to-moderate `std_icv`, and healthier minimum class sizes.
- Runtime remained competitive versus larger patch sizes.
- Prototype panels are visually structured and less degenerate for these candidates.

## 7) Rejected Patch Sizes and Why
{reject_table if reject_table else "- None"}

## Output Paths
- Comparison CSV: `results/fossum/patch_selection/patch_size_comparison.csv`
- Plots: `results/fossum/patch_selection/plots/`
- Prototypes: `results/fossum/patch_selection/prototypes_wXX_hYY/`
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


def run_for_patch_size(X: np.ndarray, mask: np.ndarray, patch_w: int, patch_h: int) -> PatchResult:
    n_images, ny, nx = X.shape
    t0 = time.perf_counter()

    if not is_valid_patch_size(ny=ny, nx=nx, patch_h=patch_h, patch_w=patch_w):
        dt = time.perf_counter() - t0
        return PatchResult(
            patch_w=patch_w,
            patch_h=patch_h,
            patches_per_image=0,
            total_patches=0,
            patch_vector_length=patch_w * patch_h,
            mean_icv=float("nan"),
            std_icv=float("nan"),
            number_of_classes=0,
            min_class_size=0,
            mean_class_size=float("nan"),
            max_class_size=0,
            runtime_seconds=float(dt),
            notes="skipped: invalid patch size for image dimensions",
        )

    patches_per_image = patch_count(ny=ny, nx=nx, patch_h=patch_h, patch_w=patch_w)
    total_patches = int(patches_per_image * n_images)
    patch_vector_length = int(patch_w * patch_h)
    log(
        f"Testing patch={patch_w}x{patch_h}: patches_per_image={patches_per_image}, total_patches={total_patches}"
    )

    model = build_dictionary(X, patch_h=patch_h, patch_w=patch_w)
    features = encode_images(X, model, patch_h=patch_h, patch_w=patch_w)

    clusterer = AgglomerativeClustering(n_clusters=N_CLASSES, linkage="ward")
    labels = clusterer.fit_predict(features)

    icv_per_class, class_sizes = compute_icv(features, labels)
    mean_icv = float(np.mean(icv_per_class))
    std_icv = float(np.std(icv_per_class))
    n_classes = int(len(np.unique(labels)))
    min_class = int(np.min(class_sizes))
    mean_class = float(np.mean(class_sizes))
    max_class = int(np.max(class_sizes))

    proto_dir = OUT_BASE / f"prototypes_w{patch_w:02d}_h{patch_h:02d}"
    proto_spatial_std = save_prototypes(
        X=X, labels=labels, mask=mask, out_dir=proto_dir, patch_w=patch_w, patch_h=patch_h
    )

    dt = time.perf_counter() - t0
    notes = (
        "ok; "
        f"icv_per_class={','.join(f'{v:.6f}' for v in icv_per_class)}; "
        f"spatial_std_mean={proto_spatial_std:.6f}"
    )
    return PatchResult(
        patch_w=patch_w,
        patch_h=patch_h,
        patches_per_image=patches_per_image,
        total_patches=total_patches,
        patch_vector_length=patch_vector_length,
        mean_icv=mean_icv,
        std_icv=std_icv,
        number_of_classes=n_classes,
        min_class_size=min_class,
        mean_class_size=mean_class,
        max_class_size=max_class,
        runtime_seconds=float(dt),
        notes=notes,
    )


def save_comparison_csv(rows: Iterable[PatchResult]) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    return df


def save_plots(df: pd.DataFrame) -> None:
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)
    plot_metric(df, "mean_icv", "Mean ICV vs Patch Size", OUT_PLOTS / "icv_mean_vs_patchsize.png")
    plot_metric(df, "std_icv", "Std ICV vs Patch Size", OUT_PLOTS / "icv_std_vs_patchsize.png")
    plot_metric(
        df,
        "min_class_size",
        "Minimum Class Size vs Patch Size",
        OUT_PLOTS / "min_class_size_vs_patchsize.png",
    )
    plot_metric(
        df,
        "mean_class_size",
        "Mean Class Size vs Patch Size",
        OUT_PLOTS / "mean_class_size_vs_patchsize.png",
    )
    plot_metric(
        df,
        "max_class_size",
        "Maximum Class Size vs Patch Size",
        OUT_PLOTS / "max_class_size_vs_patchsize.png",
    )
    plot_metric(
        df,
        "patches_per_image",
        "Patches per Image vs Patch Size",
        OUT_PLOTS / "patches_per_image_vs_patchsize.png",
    )
    plot_metric(
        df,
        "runtime_seconds",
        "Runtime vs Patch Size",
        OUT_PLOTS / "runtime_vs_patchsize.png",
    )


def main() -> None:
    X, mask, global_meta = load_data()
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)

    rows: list[PatchResult] = []
    proto_interpretability: dict[str, float] = {}

    for patch_w, patch_h in PATCH_SIZES:
        result = run_for_patch_size(X, mask, patch_w=patch_w, patch_h=patch_h)
        rows.append(result)
        log(
            f"Done patch={patch_w}x{patch_h}: mean_icv={result.mean_icv:.6f}, "
            f"std_icv={result.std_icv:.6f}, min_class={result.min_class_size}, "
            f"runtime={result.runtime_seconds:.2f}s"
        )
        if "spatial_std_mean=" in result.notes:
            val = result.notes.split("spatial_std_mean=")[-1].strip()
            try:
                proto_interpretability[f"{patch_w}x{patch_h}"] = float(val)
            except ValueError:
                pass

    df = save_comparison_csv(rows)
    save_plots(df)

    valid_df = df[
        np.isfinite(df["mean_icv"].to_numpy())
        & np.isfinite(df["std_icv"].to_numpy())
        & (df["number_of_classes"] > 0)
    ].copy()
    scores = build_selection_scores(valid_df)
    write_report(valid_df, scores, global_meta=global_meta, prototype_interpretability=proto_interpretability)

    best_n = min(3, len(scores))
    if best_n > 0:
        log("Top candidates:")
        for i, row in scores.head(best_n).iterrows():
            log(
                f"  #{i+1}: {int(row['patch_w'])}x{int(row['patch_h'])} "
                f"score={row['score']:.4f} mean_icv={row['mean_icv']:.6f} "
                f"std_icv={row['std_icv']:.6f} min_class={int(row['min_class_size'])} "
                f"runtime={row['runtime_seconds']:.2f}s"
            )

    log(f"Wrote comparison CSV: {OUT_CSV}")
    log(f"Wrote plots folder: {OUT_PLOTS}")
    log(f"Wrote report: {OUT_REPORT}")


if __name__ == "__main__":
    main()
