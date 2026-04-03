"""Utilities for strong pixel-wise prototype characterization (seed11 thesis stage)."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from scipy import ndimage as ndi

try:
    from skimage.filters import threshold_otsu

    HAS_SKIMAGE = True
except Exception:
    threshold_otsu = None
    HAS_SKIMAGE = False


LOCAL_DISTANCE_RX = re.compile(r"^subclass_(\d+)_distance_to_prototype\.csv$")
LOCAL_KEY_FALLBACK_RX = re.compile(r"^(k\d+)::subclass_(\d+)$")
VALID_REGIME_LABELS = {"homogeneous", "single_gradient", "multi_regime"}


@dataclass(frozen=True)
class PrototypePayload:
    scope: str
    key: str
    prototype_name: str
    temp_mean: np.ndarray
    temp_std: np.ndarray
    mask: np.ndarray
    lat_grid: np.ndarray
    lon_grid: np.ndarray
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CharacterizationOutput:
    pixel_df: pd.DataFrame
    region_df: pd.DataFrame
    maps: dict[str, np.ndarray]
    threshold: float
    threshold_method: str
    regime_label: str
    segmentation_mode: str


@dataclass(frozen=True)
class ImageOnlyLabelBundle:
    run_dir: Path
    global_csv: Path
    local_csv: Path
    global_by_name: dict[str, str]
    local_by_key: dict[str, str]
    local_by_name_unique: dict[str, str]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def load_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    p = path.expanduser().resolve()
    if not p.exists():
        return {}
    return load_json(p)


def resolve_repo_or_abs(project_root: Path, value: str | Path | None) -> Path | None:
    if value is None:
        return None
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = project_root / p
    return p.resolve()


def first_existing_file(candidates: Sequence[Path]) -> Path | None:
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def discover_dataset_arrays(project_root: Path) -> dict[str, Path]:
    paths = {
        "X_norm": first_existing_file(
            [
                project_root / "results" / "fossum" / "X_surface_300_norm.npy",
                project_root / "results" / "plots" / "X_surface_300_norm.npy",
            ]
        ),
        "mask_common": first_existing_file(
            [
                project_root / "results" / "fossum" / "mask_common.npy",
                project_root / "results" / "plots" / "mask_common.npy",
            ]
        ),
    }
    missing = [k for k, v in paths.items() if v is None]
    if missing:
        raise FileNotFoundError(
            "Missing dataset arrays for local prototype reconstruction: "
            + ", ".join(missing)
        )
    return {k: v for k, v in paths.items() if v is not None}


def normalize_regime_label(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "homogeneous": "homogeneous",
        "homogeneo": "homogeneous",
        "single_gradient": "single_gradient",
        "gradiente_unico": "single_gradient",
        "multi_regime": "multi_regime",
        "multiregime": "multi_regime",
        "multi_regimes": "multi_regime",
    }
    normalized = aliases.get(text, text)
    if normalized not in VALID_REGIME_LABELS:
        raise ValueError(
            f"Unknown regime label '{value}'. "
            f"Expected one of {sorted(VALID_REGIME_LABELS)}."
        )
    return normalized


def _expected_image_only_csv_names(seed_id: int) -> tuple[str, str]:
    return (
        f"cv_features_global_seed{int(seed_id)}_image_only.csv",
        f"cv_features_local_class02_seed{int(seed_id)}_image_only.csv",
    )


def _resolve_image_only_csv_pair(
    *,
    cv_downstream_root: Path,
    seed_id: int,
    explicit_run_dir: Path | None,
    explicit_global_csv: Path | None,
    explicit_local_csv: Path | None,
) -> tuple[Path, Path, Path]:
    global_name, local_name = _expected_image_only_csv_names(seed_id)
    if explicit_global_csv is not None or explicit_local_csv is not None:
        if explicit_global_csv is None or explicit_local_csv is None:
            raise ValueError("If one explicit image-only CSV path is provided, both must be provided.")
        g = explicit_global_csv.expanduser().resolve()
        l = explicit_local_csv.expanduser().resolve()
        run_dir = g.parent
        if not g.exists() or not l.exists():
            raise FileNotFoundError(f"Explicit image-only CSVs not found: {g} | {l}")
        return run_dir, g, l

    if explicit_run_dir is not None:
        run_dir = explicit_run_dir.expanduser().resolve()
        g = run_dir / global_name
        l = run_dir / local_name
        if not g.exists() or not l.exists():
            raise FileNotFoundError(f"Image-only CSVs not found in explicit run dir: {run_dir}")
        return run_dir, g.resolve(), l.resolve()

    base = cv_downstream_root.expanduser().resolve()
    preferred = base / "official_image_only_default"
    preferred_global = preferred / global_name
    preferred_local = preferred / local_name
    if preferred_global.exists() and preferred_local.exists():
        return preferred.resolve(), preferred_global.resolve(), preferred_local.resolve()

    candidates: list[tuple[float, Path, Path, Path]] = []
    if base.exists() and base.is_dir():
        for run_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            g = run_dir / global_name
            l = run_dir / local_name
            if g.exists() and l.exists():
                mtime = max(g.stat().st_mtime, l.stat().st_mtime)
                candidates.append((mtime, run_dir.resolve(), g.resolve(), l.resolve()))
    if not candidates:
        raise FileNotFoundError(
            f"Could not locate image-only CSVs for seed={seed_id} under {base}. "
            f"Expected files: {global_name}, {local_name}"
        )
    candidates.sort(key=lambda t: t[0], reverse=True)
    _, run_dir, g, l = candidates[0]
    return run_dir, g, l


def load_image_only_label_bundle(
    *,
    cv_downstream_root: Path,
    seed_id: int,
    explicit_run_dir: Path | None = None,
    explicit_global_csv: Path | None = None,
    explicit_local_csv: Path | None = None,
) -> ImageOnlyLabelBundle:
    run_dir, global_csv, local_csv = _resolve_image_only_csv_pair(
        cv_downstream_root=cv_downstream_root,
        seed_id=seed_id,
        explicit_run_dir=explicit_run_dir,
        explicit_global_csv=explicit_global_csv,
        explicit_local_csv=explicit_local_csv,
    )

    global_df = pd.read_csv(global_csv)
    local_df = pd.read_csv(local_csv)
    for required_col in ["prototype_name", "regime_label"]:
        if required_col not in global_df.columns:
            raise ValueError(f"Missing column '{required_col}' in {global_csv}")
        if required_col not in local_df.columns:
            raise ValueError(f"Missing column '{required_col}' in {local_csv}")

    global_df = global_df.copy()
    local_df = local_df.copy()
    global_df["regime_label"] = global_df["regime_label"].apply(normalize_regime_label)
    local_df["regime_label"] = local_df["regime_label"].apply(normalize_regime_label)

    global_by_name: dict[str, str] = {}
    for _, row in global_df.iterrows():
        name = str(row["prototype_name"]).strip()
        label = str(row["regime_label"]).strip()
        if name in global_by_name and global_by_name[name] != label:
            raise ValueError(f"Conflicting global image-only labels for {name}: {global_by_name[name]} vs {label}")
        global_by_name[name] = label

    local_by_key: dict[str, str] = {}
    if "key" in local_df.columns:
        for _, row in local_df.iterrows():
            key = str(row["key"]).strip()
            label = str(row["regime_label"]).strip()
            if not key:
                continue
            if key in local_by_key and local_by_key[key] != label:
                raise ValueError(f"Conflicting local image-only labels for {key}: {local_by_key[key]} vs {label}")
            local_by_key[key] = label

    name_group = local_df.groupby("prototype_name")["regime_label"].nunique(dropna=False)
    unique_names = set(name_group[name_group == 1].index.astype(str).tolist())
    local_by_name_unique = {
        str(name): str(local_df.loc[local_df["prototype_name"] == name, "regime_label"].iloc[0])
        for name in unique_names
    }

    return ImageOnlyLabelBundle(
        run_dir=run_dir,
        global_csv=global_csv,
        local_csv=local_csv,
        global_by_name=global_by_name,
        local_by_key=local_by_key,
        local_by_name_unique=local_by_name_unique,
    )


def _resolve_local_image_only_key(payload: PrototypePayload) -> str | None:
    local_k = payload.metadata.get("local_k")
    subclass_id = payload.metadata.get("subclass_id")
    if isinstance(local_k, (int, np.integer)) and isinstance(subclass_id, (int, np.integer)):
        return f"k{int(local_k)}::subclass_prototype_{int(subclass_id):02d}"
    m = LOCAL_KEY_FALLBACK_RX.match(payload.key)
    if m:
        return f"{m.group(1)}::subclass_prototype_{int(m.group(2)):02d}"
    return None


def assign_image_only_labels(
    payloads: Sequence[PrototypePayload],
    label_bundle: ImageOnlyLabelBundle,
) -> list[PrototypePayload]:
    enriched: list[PrototypePayload] = []
    missing: list[str] = []
    for payload in payloads:
        label: str | None = None
        label_source = ""
        if payload.scope == "global":
            label = label_bundle.global_by_name.get(payload.prototype_name)
            label_source = payload.prototype_name
        elif payload.scope == "local_class02":
            local_key = _resolve_local_image_only_key(payload)
            if local_key is not None:
                label = label_bundle.local_by_key.get(local_key)
                label_source = local_key
            if label is None:
                label = label_bundle.local_by_name_unique.get(payload.prototype_name)
                label_source = payload.prototype_name
        else:
            label = None
        if label is None:
            missing.append(f"{payload.scope}/{payload.key} ({payload.prototype_name})")
            continue

        metadata = dict(payload.metadata)
        metadata["image_only_regime_label"] = str(label)
        metadata["image_only_label_source_key"] = str(label_source)
        metadata["image_only_run_dir"] = str(label_bundle.run_dir)
        enriched.append(
            PrototypePayload(
                scope=payload.scope,
                key=payload.key,
                prototype_name=payload.prototype_name,
                temp_mean=payload.temp_mean,
                temp_std=payload.temp_std,
                mask=payload.mask,
                lat_grid=payload.lat_grid,
                lon_grid=payload.lon_grid,
                metadata=metadata,
            )
        )
    if missing:
        raise RuntimeError(
            "Missing image-only regime labels for prototypes: "
            + "; ".join(missing)
        )
    return enriched


def load_compact_model_global_payloads(compact_model_npz: Path) -> tuple[list[PrototypePayload], np.ndarray, np.ndarray, np.ndarray]:
    with np.load(compact_model_npz, allow_pickle=False) as data:
        class_ids = np.asarray(data["class_ids"], dtype=np.int32).reshape(-1)
        mean_maps = np.asarray(data["prototype_mean_norm"], dtype=np.float32)
        std_maps = np.asarray(data["prototype_std_norm"], dtype=np.float32)
        mask_common = np.asarray(data["mask_common"]).astype(bool, copy=False)
        lat_grid = np.asarray(data["lat_grid"], dtype=np.float32)
        lon_grid = np.asarray(data["lon_grid"], dtype=np.float32)

    if mean_maps.ndim != 3 or std_maps.ndim != 3:
        raise ValueError(
            f"compact_model prototype arrays must be 3D. "
            f"Got mean={mean_maps.shape}, std={std_maps.shape}"
        )
    if mean_maps.shape != std_maps.shape:
        raise ValueError(
            f"compact_model mean/std shape mismatch: {mean_maps.shape} vs {std_maps.shape}"
        )
    if mask_common.shape != mean_maps.shape[1:]:
        raise ValueError(
            f"mask_common shape mismatch: mask={mask_common.shape} vs prototype={mean_maps.shape[1:]}"
        )
    if lat_grid.shape != mean_maps.shape[1:] or lon_grid.shape != mean_maps.shape[1:]:
        raise ValueError(
            f"lat/lon shape mismatch with prototype grid: lat={lat_grid.shape}, lon={lon_grid.shape}, "
            f"prototype={mean_maps.shape[1:]}"
        )

    payloads: list[PrototypePayload] = []
    for i, class_id in enumerate(class_ids.tolist()):
        prototype_name = f"prototype_class_{int(class_id):02d}"
        key = f"class_{int(class_id):02d}"
        temp_mean = mean_maps[i].astype(np.float32, copy=True)
        temp_std = std_maps[i].astype(np.float32, copy=True)
        temp_mean[~mask_common] = np.nan
        temp_std[~mask_common] = np.nan
        payloads.append(
            PrototypePayload(
                scope="global",
                key=key,
                prototype_name=prototype_name,
                temp_mean=temp_mean,
                temp_std=temp_std,
                mask=mask_common.astype(bool, copy=True),
                lat_grid=lat_grid.astype(np.float32, copy=False),
                lon_grid=lon_grid.astype(np.float32, copy=False),
                metadata={"class_id": int(class_id), "source": "compact_model"},
            )
        )
    return payloads, lat_grid, lon_grid, mask_common


def _read_member_indices(distance_csv: Path) -> np.ndarray:
    df = pd.read_csv(distance_csv)
    for col in ["global_image_idx_0_based", "image_idx_0_based"]:
        if col in df.columns:
            idx = df[col].astype(int).to_numpy()
            return np.sort(np.unique(idx.astype(np.int32, copy=False)))
    raise RuntimeError(
        f"Could not find member index column in {distance_csv}. "
        f"Expected one of ['global_image_idx_0_based', 'image_idx_0_based']."
    )


def _mean_std_from_members(
    X_norm: np.ndarray,
    idx: np.ndarray,
    mask_common: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if idx.size == 0:
        raise ValueError("Cannot compute local prototype stats: empty member index list.")
    if int(np.max(idx)) >= int(X_norm.shape[0]) or int(np.min(idx)) < 0:
        raise ValueError(
            f"Local member indices out of range. min={int(np.min(idx))}, max={int(np.max(idx))}, "
            f"n_images={int(X_norm.shape[0])}"
        )
    stack = X_norm[idx].astype(np.float32, copy=False)
    mu = np.full(mask_common.shape, np.nan, dtype=np.float32)
    sigma = np.full(mask_common.shape, np.nan, dtype=np.float32)
    if np.any(mask_common):
        vals = stack[:, mask_common]
        mu[mask_common] = np.nanmean(vals, axis=0).astype(np.float32, copy=False)
        sigma[mask_common] = np.nanstd(vals, axis=0).astype(np.float32, copy=False)
    return mu, sigma


def discover_local_payloads(
    *,
    official_pipeline_root: Path,
    seed_id: int,
    local_k: int,
    X_norm: np.ndarray,
    mask_common: np.ndarray,
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
) -> list[PrototypePayload]:
    local_dir = (
        official_pipeline_root
        / f"seed{int(seed_id):02d}"
        / "local_class02"
        / f"k{int(local_k)}"
    ).resolve()
    if not local_dir.exists():
        return []

    files: list[tuple[int, Path]] = []
    for path in sorted(local_dir.glob("subclass_*_distance_to_prototype.csv")):
        m = LOCAL_DISTANCE_RX.match(path.name)
        if m:
            files.append((int(m.group(1)), path.resolve()))
    if not files:
        return []

    payloads: list[PrototypePayload] = []
    for subclass_id, csv_path in files:
        idx = _read_member_indices(csv_path)
        temp_mean, temp_std = _mean_std_from_members(X_norm=X_norm, idx=idx, mask_common=mask_common)
        key = f"k{int(local_k)}::subclass_{int(subclass_id):02d}"
        payloads.append(
            PrototypePayload(
                scope="local_class02",
                key=key,
                prototype_name=f"subclass_prototype_{int(subclass_id):02d}",
                temp_mean=temp_mean,
                temp_std=temp_std,
                mask=mask_common.astype(bool, copy=True),
                lat_grid=lat_grid.astype(np.float32, copy=False),
                lon_grid=lon_grid.astype(np.float32, copy=False),
                metadata={
                    "local_k": int(local_k),
                    "subclass_id": int(subclass_id),
                    "source_distance_csv": str(csv_path),
                    "n_members": int(idx.size),
                },
            )
        )
    return payloads


def _axis_from_grid(grid: np.ndarray, axis: int) -> np.ndarray:
    if axis == 0:
        axis_values = np.nanmean(grid, axis=1)
    elif axis == 1:
        axis_values = np.nanmean(grid, axis=0)
    else:
        raise ValueError("axis must be 0 or 1")
    if axis_values.ndim != 1 or axis_values.size < 2:
        return np.arange(grid.shape[axis], dtype=np.float32)

    diffs = np.diff(axis_values.astype(np.float64))
    if not np.all(np.isfinite(diffs)):
        return np.arange(grid.shape[axis], dtype=np.float32)
    if np.any(np.abs(diffs) < 1e-12):
        return np.arange(grid.shape[axis], dtype=np.float32)
    return axis_values.astype(np.float32, copy=False)


def compute_gradient(
    temp_mean: np.ndarray,
    mask: np.ndarray,
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    valid = mask & np.isfinite(temp_mean)
    grad_mag = np.full(temp_mean.shape, np.nan, dtype=np.float32)
    grad_dir = np.full(temp_mean.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return grad_mag, grad_dir

    fill_value = float(np.nanmean(temp_mean[valid]))
    field = np.where(valid, temp_mean, fill_value).astype(np.float32, copy=False)
    lat_axis = _axis_from_grid(lat_grid, axis=0)
    lon_axis = _axis_from_grid(lon_grid, axis=1)
    try:
        gy, gx = np.gradient(field, lat_axis, lon_axis, edge_order=1)
    except Exception:
        gy, gx = np.gradient(field)

    grad_mag = np.hypot(gx, gy).astype(np.float32, copy=False)
    grad_dir = np.arctan2(gy, gx).astype(np.float32, copy=False)
    grad_mag[~valid] = np.nan
    grad_dir[~valid] = np.nan
    return grad_mag, grad_dir


def segment_regions(temp_mean: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, float, str]:
    valid = mask & np.isfinite(temp_mean)
    labels = np.full(temp_mean.shape, -1, dtype=np.int16)
    vals = temp_mean[valid].astype(np.float32, copy=False)
    if vals.size == 0:
        return labels, float("nan"), "empty"

    threshold = float(np.nanmean(vals))
    method = "mean_fallback"
    if HAS_SKIMAGE and threshold_otsu is not None and np.unique(vals).size > 1:
        try:
            threshold = float(threshold_otsu(vals))
            method = "otsu"
        except Exception:
            method = "mean_fallback"

    low = valid & (temp_mean < threshold)
    high = valid & (~low)
    if np.any(valid) and (not np.any(low) or not np.any(high)):
        threshold = float(np.nanmedian(vals))
        method = "median_fallback"
        low = valid & (temp_mean < threshold)
        high = valid & (~low)
    labels[low] = 0
    labels[high] = 1
    return labels, threshold, method


def boundary_mask_from_regions(region_label_id: np.ndarray, valid: np.ndarray) -> np.ndarray:
    boundary = np.zeros(region_label_id.shape, dtype=bool)
    shifts = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for dy, dx in shifts:
        shifted_lbl = np.roll(region_label_id, shift=(dy, dx), axis=(0, 1))
        shifted_valid = np.roll(valid, shift=(dy, dx), axis=(0, 1))
        diff = (region_label_id != shifted_lbl) & valid & shifted_valid

        if dy > 0:
            diff[0:dy, :] = False
        elif dy < 0:
            diff[dy:, :] = False
        if dx > 0:
            diff[:, 0:dx] = False
        elif dx < 0:
            diff[:, dx:] = False

        boundary |= diff
    return boundary


def connected_region_ids(region_label_id: np.ndarray) -> np.ndarray:
    region_id = np.full(region_label_id.shape, -1, dtype=np.int32)
    low_mask = region_label_id == 0
    high_mask = region_label_id == 1

    low_cc, n_low = ndi.label(low_mask)
    high_cc, _ = ndi.label(high_mask)

    region_id[low_cc > 0] = low_cc[low_cc > 0]
    if np.any(high_cc > 0):
        region_id[high_cc > 0] = high_cc[high_cc > 0] + int(n_low)
    return region_id


def distance_to_boundary_map(boundary_mask: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.full(boundary_mask.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return out
    if not np.any(boundary_mask):
        out[valid] = np.nan
        return out
    dist = ndi.distance_transform_edt(~boundary_mask).astype(np.float32, copy=False)
    dist[~valid] = np.nan
    return dist


def gradient_norm_map(grad_mag: np.ndarray, valid: np.ndarray, percentile: float = 95.0) -> np.ndarray:
    out = np.zeros(grad_mag.shape, dtype=np.float32)
    gvals = grad_mag[valid & np.isfinite(grad_mag)]
    if gvals.size == 0:
        return out
    denom = float(np.nanpercentile(gvals, percentile))
    denom = max(denom, 1e-6)
    out = np.clip(grad_mag / denom, 0.0, 1.0).astype(np.float32, copy=False)
    out[~valid] = 0.0
    return out


def boundary_score_map(
    grad_mag: np.ndarray,
    distance_to_boundary: np.ndarray,
    valid: np.ndarray,
) -> np.ndarray:
    out = np.full(grad_mag.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return out

    gvals = grad_mag[valid & np.isfinite(grad_mag)]
    if gvals.size == 0:
        grad_norm = np.zeros(grad_mag.shape, dtype=np.float32)
    else:
        denom = float(np.nanpercentile(gvals, 95))
        denom = max(denom, 1e-6)
        grad_norm = np.clip(grad_mag / denom, 0.0, 1.0).astype(np.float32, copy=False)

    dvals = distance_to_boundary[valid & np.isfinite(distance_to_boundary)]
    if dvals.size == 0:
        proximity = np.zeros(grad_mag.shape, dtype=np.float32)
    else:
        scale = float(np.nanpercentile(dvals, 75))
        scale = max(scale, 1e-6)
        proximity = np.exp(-distance_to_boundary / scale).astype(np.float32, copy=False)

    out = np.clip((0.65 * grad_norm) + (0.35 * proximity), 0.0, 1.0).astype(np.float32, copy=False)
    out[~valid] = np.nan
    return out


def _single_region_label_map(shape: tuple[int, int], valid: np.ndarray, value: int = 0) -> np.ndarray:
    labels = np.full(shape, -1, dtype=np.int16)
    labels[valid] = int(value)
    return labels


def _single_region_id_map(shape: tuple[int, int], valid: np.ndarray, region_id_value: int = 1) -> np.ndarray:
    region_id = np.full(shape, -1, dtype=np.int32)
    region_id[valid] = int(region_id_value)
    return region_id


def _nan_map(shape: tuple[int, int], valid: np.ndarray) -> np.ndarray:
    out = np.full(shape, np.nan, dtype=np.float32)
    out[~valid] = np.nan
    return out


def _zero_score_map(shape: tuple[int, int], valid: np.ndarray) -> np.ndarray:
    out = np.full(shape, np.nan, dtype=np.float32)
    out[valid] = 0.0
    return out


def _gradient_continuous_score_map(
    grad_mag: np.ndarray,
    valid: np.ndarray,
    max_score: float = 0.35,
) -> np.ndarray:
    out = np.full(grad_mag.shape, np.nan, dtype=np.float32)
    gnorm = gradient_norm_map(grad_mag=grad_mag, valid=valid, percentile=95.0)
    out[valid] = np.clip(gnorm[valid] * float(max_score), 0.0, 1.0).astype(np.float32, copy=False)
    return out


def _nanmean_safe(values: np.ndarray) -> float:
    vals = np.asarray(values, dtype=np.float32)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return float("nan")
    return float(np.nanmean(vals))


def characterize_prototype(payload: PrototypePayload) -> CharacterizationOutput:
    temp_mean = payload.temp_mean.astype(np.float32, copy=False)
    temp_std = payload.temp_std.astype(np.float32, copy=False)
    mask = payload.mask.astype(bool, copy=False)
    valid = mask & np.isfinite(temp_mean)
    regime_label = normalize_regime_label(payload.metadata.get("image_only_regime_label", "homogeneous"))

    grad_mag, grad_dir = compute_gradient(
        temp_mean=temp_mean,
        mask=mask,
        lat_grid=payload.lat_grid,
        lon_grid=payload.lon_grid,
    )

    if regime_label == "multi_regime":
        region_label_id, threshold, threshold_method = segment_regions(temp_mean=temp_mean, mask=mask)
        boundary_mask = boundary_mask_from_regions(region_label_id=region_label_id, valid=valid)
        distance_to_boundary = distance_to_boundary_map(boundary_mask=boundary_mask, valid=valid)
        boundary_score = boundary_score_map(
            grad_mag=grad_mag,
            distance_to_boundary=distance_to_boundary,
            valid=valid,
        )
        region_id = connected_region_ids(region_label_id=region_label_id)
        region_label_text = np.where(region_label_id == 0, "low", np.where(region_label_id == 1, "high", "invalid"))
        segmentation_mode = "image_only_multi_regime_discrete"
    elif regime_label == "single_gradient":
        region_label_id = _single_region_label_map(temp_mean.shape, valid=valid, value=0)
        threshold = float("nan")
        threshold_method = "label_driven_single_gradient"
        boundary_mask = np.zeros(temp_mean.shape, dtype=bool)
        distance_to_boundary = _nan_map(temp_mean.shape, valid=valid)
        boundary_score = _gradient_continuous_score_map(grad_mag=grad_mag, valid=valid, max_score=0.35)
        region_id = _single_region_id_map(temp_mean.shape, valid=valid, region_id_value=1)
        region_label_text = np.where(valid, "single_gradient", "invalid")
        segmentation_mode = "image_only_single_gradient_continuous"
    else:
        region_label_id = _single_region_label_map(temp_mean.shape, valid=valid, value=0)
        threshold = float("nan")
        threshold_method = "label_driven_homogeneous"
        boundary_mask = np.zeros(temp_mean.shape, dtype=bool)
        distance_to_boundary = _nan_map(temp_mean.shape, valid=valid)
        boundary_score = _zero_score_map(temp_mean.shape, valid=valid)
        region_id = _single_region_id_map(temp_mean.shape, valid=valid, region_id_value=1)
        region_label_text = np.where(valid, "homogeneous", "invalid")
        segmentation_mode = "image_only_homogeneous_single_region"

    row_idx, col_idx = np.where(valid)
    pixel_df = pd.DataFrame(
        {
            "scope": payload.scope,
            "prototype_key": payload.key,
            "prototype_name": payload.prototype_name,
            "prototype_regime_label": regime_label,
            "row": row_idx.astype(np.int32),
            "col": col_idx.astype(np.int32),
            "lat": payload.lat_grid[valid].astype(np.float64),
            "lon": payload.lon_grid[valid].astype(np.float64),
            "temp_mean": temp_mean[valid].astype(np.float32),
            "temp_std": temp_std[valid].astype(np.float32),
            "region_label": region_label_text[valid],
            "region_label_id": region_label_id[valid].astype(np.int16),
            "boundary_score": boundary_score[valid].astype(np.float32),
            "gradient_magnitude": grad_mag[valid].astype(np.float32),
            "gradient_direction": grad_dir[valid].astype(np.float32),
            "distance_to_boundary": distance_to_boundary[valid].astype(np.float32),
            "region_id": region_id[valid].astype(np.int32),
        }
    )

    region_rows: list[dict[str, Any]] = []
    for rid in sorted(v for v in np.unique(region_id) if int(v) > 0):
        m = valid & (region_id == int(rid))
        if not np.any(m):
            continue
        labels_in_region = pd.Series(region_label_text[m])
        if labels_in_region.empty:
            continue
        label = str(labels_in_region.mode(dropna=True).iloc[0])
        region_rows.append(
            {
                "scope": payload.scope,
                "prototype_key": payload.key,
                "prototype_name": payload.prototype_name,
                "prototype_regime_label": regime_label,
                "region_id": int(rid),
                "region_label": label,
                "n_pixels": int(np.sum(m)),
                "temp_mean_avg": _nanmean_safe(temp_mean[m]),
                "temp_std_avg": _nanmean_safe(temp_std[m]),
                "gradient_magnitude_avg": _nanmean_safe(grad_mag[m]),
                "boundary_score_avg": _nanmean_safe(boundary_score[m]),
                "distance_to_boundary_avg": _nanmean_safe(distance_to_boundary[m]),
                "lat_min": float(np.nanmin(payload.lat_grid[m])),
                "lat_max": float(np.nanmax(payload.lat_grid[m])),
                "lon_min": float(np.nanmin(payload.lon_grid[m])),
                "lon_max": float(np.nanmax(payload.lon_grid[m])),
            }
        )
    region_df = pd.DataFrame(region_rows)

    maps = {
        "temp_mean": temp_mean.astype(np.float32, copy=False),
        "temp_std": temp_std.astype(np.float32, copy=False),
        "region_label_id": region_label_id.astype(np.int16, copy=False),
        "boundary_mask": boundary_mask.astype(np.uint8, copy=False),
        "boundary_score": boundary_score.astype(np.float32, copy=False),
        "gradient_magnitude": grad_mag.astype(np.float32, copy=False),
        "gradient_direction": grad_dir.astype(np.float32, copy=False),
        "distance_to_boundary": distance_to_boundary.astype(np.float32, copy=False),
        "region_id": region_id.astype(np.int32, copy=False),
        "mask_valid": valid.astype(np.uint8, copy=False),
    }
    return CharacterizationOutput(
        pixel_df=pixel_df,
        region_df=region_df,
        maps=maps,
        threshold=threshold,
        threshold_method=threshold_method,
        regime_label=regime_label,
        segmentation_mode=segmentation_mode,
    )


def ensure_output_dir(output_root: Path, run_tag: str | None, allow_overwrite: bool) -> Path:
    if run_tag is None or not run_tag.strip():
        run_tag = datetime.now().strftime("seed11_characterization_%Y%m%d_%H%M%S")
    out_dir = (output_root / run_tag).resolve()
    if out_dir.exists() and any(out_dir.iterdir()) and not allow_overwrite:
        raise FileExistsError(f"Output directory exists and is not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _write_guard(path: Path, allow_overwrite: bool) -> None:
    if path.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")


def save_csv(df: pd.DataFrame, path: Path, allow_overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_guard(path, allow_overwrite=allow_overwrite)
    df.to_csv(path, index=False)


def save_json(payload: Mapping[str, Any], path: Path, allow_overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_guard(path, allow_overwrite=allow_overwrite)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_text(text: str, path: Path, allow_overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_guard(path, allow_overwrite=allow_overwrite)
    path.write_text(text, encoding="utf-8")


def save_map_arrays(
    maps: Mapping[str, np.ndarray],
    out_dir: Path,
    allow_overwrite: bool,
) -> dict[str, Path]:
    out_paths: dict[str, Path] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, arr in maps.items():
        p = out_dir / f"{key}.npy"
        _write_guard(p, allow_overwrite=allow_overwrite)
        np.save(p, arr)
        out_paths[key] = p
    return out_paths


def _masked_float(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float32).copy()
    out[~valid] = np.nan
    return out


def save_map_figures(
    *,
    maps: Mapping[str, np.ndarray],
    out_dir: Path,
    allow_overwrite: bool,
) -> dict[str, Path]:
    valid = np.asarray(maps["mask_valid"]).astype(bool, copy=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_paths: dict[str, Path] = {}

    def _save(fig: plt.Figure, path: Path) -> None:
        _write_guard(path, allow_overwrite=allow_overwrite)
        fig.savefig(path, dpi=170, bbox_inches="tight")
        plt.close(fig)
        out_paths[path.stem] = path

    region = np.asarray(maps["region_label_id"], dtype=np.float32)
    region_plot = region.copy()
    region_plot[~valid] = np.nan
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.imshow(region_plot, origin="lower", cmap=ListedColormap(["#3A86FF", "#FF8C42"]), vmin=0, vmax=1, aspect="auto")
    ax.set_title("Semantic Region Map")
    ax.axis("off")
    _save(fig, out_dir / "segment_map.png")

    grad_mag = _masked_float(np.asarray(maps["gradient_magnitude"], dtype=np.float32), valid)
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(grad_mag, origin="lower", cmap="viridis", aspect="auto")
    ax.set_title("Gradient Magnitude")
    ax.axis("off")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    _save(fig, out_dir / "gradient_magnitude_map.png")

    boundary_score = _masked_float(np.asarray(maps["boundary_score"], dtype=np.float32), valid)
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(boundary_score, origin="lower", cmap="magma", vmin=0, vmax=1, aspect="auto")
    ax.set_title("Boundary Score")
    ax.axis("off")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    _save(fig, out_dir / "boundary_score_map.png")

    boundary_mask = _masked_float(np.asarray(maps["boundary_mask"], dtype=np.float32), valid)
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(boundary_mask, origin="lower", cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_title("Boundary Map")
    ax.axis("off")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    _save(fig, out_dir / "boundary_map.png")

    return out_paths


def build_manifest(
    *,
    state_config_path: Path | None,
    seed_id: int,
    local_k: int,
    compact_model_npz: Path,
    compact_model_manifest: Path | None,
    official_pipeline_root: Path,
    output_dir: Path,
    summary_df: pd.DataFrame,
    pixel_csv_path: Path,
    region_csv_path: Path,
    dataset_paths: Mapping[str, Path],
    records: Sequence[dict[str, Any]],
    image_only_bundle: ImageOnlyLabelBundle | None = None,
) -> dict[str, Any]:
    semantic_counts = {}
    if not summary_df.empty and "prototype_regime_label" in summary_df.columns:
        semantic_counts = {
            str(k): int(v) for k, v in summary_df["prototype_regime_label"].value_counts(dropna=False).items()
        }
    return {
        "generated_at_utc": now_utc(),
        "seed_id": int(seed_id),
        "local_k": int(local_k),
        "state_config_path": str(state_config_path.resolve()) if state_config_path is not None else "",
        "source": {
            "official_pipeline_root": str(official_pipeline_root.resolve()),
            "compact_model_npz": str(compact_model_npz.resolve()),
            "compact_model_manifest": str(compact_model_manifest.resolve()) if compact_model_manifest else "",
            "dataset_X_norm": str(dataset_paths["X_norm"].resolve()),
            "dataset_mask_common": str(dataset_paths["mask_common"].resolve()),
            "image_only_label_run_dir": str(image_only_bundle.run_dir.resolve()) if image_only_bundle else "",
            "image_only_global_csv": str(image_only_bundle.global_csv.resolve()) if image_only_bundle else "",
            "image_only_local_csv": str(image_only_bundle.local_csv.resolve()) if image_only_bundle else "",
        },
        "counts": {
            "n_prototypes": int(len(summary_df)),
            "n_global_prototypes": int(np.sum(summary_df["scope"] == "global")) if not summary_df.empty else 0,
            "n_local_prototypes": int(np.sum(summary_df["scope"] == "local_class02")) if not summary_df.empty else 0,
            "n_pixels_total": int(summary_df["n_valid_pixels"].sum()) if not summary_df.empty else 0,
            "prototype_regime_label_counts": semantic_counts,
        },
        "outputs": {
            "output_dir": str(output_dir.resolve()),
            "prototype_summary_csv": str((output_dir / "prototype_summary.csv").resolve()),
            "pixel_descriptors_all_csv": str(pixel_csv_path.resolve()),
            "region_descriptors_all_csv": str(region_csv_path.resolve()),
        },
        "prototype_records": list(records),
        "notes": [
            "Downstream-only characterization stage built on official frozen prototypes.",
            "No clustering or class membership changes are performed here.",
            "Prototype regime labels are sourced from image_only outputs and treated as semantic truth.",
            "Pixel-wise descriptors include lat/lon, temp_mean, temp_std, region_label, and boundary_score.",
        ],
    }


def build_run_report_markdown(
    *,
    seed_id: int,
    output_dir: Path,
    summary_df: pd.DataFrame,
    pixel_df: pd.DataFrame,
    region_df: pd.DataFrame,
    image_only_bundle: ImageOnlyLabelBundle | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# Prototype Characterization Run Report")
    lines.append("")
    lines.append(f"- Generated UTC: {now_utc()}")
    lines.append(f"- Seed: {int(seed_id)}")
    lines.append(f"- Output dir: `{output_dir}`")
    if image_only_bundle is not None:
        lines.append(f"- Image-only label run dir: `{image_only_bundle.run_dir}`")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Prototypes processed: {int(len(summary_df))}")
    lines.append(
        f"- Global prototypes: {int(np.sum(summary_df['scope'] == 'global')) if not summary_df.empty else 0}"
    )
    lines.append(
        f"- Local class_02 prototypes: {int(np.sum(summary_df['scope'] == 'local_class02')) if not summary_df.empty else 0}"
    )
    lines.append(f"- Pixel rows exported: {int(len(pixel_df))}")
    lines.append(f"- Region rows exported: {int(len(region_df))}")
    if not summary_df.empty and "prototype_regime_label" in summary_df.columns:
        vc = summary_df["prototype_regime_label"].value_counts(dropna=False)
        lines.append(f"- Regime label counts: { {str(k): int(v) for k, v in vc.items()} }")
    lines.append("")
    lines.append("## Required Pixel Columns")
    lines.append("")
    required_cols = ["lat", "lon", "temp_mean", "temp_std", "region_label", "boundary_score"]
    lines.append(f"- Present: {all(c in pixel_df.columns for c in required_cols)}")
    lines.append(f"- Columns: {list(pixel_df.columns)}")
    lines.append("")
    lines.append("## Prototype Summary")
    lines.append("")
    if summary_df.empty:
        lines.append("- No prototypes processed.")
    else:
        for _, row in summary_df.iterrows():
            lines.append(
                f"- {row['scope']} | {row['prototype_key']} | "
                f"label={row.get('prototype_regime_label', 'unknown')} | "
                f"mode={row.get('segmentation_mode', 'n/a')} | "
                f"valid_pixels={int(row['n_valid_pixels'])} | "
                f"threshold={float(row['threshold']):.6f} ({row['threshold_method']})"
            )
    lines.append("")
    lines.append("## Semantic Checks")
    lines.append("")
    if summary_df.empty or "prototype_regime_label" not in summary_df.columns:
        lines.append("- Semantic checks unavailable (missing prototype_regime_label).")
    else:
        by_label = summary_df.groupby("prototype_regime_label")["n_regions"].agg(["min", "max", "mean"]).reset_index()
        for _, row in by_label.iterrows():
            lines.append(
                f"- {row['prototype_regime_label']}: n_regions[min={int(row['min'])}, "
                f"max={int(row['max'])}, mean={float(row['mean']):.2f}]"
            )
        if "prototype_regime_label" in pixel_df.columns and "boundary_score" in pixel_df.columns:
            for label in ["homogeneous", "single_gradient", "multi_regime"]:
                m = pixel_df["prototype_regime_label"] == label
                if not m.any():
                    continue
                vals = pixel_df.loc[m, "boundary_score"].astype(float).to_numpy()
                vals = vals[np.isfinite(vals)]
                if vals.size == 0:
                    continue
                p95 = float(np.nanpercentile(vals, 95))
                avg = float(np.nanmean(vals))
                lines.append(f"- {label}: boundary_score mean={avg:.4f}, p95={p95:.4f}")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append("- `prototype_summary.csv`")
    lines.append("- `pixel_descriptors_all.csv`")
    lines.append("- `region_descriptors_all.csv`")
    lines.append("- `manifest.json`")
    lines.append("- `run_report.md`")
    lines.append("- per-prototype maps and raster arrays (`segment_map`, `gradient`, `boundary`)")
    return "\n".join(lines) + "\n"


def dict_without_none(values: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


def close_figures(figs: Iterable[plt.Figure | None]) -> None:
    for fig in figs:
        if fig is None:
            continue
        plt.close(fig)
