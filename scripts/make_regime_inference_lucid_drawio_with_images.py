#!/usr/bin/env python
"""Create a Lucidchart/draw.io import file with real embedded thumbnails.

The output keeps diagram text, boxes and arrows editable. The mini-maps are
embedded as separate image objects generated from the validated arrays.
"""

from __future__ import annotations

from pathlib import Path
import base64
from io import BytesIO
import html
import time
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTDIR = ROOT / "docs" / "figures"
OUTFILE = OUTDIR / "regime_inference_pipeline_lucid_import_with_images.drawio"

STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP05 = RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260605_141912"

ROI_SHAPE = (72, 117)
PATCH_H = 24
PATCH_W = 40
TEMP_CMAP = "coolwarm"


def enc(text: str) -> str:
    return html.escape(text, quote=True).replace("\n", "&lt;br&gt;")


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


def data_uri(
    arr: np.ndarray,
    cmap_name: str,
    vmin: float | None,
    vmax: float | None,
    mask: np.ndarray | None = None,
    pixel_size: tuple[int, int] = (180, 110),
) -> str:
    a = np.asarray(arr, dtype=float)
    invalid = ~np.isfinite(a)
    if mask is not None and mask.shape == a.shape:
        invalid = invalid | ~mask.astype(bool)
    finite = a[np.isfinite(a)]
    if finite.size == 0:
        a = np.zeros_like(a, dtype=float)
        vmin, vmax = 0.0, 1.0
    if vmin is None:
        vmin = float(np.nanmin(finite))
    if vmax is None:
        vmax = float(np.nanmax(finite))
    if vmax <= vmin:
        vmax = vmin + 1.0
    norm = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    cmap = plt.get_cmap(cmap_name)
    rgba = (cmap(norm) * 255).astype(np.uint8)
    rgba[invalid] = np.array([255, 255, 255, 255], dtype=np.uint8)
    img = Image.fromarray(rgba, mode="RGBA").resize(pixel_size, Image.Resampling.BILINEAR)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


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
    def geom(cell: ET.Element, x: float | None = None, y: float | None = None, w: float | None = None, h: float | None = None) -> None:
        attrs: dict[str, str] = {"as": "geometry"}
        if x is not None:
            attrs.update({"x": str(x), "y": str(y), "width": str(w), "height": str(h)})
        else:
            attrs["relative"] = "1"
        ET.SubElement(cell, "mxGeometry", attrs)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        fill: str,
        stroke: str,
        font_size: int = 13,
        bold: bool = False,
        rounded: bool = True,
        extra_style: str = "",
    ) -> str:
        cell_id = self._id("v")
        style = (
            f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth=2;"
            f"fontSize={font_size};fontColor=#111827;align=center;verticalAlign=middle;"
        )
        if bold:
            style += "fontStyle=1;"
        style += extra_style
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value=enc(label), style=style, vertex="1", parent="1")
        self.geom(cell, x, y, w, h)
        return cell_id

    def text(self, x: float, y: float, w: float, h: float, label: str, font_size: int = 12, bold: bool = False, color: str = "#111827") -> str:
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

    def image(self, x: float, y: float, w: float, h: float, uri: str, stroke: str = "#334155") -> str:
        image_id = self._id("img")
        style = (
            "shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;"
            f"strokeColor=none;image={uri};"
        )
        cell = ET.SubElement(self.root, "mxCell", id=image_id, value="", style=style, vertex="1", parent="1")
        self.geom(cell, x, y, w, h)
        # Editable vector border so the image remains visually anchored.
        self.rect(x, y, w, h, "", "#FFFFFF", stroke, rounded=False, extra_style="fillColor=none;")
        return image_id

    def arrow(self, source: str, target: str, stroke: str = "#334155", dashed: bool = False) -> str:
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

    def to_file(self, path: Path) -> None:
        model = ET.Element(
            "mxGraphModel",
            dx="1434",
            dy="834",
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth="1800",
            pageHeight="820",
            math="0",
            shadow="0",
        )
        model.append(self.root)
        diagram = ET.Element("diagram", id="regime-inference-images", name="Regime inference pipeline with images")
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


