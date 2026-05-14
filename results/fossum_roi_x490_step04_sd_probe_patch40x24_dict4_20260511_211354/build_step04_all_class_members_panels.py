from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STEP00 = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"
CLEAN_PNG_DIR = STEP00 / "normalized_clean_pngs"


def load_font(size: int) -> ImageFont.ImageFont:
    for path in [Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/calibri.ttf")]:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def load_dates() -> pd.DataFrame:
    dates = pd.read_csv(STEP00 / "dates_370.csv")
    dates["date"] = pd.to_datetime(dates["date"]).dt.strftime("%Y-%m-%d")
    if "day_index" not in dates.columns:
        dates.insert(0, "day_index", range(1, len(dates) + 1))
    return dates


def clean_png_path(day_index: int, date: str) -> Path:
    return CLEAN_PNG_DIR / f"{day_index:04d}_{date}_X_surface_370_roi_x490_norm_clean.png"


def read_class_members(sd_dir: Path) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for csv_path in sorted(sd_dir.glob("class_*_distance_to_prototype.csv")):
        class_id = int(csv_path.stem.split("_")[1])
        df = pd.read_csv(csv_path)
        if "image_idx_0_based" not in df.columns:
            raise RuntimeError(f"Missing image_idx_0_based in {csv_path}")
        indices = sorted(int(v) for v in df["image_idx_0_based"].tolist())
        out[class_id] = indices
    if not out:
        raise RuntimeError(f"No class distance files found in {sd_dir}")
    return out


def make_panel(sd_dir: Path, dates: pd.DataFrame, out_path: Path) -> dict:
    members = read_class_members(sd_dir)
    thumb_w, thumb_h = 96, 68
    label_h = 15
    gap_x, gap_y = 8, 8
    margin = 18
    heading_h = 26
    cols = 18
    header_font = load_font(18)
    small_font = load_font(10)

    sections = []
    total_height = margin + 38
    for class_id in sorted(members):
        idx = members[class_id]
        rows = max(1, (len(idx) + cols - 1) // cols)
        sec_h = heading_h + rows * (thumb_h + label_h + gap_y) + 16
        sections.append((class_id, idx, rows, sec_h))
        total_height += sec_h

    width = margin * 2 + cols * thumb_w + (cols - 1) * gap_x
    height = total_height + margin
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    sd_label = sd_dir.name
    title = f"Step04 SD probe | {sd_label} | patch=40x24 | xds=4 | seed=11 | n=370"
    draw.text((margin, margin), title, fill="black", font=header_font)
    y = margin + 34
    missing_pngs = []

    for class_id, idx, rows, _sec_h in sections:
        draw.text((margin, y), f"Class {class_id:02d} (n={len(idx)})", fill="black", font=header_font)
        y += heading_h
        for k, img_idx in enumerate(idx):
            row = k // cols
            col = k % cols
            x = margin + col * (thumb_w + gap_x)
            yy = y + row * (thumb_h + label_h + gap_y)
            date_row = dates.iloc[img_idx]
            day_index = int(date_row["day_index"])
            date = str(date_row["date"])
            png_path = clean_png_path(day_index, date)
            if png_path.exists():
                with Image.open(png_path) as im:
                    im = im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas.paste(im, (x, yy))
            else:
                missing_pngs.append(str(png_path))
                draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline="red", fill=(245, 245, 245))
                draw.text((x + 5, yy + 20), "missing", fill="red", font=small_font)
            draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline=(180, 180, 180))
            draw.text((x, yy + thumb_h + 1), f"{day_index:03d} {date[5:]}", fill="black", font=small_font)
        y += rows * (thumb_h + label_h + gap_y) + 16

    canvas.save(out_path, optimize=True)
    return {
        "sd_dir": sd_dir.name,
        "panel_path": str(out_path),
        "n_classes": len(members),
        "class_sizes": {f"C{cid:02d}": len(idx) for cid, idx in members.items()},
        "missing_png_count": len(missing_pngs),
        "missing_pngs": missing_pngs,
    }


def main() -> None:
    dates = load_dates()
    rows = []
    for sd_dir in sorted(OUT.glob("sd_*pct")):
        if not sd_dir.is_dir():
            continue
        panel_path = OUT / f"{sd_dir.name}_all_members_by_class.png"
        result = make_panel(sd_dir=sd_dir, dates=dates, out_path=panel_path)
        rows.append(result)
        # Also place a copy inside the SD folder, close to the original partial panels.
        local_copy = sd_dir / f"{sd_dir.name}_all_members_by_class.png"
        if local_copy.resolve() != panel_path.resolve():
            with Image.open(panel_path) as im:
                im.save(local_copy, optimize=True)

    pd.DataFrame(
        [
            {
                "sd_dir": r["sd_dir"],
                "panel_path": r["panel_path"],
                "n_classes": r["n_classes"],
                "class_sizes": json.dumps(r["class_sizes"]),
                "missing_png_count": r["missing_png_count"],
            }
            for r in rows
        ]
    ).to_csv(OUT / "step04_all_members_panels_inventory.csv", index=False)
    (OUT / "step04_all_members_panels_checks.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
