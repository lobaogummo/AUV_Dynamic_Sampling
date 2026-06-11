#!/usr/bin/env python
"""Create an editable draw.io/Lucidchart import version of the regime pipeline."""

from __future__ import annotations

from pathlib import Path
import html
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "docs" / "figures"
OUTFILE = OUTDIR / "regime_inference_pipeline_lucid_import.drawio"


def enc(text: str) -> str:
    return html.escape(text, quote=True).replace("\n", "&lt;br&gt;")


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
        parent: str = "1",
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
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value=enc(label), style=style, vertex="1", parent=parent)
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), as_="geometry")
        return cell_id

    def text(self, x: float, y: float, w: float, h: float, label: str, font_size: int = 12, bold: bool = False) -> str:
        cell_id = self._id("t")
        style = f"text;html=1;strokeColor=none;fillColor=none;whiteSpace=wrap;rounded=0;fontSize={font_size};fontColor=#111827;align=center;verticalAlign=middle;"
        if bold:
            style += "fontStyle=1;"
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value=enc(label), style=style, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), as_="geometry")
        return cell_id

    def arrow(self, source: str, target: str, stroke: str = "#334155", dashed: bool = False) -> str:
        cell_id = self._id("e")
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
            f"endArrow=block;endFill=1;strokeColor={stroke};strokeWidth=2;"
        )
        if dashed:
            style += "dashed=1;dashPattern=6 4;"
        cell = ET.SubElement(self.root, "mxCell", id=cell_id, value="", style=style, edge="1", parent="1", source=source, target=target)
        ET.SubElement(cell, "mxGeometry", relative="1", as_="geometry")
        return cell_id

    def mini_map(self, x: float, y: float, w: float, h: float, label: str, cold_warm: str = "warm") -> str:
        fill = "#FCA5A5" if cold_warm == "warm" else "#93C5FD"
        grad = "#60A5FA" if cold_warm == "warm" else "#FCA5A5"
        style = f"gradientColor={grad};gradientDirection=east;"
        return self.rect(x, y, w, h, label, fill, "#2B6CB0", font_size=10, rounded=False, extra_style=style)

    def simple_bar_matrix(self, x: float, y: float, w: float, h: float, label: str) -> str:
        box = self.rect(x, y, w, h, label, "#111827", "#6B46C1", font_size=10, rounded=False, extra_style="fontColor=#F8FAFC;")
        colors = ["#7E22CE", "#F97316", "#111827", "#A855F7", "#F59E0B", "#111827"]
        col_w = w / 14
        for i in range(10):
            self.rect(x + 8 + i * col_w, y + 10, col_w * 0.45, h - 20, "", colors[i % len(colors)], colors[i % len(colors)], rounded=False)
        return box

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
        diagram = ET.Element("diagram", id="regime-inference", name="Regime inference pipeline")
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
    d.text(70, 115, 205, 42, "370 daily\nsurface temperature maps", font_size=14, bold=True)
    daily = [
        d.mini_map(70, 180, 75, 56, "day 1", "warm"),
        d.mini_map(170, 180, 75, 56, "day 121", "cold"),
        d.mini_map(70, 265, 75, 56, "day 241", "cold"),
        d.mini_map(170, 265, 75, 56, "day 302", "warm"),
    ]
    prep = d.rect(70, 385, 205, 82, "X490 ROI\ncommon valid mask\nnormalization", "#F8FAFC", "#2B6CB0", font_size=13)
    std_map = d.mini_map(95, 510, 110, 74, "standardized\nmap", "warm")

    # Compact representation.
    roi = d.mini_map(370, 170, 110, 76, "ROI image", "warm")
    patches = []
    patch_xs = [370, 430, 490, 550]
    for i, px in enumerate(patch_xs, start=1):
        patches.append(d.mini_map(px, 330, 52, 40, f"patch {i}", "warm" if i < 3 else "cold"))
    d.text(377, 288, 225, 32, "ordered patch extraction\n40 x 24", font_size=13, bold=True)
    for a, b in zip(patches[:-1], patches[1:]):
        d.arrow(a, b, "#F97316")
    atoms = []
    for i, px in enumerate([370, 440, 510, 580], start=1):
        atoms.append(d.mini_map(px, 445, 55, 40, f"atom {i}", "warm" if i != 3 else "cold"))
    d.text(430, 402, 160, 34, "dictionary learning\nK = 4", font_size=14, bold=True)
    codes = d.simple_bar_matrix(385, 580, 230, 85, "sparse code activity\n4 atoms x 370 days")

    # Regime discovery.
    dendro = d.rect(725, 170, 150, 120, "Ward hierarchical\nclustering", "#FFFBEA", "#B7791F", font_size=12)
    classes = d.rect(725, 430, 150, 120, "six recurrent\nclasses\nC01-C06", "#FEF3C7", "#B7791F", font_size=13, bold=True)

    # Prototype interpretation.
    protos = []
    coords = [(970, 180), (1060, 180), (1150, 180), (970, 295), (1060, 295), (1150, 295)]
    for i, (x, y) in enumerate(coords, start=1):
        protos.append(d.mini_map(x, y, 75, 56, f"C{i:02d}", "warm" if i <= 3 else "cold"))
    interp = d.rect(980, 455, 250, 80, "Class interpretation\nhomogeneous | single-gradient | multi-regime", "#F0FDF4", "#2F855A", font_size=13)
    library = d.rect(980, 590, 250, 80, "prototype library\nclass-level regime maps", "#F0FDF4", "#2F855A", font_size=13)

    # Descriptor generation.
    desc_labels = ["boundary", "boundary-dist r3", "interest", "represent.", "cold", "warm"]
    descs = []
    for i, label in enumerate(desc_labels):
        row = i // 3
        col = i % 3
        color = "#FECACA" if label in {"boundary", "boundary-dist r3", "interest"} else "#DCFCE7"
        descs.append(d.rect(1320 + col * 88, 180 + row * 110, 75, 56, label, color, "#C53030", font_size=10, rounded=False))
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

    # Main arrows.
    d.arrow(std_map, roi)
    d.arrow(roi, patches[0], "#6B46C1")
    d.arrow(patches[2], atoms[2], "#6B46C1")
    d.arrow(atoms[2], codes, "#6B46C1")
    d.arrow(codes, dendro)
    d.arrow(dendro, classes, "#B7791F")
    d.arrow(dendro, protos[0])
    d.arrow(protos[5], descs[0])
    d.arrow(desc_box, out3)
    d.arrow(out3, out4)

    # Output fan-in arrows.
    d.arrow(library, out1, "#475569")
    d.arrow(classes, out2, "#475569")
    d.arrow(protos[1], library, "#2F855A")

    d.text(
        60,
        750,
        1360,
        32,
        "Editable Lucidchart import version of the offline regime-inference pipeline. Mini-map thumbnails are vector schematic placeholders; text, boxes and arrows are editable after import.",
        font_size=12,
    )

    d.to_file(OUTFILE)
    print(OUTFILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
