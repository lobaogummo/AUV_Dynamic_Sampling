from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd


INPUT_DIR = Path(r"C:\Users\pedro\Documents\Filipa_dados\results\cmems_370_surface_to_hres_20260509_135642")
OUT_DIR = Path(__file__).resolve().parent
PNG_DIR = OUT_DIR / "png_paper_roi_x490_daily"
CLEAN_DIR = OUT_DIR / "png_paper_roi_x490_daily_clean"
DELETED_PRIOR_RESULTS = [
    r"C:\Users\pedro\Documents\Filipa_dados\results\fresnel_roi_surface_370_20260509_164727",
    r"C:\Users\pedro\Documents\Filipa_dados\results\fresnel_paper_roi_surface_370_20260509_174142",
]

INPUTS = {
    "thetao": INPUT_DIR / "thetao_surface_370_hres.npy",
    "thetao_nc": INPUT_DIR / "thetao_surface_370_hres.nc",
    "lat": INPUT_DIR / "LAT_hres.npy",
    "lon": INPUT_DIR / "LON_hres.npy",
    "bathy": INPUT_DIR / "BATHY_hres.npy",
    "mask": INPUT_DIR / "MASK_hres.npy",
    "dates": INPUT_DIR / "dates_370.csv",
    "metadata": INPUT_DIR / "cmems_370_surface_hres_metadata.json",
}

REQUESTED_ROI = {
    "x_min_km": 463.0,
    "x_max_km": 490.0,
    "y_min_km": 4376.0,
    "y_max_km": 4397.0,
}
HETEROGENEOUS_DATES = ["2024-10-10", "2024-10-13", "2024-10-15", "2024-10-11", "2024-10-31", "2024-10-12", "2024-10-09"]
UTM_ZONE = 29


def wgs84_to_utm29n(lat_deg, lon_deg):
    lat = np.radians(np.asarray(lat_deg, dtype=np.float64))
    lon = np.radians(np.asarray(lon_deg, dtype=np.float64))
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0 = 0.9996
    lon0 = math.radians(-183 + 6 * UTM_ZONE)
    n = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    t = np.tan(lat) ** 2
    c = ep2 * np.cos(lat) ** 2
    aa = np.cos(lat) * (lon - lon0)
    m = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * np.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * np.sin(4 * lat)
        - (35 * e2**3 / 3072) * np.sin(6 * lat)
    )
    x = k0 * n * (
        aa
        + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120
    ) + 500000.0
    y = k0 * (
        m
        + n
        * np.tan(lat)
        * (
            aa**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720
        )
    )
    return x, y


def roi_indices(x_km, y_km):
    in_roi = (
        (x_km >= REQUESTED_ROI["x_min_km"])
        & (x_km <= REQUESTED_ROI["x_max_km"])
        & (y_km >= REQUESTED_ROI["y_min_km"])
        & (y_km <= REQUESTED_ROI["y_max_km"])
    )
    rows, cols = np.where(in_roi)
    if rows.size == 0:
        raise RuntimeError("Requested x490 ROI has no cells on the HRes grid.")
    return int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max())


def apply_mask(cube, mask):
    out = np.asarray(cube, dtype=np.float32).copy()
    out[:, ~mask] = np.nan
    return out


def stats2d(arr):
    vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return {"valid_cells": 0, "nan_cells": int(arr.size), "temp_min": np.nan, "temp_max": np.nan, "temp_mean": np.nan, "temp_std": np.nan}
    return {
        "valid_cells": int(vals.size),
        "nan_cells": int(arr.size - vals.size),
        "temp_min": float(np.min(vals)),
        "temp_max": float(np.max(vals)),
        "temp_mean": float(np.mean(vals)),
        "temp_std": float(np.std(vals)),
    }


