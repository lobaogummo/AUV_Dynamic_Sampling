#!/usr/bin/env python
"""Export individual PNG assets for the editable Lucid/draw.io regime diagram."""

from __future__ import annotations

from pathlib import Path
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTDIR = ROOT / "docs" / "figures" / "regime_inference_assets"

STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP05 = RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260605_141912"

ROI_SHAPE = (72, 117)
PATCH_H = 24
PATCH_W = 40
TEMP_CMAP = "coolwarm"


def robust_limits(arrays: list[np.ndarray], p_lo: float = 2, p_hi: float = 98) -> tuple[float, float]:
    vals = []
    for arr in arrays:
        a = np.asarray(arr, dtype=float)
        vals.append(a[np.isfinite(a)])
    flat = np.concatenate([v for v in vals if v.size])
    lo = float(np.nanpercentile(flat, p_lo))
    hi = float(np.nanpercentile(flat, p_hi))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = float(np.nanmin(flat)), float(np.nanmax(flat))
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def render_array(
    arr: np.ndarray,
    path: Path,
    cmap_name: str,
    vmin: float | None,
    vmax: float | None,
    mask: np.ndarray | None = None,
    size: tuple[int, int] = (420, 260),
    border: str | None = None,
) -> Image.Image:
    a = np.asarray(arr, dtype=float)
    invalid = ~np.isfinite(a)
    if mask is not None and mask.shape == a.shape:
        invalid = invalid | ~mask.astype(bool)
    finite = a[np.isfinite(a)]
    if finite.size == 0:
        a = np.zeros_like(a)
        vmin, vmax = 0.0, 1.0
    if vmin is None:
        vmin = float(np.nanmin(finite))
    if vmax is None:
        vmax = float(np.nanmax(finite))
    if vmax <= vmin:
        vmax = vmin + 1.0
    norm = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    rgba = (plt.get_cmap(cmap_name)(norm) * 255).astype(np.uint8)
    rgba[invalid] = np.array([255, 255, 255, 255], dtype=np.uint8)
    img = Image.fromarray(rgba, mode="RGBA").resize(size, Image.Resampling.BILINEAR)
    if border:
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, size[0] - 1, size[1] - 1], outline=border, width=4)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img


def save_roi_with_patch_overlay(
    arr: np.ndarray,
    path: Path,
    vmin: float,
    vmax: float,
    mask: np.ndarray,
    patch_positions: list[tuple[int, int]],
) -> None:
    img = render_array(arr, path, TEMP_CMAP, vmin, vmax, mask, size=(520, 340), border="#7E57C2")
    draw = ImageDraw.Draw(img)
    for i, (rr, cc) in enumerate(patch_positions, start=1):
        x0 = int(cc / ROI_SHAPE[1] * img.width)
        y0 = int((ROI_SHAPE[0] - rr - PATCH_H) / ROI_SHAPE[0] * img.height)
        x1 = int((cc + PATCH_W) / ROI_SHAPE[1] * img.width)
        y1 = int((ROI_SHAPE[0] - rr) / ROI_SHAPE[0] * img.height)
        draw.rectangle([x0, y0, x1, y1], outline="#F97316", width=5)
        draw.text((x0 + 6, y0 + 5), str(i), fill="#7C2D12")
    img.save(path)


