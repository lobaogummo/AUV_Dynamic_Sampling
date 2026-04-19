from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


SCENARIO_NAME = "TEST_C4_HighRes_31-10-2024_INST1_predModel_BASELINE"

# Same operational corners used by the planner (Config_file.py).
OPERATION_LL_CORNER = [39.50934, -9.43520]
OPERATION_UR_CORNER = [39.75313, -9.03402]


def _read_mask_out(mask_path: Path, ny: int, nx: int) -> dict[str, Any]:
    with mask_path.open("r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline().strip()
        ncols = int(f.readline().split()[0])
        _ = [f.readline().strip() for _ in range(ncols)]
        vals = [float(line.strip().split()[0]) for line in f if line.strip()]

    arr = np.asarray(vals, dtype=np.float64)
    out: dict[str, Any] = {
        "rows": int(arr.size),
        "unique_values": [float(v) for v in np.unique(arr)],
        "reshape_ok": False,
        "n_layers": None,
        "agreement": None,
    }

    if arr.size % (ny * nx) != 0:
        return out

    n_layers = arr.size // (ny * nx)
    layers = arr.reshape(n_layers, ny, nx)
    out["reshape_ok"] = True
    out["n_layers"] = int(n_layers)
    out["layers_equal"] = bool(all(np.array_equal(layers[0], layers[i]) for i in range(1, n_layers)))
    out["layer0_unique_values"] = [float(v) for v in np.unique(layers[0])]
    out["layer0_zero_fraction"] = float(np.mean(layers[0] == 0))
    out["layer0_neg1_fraction"] = float(np.mean(layers[0] == -1))
    out["layer0"] = layers[0]
    return out


def _summarize_array(name: str, arr: np.ndarray) -> dict[str, Any]:
    arr_np = np.asarray(arr)
    finite = np.isfinite(arr_np)
    out: dict[str, Any] = {
        "name": name,
        "dtype": str(arr_np.dtype),
        "shape": "x".join(str(s) for s in arr_np.shape),
        "size": int(arr_np.size),
        "finite_count": int(np.count_nonzero(finite)),
        "nan_count": int(np.count_nonzero(np.isnan(arr_np))),
        "min": None,
        "max": None,
        "mean": None,
        "std": None,
    }
    if np.any(finite):
        vals = arr_np[finite]
        out["min"] = float(np.min(vals))
        out["max"] = float(np.max(vals))
        out["mean"] = float(np.mean(vals))
        out["std"] = float(np.std(vals))
    return out


def _write_summary_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["name", "dtype", "shape", "size", "finite_count", "nan_count", "min", "max", "mean", "std"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _save_map(
    arr: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    out_path: Path,
    title: str,
    cbar_label: str,
    cmap_name: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    cmap = plt.get_cmap(cmap_name).copy()
    arr_plot = np.asarray(arr, dtype=np.float64).copy()
    arr_plot[~np.isfinite(arr_plot)] = np.nan
    if np.issubdtype(arr_plot.dtype, np.floating):
        cmap.set_bad(color="white")

    extent = [float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))]
    im = ax.imshow(arr_plot, origin="lower", extent=extent, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    repo_root = scenario_dir.parents[1]  # FILIPA_DADOS

    source_nc = repo_root / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc"
    mask_out = (
        repo_root
        / "data"
        / "TEST_C4"
        / "HighRes"
        / "Daily_dpt_20241030_NewTest_1"
        / "Nazare_31-10-2024_1"
        / "mask.out"
    )

    inputs_dir = scenario_dir / "inputs"
    validation_dir = scenario_dir / "outputs" / "validation"
    figures_dir = validation_dir / "figures"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    interface_nc = inputs_dir / "31-10-2024_predModel_1_planner_interface.nc"
    summary_csv = validation_dir / "interface_summary.csv"
    checks_json = validation_dir / "checks.json"
    run_report_md = validation_dir / "run_report.md"
    manifest_json = scenario_dir / "manifest.json"

    ds = xr.open_dataset(source_nc, decode_times=False)

    # Physical 1D axes for this C4 file are stored as LAT/LON variables.
    lat = ds["LAT"].values.astype(np.float64)
    lon = ds["LON"].values.astype(np.float64)

    std_raw = ds["STD"].values.astype(np.float32)
    if std_raw.ndim == 2:
        temperr = std_raw.astype(np.float32, copy=False)
        std_source_note = "STD[lat,lon] direct"
    elif std_raw.ndim == 3:
        # Fallback kept for compatibility with older C4 files with day dimension.
        temperr = std_raw[0].astype(np.float32, copy=False)
        std_source_note = "STD[0,:,:] from 3D field"
    else:
        raise RuntimeError(f"Unexpected STD dims: {std_raw.shape}, expected 2D or 3D")

    bathy_pos = ds["BATHY"].values.astype(np.float32, copy=False)
    tbath = -bathy_pos

    # Final rule for landt in baseline interface.
    landt = (np.isfinite(temperr) & np.isfinite(tbath)).astype(np.int8)

    # Planner baseline expects invalid area in temperr as -inf (used by contour/POI logic).
    temperr = temperr.copy()
    tbath = tbath.copy()
    temperr[landt == 0] = -np.inf
    tbath[landt == 0] = np.nan

    # Crop estimate using planner logic on physical axes.
    lat_start = next(i for i, v in enumerate(lat) if v > OPERATION_LL_CORNER[0])
    lat_stop = next(i for i, v in enumerate(lat) if v > OPERATION_UR_CORNER[0]) - 1
    lon_start = next(i for i, v in enumerate(lon) if v > OPERATION_LL_CORNER[1])
    lon_stop = next(i for i, v in enumerate(lon) if v > OPERATION_UR_CORNER[1]) - 1

    out_ds = xr.Dataset(
        data_vars={
            "temperr": (("lat", "lon"), temperr),
            "tbath": (("lat", "lon"), tbath),
            "landt": (("lat", "lon"), landt),
        },
        coords={
            "lat": ("lat", lat),
            "lon": ("lon", lon),
        },
        attrs={
            "scenario_name": SCENARIO_NAME,
            "source_file": str(source_nc),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "notes": "Planner baseline interface; no planner or cost modifications.",
        },
    )

    out_ds["temperr"].attrs.update({"long_name": "temperature_uncertainty", "source_var": "STD", "source_slice": std_source_note})
    out_ds["tbath"].attrs.update({"long_name": "bathymetry_for_planner", "source_var": "BATHY", "transform": "tbath=-BATHY"})
    out_ds["landt"].attrs.update({"long_name": "land_sea_mask", "convention": "1=sea(valid), 0=land/invalid"})
    out_ds["lat"].attrs.update({"long_name": "latitude", "units": "degrees_north"})
    out_ds["lon"].attrs.update({"long_name": "longitude", "units": "degrees_east"})

    out_ds.to_netcdf(interface_nc)
    ds.close()

    # Validation.
    vds = xr.open_dataset(interface_nc, decode_times=False)
    required_vars = {"temperr", "tbath", "landt", "lat", "lon"}
    present_vars = set(vds.data_vars) | set(vds.coords)
    checks: dict[str, Any] = {
        "required_vars_present": required_vars.issubset(present_vars),
        "present_vars": sorted(present_vars),
        "shape_temperr": list(vds["temperr"].shape),
        "shape_tbath": list(vds["tbath"].shape),
        "shape_landt": list(vds["landt"].shape),
        "shape_lat": list(vds["lat"].shape),
        "shape_lon": list(vds["lon"].shape),
        "lat_monotonic_increasing": bool(np.all(np.diff(vds["lat"].values) > 0)),
        "lon_monotonic_increasing": bool(np.all(np.diff(vds["lon"].values) > 0)),
    }

    temperr_v = vds["temperr"].values
    tbath_v = vds["tbath"].values
    landt_v = vds["landt"].values

    checks["landt_binary_values"] = sorted(int(v) for v in np.unique(landt_v))
    checks["landt_sea_fraction"] = float(np.mean(landt_v == 1))
    checks["landt_land_fraction"] = float(np.mean(landt_v == 0))
    checks["temperr_finite_fraction"] = float(np.mean(np.isfinite(temperr_v)))
    checks["tbath_finite_fraction"] = float(np.mean(np.isfinite(tbath_v)))
    checks["landt_matches_temperr_finite"] = bool(np.array_equal((landt_v == 1), np.isfinite(temperr_v)))
    checks["landt_matches_tbath_finite"] = bool(np.array_equal((landt_v == 1), np.isfinite(tbath_v)))

    # Compare with mask.out as reference-only diagnostic.
    mask_diag = _read_mask_out(mask_out, ny=int(vds.sizes["lat"]), nx=int(vds.sizes["lon"]))
    if mask_diag.get("reshape_ok"):
        layer0 = mask_diag["layer0"]
        sea_from_mask_zero = (layer0 == 0)
        sea_from_mask_neg1 = (layer0 == -1)
        checks["mask_out_zero_matches_landt_sea"] = float(np.mean(sea_from_mask_zero == (landt_v == 1)))
        checks["mask_out_neg1_matches_landt_sea"] = float(np.mean(sea_from_mask_neg1 == (landt_v == 1)))
        # remove heavy array from diagnostics payload
        mask_diag.pop("layer0", None)

    with checks_json.open("w", encoding="utf-8") as f:
        json.dump({"checks": checks, "mask_out_diagnostics": mask_diag}, f, indent=2)

    summary_rows = [
        _summarize_array("temperr", temperr_v),
        _summarize_array("tbath", tbath_v),
        _summarize_array("landt", landt_v.astype(np.float32)),
        _summarize_array("lat", vds["lat"].values),
        _summarize_array("lon", vds["lon"].values),
    ]
    _write_summary_csv(summary_rows, summary_csv)

    # Plots.
    _save_map(
        arr=temperr_v,
        lat=vds["lat"].values,
        lon=vds["lon"].values,
        out_path=figures_dir / "temperr_map.png",
        title="Planner Interface - temperr",
        cbar_label="Uncertainty proxy (STD)",
        cmap_name="viridis",
    )
    _save_map(
        arr=tbath_v,
        lat=vds["lat"].values,
        lon=vds["lon"].values,
        out_path=figures_dir / "tbath_map.png",
        title="Planner Interface - tbath",
        cbar_label="Depth (m, negative)",
        cmap_name="cividis",
    )
    _save_map(
        arr=landt_v.astype(np.float32),
        lat=vds["lat"].values,
        lon=vds["lon"].values,
        out_path=figures_dir / "landt_map.png",
        title="Planner Interface - landt",
        cbar_label="Mask (1=sea, 0=land)",
        cmap_name="gray_r",
        vmin=0.0,
        vmax=1.0,
    )

    # Simple histogram for temperr support.
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    vals = temperr_v[np.isfinite(temperr_v)]
    ax.hist(vals, bins=50, color="#2a9d8f", alpha=0.9, edgecolor="black", linewidth=0.3)
    ax.set_title("temperr Distribution (finite cells)")
    ax.set_xlabel("temperr")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(figures_dir / "temperr_hist.png", dpi=160)
    plt.close(fig)

    vds.close()

    run_report_lines = [
        "# run_report",
        "",
        "## Interface File",
        f"- path: `{interface_nc}`",
        f"- source: `{source_nc}`",
        "",
        "## Required Fields",
        f"- required_vars_present: `{checks['required_vars_present']}`",
        f"- present_vars: `{checks['present_vars']}`",
        "",
        "## Shapes",
        f"- temperr: `{checks['shape_temperr']}`",
        f"- tbath: `{checks['shape_tbath']}`",
        f"- landt: `{checks['shape_landt']}`",
        f"- lat: `{checks['shape_lat']}`",
        f"- lon: `{checks['shape_lon']}`",
        "",
        "## Ranges and Validity",
        f"- landt sea fraction: `{checks['landt_sea_fraction']:.6f}`",
        f"- landt land fraction: `{checks['landt_land_fraction']:.6f}`",
        f"- temperr finite fraction: `{checks['temperr_finite_fraction']:.6f}`",
        f"- tbath finite fraction: `{checks['tbath_finite_fraction']:.6f}`",
        f"- landt matches temperr finite: `{checks['landt_matches_temperr_finite']}`",
        f"- landt matches tbath finite: `{checks['landt_matches_tbath_finite']}`",
        "",
        "## Expected Planner Crop (native logic)",
        f"- OPERATION_LL_CORNER: `{OPERATION_LL_CORNER}`",
        f"- OPERATION_UR_CORNER: `{OPERATION_UR_CORNER}`",
        f"- indices: lat_start={lat_start}, lat_stop={lat_stop}, lon_start={lon_start}, lon_stop={lon_stop}",
        f"- expected shape: `{lat_stop - lat_start} x {lon_stop - lon_start}`",
        "",
        "## Artifacts",
        f"- summary table: `{summary_csv}`",
        f"- checks: `{checks_json}`",
        f"- figures: `{figures_dir}`",
        "",
    ]
    run_report_md.write_text("\n".join(run_report_lines), encoding="utf-8")

    manifest_payload = {
        "scenario_name": SCENARIO_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "predmodel": str(source_nc),
            "mask_out_reference": str(mask_out),
        },
        "output_files": {
            "interface_nc": str(interface_nc),
            "validation_report": str(run_report_md),
            "validation_summary_csv": str(summary_csv),
            "validation_checks_json": str(checks_json),
        },
        "interface_rules": {
            "temperr": {"source": "STD", "source_slice": std_source_note},
            "tbath": {"source": "BATHY", "transform": "tbath = -BATHY"},
            "landt": {"rule": "landt = 1 where finite(temperr) and finite(tbath), else 0"},
            "grid_policy": "keep native C4 grid 180x240; no external regridding",
        },
        "planner_operational_crop": {
            "operation_ll_corner": OPERATION_LL_CORNER,
            "operation_ur_corner": OPERATION_UR_CORNER,
            "indices": {
                "lat_start": int(lat_start),
                "lat_stop": int(lat_stop),
                "lon_start": int(lon_start),
                "lon_stop": int(lon_stop),
            },
            "expected_shape": [int(lat_stop - lat_start), int(lon_stop - lon_start)],
        },
    }
    manifest_json.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    print("[OK] interface generated:", interface_nc)
    print("[OK] validation report:", run_report_md)
    print("[OK] manifest:", manifest_json)


if __name__ == "__main__":
    main()
