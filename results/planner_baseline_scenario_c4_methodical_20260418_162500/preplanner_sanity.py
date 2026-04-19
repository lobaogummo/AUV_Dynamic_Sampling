from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import xarray as xr


def load_config(config_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("planner_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load config from {config_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def nearest_index(values: np.ndarray, target: float) -> int:
    idx = int(np.argmin(np.abs(values - float(target))))
    return idx


def map_obstacle_indices(lat_op: np.ndarray, lon_op: np.ndarray, ll: list[float], ur: list[float]) -> tuple[int, int, int, int]:
    lat_start = next(i for i, val in enumerate(lat_op) if val > ll[0]) - 1
    lat_stop = next(i for i, val in enumerate(lat_op) if val > ur[0])
    lon_start = next(i for i, val in enumerate(lon_op) if val > ll[1]) - 1
    lon_stop = next(i for i, val in enumerate(lon_op) if val > ur[1])
    return lat_start, lat_stop, lon_start, lon_stop


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    repo_root = scenario_dir.parents[1]

    interface_nc = scenario_dir / "inputs" / "31-10-2024_predModel_1_planner_interface.nc"
    validation_dir = scenario_dir / "outputs" / "validation"
    figures_dir = validation_dir / "figures"
    validation_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(repo_root / "OptimalPlanning_Lucrezia" / "Config_file.py")

    ds = xr.open_dataset(interface_nc, decode_times=False)
    temperr = ds["temperr"].values.astype(np.float64)
    tbath = ds["tbath"].values.astype(np.float64)
    landt = ds["landt"].values.astype(np.int8)
    lat = ds["lat"].values.astype(np.float64)
    lon = ds["lon"].values.astype(np.float64)
    ds.close()

    lat_start = next(i for i, v in enumerate(lat) if v > cfg.OPERATION_LL_CORNER[0])
    lat_stop = next(i for i, v in enumerate(lat) if v > cfg.OPERATION_UR_CORNER[0]) - 1
    lon_start = next(i for i, v in enumerate(lon) if v > cfg.OPERATION_LL_CORNER[1])
    lon_stop = next(i for i, v in enumerate(lon) if v > cfg.OPERATION_UR_CORNER[1]) - 1

    temperr_op = temperr[lat_start:lat_stop, lon_start:lon_stop].copy()
    tbath_op = tbath[lat_start:lat_stop, lon_start:lon_stop].copy()
    landt_op = landt[lat_start:lat_stop, lon_start:lon_stop].copy()
    lat_op = lat[lat_start:lat_stop].copy()
    lon_op = lon[lon_start:lon_stop].copy()

    total_cells = int(temperr_op.size)
    finite_after_land = int(np.count_nonzero(np.isfinite(temperr_op)))

    # Same depth mask rule as planner.
    temperr_after_depth = temperr_op.copy()
    for i in range(temperr_after_depth.shape[0]):
        for j in range(temperr_after_depth.shape[1]):
            if tbath_op[i, j] > -float(cfg.MINIMUM_DEPTH):
                temperr_after_depth[i, j] = -np.inf
    finite_after_depth = int(np.count_nonzero(np.isfinite(temperr_after_depth)))

    # Same obstacle mask rule as planner.
    temperr_after_obstacles = temperr_after_depth.copy()
    obstacle_boxes_idx: list[dict[str, int]] = []
    for idx in range(len(cfg.OBJECTS_LL_CORNER)):
        la0, la1, lo0, lo1 = map_obstacle_indices(lat_op, lon_op, cfg.OBJECTS_LL_CORNER[idx], cfg.OBJECTS_UR_CORNER[idx])
        lat_idx = np.arange(la0, la1 + 1, 1).tolist()
        lon_idx = np.arange(lo0, lo1 + 1, 1).tolist()
        if abs(la0 - la1) <= 1:
            lat_idx = [la0, la0]
        if abs(lo0 - lo1) <= 1:
            lon_idx = [lo0, lo0]
        for i in range(temperr_after_obstacles.shape[0]):
            for j in range(temperr_after_obstacles.shape[1]):
                if (i in lat_idx) and (j in lon_idx):
                    temperr_after_obstacles[i, j] = -np.inf
        obstacle_boxes_idx.append({"lat_start": int(la0), "lat_stop": int(la1), "lon_start": int(lo0), "lon_stop": int(lo1)})
    finite_after_obstacles = int(np.count_nonzero(np.isfinite(temperr_after_obstacles)))

    finite_vals = temperr_after_obstacles[np.isfinite(temperr_after_obstacles)]
    final_min = float(np.min(finite_vals)) if finite_vals.size else None
    final_max = float(np.max(finite_vals)) if finite_vals.size else None
    final_mean = float(np.mean(finite_vals)) if finite_vals.size else None

    # Start/end checks with same nearest-point logic used by planner Utils.get_depots().
    depots: list[dict[str, Any]] = []
    start_end = list(cfg.STARTING_POINTS) + list(cfg.ENDING_POINTS)
    for k, p in enumerate(start_end):
        li = nearest_index(lat_op, float(p[0]))
        lj = nearest_index(lon_op, float(p[1]))
        on_land = bool(landt_op[li, lj] == 0)
        finite_final = bool(np.isfinite(temperr_after_obstacles[li, lj]))
        depots.append(
            {
                "idx": int(k),
                "role": "start" if k < len(cfg.STARTING_POINTS) else "end",
                "latlon_requested": [float(p[0]), float(p[1])],
                "grid_idx_op": [int(li), int(lj)],
                "grid_latlon": [float(lat_op[li]), float(lon_op[lj])],
                "on_land_mask": on_land,
                "finite_after_all_masks": finite_final,
            }
        )

    # Plot with start/end and obstacle boxes.
    arr_plot = temperr_after_obstacles.copy()
    arr_plot[~np.isfinite(arr_plot)] = np.nan
    fig, ax = plt.subplots(figsize=(9.0, 5.3))
    extent = [float(np.min(lon_op)), float(np.max(lon_op)), float(np.min(lat_op)), float(np.max(lat_op))]
    im = ax.imshow(arr_plot, origin="lower", extent=extent, aspect="auto", cmap="viridis")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("temperr after all masks")
    ax.set_title("Preplanner Sanity - Operational Map with Constraints")
    ax.set_xlabel("Longitude (deg)")
    ax.set_ylabel("Latitude (deg)")

    for i, (ll, ur) in enumerate(zip(cfg.OBJECTS_LL_CORNER, cfg.OBJECTS_UR_CORNER), start=1):
        x0 = float(ll[1])
        y0 = float(ll[0])
        w = float(ur[1] - ll[1])
        h = float(ur[0] - ll[0])
        rect = patches.Rectangle((x0, y0), w, h, linewidth=1.4, edgecolor="red", facecolor="none")
        ax.add_patch(rect)
        ax.text(x0, y0, f"obs{i}", color="red", fontsize=8, va="bottom", ha="left")

    for i, p in enumerate(cfg.STARTING_POINTS, start=1):
        ax.scatter(float(p[1]), float(p[0]), marker="*", s=90, color="lime", edgecolors="black")
        ax.text(float(p[1]), float(p[0]), f"S{i}", color="black", fontsize=8, ha="left", va="bottom")
    for i, p in enumerate(cfg.ENDING_POINTS, start=1):
        ax.scatter(float(p[1]), float(p[0]), marker="X", s=75, color="orange", edgecolors="black")
        ax.text(float(p[1]), float(p[0]), f"E{i}", color="black", fontsize=8, ha="left", va="bottom")

    fig.tight_layout()
    fig.savefig(figures_dir / "preplanner_operational_map_with_constraints.png", dpi=170)
    plt.close(fig)

    sanity = {
        "operation_crop": {
            "lat_start": int(lat_start),
            "lat_stop": int(lat_stop),
            "lon_start": int(lon_start),
            "lon_stop": int(lon_stop),
            "shape": [int(temperr_op.shape[0]), int(temperr_op.shape[1])],
        },
        "finite_cells": {
            "total_cells": total_cells,
            "after_land_mask": finite_after_land,
            "after_depth_mask": finite_after_depth,
            "after_obstacle_mask": finite_after_obstacles,
        },
        "final_temperr_stats": {"min": final_min, "max": final_max, "mean": final_mean},
        "depots_check": depots,
        "obstacle_boxes_idx": obstacle_boxes_idx,
        "assessments": {
            "crop_not_empty": bool(total_cells > 0),
            "final_map_not_empty": bool(finite_after_obstacles > 0),
            "all_depots_not_on_land": bool(all(not d["on_land_mask"] for d in depots)),
            "all_depots_finite_after_masks": bool(all(d["finite_after_all_masks"] for d in depots)),
            "lat_monotonic": bool(np.all(np.diff(lat) > 0)),
            "lon_monotonic": bool(np.all(np.diff(lon) > 0)),
        },
    }

    (validation_dir / "preplanner_sanity.json").write_text(json.dumps(sanity, indent=2), encoding="utf-8")

    lines = [
        "# preplanner_sanity",
        "",
        "Verificacao rapida do pre-processamento espacial/mask do planner, aplicada ao ficheiro de interface gerado (sem alterar planner).",
        "",
        "## Resultado",
        f"- shape operacional: `{temperr_op.shape[0]} x {temperr_op.shape[1]}`",
        f"- celulas finitas apos land/invalid mask: `{finite_after_land} / {total_cells}`",
        f"- celulas finitas apos mascara de profundidade (`MINIMUM_DEPTH={cfg.MINIMUM_DEPTH}`): `{finite_after_depth} / {total_cells}`",
        f"- celulas finitas apos obstaculos: `{finite_after_obstacles} / {total_cells}`",
        f"- `temperr2d_op` final (finitas): min `{final_min:.6f}`, max `{final_max:.6f}`, media `{final_mean:.6f}`" if final_mean is not None else "- `temperr2d_op` final sem celulas finitas",
        "",
        "## Checks adicionais",
        f"- depots fora de terra (landt): `{sanity['assessments']['all_depots_not_on_land']}`",
        f"- depots em celulas finitas apos todas as mascaras: `{sanity['assessments']['all_depots_finite_after_masks']}`",
        f"- monotonia eixos lat/lon: `lat={sanity['assessments']['lat_monotonic']}`, `lon={sanity['assessments']['lon_monotonic']}`",
        "",
        "## Conclusao",
        "- O baseline so deve avancar para corrida do planner se `final_map_not_empty=True` e todos os depots forem validos.",
    ]
    (validation_dir / "preplanner_sanity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] preplanner sanity saved:", validation_dir / "preplanner_sanity.md")


if __name__ == "__main__":
    main()

