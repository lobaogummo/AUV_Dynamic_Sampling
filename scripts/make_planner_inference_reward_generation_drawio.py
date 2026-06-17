#!/usr/bin/env python
"""Create an editable draw.io file for the planner-inference diagram.

The file mirrors the PNG/PDF/SVG methodology figure and embeds the same
thumbnail maps as draw.io image objects. Shapes, labels and arrows remain
editable after import into diagrams.net/draw.io.
"""

from __future__ import annotations

import base64
import html
import json
import time
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP11Y = RESULTS / "fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260605_143425"
ASSETS = ROOT / "docs" / "figures" / "regime_inference_assets"

OUTDIR = RESULTS / "planner_inference_reward_generation_diagram_20260613_103151"
OUTFILE = OUTDIR / "planner_inference_reward_generation_diagram.drawio"


COLORS = {
    "inputs_fill": "#EAF4FF",
    "inputs_stroke": "#3B82C4",
    "class_fill": "#F1E8FF",
    "class_stroke": "#7C3AED",
    "library_fill": "#EAFBF0",
    "library_stroke": "#2F855A",
    "reward_fill": "#FFF3D6",
    "reward_stroke": "#C27A13",
    "planner_fill": "#EEF4FA",
    "planner_stroke": "#526B84",
    "text": "#111827",
    "arrow": "#475569",
}


def enc(text: str) -> str:
    return html.escape(text, quote=True).replace("\n", "&lt;br&gt;")