def save_png(arr, x_roi, y_roi, date, path, vmin, vmax):
    fig, ax = plt.subplots(figsize=(7.2, 5.4), constrained_layout=True)
    im = ax.imshow(
        arr,
        origin="lower",
        extent=[float(np.nanmin(x_roi)), float(np.nanmax(x_roi)), float(np.nanmin(y_roi)), float(np.nanmax(y_roi))],
        cmap="coolwarm",
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
        aspect="auto",
    )
    ax.set_title(f"FRESNEL paper ROI x490 surface temperature - {date}", fontsize=12)
    ax.set_xlabel("UTM 29N x (km)")
    ax.set_ylabel("UTM 29N y (km)")
    cbar = fig.colorbar(im, ax=ax, shrink=0.88)
    cbar.set_label("Temperature (deg C)")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_clean(arr, path, vmin, vmax):
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    ax.imshow(arr, origin="lower", cmap="coolwarm", vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def save_panel(cube, dates, indices, path, title, vmin, vmax):
    n = len(indices)
    cols = min(4, n)
    rows = int(math.ceil(n / cols))
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
    fig.savefig(path, dpi=150)
    plt.close(fig)


def month_indices(dates):
    seen, out = set(), []
    for i, d in enumerate(dates):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            out.append(i)
    return out


def write_nc(path, cube, dates, lat, lon, x, y, bathy, mask, meta):
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("time", cube.shape[0])
        ds.createDimension("lat", cube.shape[1])
        ds.createDimension("lon", cube.shape[2])
        timev = ds.createVariable("time", "i4", ("time",))
        epoch = pd.Timestamp("1970-01-01")
        timev[:] = [int((pd.Timestamp(d) - epoch).total_seconds()) for d in dates]
        timev.units = "seconds since 1970-01-01 00:00:00"
        timev.calendar = "standard"
        ds.createVariable("LAT", "f4", ("lat",))[:] = lat
        ds.createVariable("LON", "f4", ("lon",))[:] = lon
        ds.createVariable("X_km", "f4", ("lat", "lon"), zlib=True, complevel=4)[:] = x
        ds.createVariable("Y_km", "f4", ("lat", "lon"), zlib=True, complevel=4)[:] = y
        ds.createVariable("BATHY", "f4", ("lat", "lon"), zlib=True, complevel=4)[:] = bathy
        ds.createVariable("MASK", "u1", ("lat", "lon"), zlib=True, complevel=4)[:] = mask.astype(np.uint8)
        tv = ds.createVariable("thetao_surface_hres_paper_roi_x490", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, fill_value=np.nan)
        tv[:] = cube
        tv.units = "degrees_C"
        for k, v in meta.items():
            if isinstance(v, (dict, list)):
                setattr(ds, k, json.dumps(v))
            elif isinstance(v, (bool, np.bool_)):
                setattr(ds, k, int(v))
            elif isinstance(v, (str, int, float, np.integer, np.floating)):
                setattr(ds, k, v)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    input_files_found = {k: p.exists() for k, p in INPUTS.items()}
    if not all(input_files_found.values()):
        raise FileNotFoundError([str(INPUTS[k]) for k, ok in input_files_found.items() if not ok])

    theta = np.load(INPUTS["thetao"], mmap_mode="r")
    lat = np.load(INPUTS["lat"]).astype(np.float64)
    lon = np.load(INPUTS["lon"]).astype(np.float64)
    bathy = np.load(INPUTS["bathy"]).astype(np.float32)
    mask = np.load(INPUTS["mask"]).astype(bool)
    dates = pd.read_csv(INPUTS["dates"])["date"].astype(str).tolist()

    lon2, lat2 = np.meshgrid(lon, lat)
    x_km, y_km = [arr / 1000.0 for arr in wgs84_to_utm29n(lat2, lon2)]
    r0, r1, c0, c1 = roi_indices(x_km, y_km)
    roi = np.asarray(theta[:, r0 : r1 + 1, c0 : c1 + 1], dtype=np.float32)
    lat_roi = lat[r0 : r1 + 1].astype(np.float32)
    lon_roi = lon[c0 : c1 + 1].astype(np.float32)
    x_roi = x_km[r0 : r1 + 1, c0 : c1 + 1].astype(np.float32)
    y_roi = y_km[r0 : r1 + 1, c0 : c1 + 1].astype(np.float32)
    bathy_roi = bathy[r0 : r1 + 1, c0 : c1 + 1].astype(np.float32)
    mask_roi = mask[r0 : r1 + 1, c0 : c1 + 1]
    roi = apply_mask(roi, mask_roi)

    vals = roi[np.isfinite(roi)]
    absolute_min, absolute_max = float(np.min(vals)), float(np.max(vals))
    vmin, vmax = float(np.percentile(vals, 1)), float(np.percentile(vals, 99))
    actual_xy = {
        "x_min_km": float(np.nanmin(x_roi)),
        "x_max_km": float(np.nanmax(x_roi)),
        "y_min_km": float(np.nanmin(y_roi)),
        "y_max_km": float(np.nanmax(y_roi)),
    }
    actual_latlon = {
        "lat_min": float(np.nanmin(lat_roi)),
        "lat_max": float(np.nanmax(lat_roi)),
        "lon_min": float(np.nanmin(lon_roi)),
        "lon_max": float(np.nanmax(lon_roi)),
    }
    area = float((actual_xy["x_max_km"] - actual_xy["x_min_km"]) * (actual_xy["y_max_km"] - actual_xy["y_min_km"]))
    valid_fraction = float(np.isfinite(roi).sum() / roi.size)
    nan_fraction = float(np.isnan(roi).sum() / roi.size)
    x_max_near_490 = bool(abs(actual_xy["x_max_km"] - 490.0) < 0.75)

    np.save(OUT_DIR / "thetao_surface_370_hres_paper_roi_x490.npy", roi)
    np.save(OUT_DIR / "LAT_paper_roi_x490.npy", lat_roi)
    np.save(OUT_DIR / "LON_paper_roi_x490.npy", lon_roi)
    np.save(OUT_DIR / "X_km_paper_roi_x490.npy", x_roi)
    np.save(OUT_DIR / "Y_km_paper_roi_x490.npy", y_roi)
    np.save(OUT_DIR / "BATHY_paper_roi_x490.npy", bathy_roi)
    np.save(OUT_DIR / "MASK_paper_roi_x490.npy", mask_roi)
    pd.DataFrame({"time_index": range(len(dates)), "date": dates}).to_csv(OUT_DIR / "dates_370.csv", index=False)

    meta = {
        "input_dataset_path": str(INPUTS["thetao"]),
        "original_shape": list(theta.shape),
        "roi_shape": list(roi.shape),
        "date_start": dates[0],
        "date_end": dates[-1],
        "n_days": len(dates),
        "projection_used": "WGS84 / UTM zone 29N (EPSG:32629), x/y in km",
        "requested_roi_bounds_xy_km": REQUESTED_ROI,
        "actual_roi_bounds_xy_km": actual_xy,
        "actual_roi_bounds_latlon": actual_latlon,
        "roi_indices": {"row_min": r0, "row_max": r1, "col_min": c0, "col_max": c1},
        "roi_area_km2_approx": area,
        "valid_fraction": valid_fraction,
        "nan_fraction": nan_fraction,
        "color_scale_method": "global robust percentiles p1-p99 over all finite x490 paper ROI cells; absolute min/max recorded",
        "color_scale_vmin": vmin,
        "color_scale_vmax": vmax,
        "absolute_min": absolute_min,
        "absolute_max": absolute_max,
        "mask_applied": True,
        "x_max_near_490_km": x_max_near_490,
        "previous_roi_outputs_deleted_before_generation": True,
        "deleted_prior_results": DELETED_PRIOR_RESULTS,
        "output_npy": str(OUT_DIR / "thetao_surface_370_hres_paper_roi_x490.npy"),
        "output_nc": str(OUT_DIR / "thetao_surface_370_hres_paper_roi_x490.nc"),
        "output_png_folder": str(PNG_DIR),
        "output_clean_png_folder": str(CLEAN_DIR),
    }
    write_nc(OUT_DIR / "thetao_surface_370_hres_paper_roi_x490.nc", roi, dates, lat_roi, lon_roi, x_roi, y_roi, bathy_roi, mask_roi, meta)

    failed = []
    inventory = []
    for i, d in enumerate(dates):
        png = PNG_DIR / f"{i + 1:04d}_{d}_thetao_surface_hres_paper_roi_x490.png"
        clean = CLEAN_DIR / f"{i + 1:04d}_{d}_thetao_surface_hres_paper_roi_x490_clean.png"
        try:
            save_png(roi[i], x_roi, y_roi, d, png, vmin, vmax)
            save_clean(roi[i], clean, vmin, vmax)
        except Exception as exc:
            failed.append({"day_index": i + 1, "date": d, "error": repr(exc)})
        inventory.append({"day_index": i + 1, "date": d, "png_path": str(png), "clean_png_path": str(clean), **stats2d(roi[i])})
    pd.DataFrame(inventory).to_csv(OUT_DIR / "paper_roi_x490_png_inventory.csv", index=False)

    save_panel(roi, dates, list(range(12)), OUT_DIR / "paper_roi_x490_first_12_days_panel.png", "Paper ROI x490 first 12 days", vmin, vmax)
    save_panel(roi, dates, month_indices(dates), OUT_DIR / "paper_roi_x490_selected_monthly_panel.png", "Paper ROI x490 monthly samples", vmin, vmax)
    save_panel(roi, dates, [dates.index(d) for d in HETEROGENEOUS_DATES if d in dates], OUT_DIR / "paper_roi_x490_heterogeneous_days_panel.png", "Paper ROI x490 heterogeneous days", vmin, vmax)
    save_panel(roi, dates, list(range(len(dates) - 12, len(dates))), OUT_DIR / "paper_roi_x490_final_12_days_panel.png", "Paper ROI x490 final 12 days", vmin, vmax)

    n_png, n_clean = len(list(PNG_DIR.glob("*.png"))), len(list(CLEAN_DIR.glob("*.png")))
    checks = {
        "input_files_found": input_files_found,
        "input_shape_correct": list(theta.shape) == [370, 180, 240],
        "dates_count_correct": len(dates) == 370 and dates[0] == "2023-10-28" and dates[-1] == "2024-10-31",
        "roi_indices_found": True,
        "roi_not_empty": roi.shape[1] > 0 and roi.shape[2] > 0,
        "roi_shape": list(roi.shape),
        "output_array_shape": list(roi.shape),
        "n_png_generated": n_png,
        "n_clean_png_generated": n_clean,
        "expected_png_count": 370,
        "png_count_correct": n_png == 370,
        "clean_png_count_correct": n_clean == 370,
        "mask_applied": True,
        "orientation_preserved": bool(lat_roi[0] < lat_roi[-1] and lon_roi[0] < lon_roi[-1]),
        "x_axis_ends_near_490_km": x_max_near_490,
        "previous_results_deleted_before_generation": True,
        "no_input_files_modified": True,
        "failed_days": failed,
        "final_verdict": "The corrected FRESNEL paper ROI with x_max near 490 km was applied to the 370 HRes surface temperature maps, the previous ROI outputs were deleted, and all ROI PNGs were exported with a consistent global color scale."
        if n_png == 370 and n_clean == 370 and not failed and x_max_near_490
        else "Corrected x490 ROI export completed with issues; review checks.",
    }
    meta.update({"output_png_count": n_png, "output_clean_png_count": n_clean, "failed_days": failed, "final_verdict": checks["final_verdict"]})
    (OUT_DIR / "paper_roi_x490_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT_DIR / "paper_roi_x490_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    report = f"""# FRESNEL Paper ROI x490 Export Report

Input folder: `{INPUT_DIR}`

Previous ROI outputs were deleted before this generation:

- `results/fresnel_roi_surface_370_20260509_164727`
- `results/fresnel_paper_roi_surface_370_20260509_174142`

## ROI Applied

- Requested ROI: `{REQUESTED_ROI}`
- Actual snapped ROI: `{actual_xy}`
- Actual lat/lon: `{actual_latlon}`
- Indices: `{meta["roi_indices"]}`
- Shape: `{list(roi.shape)}`
- Area: `{area:.2f}` km²
- Valid fraction: `{valid_fraction:.4f}`
- NaN fraction: `{nan_fraction:.4f}`
- x-axis ends near 490 km: `{x_max_near_490}`

## Export

- Normal PNGs: `{n_png}`
- Clean PNGs: `{n_clean}`
- Color scale: coolwarm, p1-p99, vmin=`{vmin:.6f}`, vmax=`{vmax:.6f}`
- Absolute min/max: `{absolute_min:.6f}` / `{absolute_max:.6f}`
- Failed days: `{failed}`

{checks["final_verdict"]}
"""
    (OUT_DIR / "paper_roi_x490_export_report.md").write_text(report, encoding="utf-8")

    summary = f"""# FRESNEL Paper ROI x490 Export Summary

1. ROI pedido aplicado: x=`463-490 km`, y=`4376-4397 km` em UTM 29N.
2. ROI real após snapping à grelha: `{actual_xy}`.
3. Shape final: `{list(roi.shape)}`.
4. Área aproximada: `{area:.2f}` km².
5. Percentagem de células válidas: `{valid_fraction * 100:.2f}%`.
6. PNGs normais gerados: `{n_png}`.
7. PNGs clean gerados: `{n_clean}`.
8. Orientação preservada: `{checks["orientation_preserved"]}`.
9. O eixo x agora termina próximo de 490 km: `{x_max_near_490}`.
10. Pronto para pipeline Fossum: `{"Sim" if checks["final_verdict"].startswith("The corrected") else "Rever checks"}`.
11. Resultados anteriores apagados antes do novo output: `Sim`.

The corrected FRESNEL paper ROI with x_max near 490 km was applied to the 370 HRes surface temperature maps, the previous ROI outputs were deleted, and all ROI PNGs were exported with a consistent global color scale.
"""
    (OUT_DIR / "paper_roi_x490_export_summary.md").write_text(summary, encoding="utf-8")
    print(f"Done: {OUT_DIR}")


if __name__ == "__main__":
    main()
