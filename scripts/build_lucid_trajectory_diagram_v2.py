from __future__ import annotations

import base64
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
OUT = ROOT / "docs" / "lucid_trajectory_results_v2"
ASSETS = OUT / "assets"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(54, True)
F_H = font(34, True)
F_BODY = font(25)
F_SMALL = font(20)
F_TINY = font(17)


def sha10(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def find_plot(base: Path, physical_run_id: str) -> Path:
    suffix = sha10(physical_run_id)
    matches = list((base / "planner_runs").glob(f"*{suffix}/plots/*.png"))
    if not matches:
        raise FileNotFoundError(f"Missing plot for {physical_run_id}")
    return matches[0]


def copy_asset(src: Path, name: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    dst = ASSETS / name
    shutil.copy2(src, dst)
    return dst


def wrap_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, width: int, fnt, fill: str) -> int:
    x, y = xy
    for line in textwrap.wrap(text, width=width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * 1.22)
    return y


def card(draw: ImageDraw.ImageDraw, box, fill="#ffffff", outline="#b8c8cf", width=2):
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=width)


def arrow(draw: ImageDraw.ImageDraw, start, end, color="#2f5d6b"):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2 - 18, y2), fill=color, width=5)
    draw.polygon([(x2, y2), (x2 - 22, y2 - 13), (x2 - 22, y2 + 13)], fill=color)


def paste_image(canvas: Image.Image, draw: ImageDraw.ImageDraw, path: Path, box, title: str, caption: str):
    x1, y1, x2, y2 = box
    card(draw, box)
    draw.text((x1 + 22, y1 + 18), title, font=F_H, fill="#163847")
    img = Image.open(path).convert("RGB")
    max_w = x2 - x1 - 48
    max_h = y2 - y1 - 112
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    px = x1 + 24 + (max_w - img.width) // 2
    py = y1 + 70 + (max_h - img.height) // 2
    canvas.paste(img, (px, py))
    wrap_text(draw, (x1 + 24, y2 - 42), caption, 55, F_SMALL, "#41535b")


def make_weight_chart() -> Path:
    df = pd.read_csv(STEP12B / "step12b_weight_sensitivity_summary.csv")
    df = df.sort_values("mean_score", ascending=False).head(6).sort_values("mean_score")
    labels = (
        df["strategy"]
        .str.replace("vehicle_specific_", "", regex=False)
        .str.replace("baseline_shared_STD", "baseline STD", regex=False)
    )
    colors = ["#cc6f4b" if label == "6040" else "#5e8795" for label in labels]
    plt.figure(figsize=(6.7, 3.0), dpi=220)
    plt.barh(labels, df["mean_score"], color=colors)
    plt.xlabel("score medio")
    plt.title("Escolha dos pesos multi-AUV")
    plt.xlim(0.50, 0.63)
    plt.grid(axis="x", alpha=0.22)
    plt.tight_layout()
    out = ASSETS / "v2_weight_choice.png"
    plt.savefig(out)
    plt.close()
    return out


def make_alpha_chart() -> Path:
    df = pd.read_csv(STEP12A / "step12a_alpha_sensitivity_summary.csv")
    plt.figure(figsize=(6.7, 3.0), dpi=220)
    for descriptor, group in df.groupby("descriptor"):
        group = group.sort_values("alpha")
        plt.plot(group["alpha"], group["mean_score"], marker="o", linewidth=2.1, label=descriptor.replace("_", " "))
    plt.xlabel("alpha")
    plt.ylabel("score medio")
    plt.title("Sensibilidade single-AUV")
    plt.grid(alpha=0.22)
    plt.legend(frameon=False, fontsize=8)
    plt.tight_layout()
    out = ASSETS / "v2_single_sensitivity.png"
    plt.savefig(out)
    plt.close()
    return out


