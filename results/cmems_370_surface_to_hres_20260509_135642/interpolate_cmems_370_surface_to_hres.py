from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator


RAW_FILE = Path(r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\01.Data\ALL\thetao_20260427.nc")
PREDMODEL_ROOT = Path(r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\02.Simulations\HighRes")
HRES_OCTOBER_ROOT = Path(r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\01.Data\October\HRes")
CODE_ROOT = Path(r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\00.Code")
OUT_DIR = Path(__file__).resolve().parent

SELECTED_DEPTH_INDEX_1BASED = 1
VALIDATION_DATES = ["2024-10-10", "2024-10-13", "2024-10-31"]

# From Filipa's write14days.m.
OPERATION_LL_CORNER = (39.50955, -9.43575)
OPERATION_UR_CORNER = (39.75365, -9.03419)
MARGIN_CELLS = 4
INC = 10


def to_python_dates(time_values, units, calendar="standard") -> list[str]:
    out = netCDF4.num2date(
        time_values,
        units=units,
        calendar=calendar,
        only_use_cftime_datetimes=False,
        only_use_python_datetimes=False,
    )
    return [x.date().isoformat() if hasattr(x, "date") else str(x)[:10] for x in np.ravel(out)]


def read_target_grid():
    target_file = sorted(PREDMODEL_ROOT.rglob("01-10-2024_predModel_1.nc"))[0]
    with netCDF4.Dataset(target_file) as ds:
        lat = np.asarray(ds.variables["LAT"][:], dtype=np.float64)
        lon = np.asarray(ds.variables["LON"][:], dtype=np.float64)
        bathy = np.asarray(ds.variables["BATHY"][:], dtype=np.float32)
    return target_file, lat, lon, bathy


def crop_indices(lat, lon):
    idx_lat_max = int(np.argmin(np.abs(lat - OPERATION_UR_CORNER[0]))) + MARGIN_CELLS
    idx_lat_min = int(np.argmin(np.abs(lat - OPERATION_LL_CORNER[0]))) - MARGIN_CELLS
    idx_lon_max = int(np.argmin(np.abs(lon - OPERATION_UR_CORNER[1]))) + MARGIN_CELLS
    idx_lon_min = int(np.argmin(np.abs(lon - OPERATION_LL_CORNER[1]))) - MARGIN_CELLS
    return idx_lat_min, idx_lat_max, idx_lon_min, idx_lon_max


def interpolate_slice_to_hres(source_lat_lon: np.ndarray, target_shape=(180, 240)) -> np.ndarray:
    """Equivalent of MATLAB interp2 on index coordinates for a LAT x LON array."""
    source = np.asarray(source_lat_lon, dtype=np.float64)
    nlat, nlon = source.shape
    lat_idx_new = np.linspace(0, nlat - 1, target_shape[0])
    lon_idx_new = np.linspace(0, nlon - 1, target_shape[1])
    yy, xx = np.meshgrid(lat_idx_new, lon_idx_new, indexing="ij")
    interp = RegularGridInterpolator(
        (np.arange(nlat, dtype=np.float64), np.arange(nlon, dtype=np.float64)),
        source,
        method="linear",
        bounds_error=False,
        fill_value=np.nan,
    )
    out = interp(np.column_stack([yy.ravel(), xx.ravel()])).reshape(target_shape)
    return out.astype(np.float32)


def finite_metrics(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() == 0:
        return {
            "n_compare": 0,
            "rmse": np.nan,
            "mae": np.nan,
            "max_abs_error": np.nan,
            "pearson": np.nan,
        }
    diff = a[mask] - b[mask]
    pearson = np.corrcoef(a[mask], b[mask])[0, 1] if mask.sum() > 2 and np.std(a[mask]) > 0 and np.std(b[mask]) > 0 else np.nan
    return {
        "n_compare": int(mask.sum()),
        "rmse": float(np.sqrt(np.mean(diff**2))),
        "mae": float(np.mean(np.abs(diff))),
        "max_abs_error": float(np.max(np.abs(diff))),
        "pearson": float(pearson) if np.isfinite(pearson) else np.nan,
    }


def get_hres_reference_for_date(date_str):
    ymd = date_str.replace("-", "")
    path = HRES_OCTOBER_ROOT / f"CMEMSnaza_{ymd}_HResNew.nc"
    with netCDF4.Dataset(path) as ds:
        time = np.asarray(ds.variables["TIME"][:])
        units = getattr(ds.variables["TIME"], "units", "")
        if not units and ds.variables["TIME"].dimensions:
            units = ds.variables["TIME"].dimensions[0]
        dates = to_python_dates(time, units)
        idx = dates.index(date_str)
        temp = np.asarray(ds.variables["TEMP"][idx, SELECTED_DEPTH_INDEX_1BASED - 1, :, :], dtype=np.float32)
        lat = np.asarray(ds.variables["LAT"][:], dtype=np.float64)
        lon = np.asarray(ds.variables["LON"][:], dtype=np.float64)
    return path, temp, lat, lon


def save_validation_figures(validation_records, raw_maps, ref_maps, diff_maps):
    n = len(validation_records)
    fig, axes = plt.subplots(n, 3, figsize=(10, 3.2 * n), constrained_layout=True)
    axes = np.atleast_2d(axes)
    vals = np.concatenate([m[np.isfinite(m)].ravel() for m in raw_maps + ref_maps])
    vmin, vmax = np.nanpercentile(vals, [2, 98])
    for i, rec in enumerate(validation_records):
        for ax, arr, title in [
            (axes[i, 0], raw_maps[i], f"{rec['date']} script"),
            (axes[i, 1], ref_maps[i], "Filipa HRes"),
            (axes[i, 2], diff_maps[i], "script - HRes"),
        ]:
            if "script -" in title:
                im = ax.imshow(arr, origin="lower", cmap="coolwarm")
            else:
                im = ax.imshow(arr, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
            ax.set_title(title, fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.colorbar(im, ax=ax, shrink=0.75)
    fig.savefig(OUT_DIR / "hres_interpolation_validation_panel.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, n, figsize=(4 * n, 3.5), constrained_layout=True)
    axes = np.atleast_1d(axes)
    absmax = np.nanmax([np.nanmax(np.abs(d)) for d in diff_maps])
    for ax, rec, diff in zip(axes, validation_records, diff_maps):
        im = ax.imshow(diff, origin="lower", cmap="coolwarm", vmin=-absmax, vmax=absmax)
        ax.set_title(f"{rec['date']}\nRMSE={rec['rmse']:.3g}", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.75)
    fig.savefig(OUT_DIR / "hres_interpolation_difference_maps.png", dpi=150)
    plt.close(fig)


def save_sample_figures(cube, dates, bathy, mask):
    sample_dates = ["2023-10-28", "2024-01-15", "2024-04-15", "2024-07-15", "2024-10-31"]
    sample_indices = [dates.index(d) for d in sample_dates if d in dates]
    fig, axes = plt.subplots(1, len(sample_indices), figsize=(3.2 * len(sample_indices), 3.2), constrained_layout=True)
    axes = np.atleast_1d(axes)
    vals = np.concatenate([cube[i][np.isfinite(cube[i])].ravel() for i in sample_indices])
    vmin, vmax = np.nanpercentile(vals, [2, 98])
    for ax, idx in zip(axes, sample_indices):
        im = ax.imshow(cube[idx], origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_title(dates[idx], fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.75)
    fig.savefig(OUT_DIR / "thetao_370_hres_sample_days.png", dpi=150)
    plt.close(fig)

    month_first = []
    seen = set()
    for i, d in enumerate(dates):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            month_first.append(i)
    fig, axes = plt.subplots(3, 5, figsize=(12, 7), constrained_layout=True)
    axes = axes.ravel()
    vals = np.concatenate([cube[i][np.isfinite(cube[i])].ravel() for i in month_first])
    vmin, vmax = np.nanpercentile(vals, [2, 98])
    for ax, idx in zip(axes, month_first):
        im = ax.imshow(cube[idx], origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_title(dates[idx], fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes[len(month_first):]:
        ax.axis("off")
    fig.colorbar(im, ax=axes.tolist(), shrink=0.6)
    fig.savefig(OUT_DIR / "thetao_370_hres_monthly_samples.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.5), constrained_layout=True)
    im0 = axes[0].imshow(bathy, origin="lower", cmap="terrain")
    axes[0].set_title("BATHY HRes")
    axes[0].set_xticks([])
    axes[0].set_yticks([])
    fig.colorbar(im0, ax=axes[0], shrink=0.8)
    im1 = axes[1].imshow(mask, origin="lower", cmap="gray")
    axes[1].set_title("MASK HRes")
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    fig.colorbar(im1, ax=axes[1], shrink=0.8)
    fig.savefig(OUT_DIR / "bathymetry_hres_mask.png", dpi=150)
    plt.close(fig)


def write_netcdf(path, cube, dates, lat, lon, bathy, mask, depth_value):
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("time", cube.shape[0])
        ds.createDimension("lat", cube.shape[1])
        ds.createDimension("lon", cube.shape[2])
        tvar = ds.createVariable("time", "i4", ("time",))
        t0 = datetime(1970, 1, 1)
        tvals = [(datetime.fromisoformat(d) - t0).days * 86400 for d in dates]
        tvar[:] = tvals
        tvar.units = "seconds since 1970-01-01 00:00:00"
        tvar.calendar = "standard"
        latv = ds.createVariable("LAT", "f4", ("lat",))
        lonv = ds.createVariable("LON", "f4", ("lon",))
        bv = ds.createVariable("BATHY", "f4", ("lat", "lon"), zlib=True, complevel=4)
        mv = ds.createVariable("MASK", "u1", ("lat", "lon"), zlib=True, complevel=4)
        tv = ds.createVariable("thetao_surface_hres", "f4", ("time", "lat", "lon"), zlib=True, complevel=4, fill_value=np.nan)
        latv[:] = lat
        lonv[:] = lon
        bv[:, :] = bathy
        mv[:, :] = mask.astype(np.uint8)
        tv[:, :, :] = cube
        tv.units = "degrees_C"
        tv.long_name = "CMEMS thetao surface interpolated to Filipa high-resolution grid"
        ds.selected_depth_index_1based = SELECTED_DEPTH_INDEX_1BASED
        ds.selected_depth_value_m = float(depth_value)
        ds.interpolation_method = "Filipa MATLAB write14days equivalent: crop operational CMEMS subset with 4-cell margin and linear interp2 on index grid, inc=10"
        ds.source_file = str(RAW_FILE)
        ds.target_grid_source = str(PREDMODEL_ROOT)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_file, target_lat, target_lon, target_bathy = read_target_grid()
    target_shape = tuple(target_bathy.shape)
    mask = np.isfinite(target_bathy)

    with netCDF4.Dataset(RAW_FILE) as raw:
        source_lat = np.asarray(raw.variables["latitude"][:], dtype=np.float64)
        source_lon = np.asarray(raw.variables["longitude"][:], dtype=np.float64)
        depth_values = np.asarray(raw.variables["depth"][:], dtype=np.float64)
        depth_value = float(depth_values[SELECTED_DEPTH_INDEX_1BASED - 1])
        time = np.asarray(raw.variables["time"][:])
        time_units = raw.variables["time"].units
        calendar = getattr(raw.variables["time"], "calendar", "standard")
        dates = to_python_dates(time, time_units, calendar)
        source_shape = tuple(raw.variables["thetao"].shape)
        idx_lat_min, idx_lat_max, idx_lon_min, idx_lon_max = crop_indices(source_lat, source_lon)
        crop_lat = source_lat[idx_lat_min : idx_lat_max + 1]
        crop_lon = source_lon[idx_lon_min : idx_lon_max + 1]
        computed_lat = np.linspace(crop_lat[0], crop_lat[-1], len(crop_lat) * INC)
        computed_lon = np.linspace(crop_lon[0], crop_lon[-1], len(crop_lon) * INC)
        orientation_confirmed = (
            target_shape == (len(computed_lat), len(computed_lon))
            and np.allclose(target_lat, computed_lat, atol=2e-5)
            and np.allclose(target_lon, computed_lon, atol=2e-5)
        )

        validation_records = []
        raw_maps = []
        ref_maps = []
        diff_maps = []
        for d in VALIDATION_DATES:
            time_idx = dates.index(d)
            raw_surface = np.asarray(
                raw.variables["thetao"][time_idx, SELECTED_DEPTH_INDEX_1BASED - 1, idx_lat_min : idx_lat_max + 1, idx_lon_min : idx_lon_max + 1],
                dtype=np.float32,
            )
            interp_map = interpolate_slice_to_hres(raw_surface, target_shape=target_shape)
            hres_path, hres_ref, hres_lat, hres_lon = get_hres_reference_for_date(d)
            metrics = finite_metrics(interp_map, hres_ref)
            metrics.update(
                {
                    "date": d,
                    "raw_time_index": int(time_idx),
                    "hres_reference_file": str(hres_path),
                    "shape_match": tuple(interp_map.shape) == tuple(hres_ref.shape) == target_shape,
                    "orientation_match": bool(np.allclose(hres_lat, target_lat) and np.allclose(hres_lon, target_lon)),
                    "max_abs_error": metrics["max_abs_error"],
                }
            )
            validation_records.append(metrics)
            raw_maps.append(interp_map)
            ref_maps.append(hres_ref)
            diff_maps.append(interp_map - hres_ref)

        save_validation_figures(validation_records, raw_maps, ref_maps, diff_maps)

        validation_ok = all(r["shape_match"] and r["orientation_match"] and np.isfinite(r["rmse"]) and r["rmse"] < 1e-5 for r in validation_records)
        if not validation_ok:
            # Continue because exact reproduction can differ by tiny IO/order details, but make the verdict explicit.
            print("WARNING: validation metrics are not exact; continuing and recording final verdict.")

        cube = np.empty((len(dates), target_shape[0], target_shape[1]), dtype=np.float32)
        for i in range(len(dates)):
            src = np.asarray(
                raw.variables["thetao"][i, SELECTED_DEPTH_INDEX_1BASED - 1, idx_lat_min : idx_lat_max + 1, idx_lon_min : idx_lon_max + 1],
                dtype=np.float32,
            )
            cube[i] = interpolate_slice_to_hres(src, target_shape=target_shape)

    np.save(OUT_DIR / "thetao_surface_370_hres.npy", cube)
    np.save(OUT_DIR / "LAT_hres.npy", target_lat.astype(np.float32))
    np.save(OUT_DIR / "LON_hres.npy", target_lon.astype(np.float32))
    np.save(OUT_DIR / "BATHY_hres.npy", target_bathy.astype(np.float32))
    np.save(OUT_DIR / "MASK_hres.npy", mask.astype(bool))
    pd.DataFrame({"time_index": range(len(dates)), "date": dates}).to_csv(OUT_DIR / "dates_370.csv", index=False)
    write_netcdf(OUT_DIR / "thetao_surface_370_hres.nc", cube, dates, target_lat, target_lon, target_bathy, mask, depth_value)
    save_sample_figures(cube, dates, target_bathy, mask)

    validation_rmse = {r["date"]: r["rmse"] for r in validation_records}
    validation_mae = {r["date"]: r["mae"] for r in validation_records}
    validation_pearson = {r["date"]: r["pearson"] for r in validation_records}
    nan_pct = float(np.isnan(cube).sum() / cube.size * 100)
    metadata = {
        "input_raw_file": str(RAW_FILE),
        "target_grid_source_file": str(target_file),
        "n_days": len(dates),
        "date_start": dates[0],
        "date_end": dates[-1],
        "selected_depth_index": SELECTED_DEPTH_INDEX_1BASED,
        "selected_depth_value_m": depth_value,
        "source_shape": list(source_shape),
        "source_crop_indices_python_0based_inclusive": {
            "lat_min": idx_lat_min,
            "lat_max": idx_lat_max,
            "lon_min": idx_lon_min,
            "lon_max": idx_lon_max,
        },
        "source_crop_shape_lat_lon": [len(crop_lat), len(crop_lon)],
        "target_shape": list(target_shape),
        "output_shape": list(cube.shape),
        "interpolation_method": "Linear RegularGridInterpolator on the same index grid as Filipa MATLAB interp2, crop from write14days.m, inc=10",
        "validation_dates": VALIDATION_DATES,
        "validation_records": validation_records,
        "validation_rmse": validation_rmse,
        "validation_mae": validation_mae,
        "validation_pearson": validation_pearson,
        "orientation_confirmed": bool(orientation_confirmed),
        "all_days_processed": bool(cube.shape[0] == 370 and dates[0] == "2023-10-28" and dates[-1] == "2024-10-31"),
        "nan_problem_detected": bool(nan_pct > 50),
        "nan_pct": nan_pct,
        "output_files": {
            "thetao_surface_370_hres.npy": str(OUT_DIR / "thetao_surface_370_hres.npy"),
            "LAT_hres.npy": str(OUT_DIR / "LAT_hres.npy"),
            "LON_hres.npy": str(OUT_DIR / "LON_hres.npy"),
            "BATHY_hres.npy": str(OUT_DIR / "BATHY_hres.npy"),
            "MASK_hres.npy": str(OUT_DIR / "MASK_hres.npy"),
            "dates_370.csv": str(OUT_DIR / "dates_370.csv"),
            "thetao_surface_370_hres.nc": str(OUT_DIR / "thetao_surface_370_hres.nc"),
        },
    }
    metadata["final_verdict"] = (
        "The 370-day CMEMS surface temperature dataset was interpolated to the canonical high-resolution grid and validated against the existing October HRes files."
        if metadata["all_days_processed"] and metadata["orientation_confirmed"] and validation_ok and not metadata["nan_problem_detected"]
        else "Interpolation completed, but validation or NaN checks require review before using as final."
    )
    (OUT_DIR / "cmems_370_surface_hres_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    matlab_notes = """## MATLAB Inspection Notes

- `write14days.m` downloads/reads `thetao_20260427.nc`, writes moving 14-day October windows to `01.Data/October/CMEMSGrid`, then converts those files to HRes.
- The HRes conversion crops the CMEMS grid around `OPERATION_LL_CORNER = [39.50955, -9.43575]` and `OPERATION_UR_CORNER = [39.75365, -9.03419]`, expands each side by 4 source cells, and uses `inc=10`.
- For each depth/time, MATLAB builds index grids and calls `interp2(..., linspace(..., size*inc))`; this Python script reproduces that as linear interpolation on source index coordinates.
- The crop is 18 latitude cells x 24 longitude cells, yielding the canonical 180 x 240 target grid.
"""
    val_df = pd.DataFrame(validation_records)
    val_cols = ["date", "rmse", "mae", "max_abs_error", "pearson", "shape_match", "orientation_match", "n_compare"]
    lines = ["| " + " | ".join(val_cols) + " |", "| " + " | ".join(["---"] * len(val_cols)) + " |"]
    for _, r in val_df[val_cols].iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in val_cols) + " |")
    val_table = "\n".join(lines)
    report = f"""# CMEMS 370 Surface To HRes Report

Output folder: `{OUT_DIR}`

{matlab_notes}

## Inputs

- Raw CMEMS file: `{RAW_FILE}`
- Target grid source file: `{target_file}`
- Depth: index `{SELECTED_DEPTH_INDEX_1BASED}`, value `{depth_value:.6f}` m
- Source shape: `{source_shape}`
- Target shape: `{target_shape}`
- Output shape: `{cube.shape}`

## Validation

{val_table}

## Outputs

- `thetao_surface_370_hres.npy`
- `LAT_hres.npy`
- `LON_hres.npy`
- `BATHY_hres.npy`
- `MASK_hres.npy`
- `dates_370.csv`
- `cmems_370_surface_hres_metadata.json`
- `thetao_surface_370_hres.nc`
- diagnostic figures

## Verdict

{metadata["final_verdict"]}
"""
    (OUT_DIR / "cmems_370_surface_to_hres_report.md").write_text(report, encoding="utf-8")

    summary = f"""# CMEMS 370 Surface To HRes Summary

- Days processed: `{len(dates)}` from `{dates[0]}` to `{dates[-1]}`
- Selected depth: index `{SELECTED_DEPTH_INDEX_1BASED}`, `{depth_value:.6f}` m
- Output array: `thetao_surface_370_hres.npy`, shape `{list(cube.shape)}`
- Target grid: `{list(target_shape)}`, from `{target_file}`
- Orientation confirmed: `{orientation_confirmed}`
- Validation dates: `{", ".join(VALIDATION_DATES)}`
- Validation RMSE: `{validation_rmse}`
- NaN percentage: `{nan_pct:.3f}%`

{metadata["final_verdict"]}
"""
    (OUT_DIR / "cmems_370_surface_to_hres_summary.md").write_text(summary, encoding="utf-8")

    print(f"Done: {OUT_DIR}")


if __name__ == "__main__":
    main()
