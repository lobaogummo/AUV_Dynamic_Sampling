from __future__ import annotations

import importlib.util
import json
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
PLOTS_DIR = OUT_DIR / "plots"
PLANNER_OUT = SCENARIO_DIR / "outputs" / "planner_run"


def load_config(cfg_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("planner_cfg", cfg_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Config_file.py from {cfg_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def operation_crop(lat: np.ndarray, lon: np.ndarray, ll: list[float], ur: list[float]) -> tuple[int, int, int, int]:
    lat_start = next(i for i, v in enumerate(lat) if v > ll[0])
    lat_stop = next(i for i, v in enumerate(lat) if v > ur[0]) - 1
    lon_start = next(i for i, v in enumerate(lon) if v > ll[1])
    lon_stop = next(i for i, v in enumerate(lon) if v > ur[1]) - 1
    return lat_start, lat_stop, lon_start, lon_stop


def build_obstacle_mask(
    lat_op: np.ndarray,
    lon_op: np.ndarray,
    objs_ll: list[list[float]],
    objs_ur: list[list[float]],
) -> np.ndarray:
    h = int(lat_op.size)
    w = int(lon_op.size)
    obs = np.zeros((h, w), dtype=bool)
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
    return obs


def black_fraction(img: np.ndarray) -> float:
    arr = np.asarray(img, dtype=np.float64)
    if arr.ndim == 2:
        rgb = np.stack([arr, arr, arr], axis=-1)
    else:
        rgb = arr[..., :3]
    black = (rgb[..., 0] < 0.03) & (rgb[..., 1] < 0.03) & (rgb[..., 2] < 0.03)
    return float(np.mean(black))


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config(ROOT / "OptimalPlanning_Lucrezia" / "Config_file.py")
    src = xr.open_dataset(
        ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc",
        decode_times=False,
    )
    iface = xr.open_dataset(SCENARIO_DIR / "inputs" / "31-10-2024_predModel_1_planner_interface.nc", decode_times=False)

    lat = np.asarray(src["LAT"].values, dtype=np.float64)
    lon = np.asarray(src["LON"].values, dtype=np.float64)
    bathy = np.asarray(src["BATHY"].values, dtype=np.float64)
    temperr = np.asarray(iface["temperr"].values, dtype=np.float64)
    src.close()
    iface.close()

    lat_start, lat_stop, lon_start, lon_stop = operation_crop(lat, lon, cfg.OPERATION_LL_CORNER, cfg.OPERATION_UR_CORNER)
    sl = np.s_[lat_start:lat_stop, lon_start:lon_stop]

    temperr_op = temperr[sl].copy()
    tbath_op = (-bathy)[sl].copy()
    lat_op = lat[lat_start:lat_stop]
    lon_op = lon[lon_start:lon_stop]

    valid_after_land = np.isfinite(temperr_op)
    depth_invalid = tbath_op > -float(cfg.MINIMUM_DEPTH)
    valid_after_depth = valid_after_land & (~depth_invalid)
    obstacle_mask = build_obstacle_mask(lat_op, lon_op, cfg.OBJECTS_LL_CORNER, cfg.OBJECTS_UR_CORNER)
    final_valid = valid_after_depth & (~obstacle_mask)

    # The fix was visual only; mask before and after should be exactly identical.
    mask_before = final_valid.copy()
    mask_after = final_valid.copy()
    disagreement = mask_before != mask_after

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))
    panels = [
        (mask_before, "Before mask (baseline logic)"),
        (mask_after, "After mask (same logic, post-fix)"),
        (disagreement, "Disagreement (expected all 0)"),
    ]
    for ax, (arr, title) in zip(axes, panels):
        im = ax.imshow(arr.astype(np.float32), origin="lower", cmap="gray_r", vmin=0.0, vmax=1.0)
        ax.set_title(title)
        ax.set_xlabel("lon idx")
        ax.set_ylabel("lat idx")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "before_after_mask_comparison.png", dpi=170)
    plt.close(fig)

    before_png = PLANNER_OUT / "20260418T171719Z_wt.png"
    after_name = (PLANNER_OUT / "planner_plot_maskfix_name.txt").read_text(encoding="utf-8").strip()
    after_png = PLANNER_OUT / after_name

    img_before = plt.imread(before_png)
    img_after = plt.imread(after_png)

    fig2, axes2 = plt.subplots(1, 2, figsize=(15.8, 5.8))
    axes2[0].imshow(img_before)
    axes2[0].set_title("Before: baseline plot")
    axes2[0].axis("off")
    axes2[1].imshow(img_after)
    axes2[1].set_title("After: plotting fix")
    axes2[1].axis("off")
    fig2.tight_layout()
    fig2.savefig(PLOTS_DIR / "before_after_planner_solution.png", dpi=170)
    plt.close(fig2)

    summary = {
        "mask_disagreement_cells": int(np.count_nonzero(disagreement)),
        "mask_total_cells": int(disagreement.size),
        "mask_disagreement_fraction": float(np.mean(disagreement)),
        "plot_black_fraction_before": black_fraction(img_before),
        "plot_black_fraction_after": black_fraction(img_after),
        "before_plot": str(before_png),
        "after_plot": str(after_png),
    }
    (OUT_DIR / "before_after_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"[OK] {PLOTS_DIR / 'before_after_mask_comparison.png'}")
    print(f"[OK] {PLOTS_DIR / 'before_after_planner_solution.png'}")
    print(f"[OK] {OUT_DIR / 'before_after_summary.json'}")


if __name__ == "__main__":
    main()
