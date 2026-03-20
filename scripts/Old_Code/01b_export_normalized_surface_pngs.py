"""Export normalized Fossum surface stack to PNGs with a common symmetric color scale."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from physical_coords import load_physical_lon_lat
from pil_geo_plot import save_geo_heatmap_png

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except Exception:
    HAS_MPL = False


ROOT = Path(__file__).resolve().parents[1]
IN_X_NORM = ROOT / "results" / "fossum" / "X_surface_300_norm.npy"
IN_MASK = ROOT / "results" / "fossum" / "mask_common.npy"

OUT_DIR = ROOT / "results" / "fossum" / "pngs_normalized_surface_300"
OUT_SCALE = OUT_DIR / "color_scale_norm.json"
OUT_INDEX = OUT_DIR / "index.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export thesis-ready normalized surface figures.")
    parser.add_argument("--z-start", type=int, default=1, help="First z (1-based, inclusive).")
    parser.add_argument("--z-end", type=int, default=300, help="Last z (1-based, inclusive).")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="Output folder for PNGs and index.")
    parser.add_argument(
        "--fixed-scale-json",
        type=Path,
        default=None,
        help="Optional JSON containing vmin/vmax (or max_abs) to enforce exact pre-existing color scale.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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

    if args.fixed_scale_json is not None:
        scale_path = args.fixed_scale_json.resolve()
        payload = json.loads(scale_path.read_text(encoding="utf-8"))
        if "vmin" in payload and "vmax" in payload:
            vmin = float(payload["vmin"])
            vmax = float(payload["vmax"])
            max_abs = float(max(abs(vmin), abs(vmax)))
        else:
            max_abs = float(payload["max_abs"])
            vmin = -max_abs
            vmax = +max_abs
    else:
        max_abs = float(np.percentile(np.abs(valid_values), 98.0))
        if not np.isfinite(max_abs) or max_abs <= 0.0:
            raise RuntimeError(f"Invalid max_abs={max_abs}")
        vmin = -max_abs
        vmax = +max_abs

    z_start = max(1, int(args.z_start))
    z_end = min(int(X_norm.shape[0]), int(args.z_end))
    if z_start > z_end:
        raise RuntimeError(f"Invalid z range: z_start={z_start}, z_end={z_end}")

    out_dir = args.out_dir.resolve()
    out_scale = out_dir / OUT_SCALE.name
    out_index = out_dir / OUT_INDEX.name
    out_dir.mkdir(parents=True, exist_ok=True)

    lon, lat, coord_meta = load_physical_lon_lat(ROOT, X_norm.shape[2], X_norm.shape[1])
    extent = [float(np.nanmin(lon)), float(np.nanmax(lon)), float(np.nanmin(lat)), float(np.nanmax(lat))]

    cmap = None
    if HAS_MPL:
        cmap = plt.get_cmap("coolwarm").copy()
        cmap.set_bad(color="white")

    rows = []
    for z in range(z_start, z_end + 1):
        arr = X_norm[z - 1].copy()
        arr[~mask_common] = np.nan

        out_file = out_dir / f"X_surface_norm_z{z:03d}.png"
        title = f"Normalized surface temperature - 2024 day z={z:03d}"
        if HAS_MPL:
            fig, ax = plt.subplots(figsize=(7.0, 4.2))
            im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
            ax.set_title(title)
            ax.set_xlabel("Longitude (degrees)")
            ax.set_ylabel("Latitude (degrees)")
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label("Normalized temperature (-)")
            fig.tight_layout()
            fig.savefig(out_file, dpi=150)
            plt.close(fig)
        else:
            save_geo_heatmap_png(
                arr=arr,
                lon=lon,
                lat=lat,
                vmin=vmin,
                vmax=vmax,
                title=title,
                xlabel="Longitude (degrees)",
                ylabel="Latitude (degrees)",
                cbar_label="Normalized temperature (-)",
                out_path=out_file,
                cmap_name="coolwarm",
            )

        finite = np.isfinite(arr)
        values = arr[finite]
        rows.append(
            {
                "z": z,
                "filepath": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                "lon_min": extent[0],
                "lon_max": extent[1],
                "lat_min": extent[2],
                "lat_max": extent[3],
                "mean_norm": float(np.mean(values)),
                "std_norm": float(np.std(values)),
                "min_norm": float(np.min(values)),
                "max_norm": float(np.max(values)),
            }
        )

    with out_index.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "z",
                "filepath",
                "lon_min",
                "lon_max",
                "lat_min",
                "lat_max",
                "mean_norm",
                "std_norm",
                "min_norm",
                "max_norm",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    scale_payload = {
        "vmin": float(vmin),
        "vmax": float(vmax),
        "max_abs": float(max_abs),
        "source_file": str(IN_X_NORM.relative_to(ROOT)).replace("\\", "/"),
        "coord_source": coord_meta,
    }
    out_scale.write_text(json.dumps(scale_payload, indent=2), encoding="utf-8")

    sample = {int(r["z"]): r for r in rows}
    print(f"[OK] png_count={len(rows)}")
    print(f"[OK] coord_source_method={coord_meta.get('method')}")
    print(f"[OK] vmin={vmin:.9f}")
    print(f"[OK] vmax={vmax:.9f}")
    for z in sorted({z_start, (z_start + z_end) // 2, z_end}):
        if z in sample:
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
