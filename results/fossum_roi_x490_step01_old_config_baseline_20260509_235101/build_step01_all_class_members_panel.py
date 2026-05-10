"""Build one all-members panel grouped by Step01 Fossum baseline class."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = Path(__file__).resolve().parent
STEP00_DIR = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"

IN_X_NORM = STEP00_DIR / "X_surface_370_roi_x490_norm.npy"
IN_MASK = STEP00_DIR / "mask_common_roi_x490.npy"
IN_CLEAN_PNG_DIR = STEP00_DIR / "normalized_clean_pngs"
IN_ASSIGNMENTS = RUN_DIR / "step01_old_config_assignments.csv"
OUT_PANEL = RUN_DIR / "step01_old_config_all_class_members_panel.png"
OUT_PANEL_CLEAN = RUN_DIR / "step01_old_config_all_class_members_panel_clean.png"
OUT_META = RUN_DIR / "step01_old_config_all_class_members_panel_metadata.json"


def load_oriented_thumb(day_index: int, date: str, thumb_w: int, thumb_h: int) -> Image.Image:
    """Load the Step00 clean PNG, preserving the proven Matplotlib orientation."""
    pattern = f"{day_index:04d}_{date}_X_surface_370_roi_x490_norm_clean.png"
    path = IN_CLEAN_PNG_DIR / pattern
    if not path.exists():
        raise FileNotFoundError(f"Missing correctly oriented Step00 clean PNG: {path}")
    with Image.open(path) as im:
        return im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.BILINEAR)


def draw_colorbar(draw: ImageDraw.ImageDraw, x0: int, y0: int, w: int, h: int, vmin: float, vmax: float, font: ImageFont.ImageFont) -> None:
    cmap = plt.get_cmap("coolwarm")
    for i in range(w):
        value = i / max(1, w - 1)
        rgb = tuple(int(c * 255) for c in cmap(value)[:3])
        draw.line([(x0 + i, y0), (x0 + i, y0 + h)], fill=rgb)
    draw.rectangle([x0, y0, x0 + w, y0 + h], outline=(90, 90, 90), width=1)
    draw.text((x0, y0 + h + 4), f"{vmin:.2f}", fill=(30, 30, 30), font=font)
    vmax_text = f"{vmax:.2f}"
    bbox = draw.textbbox((0, 0), vmax_text, font=font)
    draw.text((x0 + w - (bbox[2] - bbox[0]), y0 + h + 4), vmax_text, fill=(30, 30, 30), font=font)
    draw.text((x0 + w // 2 - 55, y0 + h + 4), "normalized TEMP", fill=(30, 30, 30), font=font)


def build_panel(clean: bool = False) -> tuple[Image.Image, dict]:
    X = np.load(IN_X_NORM).astype(np.float32, copy=False)
    mask = np.load(IN_MASK).astype(bool, copy=False)
    assignments = pd.read_csv(IN_ASSIGNMENTS)
    valid = X[:, mask]
    max_abs = float(np.percentile(np.abs(valid[np.isfinite(valid)]), 98.0))
    vmin, vmax = -max_abs, max_abs

    cols = 20
    thumb_w, thumb_h = (116, 82) if clean else (122, 88)
    label_h = 14 if clean else 20
    gap = 8
    margin = 24
    header_h = 36 if clean else 52
    top_h = 48 if clean else 86
    section_gap = 18
    panel_w = margin * 2 + cols * thumb_w + (cols - 1) * gap

    class_ids = sorted(assignments["class_id"].unique().tolist())
    section_heights = []
    for cid in class_ids:
        n = int((assignments["class_id"] == cid).sum())
        rows = int(np.ceil(n / cols))
        section_heights.append(header_h + rows * (thumb_h + label_h + gap) + section_gap)
    panel_h = top_h + sum(section_heights) + margin

    canvas = Image.new("RGB", (panel_w, panel_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()

    title = "Seed 11 - all class members (FRESNEL ROI x490 Step01 baseline)"
    draw.text((margin, 18), title, fill=(0, 0, 0), font=title_font)
    draw.text(
        (margin, 38),
        f"patch=72x40 | dictionary=4 | scaler=ON | SD fraction=0.30 | n={len(assignments)}",
        fill=(40, 40, 40),
        font=font,
    )
    if not clean:
        draw_colorbar(draw, panel_w - margin - 360, 18, 330, 16, vmin, vmax, font)

    y = top_h
    metadata_rows = []
    for cid in class_ids:
        sub = assignments[assignments["class_id"] == cid].sort_values("day_index").reset_index(drop=True)
        n = int(len(sub))
        rows = int(np.ceil(n / cols))
        draw.text((margin, y), f"class_{cid:02d}, n={n}", fill=(0, 0, 0), font=title_font)
        y += header_h
        for k, row in sub.iterrows():
            r = k // cols
            c = k % cols
            x = margin + c * (thumb_w + gap)
            yy = y + r * (thumb_h + label_h + gap)
            idx = int(row["image_idx_0_based"])
            thumb = load_oriented_thumb(int(row["day_index"]), str(row["date"]), thumb_w, thumb_h)
            canvas.paste(thumb, (x, yy))
            draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline=(190, 190, 190), width=1)
            label = f"z={int(row['day_index']):03d}" if clean else f"z={int(row['day_index']):03d} {str(row['date'])[5:]}"
            draw.text((x + 2, yy + thumb_h + 2), label, fill=(20, 20, 20), font=font)
            metadata_rows.append(
                {
                    "class_id": int(cid),
                    "day_index": int(row["day_index"]),
                    "date": str(row["date"]),
                    "image_idx_0_based": idx,
                    "panel_x": int(x),
                    "panel_y": int(yy),
                }
            )
        y += rows * (thumb_h + label_h + gap) + section_gap

    meta = {
        "input_assignments": str(IN_ASSIGNMENTS),
        "input_x_norm": str(IN_X_NORM),
        "input_mask": str(IN_MASK),
        "input_oriented_clean_png_dir": str(IN_CLEAN_PNG_DIR),
        "output_panel": str(OUT_PANEL if not clean else OUT_PANEL_CLEAN),
        "n_images": int(len(assignments)),
        "class_sizes": {f"class_{int(cid):02d}": int((assignments["class_id"] == cid).sum()) for cid in class_ids},
        "columns": int(cols),
        "thumbnail_size": [int(thumb_w), int(thumb_h)],
        "color_scale_method": "symmetric +/- p98(abs(X_norm[:, mask_common]))",
        "orientation_source": "Step00 normalized_clean_pngs generated with matplotlib imshow(origin='lower')",
        "vmin": float(vmin),
        "vmax": float(vmax),
        "all_days_included": bool(len(metadata_rows) == len(assignments)),
        "placements": metadata_rows,
    }
    return canvas, meta


def main() -> None:
    panel, meta = build_panel(clean=False)
    panel.save(OUT_PANEL)
    clean_panel, clean_meta = build_panel(clean=True)
    clean_panel.save(OUT_PANEL_CLEAN)
    meta["clean_output_panel"] = str(OUT_PANEL_CLEAN)
    meta["clean_thumbnail_size"] = clean_meta["thumbnail_size"]
    OUT_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] wrote={OUT_PANEL}")
    print(f"[OK] wrote={OUT_PANEL_CLEAN}")
    print(f"[OK] n_images={meta['n_images']}")
    print(f"[OK] class_sizes={meta['class_sizes']}")


if __name__ == "__main__":
    main()