def normalize01(arr: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    data = np.asarray(arr, dtype=float).copy()
    valid = np.isfinite(data)
    if mask is not None and mask.shape == data.shape:
        valid &= mask.astype(bool)
    if not np.any(valid):
        return np.zeros_like(data, dtype=float)
    lo = float(np.nanpercentile(data[valid], 2))
    hi = float(np.nanpercentile(data[valid], 98))
    if hi <= lo:
        lo, hi = float(np.nanmin(data[valid])), float(np.nanmax(data[valid]))
    if hi <= lo:
        hi = lo + 1.0
    out = np.clip((data - lo) / (hi - lo), 0, 1)
    out[~valid] = np.nan
    return out


def map_data_uri(
    arr: np.ndarray,
    cmap_name: str,
    mask: np.ndarray | None = None,
    pixel_size: tuple[int, int] = (240, 155),
    vmin: float = 0.0,
    vmax: float = 1.0,
    origin_lower: bool = True,
) -> str:
    a = np.asarray(arr, dtype=float)
    invalid = ~np.isfinite(a)
    if mask is not None and mask.shape == a.shape:
        invalid |= ~mask.astype(bool)
    norm = np.clip((a - vmin) / max(vmax - vmin, 1e-12), 0, 1)
    rgba = (plt.get_cmap(cmap_name)(norm) * 255).astype(np.uint8)
    rgba[invalid] = np.array([255, 255, 255, 255], dtype=np.uint8)
    if origin_lower:
        rgba = np.flipud(rgba)
    image = Image.fromarray(rgba, mode="RGBA").resize(pixel_size, Image.Resampling.BILINEAR)
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    # Draw.io style strings use semicolons as delimiters, so encode the
    # semicolon in the data URI. This keeps embedded images visible on import.
    return "data:image/png%3Bbase64," + b64


def file_data_uri(path: Path, pixel_size: tuple[int, int] = (180, 110)) -> str:
    image = Image.open(path).convert("RGBA").resize(pixel_size, Image.Resampling.LANCZOS)
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return "data:image/png%3Bbase64," + b64


class Drawio:
    def __init__(self) -> None:
        self.next_id = 2
        self.root = ET.Element("root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")

    def _id(self, prefix: str = "n") -> str:
        out = f"{prefix}{self.next_id}"
        self.next_id += 1
        return out

    @staticmethod
    def geom(
        cell: ET.Element,
        x: float | None = None,
        y: float | None = None,
        w: float | None = None,
        h: float | None = None,
    ) -> None:
        attrs: dict[str, str] = {"as": "geometry"}
        if x is None:
            attrs["relative"] = "1"
        else:
            attrs.update({"x": str(x), "y": str(y), "width": str(w), "height": str(h)})
        ET.SubElement(cell, "mxGeometry", attrs)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str = "",
        fill: str = "#FFFFFF",
        stroke: str = "#CBD5E1",
        font_size: int = 13,
        bold: bool = False,
        rounded: bool = True,
        dashed: bool = False,
        extra_style: str = "",
    ) -> str:
        cell_id = self._id("v")
        style = (
            f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth=2;"
            f"fontSize={font_size};fontColor={COLORS['text']};align=center;verticalAlign=middle;"
        )
        if bold:
            style += "fontStyle=1;"
        if dashed:
            style += "dashed=1;dashPattern=8 4;"
        style += extra_style
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value=enc(label), style=style, vertex="1", parent="1")
        self.geom(cell, x, y, w, h)
        return cell_id

    def text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        font_size: int = 12,
        bold: bool = False,
        color: str = "#111827",
    ) -> str:
        cell_id = self._id("t")
        style = (
            "text;html=1;strokeColor=none;fillColor=none;whiteSpace=wrap;rounded=0;"
            f"fontSize={font_size};fontColor={color};align=center;verticalAlign=middle;"
        )
        if bold:
            style += "fontStyle=1;"
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value=enc(label), style=style, vertex="1", parent="1")
        self.geom(cell, x, y, w, h)
        return cell_id

    def image(self, x: float, y: float, w: float, h: float, uri: str, stroke: str, label: str = "") -> str:
        self.text(x, y - 20, w, 16, label, font_size=10, color="#111827") if label else None
        image_id = self._id("img")
        style = (
            "shape=image;verticalLabelPosition=bottom;verticalAlign=top;"
            f"imageAspect=0;aspect=fixed;strokeColor=none;image={uri};"
        )
        cell = ET.SubElement(self.root, "mxCell", id=image_id, value="", style=style, vertex="1", parent="1")
        self.geom(cell, x, y, w, h)
        self.rect(x, y, w, h, "", "#FFFFFF", stroke, rounded=False, extra_style="fillColor=none;")
        return image_id

    def arrow(self, source: str, target: str, stroke: str = "#475569", dashed: bool = False) -> str:
        cell_id = self._id("e")
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
            f"endArrow=block;endFill=1;strokeColor={stroke};strokeWidth=2;"
        )
        if dashed:
            style += "dashed=1;dashPattern=6 4;"
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value="", style=style, edge="1", parent="1", source=source, target=target)
        self.geom(cell)
        return cell_id

    def line_box(self, x: float, y: float, w: float, h: float, label: str, color: str) -> str:
        box = self.rect(x, y, w, h, "", "#F8FAFC", "#94A3B8", rounded=False, extra_style="strokeWidth=1;")
        pts = [
            (x + 0.08 * w, y + 0.68 * h),
            (x + 0.22 * w, y + 0.54 * h),
            (x + 0.18 * w, y + 0.27 * h),
            (x + 0.42 * w, y + 0.20 * h),
            (x + 0.58 * w, y + 0.42 * h),
            (x + 0.51 * w, y + 0.64 * h),
            (x + 0.78 * w, y + 0.54 * h),
            (x + 0.90 * w, y + 0.25 * h),
        ]
        previous = None
        for i, (px, py) in enumerate(pts):
            node = self.rect(px - 2, py - 2, 4, 4, "", color, color, rounded=True, extra_style="strokeWidth=0;")
            if previous is not None:
                edge_id = self._id("traj")
                style = f"edgeStyle=straightEdgeStyle;html=1;endArrow=none;strokeColor={color};strokeWidth=3;"
                cell = ET.SubElement(self.root, "mxCell", id=edge_id, value="", style=style, edge="1", parent="1", source=previous, target=node)
                self.geom(cell)
            previous = node
        self.text(x, y - 18, w, 14, label, font_size=10)
        return box

    def to_file(self, path: Path) -> None:
        model = ET.Element(
            "mxGraphModel",
            dx="1600",
            dy="900",
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth="1920",
            pageHeight="860",
            math="0",
            shadow="0",
        )
        model.append(self.root)
        diagram = ET.Element("diagram", id="planner-inference-reward", name="Planning-day inference and reward-map generation")
        diagram.append(model)
        mxfile = ET.Element(
            "mxfile",
            host="app.diagrams.net",
            modified=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            agent="Codex",
            version="24.7.17",
            type="device",
        )
        mxfile.append(diagram)
        tree = ET.ElementTree(mxfile)
        ET.indent(tree, space="  ")
        path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(path, encoding="utf-8", xml_declaration=True)