def svg_embed(png: Path, svg: Path, width: int, height: int) -> None:
    data = base64.b64encode(png.read_bytes()).decode("ascii")
    svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<image width="{width}" height="{height}" href="data:image/png;base64,{data}"/></svg>\n',
        encoding="utf-8",
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    m12a = pd.read_csv(STEP12A / "step12a_run_manifest.csv")
    m12b = pd.read_csv(STEP12B / "step12b_run_manifest.csv")

    single_row = m12a[
        (m12a["case_id"] == "C06_representative")
        & (m12a["mission_duration_requested_h"] == 48.0)
        & (m12a["descriptor"] == "interest_map")
        & (m12a["run_name"] == "interest_map_alpha075")
    ].iloc[0]
    single = copy_asset(find_plot(STEP12A, single_row["physical_run_id"]), "single_C06_48h_interest_alpha075.png")

    auv_paths = []
    for vehicle_id in [1, 2]:
        row = m12b[
            (m12b["case_id"] == "C06_representative")
            & (m12b["mission_duration_requested_h"] == 48.0)
            & (m12b["strategy"] == "vehicle_specific_6040")
            & (m12b["vehicle_id"].astype(str) == str(vehicle_id))
        ].iloc[0]
        auv_paths.append(
            copy_asset(
                find_plot(STEP12B, row["physical_run_id"]),
                f"multi_C06_48h_6040_AUV{vehicle_id}.png",
            )
        )

    weight_chart = make_weight_chart()
    alpha_chart = make_alpha_chart()

    W, H = 1920, 1400
    canvas = Image.new("RGB", (W, H), "#f5f8f8")
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, W, 135), fill="#143846")
    draw.text((64, 30), "Resultados finais da trajetória", font=F_TITLE, fill="#ffffff")
    draw.text((66, 92), "Comparação direta entre single-AUV e a recomendação multi-AUV 60/40", font=F_BODY, fill="#d8e6ea")

    # Compact flow.
    flow_y = 178
    labels = [
        ("Mapas objetivo", "STD + descritores"),
        ("Single-AUV", "teste de alpha"),
        ("Multi-AUV", "papeis por veiculo"),
        ("Recomendação", "60/40 STD-região"),
    ]
    xs = [80, 520, 960, 1400]
    for x, (title, body) in zip(xs, labels):
        fill = "#fff0e9" if title == "Recomendação" else "#ffffff"
        outline = "#cc6f4b" if title == "Recomendação" else "#9fb7c0"
        card(draw, (x, flow_y, x + 330, flow_y + 135), fill=fill, outline=outline, width=3)
        draw.text((x + 24, flow_y + 24), title, font=F_H, fill="#163847")
        draw.text((x + 24, flow_y + 76), body, font=F_SMALL, fill="#4a5b62")
    for x in [430, 870, 1310]:
        arrow(draw, (x, flow_y + 68), (x + 70, flow_y + 68))

    paste_image(
        canvas,
        draw,
        single,
        (70, 380, 610, 910),
        "Single-AUV",
        "C06, 48h, interest map alpha 0.75.",
    )
    paste_image(
        canvas,
        draw,
        auv_paths[0],
        (660, 380, 1260, 910),
        "Multi-AUV: AUV1",
        "C06, 48h, 60/40. Papel: região A.",
    )
    paste_image(
        canvas,
        draw,
        auv_paths[1],
        (1310, 380, 1850, 910),
        "Multi-AUV: AUV2",
        "C06, 48h, 60/40. Papel: região B.",
    )

    paste_image(
        canvas,
        draw,
        alpha_chart,
        (70, 980, 610, 1290),
        "Evidência single-AUV",
        "Os descritores alteram a rota mantendo retenção de STD aceitável.",
    )
    paste_image(
        canvas,
        draw,
        weight_chart,
        (660, 980, 1260, 1290),
        "Evidência multi-AUV",
        "O peso 60/40 tem o melhor score médio nas estratégias testadas.",
    )

    card(draw, (1310, 980, 1850, 1290), fill="#fff0e9", outline="#cc6f4b", width=3)
    draw.text((1340, 1018), "Mensagem final", font=F_H, fill="#163847")
    final = (
        "Para a secção de trajetória, usar Step12B como resultado principal: "
        "mapas específicos por veículo com 60% STD e 40% região aumentam a especialização "
        "dos AUVs e mantêm baixa sobreposição de trajetórias. Indicar que é uma implementação proxy/wrapper."
    )
    wrap_text(draw, (1340, 1078), final, 47, F_BODY, "#26383f")

    png = OUT / "trajectory_results_lucid_board_v2.png"
    svg = OUT / "trajectory_results_lucid_board_v2.svg"
    canvas.save(png, quality=95)
    svg_embed(png, svg, W, H)

    notes = OUT / "lucid_layout_notes_v2.md"
    notes.write_text(
        "\n".join(
            [
                "# Diagrama Lucid v2: trajetoria",
                "",
                "Versao mais limpa e focada nos resultados finais da trajetoria.",
                "",
                "Importar no Lucid:",
                "- Use `trajectory_results_lucid_board_v2.png` para uma prancha pronta.",
                "- Use as imagens em `assets/` se quiser montar os blocos manualmente.",
                "",
                "Mensagem principal:",
                "Step12B e o resultado final da trajetoria. O caso visual central e C06 48h com mapas especificos por veiculo e pesos 60/40.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(png)


if __name__ == "__main__":
    main()
