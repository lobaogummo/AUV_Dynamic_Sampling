"""Debug-fixed Fossum patch-size sensitivity for finalist patch sizes only.

Purpose:
- keep Fossum-faithful setup (xds=4, Ward clustering, image-space ICV)
- ensure seed changes are meaningful by making patch presentation order
  explicitly seed-dependent (image order + patch order)
- rerun only finalists: (32,20), (48,32), (64,36)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageDraw, ImageFont

try:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.decomposition import MiniBatchDictionaryLearning

    SKLEARN_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - runtime guard
    AgglomerativeClustering = None  # type: ignore
    MiniBatchDictionaryLearning = None  # type: ignore
    SKLEARN_IMPORT_ERROR = exc


ROOT = Path(__file__).resolve().parents[1]
IN_X_NORM = ROOT / "results" / "fossum" / "X_surface_300_norm.npy"
IN_MASK = ROOT / "results" / "fossum" / "mask_common.npy"

OUT_BASE = ROOT / "results" / "fossum" / "patch_size_sensitivity_fossum_debugfixed"
OUT_RUNS = OUT_BASE / "runs_finalists.csv"
OUT_SUMMARY = OUT_BASE / "summary_finalists.csv"
OUT_PLOTS = OUT_BASE / "plots"

PATCH_SIZES = [(32, 20), (48, 32), (64, 36)]
SEEDS = [11, 23, 37, 53, 71]

N_DICT = 4
N_CLASSES = 4
DICT_ALPHA = 1.0
DICT_BATCH_SIZE = 4096
TRANSFORM_ALGO = "omp"
TRANSFORM_NNZ = 2

SEED_COLORS = {
    11: (31, 119, 180),
    23: (255, 127, 14),
    37: (44, 160, 44),
    53: (214, 39, 40),
    71: (148, 103, 189),
}


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
    mean_icv: float
    std_icv: float
    min_class_size: int
    mean_class_size: float
    max_class_size: int
    runtime_seconds: float
    notes: str


def log(msg: str) -> None:
    print(f"[patch-sens-debugfixed] {msg}")


def ensure_deps() -> None:
    if SKLEARN_IMPORT_ERROR is not None:
        raise RuntimeError(
            "scikit-learn is required for debugfixed rerun, but it is not available "
            f"in this environment: {SKLEARN_IMPORT_ERROR}"
        )


def load_inputs() -> Tuple[np.ndarray, np.ndarray]:
    missing = [p for p in [IN_X_NORM, IN_MASK] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing inputs: " + ", ".join(str(p) for p in missing))
    X = np.load(IN_X_NORM).astype(np.float32, copy=False)
    mask = np.load(IN_MASK).astype(bool, copy=False)
    if X.ndim != 3 or mask.shape != X.shape[1:]:
        raise RuntimeError(f"Bad shapes: X={X.shape}, mask={mask.shape}")
    X = X.copy()
    X[:, ~mask] = np.nan
    return X, mask


def extract_patches(image_2d: np.ndarray, patch_h: int, patch_w: int) -> np.ndarray:
    clean = np.nan_to_num(image_2d, nan=0.0).astype(np.float32, copy=False)
    windows = sliding_window_view(clean, (patch_h, patch_w))
    return windows.reshape(-1, patch_h * patch_w)


def patch_count(ny: int, nx: int, patch_h: int, patch_w: int) -> int:
    return int((ny - patch_h + 1) * (nx - patch_w + 1))


def learn_dictionary_seeded_order(X: np.ndarray, patch_h: int, patch_w: int, seed: int):
    rng = np.random.default_rng(seed)
    model = MiniBatchDictionaryLearning(
        n_components=N_DICT,
        alpha=DICT_ALPHA,
        batch_size=DICT_BATCH_SIZE,
        random_state=seed,
        shuffle=True,
        transform_algorithm=TRANSFORM_ALGO,
        transform_n_nonzero_coefs=TRANSFORM_NNZ,
    )

    image_order = rng.permutation(X.shape[0])
    for img_idx in image_order:
        patches = extract_patches(X[img_idx], patch_h, patch_w)
        patch_order = rng.permutation(patches.shape[0])
        model.partial_fit(patches[patch_order])
    return model


def encode_images(X: np.ndarray, model, patch_h: int, patch_w: int) -> np.ndarray:
    n = X.shape[0]
    feats = np.zeros((n, N_DICT * 2), dtype=np.float32)
    for i in range(n):
        patches = extract_patches(X[i], patch_h, patch_w)
        codes = model.transform(patches)
        abs_codes = np.abs(codes)
        feats[i, :N_DICT] = np.mean(abs_codes, axis=0)
        feats[i, N_DICT:] = np.std(abs_codes, axis=0)
    return feats


def compute_icv_image_space(X: np.ndarray, labels: np.ndarray, mask: np.ndarray) -> Tuple[List[float], List[int]]:
    icv_per_class: List[float] = []
    class_sizes: List[int] = []
    for class_id in sorted(np.unique(labels)):
        idx = np.where(labels == class_id)[0]
        class_sizes.append(int(idx.size))
        class_pixels = X[idx][:, mask]
        pixel_var = np.var(class_pixels, axis=0, ddof=0)
        icv_per_class.append(float(np.sum(pixel_var)))
    return icv_per_class, class_sizes


def run_single(X: np.ndarray, mask: np.ndarray, patch_w: int, patch_h: int, seed: int) -> RunResult:
    t0 = time.perf_counter()
    n, ny, nx = X.shape
    if not (patch_h <= ny and patch_w <= nx):
        dt = time.perf_counter() - t0
        return RunResult(
            patch_w,
            patch_h,
            seed,
            0,
            0,
            patch_w * patch_h,
            0,
            "[]",
            float("nan"),
            float("nan"),
            0,
            float("nan"),
            0,
            dt,
            "skipped invalid patch size",
        )

    model = learn_dictionary_seeded_order(X, patch_h=patch_h, patch_w=patch_w, seed=seed)
    features = encode_images(X, model=model, patch_h=patch_h, patch_w=patch_w)
    labels = AgglomerativeClustering(n_clusters=N_CLASSES, linkage="ward").fit_predict(features)
    icv_per_class, class_sizes = compute_icv_image_space(X=X, labels=labels, mask=mask)

    dt = time.perf_counter() - t0
    return RunResult(
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
        patches_per_image=patch_count(ny, nx, patch_h, patch_w),
        total_patches=patch_count(ny, nx, patch_h, patch_w) * n,
        patch_vector_length=patch_w * patch_h,
        number_of_classes=len(class_sizes),
        class_sizes=json.dumps(class_sizes),
        mean_icv=float(np.mean(icv_per_class)),
        std_icv=float(np.std(icv_per_class)),
        min_class_size=int(np.min(class_sizes)),
        mean_class_size=float(np.mean(class_sizes)),
        max_class_size=int(np.max(class_sizes)),
        runtime_seconds=float(dt),
        notes="ok",
    )


def build_summary(runs_ok: pd.DataFrame) -> pd.DataFrame:
    g = runs_ok.groupby(["patch_w", "patch_h"], as_index=False)
    return g.agg(
        executed_runs=("seed", "count"),
        mean_icv_mean=("mean_icv", "mean"),
        mean_icv_std=("mean_icv", "std"),
        std_icv_mean=("std_icv", "mean"),
        std_icv_std=("std_icv", "std"),
        min_class_size_mean=("min_class_size", "mean"),
        min_class_size_min=("min_class_size", "min"),
        max_class_size_mean=("max_class_size", "mean"),
        runtime_mean_seconds=("runtime_seconds", "mean"),
        runtime_std_seconds=("runtime_seconds", "std"),
    )


def _make_canvas(title: str, width: int = 1450, height: int = 860):
    left, right, top, bottom = 110, 80, 85, 115
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    tw = draw.textlength(title, font=font)
    draw.text(((width - tw) / 2, 26), title, fill=(0, 0, 0), font=font)
    return img, draw, font, left, top, width - right, height - bottom


def _y_to_px(y: float, y_min: float, y_max: float, y0: int, y1: int) -> int:
    frac = (y - y_min) / (y_max - y_min + 1e-12)
    return int(round(y1 - frac * (y1 - y0)))


def _safe_range(y: np.ndarray, pad: float = 0.05) -> Tuple[float, float]:
    mn, mx = float(np.min(y)), float(np.max(y))
    if mn == mx:
        eps = 1.0 if mn == 0 else abs(mn) * 0.1
        return mn - eps, mx + eps
    d = (mx - mn) * pad
    return mn - d, mx + d


def _draw_axes(draw, font, x0, y0, x1, y1, labels: List[str], y_min: float, y_max: float, y_label: str):
    draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=1)
    for i in range(6):
        frac = i / 5.0
        yv = y_min + frac * (y_max - y_min)
        yy = _y_to_px(yv, y_min, y_max, y0, y1)
        draw.line([(x0 - 6, yy), (x0, yy)], fill=(0, 0, 0), width=1)
        txt = f"{yv:.3f}"
        tw = draw.textlength(txt, font=font)
        draw.text((x0 - 10 - tw, yy - 6), txt, fill=(0, 0, 0), font=font)
        draw.line([(x0, yy), (x1, yy)], fill=(230, 230, 230), width=1)
    xs = []
    n = len(labels)
    for i, lbl in enumerate(labels):
        xx = int(round(x0 + (i + 0.5) * (x1 - x0) / n))
        xs.append(xx)
        draw.line([(xx, y1), (xx, y1 + 6)], fill=(0, 0, 0), width=1)
        tw = draw.textlength(lbl, font=font)
        draw.text((xx - tw / 2, y1 + 12), lbl, fill=(0, 0, 0), font=font)
    draw.text((12, y0 + (y1 - y0) / 2), y_label, fill=(0, 0, 0), font=font)
    return xs


def make_debug_plots(runs_ok: pd.DataFrame, table: pd.DataFrame) -> None:
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)
    labels = table["patch_label"].tolist()

    # Seed points
    img, draw, font, x0, y0, x1, y1 = _make_canvas("Debugfixed: ICV seed points by patch size")
    all_y = runs_ok["mean_icv"].to_numpy(dtype=float)
    y_min, y_max = _safe_range(all_y, pad=0.03)
    xs = _draw_axes(draw, font, x0, y0, x1, y1, labels, y_min, y_max, "Mean ICV")
    grouped = runs_ok.groupby(["patch_w", "patch_h"], as_index=False)
    for i, (_, sub) in enumerate(grouped):
        xc = xs[i]
        arr = sub.sort_values("seed")[["seed", "mean_icv"]].to_records(index=False)
        for j, (seed, val) in enumerate(arr):
            yy = _y_to_px(float(val), y_min, y_max, y0, y1)
            jitter = int((j - (len(arr) - 1) / 2) * 7)
            color = SEED_COLORS.get(int(seed), (0, 0, 0))
            draw.ellipse([xc + jitter - 4, yy - 4, xc + jitter + 4, yy + 4], fill=color, outline=color)
    img.save(OUT_PLOTS / "icv_seed_points_by_patchsize.png", format="PNG")

    # Absolute spread
    for col, name, ylab in [
        ("absolute_spread", "icv_absolute_spread_vs_patchsize.png", "Absolute spread"),
        ("relative_spread_pct", "icv_relative_spread_vs_patchsize.png", "Relative spread (%)"),
    ]:
        img, draw, font, x0, y0, x1, y1 = _make_canvas(f"Debugfixed: {ylab} by patch size")
        y = table[col].to_numpy(dtype=float)
        y_min, y_max = _safe_range(y, pad=0.08)
        xs = _draw_axes(draw, font, x0, y0, x1, y1, labels, y_min, y_max, ylab)
        pts = []
        for i, yi in enumerate(y):
            xx = xs[i]
            yy = _y_to_px(float(yi), y_min, y_max, y0, y1)
            pts.append((xx, yy))
            draw.ellipse([xx - 4, yy - 4, xx + 4, yy + 4], fill=(31, 119, 180), outline=(31, 119, 180))
        if len(pts) >= 2:
            draw.line(pts, fill=(31, 119, 180), width=2)
        img.save(OUT_PLOTS / name, format="PNG")

    # Zoomed centered box
    img, draw, font, x0, y0, x1, y1 = _make_canvas("Debugfixed fig6a zoom: centered mean ICV by patch size")
    centered = []
    for _, sub in grouped:
        vals = sub.sort_values("seed")["mean_icv"].to_numpy(dtype=float)
        centered.append(vals - float(np.mean(vals)))
    all_centered = np.concatenate(centered)
    q95 = float(np.percentile(np.abs(all_centered), 95.0))
    lim = max(2.0, q95 * 1.25)
    y_min, y_max = -lim, lim
    xs = _draw_axes(draw, font, x0, y0, x1, y1, labels, y_min, y_max, "mean_icv - patch_mean_icv")
    for i, vals in enumerate(centered):
        xc = xs[i]
        q1, q2, q3 = np.percentile(vals, [25, 50, 75])
        vmin, vmax = float(np.min(vals)), float(np.max(vals))
        yq1 = _y_to_px(float(np.clip(q1, y_min, y_max)), y_min, y_max, y0, y1)
        yq2 = _y_to_px(float(np.clip(q2, y_min, y_max)), y_min, y_max, y0, y1)
        yq3 = _y_to_px(float(np.clip(q3, y_min, y_max)), y_min, y_max, y0, y1)
        yvmin = _y_to_px(float(np.clip(vmin, y_min, y_max)), y_min, y_max, y0, y1)
        yvmax = _y_to_px(float(np.clip(vmax, y_min, y_max)), y_min, y_max, y0, y1)
        box_w = 24
        draw.rectangle([xc - box_w, yq3, xc + box_w, yq1], outline=(0, 0, 0), width=2, fill=(224, 236, 255))
        draw.line([(xc - box_w, yq2), (xc + box_w, yq2)], fill=(0, 0, 0), width=2)
        draw.line([(xc, yvmax), (xc, yq3)], fill=(0, 0, 0), width=1)
        draw.line([(xc, yq1), (xc, yvmin)], fill=(0, 0, 0), width=1)
        for j, v in enumerate(vals):
            yy = _y_to_px(float(np.clip(v, y_min, y_max)), y_min, y_max, y0, y1)
            jitter = int((j - (len(vals) - 1) / 2) * 6)
            draw.ellipse([xc + jitter - 3, yy - 3, xc + jitter + 3, yy + 3], fill=(214, 39, 40), outline=(214, 39, 40))
    img.save(OUT_PLOTS / "fig6a_icv_boxplot_patchsize_zoom.png", format="PNG")


def build_variance_table(runs_ok: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, sub in runs_ok.groupby(["patch_w", "patch_h"], as_index=False):
        pw = int(sub["patch_w"].iloc[0])
        ph = int(sub["patch_h"].iloc[0])
        vals = sub.sort_values("seed")["mean_icv"].to_numpy(dtype=float)
        mn = float(np.min(vals))
        mx = float(np.max(vals))
        mean_val = float(np.mean(vals))
        spread = float(mx - mn)
        rel = float(spread / mean_val) if mean_val != 0 else np.nan
        rows.append(
            {
                "patch_w": pw,
                "patch_h": ph,
                "patch_label": f"{pw}x{ph}",
                "mean_icv_min": mn,
                "mean_icv_max": mx,
                "absolute_spread": spread,
                "relative_spread": rel,
                "relative_spread_pct": rel * 100 if np.isfinite(rel) else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["patch_w", "patch_h"]).reset_index(drop=True)


def main() -> None:
    ensure_deps()
    X, mask = load_inputs()
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)

    runs: List[RunResult] = []
    for patch_w, patch_h in PATCH_SIZES:
        log(f"Patch size {patch_w}x{patch_h}")
        for seed in SEEDS:
            log(f"  Run seed={seed}")
            res = run_single(X=X, mask=mask, patch_w=patch_w, patch_h=patch_h, seed=seed)
            runs.append(res)
            pd.DataFrame([r.__dict__ for r in runs]).to_csv(OUT_RUNS, index=False)
            log(f"  done seed={seed}: mean_icv={res.mean_icv:.6f}, std_icv={res.std_icv:.6f}, runtime={res.runtime_seconds:.1f}s")

    runs_df = pd.DataFrame([r.__dict__ for r in runs])
    runs_df.to_csv(OUT_RUNS, index=False)
    runs_ok = runs_df[runs_df["notes"] == "ok"].copy()
    summary = build_summary(runs_ok)
    summary.to_csv(OUT_SUMMARY, index=False)

    variance_table = build_variance_table(runs_ok)
    make_debug_plots(runs_ok, variance_table)

    log(f"Wrote {OUT_RUNS}")
    log(f"Wrote {OUT_SUMMARY}")
    log(f"Wrote plots in {OUT_PLOTS}")


if __name__ == "__main__":
    main()