def load_maps() -> dict[str, np.ndarray | str]:
    dates = pd.read_csv(STEP00 / "dates_370.csv")
    day_index = int(dates.loc[dates["date"].astype(str) == "2024-08-24", "time_index"].iloc[0])
    temp = np.load(STEP00 / "X_surface_370_roi_x490.npy", mmap_mode="r")
    mask = np.load(STEP00 / "mask_common_roi_x490.npy").astype(bool)
    bathy = np.load(STEP00 / "BATHY_roi_x490.npy")

    def load_step11y(name: str) -> np.ndarray:
        arr = np.load(STEP11Y / name)
        return np.asarray(arr[0] if arr.ndim == 3 else arr, dtype=float)

    std = normalize01(load_step11y("prototype_based_baseline_STD_norm.npy"), mask)
    descriptor = normalize01(load_step11y("prototype_based_boundary_distance_score_r3_cells_norm.npy"), mask)
    interest = normalize01(load_step11y("prototype_based_interest_map_norm.npy"), mask)
    region_a = normalize01(load_step11y("prototype_based_AUV1_region_map.npy"), mask)
    region_b = normalize01(load_step11y("prototype_based_AUV2_region_map.npy"), mask)
    temppred = normalize01(np.asarray(temp[day_index], dtype=float), mask)
    mask_visual = normalize01(-bathy, mask)
    enriched = normalize01(0.5 * std + 0.5 * descriptor, mask)

    return {
        "mask": mask,
        "temppred": temppred,
        "std": std,
        "mask_visual": mask_visual,
        "descriptor": descriptor,
        "interest": interest,
        "region_a": region_a,
        "region_b": region_b,
        "enriched": enriched,
    }


