from __future__ import annotations

import csv
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = Path(__file__).resolve().parent
OUT_DIR = SCENARIO_DIR / "outputs" / "mask_investigation"
DIAG_DIR = OUT_DIR / "plots"


@dataclass(frozen=True)
class OperationCrop:
    lat_start: int
    lat_stop: int
    lon_start: int
    lon_stop: int


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_config(cfg_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("planner_cfg", cfg_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Config_file.py from {cfg_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_mask_out(mask_path: Path, ny: int, nx: int) -> dict[str, Any]:
    with mask_path.open("r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline().strip()
        ncols = int(f.readline().split()[0])
        _ = [f.readline().strip() for _ in range(ncols)]
        vals = [float(line.strip().split()[0]) for line in f if line.strip()]

    arr = np.asarray(vals, dtype=np.float64)
    if arr.size % (ny * nx) != 0:
        raise RuntimeError(f"mask.out cannot be reshaped to ny*nx={ny*nx}, got size={arr.size}")
    n_layers = arr.size // (ny * nx)
    layers = arr.reshape(n_layers, ny, nx)
    layer0 = layers[0]
    return {
        "rows": int(arr.size),
        "n_layers": int(n_layers),
        "layers_equal": bool(all(np.array_equal(layers[0], layers[i]) for i in range(1, n_layers))),
        "layer0": layer0,
        "layer0_unique_values": [float(v) for v in np.unique(layer0)],
        "layer0_zero_fraction": float(np.mean(layer0 == 0)),
        "layer0_neg1_fraction": float(np.mean(layer0 == -1)),
    }


def operation_crop(lat: np.ndarray, lon: np.ndarray, ll: list[float], ur: list[float]) -> OperationCrop:
    lat_start = next(i for i, v in enumerate(lat) if v > ll[0])
    lat_stop = next(i for i, v in enumerate(lat) if v > ur[0]) - 1
    lon_start = next(i for i, v in enumerate(lon) if v > ll[1])
    lon_stop = next(i for i, v in enumerate(lon) if v > ur[1]) - 1
    return OperationCrop(lat_start=lat_start, lat_stop=lat_stop, lon_start=lon_start, lon_stop=lon_stop)


def build_obstacle_mask(
    lat_op: np.ndarray,
    lon_op: np.ndarray,
    objs_ll: list[list[float]],
    objs_ur: list[list[float]],
) -> tuple[np.ndarray, list[dict[str, int]]]:
    h = int(lat_op.size)
    w = int(lon_op.size)
    obs = np.zeros((h, w), dtype=bool)
    boxes: list[dict[str, int]] = []
    for idx in range(len(objs_ll)):
        lat_obj_start = next(i for i, v in enumerate(lat_op) if v > objs_ll[idx][0]) - 1
        lat_obj_stop = next(i for i, v in enumerate(lat_op) if v > objs_ur[idx][0])
        lon_obj_start = next(i for i, v in enumerate(lon_op) if v > objs_ll[idx][1]) - 1
        lon_obj_stop = next(i for i, v in enumerate(lon_op) if v > objs_ur[idx][1])

        latitude_obj = np.arange(lat_obj_start, lat_obj_stop + 1, 1).tolist()
        longitude_obj = np.arange(lon_obj_start, lon_obj_stop + 1, 1).tolist()
        if abs(lat_obj_start - lat_obj_stop) <= 1:
            latitude_obj = [lat_obj_start, lat_obj_start]
        if abs(lon_obj_start - lon_obj_stop) <= 1:
            longitude_obj = [lon_obj_start, lon_obj_start]

        for i in range(h):
            for j in range(w):
                if (i in latitude_obj) and (j in longitude_obj):
                    obs[i, j] = True
        boxes.append(
            {
                "lat_start": int(lat_obj_start),
                "lat_stop": int(lat_obj_stop),
                "lon_start": int(lon_obj_start),
                "lon_stop": int(lon_obj_stop),
            }
        )
    return obs, boxes


def imshow_binary(
    arr01: np.ndarray,
    title: str,
    out_path: Path,
    cbar_label: str,
    extent: list[float] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    im = ax.imshow(arr01.astype(np.float32), origin="lower", cmap="gray_r", vmin=0.0, vmax=1.0, extent=extent, aspect="auto")
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def imshow_float(
    arr: np.ndarray,
    title: str,
    out_path: Path,
    cbar_label: str,
    cmap: str = "viridis",
    extent: list[float] | None = None,
) -> None:
    arr_plot = np.asarray(arr, dtype=np.float64).copy()
    arr_plot[~np.isfinite(arr_plot)] = np.nan
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(color="white")
    im = ax.imshow(arr_plot, origin="lower", cmap=cmap_obj, extent=extent, aspect="auto")
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def plot_component_comparison(
    land_invalid: np.ndarray,
    depth_additional_invalid: np.ndarray,
    obstacle_additional_invalid: np.ndarray,
    final_valid: np.ndarray,
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.2))
    panels = [
        (land_invalid, "Land/invalid mask contribution"),
        (depth_additional_invalid, "Additional invalid by depth"),
        (obstacle_additional_invalid, "Additional invalid by obstacles"),
        (final_valid, "Final valid cells (after all masks)"),
    ]
    for ax, (arr, title) in zip(axes.ravel(), panels):
        im = ax.imshow(arr.astype(np.float32), origin="lower", cmap="gray_r", vmin=0.0, vmax=1.0)
        ax.set_title(title)
        ax.set_xlabel("lon idx")
        ax.set_ylabel("lat idx")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def write_csv_rows(rows: list[dict[str, Any]], out_csv: Path) -> None:
    ensure_dir(out_csv.parent)
    if not rows:
        out_csv.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def metric_row(name: str, count: int, total: int) -> dict[str, Any]:
    return {
        "metric": name,
        "count_cells": int(count),
        "total_cells": int(total),
        "fraction": float(count / total) if total > 0 else np.nan,
        "percent": float(100.0 * count / total) if total > 0 else np.nan,
    }


def main() -> None:
    ensure_dir(OUT_DIR)
    ensure_dir(DIAG_DIR)

    source_nc = ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc"
    mask_out_path = ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "Nazare_31-10-2024_1" / "mask.out"
    interface_nc = SCENARIO_DIR / "inputs" / "31-10-2024_predModel_1_planner_interface.nc"
    cfg_path = ROOT / "OptimalPlanning_Lucrezia" / "Config_file.py"

    cfg = load_config(cfg_path)

    src = xr.open_dataset(source_nc, decode_times=False)
    std = np.asarray(src["STD"].values, dtype=np.float64)
    bathy = np.asarray(src["BATHY"].values, dtype=np.float64)
    lat = np.asarray(src["LAT"].values, dtype=np.float64)
    lon = np.asarray(src["LON"].values, dtype=np.float64)
    src.close()

    iface = xr.open_dataset(interface_nc, decode_times=False)
    temperr_current = np.asarray(iface["temperr"].values, dtype=np.float64)
    tbath_current = np.asarray(iface["tbath"].values, dtype=np.float64)
    landt_current = np.asarray(iface["landt"].values, dtype=np.int8)
    iface.close()

    ny, nx = int(landt_current.shape[0]), int(landt_current.shape[1])
    mdiag = read_mask_out(mask_out_path, ny=ny, nx=nx)
    layer0 = np.asarray(mdiag["layer0"], dtype=np.float64)
    landt_from_mask_zero = (layer0 == 0).astype(np.int8)
    landt_from_mask_neg1 = (layer0 == -1).astype(np.int8)

    agree_zero = float(np.mean(landt_from_mask_zero == landt_current))
    agree_neg1 = float(np.mean(landt_from_mask_neg1 == landt_current))
    best_convention = "zero_is_sea" if agree_zero >= agree_neg1 else "neg1_is_sea"
    landt_from_mask_best = landt_from_mask_zero if best_convention == "zero_is_sea" else landt_from_mask_neg1

    crop = operation_crop(lat=lat, lon=lon, ll=cfg.OPERATION_LL_CORNER, ur=cfg.OPERATION_UR_CORNER)

    sl = np.s_[crop.lat_start : crop.lat_stop, crop.lon_start : crop.lon_stop]
    lat_op = lat[crop.lat_start : crop.lat_stop]
    lon_op = lon[crop.lon_start : crop.lon_stop]
    extent_op = [float(np.min(lon_op)), float(np.max(lon_op)), float(np.min(lat_op)), float(np.max(lat_op))]

    landt_current_op = landt_current[sl]
    landt_mask_best_op = landt_from_mask_best[sl]

    temperr_op = temperr_current[sl].copy()
    bathy_op = bathy[sl].copy()
    tbath_neg_op = (-bathy)[sl].copy()
    tbath_pos_op = bathy[sl].copy()

    obs_mask, obs_boxes = build_obstacle_mask(
        lat_op=lat_op,
        lon_op=lon_op,
        objs_ll=cfg.OBJECTS_LL_CORNER,
        objs_ur=cfg.OBJECTS_UR_CORNER,
    )

    valid_after_landt = np.isfinite(temperr_op)
    depth_invalid_neg = tbath_neg_op > -float(cfg.MINIMUM_DEPTH)
    depth_invalid_pos = tbath_pos_op > -float(cfg.MINIMUM_DEPTH)

    newly_invalid_depth_neg = valid_after_landt & depth_invalid_neg
    valid_after_depth_neg = valid_after_landt & (~depth_invalid_neg)

    newly_invalid_obs_neg = valid_after_depth_neg & obs_mask
    final_valid_neg = valid_after_depth_neg & (~obs_mask)
    final_invalid_neg = ~final_valid_neg

    total_op = int(final_valid_neg.size)

    # Quantitative summary rows.
    rows: list[dict[str, Any]] = []
    rows.append(metric_row("op_total_cells", total_op, total_op))
    rows.append(metric_row("landt_current_valid_cells", int(np.count_nonzero(valid_after_landt)), total_op))
    rows.append(metric_row("landt_current_invalid_cells", int(np.count_nonzero(~valid_after_landt)), total_op))
    rows.append(metric_row("additional_invalid_by_depth_tbath_neg", int(np.count_nonzero(newly_invalid_depth_neg)), total_op))
    rows.append(metric_row("valid_after_depth_tbath_neg", int(np.count_nonzero(valid_after_depth_neg)), total_op))
    rows.append(metric_row("additional_invalid_by_obstacles", int(np.count_nonzero(newly_invalid_obs_neg)), total_op))
    rows.append(metric_row("final_valid_tbath_neg", int(np.count_nonzero(final_valid_neg)), total_op))
    rows.append(metric_row("final_invalid_tbath_neg", int(np.count_nonzero(final_invalid_neg)), total_op))

    # H1 explicit test: bathy sign.
    newly_invalid_depth_pos = valid_after_landt & depth_invalid_pos
    valid_after_depth_pos = valid_after_landt & (~depth_invalid_pos)
    rows.append(metric_row("additional_invalid_by_depth_tbath_pos", int(np.count_nonzero(newly_invalid_depth_pos)), total_op))
    rows.append(metric_row("valid_after_depth_tbath_pos", int(np.count_nonzero(valid_after_depth_pos)), total_op))

    # H2/H3 quantitative comparisons for land masks.
    disagree_landt_vs_mask_zero = landt_current_op != landt_from_mask_zero[sl]
    disagree_landt_vs_mask_neg1 = landt_current_op != landt_from_mask_neg1[sl]
    disagree_landt_vs_mask_best = landt_current_op != landt_mask_best_op
    rows.append(metric_row("landt_disagreement_vs_maskout_zero", int(np.count_nonzero(disagree_landt_vs_mask_zero)), total_op))
    rows.append(metric_row("landt_disagreement_vs_maskout_neg1", int(np.count_nonzero(disagree_landt_vs_mask_neg1)), total_op))
    rows.append(metric_row("landt_disagreement_vs_maskout_best", int(np.count_nonzero(disagree_landt_vs_mask_best)), total_op))

    write_csv_rows(rows, OUT_DIR / "mask_diagnostics_summary.csv")

    summary_json = {
        "inputs": {
            "source_nc": str(source_nc),
            "interface_nc": str(interface_nc),
            "mask_out": str(mask_out_path),
            "config_file": str(cfg_path),
        },
        "crop": {
            "lat_start": int(crop.lat_start),
            "lat_stop": int(crop.lat_stop),
            "lon_start": int(crop.lon_start),
            "lon_stop": int(crop.lon_stop),
            "shape": [int(landt_current_op.shape[0]), int(landt_current_op.shape[1])],
        },
        "mask_out": {
            "n_layers": mdiag["n_layers"],
            "layers_equal": mdiag["layers_equal"],
            "layer0_unique_values": mdiag["layer0_unique_values"],
            "layer0_zero_fraction": mdiag["layer0_zero_fraction"],
            "layer0_neg1_fraction": mdiag["layer0_neg1_fraction"],
            "agreement_current_with_zero_is_sea": agree_zero,
            "agreement_current_with_neg1_is_sea": agree_neg1,
            "best_convention": best_convention,
        },
        "h1_bathy_sign_test": {
            "rule": "depth invalid when tbath > -MINIMUM_DEPTH",
            "minimum_depth": float(cfg.MINIMUM_DEPTH),
            "additional_invalid_cells_tbath_neg": int(np.count_nonzero(newly_invalid_depth_neg)),
            "additional_invalid_cells_tbath_pos": int(np.count_nonzero(newly_invalid_depth_pos)),
            "valid_after_depth_tbath_neg": int(np.count_nonzero(valid_after_depth_neg)),
            "valid_after_depth_tbath_pos": int(np.count_nonzero(valid_after_depth_pos)),
        },
        "component_counts": {row["metric"]: row for row in rows},
        "obstacle_boxes_index_space": obs_boxes,
    }
    (OUT_DIR / "mask_diagnostics_summary.json").write_text(json.dumps(summary_json, indent=2), encoding="utf-8")

    # Required diagnostic plots.
    imshow_binary(
        arr01=landt_current_op,
        title="diag_01 landt current (1=sea,0=land)",
        out_path=DIAG_DIR / "diag_01_landt_current.png",
        cbar_label="landt current",
        extent=extent_op,
    )
    imshow_binary(
        arr01=landt_mask_best_op,
        title=f"diag_02 landt from mask.out ({best_convention})",
        out_path=DIAG_DIR / "diag_02_landt_from_maskout.png",
        cbar_label="landt from mask.out",
        extent=extent_op,
    )
    imshow_float(
        arr=bathy_op,
        title="diag_03 bathymetry raw (BATHY)",
        out_path=DIAG_DIR / "diag_03_bathymetry_raw.png",
        cbar_label="BATHY (m)",
        cmap="cividis",
        extent=extent_op,
    )
    imshow_binary(
        arr01=depth_invalid_neg.astype(np.int8),
        title=f"diag_04 depth mask (tbath>-{cfg.MINIMUM_DEPTH}m, tbath=-BATHY)",
        out_path=DIAG_DIR / "diag_04_bathymetry_mask_lt_40m.png",
        cbar_label="1=masked by depth",
        extent=extent_op,
    )
    imshow_binary(
        arr01=obs_mask.astype(np.int8),
        title="diag_05 obstacle mask",
        out_path=DIAG_DIR / "diag_05_obstacle_mask.png",
        cbar_label="1=obstacle mask",
        extent=extent_op,
    )
    imshow_binary(
        arr01=final_valid_neg.astype(np.int8),
        title="diag_06 final combined mask (1=valid)",
        out_path=DIAG_DIR / "diag_06_final_combined_mask.png",
        cbar_label="1=valid final",
        extent=extent_op,
    )
    plot_component_comparison(
        land_invalid=(~valid_after_landt).astype(np.int8),
        depth_additional_invalid=newly_invalid_depth_neg.astype(np.int8),
        obstacle_additional_invalid=newly_invalid_obs_neg.astype(np.int8),
        final_valid=final_valid_neg.astype(np.int8),
        out_path=DIAG_DIR / "diag_07_mask_component_comparison.png",
    )

    print(f"[OK] diagnostics dir: {DIAG_DIR}")
    print(f"[OK] summary csv: {OUT_DIR / 'mask_diagnostics_summary.csv'}")
    print(f"[OK] summary json: {OUT_DIR / 'mask_diagnostics_summary.json'}")


if __name__ == "__main__":
    main()

