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
IN_SCALE_TEMP_CANDIDATES = [
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis" / "color_scale.json",
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json",
]
IN_SCALE_NORM_CANDIDATES = [
    ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis" / "color_scale_norm.json",
    ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis_indexed_axes" / "color_scale_norm.json",
]

GEOREF_NOTE = (
    "Relative-km axes are display-derived from local HRes bounding-box mapping "
    "and are not independently verified native georeferencing of tempIBHRes."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export tempIBHRes figures with relative-km axes (display-derived).")
    p.add_argument("--tag", type=str, default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    p.add_argument("--z-start", type=int, default=1)
    p.add_argument("--z-end", type=int, default=300)
    p.add_argument("--x-label", type=str, default="x", help="X axis label text.")
    p.add_argument("--y-label", type=str, default="y", help="Y axis label text.")
    p.add_argument("--unit-tag", type=str, default="km", help="Unit annotation shown near axes; use '' to disable.")
    p.add_argument("--figure-tag", type=str, default="", help="Optional panel tag, e.g., 'a)'.")
    p.add_argument("--x-offset-km", type=float, default=0.0, help="Additive offset applied to x-axis ticks.")
    p.add_argument("--y-offset-km", type=float, default=0.0, help="Additive offset applied to y-axis ticks.")
    p.add_argument("--x-start-col", type=int, default=1, help="1-based starting column for spatial crop.")
    p.add_argument("--x-end-col", type=int, default=0, help="1-based ending column for spatial crop (0 = full width).")
    p.add_argument("--y-start-row", type=int, default=1, help="1-based starting row for spatial crop.")
    p.add_argument("--y-end-row", type=int, default=0, help="1-based ending row for spatial crop (0 = full height).")
    p.add_argument(
        "--title-prefix-det",
        type=str,
        default="Surface temperature - 2024 day",
        help="Deterministic title prefix. Use '' to hide title.",
    )
    p.add_argument(
        "--title-prefix-norm",
        type=str,
        default="Normalized surface temperature - 2024 day",
        help="Normalized title prefix. Use '' to hide title.",
    )
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


def build_1based_crop_slice(start_1b: int, end_1b: int, limit: int, axis_name: str) -> Tuple[slice, int, int]:
    start = max(1, int(start_1b))
    end = int(limit) if int(end_1b) <= 0 else min(int(limit), int(end_1b))
    if start > end:
        raise RuntimeError(
            f"Invalid crop for {axis_name}: start={start_1b}, end={end_1b}, "
            f"resolved_start={start}, resolved_end={end}, limit={limit}"
        )
    return slice(start - 1, end), start, end


def render_field(
    arr: np.ndarray,
    out_png: Path,
    title: str,
    cbar_label: str,
    vmin: float,
    vmax: float,
    extent: List[float],
    cmap_name: str,
    x_label: str,
    y_label: str,
    unit_tag: str,
    figure_tag: str,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if unit_tag.strip():
        ax.text(1.005, -0.04, unit_tag, transform=ax.transAxes, ha="left", va="top")
        ax.text(-0.055, -0.01, unit_tag, transform=ax.transAxes, ha="right", va="top")
    if figure_tag.strip():
        ax.text(-0.18, 1.04, figure_tag, transform=ax.transAxes, fontsize=18, fontweight="bold")
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
    x_label: str,
    y_label: str,
    unit_tag: str,
    figure_tag: str,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for z in range(z_start, z_end + 1):
        arr = x_stack[z - 1].copy()
        if mask_common is not None:
            arr[~mask_common] = np.nan

        out_png = out_dir / f"{fname_prefix}{z:03d}.png"
        title = f"{title_prefix} z={z:03d}" if title_prefix.strip() else ""
        render_field(
            arr=arr,
            out_png=out_png,
            title=title,
            cbar_label=cbar_label,
            vmin=vmin,
            vmax=vmax,
            extent=extent,
            cmap_name=cmap_name,
            x_label=x_label,
            y_label=y_label,
            unit_tag=unit_tag,
            figure_tag=figure_tag,
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
                "x_axis_label": x_label,
                "y_axis_label": y_label,
                "unit_tag": unit_tag,
                "figure_tag": figure_tag,
                "georef_note": GEOREF_NOTE,
            }
        )
    return rows


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
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
    in_scale_temp = resolve_existing(IN_SCALE_TEMP_CANDIDATES)
    in_scale_norm = resolve_existing(IN_SCALE_NORM_CANDIDATES)

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

    scale_temp = load_json(in_scale_temp)
    scale_norm = load_json(in_scale_norm)
    vmin_temp = float(scale_temp["vmin"])
    vmax_temp = float(scale_temp["vmax"])
    vmin_norm = float(scale_norm["vmin"])
    vmax_norm = float(scale_norm["vmax"])

    bbox = find_hres_bbox(NETCDF_SUMMARY)
    full_ny, full_nx = int(x_surface.shape[1]), int(x_surface.shape[2])
    full_x_km, full_y_km, km_meta = build_relative_km_axes(nx=full_nx, ny=full_ny, bbox=bbox)
    x_slice, x_start, x_end = build_1based_crop_slice(args.x_start_col, args.x_end_col, full_nx, "x")
    y_slice, y_start, y_end = build_1based_crop_slice(args.y_start_row, args.y_end_row, full_ny, "y")

    x_surface = x_surface[:, y_slice, x_slice]
    x_norm = x_norm[:, y_slice, x_slice]
    mask_common = mask_common[y_slice, x_slice]

    ny, nx = int(x_surface.shape[1]), int(x_surface.shape[2])
    x_km = full_x_km[x_slice] + float(args.x_offset_km)
    y_km = full_y_km[y_slice] + float(args.y_offset_km)
    extent = [float(x_km.min()), float(x_km.max()), float(y_km.min()), float(y_km.max())]

    x_label = args.x_label
    y_label = args.y_label
    unit_tag = args.unit_tag
    figure_tag = args.figure_tag

    out_det = out_root / "deterministic_2024_surface_300_thesis_relative_km_display_assumed"
    out_norm = out_root / "pngs_normalized_surface_300_thesis_relative_km_display_assumed"

    det_rows = export_set(
        x_stack=x_surface,
        mask_common=None,
        out_dir=out_det,
        fname_prefix="TEMP_surface_2024_z",
        title_prefix=args.title_prefix_det,
        cbar_label="Temperature (degC)",
        cmap_name="viridis",
        vmin=vmin_temp,
        vmax=vmax_temp,
        extent=extent,
        z_start=z_start,
        z_end=z_end,
        value_prefix="temp",
        x_label=x_label,
        y_label=y_label,
        unit_tag=unit_tag,
        figure_tag=figure_tag,
    )
    norm_rows = export_set(
        x_stack=x_norm,
        mask_common=mask_common,
        out_dir=out_norm,
        fname_prefix="X_surface_norm_z",
        title_prefix=args.title_prefix_norm,
        cbar_label="Normalized temperature (-)",
        cmap_name="coolwarm",
        vmin=vmin_norm,
        vmax=vmax_norm,
        extent=extent,
        z_start=z_start,
        z_end=z_end,
        value_prefix="norm",
        x_label=x_label,
        y_label=y_label,
        unit_tag=unit_tag,
        figure_tag=figure_tag,
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
            "unit_tag",
            "figure_tag",
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
            "unit_tag",
            "figure_tag",
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
            "deterministic_scale": to_rel(in_scale_temp),
            "normalized_scale": to_rel(in_scale_norm),
            "netcdf_summary": to_rel(NETCDF_SUMMARY),
        },
        "axis_mode": {
            "x_axis_label": x_label,
            "y_axis_label": y_label,
            "unit_tag": unit_tag,
            "figure_tag": figure_tag,
            "mode": "relative_km_display_assumed_from_hres_bbox",
            "independent_validation_status": "not_independently_validated",
            "note": GEOREF_NOTE,
        },
        "crop": {
            "x_start_col_1based": int(x_start),
            "x_end_col_1based": int(x_end),
            "y_start_row_1based": int(y_start),
            "y_end_row_1based": int(y_end),
            "full_shape_ny_nx": [int(full_ny), int(full_nx)],
            "cropped_shape_ny_nx": [int(ny), int(nx)],
        },
        "axis_offsets_km": {
            "x_offset_km": float(args.x_offset_km),
            "y_offset_km": float(args.y_offset_km),
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
        f"- X: `{x_label}`",
        f"- Y: `{y_label}`",
        f"- Unit tag: `{unit_tag}`",
        f"- Figure tag: `{figure_tag}`",
        "",
        "## Method",
        "- Source bbox from `results/netcdf_files_summary.csv` (HRes row).",
        "- Converted deg-per-cell to km-per-cell at midpoint latitude.",
        "- Built relative axes from origin `(0,0)` plus optional axis offsets.",
        f"- Cropped grid: x={x_start}..{x_end}, y={y_start}..{y_end} (1-based).",
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

