#!/usr/bin/env python
"""Create a thesis methodology diagram as editable SVG/PDF plus PNG."""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "docs"


COLORS = {
    "data": ("#DCEEFF", "#2B6CB0"),
    "regime": ("#E9DDFF", "#6B46C1"),
    "descriptor": ("#FFF1CC", "#B7791F"),
    "planner": ("#DDF7E7", "#2F855A"),
    "evaluation": ("#FFE3E0", "#C53030"),
    "future": ("#F1F5F9", "#64748B"),
    "section": ("#F8FAFC", "#CBD5E1"),
}


def wrap(label: str, width: int = 18) -> str:
    lines: list[str] = []
    for part in label.splitlines():
        lines.extend(textwrap.wrap(part, width=width, break_long_words=False) or [""])
    return "\n".join(lines)


def add_box(ax, xy, wh, label, kind, fontsize=9.3, bold=False, radius=0.045, wrap_width=18):
    x, y = xy
    w, h = wh
    face, edge = COLORS[kind]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.018,rounding_size={radius}",
        linewidth=1.4,
        facecolor=face,
        edgecolor=edge,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        wrap(label, width=wrap_width),
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        color="#111827",
        linespacing=1.18,
        zorder=4,
    )
    return {"x": x, "y": y, "w": w, "h": h, "patch": patch}


def add_section(ax, x, y, w, h, title):
    face, edge = COLORS["section"]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1.15,
        facecolor=face,
        edgecolor=edge,
        zorder=1,
    )
    ax.add_patch(patch)
    ax.text(
        x + 0.06,
        y + h - 0.13,
        title,
        ha="left",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#0F172A",
        zorder=2,
    )


def center_right(box):
    return (box["x"] + box["w"], box["y"] + box["h"] / 2)


def center_left(box):
    return (box["x"], box["y"] + box["h"] / 2)


def top_center(box):
    return (box["x"] + box["w"] / 2, box["y"] + box["h"])


def bottom_center(box):
    return (box["x"] + box["w"] / 2, box["y"])


def add_arrow(ax, start, end, color="#475569", dashed=False, rad=0.0, label=None, label_offset=(0, 0)):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=13,
        linewidth=1.35,
        color=color,
        linestyle=(0, (4, 3)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=5,
        shrinkB=5,
        zorder=2.5,
    )
    ax.add_patch(arrow)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, fontsize=8, color=color, ha="center", va="center")


def write_mermaid(path: Path) -> None:
    source = """flowchart LR
  subgraph O[Offline regime modelling]
    A[Historical/model temperature data] --> B[ROI selection and preprocessing]
    B --> C[Dictionary learning + hierarchical clustering]
    C --> D[Prototype classes C01-C06]
    D --> E[Prototype-derived descriptors]
  end
  subgraph P[Daily planner input]
    F[Daily model prediction maps: TEMPpred + STD] --> G[Predicted class / prototype selection]
    D --> G
  end
  subgraph R[Reward-map shaping]
    E --> H[Descriptor map D_norm]
    F --> I[STD_norm]
    G --> H
    H --> J[I_alpha(x,y) = (1-alpha) STD_norm(x,y) + alpha D_norm(x,y)]
    I --> J
  end
  subgraph V[AUV route optimization]
    J --> K[Lucrezia PCVRP/orienteering planner]
    K --> L[Single-AUV trajectories]
    K --> M[Multi-AUV trajectories]
  end
  subgraph S[Evaluation and selection]
    L --> N[Post-processing metrics]
    M --> N
    N --> Q[Final balanced alpha/descriptor selection]
  end
  M -. future work .-> U[Data assimilation / future work]
  L -. future work .-> U
  U -. feedback .-> F
"""
    path.write_text(source, encoding="utf-8")


