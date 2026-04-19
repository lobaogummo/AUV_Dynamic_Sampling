from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


SCENARIO_NAME = "SURFACE_DAYFIX_30-10-2024_PRIOR_surface_only"

# Same operational corners used by the planner (Config_file.py).
OPERATION_LL_CORNER = [39.50934, -9.43520]
OPERATION_UR_CORNER = [39.75313, -9.03402]


def _inspect_nc(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return out

    ds = xr.open_dataset(path, decode_times=False)
    required = ["STD", "LAT", "LON", "BATHY"]
    out["required_present"] = {k: bool(k in ds.variables) for k in required}
    out["has_all_required"] = all(out["required_present"].values())
    out["dims"] = {k: {d: int(s) for d, s in ds[k].sizes.items()} for k in required if k in ds.variables}
    out["std_ndim"] = int(ds["STD"].ndim) if "STD" in ds.variables else None
    out["std_dims"] = list(ds["STD"].dims) if "STD" in ds.variables else []
    ds.close()
    return out


def _extract_surface_std(
    ds: xr.Dataset,
    preferred_day_idx: int | None = None,
) -> tuple[np.ndarray, str, int | None, list[dict[str, Any]]]:
    std_raw = np.asarray(ds["STD"].values, dtype=np.float32)
    day_stats: list[dict[str, Any]] = []

    if std_raw.ndim == 2:
        return std_raw, "STD[LAT,LON] direct", None, day_stats

    if std_raw.ndim != 3:
        raise RuntimeError(f"surface-only expects STD 2D or day+2D; got shape={std_raw.shape}")

    n_day = int(std_raw.shape[0])
    for i in range(n_day):
        arr = np.asarray(std_raw[i], dtype=np.float64)
        finite = np.isfinite(arr)
        if np.any(finite):
            day_stats.append(
                {
                    "day_index": i,
                    "finite_fraction": float(np.mean(finite)),
                    "min": float(np.nanmin(arr)),
                    "max": float(np.nanmax(arr)),
                    "mean": float(np.nanmean(arr)),
                    "std": float(np.nanstd(arr)),
                }
            )
        else:
            day_stats.append(
                {
                    "day_index": i,
                    "finite_fraction": 0.0,
                    "min": None,
                    "max": None,
                    "mean": None,
                    "std": None,
                }
            )

    if preferred_day_idx is not None:
        if preferred_day_idx < 0 or preferred_day_idx >= n_day:
            raise RuntimeError(f"preferred_day_idx={preferred_day_idx} is out of bounds for STD day dimension size={n_day}")
        idx = preferred_day_idx
    else:
        # Deterministic and evidence-based choice:
        # pick the day slice with highest finite mean uncertainty.
        score = []
        for st in day_stats:
            m = st["mean"]
            score.append(float(m) if m is not None and np.isfinite(m) else -np.inf)
        idx = int(np.argmax(np.asarray(score)))

    return np.asarray(std_raw[idx], dtype=np.float32), f"STD[day={idx},LAT,LON]", idx, day_stats


def _read_surface_map(path: Path, preferred_day_idx: int | None = None) -> dict[str, Any]:
    ds = xr.open_dataset(path, decode_times=False)
    lat = np.asarray(ds["LAT"].values, dtype=np.float64)
    lon = np.asarray(ds["LON"].values, dtype=np.float64)
    std_map, source_slice, day_idx, day_stats = _extract_surface_std(ds, preferred_day_idx=preferred_day_idx)
    ds.close()
    return {
        "lat": lat,
        "lon": lon,
        "std_map": std_map,
        "source_slice": source_slice,
        "day_index_used": day_idx,
        "day_stats": day_stats,
    }


def _save_side_by_side_map(
    std_current: np.ndarray,
    lat_current: np.ndarray,
    lon_current: np.ndarray,
    title_current: str,
    std_fixed: np.ndarray,
    lat_fixed: np.ndarray,
    lon_fixed: np.ndarray,
    title_fixed: str,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    a = np.asarray(std_current, dtype=np.float64).copy()
    b = np.asarray(std_fixed, dtype=np.float64).copy()
    a[~np.isfinite(a)] = np.nan
    b[~np.isfinite(b)] = np.nan

    combo = np.concatenate([a[np.isfinite(a)], b[np.isfinite(b)]])
    vmin = float(np.min(combo))
    vmax = float(np.max(combo))

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="white")

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), constrained_layout=True)
    for ax, arr, lat, lon, title in [
        (axes[0], a, lat_current, lon_current, title_current),
        (axes[1], b, lat_fixed, lon_fixed, title_fixed),
    ]:
        extent = [float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))]
        im = ax.imshow(arr, origin="lower", extent=extent, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("Longitude (degrees)")
        ax.set_ylabel("Latitude (degrees)")

    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.94)
    cbar.set_label("STD (surface-only)")
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def _build_interface_from_arrays(
    source_nc: Path,
    interface_nc: Path,
    lat: np.ndarray,
    lon: np.ndarray,
    temperr: np.ndarray,
    source_slice_note: str,
) -> dict[str, Any]:
    ds = xr.open_dataset(source_nc, decode_times=False)
    tbath = -np.asarray(ds["BATHY"].values, dtype=np.float32)
    ds.close()

    landt = (np.isfinite(temperr) & np.isfinite(tbath)).astype(np.int8)
    temperr = np.asarray(temperr, dtype=np.float32).copy()
    tbath = tbath.copy()
    temperr[landt == 0] = -np.inf
    tbath[landt == 0] = np.nan

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
        coords={"lat": ("lat", lat), "lon": ("lon", lon)},
        attrs={
            "scenario_name": SCENARIO_NAME,
            "source_file": str(source_nc),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "notes": "Surface-only day fix using prior model file; no vertical aggregation.",
        },
    )
    out_ds["temperr"].attrs.update({"long_name": "temperature_uncertainty", "source_var": "STD", "source_slice": source_slice_note})
    out_ds["tbath"].attrs.update({"long_name": "bathymetry_for_planner", "source_var": "BATHY", "transform": "tbath=-BATHY"})
    out_ds["landt"].attrs.update({"long_name": "land_sea_mask", "convention": "1=sea(valid), 0=land/invalid"})
    out_ds.to_netcdf(interface_nc)
    out_ds.close()

    return {
        "interface_nc": str(interface_nc),
        "latlon_shape": [int(lat.size), int(lon.size)],
        "expected_crop_shape": [int(lat_stop - lat_start), int(lon_stop - lon_start)],
        "source_slice_note": source_slice_note,
    }


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    repo_root = scenario_dir.parents[1]

    current_source = repo_root / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc"
    preferred_day_source = repo_root / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc"

    out_dir = scenario_dir / "outputs" / "surface_day_fix"
    inputs_dir = scenario_dir / "inputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    report_md = out_dir / "surface_day_fix_report.md"
    summary_md = out_dir / "surface_day_fix_summary.md"
    comparison_png = out_dir / "surface_day_comparison.png"
    checks_json = out_dir / "surface_day_fix_checks.json"
    interface_nc = inputs_dir / "30-10-2024_surface_dayfix_planner_interface.nc"
    manifest_json = out_dir / "surface_day_fix_manifest.json"

    current_info = _inspect_nc(current_source)
    preferred_info = _inspect_nc(preferred_day_source)

    status = "FILE NOT FOUND"
    selection_note = ""
    selected_source: Path | None = None
    selected_payload: dict[str, Any] | None = None
    interface_info: dict[str, Any] | None = None

    if not preferred_info["exists"]:
        status = "FILE NOT FOUND"
        selection_note = "Required prior file `30-10-2024_predModel_1.nc` does not exist in the expected path."
    elif not preferred_info.get("has_all_required"):
        status = "FILE FOUND BUT STD NOT SURFACE-COMPATIBLE"
        selection_note = "Required variables (`STD`,`LAT`,`LON`,`BATHY`) are not fully present."
    elif preferred_info.get("std_ndim") not in (2, 3):
        status = "FILE FOUND BUT STD NOT SURFACE-COMPATIBLE"
        selection_note = f"STD has unsupported ndim={preferred_info.get('std_ndim')} for surface-only extraction."
    else:
        selected_source = preferred_day_source
        selected_payload = _read_surface_map(selected_source)
        status = "FOUND AND FIXED"
        if selected_payload["day_index_used"] is None:
            selection_note = "Using `30-10-2024_predModel_1.nc` with direct 2D STD."
        else:
            selection_note = (
                "Using `30-10-2024_predModel_1.nc` with one 2D day slice of STD "
                f"(selected day index={selected_payload['day_index_used']})."
            )

    # current map for comparison (always 2D)
    current_payload = _read_surface_map(current_source)

    if selected_source is not None and selected_payload is not None:
        _save_side_by_side_map(
            std_current=current_payload["std_map"],
            lat_current=current_payload["lat"],
            lon_current=current_payload["lon"],
            title_current="Current source: 31-10-2024_predModel_1.nc",
            std_fixed=selected_payload["std_map"],
            lat_fixed=selected_payload["lat"],
            lon_fixed=selected_payload["lon"],
            title_fixed=(
                "Day-fix source: 30-10-2024_predModel_1.nc"
                if selected_payload["day_index_used"] is None
                else f"Day-fix source: 30-10-2024_predModel_1.nc [day={selected_payload['day_index_used']}]"
            ),
            out_path=comparison_png,
        )
        interface_info = _build_interface_from_arrays(
            source_nc=selected_source,
            interface_nc=interface_nc,
            lat=selected_payload["lat"],
            lon=selected_payload["lon"],
            temperr=selected_payload["std_map"],
            source_slice_note=selected_payload["source_slice"],
        )

    checks_payload = {
        "status": status,
        "selection_note": selection_note,
        "current_source": current_info,
        "preferred_day_source": preferred_info,
        "current_surface_extraction": {
            "source_slice": current_payload["source_slice"],
            "day_index_used": current_payload["day_index_used"],
        },
        "selected_source": str(selected_source) if selected_source is not None else None,
        "selected_surface_extraction": {
            "source_slice": selected_payload["source_slice"] if selected_payload is not None else None,
            "day_index_used": selected_payload["day_index_used"] if selected_payload is not None else None,
            "day_stats": selected_payload["day_stats"] if selected_payload is not None else [],
        },
        "interface_output": interface_info,
    }
    checks_json.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    report_lines = [
        "# surface_day_fix_report",
        "",
        "## Goal",
        "- Keep surface-only and force the prior model day file (`30-10-2024_predModel_1.nc`).",
        "",
        "## Current source",
        f"- `{current_source}`",
        f"- STD dims: `{current_info.get('dims', {}).get('STD')}`",
        "",
        "## Required prior source",
        f"- `{preferred_day_source}`",
        f"- exists: `{preferred_info.get('exists')}`",
        f"- required vars present (`STD`,`LAT`,`LON`,`BATHY`): `{preferred_info.get('required_present')}`",
        f"- STD dims: `{preferred_info.get('dims', {}).get('STD')}`",
        f"- STD ndim: `{preferred_info.get('std_ndim')}`",
        "",
        "## Decision",
        f"- status: `{status}`",
        f"- note: {selection_note}",
    ]

    if selected_payload is not None and selected_payload["day_stats"]:
        report_lines.extend(["", "## STD day diagnostics (prior file)"])
        for st in selected_payload["day_stats"]:
            report_lines.append(
                "- day={day_index}: mean={mean:.6f}, std={std:.6f}, min={min:.6f}, max={max:.6f}, finite_fraction={finite_fraction:.6f}".format(
                    **st
                )
            )

    if selected_source is not None and interface_info is not None:
        report_lines.extend(
            [
                f"- selected source: `{selected_source}`",
                f"- selected slice: `{selected_payload['source_slice']}`",
                f"- interface generated: `{interface_nc}`",
                "- rules kept: `temperr = STD` (single 2D surface slice), `tbath = -BATHY`, no other pipeline changes.",
                f"- comparison figure: `{comparison_png}`",
            ]
        )
    else:
        report_lines.append("- interface not generated due to incompatibility.")

    report_md.write_text("\n".join(report_lines), encoding="utf-8")

    summary_lines = [
        "# surface_day_fix_summary",
        "",
        f"- status: `{status}`",
        f"- current source: `{current_source.name}`",
        f"- required prior source: `{preferred_day_source.name}`",
        f"- note: {selection_note}",
    ]
    if selected_source is not None and selected_payload is not None:
        summary_lines.extend(
            [
                f"- selected source: `{selected_source.name}`",
                f"- selected slice: `{selected_payload['source_slice']}`",
                "- rules kept: `temperr=STD` (single 2D slice), `tbath=-BATHY`",
                f"- figure: `{comparison_png.name}`",
                f"- interface: `{interface_nc.name}`",
            ]
        )
    summary_md.write_text("\n".join(summary_lines), encoding="utf-8")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "selection_note": selection_note,
        "paths": {
            "current_source": str(current_source),
            "required_prior_source": str(preferred_day_source),
            "selected_source": str(selected_source) if selected_source is not None else None,
            "comparison_figure": str(comparison_png) if selected_source is not None else None,
            "interface_output": str(interface_nc) if selected_source is not None else None,
            "report": str(report_md),
            "summary": str(summary_md),
            "checks_json": str(checks_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("[STATUS]", status)
    print("[NOTE]", selection_note)
    if selected_source is not None and selected_payload is not None:
        print("[OK] selected source:", selected_source)
        print("[OK] selected slice:", selected_payload["source_slice"])
        print("[OK] comparison:", comparison_png)
        print("[OK] interface:", interface_nc)
    print("[OK] report:", report_md)
    print("[OK] summary:", summary_md)


if __name__ == "__main__":
    main()
