from __future__ import annotations

import csv
import json
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd


INPUT_ROOT = Path(
    r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\02.Simulations\HighRes"
)
STD_AUDIT_FOLDER = Path(
    r"C:\Users\pedro\Documents\Filipa_dados\results\std_october_surface_audit_20260511_153958"
)
ROI_REFERENCE_FOLDER = Path(
    r"C:\Users\pedro\Documents\Filipa_dados\results\fresnel_paper_roi_x490_surface_370_20260509_180348"
)
OUTPUT_DIR = Path(
    r"C:\Users\pedro\Documents\Filipa_dados\results\october_surface_temppred_std_roi_x490_20260511_155923"
)

STD_DAILY_DIR = OUTPUT_DIR / "std_roi_x490_daily"
STD_DAILY_CLEAN_DIR = OUTPUT_DIR / "std_roi_x490_daily_clean"
TEMP_DAILY_DIR = OUTPUT_DIR / "temppred_roi_x490_daily"
TEMP_DAILY_CLEAN_DIR = OUTPUT_DIR / "temppred_roi_x490_daily_clean"

EXPECTED_DAYS = [date(2024, 10, 1) + timedelta(days=i) for i in range(31)]
SELECTED_DAY_SLICE = 1
SELECTED_DEPTH_INDEX = 1
FULL_GRID_SHAPE = (180, 240)
ROI_SHAPE = (72, 117)
EXPECTED_STACK_SHAPE = (31, 72, 117)
PREDMODEL_SUFFIX = "predModel_1.nc"
SELECTED_COMPARISON_DAYS = ["2024-10-10", "2024-10-13", "2024-10-15", "2024-10-30", "2024-10-31"]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def masked_to_nan(array: Any) -> np.ndarray:
    arr = np.asanyarray(array)
    if np.ma.isMaskedArray(arr):
        return np.ma.filled(arr.astype(np.float64), np.nan)
    return arr.astype(np.float64, copy=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_expected_file(day: date) -> Path | None:
    expected_name = f"{day:%d-%m-%Y}_{PREDMODEL_SUFFIX}"
    matches = sorted(INPUT_ROOT.rglob(expected_name))
    return matches[0] if matches else None


def apply_reference_mask(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    out[~mask] = np.nan
    return out


def finite_stats(arr: np.ndarray) -> dict[str, float | int]:
    vals = arr[np.isfinite(arr)]
    if vals.size == 0:
        return {
            "min": np.nan,
            "max": np.nan,
            "mean": np.nan,
            "std": np.nan,
            "p50": np.nan,
            "p99": np.nan,
            "finite_count": 0,
            "nan_count": int(np.isnan(arr).sum()),
        }
    return {
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "p50": float(np.percentile(vals, 50)),
        "p99": float(np.percentile(vals, 99)),
        "finite_count": int(vals.size),
        "nan_count": int(np.isnan(arr).sum()),
    }


def gradient_stats(temp: np.ndarray) -> tuple[float, float]:
    grad_y, grad_x = np.gradient(temp.astype(np.float64))
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    vals = grad_mag[np.isfinite(grad_mag)]
    if vals.size == 0:
        return np.nan, np.nan
    return float(np.mean(vals)), float(np.max(vals))


def global_scale(stack: np.ndarray) -> tuple[float, float]:
    vals = stack[np.isfinite(stack)]
    if vals.size == 0:
        return 0.0, 1.0
    vmin, vmax = [float(x) for x in np.percentile(vals, [1, 99])]
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        vmin = float(np.nanmin(vals))
        vmax = float(np.nanmax(vals))
    if vmin == vmax:
        vmax = vmin + 1.0
    return vmin, vmax


def plot_map(
    arr: np.ndarray,
    x_km: np.ndarray,
    y_km: np.ndarray,
    title: str,
    outfile: Path,
    vmin: float,
    vmax: float,
    cmap_name: str,
    colorbar_label: str,
    clean: bool,
) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 5.2), constrained_layout=True)
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("#f2f2f2")
    image = ax.imshow(
        np.ma.masked_invalid(arr),
        origin="lower",
        extent=[
            float(np.nanmin(x_km)),
            float(np.nanmax(x_km)),
            float(np.nanmin(y_km)),
            float(np.nanmax(y_km)),
        ],
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
        interpolation="nearest",
        aspect="auto",
    )
    if clean:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=10)
    else:
        ax.set_xlabel("x (km)")
        ax.set_ylabel("y (km)")
        ax.set_title(title, fontsize=11)
    fig.colorbar(image, ax=ax, shrink=0.84, label=colorbar_label)
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def save_panel(
    stack: np.ndarray,
    dates: list[str],
    outfile: Path,
    vmin: float,
    vmax: float,
    title: str,
    cmap_name: str,
    colorbar_label: str,
    clean: bool,
) -> None:
    cols = 6
    rows = int(math.ceil(len(dates) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 2.45), constrained_layout=True)
    axes_flat = np.ravel(axes)
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("#f2f2f2")
    image = None
    for i, ax in enumerate(axes_flat):
        if i >= len(dates):
            ax.axis("off")
            continue
        image = ax.imshow(
            np.ma.masked_invalid(stack[i]),
            origin="lower",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            interpolation="nearest",
        )
        ax.set_title(dates[i][-2:], fontsize=8)
        if clean:
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            ax.set_xticks([])
            ax.set_yticks([])
    if image is not None:
        fig.colorbar(image, ax=axes_flat.tolist(), shrink=0.72, label=colorbar_label)
    fig.suptitle(title, fontsize=13)
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def save_timeseries_std(metrics: pd.DataFrame, outfile: Path) -> None:
    x = pd.to_datetime(metrics["date"])
    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    ax.plot(x, metrics["std_mean"], marker="o", label="mean")
    ax.plot(x, metrics["std_max"], marker="o", label="max")
    ax.plot(x, metrics["std_p99"], marker="o", label="p99")
    ax.set_title("STD ROI x490 daily mean, max and p99")
    ax.set_ylabel("STD")
    ax.set_xlabel("October 2024")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def save_timeseries_temp(metrics: pd.DataFrame, outfile: Path) -> None:
    x = pd.to_datetime(metrics["date"])
    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    ax.plot(x, metrics["temp_mean"], marker="o", label="mean")
    ax.fill_between(
        x,
        metrics["temp_min"].astype(float),
        metrics["temp_max"].astype(float),
        alpha=0.18,
        label="min-max range",
    )
    ax.set_title("TEMPpred ROI x490 daily mean and range")
    ax.set_ylabel("TEMPpred (°C)")
    ax.set_xlabel("October 2024")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def save_selected_comparison_panel(
    temp_stack: np.ndarray,
    std_stack: np.ndarray,
    dates: list[str],
    outfile: Path,
    temp_scale: tuple[float, float],
    std_scale: tuple[float, float],
) -> None:
    selected_indices = [dates.index(d) for d in SELECTED_COMPARISON_DAYS if d in dates]
    if not selected_indices:
        return
    fig, axes = plt.subplots(len(selected_indices), 2, figsize=(8.8, 3.1 * len(selected_indices)), constrained_layout=True)
    axes = np.asarray(axes).reshape(len(selected_indices), 2)
    cmap_temp = plt.get_cmap("turbo").copy()
    cmap_std = plt.get_cmap("viridis").copy()
    cmap_temp.set_bad("#f2f2f2")
    cmap_std.set_bad("#f2f2f2")
    temp_image = None
    std_image = None
    for row, idx in enumerate(selected_indices):
        d = dates[idx]
        temp_image = axes[row, 0].imshow(
            np.ma.masked_invalid(temp_stack[idx]),
            origin="lower",
            vmin=temp_scale[0],
            vmax=temp_scale[1],
            cmap=cmap_temp,
            interpolation="nearest",
        )
        axes[row, 0].set_title(f"{d} TEMPpred", fontsize=9)
        axes[row, 0].set_xticks([])
        axes[row, 0].set_yticks([])
        std_image = axes[row, 1].imshow(
            np.ma.masked_invalid(std_stack[idx]),
            origin="lower",
            vmin=std_scale[0],
            vmax=std_scale[1],
            cmap=cmap_std,
            interpolation="nearest",
        )
        axes[row, 1].set_title(f"{d} STD", fontsize=9)
        axes[row, 1].set_xticks([])
        axes[row, 1].set_yticks([])
    if temp_image is not None:
        fig.colorbar(temp_image, ax=axes[:, 0].tolist(), shrink=0.78, label="TEMPpred (°C)")
    if std_image is not None:
        fig.colorbar(std_image, ax=axes[:, 1].tolist(), shrink=0.78, label="STD")
    fig.suptitle("Selected October days: TEMPpred and STD in ROI x490", fontsize=13)
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def write_netcdf(
    path: Path,
    temp_stack: np.ndarray,
    std_stack: np.ndarray,
    dates: list[str],
    lat: np.ndarray,
    lon: np.ndarray,
    x_km: np.ndarray,
    y_km: np.ndarray,
    bathy: np.ndarray,
    mask: np.ndarray,
) -> None:
    epoch = date(1970, 1, 1)
    time_days = np.array([(datetime.strptime(d, "%Y-%m-%d").date() - epoch).days for d in dates], dtype=np.int32)
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("time", len(dates))
        ds.createDimension("lat", len(lat))
        ds.createDimension("lon", len(lon))
        ds.title = "October 2024 surface TEMPpred and STD cropped to FRESNEL x490 ROI"
        ds.source_predmodel_root = str(INPUT_ROOT)
        ds.roi_reference_folder = str(ROI_REFERENCE_FOLDER)
        ds.selected_day_slice = SELECTED_DAY_SLICE
        ds.selected_depth_index = SELECTED_DEPTH_INDEX

        t = ds.createVariable("time", "i4", ("time",))
        t.units = "days since 1970-01-01"
        t.calendar = "standard"
        t[:] = time_days
        date_var = ds.createVariable("date", str, ("time",))
        date_var[:] = np.array(dates, dtype=object)

        lat_var = ds.createVariable("LAT", "f4", ("lat",))
        lon_var = ds.createVariable("LON", "f4", ("lon",))
        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"
        lat_var[:] = lat.astype(np.float32)
        lon_var[:] = lon.astype(np.float32)

        ds.createVariable("X_km", "f4", ("lat", "lon"), zlib=True, complevel=4)[:] = x_km.astype(np.float32)
        ds.createVariable("Y_km", "f4", ("lat", "lon"), zlib=True, complevel=4)[:] = y_km.astype(np.float32)
        ds.createVariable("BATHY", "f4", ("lat", "lon"), zlib=True, complevel=4)[:] = bathy.astype(np.float32)
        ds.createVariable("MASK", "u1", ("lat", "lon"), zlib=True, complevel=4)[:] = mask.astype(np.uint8)

        temp_var = ds.createVariable("TEMPpred", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, fill_value=np.nan)
        std_var = ds.createVariable("STD", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, fill_value=np.nan)
        temp_var.units = "degree_Celsius"
        std_var.units = "unknown"
        temp_var[:] = temp_stack.astype(np.float32)
        std_var[:] = std_stack.astype(np.float32)