def main() -> int:
    OUTDIR.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(16.5, 7.15))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 7.15)
    ax.axis("off")

    add_section(ax, 0.25, 0.75, 4.3, 5.95, "Offline regime modelling")
    add_section(ax, 4.8, 0.75, 2.75, 5.95, "Daily planner input")
    add_section(ax, 7.8, 0.75, 3.25, 5.95, "Reward-map shaping")
    add_section(ax, 11.3, 0.75, 2.85, 5.95, "AUV route optimization")
    add_section(ax, 14.4, 0.75, 3.35, 5.95, "Evaluation and selection")

    boxes = {}
    boxes["hist"] = add_box(ax, (0.55, 5.35), (1.55, 0.68), "Historical/model temperature data", "data", wrap_width=16)
    boxes["roi"] = add_box(ax, (2.45, 5.35), (1.65, 0.68), "ROI selection and preprocessing", "data", wrap_width=17)
    boxes["dict"] = add_box(ax, (0.55, 4.0), (1.65, 0.85), "Dictionary learning and hierarchical clustering", "regime", fontsize=8.9, wrap_width=17)
    boxes["proto"] = add_box(ax, (2.45, 4.0), (1.65, 0.85), "Prototype classes C01-C06", "regime", bold=True, wrap_width=16)
    boxes["desc"] = add_box(
        ax,
        (0.7, 1.45),
        (3.2, 1.55),
        "Prototype-derived descriptors: boundary_score, boundary_distance r1/r3/r5, interest_map, representative_zone, cold/warm regions, region_A/region_B",
        "descriptor",
        fontsize=8.2,
        wrap_width=24,
    )

    boxes["daily"] = add_box(ax, (5.15, 4.95), (2.05, 0.9), "Daily model prediction maps: TEMPpred and STD", "data", wrap_width=21)
    boxes["class"] = add_box(ax, (5.15, 2.85), (2.05, 0.95), "Predicted class and prototype selection", "regime", wrap_width=22)

    boxes["std"] = add_box(ax, (8.15, 4.95), (1.05, 0.72), "STD_norm(x,y)", "data", fontsize=9, wrap_width=12)
    boxes["dnorm"] = add_box(ax, (9.62, 4.95), (1.05, 0.72), "D_norm(x,y)", "descriptor", fontsize=9, wrap_width=12)
    boxes["formula"] = add_box(
        ax,
        (8.25, 2.75),
        (2.55, 1.18),
        "Reward map\nI_alpha(x,y) = (1-alpha) STD_norm(x,y) + alpha D_norm(x,y)",
        "descriptor",
        fontsize=9.4,
        bold=True,
        wrap_width=29,
    )

    boxes["planner"] = add_box(ax, (11.65, 3.72), (2.15, 0.9), "Lucrezia PCVRP / orienteering planner", "planner", bold=True, wrap_width=22)
    boxes["single"] = add_box(ax, (11.55, 2.0), (1.12, 0.84), "Single-AUV\ntrajectories", "planner", fontsize=8.4, wrap_width=11)
    boxes["multi"] = add_box(ax, (12.87, 2.0), (1.12, 0.84), "Multi-AUV\ntrajectories", "planner", fontsize=8.4, wrap_width=11)

    boxes["metrics"] = add_box(
        ax,
        (14.72, 3.92),
        (2.45, 1.18),
        "Post-processing metrics: STD collected, STD by regime, IQR10 proxy, boundary coverage, geometry, overlap and complementarity",
        "evaluation",
        fontsize=8.2,
        wrap_width=25,
    )
    boxes["select"] = add_box(ax, (14.95, 1.78), (2.0, 0.9), "Final balanced alpha / descriptor selection", "evaluation", bold=True, wrap_width=22)
    boxes["future"] = add_box(ax, (15.05, 5.65), (1.9, 0.62), "Data assimilation / future work", "future", fontsize=8.8, wrap_width=22)

    add_arrow(ax, center_right(boxes["hist"]), center_left(boxes["roi"]))
    add_arrow(ax, bottom_center(boxes["hist"]), top_center(boxes["dict"]), rad=0.12)
    add_arrow(ax, center_right(boxes["dict"]), center_left(boxes["proto"]))
    add_arrow(ax, bottom_center(boxes["proto"]), top_center(boxes["desc"]))

    add_arrow(ax, center_right(boxes["proto"]), center_left(boxes["class"]), color="#6B46C1", rad=-0.12)
    add_arrow(ax, bottom_center(boxes["daily"]), top_center(boxes["class"]), color="#2B6CB0")
    add_arrow(ax, center_right(boxes["daily"]), center_left(boxes["std"]), color="#2B6CB0")
    add_arrow(ax, center_right(boxes["desc"]), center_left(boxes["dnorm"]), color="#B7791F", rad=-0.08)
    add_arrow(ax, bottom_center(boxes["class"]), center_left(boxes["formula"]), color="#6B46C1", rad=0.12)
    add_arrow(ax, bottom_center(boxes["std"]), top_center(boxes["formula"]), color="#2B6CB0")
    add_arrow(ax, bottom_center(boxes["dnorm"]), top_center(boxes["formula"]), color="#B7791F")

    add_arrow(ax, center_right(boxes["formula"]), center_left(boxes["planner"]), color="#2F855A")
    add_arrow(ax, bottom_center(boxes["planner"]), top_center(boxes["single"]), color="#2F855A", rad=0.12)
    add_arrow(ax, bottom_center(boxes["planner"]), top_center(boxes["multi"]), color="#2F855A", rad=-0.12)

    add_arrow(ax, center_right(boxes["single"]), center_left(boxes["metrics"]), color="#C53030", rad=0.08)
    add_arrow(ax, center_right(boxes["multi"]), center_left(boxes["metrics"]), color="#C53030", rad=-0.08)
    add_arrow(ax, bottom_center(boxes["metrics"]), top_center(boxes["select"]), color="#C53030")

    add_arrow(ax, top_center(boxes["single"]), center_left(boxes["future"]), color="#64748B", dashed=True, rad=-0.12)
    add_arrow(ax, top_center(boxes["multi"]), center_left(boxes["future"]), color="#64748B", dashed=True, rad=-0.04, label="future work", label_offset=(0.0, 0.3))
    add_arrow(ax, center_left(boxes["future"]), top_center(boxes["daily"]), color="#64748B", dashed=True, rad=0.32)

    ax.text(
        0.28,
        0.35,
        "Note: data assimilation is not implemented in this thesis; dashed links indicate future work only.",
        fontsize=9,
        color="#475569",
        ha="left",
        va="center",
    )

    for ext in ["svg", "pdf", "png"]:
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.08}
        if ext == "png":
            kwargs["dpi"] = 300
        fig.savefig(OUTDIR / f"methodology_diagram.{ext}", **kwargs)
    plt.close(fig)
    write_mermaid(OUTDIR / "methodology_diagram.mmd")
    print(OUTDIR / "methodology_diagram.svg")
    print(OUTDIR / "methodology_diagram.pdf")
    print(OUTDIR / "methodology_diagram.png")
    print(OUTDIR / "methodology_diagram.mmd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
