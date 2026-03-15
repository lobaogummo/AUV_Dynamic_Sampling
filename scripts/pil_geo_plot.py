"""Lightweight geographic heatmap renderer using Pillow (matplotlib-free fallback)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _interp_colors(vals: np.ndarray, anchors: Iterable[Tuple[float, Tuple[int, int, int]]]) -> np.ndarray:
    pts = sorted(list(anchors), key=lambda x: x[0])
    x = np.asarray([p[0] for p in pts], dtype=np.float64)
    c = np.asarray([p[1] for p in pts], dtype=np.float64)
    vals = np.nan_to_num(vals, nan=0.0, posinf=1.0, neginf=0.0)
    vals = np.clip(vals, 0.0, 1.0)
    out = np.zeros((vals.size, 3), dtype=np.float64)
    for k in range(3):
        out[:, k] = np.interp(vals, x, c[:, k])
    return out.astype(np.uint8)


def _cmap_rgb(norm01: np.ndarray, cmap_name: str) -> np.ndarray:
    if cmap_name == "coolwarm":
        anchors = [
            (0.0, (59, 76, 192)),
            (0.25, (120, 160, 225)),
            (0.5, (221, 221, 221)),
            (0.75, (243, 152, 121)),
            (1.0, (180, 4, 38)),
        ]
    else:  # viridis-like
        anchors = [
            (0.0, (68, 1, 84)),
            (0.25, (59, 82, 139)),
            (0.5, (33, 145, 140)),
            (0.75, (94, 201, 98)),
            (1.0, (253, 231, 37)),
        ]
    flat = _interp_colors(norm01.reshape(-1), anchors)
    return flat.reshape(norm01.shape + (3,))


def _format_num(v: float) -> str:
    if abs(v) >= 100:
        return f"{v:.1f}"
    return f"{v:.3f}"


def save_geo_heatmap_png(
    arr: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    vmin: float,
    vmax: float,
    title: str,
    xlabel: str,
    ylabel: str,
    cbar_label: str,
    out_path: Path,
    cmap_name: str = "viridis",
) -> None:
    arr = np.asarray(arr, dtype=np.float64)
    lon = np.asarray(lon, dtype=np.float64)
    lat = np.asarray(lat, dtype=np.float64)

    h, w = arr.shape
    scale = 4
    map_w = w * scale
    map_h = h * scale

    left = 120
    right = 120
    top = 58
    bottom = 74
    bar_w = 18
    bar_pad = 20

    img_w = left + map_w + bar_pad + bar_w + right
    img_h = top + map_h + bottom

    norm = (arr - vmin) / (vmax - vmin + 1e-12)
    rgb = _cmap_rgb(np.clip(norm, 0.0, 1.0), cmap_name)
    rgb[~np.isfinite(arr)] = np.array([255, 255, 255], dtype=np.uint8)

    # Match matplotlib(origin="lower"): first row of array must appear at the bottom.
    rgb_plot = np.flipud(rgb)
    field = Image.fromarray(rgb_plot, mode="RGB").resize((map_w, map_h), resample=Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    x0 = left
    y0 = top
    x1 = x0 + map_w
    y1 = y0 + map_h
    canvas.paste(field, (x0, y0))
    draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=1)

    # X ticks (longitude)
    for i in range(5):
        fx = i / 4.0
        xx = int(round(x0 + fx * map_w))
        vv = float(np.nanmin(lon) + fx * (np.nanmax(lon) - np.nanmin(lon)))
        txt = _format_num(vv)
        draw.line([(xx, y1), (xx, y1 + 5)], fill=(0, 0, 0), width=1)
        tw = draw.textlength(txt, font=font)
        draw.text((xx - tw / 2, y1 + 8), txt, fill=(0, 0, 0), font=font)

    # Y ticks (latitude)
    for i in range(5):
        fy = i / 4.0
        yy = int(round(y1 - fy * map_h))
        vv = float(np.nanmin(lat) + fy * (np.nanmax(lat) - np.nanmin(lat)))
        txt = _format_num(vv)
        draw.line([(x0 - 5, yy), (x0, yy)], fill=(0, 0, 0), width=1)
        tw = draw.textlength(txt, font=font)
        draw.text((x0 - 8 - tw, yy - 6), txt, fill=(0, 0, 0), font=font)

    # Labels and title
    title_w = draw.textlength(title, font=font)
    draw.text(((img_w - title_w) / 2, 14), title, fill=(0, 0, 0), font=font)

    xlabel_w = draw.textlength(xlabel, font=font)
    draw.text((x0 + (map_w - xlabel_w) / 2, img_h - 24), xlabel, fill=(0, 0, 0), font=font)
    ylab_bbox = draw.textbbox((0, 0), ylabel, font=font)
    ylab_w = int(ylab_bbox[2] - ylab_bbox[0])
    ylab_h = int(ylab_bbox[3] - ylab_bbox[1])
    ylab_img = Image.new("RGBA", (ylab_w + 6, ylab_h + 6), (255, 255, 255, 0))
    ylab_draw = ImageDraw.Draw(ylab_img)
    ylab_draw.text((3, 3), ylabel, fill=(0, 0, 0, 255), font=font)
    ylab_rot = ylab_img.rotate(90, expand=True)
    ylab_x = 8
    ylab_y = int(y0 + (map_h - ylab_rot.height) / 2)
    canvas.paste(ylab_rot, (ylab_x, ylab_y), ylab_rot)

    # Colorbar
    bx0 = x1 + bar_pad
    bx1 = bx0 + bar_w
    by0 = y0
    by1 = y1
    bar_vals = np.linspace(1.0, 0.0, map_h, dtype=np.float64).reshape(map_h, 1)
    bar_rgb = _cmap_rgb(bar_vals, cmap_name).repeat(bar_w, axis=1)
    bar = Image.fromarray(bar_rgb.astype(np.uint8), mode="RGB")
    canvas.paste(bar, (bx0, by0))
    draw.rectangle([bx0, by0, bx1, by1], outline=(0, 0, 0), width=1)

    for i in range(5):
        fy = i / 4.0
        yy = int(round(by1 - fy * map_h))
        vv = float(vmin + fy * (vmax - vmin))
        txt = _format_num(vv)
        draw.line([(bx1, yy), (bx1 + 5, yy)], fill=(0, 0, 0), width=1)
        draw.text((bx1 + 8, yy - 6), txt, fill=(0, 0, 0), font=font)

    draw.text((bx0 - 8, by0 - 18), cbar_label, fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
