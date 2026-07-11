#!/usr/bin/env python
"""Create a thesis-ready planning-day inference and reward-map diagram.

The figure explains how day-specific TEMPpred and STD maps are combined with
the offline prototype/descriptor library to produce planner-ready reward maps.
It is a post-processing/documentation script only; it does not rerun planners.
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
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

STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP11Y = RESULTS / "fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260605_143425"
ASSETS = ROOT / "docs" / "figures" / "regime_inference_assets"

TEMP_CMAP = "coolwarm"
STD_CMAP = "viridis"
DESCRIPTOR_CMAP = "magma"
MASK_CMAP = "Blues"

COLORS = {
    "inputs": ("#EAF4FF", "#3B82C4"),
    "class": ("#F1E8FF", "#7C3AED"),
    "library": ("#EAFBF0", "#2F855A"),
    "reward": ("#FFF3D6", "#C27A13"),
    "planner": ("#EEF4FA", "#526B84"),
    "neutral": ("#FFFFFF", "#CBD5E1"),
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wrap(text: str, width: int) -> str:
    out: list[str] = []
    for part in text.splitlines():
        out.extend(textwrap.wrap(part, width=width, break_long_words=False) or [""])
    return "\n".join(out)


def normalize01(arr: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    data = np.asarray(arr, dtype=float).copy()
    valid = np.isfinite(data)
    if mask is not None and mask.shape == data.shape:
        valid &= mask.astype(bool)
    if not np.any(valid):
        return np.zeros_like(data, dtype=float)
    lo = float(np.nanpercentile(data[valid], 2))
    hi = float(np.nanpercentile(data[valid], 98))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo = float(np.nanmin(data[valid]))
        hi = float(np.nanmax(data[valid]))
    if hi <= lo:
        hi = lo + 1.0
    out = (data - lo) / (hi - lo)
    out = np.clip(out, 0, 1)
    out[~valid] = np.nan
    return out


def synthetic_heatmap(seed: int, shape: tuple[int, int] = (72, 117)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0 : shape[0], 0 : shape[1]]
    field = (
        0.55 * np.sin(x / 24.0)
        + 0.35 * np.cos(y / 18.0)
        + 0.28 * np.sin((x + y) / 31.0)
        + 0.05 * rng.standard_normal(shape)
    )
    return normalize01(field)


def load_inputs() -> tuple[dict[str, Any], list[str]]:
    """Load real maps when available; return data and source notes."""
    missing: list[str] = []
    data: dict[str, Any] = {}

    mask_path = STEP00 / "mask_common_roi_x490.npy"
    temp_path = STEP00 / "X_surface_370_roi_x490.npy"
    dates_path = STEP00 / "dates_370.csv"
    bathy_path = STEP00 / "BATHY_roi_x490.npy"

    mask = np.load(mask_path) if mask_path.exists() else None
    if mask is None:
        missing.append(f"common ROI mask not found: {rel(mask_path)}")
    data["mask"] = mask

    day_index = 0
    planning_date = "2024-08-24"
    if temp_path.exists() and dates_path.exists():
        dates = pd.read_csv(dates_path)
        if "date" in dates.columns and planning_date in set(dates["date"].astype(str)):
            day_index = int(dates.loc[dates["date"].astype(str) == planning_date, "time_index"].iloc[0])
        else:
            missing.append(f"planning date {planning_date} not found in {rel(dates_path)}; using first day")
        stack = np.load(temp_path, mmap_mode="r")
        temp = np.asarray(stack[day_index], dtype=float)
    else:
        missing.append(f"TEMPpred stack or dates not found: {rel(temp_path)}, {rel(dates_path)}")
        temp = synthetic_heatmap(10)
    data["temppred"] = temp
    data["temppred_norm"] = normalize01(temp, mask)
    data["planning_date"] = planning_date
    data["day_index"] = day_index

    if bathy_path.exists():
        bathy = np.load(bathy_path)
        data["mask_visual"] = normalize01(-bathy, mask)
    elif mask is not None:
        data["mask_visual"] = mask.astype(float)
        missing.append(f"bathymetry not found: {rel(bathy_path)}")
    else:
        data["mask_visual"] = synthetic_heatmap(20)

    def load_step11y(name: str, fallback_seed: int) -> np.ndarray:
        path = STEP11Y / name
        if path.exists():
            arr = np.load(path)
            if arr.ndim == 3:
                return np.asarray(arr[0], dtype=float)
            return np.asarray(arr, dtype=float)
        missing.append(f"Step11Y map not found: {rel(path)}")
        return synthetic_heatmap(fallback_seed)

    std = load_step11y("prototype_based_baseline_STD_norm.npy", 30)
    descriptor = load_step11y("prototype_based_boundary_distance_score_r3_cells_norm.npy", 31)
    interest = load_step11y("prototype_based_interest_map_norm.npy", 32)
    rep = load_step11y("prototype_based_representative_zone_norm.npy", 33)
    region_a = load_step11y("prototype_based_AUV1_region_map.npy", 34)
    region_b = load_step11y("prototype_based_AUV2_region_map.npy", 35)

    data["std_norm"] = normalize01(std, mask)
    data["descriptor_norm"] = normalize01(descriptor, mask)
    data["interest_norm"] = normalize01(interest, mask)
    data["representative_norm"] = normalize01(rep, mask)
    data["region_a"] = normalize01(region_a, mask)
    data["region_b"] = normalize01(region_b, mask)
    enriched = 0.5 * data["std_norm"] + 0.5 * data["descriptor_norm"]
    data["enriched_reward"] = normalize01(enriched, mask)
    data["multi_auv1_reward"] = normalize01(0.7 * data["std_norm"] + 0.3 * data["region_a"], mask)
    data["multi_auv2_reward"] = normalize01(0.7 * data["std_norm"] + 0.3 * data["region_b"], mask)

    return data, missing


def add_section(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    kind: str,
    dashed: bool = False,
) -> None:
    face, edge = COLORS[kind]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.03,rounding_size=0.13",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.45,
        linestyle=(0, (5, 3)) if dashed else "solid",
        zorder=0,
    )
    ax.add_patch(patch)
    ax.text(
        x + 0.14,
        y + h - 0.25,
        title,
        ha="left",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#0F172A",
        zorder=5,
    )


def add_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    kind: str = "neutral",
    fontsize: float = 9.2,
    bold: bool = False,
    wrap_width: int = 22,
    dashed: bool = False,
) -> dict[str, float]:
    face, edge = COLORS[kind]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.08",
        facecolor=face if kind != "neutral" else "#FFFFFF",
        edgecolor=edge,
        linewidth=1.2,
        linestyle=(0, (4, 3)) if dashed else "solid",
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        wrap(text, wrap_width),
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        color="#111827",
        linespacing=1.15,
        zorder=5,
    )
    return {"x": x, "y": y, "w": w, "h": h}


def center_right(box: dict[str, float]) -> tuple[float, float]:
    return (box["x"] + box["w"], box["y"] + box["h"] / 2)


def center_left(box: dict[str, float]) -> tuple[float, float]:
    return (box["x"], box["y"] + box["h"] / 2)


def top_center(box: dict[str, float]) -> tuple[float, float]:
    return (box["x"] + box["w"] / 2, box["y"] + box["h"])


def bottom_center(box: dict[str, float]) -> tuple[float, float]:
    return (box["x"] + box["w"] / 2, box["y"])


def add_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#475569",
    linewidth: float = 1.55,
    dashed: bool = False,
    rad: float = 0.0,
    label: str | None = None,
    label_offset: tuple[float, float] = (0, 0),
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=linewidth,
        color=color,
        linestyle=(0, (4, 3)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=5,
        shrinkB=5,
        zorder=4,
    )
    ax.add_patch(arrow)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=8, color=color, zorder=6)


def image_box(
    ax,
    arr: np.ndarray,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    cmap: str,
    edge: str,
    vmin: float = 0.0,
    vmax: float = 1.0,
    label_size: float = 7.2,
) -> None:
    ax.imshow(
        np.ma.masked_invalid(arr),
        extent=(x, x + w, y, y + h),
        origin="lower",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
        zorder=2,
    )
    ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=edge, linewidth=0.9, zorder=4))
    ax.text(x + w / 2, y + h + 0.065, label, ha="center", va="bottom", fontsize=label_size, color="#111827", zorder=5)


def png_image_box(
    ax,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    edge: str,
    missing: list[str],
    label_size: float = 6.7,
) -> None:
    if path.exists():
        img = plt.imread(path)
        ax.imshow(img, extent=(x, x + w, y, y + h), origin="upper", interpolation="nearest", zorder=2)
    else:
        missing.append(f"thumbnail not found: {rel(path)}")
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#F8FAFC", edgecolor=edge, hatch="///", linewidth=0.9, zorder=2))
    ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=edge, linewidth=0.85, zorder=4))
    ax.text(x + w / 2, y + h + 0.045, label, ha="center", va="bottom", fontsize=label_size, color="#111827", zorder=5)


def draw_mini_trajectory(ax, x: float, y: float, w: float, h: float, color: str, label: str) -> None:
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#F8FAFC", edgecolor="#94A3B8", linewidth=0.8, zorder=2))
    xs = np.array([0.08, 0.22, 0.18, 0.40, 0.55, 0.48, 0.75, 0.88]) * w + x
    ys = np.array([0.18, 0.30, 0.58, 0.66, 0.44, 0.25, 0.35, 0.72]) * h + y
    ax.plot(xs, ys, color=color, linewidth=1.8, marker="o", markersize=2.2, zorder=5)
    ax.text(x + w / 2, y + h + 0.055, label, ha="center", va="bottom", fontsize=7.0, color="#111827", zorder=5)


def write_mermaid(path: Path) -> None:
    source = """flowchart LR
  subgraph A["Planning-day inputs"]
    T["TEMPpred(t)"]
    S["STD(t)"]
    M["Bathymetry / operational mask"]
    G["Nazaré Canyon ROI common grid"]
  end

  subgraph B["Class assignment"]
    B1["crop, mask, normalise"]
    B2["compare against prototype library"]
    B3["predicted class C_k"]
  end

  subgraph C["Offline library retrieval"]
    C1["prototype library C01-C06"]
    C2["descriptor library"]
    C3["prototype-derived descriptor maps for C_k"]
  end

  subgraph D["Reward-map generation"]
    D1["R_base = STD_norm"]
    D2["R_alpha = (1 - alpha) STD_norm + alpha D_norm"]
    D3["R_AUV1 = w_sigma STD_norm + w_A R_A"]
    D4["R_AUV2 = w_sigma STD_norm + w_B R_B"]
  end

  subgraph E["Planner-ready outputs"]
    E1["reward maps (.nc / .npz)"]
    E2["Lucrezia AUV planner"]
    E3["planned trajectories"]
    E4["evaluation metrics"]
    E5["baseline vs enriched comparison"]
  end

  T --> B1 --> B2 --> B3
  B3 --> C3
  C1 --> C2 --> C3
  S --> D1
  S --> D2
  C3 --> D2
  S --> D3
  S --> D4
  C3 --> D3
  C3 --> D4
  D1 --> E1
  D2 --> E1
  D3 --> E1
  D4 --> E1
  E1 --> E2 --> E3 --> E4 --> E5
