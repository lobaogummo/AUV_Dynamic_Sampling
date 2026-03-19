"""Shared utilities for the Fossum faithful-initial pipeline.

This module is intentionally separated from the historical baseline scripts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from sklearn.decomposition import MiniBatchDictionaryLearning

ROOT = Path(__file__).resolve().parents[1]

IN_X_NORM = ROOT / "results" / "fossum" / "X_surface_300_norm.npy"
IN_X_SST = ROOT / "results" / "fossum" / "X_surface_300.npy"
IN_MASK = ROOT / "results" / "fossum" / "mask_common.npy"
IN_STATS = ROOT / "results" / "fossum" / "global_stats.json"
IN_PNG_DIR = ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis"


@dataclass(frozen=True)
class FaithfulInitialConfig:
    n_classes: int = 4
    dict_alpha: float = 1.0
    dict_batch_size: int = 4096
    transform_algo: str = "omp"
    transform_nnz: int = 2
    include_valid_mask: bool = True
    mask_encoding: str = "concat"
    feature_mode: str = "raw"


@dataclass(frozen=True)
class OrderedBatchMeta:
    image_idx: int
    patch_start: int
    patch_end: int


def ensure_inputs(require_png_dir: bool = False) -> None:
    paths = [IN_X_SST, IN_X_NORM, IN_MASK, IN_STATS]
    if require_png_dir:
        paths.append(IN_PNG_DIR)
    missing = [p for p in paths if not p.exists()]
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
        raise RuntimeError(f"No PNGs found in {IN_PNG_DIR}")
    out: Dict[int, Path] = {}
    rx = re.compile(r"_z(\d+)\.png$", re.IGNORECASE)
    for p in files:
        m = rx.search(p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def parse_patch_sizes(values: Sequence[str] | None, defaults: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not values:
        return [(int(w), int(h)) for w, h in defaults]
    out: List[Tuple[int, int]] = []
    rx = re.compile(r"^\s*(\d+)\s*[xX]\s*(\d+)\s*$")
    for token in values:
        m = rx.match(token)
        if not m:
            raise ValueError(f"Invalid patch size token '{token}'. Use WxH.")
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def parse_positive_int_values(values: Sequence[int] | None, defaults: Sequence[int], label: str) -> List[int]:
    if not values:
        values = list(defaults)
    uniq: List[int] = []
    seen = set()
    for v in values:
        vi = int(v)
        if vi <= 0:
            raise ValueError(f"Invalid {label} value '{v}'. Must be > 0.")
        if vi not in seen:
            uniq.append(vi)
            seen.add(vi)
    return uniq


def patch_count(ny: int, nx: int, patch_h: int, patch_w: int) -> int:
    return int((ny - patch_h + 1) * (nx - patch_w + 1))


def valid_patch_size(ny: int, nx: int, patch_h: int, patch_w: int) -> bool:
    return patch_h > 0 and patch_w > 0 and patch_h <= ny and patch_w <= nx


def extract_patch_components(
    image_2d: np.ndarray,
    patch_h: int,
    patch_w: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return flattened patch temperature and patch-validity components.

    Patch order is deterministic and follows sliding-window traversal:
    top-to-bottom rows and, within each row, left-to-right columns.
    """

    temp_filled = np.nan_to_num(image_2d, nan=0.0).astype(np.float32, copy=False)
    valid_mask = np.isfinite(image_2d).astype(np.float32, copy=False)

    temp_windows = sliding_window_view(temp_filled, (patch_h, patch_w)).reshape(-1, patch_h * patch_w)
    mask_windows = sliding_window_view(valid_mask, (patch_h, patch_w)).reshape(-1, patch_h * patch_w)
    return temp_windows, mask_windows


def build_patch_vectors(
    image_2d: np.ndarray,
    patch_h: int,
    patch_w: int,
    include_valid_mask: bool = True,
    mask_encoding: str = "concat",
) -> np.ndarray:
    patch_temp_filled, patch_valid_mask = extract_patch_components(image_2d=image_2d, patch_h=patch_h, patch_w=patch_w)
    if not include_valid_mask:
        return patch_temp_filled
    if mask_encoding != "concat":
        raise ValueError(f"Unsupported mask encoding '{mask_encoding}'. Only 'concat' is supported.")
    return np.concatenate([patch_temp_filled, patch_valid_mask], axis=1).astype(np.float32, copy=False)


