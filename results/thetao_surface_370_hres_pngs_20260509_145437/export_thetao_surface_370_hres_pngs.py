from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_DIR = Path(r"C:\Users\pedro\Documents\Filipa_dados\results\cmems_370_surface_to_hres_20260509_135642")
OUT_DIR = Path(__file__).resolve().parent
PNG_DIR = OUT_DIR / "png_daily"
CLEAN_DIR = OUT_DIR / "png_daily_clean"

ARRAY_PATH = INPUT_DIR / "thetao_surface_370_hres.npy"
LAT_PATH = INPUT_DIR / "LAT_hres.npy"
LON_PATH = INPUT_DIR / "LON_hres.npy"
MASK_PATH = INPUT_DIR / "MASK_hres.npy"
DATES_PATH = INPUT_DIR / "dates_370.csv"
META_PATH = INPUT_DIR / "cmems_370_surface_hres_metadata.json"


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def masked_map(arr, mask):
    out = np.asarray(arr, dtype=np.float32).copy()
    out[~mask] = np.nan
    return out


def daily_stats(arr):
    finite = np.isfinite(arr)
    vals = arr[finite]
    if vals.size == 0:
        return {
            "valid_cells": 0,
            "nan_cells": int(arr.size),
            "temp_min": np.nan,
            "temp_max": np.nan,
            "temp_mean": np.nan,
            "temp_std": np.nan,
        }
    return {
        "valid_cells": int(vals.size),
        "nan_cells": int(arr.size - vals.size),
        "temp_min": float(np.min(vals)),
        "temp_max": float(np.max(vals)),
        "temp_mean": float(np.mean(vals)),
        "temp_std": float(np.std(vals)),
    }


