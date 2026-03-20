"""Diagnose ICV run-to-run variance visibility for Fossum patch-size sensitivity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RUNS_CSV = ROOT / "results" / "fossum" / "patch_size_sensitivity_fossum" / "runs.csv"
OUT_TABLE = ROOT / "results" / "fossum" / "patch_size_sensitivity_fossum" / "debug_variance_table.csv"
OUT_PLOTS = ROOT / "results" / "fossum" / "patch_size_sensitivity_fossum" / "debug_plots"


SEED_COLORS = {
    11: (31, 119, 180),
    23: (255, 127, 14),
    37: (44, 160, 44),
    53: (214, 39, 40),
    71: (148, 103, 189),
}


@dataclass
class PlotCanvas:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    font: ImageFont.ImageFont
    title_font: ImageFont.ImageFont
    x0: int
    y0: int
    x1: int
    y1: int


def log(msg: str) -> None:
    print(f"[icv-diagnose] {msg}")


def _make_canvas(title: str, width: int = 1500, height: int = 900) -> PlotCanvas:
    left, right, top, bottom = 120, 80, 90, 120
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    tw = draw.textlength(title, font=title_font)
    draw.text(((width - tw) / 2, 28), title, fill=(0, 0, 0), font=title_font)
    return PlotCanvas(img, draw, font, title_font, left, top, width - right, height - bottom)


def _safe_range(vmin: float, vmax: float, pad_frac: float = 0.05) -> Tuple[float, float]:
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        return 0.0, 1.0
    if vmin == vmax:
        eps = 1.0 if vmin == 0 else abs(vmin) * 0.1
        return vmin - eps, vmax + eps
    pad = (vmax - vmin) * pad_frac
    return vmin - pad, vmax + pad


def _y_to_px(y: float, y_min: float, y_max: float, y0: int, y1: int) -> int:
    frac = (y - y_min) / (y_max - y_min + 1e-12)
    return int(round(y1 - frac * (y1 - y0)))


def _draw_axes(
    c: PlotCanvas,
    x_labels: List[str],
    y_min: float,
    y_max: float,
    y_label: str,
    x_label: str = "Patch size (w x h)",
) -> List[int]:
    d = c.draw
    d.rectangle([c.x0, c.y0, c.x1, c.y1], outline=(0, 0, 0), width=1)

    # Y ticks
    for i in range(6):
        frac = i / 5.0
        yv = y_min + frac * (y_max - y_min)
        yy = _y_to_px(yv, y_min, y_max, c.y0, c.y1)
        d.line([(c.x0 - 6, yy), (c.x0, yy)], fill=(0, 0, 0), width=1)
        txt = f"{yv:.3f}"
        tw = d.textlength(txt, font=c.font)
        d.text((c.x0 - 10 - tw, yy - 6), txt, fill=(0, 0, 0), font=c.font)
        d.line([(c.x0, yy), (c.x1, yy)], fill=(230, 230, 230), width=1)

    n = len(x_labels)
    xs = []
    for i, lbl in enumerate(x_labels):
        xx = int(round(c.x0 + (i + 0.5) * (c.x1 - c.x0) / n))
        xs.append(xx)
        d.line([(xx, c.y1), (xx, c.y1 + 6)], fill=(0, 0, 0), width=1)
        tw = d.textlength(lbl, font=c.font)
        d.text((xx - tw / 2, c.y1 + 14), lbl, fill=(0, 0, 0), font=c.font)

    # Axis labels
    tw = d.textlength(x_label, font=c.font)
    d.text((c.x0 + (c.x1 - c.x0 - tw) / 2, c.y1 + 56), x_label, fill=(0, 0, 0), font=c.font)
    d.text((12, c.y0 + (c.y1 - c.y0) / 2), y_label, fill=(0, 0, 0), font=c.font)
    return xs


def _save(c: PlotCanvas, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c.image.save(path, format="PNG")


def classify_spread(abs_spread: float, rel_spread: float) -> str:
    if abs_spread <= 1e-12 or rel_spread <= 1e-8:
        return "numerically_zero_or_negligible"
    if rel_spread <= 0.005:
        return "small_but_nonzero"
    return "meaningful"


def build_variance_table(runs_ok: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = runs_ok.groupby(["patch_w", "patch_h"], as_index=False)
    for _, sub in grouped:
        pw = int(sub["patch_w"].iloc[0])
        ph = int(sub["patch_h"].iloc[0])
        ordered = sub.sort_values("seed")
        vals = ordered["mean_icv"].to_numpy(dtype=float)
        mean_val = float(np.mean(vals))
        mn = float(np.min(vals))
        mx = float(np.max(vals))
        abs_spread = float(mx - mn)
        rel_spread = float(abs_spread / mean_val) if mean_val != 0 else np.nan
        rows.append(
            {
                "patch_w": pw,
                "patch_h": ph,
                "patch_label": f"{pw}x{ph}",
                "seeds": ",".join(str(int(s)) for s in ordered["seed"].tolist()),
                "mean_icv_values": "|".join(f"{v:.12f}" for v in vals.tolist()),
                "mean_icv_min": mn,
                "mean_icv_max": mx,
                "absolute_spread": abs_spread,
                "relative_spread": rel_spread,
                "relative_spread_pct": rel_spread * 100.0 if np.isfinite(rel_spread) else np.nan,
                "spread_classification": classify_spread(abs_spread, rel_spread),
            }
        )
    out = pd.DataFrame(rows).sort_values(["patch_w", "patch_h"]).reset_index(drop=True)
    return out


def plot_seed_points(runs_ok: pd.DataFrame, out_path: Path) -> None:
    grouped = runs_ok.groupby(["patch_w", "patch_h"], as_index=False)
    labels, values = [], []
    for _, sub in grouped:
        pw = int(sub["patch_w"].iloc[0])
        ph = int(sub["patch_h"].iloc[0])
        labels.append(f"{pw}x{ph}")
        values.append(sub.sort_values("seed")[["seed", "mean_icv"]].to_records(index=False))

    all_y = np.concatenate([np.array([v[1] for v in arr], dtype=float) for arr in values])
    y_min, y_max = _safe_range(float(np.min(all_y)), float(np.max(all_y)), pad_frac=0.03)
    c = _make_canvas("ICV seed points by patch size")
    xs = _draw_axes(c, labels, y_min, y_max, y_label="Mean ICV")

    for i, arr in enumerate(values):
        xc = xs[i]
        for j, (seed, val) in enumerate(arr):
            jitter = int((j - (len(arr) - 1) / 2) * 7)
            yy = _y_to_px(float(val), y_min, y_max, c.y0, c.y1)
            color = SEED_COLORS.get(int(seed), (0, 0, 0))
            c.draw.ellipse([xc + jitter - 4, yy - 4, xc + jitter + 4, yy + 4], fill=color, outline=color)
        mean_val = float(np.mean([v[1] for v in arr]))
        yy = _y_to_px(mean_val, y_min, y_max, c.y0, c.y1)
        c.draw.line([(xc - 20, yy), (xc + 20, yy)], fill=(0, 0, 0), width=2)

    _save(c, out_path)


def plot_line_metric(df: pd.DataFrame, y_col: str, title: str, y_label: str, out_path: Path) -> None:
    labels = df["patch_label"].tolist()
    y = df[y_col].to_numpy(dtype=float)
    y_min, y_max = _safe_range(float(np.min(y)), float(np.max(y)), pad_frac=0.08)
    c = _make_canvas(title)
    xs = _draw_axes(c, labels, y_min, y_max, y_label=y_label)

    pts = []
    for i, yi in enumerate(y):
        xx = xs[i]
        yy = _y_to_px(float(yi), y_min, y_max, c.y0, c.y1)
        pts.append((xx, yy))
        c.draw.ellipse([xx - 4, yy - 4, xx + 4, yy + 4], fill=(31, 119, 180), outline=(31, 119, 180))

    if len(pts) >= 2:
        c.draw.line(pts, fill=(31, 119, 180), width=2)
    _save(c, out_path)


def plot_boxplot_zoom(runs_ok: pd.DataFrame, out_path: Path) -> None:
    grouped = runs_ok.groupby(["patch_w", "patch_h"], as_index=False)
    labels = []
    centered: List[np.ndarray] = []
    for _, sub in grouped:
        pw = int(sub["patch_w"].iloc[0])
        ph = int(sub["patch_h"].iloc[0])
        labels.append(f"{pw}x{ph}")
        vals = sub.sort_values("seed")["mean_icv"].to_numpy(dtype=float)
        centered.append(vals - float(np.mean(vals)))

    all_y = np.concatenate(centered)
    # Zoom to typical spread: robust window to avoid one large outlier hiding small variations.
    q95 = float(np.percentile(np.abs(all_y), 95.0))
    y_lim = max(2.0, q95 * 1.25)
    y_min, y_max = -y_lim, y_lim
    c = _make_canvas("Fig6a zoom (robust): mean ICV centered by patch-size mean")
    xs = _draw_axes(c, labels, y_min, y_max, y_label="mean_icv - patch_mean_icv")

    for i, vals in enumerate(centered):
        xc = xs[i]
        q1, q2, q3 = np.percentile(vals, [25, 50, 75])
        vmin, vmax = float(np.min(vals)), float(np.max(vals))
        y_q1 = _y_to_px(float(np.clip(q1, y_min, y_max)), y_min, y_max, c.y0, c.y1)
        y_q2 = _y_to_px(float(np.clip(q2, y_min, y_max)), y_min, y_max, c.y0, c.y1)
        y_q3 = _y_to_px(float(np.clip(q3, y_min, y_max)), y_min, y_max, c.y0, c.y1)
        y_vmin = _y_to_px(float(np.clip(vmin, y_min, y_max)), y_min, y_max, c.y0, c.y1)
        y_vmax = _y_to_px(float(np.clip(vmax, y_min, y_max)), y_min, y_max, c.y0, c.y1)

        box_w = 24
        c.draw.rectangle([xc - box_w, y_q3, xc + box_w, y_q1], outline=(0, 0, 0), width=2, fill=(224, 236, 255))
        c.draw.line([(xc - box_w, y_q2), (xc + box_w, y_q2)], fill=(0, 0, 0), width=2)
        c.draw.line([(xc, y_vmax), (xc, y_q3)], fill=(0, 0, 0), width=1)
        c.draw.line([(xc, y_q1), (xc, y_vmin)], fill=(0, 0, 0), width=1)
        c.draw.line([(xc - 10, y_vmax), (xc + 10, y_vmax)], fill=(0, 0, 0), width=1)
        c.draw.line([(xc - 10, y_vmin), (xc + 10, y_vmin)], fill=(0, 0, 0), width=1)

        for j, v in enumerate(vals):
            jitter = int((j - (len(vals) - 1) / 2) * 6)
            yy = _y_to_px(float(np.clip(v, y_min, y_max)), y_min, y_max, c.y0, c.y1)
            c.draw.ellipse([xc + jitter - 3, yy - 3, xc + jitter + 3, yy + 3], fill=(214, 39, 40), outline=(214, 39, 40))

    _save(c, out_path)


def main() -> None:
    if not RUNS_CSV.exists():
        raise FileNotFoundError(RUNS_CSV)
    OUT_PLOTS.mkdir(parents=True, exist_ok=True)

    runs = pd.read_csv(RUNS_CSV)
    runs_ok = runs[runs["notes"] == "ok"].copy()
    if runs_ok.empty:
        raise RuntimeError("No ok runs found.")

    table = build_variance_table(runs_ok)
    table.to_csv(OUT_TABLE, index=False)
    log(f"Wrote {OUT_TABLE.relative_to(ROOT)}")

    plot_seed_points(runs_ok, OUT_PLOTS / "icv_seed_points_by_patchsize.png")
    plot_line_metric(
        table,
        y_col="absolute_spread",
        title="Absolute spread of mean ICV across seeds",
        y_label="Absolute spread (max - min)",
        out_path=OUT_PLOTS / "icv_absolute_spread_vs_patchsize.png",
    )
    plot_line_metric(
        table,
        y_col="relative_spread_pct",
        title="Relative spread of mean ICV across seeds",
        y_label="Relative spread (%)",
        out_path=OUT_PLOTS / "icv_relative_spread_vs_patchsize.png",
    )
    plot_boxplot_zoom(runs_ok, OUT_PLOTS / "fig6a_icv_boxplot_patchsize_zoom.png")
    log(f"Wrote plots in {OUT_PLOTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