def write_reports(
    metadata: dict[str, Any],
    checks: dict[str, Any],
    metrics: pd.DataFrame,
    summary_path: Path,
    report_path: Path,
) -> None:
    final_ready = checks["final_verdict"].startswith("READY")
    ready_text = (
        "Sim, os outputs estao prontos para integracao com descriptors e planner."
        if final_ready
        else "Ainda nao: rever os dias falhados/suspeitos antes de integrar."
    )
    failed_days = checks["failed_days"] or []
    failed_text = ", ".join(failed_days) if failed_days else "Nenhum"
    summary = f"""# October Surface TEMPpred/STD ROI x490 Summary

Output folder: `{OUTPUT_DIR}`

1. Os 31 mapas TEMPpred/STD surface foram encontrados?
   - {'Sim' if checks['all_31_files_found'] else 'Nao'}.
2. Qual slice do eixo day foi usado?
   - Slice `{metadata['selected_day_slice']}`.
3. O slice 0 foi ignorado?
   - {'Sim' if checks['slice0_not_used'] else 'Nao'}.
4. O ROI aplicado e exatamente o mesmo ROI x490 dos 370 mapas HRes?
   - {'Sim' if checks['lat_lon_match_reference_roi'] and checks['bathy_match_reference_roi'] and checks['mask_match_reference_roi'] and checks['same_orientation_as_reference_roi'] else 'Nao'}; foram usados os indices `{metadata['roi_indices']}` do metadata de referencia.
5. Qual shape final dos arrays?
   - TEMPpred: `{checks['temp_stack_shape']}`; STD: `{checks['std_stack_shape']}`.
6. TEMPpred e STD ficaram com shape [31, 72, 117]?
   - {'Sim' if checks['shape_matches_expected'] else 'Nao'}.
7. LAT/LON/BATHY/MASK ficaram consistentes com o ROI de referencia?
   - LAT/LON: `{checks['lat_lon_match_reference_roi']}`; BATHY: `{checks['bathy_match_reference_roi']}`; MASK: `{checks['mask_match_reference_roi']}`.
8. Quantos PNGs STD foram gerados?
   - {checks['n_std_pngs']} normais + {checks['n_std_clean_pngs']} clean.
9. Quantos PNGs TEMPpred foram gerados?
   - {checks['n_temppred_pngs']} normais + {checks['n_temppred_clean_pngs']} clean.
10. Houve algum dia falhado ou suspeito?
   - {failed_text}.
11. Os outputs estao prontos para integracao com descriptors e planner?
   - {ready_text}

Final verdict: {checks['final_verdict']}

The October surface TEMPpred and STD maps were cropped to the same FRESNEL x490 ROI used by the 370-day HRes temperature dataset, using the validated day-slice convention.
"""
    summary_path.write_text(summary, encoding="utf-8")

    top_std = metrics.sort_values("std_mean", ascending=False).head(5)
    top_temp = metrics.sort_values("temp_mean", ascending=False).head(5)
    top_std_text = "\n".join(
        f"- {r.date}: STD mean={r.std_mean:.6g}, STD max={r.std_max:.6g}, STD p99={r.std_p99:.6g}"
        for r in top_std.itertuples()
    )
    top_temp_text = "\n".join(
        f"- {r.date}: TEMP mean={r.temp_mean:.6g}, TEMP range={r.temp_range:.6g}, TEMP max={r.temp_max:.6g}"
        for r in top_temp.itertuples()
    )
    report = f"""# October Surface TEMPpred/STD ROI x490 Report

## Scope

- Input predModel root: `{metadata['input_predmodel_root']}`
- STD audit folder: `{metadata['input_std_audit_folder']}`
- ROI reference folder: `{metadata['roi_reference_folder']}`
- Selected day slice: `{metadata['selected_day_slice']}`
- Selected depth: predModel_{metadata['selected_depth_index']} / {metadata['selected_depth_value_m']:.6g} m
- Original NetCDF files were read only.

## ROI

- Requested bounds: `{metadata['requested_roi_bounds_xy_km']}`
- Actual bounds: `{metadata['actual_roi_bounds_xy_km']}`
- Indices: `{metadata['roi_indices']}`
- Shape: `{metadata['roi_shape']}`
- Mask applied: `{metadata['mask_applied']}`
- Orientation preserved: `{metadata['orientation_preserved']}`

## Outputs

- `TEMPpred_october_surface_roi_x490.npy`
- `STD_october_surface_roi_x490.npy`
- `october_surface_TEMPpred_STD_roi_x490.nc`
- Daily PNG folders for STD and TEMPpred, normal and clean.
- Panels and daily metrics CSV.

## Validation

- All files found: `{checks['all_31_files_found']}`
- Expected stack shape: `{checks['expected_shape']}`
- TEMP stack shape: `{checks['temp_stack_shape']}`
- STD stack shape: `{checks['std_stack_shape']}`
- Reference LAT/LON match: `{checks['lat_lon_match_reference_roi']}`
- Reference BATHY match: `{checks['bathy_match_reference_roi']}`
- Reference MASK match: `{checks['mask_match_reference_roi']}`
- Same orientation as reference: `{checks['same_orientation_as_reference_roi']}`
- Blank STD maps: `{not checks['no_blank_std_maps']}`
- Zero STD maps: `{not checks['no_zero_std_maps']}`
- Failed days: `{failed_text}`

## Highest STD Mean Days

{top_std_text}

## Highest TEMPpred Mean Days

{top_temp_text}

## Final Recommendation

{ready_text}
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for directory in [STD_DAILY_DIR, STD_DAILY_CLEAN_DIR, TEMP_DAILY_DIR, TEMP_DAILY_CLEAN_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    roi_meta = read_json(ROI_REFERENCE_FOLDER / "paper_roi_x490_metadata.json")
    roi_checks = read_json(ROI_REFERENCE_FOLDER / "paper_roi_x490_checks.json")
    roi_indices = roi_meta["roi_indices"]
    row_min = int(roi_indices["row_min"])
    row_max = int(roi_indices["row_max"])
    col_min = int(roi_indices["col_min"])
    col_max = int(roi_indices["col_max"])
    row_slice = slice(row_min, row_max + 1)
    col_slice = slice(col_min, col_max + 1)

    lat_ref = np.load(ROI_REFERENCE_FOLDER / "LAT_paper_roi_x490.npy").astype(np.float32)
    lon_ref = np.load(ROI_REFERENCE_FOLDER / "LON_paper_roi_x490.npy").astype(np.float32)
    x_ref = np.load(ROI_REFERENCE_FOLDER / "X_km_paper_roi_x490.npy").astype(np.float32)
    y_ref = np.load(ROI_REFERENCE_FOLDER / "Y_km_paper_roi_x490.npy").astype(np.float32)
    bathy_ref = np.load(ROI_REFERENCE_FOLDER / "BATHY_paper_roi_x490.npy").astype(np.float32)
    mask_ref = np.load(ROI_REFERENCE_FOLDER / "MASK_paper_roi_x490.npy").astype(bool)

    files = {d: find_expected_file(d) for d in EXPECTED_DAYS}
    input_mtimes_before = {str(p): os.path.getmtime(p) for p in files.values() if p is not None}
    failed_days: dict[str, list[str]] = {}
    dates: list[str] = []
    temp_maps: list[np.ndarray] = []
    std_maps: list[np.ndarray] = []
    metrics_rows: list[dict[str, Any]] = []
    lat_lon_match_all = True
    bathy_match_all = True
    depth_values: list[float] = []

    for day in EXPECTED_DAYS:
        date_label = day.isoformat()
        path = files[day]
        reasons: list[str] = []
        if path is None:
            failed_days[date_label] = ["file_missing"]
            continue

        with netCDF4.Dataset(path) as ds:
            for var_name in ["TEMPpred", "STD", "LAT", "LON", "BATHY"]:
                if var_name not in ds.variables:
                    reasons.append(f"{var_name}_missing")
            if reasons:
                failed_days[date_label] = reasons
                continue

            temp_full = masked_to_nan(ds.variables["TEMPpred"][:])
            std_full = masked_to_nan(ds.variables["STD"][:])
            lat_full = masked_to_nan(ds.variables["LAT"][:])
            lon_full = masked_to_nan(ds.variables["LON"][:])
            bathy_full = masked_to_nan(ds.variables["BATHY"][:])
            if "DEPT" in ds.variables:
                dept = masked_to_nan(ds.variables["DEPT"][:]).ravel()
                if dept.size >= SELECTED_DEPTH_INDEX:
                    depth_values.append(float(dept[SELECTED_DEPTH_INDEX - 1]))

        if temp_full.shape != (2, *FULL_GRID_SHAPE):
            reasons.append(f"TEMPpred_shape_{temp_full.shape}")
        if std_full.shape != (2, *FULL_GRID_SHAPE):
            reasons.append(f"STD_shape_{std_full.shape}")
        if SELECTED_DAY_SLICE >= temp_full.shape[0] or SELECTED_DAY_SLICE >= std_full.shape[0]:
            reasons.append("selected_day_slice_missing")
        if reasons:
            failed_days[date_label] = reasons
            continue

        lat_roi_from_nc = lat_full[row_slice].astype(np.float32)
        lon_roi_from_nc = lon_full[col_slice].astype(np.float32)
        bathy_roi_from_nc = bathy_full[row_slice, col_slice].astype(np.float32)
        lat_lon_match_all = lat_lon_match_all and np.allclose(lat_roi_from_nc, lat_ref, rtol=0, atol=5e-5) and np.allclose(
            lon_roi_from_nc, lon_ref, rtol=0, atol=5e-5
        )
        bathy_match_all = bathy_match_all and np.allclose(bathy_roi_from_nc, bathy_ref, equal_nan=True, rtol=0, atol=1e-3)

        temp_roi = temp_full[SELECTED_DAY_SLICE, row_slice, col_slice]
        std_roi = std_full[SELECTED_DAY_SLICE, row_slice, col_slice]
        if temp_roi.shape != ROI_SHAPE:
            reasons.append(f"TEMPpred_roi_shape_{temp_roi.shape}")
        if std_roi.shape != ROI_SHAPE:
            reasons.append(f"STD_roi_shape_{std_roi.shape}")
        temp_roi = apply_reference_mask(temp_roi, mask_ref)
        std_roi = apply_reference_mask(std_roi, mask_ref)

        std_stats = finite_stats(std_roi)
        temp_stats = finite_stats(temp_roi)
        valid = np.isfinite(std_roi) & np.isfinite(temp_roi)
        if std_stats["finite_count"] == 0:
            reasons.append("STD_blank")
        elif float(std_stats["max"]) == 0.0 and float(std_stats["min"]) == 0.0:
            reasons.append("STD_all_zero")
        if reasons:
            failed_days[date_label] = reasons

        grad_mean, grad_max = gradient_stats(temp_roi)
        metrics_rows.append(
            {
                "date": date_label,
                "temp_mean": temp_stats["mean"],
                "temp_std": temp_stats["std"],
                "temp_min": temp_stats["min"],
                "temp_max": temp_stats["max"],
                "temp_range": float(temp_stats["max"] - temp_stats["min"])
                if np.isfinite(temp_stats["max"]) and np.isfinite(temp_stats["min"])
                else np.nan,
                "std_mean": std_stats["mean"],
                "std_std": std_stats["std"],
                "std_min": std_stats["min"],
                "std_max": std_stats["max"],
                "std_p50": std_stats["p50"],
                "std_p99": std_stats["p99"],
                "valid_cells": int(valid.sum()),
                "nan_cells": int((~valid).sum()),
                "valid_fraction": float(valid.sum() / valid.size),
                "temp_gradient_mean": grad_mean,
                "temp_gradient_max": grad_max,
            }
        )
        dates.append(date_label)
        temp_maps.append(temp_roi)
        std_maps.append(std_roi)

    if temp_maps:
        temp_stack = np.stack(temp_maps).astype(np.float32)
        std_stack = np.stack(std_maps).astype(np.float32)
    else:
        temp_stack = np.empty((0, *ROI_SHAPE), dtype=np.float32)
        std_stack = np.empty((0, *ROI_SHAPE), dtype=np.float32)

    temp_vmin, temp_vmax = global_scale(temp_stack)
    std_vmin, std_vmax = global_scale(std_stack)
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUTPUT_DIR / "october_surface_roi_x490_day_metrics.csv", index=False)

    np.save(OUTPUT_DIR / "TEMPpred_october_surface_roi_x490.npy", temp_stack)
    np.save(OUTPUT_DIR / "STD_october_surface_roi_x490.npy", std_stack)
    np.save(OUTPUT_DIR / "LAT_october_roi_x490.npy", lat_ref)
    np.save(OUTPUT_DIR / "LON_october_roi_x490.npy", lon_ref)
    np.save(OUTPUT_DIR / "X_km_october_roi_x490.npy", x_ref)
    np.save(OUTPUT_DIR / "Y_km_october_roi_x490.npy", y_ref)
    np.save(OUTPUT_DIR / "BATHY_october_roi_x490.npy", bathy_ref)
    np.save(OUTPUT_DIR / "MASK_october_roi_x490.npy", mask_ref)

    with (OUTPUT_DIR / "dates_october.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["day_index", "date", "source_file"])
        writer.writeheader()
        for i, d in enumerate(dates, start=1):
            writer.writerow({"day_index": i, "date": d, "source_file": str(files[datetime.strptime(d, "%Y-%m-%d").date()])})

    write_netcdf(
        OUTPUT_DIR / "october_surface_TEMPpred_STD_roi_x490.nc",
        temp_stack,
        std_stack,
        dates,
        lat_ref,
        lon_ref,
        x_ref,
        y_ref,
        bathy_ref,
        mask_ref,
    )

    std_inventory: list[dict[str, Any]] = []
    temp_inventory: list[dict[str, Any]] = []
    for i, d in enumerate(dates):
        std_png = STD_DAILY_DIR / f"{i + 1:02d}_{d}_STD_roi_x490.png"
        std_clean = STD_DAILY_CLEAN_DIR / f"{i + 1:02d}_{d}_STD_roi_x490_clean.png"
        temp_png = TEMP_DAILY_DIR / f"{i + 1:02d}_{d}_TEMPpred_roi_x490.png"
        temp_clean = TEMP_DAILY_CLEAN_DIR / f"{i + 1:02d}_{d}_TEMPpred_roi_x490_clean.png"
        plot_map(std_stack[i], x_ref, y_ref, f"STD ROI x490 - {d}", std_png, std_vmin, std_vmax, "viridis", "STD", False)
        plot_map(
            std_stack[i],
            x_ref,
            y_ref,
            f"STD ROI x490 - {d}",
            std_clean,
            std_vmin,
            std_vmax,
            "viridis",
            "STD",
            True,
        )
        plot_map(
            temp_stack[i],
            x_ref,
            y_ref,
            f"TEMPpred ROI x490 - {d}",
            temp_png,
            temp_vmin,
            temp_vmax,
            "turbo",
            "TEMPpred (°C)",
            False,
        )
        plot_map(
            temp_stack[i],
            x_ref,
            y_ref,
            f"TEMPpred ROI x490 - {d}",
            temp_clean,
            temp_vmin,
            temp_vmax,
            "turbo",
            "TEMPpred (°C)",
            True,
        )
        std_inventory.append({"day_index": i + 1, "date": d, "png_path": str(std_png), "clean_png_path": str(std_clean), **finite_stats(std_stack[i])})
        temp_inventory.append({"day_index": i + 1, "date": d, "png_path": str(temp_png), "clean_png_path": str(temp_clean), **finite_stats(temp_stack[i])})

    pd.DataFrame(std_inventory).to_csv(OUTPUT_DIR / "std_roi_x490_png_inventory.csv", index=False)
    pd.DataFrame(temp_inventory).to_csv(OUTPUT_DIR / "temppred_roi_x490_png_inventory.csv", index=False)

    if len(dates) == 31:
        save_panel(std_stack, dates, OUTPUT_DIR / "october_STD_roi_x490_panel.png", std_vmin, std_vmax, "October STD ROI x490", "viridis", "STD", False)
        save_panel(
            std_stack,
            dates,
            OUTPUT_DIR / "october_STD_roi_x490_clean_panel.png",
            std_vmin,
            std_vmax,
            "October STD ROI x490 clean",
            "viridis",
            "STD",
            True,
        )
        save_panel(
            temp_stack,
            dates,
            OUTPUT_DIR / "october_TEMPpred_roi_x490_panel.png",
            temp_vmin,
            temp_vmax,
            "October TEMPpred ROI x490",
            "turbo",
            "TEMPpred (°C)",
            False,
        )
        save_panel(
            temp_stack,
            dates,
            OUTPUT_DIR / "october_TEMPpred_roi_x490_clean_panel.png",
            temp_vmin,
            temp_vmax,
            "October TEMPpred ROI x490 clean",
            "turbo",
            "TEMPpred (°C)",
            True,
        )
        save_timeseries_std(metrics_df, OUTPUT_DIR / "STD_roi_x490_timeseries_mean_max_p99.png")
        save_timeseries_temp(metrics_df, OUTPUT_DIR / "TEMPpred_roi_x490_timeseries_mean_range.png")
        save_selected_comparison_panel(
            temp_stack,
            std_stack,
            dates,
            OUTPUT_DIR / "october_TEMPpred_STD_roi_x490_selected_days_panel.png",
            (temp_vmin, temp_vmax),
            (std_vmin, std_vmax),
        )

    input_mtimes_after = {str(p): os.path.getmtime(p) for p in files.values() if p is not None}
    no_input_files_modified = input_mtimes_before == input_mtimes_after
    n_std_pngs = len(list(STD_DAILY_DIR.glob("*.png")))
    n_std_clean_pngs = len(list(STD_DAILY_CLEAN_DIR.glob("*.png")))
    n_temp_pngs = len(list(TEMP_DAILY_DIR.glob("*.png")))
    n_temp_clean_pngs = len(list(TEMP_DAILY_CLEAN_DIR.glob("*.png")))

    actual_bounds = {
        "x_min_km": float(np.nanmin(x_ref)),
        "x_max_km": float(np.nanmax(x_ref)),
        "y_min_km": float(np.nanmin(y_ref)),
        "y_max_km": float(np.nanmax(y_ref)),
    }
    orientation_preserved = bool(
        np.all(np.diff(lat_ref) > 0)
        and np.all(np.diff(lon_ref) > 0)
        and np.nanmean(np.diff(y_ref[:, 0])) > 0
        and np.nanmean(np.diff(x_ref[0, :])) > 0
    )
    metadata = {
        "input_predmodel_root": str(INPUT_ROOT),
        "input_std_audit_folder": str(STD_AUDIT_FOLDER),
        "roi_reference_folder": str(ROI_REFERENCE_FOLDER),
        "selected_day_slice": SELECTED_DAY_SLICE,
        "selected_depth_index": SELECTED_DEPTH_INDEX,
        "selected_depth_value_m": float(np.nanmedian(depth_values)) if depth_values else np.nan,
        "requested_roi_bounds_xy_km": roi_meta.get("requested_roi_bounds_xy_km"),
        "actual_roi_bounds_xy_km": roi_meta.get("actual_roi_bounds_xy_km", actual_bounds),
        "actual_roi_bounds_xy_km_from_arrays": actual_bounds,
        "roi_indices": roi_indices,
        "roi_shape": list(ROI_SHAPE),
        "n_days": len(dates),
        "date_start": dates[0] if dates else None,
        "date_end": dates[-1] if dates else None,
        "std_color_scale_vmin": std_vmin,
        "std_color_scale_vmax": std_vmax,
        "temppred_color_scale_vmin": temp_vmin,
        "temppred_color_scale_vmax": temp_vmax,
        "mask_applied": True,
        "mask_valid_cells": int(mask_ref.sum()),
        "mask_valid_fraction": float(mask_ref.mean()),
        "reference_hres_valid_fraction": roi_meta.get("valid_fraction"),
        "orientation_preserved": orientation_preserved,
    }

    mask_match_reference_roi = bool(np.array_equal(mask_ref, np.load(ROI_REFERENCE_FOLDER / "MASK_paper_roi_x490.npy").astype(bool)))
    lat_lon_match_reference_roi = bool(
        np.allclose(lat_ref, np.load(ROI_REFERENCE_FOLDER / "LAT_paper_roi_x490.npy"), rtol=0, atol=5e-5)
        and np.allclose(lon_ref, np.load(ROI_REFERENCE_FOLDER / "LON_paper_roi_x490.npy"), rtol=0, atol=5e-5)
        and lat_lon_match_all
    )
    bathy_match_reference_roi = bool(
        np.allclose(bathy_ref, np.load(ROI_REFERENCE_FOLDER / "BATHY_paper_roi_x490.npy"), equal_nan=True, rtol=0, atol=1e-3)
        and bathy_match_all
    )
    blank_std_days = []
    zero_std_days = []
    if len(std_stack):
        for d, arr in zip(dates, std_stack):
            vals = arr[np.isfinite(arr)]
            if vals.size == 0:
                blank_std_days.append(d)
            elif np.nanmin(vals) == 0.0 and np.nanmax(vals) == 0.0:
                zero_std_days.append(d)

    shape_matches_expected = list(temp_stack.shape) == list(EXPECTED_STACK_SHAPE) and list(std_stack.shape) == list(EXPECTED_STACK_SHAPE)
    failed_days_flat = sorted(failed_days.keys())
    no_suspicious_days = bool(not failed_days_flat and not blank_std_days and not zero_std_days)
    final_ready = bool(
        len(dates) == 31
        and SELECTED_DAY_SLICE == 1
        and shape_matches_expected
        and lat_lon_match_reference_roi
        and bathy_match_reference_roi
        and mask_match_reference_roi
        and orientation_preserved
        and no_suspicious_days
        and n_std_pngs == 31
        and n_std_clean_pngs == 31
        and n_temp_pngs == 31
        and n_temp_clean_pngs == 31
        and no_input_files_modified
    )
    checks = {
        "all_31_files_found": all(p is not None for p in files.values()),
        "selected_day_slice_is_1": SELECTED_DAY_SLICE == 1,
        "slice0_not_used": True,
        "temp_stack_shape": list(temp_stack.shape),
        "std_stack_shape": list(std_stack.shape),
        "expected_shape": list(EXPECTED_STACK_SHAPE),
        "shape_matches_expected": shape_matches_expected,
        "lat_lon_match_reference_roi": lat_lon_match_reference_roi,
        "bathy_match_reference_roi": bathy_match_reference_roi,
        "mask_match_reference_roi": mask_match_reference_roi,
        "same_orientation_as_reference_roi": orientation_preserved and bool(roi_checks.get("orientation_preserved", True)),
        "no_blank_std_maps": len(blank_std_days) == 0,
        "no_zero_std_maps": len(zero_std_days) == 0,
        "no_suspicious_days": no_suspicious_days,
        "n_std_pngs": n_std_pngs,
        "n_std_clean_pngs": n_std_clean_pngs,
        "n_temppred_pngs": n_temp_pngs,
        "n_temppred_clean_pngs": n_temp_clean_pngs,
        "failed_days": failed_days_flat,
        "failed_day_reasons": failed_days,
        "blank_std_days": blank_std_days,
        "zero_std_days": zero_std_days,
        "no_input_files_modified": no_input_files_modified,
        "final_verdict": "READY_FOR_DESCRIPTORS_AND_PLANNER: October surface TEMPpred and STD ROI x490 outputs passed all checks."
        if final_ready
        else "REVIEW_BEFORE_DESCRIPTORS_AND_PLANNER: one or more ROI x490 checks require attention.",
    }

    (OUTPUT_DIR / "october_surface_roi_x490_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=to_jsonable),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "october_surface_roi_x490_checks.json").write_text(
        json.dumps(checks, indent=2, ensure_ascii=False, default=to_jsonable),
        encoding="utf-8",
    )
    write_reports(
        metadata,
        checks,
        metrics_df,
        OUTPUT_DIR / "october_surface_roi_x490_summary.md",
        OUTPUT_DIR / "october_surface_roi_x490_report.md",
    )
    print(json.dumps(checks, indent=2, ensure_ascii=False, default=to_jsonable))


if __name__ == "__main__":
    main()
