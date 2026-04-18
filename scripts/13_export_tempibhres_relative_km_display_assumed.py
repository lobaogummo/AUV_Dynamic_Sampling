"""Generate tempIBHRes figures with relative-km axes (display-derived assumption).

This script is intentionally presentation-only:
- does NOT change clustering, prototypes, planner, or cost function.
- does NOT overwrite existing official outputs.
- creates a new, versioned output folder.

Methodological note:
- `tempIBHRes2024_*` has indexed coordinates (`x,y,z,temp`) in the audited files.
- Relative-km axes here are derived from the same HRes bbox mapping previously used
  for display, not from independently verified native georeferencing of tempIBHRes.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from math import cos, radians
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
PREFERRED_HRES_REL = "data/HResNew/CMEMSnaza_20241029_HResNew.nc"
NETCDF_SUMMARY = ROOT / "results" / "netcdf_files_summary.csv"

IN_X_SURFACE_CANDIDATES = [
    ROOT / "results" / "plots" / "X_surface_300.npy",
    ROOT / "results" / "fossum" / "X_surface_300.npy",
]
IN_X_NORM_CANDIDATES = [
    ROOT / "results" / "plots" / "X_surface_300_norm.npy",
    ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
]
IN_MASK_CANDIDATES = [
    ROOT / "results" / "plots" / "mask_common.npy",
    ROOT / "results" / "fossum" / "mask_common.npy",
]
IN_SCALE_TEMP = ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis" / "color_scale.json"
IN_SCALE_NORM = ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis" / "color_scale_norm.json"

X_LABEL = "X (km, relative)"
Y_LABEL = "Y (km, relative)"
GEOREF_NOTE = (
    "Relative-km axes are display-derived from local HRes bounding-box mapping "
    "and are not independently verified native georeferencing of tempIBHRes."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export tempIBHRes figures with relative-km axes (display-derived).")
    p.add_argument("--tag", type=str, default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    p.add_argument("--z-start", type=int, default=1)
    p.add_argument("--z-end", type=int, default=300)
    return p.parse_args()


def resolve_existing(candidates: Iterable[Path]) -> Path:
    for p in candidates:
        if p.exists():
            return p
    listed = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Required input not found. Checked: {listed}")


def to_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_hres_bbox(summary_csv: Path) -> Dict[str, float]:
    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing summary CSV: {summary_csv}")
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    preferred = next((r for r in rows if r.get("path") == PREFERRED_HRES_REL and r.get("open_ok") == "True"), None)
    if preferred is None:
        preferred = next(
            (
                r
                for r in rows
                if "/HResNew/" in (r.get("path") or "").replace("\\", "/") and r.get("open_ok") == "True"
            ),
            None,
        )
    if preferred is None:
        raise RuntimeError("No valid HRes row available in netcdf_files_summary.csv")

    return {
        "source_path": preferred["path"],
        "lon_min": float(preferred["lon_min"]),
        "lon_max": float(preferred["lon_max"]),
        "lat_min": float(preferred["lat_min"]),
        "lat_max": float(preferred["lat_max"]),
    }


def km_per_degree(lat_deg: float) -> Tuple[float, float]:
    phi = radians(lat_deg)
    km_deg_lat = (
        111.13292
        - 0.55982 * cos(2.0 * phi)
        + 0.001175 * cos(4.0 * phi)
        - 0.0000023 * cos(6.0 * phi)
    )
    km_deg_lon = 111.41284 * cos(phi) - 0.0935 * cos(3.0 * phi) + 0.00012 * cos(5.0 * phi)
    return float(km_deg_lat), float(km_deg_lon)


def build_relative_km_axes(nx: int, ny: int, bbox: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
    lat_mid = 0.5 * (bbox["lat_min"] + bbox["lat_max"])
    km_deg_lat, km_deg_lon = km_per_degree(lat_mid)

    dlon = (bbox["lon_max"] - bbox["lon_min"]) / float(nx - 1)
    dlat = (bbox["lat_max"] - bbox["lat_min"]) / float(ny - 1)

    dx_km = dlon * km_deg_lon
    dy_km = dlat * km_deg_lat

    x_km = np.arange(nx, dtype=np.float64) * dx_km
    y_km = np.arange(ny, dtype=np.float64) * dy_km

    meta = {
        "lat_mid_deg": float(lat_mid),
        "km_per_deg_lat": float(km_deg_lat),
        "km_per_deg_lon": float(km_deg_lon),
        "delta_lon_deg_per_cell": float(dlon),
        "delta_lat_deg_per_cell": float(dlat),
        "dx_km_per_cell": float(dx_km),
        "dy_km_per_cell": float(dy_km),
        "x_km_min": float(x_km.min()),
        "x_km_max": float(x_km.max()),
        "y_km_min": float(y_km.min()),
        "y_km_max": float(y_km.max()),
    }
    return x_km, y_km, meta


def render_field(
    arr: np.ndarray,
    out_png: Path,
    title: str,
    cbar_label: str,
    vmin: float,
    vmax: float,
    extent: List[float],
    cmap_name: str,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
    ax.set_title(title)
    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(Y_LABEL)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def export_set(
    x_stack: np.ndarray,
    mask_common: np.ndarray | None,
    out_dir: Path,
    fname_prefix: str,
    title_prefix: str,
    cbar_label: str,
    cmap_name: str,
    vmin: float,
    vmax: float,
    extent: List[float],
    z_start: int,
    z_end: int,
    value_prefix: str,
) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for z in range(z_start, z_end + 1):
        arr = x_stack[z - 1].copy()
        if mask_common is not None:
            arr[~mask_common] = np.nan

        out_png = out_dir / f"{fname_prefix}{z:03d}.png"
        render_field(
            arr=arr,
            out_png=out_png,
            title=f"{title_prefix} z={z:03d}",
            cbar_label=cbar_label,
            vmin=vmin,
            vmax=vmax,
            extent=extent,
            cmap_name=cmap_name,
        )
        finite = np.isfinite(arr)
        values = arr[finite]
        rows.append(
            {
                "z": int(z),
                "filepath": to_rel(out_png),
                "x_km_min": float(extent[0]),
                "x_km_max": float(extent[1]),
                "y_km_min": float(extent[2]),
                "y_km_max": float(extent[3]),
                f"mean_{value_prefix}": float(np.mean(values)),
                f"std_{value_prefix}": float(np.std(values)),
                f"min_{value_prefix}": float(np.min(values)),
                f"max_{value_prefix}": float(np.max(values)),
                "x_axis_label": X_LABEL,
                "y_axis_label": Y_LABEL,
                "georef_note": GEOREF_NOTE,
            }
        )
    return rows


def write_csv(path: Path, rows: List[Dict[str, float]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    out_root = ROOT / "results" / "plots" / f"tempibhres_relative_km_display_assumed_{args.tag}"

    in_x = resolve_existing(IN_X_SURFACE_CANDIDATES)
    in_x_norm = resolve_existing(IN_X_NORM_CANDIDATES)
    in_mask = resolve_existing(IN_MASK_CANDIDATES)

    x_surface = np.load(in_x).astype(np.float32, copy=False)
    x_norm = np.load(in_x_norm).astype(np.float32, copy=False)
    mask_common = np.load(in_mask).astype(bool, copy=False)
    if x_surface.shape != x_norm.shape:
        raise RuntimeError(f"Shape mismatch X vs X_norm: {x_surface.shape} vs {x_norm.shape}")
    if mask_common.shape != x_surface.shape[1:]:
        raise RuntimeError(f"Shape mismatch mask vs spatial: {mask_common.shape} vs {x_surface.shape[1:]}")

    z_start = max(1, int(args.z_start))
    z_end = min(int(x_surface.shape[0]), int(args.z_end))
    if z_start > z_end:
        raise RuntimeError(f"Invalid z range: {z_start}..{z_end}")

    scale_temp = load_json(IN_SCALE_TEMP)
    scale_norm = load_json(IN_SCALE_NORM)
    vmin_temp = float(scale_temp["vmin"])
    vmax_temp = float(scale_temp["vmax"])
    vmin_norm = float(scale_norm["vmin"])
    vmax_norm = float(scale_norm["vmax"])

    bbox = find_hres_bbox(NETCDF_SUMMARY)
    ny, nx = int(x_surface.shape[1]), int(x_surface.shape[2])
    x_km, y_km, km_meta = build_relative_km_axes(nx=nx, ny=ny, bbox=bbox)
    extent = [float(x_km.min()), float(x_km.max()), float(y_km.min()), float(y_km.max())]

    out_det = out_root / "deterministic_2024_surface_300_thesis_relative_km_display_assumed"
    out_norm = out_root / "pngs_normalized_surface_300_thesis_relative_km_display_assumed"

    det_rows = export_set(
        x_stack=x_surface,
        mask_common=None,
        out_dir=out_det,
        fname_prefix="TEMP_surface_2024_z",
        title_prefix="Surface temperature - 2024 day",
        cbar_label="Temperature (degC)",
        cmap_name="viridis",
        vmin=vmin_temp,
        vmax=vmax_temp,
        extent=extent,
        z_start=z_start,
        z_end=z_end,
        value_prefix="temp",
    )
    norm_rows = export_set(
        x_stack=x_norm,
        mask_common=mask_common,
        out_dir=out_norm,
        fname_prefix="X_surface_norm_z",
        title_prefix="Normalized surface temperature - 2024 day",
        cbar_label="Normalized temperature (-)",
        cmap_name="coolwarm",
        vmin=vmin_norm,
        vmax=vmax_norm,
        extent=extent,
        z_start=z_start,
        z_end=z_end,
        value_prefix="norm",
    )

    write_csv(
        out_det / "index.csv",
        det_rows,
        [
            "z",
            "filepath",
            "x_km_min",
            "x_km_max",
            "y_km_min",
            "y_km_max",
            "mean_temp",
            "std_temp",
            "min_temp",
            "max_temp",
            "x_axis_label",
            "y_axis_label",
            "georef_note",
        ],
    )
    write_csv(
        out_norm / "index.csv",
        norm_rows,
        [
            "z",
            "filepath",
            "x_km_min",
            "x_km_max",
            "y_km_min",
            "y_km_max",
            "mean_norm",
            "std_norm",
            "min_norm",
            "max_norm",
            "x_axis_label",
            "y_axis_label",
            "georef_note",
        ],
    )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "output_root": to_rel(out_root),
        "inputs": {
            "x_surface": to_rel(in_x),
            "x_surface_norm": to_rel(in_x_norm),
            "mask_common": to_rel(in_mask),
            "deterministic_scale": to_rel(IN_SCALE_TEMP),
            "normalized_scale": to_rel(IN_SCALE_NORM),
            "netcdf_summary": to_rel(NETCDF_SUMMARY),
        },
        "axis_mode": {
            "x_axis_label": X_LABEL,
            "y_axis_label": Y_LABEL,
            "mode": "relative_km_display_assumed_from_hres_bbox",
            "independent_validation_status": "not_independently_validated",
            "note": GEOREF_NOTE,
        },
        "hres_bbox_source": bbox,
        "relative_km_geometry": km_meta,
        "counts": {
            "deterministic_pngs": len(det_rows),
            "normalized_pngs": len(norm_rows),
            "z_start": int(z_start),
            "z_end": int(z_end),
        },
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report = [
        "# Relative-km Feasibility (tempIBHRes)",
        "",
        "## Conclusion",
        "- Relative-km axes are technically possible for display.",
        "- In current repo state, spacing is not independently validated from tempIBHRes native metadata.",
        "- This output therefore uses a display-derived assumption from HRes bbox mapping.",
        "",
        "## Axes Used",
        f"- X: `{X_LABEL}`",
        f"- Y: `{Y_LABEL}`",
        "",
        "## Method",
        "- Source bbox from `results/netcdf_files_summary.csv` (HRes row).",
        "- Converted deg-per-cell to km-per-cell at midpoint latitude.",
        "- Built relative axes from origin `(0,0)`.",
        "",
        "## Key Parameters",
        f"- dx_km_per_cell: `{km_meta['dx_km_per_cell']:.6f}`",
        f"- dy_km_per_cell: `{km_meta['dy_km_per_cell']:.6f}`",
        f"- x_extent_km: `{km_meta['x_km_min']:.6f} .. {km_meta['x_km_max']:.6f}`",
        f"- y_extent_km: `{km_meta['y_km_min']:.6f} .. {km_meta['y_km_max']:.6f}`",
        "",
        "## Methodological Safety",
        f"- {GEOREF_NOTE}",
    ]
    (out_root / "RELATIVE_KM_FEASIBILITY.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"[OK] output_root={out_root}")
    print(f"[OK] deterministic_pngs={len(det_rows)}")
    print(f"[OK] normalized_pngs={len(norm_rows)}")
    print(f"[OK] dx_km_per_cell={km_meta['dx_km_per_cell']:.6f}")
    print(f"[OK] dy_km_per_cell={km_meta['dy_km_per_cell']:.6f}")


if __name__ == "__main__":
    main()