def build_image_feature_from_full_sparse_codes(codes: np.ndarray, feature_mode: str = "raw") -> np.ndarray:
    """Convert full patch-by-patch sparse codes into one image feature vector.

    Input shape:
      - codes: (n_patches_per_image, dictionary_size)
    Output shape:
      - feature: (n_patches_per_image * dictionary_size,)
    """

    if codes.ndim != 2:
        raise ValueError(f"Expected 2D codes array, got {codes.shape}")

    if feature_mode == "raw":
        selected = codes
    elif feature_mode == "abs":
        selected = np.abs(codes)
    else:
        raise ValueError(f"Unsupported feature_mode '{feature_mode}'. Use 'raw' or 'abs'.")

    return selected.astype(np.float32, copy=False).reshape(-1)


def iterate_ordered_patch_batches(
    X: np.ndarray,
    patch_h: int,
    patch_w: int,
    batch_size: int,
    include_valid_mask: bool = True,
    mask_encoding: str = "concat",
) -> Iterator[Tuple[OrderedBatchMeta, np.ndarray]]:
    for image_idx in range(X.shape[0]):
        patch_vectors = build_patch_vectors(
            image_2d=X[image_idx],
            patch_h=patch_h,
            patch_w=patch_w,
            include_valid_mask=include_valid_mask,
            mask_encoding=mask_encoding,
        )
        for start in range(0, patch_vectors.shape[0], batch_size):
            stop = min(start + batch_size, patch_vectors.shape[0])
            yield OrderedBatchMeta(image_idx=image_idx, patch_start=start, patch_end=stop), patch_vectors[start:stop]


def train_dictionary_ordered_stream(
    X: np.ndarray,
    patch_h: int,
    patch_w: int,
    seed: int,
    dictionary_size: int,
    cfg: FaithfulInitialConfig,
) -> MiniBatchDictionaryLearning:
    model = MiniBatchDictionaryLearning(
        n_components=dictionary_size,
        alpha=cfg.dict_alpha,
        batch_size=cfg.dict_batch_size,
        random_state=seed,
        shuffle=False,
        transform_algorithm=cfg.transform_algo,
        transform_n_nonzero_coefs=min(cfg.transform_nnz, dictionary_size),
    )

    for _meta, batch in iterate_ordered_patch_batches(
        X=X,
        patch_h=patch_h,
        patch_w=patch_w,
        batch_size=cfg.dict_batch_size,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
    ):
        model.partial_fit(batch)
    return model


def encode_images_with_full_sparse_features(
    X: np.ndarray,
    model: MiniBatchDictionaryLearning,
    patch_h: int,
    patch_w: int,
    dictionary_size: int,
    cfg: FaithfulInitialConfig,
) -> Tuple[np.ndarray, int, int, int]:
    first_patches = build_patch_vectors(
        image_2d=X[0],
        patch_h=patch_h,
        patch_w=patch_w,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
    )
    patches_per_image = int(first_patches.shape[0])
    patch_vector_length = int(first_patches.shape[1])
    feature_vector_length = int(patches_per_image * dictionary_size)

    n_images = X.shape[0]
    features = np.empty((n_images, feature_vector_length), dtype=np.float32)

    for img_idx in range(n_images):
        patch_vectors = build_patch_vectors(
            image_2d=X[img_idx],
            patch_h=patch_h,
            patch_w=patch_w,
            include_valid_mask=cfg.include_valid_mask,
            mask_encoding=cfg.mask_encoding,
        )
        if patch_vectors.shape[0] != patches_per_image:
            raise RuntimeError(
                "Inconsistent number of patches per image: "
                f"image0={patches_per_image} vs image{img_idx}={patch_vectors.shape[0]}"
            )

        codes = model.transform(patch_vectors).astype(np.float32, copy=False)
        features[img_idx, :] = build_image_feature_from_full_sparse_codes(codes=codes, feature_mode=cfg.feature_mode)

    return features, patches_per_image, patch_vector_length, feature_vector_length


def compute_icv_sst_space(
    X_sst: np.ndarray,
    labels: np.ndarray,
    mask: np.ndarray,
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


def make_md_table(df, cols: List[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for _, row in df.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, sep] + body)