def main() -> int:
    maps = load_maps()
    mask = maps["mask"]

    uri = {
        "temppred": map_data_uri(maps["temppred"], "coolwarm", mask=mask),
        "std": map_data_uri(maps["std"], "viridis", mask=mask),
        "mask": map_data_uri(maps["mask_visual"], "Blues", mask=mask),
        "descriptor": map_data_uri(maps["descriptor"], "magma", mask=mask),
        "interest": map_data_uri(maps["interest"], "magma", mask=mask),
        "region_a": map_data_uri(maps["region_a"], "Greens", mask=mask, pixel_size=(120, 75)),
        "region_b": map_data_uri(maps["region_b"], "Oranges", mask=mask, pixel_size=(120, 75)),
        "enriched": map_data_uri(maps["enriched"], "plasma", mask=mask),
    }
    for c in ["C01", "C02", "C03", "C04", "C05", "C06"]:
        uri[c] = file_data_uri(ASSETS / f"09_prototype_{c}.png", pixel_size=(120, 75))

    d = Drawio()
    d.text(350, 20, 1220, 40, "Planning-day inference and reward-map generation", font_size=30, bold=True, color="#0F172A")
    d.text(
        420,
        62,
        1080,
        28,
        "TEMPpred selects the prototype class; STD and prototype-derived descriptors shape planner-ready rewards.",
        font_size=16,
        color="#475569",
    )

    sections = {
        "inputs": d.rect(30, 125, 315, 675, "Planning-day inputs", COLORS["inputs_fill"], COLORS["inputs_stroke"], font_size=22, bold=True, extra_style="verticalAlign=top;spacingTop=14;"),
        "class": d.rect(365, 125, 300, 675, "Class assignment", COLORS["class_fill"], COLORS["class_stroke"], font_size=22, bold=True, extra_style="verticalAlign=top;spacingTop=14;"),
        "library": d.rect(685, 125, 340, 675, "Offline library retrieval", COLORS["library_fill"], COLORS["library_stroke"], font_size=22, bold=True, dashed=True, extra_style="verticalAlign=top;spacingTop=14;"),
        "reward": d.rect(1045, 125, 455, 675, "Reward-map generation", COLORS["reward_fill"], COLORS["reward_stroke"], font_size=22, bold=True, extra_style="verticalAlign=top;spacingTop=14;"),
        "planner": d.rect(1520, 125, 370, 675, "Planner-ready outputs", COLORS["planner_fill"], COLORS["planner_stroke"], font_size=22, bold=True, extra_style="verticalAlign=top;spacingTop=14;"),
    }

    # Planning-day inputs.
    temp_img = d.image(65, 250, 120, 74, uri["temppred"], COLORS["inputs_stroke"], "TEMPpred(t)")
    std_img = d.image(205, 250, 120, 74, uri["std"], COLORS["inputs_stroke"], "STD(t)")
    mask_img = d.image(65, 370, 120, 74, uri["mask"], COLORS["inputs_stroke"], "bathymetry / mask")
    grid_box = d.rect(205, 370, 120, 74, "ROI X490\ncommon grid", COLORS["inputs_fill"], COLORS["inputs_stroke"], font_size=15, bold=True)
    d.rect(65, 505, 260, 96, "Planning day\n2024-08-24\nvalid cells only", "#FFFFFF", "#CBD5E1", font_size=15)
    d.rect(65, 650, 260, 78, "STD remains the\nuncertainty baseline", COLORS["inputs_fill"], COLORS["inputs_stroke"], font_size=16, bold=True)

    # Class assignment.
    class_temp = d.image(405, 250, 125, 78, uri["temppred"], COLORS["class_stroke"], "TEMPpred")
    crop = d.rect(400, 370, 145, 72, "crop / mask\nnormalise", COLORS["class_fill"], COLORS["class_stroke"], font_size=15)
    compare = d.rect(400, 478, 145, 74, "compare with\nprototype library", COLORS["class_fill"], COLORS["class_stroke"], font_size=14)
    one_class = d.rect(560, 330, 75, 160, "one class\nper planning\nday", "#FFFFFF", "#CBD5E1", font_size=13)
    ck = d.rect(400, 615, 230, 92, "assigned class\nC_k = C01", COLORS["class_fill"], COLORS["class_stroke"], font_size=18, bold=True)
    d.arrow(class_temp, crop, COLORS["class_stroke"])
    d.arrow(crop, compare, COLORS["class_stroke"])
    d.arrow(compare, ck, COLORS["class_stroke"])

    # Offline library retrieval.
    d.text(730, 160, 250, 28, "Offline library from Diagram 1", font_size=14, color="#166534")
    proto_positions = {
        "C01": (720, 255),
        "C02": (805, 255),
        "C03": (890, 255),
        "C04": (720, 350),
        "C05": (805, 350),
        "C06": (890, 350),
    }
    for c, (x, y) in proto_positions.items():
        d.image(x, y, 66, 44, uri[c], COLORS["library_stroke"], c)
    desc_library = d.rect(730, 455, 260, 74, "descriptor library", COLORS["library_fill"], COLORS["library_stroke"], font_size=16, bold=True)
    desc_list = d.rect(710, 575, 135, 145, "boundary score\nboundary distance\nrepresentative zone\ncold / warm regions\ninterest map", "#FFFFFF", "#CBD5E1", font_size=13)
    desc_img = d.image(870, 585, 82, 52, uri["descriptor"], COLORS["library_stroke"], "boundary-dist r3")
    interest_img = d.image(870, 675, 82, 52, uri["interest"], COLORS["library_stroke"], "interest map")
    d.arrow(ck, desc_library, COLORS["library_stroke"])
    d.arrow(desc_library, desc_list, COLORS["library_stroke"])

    # Reward map generation.
    std_thumb = d.image(1085, 260, 100, 64, uri["std"], COLORS["reward_stroke"], "STD_norm")
    desc_thumb = d.image(1230, 260, 100, 64, uri["descriptor"], COLORS["reward_stroke"], "D_norm")
    enriched_thumb = d.image(1375, 260, 100, 64, uri["enriched"], COLORS["reward_stroke"], "enriched reward")
    d.text(1200, 270, 35, 45, "+", font_size=30, bold=True, color="#92400E")
    d.arrow(desc_thumb, enriched_thumb, COLORS["reward_stroke"])
    baseline = d.rect(1080, 365, 150, 74, "Baseline\nR_base\n= STD_norm", COLORS["reward_fill"], COLORS["reward_stroke"], font_size=15, bold=True)
    single = d.rect(
        1250,
        350,
        220,
        96,
        "Single-AUV enriched\nR_alpha = (1 - alpha)\nSTD_norm + alpha D_norm",
        COLORS["reward_fill"],
        COLORS["reward_stroke"],
        font_size=14,
        bold=True,
    )
    multi = d.rect(
        1105,
        520,
        340,
        112,
        "Multi-AUV vehicle-specific\nR_AUV1 = w_sigma STD_norm + w_A R_A\nR_AUV2 = w_sigma STD_norm + w_B R_B",
        COLORS["reward_fill"],
        COLORS["reward_stroke"],
        font_size=14,
        bold=True,
    )
    d.image(1105, 645, 58, 36, uri["region_a"], COLORS["reward_stroke"], "R_A")
    d.image(1175, 645, 58, 36, uri["region_b"], COLORS["reward_stroke"], "R_B")
    d.rect(1100, 715, 360, 58, "Descriptors complement STD;\nthey do not replace it.", "#FFFFFF", "#CBD5E1", font_size=15, bold=True)
    d.arrow(std_thumb, baseline, COLORS["reward_stroke"])
    d.arrow(std_thumb, single, COLORS["reward_stroke"])
    d.arrow(desc_thumb, single, COLORS["reward_stroke"])
    d.arrow(std_thumb, multi, COLORS["reward_stroke"])
    d.arrow(desc_thumb, multi, COLORS["reward_stroke"])

    # Planner-ready outputs.
    maps_box = d.rect(1565, 230, 145, 88, "reward maps\nNetCDF / NPZ", COLORS["planner_fill"], COLORS["planner_stroke"], font_size=15, bold=True)
    lucrezia = d.rect(1735, 230, 135, 88, "Lucrezia\nAUV planner", COLORS["planner_fill"], COLORS["planner_stroke"], font_size=15, bold=True)
    base_traj = d.line_box(1565, 385, 120, 64, "baseline", "#111827")
    enrich_traj = d.line_box(1735, 385, 120, 64, "enriched", "#0891B2")
    metrics = d.rect(1568, 515, 280, 94, "trajectory metrics\nSTD collected, regime coverage,\nIQR10, efficiency, overlap", "#FFFFFF", "#CBD5E1", font_size=14)
    comparison = d.rect(1568, 665, 280, 78, "Baseline vs enriched\ntrajectory comparison", COLORS["planner_fill"], COLORS["planner_stroke"], font_size=15, bold=True)

    # Main and output arrows.
    d.arrow(sections["inputs"], sections["class"], COLORS["arrow"])
    d.arrow(sections["class"], sections["library"], COLORS["arrow"])
    d.arrow(sections["library"], sections["reward"], COLORS["arrow"])
    d.arrow(enriched_thumb, maps_box, COLORS["planner_stroke"])
    d.arrow(baseline, maps_box, COLORS["planner_stroke"])
    d.arrow(single, maps_box, COLORS["planner_stroke"])
    d.arrow(multi, maps_box, COLORS["planner_stroke"])
    d.arrow(maps_box, lucrezia, COLORS["planner_stroke"])
    d.arrow(lucrezia, enrich_traj, COLORS["planner_stroke"])
    d.arrow(enrich_traj, base_traj, COLORS["planner_stroke"])
    d.arrow(enrich_traj, metrics, COLORS["planner_stroke"])
    d.arrow(metrics, comparison, COLORS["planner_stroke"])

    d.text(
        420,
        820,
        1080,
        24,
        "Correct logic: TEMPpred(t) -> assigned class C_k -> prototype-derived descriptors; STD(t) + descriptors -> reward map -> planner.",
        font_size=13,
        color="#475569",
    )

    d.to_file(OUTFILE)

    sources = {
        "drawio": str(OUTFILE),
        "based_on_png": str(OUTDIR / "planner_inference_reward_generation_diagram.png"),
        "images_embedded": True,
        "note": "Image data URIs encode the semicolon as %3B to improve draw.io import compatibility.",
    }
    (OUTDIR / "planner_inference_reward_generation_drawio_sources.json").write_text(
        json.dumps(sources, indent=2), encoding="utf-8"
    )
    print(OUTFILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