"""
    path.write_text(source, encoding="utf-8")


def write_sources(path: Path, outdir: Path, missing: list[str]) -> None:
    payload = {
        "title": "Planning-day inference and reward-map generation",
        "output_folder": rel(outdir),
        "created_by": rel(Path(__file__)),
        "source_folders": {
            "Step00_dataset": rel(STEP00),
            "Step11Y_validated_planner_inputs": rel(STEP11Y),
            "offline_diagram_assets": rel(ASSETS),
        },
        "files_used": {
            "TEMPpred": rel(STEP00 / "X_surface_370_roi_x490.npy"),
            "dates": rel(STEP00 / "dates_370.csv"),
            "ROI_mask": rel(STEP00 / "mask_common_roi_x490.npy"),
            "bathymetry": rel(STEP00 / "BATHY_roi_x490.npy"),
            "STD_norm": rel(STEP11Y / "prototype_based_baseline_STD_norm.npy"),
            "boundary_distance_r3": rel(STEP11Y / "prototype_based_boundary_distance_score_r3_cells_norm.npy"),
            "interest_map": rel(STEP11Y / "prototype_based_interest_map_norm.npy"),
            "representative_zone": rel(STEP11Y / "prototype_based_representative_zone_norm.npy"),
            "region_A": rel(STEP11Y / "prototype_based_AUV1_region_map.npy"),
            "region_B": rel(STEP11Y / "prototype_based_AUV2_region_map.npy"),
            "prototype_thumbnails": rel(ASSETS / "09_prototype_C01.png") + " ... C06",
        },
        "block_meanings": [
            {
                "block": "Planning-day inputs",
                "meaning": "Day-specific TEMPpred and STD maps are prepared on the Nazaré Canyon ROI/common grid with the operational mask.",
            },
            {
                "block": "Class assignment",
                "meaning": "TEMPpred(t) is cropped, masked and normalised, then compared with the offline prototype library to assign a single regime class C_k for the planning day.",
            },
            {
                "block": "Offline library retrieval",
                "meaning": "The predicted class C_k indexes prototype-derived descriptor maps from the offline library. The descriptors are not computed from STD.",
            },
            {
                "block": "Reward-map generation",
                "meaning": "STD_norm remains the baseline reward. Descriptor maps complement STD through alpha-weighted or vehicle-specific blends.",
            },
            {
                "block": "Planner-ready outputs",
                "meaning": "Baseline, descriptor-enriched and vehicle-specific reward maps are exported to Lucrezia inputs and evaluated through trajectory and metric comparisons.",
            },
        ],
        "conceptual_constraints": [
            "TEMPpred(t) is used for class/prototype assignment only.",
            "STD(t) is the baseline uncertainty-driven reward source.",
            "Prototype-derived descriptors complement STD rather than replacing it.",
            "Regimes are class-level prototype assignments, not cell-wise labels for the planning day.",
        ],
        "missing_or_placeholder_inputs": missing,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def draw_figure(data: dict[str, Any], outdir: Path, missing: list[str]) -> None:
    fig, ax = plt.subplots(figsize=(19.2, 8.8))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 8.8)
    ax.axis("off")

    ax.text(
        10,
        8.45,
        "Planning-day inference and reward-map generation",
        ha="center",
        va="center",
        fontsize=19,
        fontweight="bold",
        color="#0F172A",
    )
    ax.text(
        10,
        8.12,
        "TEMPpred selects the prototype class; STD and prototype-derived descriptors shape planner-ready rewards.",
        ha="center",
        va="center",
        fontsize=10.8,
        color="#475569",
    )

    # Main grouped sections.
    y0, h = 0.45, 7.15
    add_section(ax, 0.25, y0, 3.25, h, "Planning-day inputs", "inputs")
    add_section(ax, 3.75, y0, 3.05, h, "Class assignment", "class")
    add_section(ax, 7.05, y0, 3.45, h, "Offline library retrieval", "library", dashed=True)
    add_section(ax, 10.75, y0, 4.65, h, "Reward-map generation", "reward")
    add_section(ax, 15.65, y0, 4.1, h, "Planner-ready outputs", "planner")

    # Block 1: inputs.
    image_box(ax, data["temppred_norm"], 0.55, 5.55, 1.24, 0.76, "TEMPpred(t)", TEMP_CMAP, "#3B82C4")
    image_box(ax, data["std_norm"], 2.00, 5.55, 1.24, 0.76, "STD(t)", STD_CMAP, "#3B82C4")
    image_box(ax, data["mask_visual"], 0.55, 4.30, 1.24, 0.76, "bathymetry / mask", MASK_CMAP, "#3B82C4")
    add_box(ax, 2.00, 4.30, 1.22, 0.76, "Nazaré ROI\ncommon grid", "inputs", fontsize=8.4, bold=True, wrap_width=12)
    add_box(
        ax,
        0.62,
        2.45,
        2.55,
        1.00,
        "Planning day\n2024-08-24\nvalid cells only",
        "neutral",
        fontsize=8.8,
        wrap_width=18,
    )
    add_box(
        ax,
        0.62,
        1.20,
        2.55,
        0.78,
        "STD remains the uncertainty baseline",
        "inputs",
        fontsize=8.8,
        bold=True,
        wrap_width=22,
    )

    # Block 2: class assignment.
    image_box(ax, data["temppred_norm"], 4.10, 5.62, 1.28, 0.78, "TEMPpred(t)", TEMP_CMAP, "#7C3AED")
    crop = add_box(ax, 4.00, 4.48, 1.48, 0.72, "crop, mask,\nnormalise", "class", fontsize=8.3, wrap_width=13)
    compare = add_box(ax, 4.00, 3.32, 1.48, 0.72, "compare against\nprototype library", "class", fontsize=8.0, wrap_width=15)
    ck = add_box(ax, 4.03, 1.83, 2.35, 0.92, "assigned class\nC_k = C01", "class", fontsize=10.0, bold=True, wrap_width=15)
    add_arrow(ax, (4.73, 5.57), (4.73, 5.23), color="#7C3AED", linewidth=1.15)
    add_arrow(ax, bottom_center(crop), top_center(compare), color="#7C3AED", linewidth=1.15)
    add_arrow(ax, bottom_center(compare), top_center(ck), color="#7C3AED", linewidth=1.15)
    add_box(
        ax,
        5.70,
        4.00,
        0.76,
        1.65,
        "one class\nper planning day",
        "neutral",
        fontsize=7.5,
        wrap_width=10,
    )

    # Block 3: offline retrieval.
    ax.text(8.78, 7.12, "Offline library from Diagram 1", ha="center", va="center", fontsize=8.6, color="#166534")
    proto_x = [7.35, 8.22, 9.09]
    proto_y = [5.72, 4.75]
    labels = ["C01", "C02", "C03", "C04", "C05", "C06"]
    for i, label in enumerate(labels):
        x = proto_x[i % 3]
        y = proto_y[i // 3]
        png_image_box(ax, ASSETS / f"09_prototype_{label}.png", x, y, 0.67, 0.46, label, "#2F855A", missing, label_size=6.0)

    add_box(ax, 7.52, 3.56, 2.68, 0.72, "descriptor library", "library", fontsize=8.8, bold=True, wrap_width=22)
    desc_text = "boundary score\nboundary distance\nrepresentative zone\ncold / warm regions\ninterest map"
    add_box(ax, 7.35, 1.45, 1.38, 1.48, desc_text, "neutral", fontsize=7.7, wrap_width=20)
    image_box(ax, data["descriptor_norm"], 8.98, 2.15, 0.86, 0.54, "boundary-dist r3", DESCRIPTOR_CMAP, "#2F855A", label_size=6.2)
    image_box(ax, data["interest_norm"], 8.98, 1.18, 0.86, 0.54, "interest map", DESCRIPTOR_CMAP, "#2F855A", label_size=6.2)
    add_arrow(ax, center_right(ck), (7.48, 3.96), color="#2F855A", linewidth=1.35, rad=-0.12)
    add_arrow(ax, (8.85, 4.72), (8.85, 4.33), color="#2F855A", linewidth=1.05)
    add_arrow(ax, (8.85, 3.50), (8.85, 2.93), color="#2F855A", linewidth=1.05)

    # Block 4: reward-map generation.
    std_thumb = (11.10, 5.52, 1.05, 0.66)
    desc_thumb = (12.55, 5.52, 1.05, 0.66)
    enrich_thumb = (14.00, 5.52, 1.05, 0.66)
    image_box(ax, data["std_norm"], *std_thumb, "STD_norm", STD_CMAP, "#C27A13")
    image_box(ax, data["descriptor_norm"], *desc_thumb, "D_norm", DESCRIPTOR_CMAP, "#C27A13")
    image_box(ax, data["enriched_reward"], *enrich_thumb, "enriched reward", "plasma", "#C27A13")
    ax.text(12.32, 5.86, "+", ha="center", va="center", fontsize=18, fontweight="bold", color="#92400E")
    add_arrow(ax, (13.66, 5.86), (13.94, 5.86), color="#92400E", linewidth=1.35)

    base = add_box(ax, 11.05, 4.35, 1.50, 0.72, "Baseline\nR_base\n= STD_norm", "reward", fontsize=8.6, bold=True, wrap_width=18)
    single = add_box(
        ax,
        12.80,
        4.22,
        2.25,
        0.98,
        "Single-AUV enriched\nR_alpha = (1 - alpha) STD_norm + alpha D_norm",
        "reward",
        fontsize=8.2,
        bold=True,
        wrap_width=28,
    )
    multi = add_box(
        ax,
        11.30,
        2.25,
        3.52,
        1.15,
        "Multi-AUV vehicle-specific\nR_AUV1 = w_sigma STD_norm + w_A R_A\nR_AUV2 = w_sigma STD_norm + w_B R_B",
        "reward",
        fontsize=8.0,
        bold=True,
        wrap_width=38,
    )
    add_box(
        ax,
        11.25,
        1.05,
        3.70,
        0.58,
        "Descriptors complement STD; they do not replace it.",
        "neutral",
        fontsize=8.2,
        bold=True,
        wrap_width=36,
    )
    add_arrow(ax, (11.62, 5.50), top_center(base), color="#C27A13", linewidth=1.05)
    add_arrow(ax, (12.98, 5.50), top_center(single), color="#C27A13", linewidth=1.05)
    add_arrow(ax, (11.60, 5.45), (12.25, 3.45), color="#C27A13", linewidth=1.05, rad=0.12)
    add_arrow(ax, (13.08, 5.45), (13.48, 3.45), color="#C27A13", linewidth=1.05, rad=-0.08)

    image_box(ax, data["region_a"], 11.25, 1.75, 0.54, 0.34, "R_A", "Greens", "#C27A13", label_size=5.8)
    image_box(ax, data["region_b"], 12.00, 1.75, 0.54, 0.34, "R_B", "Oranges", "#C27A13", label_size=5.8)

    # Block 5: planner-ready outputs.
    maps = add_box(
        ax,
        16.10,
        5.70,
        1.45,
        0.88,
        "reward maps\n(.nc / .npz)",
        "planner",
        fontsize=8.4,
        bold=True,
        wrap_width=16,
    )
    lucrezia = add_box(ax, 17.90, 5.70, 1.35, 0.88, "Lucrezia\nAUV planner", "planner", fontsize=8.8, bold=True, wrap_width=14)
    draw_mini_trajectory(ax, 16.10, 4.30, 1.18, 0.65, "#111827", "baseline")
    draw_mini_trajectory(ax, 17.80, 4.30, 1.18, 0.65, "#0891B2", "enriched")
    metrics = add_box(
        ax,
        16.15,
        2.65,
        2.95,
        0.95,
        "trajectory metrics\nSTD collected, regime coverage,\nIQR10, efficiency, overlap",
        "neutral",
        fontsize=7.8,
        wrap_width=32,
    )
    compare_out = add_box(
        ax,
        16.15,
        1.25,
        2.95,
        0.78,
        "Baseline vs enriched\ntrajectory comparison",
        "planner",
        fontsize=8.6,
        bold=True,
        wrap_width=26,
    )
    add_arrow(ax, (15.08, 5.86), center_left(maps), color="#526B84", linewidth=1.55)
    add_arrow(ax, center_right(maps), center_left(lucrezia), color="#526B84", linewidth=1.35)
    add_arrow(ax, bottom_center(lucrezia), (18.39, 5.02), color="#526B84", linewidth=1.10)
    add_arrow(ax, (17.90, 4.62), (17.30, 4.62), color="#526B84", linewidth=1.0)
    add_arrow(ax, (18.50, 4.27), top_center(metrics), color="#526B84", linewidth=1.10)
    add_arrow(ax, bottom_center(metrics), top_center(compare_out), color="#526B84", linewidth=1.10)

    # Main inter-block arrows.
    add_arrow(ax, (3.50, 5.92), (3.93, 5.92), color="#334155", linewidth=2.0)
    add_arrow(ax, (6.80, 4.13), (7.08, 4.13), color="#334155", linewidth=2.0)
    add_arrow(ax, (10.50, 3.95), (10.78, 3.95), color="#334155", linewidth=2.0)

    # Conceptual guardrails.
    ax.text(
        10,
        0.18,
        "Correct logic: TEMPpred(t) -> assigned class C_k -> prototype-derived descriptors; STD(t) + descriptors -> reward map -> planner.",
        ha="center",
        va="center",
        fontsize=8.8,
        color="#475569",
    )

    out_svg = outdir / "planner_inference_reward_generation_diagram.svg"
    out_png = outdir / "planner_inference_reward_generation_diagram.png"
    out_pdf = outdir / "planner_inference_reward_generation_diagram.pdf"
    fig.savefig(out_svg, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(out_pdf, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(out_png, bbox_inches="tight", pad_inches=0.08, dpi=320)
    plt.close(fig)


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = RESULTS / f"planner_inference_reward_generation_diagram_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)

    data, missing = load_inputs()
    draw_figure(data, outdir, missing)
    write_mermaid(outdir / "planner_inference_reward_generation_diagram.mmd")
    write_sources(outdir / "planner_inference_reward_generation_sources.json", outdir, missing)

    print(outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
