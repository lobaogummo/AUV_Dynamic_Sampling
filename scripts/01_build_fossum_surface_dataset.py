"""Build base Fossum surface dataset from deterministic 2024 depth-1 GSLIB."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from export_surface_2024_300_images import (
    TARGET_Z_MAX,
    parse_header,
    resolve_source_file,
    second_pass_build_grids,
    _validate_columns,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "fossum"

OUT_X = OUT_DIR / "X_surface_300.npy"
OUT_X_NORM = OUT_DIR / "X_surface_300_norm.npy"
OUT_MASK = OUT_DIR / "mask_common.npy"
OUT_GLOBAL_STATS = OUT_DIR / "global_stats.json"
OUT_SUMMARY = OUT_DIR / "dataset_summary.json"


def main() -> None:
    source_file = resolve_source_file()
    _title, varnames = parse_header(source_file)
    idx = _validate_columns(varnames)
    nvars = len(varnames)

    X = second_pass_build_grids(source_file, nvars, idx).astype(np.float32, copy=False)
    expected_shape = (TARGET_Z_MAX, 64, 112)
    if X.shape != expected_shape:
        raise RuntimeError(f"Unexpected shape. Expected {expected_shape}, got {X.shape}")

    mask_common = np.isfinite(X).all(axis=0)
    valid_stack = X[:, mask_common]
    if valid_stack.size == 0:
        raise RuntimeError("No valid pixels found for common mask.")

    mu_global = float(np.mean(valid_stack))
    sigma_global = float(np.std(valid_stack))
    if not np.isfinite(mu_global) or not np.isfinite(sigma_global) or sigma_global <= 0.0:
        raise RuntimeError(f"Invalid global stats: mu={mu_global}, sigma={sigma_global}")

    X_norm = np.full_like(X, np.nan, dtype=np.float32)
    X_norm[:, mask_common] = ((valid_stack - mu_global) / sigma_global).astype(np.float32)

    valid_pixels_per_image = np.isfinite(X).sum(axis=(1, 2))
    global_stats = {
        "mu_global": mu_global,
        "sigma_global": sigma_global,
        "n_images": int(X.shape[0]),
        "ny": int(X.shape[1]),
        "nx": int(X.shape[2]),
        "valid_pixels_per_image_mean": float(np.mean(valid_pixels_per_image)),
        "valid_pixels_total": int(valid_stack.size),
    }

    mask_fraction_valid = float(np.mean(mask_common))
    summary = {
        "source_file": str(source_file.relative_to(ROOT)).replace("\\", "/"),
        "shape": [int(X.shape[0]), int(X.shape[1]), int(X.shape[2])],
        "dtype": str(X.dtype),
        "mask_fraction_valid": mask_fraction_valid,
        "mask_fraction_invalid": float(1.0 - mask_fraction_valid),
        "z_min": 1,
        "z_max": int(X.shape[0]),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_X, X)
    np.save(OUT_X_NORM, X_norm)
    np.save(OUT_MASK, mask_common)
    OUT_GLOBAL_STATS.write_text(json.dumps(global_stats, indent=2), encoding="utf-8")
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"[OK] wrote={OUT_X}")
    print(f"[OK] wrote={OUT_X_NORM}")
    print(f"[OK] wrote={OUT_MASK}")
    print(f"[OK] wrote={OUT_GLOBAL_STATS}")
    print(f"[OK] wrote={OUT_SUMMARY}")
    print(f"[OK] shape={X.shape}, dtype={X.dtype}")
    print(f"[OK] mu_global={mu_global:.9f}")
    print(f"[OK] sigma_global={sigma_global:.9f}")
    print(f"[OK] mask_common_valid_fraction={mask_fraction_valid * 100.0:.6f}%")


if __name__ == "__main__":
    main()
