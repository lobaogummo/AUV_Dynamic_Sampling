"""Regenerate tempIBHRes-derived figures with indexed-axis labels.

This script only updates presentation outputs (labels/captions/metadata).
It does not change clustering, prototypes, planner logic, or scientific core data.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

IN_X_SURFACE = ROOT / "results" / "plots" / "X_surface_300.npy"
IN_X_SURFACE_NORM = ROOT / "results" / "plots" / "X_surface_300_norm.npy"
IN_MASK_COMMON = ROOT / "results" / "plots" / "mask_common.npy"

IN_COLOR_SCALE_TEMP = ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis" / "color_scale.json"
IN_COLOR_SCALE_NORM = ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis" / "color_scale_norm.json"

IN_VAL_HRES_MANIFEST = ROOT / "results" / "validation_hres_surface_comparison_20260405_130636" / "manifest.json"
IN_VAL_VIS_MANIFEST = ROOT / "results" / "validation_visual_data_branches_20260405_193102" / "manifest.json"

IN_VAL_HRES_PANELS = ROOT / "results" / "validation_hres_surface_comparison_20260405_130636" / "panels"
IN_VAL_VIS_PANELS = ROOT / "results" / "validation_visual_data_branches_20260405_193102" / "panels"

X_LABEL = "X index"
Y_LABEL = "Y index"
INDEXED_COORD_NOTE = (
    "Figures derived from tempIBHRes2024_* are shown in indexed grid coordinates (X index, Y index), "
    "since independently verified native georeferencing of this reduced product is not established "
    "in the current repository state."
)


def to_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fix tempIBHRes figure labels to indexed axes.")
    p.add_argument(
        "--tag",
        type=str,
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Suffix used in output folder naming.",
    )
    return p.parse_args()


def read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_index_extent(scale_payload: Dict) -> Tuple[float, float, float, float]:
    coord = scale_payload.get("coord_source", {})
    try:
        nx = int(scale_payload.get("nx", coord.get("target_nx")))
        ny = int(scale_payload.get("ny", coord.get("target_ny")))
    except Exception as exc:
        raise RuntimeError(f"Missing nx/ny in scale payload: {scale_payload}") from exc
    return 1.0, float(nx), 1.0, float(ny)


def write_csv(path: Path, rows: Sequence[Dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def render_map(
    arr: np.ndarray,
    out_path: Path,
    title: str,
    cbar_label: str,
    vmin: float,
    vmax: float,
    extent: Tuple[float, float, float, float],
    cmap_name: str,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, extent=extent, aspect="auto")
    ax.set_title(title)
    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(Y_LABEL)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def regenerate_deterministic_set(
    x_surface: np.ndarray,
    scale_payload: Dict,
    out_dir: Path,
) -> List[Dict[str, object]]:
    vmin = float(scale_payload["vmin"])
    vmax = float(scale_payload["vmax"])
    extent = load_index_extent(scale_payload)

    rows: List[Dict[str, object]] = []
    for z in range(1, int(x_surface.shape[0]) + 1):
        arr = x_surface[z - 1]
        out_png = out_dir / f"TEMP_surface_2024_z{z:03d}.png"
        render_map(
            arr=arr,
            out_path=out_png,
            title=f"Surface temperature - 2024 day z={z:03d}",
            cbar_label="Temperature (degC)",
            vmin=vmin,
            vmax=vmax,
            extent=extent,
            cmap_name="viridis",
        )
        finite = np.isfinite(arr)
        rows.append(
            {
                "z": int(z),
                "filepath": to_rel(out_png),
                "x_index_min": float(extent[0]),
                "x_index_max": float(extent[1]),
                "y_index_min": float(extent[2]),
                "y_index_max": float(extent[3]),
                "mean_temp": float(np.nanmean(arr)),
                "std_temp": float(np.nanstd(arr)),
                "min_temp": float(np.nanmin(arr)),
                "max_temp": float(np.nanmax(arr)),
                "missing_fraction": float(1.0 - (float(np.count_nonzero(finite)) / float(arr.size))),
                "x_axis_label": X_LABEL,
                "y_axis_label": Y_LABEL,
                "georef_note": INDEXED_COORD_NOTE,
            }
        )
    return rows


def regenerate_normalized_set(
    x_surface_norm: np.ndarray,
    mask_common: np.ndarray,
    scale_payload: Dict,
    out_dir: Path,
) -> List[Dict[str, object]]:
    vmin = float(scale_payload["vmin"])
    vmax = float(scale_payload["vmax"])
    extent = load_index_extent(scale_payload)

    rows: List[Dict[str, object]] = []
    for z in range(1, int(x_surface_norm.shape[0]) + 1):
        arr = x_surface_norm[z - 1].copy()
        arr[~mask_common] = np.nan
        out_png = out_dir / f"X_surface_norm_z{z:03d}.png"
        render_map(
            arr=arr,
            out_path=out_png,
            title=f"Normalized surface temperature - 2024 day z={z:03d}",
            cbar_label="Normalized temperature (-)",
            vmin=vmin,
            vmax=vmax,
            extent=extent,
            cmap_name="coolwarm",
        )
        vals = arr[np.isfinite(arr)]
        rows.append(
            {
                "z": int(z),
                "filepath": to_rel(out_png),
                "x_index_min": float(extent[0]),
                "x_index_max": float(extent[1]),
                "y_index_min": float(extent[2]),
                "y_index_max": float(extent[3]),
                "mean_norm": float(np.mean(vals)),
                "std_norm": float(np.std(vals)),
                "min_norm": float(np.min(vals)),
                "max_norm": float(np.max(vals)),
                "x_axis_label": X_LABEL,
                "y_axis_label": Y_LABEL,
                "georef_note": INDEXED_COORD_NOTE,
            }
        )
    return rows


def regenerate_validation_tempibhres_examples(
    x_surface: np.ndarray,
    scale_payload_temp: Dict,
    out_root: Path,
) -> List[Dict[str, object]]:
    extent = load_index_extent(scale_payload_temp)
    hres_manifest = read_json(IN_VAL_HRES_MANIFEST)
    vis_manifest = read_json(IN_VAL_VIS_MANIFEST)

    hres_vmin = float(hres_manifest["color_scale"]["vmin"])
    hres_vmax = float(hres_manifest["color_scale"]["vmax"])
    vis_vmin = float(vis_manifest["scale"]["thermal_vmin"])
    vis_vmax = float(vis_manifest["scale"]["thermal_vmax"])

    rows: List[Dict[str, object]] = []
    steps = [13, 14, 15]

    out_hres_dir = out_root / "validation_hres_surface_comparison_tempIBHRes"
    out_vis_dir = out_root / "validation_visual_data_branches_tempIBHRes"

    for step in steps:
        arr = x_surface[step - 1]

        out_hres_png = out_hres_dir / f"tempIBHRes2024_1_z{step:03d}.png"
        render_map(
            arr=arr,
            out_path=out_hres_png,
            title=f"tempIBHRes2024_1 | z={step:03d}",
            cbar_label="Temperature (degC)",
            vmin=hres_vmin,
            vmax=hres_vmax,
            extent=extent,
            cmap_name="viridis",
        )
        rows.append(
            {
                "family": "validation_hres_surface_comparison",
                "step": int(step),
                "filepath": to_rel(out_hres_png),
                "vmin": hres_vmin,
                "vmax": hres_vmax,
                "x_axis_label": X_LABEL,
                "y_axis_label": Y_LABEL,
                "georef_note": INDEXED_COORD_NOTE,
            }
        )

        out_vis_png = out_vis_dir / f"tempIBHRes2024_1_step{step:03d}.png"
        render_map(
            arr=arr,
            out_path=out_vis_png,
            title=f"tempIBHRes2024_1 | temp | step {step}",
            cbar_label="value",
            vmin=vis_vmin,
            vmax=vis_vmax,
            extent=extent,
            cmap_name="turbo",
        )
        rows.append(
            {
                "family": "validation_visual_data_branches",
                "step": int(step),
                "filepath": to_rel(out_vis_png),
                "vmin": vis_vmin,
                "vmax": vis_vmax,
                "x_axis_label": X_LABEL,
                "y_axis_label": Y_LABEL,
                "georef_note": INDEXED_COORD_NOTE,
            }
        )

    return rows


def build_panel_caption_overrides(out_root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for panel in sorted(IN_VAL_HRES_PANELS.glob("panel_compare_step_*.png")):
        rows.append(
            {
                "panel_path": to_rel(panel),
                "caption_override": INDEXED_COORD_NOTE,
                "scope": "applies to tempIBHRes subplot in this comparative panel",
            }
        )
    for panel in sorted(IN_VAL_VIS_PANELS.glob("panel_thermal_step_*.png")):
        rows.append(
            {
                "panel_path": to_rel(panel),
                "caption_override": INDEXED_COORD_NOTE,
                "scope": "applies to tempIBHRes subplot in this comparative panel",
            }
        )

    out_csv = out_root / "comparison_panel_caption_overrides.csv"
    write_csv(out_csv, rows, ["panel_path", "caption_override", "scope"])
    return rows


def main() -> None:
    args = parse_args()
    out_root = ROOT / "results" / "plots" / f"tempibhres_indexed_axes_fix_{args.tag}"
    out_root.mkdir(parents=True, exist_ok=True)

    if not IN_X_SURFACE.exists() or not IN_X_SURFACE_NORM.exists() or not IN_MASK_COMMON.exists():
        raise FileNotFoundError("Missing one or more required plot arrays in results/plots/")
    if not IN_COLOR_SCALE_TEMP.exists() or not IN_COLOR_SCALE_NORM.exists():
        raise FileNotFoundError("Missing official color scale JSON files.")

    x_surface = np.load(IN_X_SURFACE).astype(np.float32, copy=False)
    x_surface_norm = np.load(IN_X_SURFACE_NORM).astype(np.float32, copy=False)
    mask_common = np.load(IN_MASK_COMMON).astype(bool, copy=False)
    if x_surface.shape != x_surface_norm.shape:
        raise RuntimeError(f"Shape mismatch between X_surface and X_surface_norm: {x_surface.shape} vs {x_surface_norm.shape}")
    if mask_common.shape != x_surface.shape[1:]:
        raise RuntimeError(f"mask_common shape mismatch: {mask_common.shape} vs {x_surface.shape[1:]}")

    scale_temp = read_json(IN_COLOR_SCALE_TEMP)
    scale_norm = read_json(IN_COLOR_SCALE_NORM)

    out_det = out_root / "deterministic_2024_surface_300_thesis_indexed_axes"
    out_norm = out_root / "pngs_normalized_surface_300_thesis_indexed_axes"
    out_validation = out_root / "validation_tempIBHRes_examples_indexed_axes"

    det_rows = regenerate_deterministic_set(x_surface=x_surface, scale_payload=scale_temp, out_dir=out_det)
    norm_rows = regenerate_normalized_set(
        x_surface_norm=x_surface_norm,
        mask_common=mask_common,
        scale_payload=scale_norm,
        out_dir=out_norm,
    )
    val_rows = regenerate_validation_tempibhres_examples(
        x_surface=x_surface,
        scale_payload_temp=scale_temp,
        out_root=out_validation,
    )
    panel_rows = build_panel_caption_overrides(out_root=out_root)

    write_csv(
        out_det / "index.csv",
        det_rows,
        [
            "z",
            "filepath",
            "x_index_min",
            "x_index_max",
            "y_index_min",
            "y_index_max",
            "mean_temp",
            "std_temp",
            "min_temp",
            "max_temp",
            "missing_fraction",
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
            "x_index_min",
            "x_index_max",
            "y_index_min",
            "y_index_max",
            "mean_norm",
            "std_norm",
            "min_norm",
            "max_norm",
            "x_axis_label",
            "y_axis_label",
            "georef_note",
        ],
    )
    write_csv(
        out_validation / "tempibhres_validation_examples_index.csv",
        val_rows,
        ["family", "step", "filepath", "vmin", "vmax", "x_axis_label", "y_axis_label", "georef_note"],
    )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "output_root": to_rel(out_root),
        "input_arrays": {
            "x_surface": to_rel(IN_X_SURFACE),
            "x_surface_norm": to_rel(IN_X_SURFACE_NORM),
            "mask_common": to_rel(IN_MASK_COMMON),
        },
        "source_scales": {
            "deterministic_color_scale": to_rel(IN_COLOR_SCALE_TEMP),
            "normalized_color_scale": to_rel(IN_COLOR_SCALE_NORM),
        },
        "axis_convention": {
            "x_axis_label": X_LABEL,
            "y_axis_label": Y_LABEL,
            "georef_mode": "indexed_grid_from_gslib_xy",
            "georef_note": INDEXED_COORD_NOTE,
        },
        "counts": {
            "deterministic_pngs": len(det_rows),
            "normalized_pngs": len(norm_rows),
            "validation_tempibhres_pngs": len(val_rows),
            "panel_caption_overrides": len(panel_rows),
        },
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[OK] output_root={out_root}")
    print(f"[OK] deterministic_pngs={len(det_rows)}")
    print(f"[OK] normalized_pngs={len(norm_rows)}")
    print(f"[OK] validation_tempibhres_pngs={len(val_rows)}")
    print(f"[OK] panel_caption_overrides={len(panel_rows)}")


if __name__ == "__main__":
    main()
