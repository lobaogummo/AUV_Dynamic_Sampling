from __future__ import annotations

import base64
import csv
import hashlib
import shutil
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
STEP12A = ROOT / "results" / "fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260529_175726"
STEP12B = ROOT / "results" / "fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity_20260529_221108"
STEP12C = ROOT / "results" / "fossum_roi_x490_step12c_methodological_justification_20260530_035759"
OUT = ROOT / "docs" / "lucid_trajectory_results"
ASSETS = OUT / "assets"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_TITLE = font(44, True)
FONT_H = font(27, True)
FONT_SUB = font(19)
FONT_BODY = font(22)
FONT_SMALL = font(17)


def sha10(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def find_plot(base: Path, physical_run_id: str) -> Path:
    suffix = sha10(physical_run_id)
    candidates = list((base / "planner_runs").glob(f"*{suffix}/plots/*.png"))
    if not candidates:
        raise FileNotFoundError(f"No plot found for {physical_run_id} ({suffix})")
    return candidates[0]


def copy_asset(source: Path, name: str) -> Path:
    target = ASSETS / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def make_step12a_chart() -> Path:
    df = pd.read_csv(STEP12A / "step12a_alpha_sensitivity_summary.csv")
    plt.figure(figsize=(8.5, 4.7), dpi=180)
    for descriptor, group in df.groupby("descriptor"):
        group = group.sort_values("alpha")
        label = descriptor.replace("_", " ")
        plt.plot(group["alpha"], group["mean_score"], marker="o", linewidth=2.2, label=label)
    plt.title("Single-AUV descriptor sensitivity")
    plt.xlabel("alpha")
    plt.ylabel("mean recommendation score")
    plt.ylim(0.45, 0.66)
    plt.grid(True, alpha=0.25)
    plt.legend(frameon=False, ncol=1)
    plt.tight_layout()
    out = ASSETS / "step12a_alpha_sensitivity.png"
    plt.savefig(out)
    plt.close()
    return out


def make_step12b_chart() -> Path:
    df = pd.read_csv(STEP12B / "step12b_weight_sensitivity_summary.csv")
    df = df.sort_values("mean_score", ascending=True)
    labels = df["strategy"].str.replace("vehicle_specific_", "veh. ", regex=False).str.replace(
        "baseline_shared_STD", "baseline STD", regex=False
    )
    colors = ["#5c8796" if "veh. 6040" not in label else "#c96f4a" for label in labels]
    plt.figure(figsize=(8.5, 5.6), dpi=180)
    plt.barh(labels, df["mean_score"], color=colors)
    plt.title("Multi-AUV weight sensitivity")
    plt.xlabel("mean recommendation score")
    plt.xlim(0.42, 0.64)
    plt.grid(True, axis="x", alpha=0.25)
    plt.tight_layout()
    out = ASSETS / "step12b_weight_sensitivity.png"
    plt.savefig(out)
    plt.close()
    return out


def wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, width: int, fnt, fill) -> int:
    x, y = xy
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    line_h = int(fnt.size * 1.25)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def round_rect(draw, box, fill, outline, radius=18, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def add_box(draw, box, title, body, fill="#ffffff", outline="#31576b"):
    round_rect(draw, box, fill, outline)
    x1, y1, x2, _ = box
    draw.text((x1 + 24, y1 + 18), title, font=FONT_H, fill="#12313f")
    wrapped(draw, (x1 + 24, y1 + 58), body, 40, FONT_SMALL, "#26383f")


def paste_thumb(canvas: Image.Image, draw: ImageDraw.ImageDraw, path: Path, box, title: str, caption: str):
    x1, y1, x2, y2 = box
    round_rect(draw, box, "#ffffff", "#c7d3d8", radius=14, width=2)
    inner_w = x2 - x1 - 28
    inner_h = y2 - y1 - 92
    img = Image.open(path).convert("RGB")
    img.thumbnail((inner_w, inner_h), Image.LANCZOS)
    px = x1 + 14 + (inner_w - img.width) // 2
    py = y1 + 48 + (inner_h - img.height) // 2
    canvas.paste(img, (px, py))
    draw.text((x1 + 16, y1 + 14), title, font=FONT_SUB, fill="#12313f")
    wrapped(draw, (x1 + 16, y2 - 42), caption, 36, FONT_SMALL, "#4b5960")


def make_manifest(selected: list[dict[str, str]]) -> None:
    with (OUT / "selected_images_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["asset", "source", "why_selected"])
        writer.writeheader()
        writer.writerows(selected)


def make_markdown(selected: list[dict[str, str]]) -> None:
    md = [
        "# Lucid trajectory-results diagram",
        "",
        "Use `trajectory_results_lucid_board.png` as a single image in Lucid, or rebuild the board with the assets in `assets/`.",
        "",
        "Suggested Lucid structure:",
        "1. Methods: prototype classes and descriptor maps.",
        "2. Single-AUV sensitivity: alpha sweep and representative trajectory maps.",
        "3. Multi-AUV sensitivity: vehicle-specific 60/40 recommendation and AUV role maps.",
        "4. Final recommendation: 60/40 vehicle-specific maps for multi-AUV, with the proxy/wrapper limitation stated.",
        "",
        "Selected assets:",
    ]
    for row in selected:
        md.append(f"- `{row['asset']}`: {row['why_selected']}")
    (OUT / "lucid_layout_notes.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def make_svg_from_png(png: Path) -> Path:
    data = base64.b64encode(png.read_bytes()).decode("ascii")
    svg = OUT / "trajectory_results_lucid_board.svg"
    svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="2200" viewBox="0 0 1800 2200">'
        f'<image width="1800" height="2200" href="data:image/png;base64,{data}"/></svg>\n',
        encoding="utf-8",
    )
    return svg


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    step12a_manifest = pd.read_csv(STEP12A / "step12a_run_manifest.csv")
    single_specs = [
        ("C01_representative", 12.0, "boundary_score", "boundary_score_alpha050", "Single C01 12h: boundary score alpha 0.50"),
        ("C06_representative", 48.0, "interest_map", "interest_map_alpha075", "Single C06 48h: interest map alpha 0.75"),
        ("October_control", 48.0, "representative_zone", "representative_zone_alpha050", "Single October 48h: representative zone alpha 0.50"),
    ]
    selected: list[dict[str, str]] = []
    copied: dict[str, Path] = {}
    for case_id, duration, descriptor, run_name, why in single_specs:
        row = step12a_manifest[
            (step12a_manifest["case_id"] == case_id)
            & (step12a_manifest["mission_duration_requested_h"] == duration)
            & (step12a_manifest["descriptor"] == descriptor)
            & (step12a_manifest["run_name"] == run_name)
        ].iloc[0]
        src = find_plot(STEP12A, row["physical_run_id"])
        name = f"{case_id}_{int(duration)}h_{run_name}.png"
        copied[name] = copy_asset(src, name)
        selected.append({"asset": name, "source": str(src.relative_to(ROOT)), "why_selected": why})

    step12b_manifest = pd.read_csv(STEP12B / "step12b_run_manifest.csv")
    multi_specs = [
        ("C06_representative", 48.0, "vehicle_specific_6040", 1, "Multi C06 48h: AUV1 region A, recommended 60/40"),
        ("C06_representative", 48.0, "vehicle_specific_6040", 2, "Multi C06 48h: AUV2 region B, recommended 60/40"),
    ]
    for case_id, duration, strategy, vehicle_id, why in multi_specs:
        row = step12b_manifest[
            (step12b_manifest["case_id"] == case_id)
            & (step12b_manifest["mission_duration_requested_h"] == duration)
            & (step12b_manifest["strategy"] == strategy)
            & (step12b_manifest["vehicle_id"].astype(str) == str(vehicle_id))
        ].iloc[0]
        src = find_plot(STEP12B, row["physical_run_id"])
        name = f"{case_id}_{int(duration)}h_{strategy}_AUV{vehicle_id}.png"
        copied[name] = copy_asset(src, name)
        selected.append({"asset": name, "source": str(src.relative_to(ROOT)), "why_selected": why})

    chart_a = make_step12a_chart()
    chart_b = make_step12b_chart()
    selected.extend(
        [
            {"asset": chart_a.name, "source": "generated from step12a_alpha_sensitivity_summary.csv", "why_selected": "Single-AUV descriptor/alpha evidence"},
            {"asset": chart_b.name, "source": "generated from step12b_weight_sensitivity_summary.csv", "why_selected": "Multi-AUV final weight evidence"},
        ]
    )

    canvas = Image.new("RGB", (1800, 2200), "#f4f7f8")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1800, 150), fill="#163847")
    draw.text((60, 38), "Trajectory Results: Final Planning Evidence", font=FONT_TITLE, fill="#ffffff")
    draw.text(
        (60, 96),
        "Prototype-based objective maps only; TEMPpred is diagnostic background, not the trajectory objective.",
        font=FONT_BODY,
        fill="#dbe8ec",
    )

    add_box(
        draw,
        (60, 190, 500, 405),
        "1. Inputs",
        "Classes and descriptor maps define the objective layers: STD, boundary score, interest map, and representative zones.",
        "#ffffff",
        "#31576b",
    )
    add_box(
        draw,
        (560, 190, 1000, 405),
        "2. Single-AUV",
        "Step12A tests descriptor weight alpha across C01, C06, and October for 12h, 24h, and 48h missions.",
        "#ffffff",
        "#31576b",
    )
    add_box(
        draw,
        (1060, 190, 1440, 405),
        "3. Multi-AUV",
        "Step12B tests vehicle-specific maps. The strongest repeated recommendation is 60/40 STD-region weighting.",
        "#ffffff",
        "#31576b",
    )
    add_box(
        draw,
        (1500, 190, 1740, 405),
        "Final",
        "Use Step12B as the main route-level result, with proxy-wrapper limitation stated.",
        "#fff4ee",
        "#c96f4a",
    )
    for x in [520, 1020, 1460]:
        draw.line((x, 300, x + 35, 300), fill="#31576b", width=5)
        draw.polygon([(x + 35, 300), (x + 20, 290), (x + 20, 310)], fill="#31576b")

    paste_thumb(canvas, draw, chart_a, (60, 455, 850, 875), "Single-AUV sensitivity", "Representative zones peak globally; boundary and interest remain strong.")
    paste_thumb(canvas, draw, chart_b, (910, 455, 1740, 875), "Multi-AUV sensitivity", "Vehicle-specific 60/40 has the best mean score and good specialization.")

    y = 935
    draw.text((60, y), "Trajectory maps selected for Lucid", font=FONT_H, fill="#12313f")
    y += 50
    boxes = [
        ((60, y, 590, y + 430), copied["C01_representative_12h_boundary_score_alpha050.png"], "C01 12h single AUV", "Boundary alpha 0.50; top C01 12h score."),
        ((620, y, 1190, y + 430), copied["C06_representative_48h_interest_map_alpha075.png"], "C06 48h single AUV", "Interest alpha 0.75; strong 48h C06 score."),
        ((1220, y, 1740, y + 430), copied["October_control_48h_representative_zone_alpha050.png"], "October 48h single AUV", "Representative zone alpha 0.50; best October trajectory choice."),
    ]
    for box, path, title, cap in boxes:
        paste_thumb(canvas, draw, path, box, title, cap)

    y += 500
    boxes = [
        ((160, y, 850, y + 500), copied["C06_representative_48h_vehicle_specific_6040_AUV1.png"], "C06 48h multi-AUV: AUV1", "Vehicle-specific 60/40; role A: region A."),
        ((960, y, 1650, y + 500), copied["C06_representative_48h_vehicle_specific_6040_AUV2.png"], "C06 48h multi-AUV: AUV2", "Vehicle-specific 60/40; role B: region B."),
    ]
    for box, path, title, cap in boxes:
        paste_thumb(canvas, draw, path, box, title, cap)

    y += 560
    round_rect(draw, (60, y, 1740, y + 150), "#fff4ee", "#c96f4a", radius=18, width=2)
    draw.text((90, y + 26), "Thesis-ready conclusion", font=FONT_H, fill="#12313f")
    conclusion = (
        "Use Step12A as evidence that route objectives respond to descriptor weighting. "
        "Use Step12B as the final trajectory result: vehicle-specific 60/40 STD-region maps "
        "produce stronger multi-AUV specialization with low route overlap, while remaining a proxy/wrapper implementation."
    )
    wrapped(draw, (90, y + 70), conclusion, 135, FONT_BODY, "#26383f")

    png = OUT / "trajectory_results_lucid_board.png"
    canvas.save(png, quality=95)
    make_svg_from_png(png)
    make_manifest(selected)
    make_markdown(selected)
    print(png)


if __name__ == "__main__":
    main()
