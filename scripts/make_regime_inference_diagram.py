#!/usr/bin/env python
"""Create an illustrated offline regime-inference pipeline diagram.

The figure is a publication-style schematic with real thumbnails from the
validated outputs. It does not rerun any experiment or modify core pipeline
scripts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTDIR = ROOT / "docs" / "figures"

STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP_CMEMS_HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
STEP_PAPER_ROI = RESULTS / "fresnel_paper_roi_x490_surface_370_20260509_180348"
STEP05 = RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260605_141912"

ROI_SHAPE = (72, 117)
PATCH_H = 24
PATCH_W = 40
TEMP_CMAP = "coolwarm"

SECTION_COLORS = {
    "data": ("#EEF6FF", "#2B6CB0"),
    "compact": ("#F1EAFF", "#6B46C1"),
    "discovery": ("#FFF7D6", "#B7791F"),
    "prototype": ("#EAFBF0", "#2F855A"),
    "descriptor": ("#FFF0F0", "#C53030"),
    "output": ("#F1F5F9", "#475569"),
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def require(path: Path, missing: list[str], label: str) -> bool:
    if path.exists():
        return True
    missing.append(f"{label}: {rel(path)}")
    return False


def load_npy(path: Path, missing: list[str], label: str, mmap: bool = False) -> np.ndarray | None:
    if not require(path, missing, label):
        return None
    return np.load(path, mmap_mode="r" if mmap else None)


def load_npz_array(path: Path, key: str, missing: list[str], label: str) -> np.ndarray | None:
    if not require(path, missing, label):
        return None
    z = np.load(path, allow_pickle=True)
    if key not in z.files:
        missing.append(f"{label} key `{key}` missing in {rel(path)}")
        return None
    return z[key]


def masked(arr: np.ndarray, mask: np.ndarray | None = None) -> np.ma.MaskedArray:
    data = np.asarray(arr, dtype=float)
    invalid = ~np.isfinite(data)
    if mask is not None and mask.shape == data.shape:
        invalid = invalid | ~mask.astype(bool)
    return np.ma.array(data, mask=invalid)


def robust_limits(arrays: list[np.ndarray], p_lo: float = 2, p_hi: float = 98) -> tuple[float, float]:
    vals = []
    for arr in arrays:
        a = np.asarray(arr, dtype=float)
        vals.append(a[np.isfinite(a)])
    flat = np.concatenate([v for v in vals if v.size])
    if flat.size == 0:
        return 0.0, 1.0
    lo = float(np.nanpercentile(flat, p_lo))
    hi = float(np.nanpercentile(flat, p_hi))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = float(np.nanmin(flat)), float(np.nanmax(flat))
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def add_section(ax, x: float, y: float, w: float, h: float, title: str, color_key: str) -> None:
    face, edge = SECTION_COLORS[color_key]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.08",
        linewidth=1.3,
        edgecolor=edge,
        facecolor=face,
        zorder=0,
    )
    ax.add_patch(patch)
    ax.text(x + 0.08, y + h - 0.18, title, ha="left", va="center", fontsize=10.6, fontweight="bold", color="#111827")


def add_label(ax, x: float, y: float, text: str, size: float = 8.5, weight: str = "normal", color: str = "#111827") -> None:
    ax.text(x, y, text, ha="center", va="center", fontsize=size, fontweight=weight, color=color, linespacing=1.05, zorder=5)


def add_note_box(ax, x: float, y: float, w: float, h: float, text: str, edge: str, face: str = "white", size: float = 8.0) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.018,rounding_size=0.045",
            linewidth=1.05,
            edgecolor=edge,
            facecolor=face,
            zorder=2,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color="#111827", linespacing=1.08, zorder=4)


def add_arrow(ax, start: tuple[float, float], end: tuple[float, float], color: str = "#334155", rad: float = 0.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.4,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=5,
            shrinkB=5,
            zorder=6,
        )
    )


def add_small_arrow(ax, start: tuple[float, float], end: tuple[float, float], color: str = "#64748B") -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=0.8,
            color=color,
            shrinkA=2,
            shrinkB=2,
            zorder=6,
        )
    )


def image_box(
    ax,
    arr: np.ndarray,
    extent: tuple[float, float, float, float],
    cmap: str,
    label: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    mask: np.ndarray | None = None,
    edge: str = "#334155",
    interpolation: str = "nearest",
    label_size: float = 7.0,
) -> None:
    x0, x1, y0, y1 = extent
    ax.imshow(masked(arr, mask), extent=extent, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, interpolation=interpolation, zorder=2)
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, linewidth=0.9, edgecolor=edge, zorder=4))
    if label:
        ax.text((x0 + x1) / 2, y1 + 0.055, label, ha="center", va="bottom", fontsize=label_size, color="#111827", zorder=5)


def placeholder(ax, extent: tuple[float, float, float, float], label: str) -> None:
    x0, x1, y0, y1 = extent
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="#F8FAFC", edgecolor="#94A3B8", hatch="///", linewidth=0.9))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, label, ha="center", va="center", fontsize=7, color="#64748B")


def add_roi_rectangle(
    ax,
    extent: tuple[float, float, float, float],
    source_shape: tuple[int, int],
    roi_indices: dict[str, int],
    color: str = "#F97316",
) -> None:
    x0, x1, y0, y1 = extent
    nrow, ncol = source_shape
    c0 = roi_indices.get("col_min", 0)
    c1 = roi_indices.get("col_max", ncol - 1)
    r0 = roi_indices.get("row_min", 0)
    r1 = roi_indices.get("row_max", nrow - 1)
    rx0 = x0 + c0 / ncol * (x1 - x0)
    rx1 = x0 + (c1 + 1) / ncol * (x1 - x0)
    ry0 = y0 + r0 / nrow * (y1 - y0)
    ry1 = y0 + (r1 + 1) / nrow * (y1 - y0)
    ax.add_patch(Rectangle((rx0, ry0), rx1 - rx0, ry1 - ry0, fill=False, edgecolor=color, linewidth=1.15, zorder=7))


def add_grid_overlay(
    ax,
    extent: tuple[float, float, float, float],
    nx: int = 6,
    ny: int = 5,
    color: str = "#FFFFFF",
) -> None:
    x0, x1, y0, y1 = extent
    for i in range(1, nx):
        x = x0 + i / nx * (x1 - x0)
        ax.plot([x, x], [y0, y1], color=color, linewidth=0.28, alpha=0.55, zorder=5)
    for j in range(1, ny):
        y = y0 + j / ny * (y1 - y0)
        ax.plot([x0, x1], [y, y], color=color, linewidth=0.28, alpha=0.55, zorder=5)


def draw_code_matrix(ax, codes: np.ndarray | None, extent: tuple[float, float, float, float]) -> None:
    if codes is None:
        placeholder(ax, extent, "sparse\ncodes")
        return
    daily = np.nanmean(np.abs(codes), axis=1).T
    daily = daily[:, :: max(1, daily.shape[1] // 92)]
    image_box(ax, daily, extent, cmap="magma", label="sparse code activity", edge="#6B46C1", label_size=6.8)
    ax.text((extent[0] + extent[1]) / 2, extent[2] - 0.07, "4 atoms x 370 days", ha="center", va="top", fontsize=6.5, color="#475569")


def draw_dendrogram_icon(ax, x: float, y: float, w: float, h: float) -> None:
    leaves_x = np.linspace(x + 0.12, x + w - 0.12, 6)
    base = y + 0.12
    heights = [0.25, 0.36, 0.55, 0.43, 0.65]
    for i, lx in enumerate(leaves_x):
        ax.text(lx, y + 0.02, f"C{i+1:02d}", ha="center", va="bottom", fontsize=6.3)
    # Hand-drawn compact dendrogram icon, labelled as Ward clustering.
    pairs = [(0, 1, heights[0]), (2, 3, heights[1]), (4, 5, heights[2])]
    centers = []
    for a, b, hh in pairs:
        xa, xb = leaves_x[a], leaves_x[b]
        ax.plot([xa, xa, xb, xb], [base, y + hh, y + hh, base], color="#92400E", linewidth=1.25)
        centers.append((xa + xb) / 2)
    ax.plot([centers[0], centers[0], centers[1], centers[1]], [y + heights[0], y + 0.82, y + 0.82, y + heights[1]], color="#92400E", linewidth=1.25)
    ax.plot([centers[1], centers[1], centers[2], centers[2]], [y + 0.82, y + 1.05, y + 1.05, y + heights[2]], color="#92400E", linewidth=1.25)
    ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor="#B7791F", linewidth=0.9))
    add_label(ax, x + w / 2, y + h + 0.08, "Ward hierarchical clustering", size=6.9)


def class_interpretation_table(ax, x: float, y: float, w: float, h: float) -> None:
    add_note_box(
        ax,
        x,
        y,
        w,
        h,
        "Prototype interpretation\nhomogeneous\nsingle-gradient\nmulti-regime",
        edge="#2F855A",
        face="#F0FDF4",
        size=7.4,
    )


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []

    temp = load_npy(STEP00 / "X_surface_370_roi_x490.npy", missing, "370 daily temperature maps", mmap=True)
    temp_norm = load_npy(STEP00 / "X_surface_370_roi_x490_norm.npy", missing, "370 normalized temperature maps", mmap=True)
    mask = load_npy(STEP00 / "mask_common_roi_x490.npy", missing, "common valid mask")
    hres_temp = load_npy(STEP_CMEMS_HRES / "thetao_surface_370_hres.npy", missing, "CMEMS high-resolution regional surface maps", mmap=True)
    hres_mask = load_npy(STEP_CMEMS_HRES / "MASK_hres.npy", missing, "CMEMS high-resolution regional mask")
    paper_roi = load_npy(STEP_PAPER_ROI / "thetao_surface_370_hres_paper_roi_x490.npy", missing, "Filipa paper X490 ROI maps", mmap=True)
    paper_roi_meta_path = STEP_PAPER_ROI / "paper_roi_x490_metadata.json"
    if require(paper_roi_meta_path, missing, "Filipa paper ROI metadata"):
        with paper_roi_meta_path.open("r", encoding="utf-8") as f:
            paper_roi_meta = json.load(f)
    else:
        paper_roi_meta = {}
    prototypes = load_npy(STEP05 / "canonical_prototypes.npy", missing, "canonical prototypes")
    linkage = load_npy(STEP05 / "canonical_linkage.npy", missing, "canonical Ward linkage")
    atoms = load_npz_array(STEP05 / "canonical_dictionary.npz", "components", missing, "dictionary atoms")
    codes = load_npz_array(STEP05 / "canonical_sparse_codes.npz", "sparse_codes", missing, "sparse codes")
    class_sizes_path = STEP05 / "canonical_class_members_summary.csv"
    if require(class_sizes_path, missing, "class membership summary"):
        class_summary = pd.read_csv(class_sizes_path)
    else:
        class_summary = pd.DataFrame()

    descriptor_files = {
        "boundary": "step08_descriptor_boundary_map.npy",
        "boundary distance r3": "step08_descriptor_boundary_distance_score_r3_cells.npy",
        "interest": "step08_descriptor_interest_map.npy",
        "representative": "step08_descriptor_representative_zone_map.npy",
        "warm": "step08_descriptor_warm_region_map.npy",
        "cold": "step08_descriptor_cold_region_map.npy",
    }
    descriptor_cmaps = {
        "boundary": "magma",
        "boundary distance r3": "magma",
        "interest": "inferno",
        "representative": "Greens",
        "cold": "Blues",
        "warm": "Reds",
    }
    descriptors: dict[str, np.ndarray] = {}
    for name, filename in descriptor_files.items():
        arr = load_npy(STEP08 / filename, missing, f"descriptor {name}")
        if arr is not None:
            descriptors[name] = arr

    mask_arr = np.asarray(mask, dtype=bool) if mask is not None else None
    temp_examples = []
    if temp is not None:
        for idx in [0, 120, 240, 301]:
            temp_examples.append(np.asarray(temp[min(idx, temp.shape[0] - 1)]))
    if hres_temp is not None:
        for idx in [0, 120, 240, 301]:
            temp_examples.append(np.asarray(hres_temp[min(idx, hres_temp.shape[0] - 1)]))
    temp_vmin, temp_vmax = robust_limits(temp_examples or [np.zeros(ROI_SHAPE)])
    proto_vmin, proto_vmax = robust_limits([np.asarray(prototypes[i]) for i in range(min(6, prototypes.shape[0]))] if prototypes is not None else [np.zeros(ROI_SHAPE)])
    norm_examples = []
    if temp_norm is not None:
        for idx in [0, 120, 240, 301]:
            norm_examples.append(np.asarray(temp_norm[min(idx, temp_norm.shape[0] - 1)]))
    norm_vmin, norm_vmax = robust_limits(norm_examples or [np.zeros(ROI_SHAPE)])

    fig, ax = plt.subplots(figsize=(18.2, 7.9))
    ax.set_xlim(0, 18.2)
    ax.set_ylim(0, 7.9)
    ax.axis("off")

    sections = [
        (0.25, 0.5, 2.8, 6.95, "Data and preprocessing", "data"),
        (3.25, 0.5, 3.2, 6.95, "Compact representation", "compact"),
        (6.65, 0.5, 2.15, 6.95, "Regime discovery", "discovery"),
        (9.0, 0.5, 3.25, 6.95, "Prototype interpretation", "prototype"),
        (12.45, 0.5, 3.35, 6.95, "Descriptor generation", "descriptor"),
        (16.0, 0.5, 1.95, 6.95, "Planner-ready\noutputs", "output"),
    ]
    for s in sections:
        add_section(ax, *s)

    # Data and preprocessing.
    add_label(ax, 1.65, 6.93, "CMEMS regional product\nto Nazaré Canyon ROI", size=7.7, weight="bold", color="#1E3A8A")
    context_day_idx = 301
    regional_extent = (0.46, 1.12, 6.05, 6.53)
    interp_extent = (1.27, 1.93, 6.05, 6.53)
    roi_extent = (2.08, 2.74, 6.05, 6.53)
    if hres_temp is not None:
        hres_day = np.asarray(hres_temp[min(context_day_idx, hres_temp.shape[0] - 1)])
        hres_mask_arr = np.asarray(hres_mask, dtype=bool) if hres_mask is not None else None
        coarse_day = hres_day[::10, ::10]
        image_box(ax, coarse_day, regional_extent, TEMP_CMAP, vmin=temp_vmin, vmax=temp_vmax, label="CMEMS\nregional", label_size=5.9, edge="#2B6CB0")
        image_box(ax, hres_day, interp_extent, TEMP_CMAP, vmin=temp_vmin, vmax=temp_vmax, mask=hres_mask_arr, label="interpolated\nhigh-resolution", label_size=5.8, edge="#2B6CB0")
        add_grid_overlay(ax, interp_extent, nx=6, ny=5)
        roi_indices = paper_roi_meta.get("roi_indices", {})
        if roi_indices:
            add_roi_rectangle(ax, interp_extent, hres_day.shape, roi_indices)
    else:
        placeholder(ax, regional_extent, "CMEMS")
        placeholder(ax, interp_extent, "interp.")
    if paper_roi is not None:
        roi_day = np.asarray(paper_roi[min(context_day_idx, paper_roi.shape[0] - 1)])
        image_box(ax, roi_day, roi_extent, TEMP_CMAP, vmin=temp_vmin, vmax=temp_vmax, mask=mask_arr, label="Nazaré Canyon\nROI", label_size=6.1, edge="#2B6CB0")
    elif temp is not None:
        roi_day = np.asarray(temp[min(context_day_idx, temp.shape[0] - 1)])
        image_box(ax, roi_day, roi_extent, TEMP_CMAP, vmin=temp_vmin, vmax=temp_vmax, mask=mask_arr, label="Nazaré Canyon\nROI", label_size=6.1, edge="#2B6CB0")
    else:
        placeholder(ax, roi_extent, "ROI")
    add_small_arrow(ax, (1.14, 6.29), (1.25, 6.29), "#2B6CB0")
    add_small_arrow(ax, (1.95, 6.29), (2.06, 6.29), "#2B6CB0")
    add_note_box(ax, 0.48, 5.00, 2.32, 0.62, "Nazaré Canyon ROI\nsame planning domain", edge="#2B6CB0", face="#EFF6FF", size=7.0)
    if temp is not None:
        day1 = np.asarray(temp[0])
        day302 = np.asarray(temp[min(context_day_idx, temp.shape[0] - 1)])
        image_box(ax, day1, (0.66, 1.30, 4.10, 4.55), TEMP_CMAP, vmin=temp_vmin, vmax=temp_vmax, mask=mask_arr, label="day 1", label_size=5.9, edge="#2B6CB0")
        image_box(ax, day302, (1.95, 2.59, 4.10, 4.55), TEMP_CMAP, vmin=temp_vmin, vmax=temp_vmax, mask=mask_arr, label="day 302", label_size=5.9, edge="#2B6CB0")
        ax.text(1.62, 4.31, "…", ha="center", va="center", fontsize=13, color="#1E3A8A", zorder=6)
    else:
        placeholder(ax, (0.66, 2.59, 4.10, 4.55), "370 daily maps")
    add_label(ax, 1.62, 3.82, "370 daily\nsurface-temperature maps", size=7.3, weight="bold", color="#1E3A8A")
    add_note_box(ax, 0.63, 2.78, 1.95, 0.58, "common valid mask\nstandardisation", edge="#2B6CB0", face="#EFF6FF", size=7.0)
    if temp_norm is not None:
        norm_example = np.asarray(temp_norm[301 if temp_norm.shape[0] > 301 else 0])
        image_box(ax, norm_example, (0.85, 1.88, 1.70, 2.45), TEMP_CMAP, vmin=norm_vmin, vmax=norm_vmax, mask=mask_arr, label="standardised map", label_size=6.5, edge="#2B6CB0")
    else:
        placeholder(ax, (0.85, 1.88, 1.70, 2.45), "normalized")

    # Compact representation: patches, atoms, codes.
    if temp_norm is not None:
        base = np.asarray(temp_norm[301 if temp_norm.shape[0] > 301 else 0])
        roi_extent = (3.55, 4.55, 5.45, 6.20)
        image_box(ax, base, roi_extent, TEMP_CMAP, vmin=norm_vmin, vmax=norm_vmax, mask=mask_arr, label="ROI map", label_size=6.6, edge="#6B46C1")
        patch_positions = [(24, 0), (24, 25), (24, 50), (24, 77)]
        rect_centers = []
        for i, (rr, cc) in enumerate(patch_positions):
            rx = roi_extent[0] + cc / ROI_SHAPE[1] * (roi_extent[1] - roi_extent[0])
            ry = roi_extent[2] + rr / ROI_SHAPE[0] * (roi_extent[3] - roi_extent[2])
            rw = PATCH_W / ROI_SHAPE[1] * (roi_extent[1] - roi_extent[0])
            rh = PATCH_H / ROI_SHAPE[0] * (roi_extent[3] - roi_extent[2])
            ax.add_patch(Rectangle((rx, ry), rw, rh, fill=False, edgecolor="#F97316", linewidth=1.0, zorder=5))
            ax.text(rx + 0.025, ry + rh - 0.03, str(i + 1), ha="left", va="top", fontsize=5.8, color="#7C2D12", fontweight="bold", zorder=6)
            rect_centers.append((rx + rw / 2, ry + rh / 2))
        for a, b in zip(rect_centers[:-1], rect_centers[1:]):
            add_small_arrow(ax, a, b, "#F97316")
        patch_y0, patch_y1 = 4.33, 4.72
        patch_x0 = 3.45
        patch_gap = 0.13
        patch_w = 0.48
        for i, (rr, cc) in enumerate(patch_positions):
            patch = base[rr : rr + PATCH_H, cc : cc + PATCH_W]
            x = patch_x0 + i * (patch_w + patch_gap)
            image_box(ax, patch, (x, x + patch_w, patch_y0, patch_y1), TEMP_CMAP, vmin=norm_vmin, vmax=norm_vmax, label=f"patch {i+1}", edge="#F97316", label_size=5.8)
            if i < len(patch_positions) - 1:
                add_small_arrow(ax, (x + patch_w + 0.015, (patch_y0 + patch_y1) / 2), (x + patch_w + patch_gap - 0.015, (patch_y0 + patch_y1) / 2), "#F97316")
        add_label(ax, 4.57, 4.98, "Ordered patch extraction\n40 x 24", size=7.3, weight="bold", color="#6B46C1")
    else:
        placeholder(ax, (3.55, 4.55, 5.45, 6.20), "patches")
    if atoms is not None:
        # Canonical components concatenate the temperature-like patch features
        # with the valid-mask encoding. Visualize only the temperature half.
        atom_patch_size = PATCH_H * PATCH_W
        atoms_img = np.asarray(atoms)[:, :atom_patch_size].reshape((-1, PATCH_H, PATCH_W))
        atom_lim = float(np.nanpercentile(np.abs(atoms_img[np.isfinite(atoms_img)]), 98)) or 1.0
        for i in range(min(4, atoms_img.shape[0])):
            x = 3.55 + i * 0.67
            image_box(ax, atoms_img[i], (x, x + 0.54, 3.18, 3.55), TEMP_CMAP, vmin=-atom_lim, vmax=atom_lim, label=f"atom {i+1}", edge="#6B46C1", label_size=6.1)
    else:
        placeholder(ax, (3.55, 6.10, 3.18, 3.55), "dictionary\natoms")
    add_label(ax, 4.72, 3.83, "Dictionary learning\nK = 4", size=7.6, weight="bold", color="#4C1D95")
    draw_code_matrix(ax, codes, (3.70, 5.85, 1.35, 2.25))

    # Regime discovery.
    if linkage is not None:
        draw_dendrogram_icon(ax, 6.93, 4.85, 1.5, 1.35)
    else:
        placeholder(ax, (6.93, 8.43, 4.85, 6.20), "Ward\nclustering")
    if not class_summary.empty:
        sizes = class_summary["n_days"].astype(float).to_numpy()
        ax.bar(np.arange(6) * 0.21 + 7.05, sizes / max(sizes) * 0.95, width=0.13, bottom=2.65, color="#F59E0B", edgecolor="#92400E", linewidth=0.5, zorder=3)
        for i in range(6):
            ax.text(7.05 + i * 0.21, 2.52, f"C{i+1}", ha="center", va="top", fontsize=5.9)
        ax.add_patch(Rectangle((6.88, 2.43), 1.55, 1.32, fill=False, edgecolor="#B7791F", linewidth=0.9, zorder=4))
        add_label(ax, 7.65, 3.98, "Class sizes\nsix recurrent classes", size=7.3, weight="bold", color="#78350F")

    # Prototype interpretation.
    if prototypes is not None:
        for i in range(min(6, prototypes.shape[0])):
            row, col = divmod(i, 3)
            x = 9.25 + col * 0.88
            y = 5.52 - row * 1.06
            image_box(ax, np.asarray(prototypes[i]), (x, x + 0.74, y, y + 0.56), TEMP_CMAP, vmin=proto_vmin, vmax=proto_vmax, mask=mask_arr, label=f"C{i+1:02d}", label_size=6.2, edge="#2F855A")
    else:
        placeholder(ax, (9.25, 11.85, 4.42, 6.08), "C01-C06\nprototypes")
    class_interpretation_table(ax, 9.38, 2.48, 2.35, 0.96)
    add_note_box(ax, 9.38, 1.28, 2.35, 0.78, "Prototype library\nclass-level regime maps", edge="#2F855A", face="#F0FDF4", size=7.4)

    # Descriptor generation.
    desc_items = list(descriptors.items())[:6]
    for i, (name, arr) in enumerate(desc_items):
        row, col = divmod(i, 3)
        x = 12.72 + col * 0.88
        y = 5.52 - row * 1.06
        image_box(
            ax,
            np.asarray(arr[0]),
            (x, x + 0.74, y, y + 0.56),
            descriptor_cmaps.get(name, "viridis"),
            vmin=0,
            vmax=1,
            mask=mask_arr,
            label=name,
            label_size=5.9,
            edge="#C53030",
        )
    add_note_box(ax, 12.86, 2.10, 2.44, 1.05, "Boundary score\nBoundary distance r1/r3/r5\nInterest map\nRepresentative zone\nCold/warm and A/B regions", edge="#C53030", face="#FFF5F5", size=7.0)

    # Planner-ready outputs.
    add_note_box(ax, 16.23, 5.22, 1.42, 0.74, "Prototype\nlibrary", edge="#475569", face="#F8FAFC", size=7.2)
    add_note_box(ax, 16.23, 4.05, 1.42, 0.74, "Predicted\nclass", edge="#475569", face="#F8FAFC", size=7.2)
    add_note_box(ax, 16.23, 2.88, 1.42, 0.86, "Prototype-specific\ndescriptor maps", edge="#475569", face="#F8FAFC", size=6.9)
    add_note_box(ax, 16.18, 1.35, 1.52, 0.9, "Planner\nreward-map\ninputs", edge="#475569", face="#E2E8F0", size=7.1)

    # Arrows between stages.
    add_arrow(ax, (2.62, 3.84), (3.38, 5.55), "#334155", rad=-0.18)
    add_arrow(ax, (5.92, 2.00), (6.78, 5.53), "#334155", rad=-0.10)
    add_arrow(ax, (8.55, 5.52), (9.17, 5.82), "#334155")
    add_arrow(ax, (11.85, 4.68), (12.60, 5.55), "#334155", rad=-0.08)
    add_arrow(ax, (15.45, 4.68), (16.12, 3.30), "#334155", rad=-0.10)

    # Local arrows inside compact section.
    add_arrow(ax, (4.65, 4.38), (4.65, 3.62), "#6B46C1")
    add_arrow(ax, (5.02, 3.14), (5.12, 2.32), "#6B46C1")

    ax.text(
        0.35,
        0.22,
        "Offline regime-inference pipeline. Real thumbnails are used where available; descriptors shown for C01 as the boundary-rich reference class.",
        fontsize=8.5,
        color="#475569",
        ha="left",
        va="center",
    )

    for ext in ("png", "svg", "pdf"):
        kwargs: dict[str, Any] = {"bbox_inches": "tight", "pad_inches": 0.08}
        if ext == "png":
            kwargs["dpi"] = 300
        fig.savefig(OUTDIR / f"regime_inference_pipeline_diagram.{ext}", **kwargs)
    plt.close(fig)

    caption = (
        "Offline regime-inference pipeline used in this thesis. The workflow starts from CMEMS regional surface-temperature fields over a larger domain, interpolates them to the high-resolution/common grid, and then extracts the Nazaré Canyon ROI used as the common planning domain. The resulting 370 daily ROI maps are masked, standardised, decomposed into local patches, represented with a compact dictionary-learning model, and clustered with Ward hierarchical clustering to obtain six recurrent prototype classes (C01-C06). The prototypes are then interpreted as homogeneous, gradient-dominated, or multi-regime spatial patterns and converted into prototype-derived descriptors, including boundary scores, boundary-distance scores, interest maps, representative zones, and cold/warm or region_A/region_B maps. These offline products define the prototype library, predicted-class interface, and prototype-specific descriptor maps used later for planner reward-map construction."
    )
    if missing:
        caption += "\n\nPlaceholder note: the following expected inputs were missing and were replaced by schematic placeholders: " + "; ".join(missing)
    else:
        caption += "\n\nAll illustrated thumbnails were generated from existing validated outputs; no expensive experiment was rerun."
    (OUTDIR / "regime_inference_pipeline_caption.txt").write_text(caption + "\n", encoding="utf-8")
    note = (
        "Regime inference pipeline diagram revision note\n"
        "\n"
        "Dictionary atoms: the four atom thumbnails are the real learned atoms from the validated canonical Step05 output "
        "`canonical_dictionary.npz`, key `components` (shape 4 x 1920). Each learned component concatenates a 40 x 24 temperature-like patch field and a 40 x 24 valid-mask encoding; the diagram visualizes the temperature-like half as four learned atom fields. They are not schematic placeholders.\n"
        "\n"
        "Colormap: temperature-like fields now use the same `coolwarm` colormap used by the 370 daily surface-temperature map exports and canonical prototype visualizations. This applies to the ROI map, standardised map, extracted patches, prototype thumbnails, and dictionary atoms. Descriptor maps use descriptor-appropriate sequential colormaps: magma for boundary/boundary-distance, inferno for interest, Greens for representative zone, Blues for cold region, and Reds for warm region.\n"
        "\n"
        "Patch extraction panel: the patch thumbnails now follow a left-to-right spatial extraction sequence from the ROI image. Four patch rectangles are drawn on the ROI image, numbered 1-4, with subtle arrows indicating the extraction order; the thumbnails below are the corresponding real 40 x 24 patches in the same order.\n"
        "\n"
        "Data-origin panel: the first block now explicitly shows the upstream data chain: CMEMS regional surface-temperature field over a larger domain, interpolation to the high-resolution/common grid, and extraction of the Nazaré Canyon ROI before building the 370 daily ROI map stack.\n"
    )
    (OUTDIR / "regime_inference_pipeline_revision_note.txt").write_text(note, encoding="utf-8")
    (OUTDIR / "regime_inference_pipeline_sources.json").write_text(
        json.dumps(
            {
                "step00": rel(STEP00),
                "cmems_hres": rel(STEP_CMEMS_HRES),
                "fresnel_paper_roi_x490": rel(STEP_PAPER_ROI),
                "step05": rel(STEP05),
                "step08": rel(STEP08),
                "temperature_colormap": TEMP_CMAP,
                "dictionary_atoms": {
                    "source": rel(STEP05 / "canonical_dictionary.npz"),
                    "key": "components",
                    "shape": list(atoms.shape) if atoms is not None else None,
                    "visualized_slice": f"components[:, :{PATCH_H * PATCH_W}]",
                    "visualized_as": [4, PATCH_H, PATCH_W] if atoms is not None else None,
                },
                "missing_inputs": missing,
                "outputs": {
                    "png": rel(OUTDIR / "regime_inference_pipeline_diagram.png"),
                    "svg": rel(OUTDIR / "regime_inference_pipeline_diagram.svg"),
                    "pdf": rel(OUTDIR / "regime_inference_pipeline_diagram.pdf"),
                    "caption": rel(OUTDIR / "regime_inference_pipeline_caption.txt"),
                    "revision_note": rel(OUTDIR / "regime_inference_pipeline_revision_note.txt"),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(OUTDIR / "regime_inference_pipeline_diagram.png")
    print(OUTDIR / "regime_inference_pipeline_diagram.svg")
    print(OUTDIR / "regime_inference_pipeline_diagram.pdf")
    print(OUTDIR / "regime_inference_pipeline_caption.txt")
    print(OUTDIR / "regime_inference_pipeline_revision_note.txt")
    if missing:
        print("Missing inputs:")
        for item in missing:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