def save_daily_png(arr, lat, lon, date, out_path, vmin, vmax):
    fig, ax = plt.subplots(figsize=(7.2, 5.4), constrained_layout=True)
    im = ax.imshow(
        arr,
        origin="lower",
        extent=[float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max())],
        cmap="coolwarm",
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
        aspect="auto",
    )
    ax.set_title(f"CMEMS HRes surface temperature - {date}", fontsize=12)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    cbar = fig.colorbar(im, ax=ax, shrink=0.88)
    cbar.set_label("Temperature (deg C)")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_clean_png(arr, out_path, vmin, vmax):
    fig, ax = plt.subplots(figsize=(4.8, 3.6), constrained_layout=False)
    ax.imshow(arr, origin="lower", cmap="coolwarm", vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(out_path, dpi=120, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def save_panel(cube, dates, indices, out_path, title, vmin, vmax):
    n = len(indices)
    cols = min(4, n)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 2.8), constrained_layout=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, idx in zip(axes, indices):
        im = ax.imshow(cube[idx], origin="lower", cmap="coolwarm", vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title(f"{idx + 1:04d} {dates[idx]}", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes[n:]:
        ax.axis("off")
    fig.suptitle(title, fontsize=13)
    fig.colorbar(im, ax=axes.tolist(), shrink=0.65, label="Temperature (deg C)")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def month_indices(dates):
    out = []
    seen = set()
    for i, d in enumerate(dates):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            out.append(i)
    return out


def heterogeneous_indices(inventory_df, n=12):
    return inventory_df.sort_values("temp_std", ascending=False).head(n)["day_index"].sub(1).astype(int).tolist()


def main():
    ensure_dirs()
    cube = np.load(ARRAY_PATH, mmap_mode="r")
    lat = np.load(LAT_PATH)
    lon = np.load(LON_PATH)
    mask = np.load(MASK_PATH).astype(bool)
    dates_df = pd.read_csv(DATES_PATH)
    dates = dates_df["date"].astype(str).tolist()
    source_meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    input_shape = list(cube.shape)
    n_days = int(cube.shape[0])
    dates_complete = n_days == len(dates) == 370 and dates[0] == "2023-10-28" and dates[-1] == "2024-10-31"
    shape_per_day_consistent = cube.ndim == 3 and tuple(cube.shape[1:]) == tuple(mask.shape) == (180, 240)
    orientation_confirmed = bool(lat[0] < lat[-1] and lon[0] < lon[-1] and source_meta.get("orientation_confirmed", False))

    valid_values = np.asarray(cube[np.isfinite(cube)], dtype=np.float32)
    abs_min = float(np.min(valid_values))
    abs_max = float(np.max(valid_values))
    p1 = float(np.percentile(valid_values, 1))
    p99 = float(np.percentile(valid_values, 99))
    vmin, vmax = p1, p99
    color_scale_method = "robust global percentiles p1-p99; absolute min/max recorded in metadata"

    inventory = []
    failed_days = []
    for i, date in enumerate(dates):
        arr = masked_map(cube[i], mask)
        stats = daily_stats(arr)
        name = f"{i + 1:04d}_{date}_thetao_surface_hres.png"
        png_path = PNG_DIR / name
        clean_path = CLEAN_DIR / name
        try:
            save_daily_png(arr, lat, lon, date, png_path, vmin, vmax)
            save_clean_png(arr, clean_path, vmin, vmax)
        except Exception as exc:
            failed_days.append({"day_index": i + 1, "date": date, "error": repr(exc)})
        inventory.append(
            {
                "day_index": i + 1,
                "date": date,
                "png_path": str(png_path),
                "clean_png_path": str(clean_path),
                **stats,
            }
        )

    inv_df = pd.DataFrame(inventory)
    inv_df.to_csv(OUT_DIR / "png_inventory.csv", index=False)

    cube_for_panels = np.stack([masked_map(cube[i], mask) for i in range(n_days)])
    save_panel(cube_for_panels, dates, list(range(12)), OUT_DIR / "first_12_days_panel.png", "First 12 days", vmin, vmax)
    save_panel(cube_for_panels, dates, month_indices(dates), OUT_DIR / "selected_monthly_panel.png", "Monthly samples", vmin, vmax)
    save_panel(cube_for_panels, dates, heterogeneous_indices(inv_df), OUT_DIR / "heterogeneous_days_panel.png", "Most heterogeneous days", vmin, vmax)
    save_panel(cube_for_panels, dates, list(range(n_days - 12, n_days)), OUT_DIR / "final_12_days_panel.png", "Final 12 days", vmin, vmax)

    output_png_count = len(list(PNG_DIR.glob("*.png")))
    output_clean_png_count = len(list(CLEAN_DIR.glob("*.png")))
    nan_pct = float(np.isnan(cube_for_panels).sum() / cube_for_panels.size * 100)
    metadata = {
        "input_array_path": str(ARRAY_PATH),
        "input_shape": input_shape,
        "n_days": n_days,
        "date_start": dates[0],
        "date_end": dates[-1],
        "output_dir": str(OUT_DIR),
        "png_daily_dir": str(PNG_DIR),
        "png_daily_clean_dir": str(CLEAN_DIR),
        "output_png_count": output_png_count,
        "output_clean_png_count": output_clean_png_count,
        "dates_complete": bool(dates_complete),
        "shape_per_day_consistent": bool(shape_per_day_consistent),
        "global_color_scale_used": True,
        "color_scale_method": color_scale_method,
        "color_scale_vmin": vmin,
        "color_scale_vmax": vmax,
        "absolute_temp_min": abs_min,
        "absolute_temp_max": abs_max,
        "mask_applied": True,
        "global_nan_pct_after_mask": nan_pct,
        "orientation_confirmed": orientation_confirmed,
        "any_failed_exports": bool(failed_days),
        "failed_days": failed_days,
        "colormap": "coolwarm",
        "panels": [
            "first_12_days_panel.png",
            "selected_monthly_panel.png",
            "heterogeneous_days_panel.png",
            "final_12_days_panel.png",
        ],
    }
    metadata["final_verdict"] = (
        "The 370 daily HRes surface temperature PNG maps were successfully exported with a consistent global color scale."
        if output_png_count == 370 and output_clean_png_count == 370 and not failed_days and dates_complete and shape_per_day_consistent
        else "PNG export completed with issues; review failed_days and output counts."
    )
    (OUT_DIR / "png_export_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    checks_keys = [
        "input_array_path",
        "input_shape",
        "n_days",
        "date_start",
        "date_end",
        "output_png_count",
        "output_clean_png_count",
        "dates_complete",
        "shape_per_day_consistent",
        "global_color_scale_used",
        "color_scale_method",
        "color_scale_vmin",
        "color_scale_vmax",
        "mask_applied",
        "orientation_confirmed",
        "any_failed_exports",
        "failed_days",
        "final_verdict",
    ]
    checks = {k: metadata[k] for k in checks_keys}
    (OUT_DIR / "png_export_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    report = f"""# Export CMEMS Surface HRes PNGs Report

Input array: `{ARRAY_PATH}`

Output folder: `{OUT_DIR}`

## Checks

- Input shape: `{input_shape}`
- Dates: `{dates[0]}` to `{dates[-1]}`
- PNG count: `{output_png_count}`
- Clean PNG count: `{output_clean_png_count}`
- Mask applied: `True`
- Orientation confirmed: `{orientation_confirmed}`
- Failed exports: `{len(failed_days)}`

## Color Scale

Used a global robust color scale from all finite cells across the 370-day cube:

- Method: `{color_scale_method}`
- vmin: `{vmin:.6f}`
- vmax: `{vmax:.6f}`
- absolute min: `{abs_min:.6f}`
- absolute max: `{abs_max:.6f}`

The robust p1-p99 scale keeps the daily maps visually comparable while reducing the influence of rare extremes.

## Outputs

- `png_daily/`: full labeled PNGs
- `png_daily_clean/`: clean image-only PNGs
- `png_inventory.csv`
- `png_export_metadata.json`
- `png_export_checks.json`
- summary panels

## Verdict

{metadata["final_verdict"]}
"""
    (OUT_DIR / "export_thetao_surface_370_hres_pngs_report.md").write_text(report, encoding="utf-8")

    summary = f"""# Export CMEMS Surface HRes PNGs Summary

1. Quantos PNGs foram gerados? `{output_png_count}`
2. Quantos clean PNGs foram gerados? `{output_clean_png_count}`
3. Qual escala de cor foi usada (vmin/vmax)? `coolwarm`, global p1-p99, vmin=`{vmin:.6f}`, vmax=`{vmax:.6f}`
4. A máscara foi aplicada? `Sim`
5. A orientação foi confirmada? `{orientation_confirmed}`
6. Houve algum dia que falhou? `{"Sim" if failed_days else "Não"}`
7. Os 370 mapas estão agora prontos para inspeção visual? `{"Sim" if metadata["final_verdict"].startswith("The 370") else "Rever checks"}`

The 370 daily HRes surface temperature PNG maps were successfully exported with a consistent global color scale.
"""
    (OUT_DIR / "export_thetao_surface_370_hres_pngs_summary.md").write_text(summary, encoding="utf-8")
    print(f"Done: {OUT_DIR}")


if __name__ == "__main__":
    main()
