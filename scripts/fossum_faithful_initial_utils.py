"""Shared utilities for the Fossum faithful-initial pipeline.

This module is intentionally separated from the historical baseline scripts.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from sklearn.decomposition import MiniBatchDictionaryLearning, sparse_encode

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


class SparseCodingModel:
    """Lightweight fixed-dictionary sparse coding model with sklearn-compatible transform."""

    def __init__(
        self,
        components: np.ndarray,
        transform_algorithm: str = "omp",
        transform_n_nonzero_coefs: int | None = 2,
        alpha: float = 1.0,
    ) -> None:
        comps = np.asarray(components, dtype=np.float32)
        if comps.ndim != 2:
            raise ValueError(f"Dictionary components must be 2D, got {comps.shape}.")
        self.components_ = comps
        self.transform_algorithm = str(transform_algorithm)
        self.transform_n_nonzero_coefs = None if transform_n_nonzero_coefs is None else int(transform_n_nonzero_coefs)
        self.alpha = float(alpha)

    def transform(self, X: np.ndarray) -> np.ndarray:
        kwargs = {
            "X": np.asarray(X, dtype=np.float32),
            "dictionary": self.components_,
            "algorithm": self.transform_algorithm,
        }
        if self.transform_algorithm == "omp":
            kwargs["n_nonzero_coefs"] = (
                None if self.transform_n_nonzero_coefs is None else min(int(self.transform_n_nonzero_coefs), self.components_.shape[0])
            )
        else:
            kwargs["alpha"] = self.alpha
        return sparse_encode(**kwargs)


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


def seeded_deterministic_image_order(n_images: int, seed: int) -> np.ndarray:
    """Build a deterministic image order permutation from seed without randomness."""
    if n_images <= 0:
        return np.zeros((0,), dtype=np.int32)
    if n_images == 1:
        return np.array([0], dtype=np.int32)

    start = int(abs(seed)) % n_images
    step = (2 * (int(abs(seed)) % max(1, n_images - 1))) + 1
    step = step % n_images
    if step == 0:
        step = 1
    while math.gcd(step, n_images) != 1:
        step = (step + 2) % n_images
        if step == 0:
            step = 1

    order = (start + step * np.arange(n_images, dtype=np.int64)) % n_images
    return order.astype(np.int32, copy=False)


def image_icv_proxy(X_sst: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Per-image variance proxy in SST/original space over common valid mask."""
    class_pixels = X_sst[:, mask]
    return np.var(class_pixels, axis=1, ddof=0).astype(np.float64, copy=False)


def deterministic_spread_order(indices: np.ndarray, proxy_values: np.ndarray) -> np.ndarray:
    """Order indices by alternating low/high proxy values to maximize visual spread."""
    if indices.size <= 1:
        return indices.astype(np.int32, copy=False)

    idx = np.asarray(indices, dtype=np.int64)
    sorted_pos = np.argsort(proxy_values[idx], kind="stable")
    sorted_idx = idx[sorted_pos]

    out = np.empty(sorted_idx.size, dtype=np.int64)
    left = 0
    right = sorted_idx.size - 1
    k = 0
    while left <= right:
        out[k] = sorted_idx[left]
        k += 1
        left += 1
        if left <= right:
            out[k] = sorted_idx[right]
            k += 1
            right -= 1
    return out.astype(np.int32, copy=False)


def iterate_ordered_patch_batches(
    X: np.ndarray,
    patch_h: int,
    patch_w: int,
    batch_size: int,
    include_valid_mask: bool = True,
    mask_encoding: str = "concat",
    image_order: np.ndarray | None = None,
) -> Iterator[Tuple[OrderedBatchMeta, np.ndarray]]:
    if image_order is None:
        image_order = np.arange(X.shape[0], dtype=np.int32)
    else:
        image_order = np.asarray(image_order, dtype=np.int32)
        if image_order.shape != (X.shape[0],):
            raise ValueError(f"image_order must have shape ({X.shape[0]},), got {image_order.shape}")
        if np.unique(image_order).size != X.shape[0]:
            raise ValueError("image_order must be a permutation without duplicates.")
        if int(np.min(image_order)) < 0 or int(np.max(image_order)) >= X.shape[0]:
            raise ValueError("image_order contains out-of-range indices.")

    for image_idx in image_order:
        image_idx_int = int(image_idx)
        patch_vectors = build_patch_vectors(
            image_2d=X[image_idx_int],
            patch_h=patch_h,
            patch_w=patch_w,
            include_valid_mask=include_valid_mask,
            mask_encoding=mask_encoding,
        )
        for start in range(0, patch_vectors.shape[0], batch_size):
            stop = min(start + batch_size, patch_vectors.shape[0])
            yield OrderedBatchMeta(image_idx=image_idx_int, patch_start=start, patch_end=stop), patch_vectors[start:stop]


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

    image_order = seeded_deterministic_image_order(n_images=X.shape[0], seed=seed)
    for _meta, batch in iterate_ordered_patch_batches(
        X=X,
        patch_h=patch_h,
        patch_w=patch_w,
        batch_size=cfg.dict_batch_size,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
        image_order=image_order,
    ):
        model.partial_fit(batch)
    return model


def save_dictionary_artifact(
    out_path: Path,
    components: np.ndarray,
    metadata: dict,
) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    comps = np.asarray(components, dtype=np.float32)
    if comps.ndim != 2:
        raise ValueError(f"Dictionary components must be 2D, got {comps.shape}.")
    payload_meta = dict(metadata)
    payload_meta["components_shape"] = [int(v) for v in comps.shape]
    np.savez_compressed(
        out_path,
        components=comps,
        metadata_json=np.array(json.dumps(payload_meta, sort_keys=True)),
    )


def load_dictionary_artifact(dictionary_path: Path) -> Tuple[np.ndarray, dict]:
    dictionary_path = Path(dictionary_path)
    if not dictionary_path.exists():
        raise FileNotFoundError(f"Missing dictionary artifact: {dictionary_path}")
    with np.load(dictionary_path, allow_pickle=False) as data:
        if "components" not in data:
            raise RuntimeError(f"Dictionary artifact missing 'components': {dictionary_path}")
        components = np.asarray(data["components"], dtype=np.float32)
        raw_meta = data["metadata_json"] if "metadata_json" in data else np.array("{}")
    meta_text = str(raw_meta.item()) if np.asarray(raw_meta).shape == () else str(raw_meta)
    metadata = json.loads(meta_text) if meta_text else {}
    if components.ndim != 2:
        raise RuntimeError(f"Invalid dictionary component shape in {dictionary_path}: {components.shape}")
    return components, metadata


def load_fixed_dictionary_model(
    dictionary_path: Path,
    cfg: FaithfulInitialConfig,
    expected_dictionary_size: int | None = None,
) -> Tuple[SparseCodingModel, dict]:
    components, metadata = load_dictionary_artifact(dictionary_path)
    n_components = int(components.shape[0])
    if expected_dictionary_size is not None and n_components != int(expected_dictionary_size):
        raise RuntimeError(
            f"Dictionary size mismatch in {dictionary_path}: artifact={n_components}, expected={expected_dictionary_size}"
        )
    model = SparseCodingModel(
        components=components,
        transform_algorithm=cfg.transform_algo,
        transform_n_nonzero_coefs=min(cfg.transform_nnz, n_components),
        alpha=cfg.dict_alpha,
    )
    return model, metadata


def encode_images_with_full_sparse_features(
    X: np.ndarray,
    model: MiniBatchDictionaryLearning | SparseCodingModel,
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
