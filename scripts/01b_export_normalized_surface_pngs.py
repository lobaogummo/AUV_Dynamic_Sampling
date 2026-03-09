"""Export normalized Fossum surface stack to PNGs with a common symmetric color scale."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
IN_X_NORM = ROOT / "results" / "fossum" / "X_surface_300_norm.npy"
IN_MASK = ROOT / "results" / "fossum" / "mask_common.npy"

OUT_DIR = ROOT / "results" / "fossum" / "pngs_normalized_surface_300"
OUT_SCALE = OUT_DIR / "color_scale_norm.json"
OUT_INDEX = OUT_DIR / "index.csv"


def main() -> None:
    X_norm = np.load(IN_X_NORM)
    mask_common = np.load(IN_MASK)

    if X_norm.ndim != 3:
        raise RuntimeError(f"Expected 3D array for X_norm, got shape={X_norm.shape}")
    if mask_common.shape != X_norm.shape[1:]:
        raise RuntimeError(
            f"mask_common shape mismatch. mask={mask_common.shape}, X_norm spatial={X_norm.shape[1:]}"
        )

    X_norm = X_norm.astype(np.float32, copy=False)
    mask_common = mask_common.astype(bool, copy=False)

    valid_values = X_norm[:, mask_common]
    if valid_values.size == 0:
        raise RuntimeError("No valid pixels found using common mask")

    max_abs = float(np.percentile(np.abs(valid_values), 98.0))
    if not np.isfinite(max_abs) or max_abs <= 0.0:
        raise RuntimeError(f"Invalid max_abs={max_abs}")
    vmin = -max_abs
    vmax = +max_abs

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")

    rows = []
    for z in range(1, X_norm.shape[0] + 1):
        arr = X_norm[z - 1].copy()
        arr[~mask_common] = np.nan

        out_file = OUT_DIR / f"X_surface_norm_z{z:03d}.png"
        fig, ax = plt.subplots(figsize=(7.0, 4.2))
        im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"Normalized TEMP Surface 2024 z={z:03d}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Normalized temp")
        fig.tight_layout()
        fig.savefig(out_file, dpi=150)
        plt.close(fig)

        finite = np.isfinite(arr)
        values = arr[finite]
        rows.append(
            {
                "z": z,
                "filepath": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                "mean_norm": float(np.mean(values)),
                "std_norm": float(np.std(values)),
                "min_norm": float(np.min(values)),
                "max_norm": float(np.max(values)),
            }
        )

    with OUT_INDEX.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["z", "filepath", "mean_norm", "std_norm", "min_norm", "max_norm"],
        )
        writer.writeheader()
        writer.writerows(rows)

    scale_payload = {
        "vmin": float(vmin),
        "vmax": float(vmax),
        "max_abs": float(max_abs),
        "source_file": str(IN_X_NORM.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT_SCALE.write_text(json.dumps(scale_payload, indent=2), encoding="utf-8")

    sample = {int(r["z"]): r for r in rows}
    print(f"[OK] png_count={len(rows)}")
    print(f"[OK] vmin={vmin:.9f}")
    print(f"[OK] vmax={vmax:.9f}")
    for z in (1, 150, 300):
        r = sample[z]
        print(
            "[OK] z={z} mean={mean:.9f} std={std:.9f} min={mn:.9f} max={mx:.9f}".format(
                z=z,
                mean=r["mean_norm"],
                std=r["std_norm"],
                mn=r["min_norm"],
                mx=r["max_norm"],
            )
        )


if __name__ == "__main__":
    main()
