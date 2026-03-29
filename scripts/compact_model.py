"""Loader and validation helpers for SST compact model artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


REQUIRED_NPZ_FIELDS = [
    "class_ids",
    "class_names",
    "class_sizes",
    "global_labels",
    "prototype_mean_norm",
    "prototype_std_norm",
    "prototype_mean_orig",
    "prototype_std_orig",
    "mask_common",
    "lat_grid",
    "lon_grid",
    "mu_global",
    "sigma_global",
    "member_indices_by_class",
    "member_indices_lengths",
]


@dataclass(frozen=True)
class CompactModelBundle:
    npz_path: Path
    manifest_path: Path | None
    manifest: Dict[str, Any] | None
    class_ids: np.ndarray
    class_names: np.ndarray
    class_sizes: np.ndarray
    global_labels: np.ndarray
    member_indices_by_class: List[np.ndarray]
    prototype_mean_norm: np.ndarray
    prototype_std_norm: np.ndarray
    prototype_mean_orig: np.ndarray
    prototype_std_orig: np.ndarray
    mask_common: np.ndarray
    lat_grid: np.ndarray
    lon_grid: np.ndarray
    mu_global: float
    sigma_global: float


def _as_path(path_like: str | Path) -> Path:
    return Path(path_like).expanduser().resolve()


def _require_shape(name: str, arr: np.ndarray, expected_shape: tuple[int, ...]) -> None:
    if arr.shape != expected_shape:
        raise ValueError(f"Invalid shape for '{name}': expected {expected_shape}, got {arr.shape}")


def _load_manifest_if_available(manifest_path: Path | None) -> Dict[str, Any] | None:
    if manifest_path is None:
        return None
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_compact_model(
    npz_path: str | Path,
    manifest_path: str | Path | None = None,
) -> CompactModelBundle:
    """Load compact model NPZ + optional manifest and validate consistency."""

    model_npz_path = _as_path(npz_path)
    if not model_npz_path.exists():
        raise FileNotFoundError(f"Compact model NPZ not found: {model_npz_path}")

    resolved_manifest_path: Path | None
    if manifest_path is None:
        default_manifest = model_npz_path.with_name("compact_model_manifest.json")
        resolved_manifest_path = default_manifest if default_manifest.exists() else None
    else:
        resolved_manifest_path = _as_path(manifest_path)

    with np.load(model_npz_path, allow_pickle=False) as data:
        missing = [k for k in REQUIRED_NPZ_FIELDS if k not in data.files]
        if missing:
            raise ValueError(f"Compact model NPZ missing required fields: {missing}")

        class_ids = np.asarray(data["class_ids"], dtype=np.int32).reshape(-1)
        class_names = np.asarray(data["class_names"]).astype(str).reshape(-1)
        class_sizes = np.asarray(data["class_sizes"], dtype=np.int32).reshape(-1)
        global_labels = np.asarray(data["global_labels"], dtype=np.int32).reshape(-1)

        prototype_mean_norm = np.asarray(data["prototype_mean_norm"], dtype=np.float32)
        prototype_std_norm = np.asarray(data["prototype_std_norm"], dtype=np.float32)
        prototype_mean_orig = np.asarray(data["prototype_mean_orig"], dtype=np.float32)
        prototype_std_orig = np.asarray(data["prototype_std_orig"], dtype=np.float32)

        mask_common = np.asarray(data["mask_common"]).astype(bool, copy=False)
        lat_grid = np.asarray(data["lat_grid"], dtype=np.float32)
        lon_grid = np.asarray(data["lon_grid"], dtype=np.float32)

        member_matrix = np.asarray(data["member_indices_by_class"], dtype=np.int32)
        member_lengths = np.asarray(data["member_indices_lengths"], dtype=np.int32).reshape(-1)

        mu_raw = np.asarray(data["mu_global"], dtype=np.float64).reshape(-1)
        sigma_raw = np.asarray(data["sigma_global"], dtype=np.float64).reshape(-1)
        if mu_raw.size != 1 or sigma_raw.size != 1:
            raise ValueError("Expected scalar mu_global and sigma_global in compact model NPZ.")
        mu_global = float(mu_raw[0])
        sigma_global = float(sigma_raw[0])

    k = int(class_ids.size)
    if k <= 0:
        raise ValueError("Compact model must contain at least one class.")
    if class_names.size != k or class_sizes.size != k:
        raise ValueError(
            "class_ids, class_names and class_sizes must share the same length. "
            f"Got class_ids={class_ids.size}, class_names={class_names.size}, class_sizes={class_sizes.size}."
        )
    if np.unique(class_ids).size != k:
        raise ValueError(f"class_ids must be unique. Got: {class_ids.tolist()}")

    if np.any(class_sizes <= 0):
        raise ValueError(f"class_sizes must be positive. Got: {class_sizes.tolist()}")

    if mask_common.ndim != 2:
        raise ValueError(f"mask_common must be 2D. Got shape {mask_common.shape}")
    h, w = int(mask_common.shape[0]), int(mask_common.shape[1])

    _require_shape("prototype_mean_norm", prototype_mean_norm, (k, h, w))
    _require_shape("prototype_std_norm", prototype_std_norm, (k, h, w))
    _require_shape("prototype_mean_orig", prototype_mean_orig, (k, h, w))
    _require_shape("prototype_std_orig", prototype_std_orig, (k, h, w))
    _require_shape("lat_grid", lat_grid, (h, w))
    _require_shape("lon_grid", lon_grid, (h, w))

    if member_matrix.ndim != 2:
        raise ValueError(f"member_indices_by_class must be 2D. Got shape {member_matrix.shape}")
    if member_matrix.shape[0] != k:
        raise ValueError(
            "member_indices_by_class first dimension must match class count. "
            f"Got {member_matrix.shape[0]} vs {k}."
        )
    if member_lengths.shape != (k,):
        raise ValueError(
            "member_indices_lengths must have shape (K,). "
            f"Got {member_lengths.shape} for K={k}."
        )

    if not np.isfinite(mu_global) or not np.isfinite(sigma_global) or sigma_global <= 0.0:
        raise ValueError(f"Invalid normalization metadata: mu_global={mu_global}, sigma_global={sigma_global}")

    n = int(global_labels.size)
    allowed_labels = set(int(v) for v in class_ids.tolist())
    unique_labels = set(int(v) for v in np.unique(global_labels).tolist())
    if not unique_labels.issubset(allowed_labels):
        raise ValueError(
            "global_labels contains unknown class ids. "
            f"Known={sorted(allowed_labels)}, seen={sorted(unique_labels)}"
        )

    member_indices_by_class: List[np.ndarray] = []
    assigned = np.full((n,), -1, dtype=np.int32)
    max_width = int(member_matrix.shape[1])

    for i, class_id in enumerate(class_ids.tolist()):
        n_i = int(member_lengths[i])
        if n_i < 0 or n_i > max_width:
            raise ValueError(
                f"Invalid member length for class slot {i}: {n_i} not in [0, {max_width}]"
            )
        idx = member_matrix[i, :n_i].astype(np.int32, copy=False)
        if idx.size != int(class_sizes[i]):
            raise ValueError(
                f"class_sizes mismatch for class_id={class_id}: class_sizes={int(class_sizes[i])}, "
                f"member_indices_count={idx.size}"
            )
        if idx.size == 0:
            raise ValueError(f"Class {class_id} has no members, but class_sizes indicates positive size.")
        if np.any(idx < 0) or np.any(idx >= n):
            raise ValueError(f"Out-of-range member index detected for class {class_id}.")
        if np.unique(idx).size != idx.size:
            raise ValueError(f"Duplicate member indices detected inside class {class_id}.")
        if np.any(global_labels[idx] != int(class_id)):
            raise ValueError(f"global_labels are inconsistent with member indices for class {class_id}.")
        if np.any(assigned[idx] != -1):
            raise ValueError(f"Overlapping member indices detected across classes at class {class_id}.")
        assigned[idx] = int(class_id)
        member_indices_by_class.append(idx.copy())

    if np.any(assigned == -1):
        missing = int(np.sum(assigned == -1))
        raise ValueError(f"member_indices_by_class does not cover all observations. Missing {missing} indices.")

    for class_id, class_size in zip(class_ids.tolist(), class_sizes.tolist()):
        observed = int(np.sum(global_labels == int(class_id)))
        if observed != int(class_size):
            raise ValueError(
                f"class_sizes mismatch against global_labels for class {class_id}: "
                f"class_sizes={class_size}, observed={observed}"
            )

    valid_mask = mask_common
    if np.any(valid_mask):
        if not np.isfinite(prototype_std_norm[:, valid_mask]).all():
            raise ValueError("prototype_std_norm has non-finite values over valid mask pixels.")
        if not np.isfinite(prototype_std_orig[:, valid_mask]).all():
            raise ValueError("prototype_std_orig has non-finite values over valid mask pixels.")

    if not np.isfinite(lat_grid).all() or not np.isfinite(lon_grid).all():
        raise ValueError("lat_grid/lon_grid must be finite everywhere.")

    manifest = _load_manifest_if_available(resolved_manifest_path)
    if manifest is not None:
        if "global_n_classes" in manifest and int(manifest["global_n_classes"]) != k:
            raise ValueError(
                f"Manifest global_n_classes={manifest['global_n_classes']} does not match NPZ class count {k}."
            )
        if "class_sizes" in manifest:
            m_sizes = np.asarray(manifest["class_sizes"], dtype=np.int32).reshape(-1)
            if m_sizes.shape != class_sizes.shape or not np.array_equal(m_sizes, class_sizes):
                raise ValueError("Manifest class_sizes does not match NPZ class_sizes.")
        if "global_classes" in manifest:
            m_names = np.asarray(manifest["global_classes"]).astype(str).reshape(-1)
            if m_names.shape != class_names.shape:
                raise ValueError("Manifest global_classes length does not match NPZ class_names.")

    return CompactModelBundle(
        npz_path=model_npz_path,
        manifest_path=resolved_manifest_path,
        manifest=manifest,
        class_ids=class_ids,
        class_names=class_names,
        class_sizes=class_sizes,
        global_labels=global_labels,
        member_indices_by_class=member_indices_by_class,
        prototype_mean_norm=prototype_mean_norm,
        prototype_std_norm=prototype_std_norm,
        prototype_mean_orig=prototype_mean_orig,
        prototype_std_orig=prototype_std_orig,
        mask_common=mask_common,
        lat_grid=lat_grid,
        lon_grid=lon_grid,
        mu_global=mu_global,
        sigma_global=sigma_global,
    )


__all__ = ["CompactModelBundle", "load_compact_model", "REQUIRED_NPZ_FIELDS"]