def save_code_matrix(codes: np.ndarray, path: Path) -> None:
    daily = np.nanmean(np.abs(codes), axis=1).T
    daily = daily[:, :: max(1, daily.shape[1] // 92)]
    render_array(daily, path, "magma", None, None, None, size=(640, 220), border="#6B46C1")


def save_dendrogram_placeholder(path: Path) -> None:
    img = Image.new("RGBA", (420, 300), "#FFFBEA")
    draw = ImageDraw.Draw(img)
    brown = "#92400E"
    leaves = [45, 105, 165, 225, 285, 345]
    base = 250
    for i, x in enumerate(leaves, start=1):
        draw.text((x - 16, 260), f"C{i:02d}", fill="#111827")
    def line(points):
        draw.line(points, fill=brown, width=5, joint="curve")
    line([(leaves[0], base), (leaves[0], 170), (leaves[1], 170), (leaves[1], base)])
    line([(leaves[2], base), (leaves[2], 150), (leaves[3], 150), (leaves[3], base)])
    line([(leaves[4], base), (leaves[4], 125), (leaves[5], 125), (leaves[5], base)])
    line([(75, 170), (75, 80), (195, 80), (195, 150)])
    line([(195, 80), (195, 45), (315, 45), (315, 125)])
    draw.rectangle([0, 0, img.width - 1, img.height - 1], outline="#B7791F", width=4)
    img.save(path)


def save_class_size_bars(path: Path) -> None:
    import pandas as pd
    df = pd.read_csv(STEP05 / "canonical_class_members_summary.csv")
    vals = df["n_days"].astype(float).to_numpy()
    img = Image.new("RGBA", (420, 300), "#FFFBEA")
    draw = ImageDraw.Draw(img)
    max_v = float(vals.max())
    x0 = 45
    for i, v in enumerate(vals, start=1):
        x = x0 + (i - 1) * 58
        h = int(v / max_v * 190)
        draw.rectangle([x, 240 - h, x + 34, 240], fill="#F59E0B", outline="#92400E", width=3)
        draw.text((x + 2, 250), f"C{i}", fill="#111827")
    draw.rectangle([0, 0, img.width - 1, img.height - 1], outline="#B7791F", width=4)
    img.save(path)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    temp = np.load(STEP00 / "X_surface_370_roi_x490.npy", mmap_mode="r")
    temp_norm = np.load(STEP00 / "X_surface_370_roi_x490_norm.npy", mmap_mode="r")
    mask = np.load(STEP00 / "mask_common_roi_x490.npy").astype(bool)
    prototypes = np.load(STEP05 / "canonical_prototypes.npy")
    atom_components = np.load(STEP05 / "canonical_dictionary.npz", allow_pickle=True)["components"]
    atoms = atom_components[:, : PATCH_H * PATCH_W].reshape(4, PATCH_H, PATCH_W)
    codes = np.load(STEP05 / "canonical_sparse_codes.npz", allow_pickle=True)["sparse_codes"]

    temp_indices = [0, 120, 240, 301]
    temp_vmin, temp_vmax = robust_limits([np.asarray(temp[i]) for i in temp_indices])
    norm_vmin, norm_vmax = robust_limits([np.asarray(temp_norm[i]) for i in temp_indices])
    proto_vmin, proto_vmax = robust_limits([prototypes[i] for i in range(6)])
    atom_lim = float(np.nanpercentile(np.abs(atoms[np.isfinite(atoms)]), 98)) or 1.0

    manifest = []

    def record(path: Path, role: str) -> None:
        manifest.append({"file": str(path.relative_to(ROOT)), "role": role})

    for idx, label in zip(temp_indices, ["day001", "day121", "day241", "day302"]):
        p = OUTDIR / f"01_temperature_{label}.png"
        render_array(np.asarray(temp[idx]), p, TEMP_CMAP, temp_vmin, temp_vmax, mask, border="#2B6CB0")
        record(p, f"370 daily surface temperature thumbnail: {label}")

    p = OUTDIR / "02_standardized_map_day302.png"
    render_array(np.asarray(temp_norm[301]), p, TEMP_CMAP, norm_vmin, norm_vmax, mask, border="#2B6CB0")
    record(p, "standardized map thumbnail")

    base = np.asarray(temp_norm[301])
    patch_positions = [(24, 0), (24, 25), (24, 50), (24, 77)]
    p = OUTDIR / "03_roi_image_day302.png"
    render_array(base, p, TEMP_CMAP, norm_vmin, norm_vmax, mask, size=(520, 340), border="#6B46C1")
    record(p, "ROI image without patch overlay")

    p = OUTDIR / "03_roi_image_day302_patch_overlay.png"
    save_roi_with_patch_overlay(base, p, norm_vmin, norm_vmax, mask, patch_positions)
    record(p, "ROI image with numbered left-to-right patch overlay")

    for i, (rr, cc) in enumerate(patch_positions, start=1):
        p = OUTDIR / f"04_patch_{i}_40x24.png"
        render_array(base[rr : rr + PATCH_H, cc : cc + PATCH_W], p, TEMP_CMAP, norm_vmin, norm_vmax, None, size=(260, 170), border="#F97316")
        record(p, f"ordered extracted patch {i}")

    for i, atom in enumerate(atoms, start=1):
        p = OUTDIR / f"05_dictionary_atom_{i}.png"
        render_array(atom, p, TEMP_CMAP, -atom_lim, atom_lim, None, size=(260, 170), border="#6B46C1")
        record(p, f"real learned dictionary atom {i}, temperature-like half")

    p = OUTDIR / "06_sparse_code_activity.png"
    save_code_matrix(codes, p)
    record(p, "sparse code activity matrix")

    p = OUTDIR / "07_ward_dendrogram_schematic.png"
    save_dendrogram_placeholder(p)
    record(p, "Ward clustering dendrogram schematic")

    p = OUTDIR / "08_class_size_bars.png"
    save_class_size_bars(p)
    record(p, "six-class size bar chart")

    for i in range(6):
        p = OUTDIR / f"09_prototype_C{i+1:02d}.png"
        render_array(prototypes[i], p, TEMP_CMAP, proto_vmin, proto_vmax, mask, border="#2F855A")
        record(p, f"prototype class C{i+1:02d}")

    descriptor_specs = [
        ("10_descriptor_boundary.png", "boundary_score", "step08_descriptor_boundary_map.npy", "magma"),
        ("10_descriptor_boundary_distance_r3.png", "boundary_distance_score_r3_cells", "step08_descriptor_boundary_distance_score_r3_cells.npy", "magma"),
        ("10_descriptor_interest.png", "interest_map", "step08_descriptor_interest_map.npy", "inferno"),
        ("10_descriptor_representative_zone.png", "representative_zone", "step08_descriptor_representative_zone_map.npy", "Greens"),
        ("10_descriptor_cold_region.png", "cold_region", "step08_descriptor_cold_region_map.npy", "Blues"),
        ("10_descriptor_warm_region.png", "warm_region", "step08_descriptor_warm_region_map.npy", "Reds"),
    ]
    for filename, role, npy, cmap in descriptor_specs:
        arr = np.load(STEP08 / npy)[0]
        p = OUTDIR / filename
        render_array(arr, p, cmap, 0, 1, mask, border="#C53030")
        record(p, role)

    import pandas as pd
    pd.DataFrame(manifest).to_csv(OUTDIR / "asset_manifest.csv", index=False)
    print(OUTDIR)
    print(OUTDIR / "asset_manifest.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