def main() -> int:
    temp = np.load(STEP00 / "X_surface_370_roi_x490.npy", mmap_mode="r")
    temp_norm = np.load(STEP00 / "X_surface_370_roi_x490_norm.npy", mmap_mode="r")
    mask = np.load(STEP00 / "mask_common_roi_x490.npy").astype(bool)
    prototypes = np.load(STEP05 / "canonical_prototypes.npy")
    atom_components = np.load(STEP05 / "canonical_dictionary.npz", allow_pickle=True)["components"]
    # Components concatenate temperature-like patch values and valid-mask
    # encoding. Visualize the temperature-like half as atom thumbnails.
    atoms = atom_components[:, : PATCH_H * PATCH_W].reshape(4, PATCH_H, PATCH_W)
    codes = np.load(STEP05 / "canonical_sparse_codes.npz", allow_pickle=True)["sparse_codes"]

    descriptors = {
        "boundary": (np.load(STEP08 / "step08_descriptor_boundary_map.npy")[0], "magma"),
        "boundary-dist r3": (np.load(STEP08 / "step08_descriptor_boundary_distance_score_r3_cells.npy")[0], "magma"),
        "interest": (np.load(STEP08 / "step08_descriptor_interest_map.npy")[0], "inferno"),
        "represent.": (np.load(STEP08 / "step08_descriptor_representative_zone_map.npy")[0], "Greens"),
        "cold": (np.load(STEP08 / "step08_descriptor_cold_region_map.npy")[0], "Blues"),
        "warm": (np.load(STEP08 / "step08_descriptor_warm_region_map.npy")[0], "Reds"),
    }

    temp_examples = [np.asarray(temp[i]) for i in [0, 120, 240, 301]]
    temp_vmin, temp_vmax = robust_limits(temp_examples)
    norm_examples = [np.asarray(temp_norm[i]) for i in [0, 120, 240, 301]]
    norm_vmin, norm_vmax = robust_limits(norm_examples)
    proto_vmin, proto_vmax = robust_limits([prototypes[i] for i in range(6)])
    atom_lim = float(np.nanpercentile(np.abs(atoms[np.isfinite(atoms)]), 98)) or 1.0

    base = np.asarray(temp_norm[301])
    patch_positions = [(24, 0), (24, 25), (24, 50), (24, 77)]
    patches = [base[r : r + PATCH_H, c : c + PATCH_W] for r, c in patch_positions]
    code_img = np.nanmean(np.abs(codes), axis=1).T
    code_img = code_img[:, :: max(1, code_img.shape[1] // 92)]

    d = Drawio()
    section_specs = [
        ("Data and preprocessing", 30, 40, 280, 690, "#EEF6FF", "#2B6CB0"),
        ("Compact representation", 335, 40, 330, 690, "#F1EAFF", "#6B46C1"),
        ("Regime discovery", 690, 40, 220, 690, "#FFF7D6", "#B7791F"),
        ("Prototype interpretation", 935, 40, 330, 690, "#EAFBF0", "#2F855A"),
        ("Descriptor generation", 1290, 40, 330, 690, "#FFF0F0", "#C53030"),
        ("Planner-ready outputs", 1645, 40, 170, 690, "#F1F5F9", "#475569"),
    ]
    for title, x, y, w, h, fill, stroke in section_specs:
        d.rect(x, y, w, h, "", fill, stroke, rounded=True, extra_style="fontSize=1;")
        d.text(x + 10, y + 8, w - 20, 34, title, font_size=18, bold=True)

    # Data and preprocessing.
    d.text(70, 112, 205, 42, "370 daily\nsurface temperature maps", font_size=14, bold=True, color="#1E3A8A")
    daily_ids = []
    for label, idx, x, y in [("day 1", 0, 70, 180), ("day 121", 120, 170, 180), ("day 241", 240, 70, 265), ("day 302", 301, 170, 265)]:
        d.text(x, y - 20, 75, 16, label, font_size=10)
        daily_ids.append(d.image(x, y, 75, 56, data_uri(np.asarray(temp[idx]), TEMP_CMAP, temp_vmin, temp_vmax, mask, (150, 100)), "#2B6CB0"))
    prep = d.rect(70, 385, 205, 82, "X490 ROI\ncommon valid mask\nnormalization", "#F8FAFC", "#2B6CB0", font_size=13)
    d.text(92, 492, 115, 18, "standardized map", font_size=10)
    std_map = d.image(95, 515, 110, 74, data_uri(np.asarray(temp_norm[301]), TEMP_CMAP, norm_vmin, norm_vmax, mask, (180, 120)), "#2B6CB0")

    # Compact representation.
    d.text(402, 150, 110, 18, "ROI image", font_size=10)
    roi = d.image(370, 172, 110, 76, data_uri(base, TEMP_CMAP, norm_vmin, norm_vmax, mask, (180, 120)), "#6B46C1")
    # Numbered patch regions drawn on top of the ROI image as editable rectangles.
    roi_x, roi_y, roi_w, roi_h = 370, 172, 110, 76
    for i, (rr, cc) in enumerate(patch_positions, start=1):
        rx = roi_x + cc / ROI_SHAPE[1] * roi_w
        ry = roi_y + (ROI_SHAPE[0] - rr - PATCH_H) / ROI_SHAPE[0] * roi_h
        rw = PATCH_W / ROI_SHAPE[1] * roi_w
        rh = PATCH_H / ROI_SHAPE[0] * roi_h
        d.rect(rx, ry, rw, rh, str(i), "none", "#F97316", font_size=9, bold=True, rounded=False, extra_style="fillColor=none;fontColor=#7C2D12;")
    d.text(390, 290, 190, 32, "ordered patch extraction\n40 x 24", font_size=13, bold=True, color="#6B46C1")
    patch_ids = []
    for i, (patch, x) in enumerate(zip(patches, [370, 430, 490, 550]), start=1):
        d.text(x, 318, 52, 14, f"patch {i}", font_size=9)
        patch_ids.append(d.image(x, 335, 52, 40, data_uri(patch, TEMP_CMAP, norm_vmin, norm_vmax, None, (120, 80)), "#F97316"))
    for a, b in zip(patch_ids[:-1], patch_ids[1:]):
        d.arrow(a, b, "#F97316")
    d.text(430, 405, 160, 34, "dictionary learning\nK = 4", font_size=14, bold=True, color="#4C1D95")
    atom_ids = []
    for i, (atom, x) in enumerate(zip(atoms, [370, 440, 510, 580]), start=1):
        d.text(x, 437, 55, 14, f"atom {i}", font_size=9)
        atom_ids.append(d.image(x, 455, 55, 40, data_uri(atom, TEMP_CMAP, -atom_lim, atom_lim, None, (120, 80)), "#6B46C1"))
    d.text(430, 578, 160, 18, "sparse code activity", font_size=10)
    codes_id = d.image(385, 600, 230, 85, data_uri(code_img, "magma", None, None, None, (260, 80)), "#6B46C1")
    d.text(430, 688, 160, 18, "4 atoms x 370 days", font_size=10, color="#475569")

    # Regime discovery.
    dendro = d.rect(725, 170, 150, 120, "Ward hierarchical\nclustering", "#FFFBEA", "#B7791F", font_size=12)
    classes = d.rect(725, 430, 150, 120, "six recurrent\nclasses\nC01-C06", "#FEF3C7", "#B7791F", font_size=13, bold=True)

    # Prototype interpretation.
    proto_ids = []
    coords = [(970, 180), (1060, 180), (1150, 180), (970, 295), (1060, 295), (1150, 295)]
    for i, (x, y) in enumerate(coords, start=1):
        d.text(x, y - 20, 75, 16, f"C{i:02d}", font_size=10)
        proto_ids.append(d.image(x, y, 75, 56, data_uri(prototypes[i - 1], TEMP_CMAP, proto_vmin, proto_vmax, mask, (150, 100)), "#2F855A"))
    interp = d.rect(980, 455, 250, 80, "Class interpretation\nhomogeneous | single-gradient | multi-regime", "#F0FDF4", "#2F855A", font_size=13)
    library = d.rect(980, 590, 250, 80, "prototype library\nclass-level regime maps", "#F0FDF4", "#2F855A", font_size=13)

    # Descriptor generation.
    desc_ids = []
    for i, (label, (arr, cmap)) in enumerate(descriptors.items()):
        row, col = divmod(i, 3)
        x = 1320 + col * 88
        y = 180 + row * 110
        d.text(x, y - 22, 75, 18, label, font_size=9)
        desc_ids.append(d.image(x, y, 75, 56, data_uri(arr, cmap, 0, 1, mask, (150, 100)), "#C53030"))
    desc_box = d.rect(
        1335,
        495,
        255,
        112,
        "boundary_score\nboundary_distance r1/r3/r5\ninterest_map\nrepresentative_zone\ncold/warm and A/B regions",
        "#FFF5F5",
        "#C53030",
        font_size=12,
    )

    # Planner-ready outputs.
    out1 = d.rect(1675, 190, 120, 80, "prototype\nlibrary", "#F8FAFC", "#475569", font_size=13)
    out2 = d.rect(1675, 315, 120, 80, "predicted\nclass", "#F8FAFC", "#475569", font_size=13)
    out3 = d.rect(1675, 440, 120, 90, "prototype-specific\ndescriptor maps", "#F8FAFC", "#475569", font_size=12)
    out4 = d.rect(1675, 600, 120, 90, "downstream\nreward-map\nshaping", "#E2E8F0", "#475569", font_size=12)

    # Editable arrows.
    d.arrow(std_map, roi)
    d.arrow(patch_ids[2], atom_ids[2], "#6B46C1")
    d.arrow(atom_ids[2], codes_id, "#6B46C1")
    d.arrow(codes_id, dendro)
    d.arrow(dendro, classes, "#B7791F")
    d.arrow(dendro, proto_ids[0])
    d.arrow(proto_ids[5], desc_ids[0])
    d.arrow(desc_box, out3)
    d.arrow(out3, out4)
    d.arrow(library, out1, "#475569")
    d.arrow(classes, out2, "#475569")
    d.arrow(proto_ids[1], library, "#2F855A")

    d.text(
        60,
        750,
        1500,
        32,
        "Editable Lucidchart import version with real embedded thumbnails from Step00, Step05 and Step08. Images can be moved/resized; text, boxes and arrows remain editable.",
        font_size=12,
        color="#475569",
    )

    d.to_file(OUTFILE)
    note = (
        "This Lucid/draw.io import file embeds the real thumbnails used in the PNG-style regime inference diagram. "
        "The thumbnails are separate image objects generated from the validated Step00, Step05 and Step08 arrays. "
        "Dictionary atom thumbnails use the temperature-like half of the real Step05 `canonical_dictionary.npz` components; the second half is the valid-mask encoding. "
        "They are not pixel-editable inside Lucidchart, but they can be moved, resized, copied or replaced. "
        "All labels, section boxes, callout boxes and arrows are editable vector/text objects.\n"
    )
    (OUTDIR / "regime_inference_pipeline_lucid_import_with_images_note.txt").write_text(note, encoding="utf-8")
    print(OUTFILE)
    print(OUTDIR / "regime_inference_pipeline_lucid_import_with_images_note.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
