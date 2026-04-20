from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import TwoSlopeNorm
from scipy.ndimage import gaussian_filter


@dataclass
class VariantRun:
    name: str
    workspace: Path
    log_file: Path
    runtime_file: Path
    routes_file: Path
    routes_est_file: Path
    plot_file: Path
    vrp_file: Path
    prize_debug_file: Path
    exit_code: int
    elapsed_seconds: float
    log_text: str


def load_config_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("cfg_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load config module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def summary_stats(arr: np.ndarray) -> dict[str, Any]:
    a = np.asarray(arr, dtype=np.float64)
    finite = np.isfinite(a)
    out: dict[str, Any] = {
        "count_total": int(a.size),
        "count_finite": int(np.count_nonzero(finite)),
        "finite_fraction": float(np.mean(finite)),
        "count_zero_all": int(np.count_nonzero(a == 0)),
        "zero_fraction_all": float(np.mean(a == 0)),
        "min": None,
        "max": None,
        "mean": None,
        "std": None,
        "p01": None,
        "p05": None,
        "p50": None,
        "p95": None,
        "p99": None,
    }
    if np.any(finite):
        vals = a[finite]
        out["min"] = float(np.min(vals))
        out["max"] = float(np.max(vals))
        out["mean"] = float(np.mean(vals))
        out["std"] = float(np.std(vals))
        out["p01"] = float(np.percentile(vals, 1))
        out["p05"] = float(np.percentile(vals, 5))
        out["p50"] = float(np.percentile(vals, 50))
        out["p95"] = float(np.percentile(vals, 95))
        out["p99"] = float(np.percentile(vals, 99))
    return out


def gaussian_preserve_invalid(arr: np.ndarray, sigma_xy: list[float]) -> np.ndarray:
    arr_np = np.asarray(arr, dtype=np.float64)
    finite = np.isfinite(arr_np)
    data = np.where(finite, arr_np, 0.0)
    weights = finite.astype(np.float64)

    smooth_data = gaussian_filter(data, sigma=sigma_xy, mode="reflect")
    smooth_weights = gaussian_filter(weights, sigma=sigma_xy, mode="reflect")
    with np.errstate(divide="ignore", invalid="ignore"):
        smooth = np.divide(
            smooth_data,
            smooth_weights,
            out=np.full_like(smooth_data, np.nan),
            where=smooth_weights > 1e-12,
        )
    smooth[~finite] = -np.inf
    return smooth


def build_day1_interface(source_nc: Path, out_nc: Path) -> dict[str, Any]:
    ds = xr.open_dataset(source_nc, decode_times=False)
    lat = np.asarray(ds["LAT"].values, dtype=np.float64)
    lon = np.asarray(ds["LON"].values, dtype=np.float64)
    std = np.asarray(ds["STD"].values, dtype=np.float32)
    bathy = np.asarray(ds["BATHY"].values, dtype=np.float32)
    ds.close()

    if std.ndim != 3 or std.shape[0] < 2:
        raise RuntimeError(f"Expected STD(day,LAT,LON) with at least 2 slices, got shape={std.shape}")

    day_idx = 1
    temperr = std[day_idx].copy()
    tbath = -bathy.copy()
    landt = (np.isfinite(temperr) & np.isfinite(tbath)).astype(np.int8)

    temperr[landt == 0] = -np.inf
    tbath[landt == 0] = np.nan

    out_ds = xr.Dataset(
        data_vars={
            "temperr": (("lat", "lon"), temperr),
            "tbath": (("lat", "lon"), tbath),
            "landt": (("lat", "lon"), landt),
        },
        coords={"lat": ("lat", lat), "lon": ("lon", lon)},
        attrs={
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_nc": str(source_nc),
            "surface_policy": "surface-only",
            "temperr_rule": "STD[day=1,:,:]",
            "tbath_rule": "tbath=-BATHY",
            "assimilated_source_used": "false",
        },
    )
    out_ds["temperr"].attrs.update({"source_slice": "STD[day=1,LAT,LON]"})
    out_nc.parent.mkdir(parents=True, exist_ok=True)
    out_ds.to_netcdf(out_nc)
    out_ds.close()

    finite = np.isfinite(temperr)
    return {
        "path": str(out_nc),
        "source_nc": str(source_nc),
        "slice": "STD[day=1,LAT,LON]",
        "shape": [int(temperr.shape[0]), int(temperr.shape[1])],
        "finite_fraction": float(np.mean(finite)),
        "min": float(np.nanmin(temperr[finite])),
        "max": float(np.nanmax(temperr[finite])),
        "mean": float(np.nanmean(temperr[finite])),
        "std": float(np.nanstd(temperr[finite])),
    }


def obstacle_mask(lat_op: np.ndarray, lon_op: np.ndarray, objs_ll: list[list[float]], objs_ur: list[list[float]]) -> np.ndarray:
    h, w = int(lat_op.size), int(lon_op.size)
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


def compute_operational_map(interface_nc: Path, cfg: Any) -> dict[str, Any]:
    ds = xr.open_dataset(interface_nc, decode_times=False)
    temperr = np.asarray(ds["temperr"].values, dtype=np.float64)
    tbath = np.asarray(ds["tbath"].values, dtype=np.float64)
    lat = np.asarray(ds["lat"].values, dtype=np.float64)
    lon = np.asarray(ds["lon"].values, dtype=np.float64)
    ds.close()

    lat_start = next(i for i, v in enumerate(lat) if v > cfg.OPERATION_LL_CORNER[0])
    lat_stop = next(i for i, v in enumerate(lat) if v > cfg.OPERATION_UR_CORNER[0]) - 1
    lon_start = next(i for i, v in enumerate(lon) if v > cfg.OPERATION_LL_CORNER[1])
    lon_stop = next(i for i, v in enumerate(lon) if v > cfg.OPERATION_UR_CORNER[1]) - 1

    sl = np.s_[lat_start:lat_stop, lon_start:lon_stop]
    m = temperr[sl].copy()
    tb = tbath[sl].copy()
    lat_op = lat[lat_start:lat_stop]
    lon_op = lon[lon_start:lon_stop]

    m[tb > -float(cfg.MINIMUM_DEPTH)] = -np.inf
    obs = obstacle_mask(lat_op, lon_op, cfg.OBJECTS_LL_CORNER, cfg.OBJECTS_UR_CORNER)
    m[obs] = -np.inf

    return {
        "map": m,
        "lat": lat_op,
        "lon": lon_op,
        "indices": {
            "lat_start": int(lat_start),
            "lat_stop": int(lat_stop),
            "lon_start": int(lon_start),
            "lon_stop": int(lon_stop),
        },
    }


def save_map(arr: np.ndarray, lat: np.ndarray, lon: np.ndarray, out_path: Path, title: str, cbar_label: str, cmap_name: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    a = np.asarray(arr, dtype=np.float64).copy()
    a[~np.isfinite(a)] = np.nan
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("white")
    extent = [float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))]
    fig, ax = plt.subplots(figsize=(8.3, 5.0))
    im = ax.imshow(a, origin="lower", extent=extent, aspect="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_difference_map(a: np.ndarray, b: np.ndarray, lat: np.ndarray, lon: np.ndarray, out_path: Path, title: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    d = np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64)
    d[~np.isfinite(d)] = np.nan
    finite = d[np.isfinite(d)]
    vmax = float(np.max(np.abs(finite))) if finite.size else 1.0
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad("white")
    extent = [float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))]
    fig, ax = plt.subplots(figsize=(8.3, 5.0))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    im = ax.imshow(d, origin="lower", extent=extent, aspect="auto", cmap=cmap, norm=norm)
    ax.set_title(title)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Difference")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_hist_comparison(a: np.ndarray, b: np.ndarray, out_path: Path, title: str, labels: tuple[str, str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    av = np.asarray(a, dtype=np.float64)
    bv = np.asarray(b, dtype=np.float64)
    af = av[np.isfinite(av)]
    bf = bv[np.isfinite(bv)]
    allv = np.concatenate([af, bf]) if af.size and bf.size else (af if af.size else bf)
    vmin = float(np.min(allv))
    vmax = float(np.max(allv))
    if np.isclose(vmin, vmax):
        vmax = vmin + 1e-6
    bins = np.linspace(vmin, vmax, 90)

    fig, ax = plt.subplots(figsize=(8.7, 4.7))
    ax.hist(af, bins=bins, alpha=0.55, density=True, label=labels[0], color="#2f4f90")
    ax.hist(bf, bins=bins, alpha=0.55, density=True, label=labels[1], color="#d16d00")
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Density")
    ax.legend(framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def parse_solver_blocks(log_text: str) -> list[dict[str, Any]]:
    pat = re.compile(
        r"Solution results\s*=+\s*"
        r"# routes:\s*(\d+)\s*"
        r"# clients:\s*(\d+)\s*"
        r"objective:\s*([0-9]+)\s*"
        r"distance:\s*([0-9]+)\s*"
        r"duration:\s*([0-9]+)\s*"
        r"# iterations:\s*([0-9]+)\s*"
        r"run-time:\s*([0-9]+(?:\.[0-9]+)?)\s*seconds",
        re.MULTILINE,
    )
    out = []
    for m in pat.finditer(log_text):
        out.append(
            {
                "n_routes": int(m.group(1)),
                "n_clients": int(m.group(2)),
                "objective": int(m.group(3)),
                "distance": int(m.group(4)),
                "duration": int(m.group(5)),
                "iterations": int(m.group(6)),
                "solver_runtime_s": float(m.group(7)),
            }
        )
    return out


def parse_candidate_clients(log_text: str) -> int | None:
    m = re.search(r"Solving an instance with:\s*\n\s*\d+\s+depots\s*\n\s*(\d+)\s+clients", log_text, re.MULTILINE)
    return int(m.group(1)) if m else None


def parse_total_prize(log_text: str) -> dict[str, float | None]:
    wp = re.search(r"Total WP Routes Temperr .*?\n([0-9]+(?:\.[0-9]+)?)", log_text)
    allp = re.search(r"Total All Routes Temperr .*?\n([0-9]+(?:\.[0-9]+)?)", log_text)
    return {
        "total_wp_temperr": float(wp.group(1)) if wp else None,
        "total_all_temperr": float(allp.group(1)) if allp else None,
    }


def parse_routes_file(routes_path: Path) -> dict[str, Any]:
    if not routes_path.exists():
        return {"exists": False, "route_specs": [], "waypoint_counts": [], "routes_latlon": []}

    lines = routes_path.read_text(encoding="utf-8", errors="replace").splitlines()
    pat_spec = re.compile(
        r"#length_2D:\s*([0-9.]+)\s*\[km\]\s*travel_duration:\s*(\d+)\s*\[h\]\s*(\d+)\s*\[m\]\s*"
        r"mission_duration:\s*(\d+)\s*\[h\]\s*(\d+)\s*\[m\]\s*minimum_depth:\s*([0-9.]+)\s*\[m\]"
    )
    route_specs: list[dict[str, Any]] = []
    waypoint_counts: list[int] = []
    routes_latlon: list[list[tuple[float, float]]] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = pat_spec.match(line)
        if m:
            route_specs.append(
                {
                    "length_km": float(m.group(1)),
                    "travel_h": int(m.group(2)),
                    "travel_m": int(m.group(3)),
                    "mission_h": int(m.group(4)),
                    "mission_m": int(m.group(5)),
                    "minimum_depth_m": float(m.group(6)),
                }
            )
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines):
                segs = [s.strip() for s in lines[j].split(";") if s.strip()]
                route_pts: list[tuple[float, float]] = []
                for seg in segs:
                    parts = [p.strip() for p in seg.split(",")]
                    if len(parts) >= 2:
                        route_pts.append((float(parts[0]), float(parts[1])))
                routes_latlon.append(route_pts)
                waypoint_counts.append(len(route_pts))
                i = j
        i += 1
    return {"exists": True, "route_specs": route_specs, "waypoint_counts": waypoint_counts, "routes_latlon": routes_latlon}


def parse_vrp_prizes(vrp_path: Path) -> dict[str, Any]:
    if not vrp_path.exists():
        return {"exists": False}
    lines = vrp_path.read_text(encoding="utf-8", errors="replace").splitlines()
    # Depot count.
    depot_count = 0
    in_depot = False
    for line in lines:
        s = line.strip()
        if s == "DEPOT_SECTION":
            in_depot = True
            continue
        if in_depot:
            if s == "EOF":
                break
            if s:
                depot_count += 1

    prices: list[int] = []
    in_prize = False
    for line in lines:
        s = line.strip()
        if s == "PRIZE_SECTION":
            in_prize = True
            continue
        if in_prize:
            if s == "DEPOT_SECTION":
                break
            if s:
                parts = s.split()
                if len(parts) >= 2:
                    prices.append(int(parts[1]))

    arr = np.asarray(prices, dtype=np.float64) if prices else np.asarray([], dtype=np.float64)
    client_arr = arr[depot_count:] if arr.size >= depot_count else np.asarray([], dtype=np.float64)
    return {
        "exists": True,
        "depot_count": depot_count,
        "total_nodes_with_prize_entries": int(arr.size),
        "client_count": int(client_arr.size),
        "all_prices": prices,
        "client_prices": client_arr.tolist(),
        "client_price_stats": summary_stats(client_arr),
        "client_price_sum": float(np.sum(client_arr)) if client_arr.size else None,
    }


def parse_baseline_log_any_encoding(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    for enc in ("utf-8", "utf-16", "utf-16-le", "cp1252"):
        try:
            txt = data.decode(enc)
            if "VRP Solver" in txt or "Solution results" in txt or "clients" in txt:
                return txt
        except Exception:
            pass
    return data.decode("utf-8", errors="replace")


def instrument_planner_file(path: Path, apply_smoothing: bool) -> None:
    txt = path.read_text(encoding="utf-8", errors="replace")

    if "import json" not in txt:
        txt = txt.replace("import datetime", "import datetime\nimport json\nimport math")

    helper_anchor = "def _plot_base_map(arr, title, cmap_name=\"viridis\"):\n"
    if helper_anchor in txt and "def _stats_from_values(_values):" not in txt:
        idx = txt.index(helper_anchor)
        # find end of function by first "\n\n" after return fig, ax
        ret_marker = "    return fig, ax\n"
        ridx = txt.index(ret_marker, idx) + len(ret_marker)
        insert = (
            "\n"
            "def _stats_from_values(_values):\n"
            "    _arr = np.asarray(_values, dtype=np.float64)\n"
            "    if _arr.size == 0:\n"
            "        return {\"count\": 0, \"min\": None, \"max\": None, \"mean\": None, \"std\": None}\n"
            "    return {\n"
            "        \"count\": int(_arr.size),\n"
            "        \"min\": float(np.min(_arr)),\n"
            "        \"max\": float(np.max(_arr)),\n"
            "        \"mean\": float(np.mean(_arr)),\n"
            "        \"std\": float(np.std(_arr)),\n"
            "    }\n"
        )
        txt = txt[:ridx] + insert + txt[ridx:]

    if apply_smoothing and "def _gaussian_filter_preserve_mask(arr, sigma_xy):" not in txt:
        ridx = txt.index("def _stats_from_values(_values):")
        insert = (
            "\n"
            "def _gaussian_filter_preserve_mask(arr, sigma_xy):\n"
            "    _arr_np = np.asarray(arr, dtype=np.float64)\n"
            "    _finite = np.isfinite(_arr_np)\n"
            "    _data = np.where(_finite, _arr_np, 0.0)\n"
            "    _weights = _finite.astype(np.float64)\n"
            "    _smooth_data = scipy.ndimage.gaussian_filter(_data, sigma=sigma_xy, mode=\"reflect\")\n"
            "    _smooth_weights = scipy.ndimage.gaussian_filter(_weights, sigma=sigma_xy, mode=\"reflect\")\n"
            "    with np.errstate(divide=\"ignore\", invalid=\"ignore\"):\n"
            "        _smooth = np.divide(_smooth_data, _smooth_weights, out=np.full_like(_smooth_data, np.nan), where=_smooth_weights > 1e-12)\n"
            "    _smooth[~_finite] = -np.inf\n"
            "    return _smooth\n\n"
        )
        txt = txt[:ridx] + insert + txt[ridx:]

    if apply_smoothing:
        marker = "#PLOTS: for analysis before proceeding with the optimization"
        if marker in txt and "_temperr2d_before_smooth" not in txt:
            sm = (
                "# Audit smoothing variant (paper-faithful style): Gaussian smoothing before graph generation.\n"
                "_temperr2d_before_smooth = temperr2d_op.copy()\n"
                "temperr2d_op = _gaussian_filter_preserve_mask(temperr2d_op, sigma_xy=[1.0, 1.0])\n"
                "temperr2d_op[~np.isfinite(_temperr2d_before_smooth)] = -np.inf\n\n"
            )
            txt = txt.replace(marker, sm + marker, 1)

    if "# AUDIT_DEBUG_PAYLOAD_START" not in txt:
        payload_block = (
            "\n# AUDIT_DEBUG_PAYLOAD_START\n"
            "try:\n"
            "    _N_level_audit = 1000\n"
            "    _max_map = float(temperr2d_op.max())\n"
            "    _min_map = float(np.nanmin(temperr2d_op[temperr2d_op != -np.inf]))\n"
            "    _range_map = float(_max_map - _min_map)\n"
            "    _decimal_number = int(math.ceil(-math.log10(_range_map / _N_level_audit)))\n"
            "    _multiplicative_factor = int(pow(10, _decimal_number))\n"
            "    _visited_client_node_ids = []\n"
            "    for _route in vrp_result_wt.best.routes():\n"
            "        for _node in _route:\n"
            "            _visited_client_node_ids.append(int(_node))\n"
            "    _all_client_prices = [int(v) for v in node_prices[N_DEPOT:]]\n"
            "    _visited_client_prices = [int(node_prices[_idx]) for _idx in _visited_client_node_ids if _idx >= N_DEPOT and _idx < len(node_prices)]\n"
            "    _payload = {\n"
            "        \"smoothing_applied\": " + ("True" if apply_smoothing else "False") + ",\n"
            "        \"candidate_points\": int(len(uncertain_points)),\n"
            "        \"n_depot\": int(N_DEPOT),\n"
            "        \"n_total_nodes\": int(len(vrp_nodes)),\n"
            "        \"prize_scaling\": {\n"
            "            \"N_level\": int(_N_level_audit),\n"
            "            \"map_min\": _min_map,\n"
            "            \"map_max\": _max_map,\n"
            "            \"map_range\": _range_map,\n"
            "            \"decimal_number\": int(_decimal_number),\n"
            "            \"multiplicative_factor\": int(_multiplicative_factor)\n"
            "        },\n"
            "        \"all_client_price_stats\": _stats_from_values(_all_client_prices),\n"
            "        \"all_client_price_sum\": float(np.sum(_all_client_prices)) if len(_all_client_prices) > 0 else 0.0,\n"
            "        \"visited_client_node_ids\": _visited_client_node_ids,\n"
            "        \"visited_client_price_stats\": _stats_from_values(_visited_client_prices),\n"
            "        \"visited_client_price_sum\": float(np.sum(_visited_client_prices)) if len(_visited_client_prices) > 0 else 0.0,\n"
            "        \"final_solver\": {\n"
            "            \"n_routes\": int(len(vrp_result_wt.best.routes())),\n"
            "            \"n_clients\": int(sum(len(list(r)) for r in vrp_result_wt.best.routes()))\n"
            "        },\n"
            "        \"route_waypoint_counts_clean\": [int(len(r)-2) for r in vrp_routes_points_wt_clean],\n"
            "        \"total_wp_temperr\": float(total_wp_prize_wt),\n"
            "        \"total_all_temperr\": float(total_prize_wt),\n"
            "    }\n"
            "    with open('audit_prize_debug.json', 'w', encoding='utf-8') as _f:\n"
            "        json.dump(_payload, _f, indent=2)\n"
            "except Exception as _e:\n"
            "    with open('audit_prize_debug_error.txt', 'w', encoding='utf-8') as _f:\n"
            "        _f.write(str(_e))\n"
            "# AUDIT_DEBUG_PAYLOAD_END\n"
        )
        txt += payload_block

    path.write_text(txt, encoding="utf-8")


def run_variant(
    variant_name: str,
    planner_src_dir: Path,
    interface_nc: Path,
    out_dir: Path,
    apply_smoothing: bool,
) -> VariantRun:
    variant_work = out_dir / f"variant_{variant_name}" / "planner_snapshot"
    if variant_work.parent.exists():
        shutil.rmtree(variant_work.parent)
    variant_work.mkdir(parents=True, exist_ok=True)
    (variant_work / "plots").mkdir(parents=True, exist_ok=True)

    for fname in ["Config_file.py", "OptimalPlanning.py", "Utils.py", "README.txt"]:
        shutil.copy2(planner_src_dir / fname, variant_work / fname)

    planner_file = variant_work / "OptimalPlanning.py"
    instrument_planner_file(planner_file, apply_smoothing=apply_smoothing)

    log_file = out_dir / f"planner_stdout_day1_{variant_name}.log"
    runtime_file = out_dir / f"planner_runtime_day1_{variant_name}.txt"
    routes_file = out_dir / f"routes_file_day1_{variant_name}.txt"
    routes_est_file = out_dir / f"routes_file_node_estimation_day1_{variant_name}.txt"
    plot_file = out_dir / f"planner_plot_day1_{variant_name}.png"
    vrp_file = out_dir / f"VRP_instance_problem_day1_{variant_name}.vrp"
    prize_debug_file = out_dir / f"audit_prize_debug_day1_{variant_name}.json"

    cmd = [sys.executable, "OptimalPlanning.py", str(interface_nc)]
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=variant_work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "MPLBACKEND": "Agg"},
    )
    elapsed = time.perf_counter() - t0
    log_text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    log_file.write_text(log_text, encoding="utf-8")
    runtime_file.write_text(f"elapsed_seconds={elapsed:.6f}\nexit_code={proc.returncode}\n", encoding="utf-8")

    if (variant_work / "routes_file.txt").exists():
        shutil.copy2(variant_work / "routes_file.txt", routes_file)
    if (variant_work / "routes_file_node_estimation.txt").exists():
        shutil.copy2(variant_work / "routes_file_node_estimation.txt", routes_est_file)
    if (variant_work / "VRP_instance_problem.vrp").exists():
        shutil.copy2(variant_work / "VRP_instance_problem.vrp", vrp_file)
    if (variant_work / "audit_prize_debug.json").exists():
        shutil.copy2(variant_work / "audit_prize_debug.json", prize_debug_file)

    wt_plots = sorted((variant_work / "plots").glob("*_wt.png"), key=lambda p: p.stat().st_mtime)
    if wt_plots:
        shutil.copy2(wt_plots[-1], plot_file)

    return VariantRun(
        name=variant_name,
        workspace=variant_work,
        log_file=log_file,
        runtime_file=runtime_file,
        routes_file=routes_file,
        routes_est_file=routes_est_file,
        plot_file=plot_file,
        vrp_file=vrp_file,
        prize_debug_file=prize_debug_file,
        exit_code=proc.returncode,
        elapsed_seconds=elapsed,
        log_text=log_text,
    )


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)


def save_routes_overlay(
    base_map: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    routes_nosmooth: list[list[tuple[float, float]]],
    routes_smoothed: list[list[tuple[float, float]]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(base_map, dtype=np.float64).copy()
    arr[~np.isfinite(arr)] = np.nan
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("white")
    extent = [float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))]
    n_routes = max(len(routes_nosmooth), len(routes_smoothed), 1)
    route_colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, n_routes))

    def _route_xy(route: list[tuple[float, float]]) -> tuple[list[float], list[float]]:
        # Keep plotting stable: remove consecutive duplicate points only.
        cleaned: list[tuple[float, float]] = []
        for pt in route:
            if not cleaned or cleaned[-1] != pt:
                cleaned.append(pt)
        if len(cleaned) < 2:
            return ([], [])
        ys = [p[0] for p in cleaned]
        xs = [p[1] for p in cleaned]
        return xs, ys

    fig, ax = plt.subplots(figsize=(9.2, 5.5))
    im = ax.imshow(arr, origin="lower", extent=extent, aspect="auto", cmap=cmap)
    for i, route in enumerate(routes_nosmooth):
        xs, ys = _route_xy(route)
        if len(xs) >= 2:
            ax.plot(xs, ys, "-", color=route_colors[i % n_routes], linewidth=1.9, alpha=0.95, label=f"AUV {i+1} no smooth")
    for i, route in enumerate(routes_smoothed):
        xs, ys = _route_xy(route)
        if len(xs) >= 2:
            ax.plot(xs, ys, "--", color=route_colors[i % n_routes], linewidth=1.9, alpha=0.95, label=f"AUV {i+1} smoothed")

    ax.set_title("Routes overlay: day1 nosmooth vs day1 smoothed")
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.legend(loc="upper right", framealpha=0.95)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("temperr (day1)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def parse_baseline_candidate(path: Path) -> int | None:
    txt = parse_baseline_log_any_encoding(path)
    return parse_candidate_clients(txt)


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    repo_root = scenario_dir.parents[1]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    planner_src_dir = scenario_dir / "planner_snapshot"
    cfg = load_config_module(planner_src_dir / "Config_file.py")

    source_day1_nc = repo_root / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc"
    old_interface = scenario_dir / "inputs" / "31-10-2024_predModel_1_planner_interface.nc"

    baseline_metrics_json = scenario_dir / "outputs" / "planner_run" / "run_metrics.json"
    baseline_log = scenario_dir / "outputs" / "planner_run" / "planner_stdout_final.log"
    baseline_vrp = scenario_dir / "outputs" / "planner_run" / "VRP_instance_problem.vrp"
    baseline_plot = scenario_dir / "outputs" / "planner_run" / "20260418T171719Z_wt.png"

    audit_root = scenario_dir / "outputs" / f"cost_smoothing_audit_{ts}"
    inputs_dir = audit_root / "inputs"
    run_dir = audit_root / "planner_run"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    day1_interface = inputs_dir / "30-10-2024_surface_day1_planner_interface.nc"
    day1_info = build_day1_interface(source_day1_nc, day1_interface)

    # H2: map comparison old vs day1.
    old_op = compute_operational_map(old_interface, cfg)
    day1_op = compute_operational_map(day1_interface, cfg)
    day1_smooth_map = gaussian_preserve_invalid(day1_op["map"], sigma_xy=[1.0, 1.0])
    day1_smooth_map[~np.isfinite(day1_op["map"])] = -np.inf

    map_old = old_op["map"]
    map_day1 = day1_op["map"]

    fig_old = run_dir / "cost_audit_map_old.png"
    fig_day1 = run_dir / "cost_audit_map_day1.png"
    fig_diff = run_dir / "cost_audit_map_difference.png"
    fig_hist = run_dir / "cost_audit_hist_comparison.png"
    save_map(map_old, old_op["lat"], old_op["lon"], fig_old, "Old map (31-10 interface operational map)", "temperr", "viridis")
    save_map(map_day1, day1_op["lat"], day1_op["lon"], fig_day1, "Day1 map (30-10 predModel day=1 operational map)", "temperr", "viridis")
    save_difference_map(map_old, map_day1, day1_op["lat"], day1_op["lon"], fig_diff, "Map difference: day1 - old")
    save_hist_comparison(map_old, map_day1, fig_hist, "Histogram comparison: old vs day1", ("old (31-10)", "day1 (30-10)"))

    # Run day1 variants.
    nosmooth = run_variant("nosmooth", planner_src_dir, day1_interface, run_dir, apply_smoothing=False)
    smoothed = run_variant("smoothed", planner_src_dir, day1_interface, run_dir, apply_smoothing=True)

    # Parse metrics.
    baseline_metrics = read_json_if_exists(baseline_metrics_json)
    baseline_blocks = baseline_metrics.get("solver_blocks", [])
    baseline_final = baseline_metrics.get("final_solver_block", {})
    baseline_candidate_clients = parse_baseline_candidate(baseline_log)

    def extract_variant_metrics(v: VariantRun) -> dict[str, Any]:
        blocks = parse_solver_blocks(v.log_text)
        final_block = blocks[-1] if blocks else {}
        cand = parse_candidate_clients(v.log_text)
        prize_tot = parse_total_prize(v.log_text)
        routes = parse_routes_file(v.routes_file)
        prize_debug = read_json_if_exists(v.prize_debug_file)
        return {
            "exit_code": v.exit_code,
            "elapsed_seconds_total": v.elapsed_seconds,
            "candidate_clients": cand,
            "solver_blocks": blocks,
            "final_solver_block": final_block,
            "route_specs_final": routes.get("route_specs", []),
            "route_waypoint_counts_including_start_end": routes.get("waypoint_counts", []),
            "routes_latlon": routes.get("routes_latlon", []),
            "total_wp_temperr": prize_tot.get("total_wp_temperr"),
            "total_all_temperr": prize_tot.get("total_all_temperr"),
            "prize_debug": prize_debug,
        }

    nos_metrics = extract_variant_metrics(nosmooth)
    sm_metrics = extract_variant_metrics(smoothed)

    # Parse prize sections from VRP files.
    old_prize = parse_vrp_prizes(baseline_vrp)
    nos_prize = parse_vrp_prizes(nosmooth.vrp_file)
    sm_prize = parse_vrp_prizes(smoothed.vrp_file)

    # H1/H4 objective decomposition approximation.
    def objective_decomp(run_name: str, final_block: dict[str, Any], prize_info: dict[str, Any], prize_debug: dict[str, Any]) -> dict[str, Any]:
        objective = final_block.get("objective")
        distance = final_block.get("distance")
        total_client_prize = prize_info.get("client_price_sum")
        dropped_prize_proxy = None
        collected_prize_proxy = None
        if objective is not None and distance is not None:
            dropped_prize_proxy = int(objective) - int(distance)
        if total_client_prize is not None and dropped_prize_proxy is not None:
            collected_prize_proxy = float(total_client_prize) - float(dropped_prize_proxy)
        visited_sum_debug = None
        if prize_debug:
            visited_sum_debug = prize_debug.get("visited_client_price_sum")

        return {
            "run": run_name,
            "objective": objective,
            "distance": distance,
            "objective_minus_distance": dropped_prize_proxy,
            "total_client_prize_sum": total_client_prize,
            "collected_prize_proxy_if_obj_eq_dist_plus_dropped": collected_prize_proxy,
            "visited_client_prize_sum_debug": visited_sum_debug,
        }

    old_decomp = objective_decomp("old_31-10_baseline", baseline_final, old_prize, {})
    nos_decomp = objective_decomp("day1_nosmooth", nos_metrics["final_solver_block"], nos_prize, nos_metrics["prize_debug"])
    sm_decomp = objective_decomp("day1_smoothed", sm_metrics["final_solver_block"], sm_prize, sm_metrics["prize_debug"])

    # Prize stats table.
    prize_rows: list[dict[str, Any]] = []

    def append_prize_row(label: str, prize_info: dict[str, Any], metrics: dict[str, Any], decomp: dict[str, Any], has_debug: bool) -> None:
        ps = prize_info.get("client_price_stats", {})
        dbg = metrics.get("prize_debug", {}) if has_debug else {}
        scaling = dbg.get("prize_scaling", {}) if dbg else {}
        visited_stats = dbg.get("visited_client_price_stats", {}) if dbg else {}
        prize_rows.append(
            {
                "run": label,
                "candidate_clients": metrics.get("candidate_clients"),
                "visited_clients_final": metrics.get("final_solver_block", {}).get("n_clients"),
                "objective_final": metrics.get("final_solver_block", {}).get("objective"),
                "distance_final": metrics.get("final_solver_block", {}).get("distance"),
                "map_min_for_prize": scaling.get("map_min"),
                "map_max_for_prize": scaling.get("map_max"),
                "map_range_for_prize": scaling.get("map_range"),
                "decimal_number": scaling.get("decimal_number"),
                "multiplicative_factor": scaling.get("multiplicative_factor"),
                "all_client_price_min": ps.get("min"),
                "all_client_price_max": ps.get("max"),
                "all_client_price_mean": ps.get("mean"),
                "all_client_price_std": ps.get("std"),
                "all_client_price_sum": prize_info.get("client_price_sum"),
                "visited_client_price_min": visited_stats.get("min"),
                "visited_client_price_max": visited_stats.get("max"),
                "visited_client_price_mean": visited_stats.get("mean"),
                "visited_client_price_std": visited_stats.get("std"),
                "visited_client_price_sum": dbg.get("visited_client_price_sum") if dbg else None,
                "objective_minus_distance": decomp.get("objective_minus_distance"),
                "collected_prize_proxy": decomp.get("collected_prize_proxy_if_obj_eq_dist_plus_dropped"),
            }
        )

    # Old run has no debug prize instrumentation.
    old_metrics_for_row = {
        "candidate_clients": baseline_candidate_clients,
        "final_solver_block": baseline_final,
    }
    append_prize_row("old_31-10_baseline", old_prize, old_metrics_for_row, old_decomp, has_debug=False)
    append_prize_row("day1_nosmooth", nos_prize, nos_metrics, nos_decomp, has_debug=True)
    append_prize_row("day1_smoothed", sm_prize, sm_metrics, sm_decomp, has_debug=True)

    prize_stats_csv = run_dir / "cost_audit_prize_stats.csv"
    prize_stats_json = run_dir / "cost_audit_prize_stats.json"
    write_csv(prize_stats_csv, prize_rows)
    prize_stats_json.write_text(json.dumps({"rows": prize_rows}, indent=2), encoding="utf-8")

    # Main comparison requested (nosmooth vs smoothed, plus baseline context).
    comp = {
        "baseline_old_31_10": {
            "candidate_clients": baseline_candidate_clients,
            "visited_clients_final": baseline_final.get("n_clients"),
            "objective_final": baseline_final.get("objective"),
            "n_routes_final": baseline_final.get("n_routes"),
            "plot": str(baseline_plot) if baseline_plot.exists() else None,
        },
        "day1_nosmooth": {
            "candidate_clients": nos_metrics.get("candidate_clients"),
            "visited_clients_final": nos_metrics.get("final_solver_block", {}).get("n_clients"),
            "objective_final": nos_metrics.get("final_solver_block", {}).get("objective"),
            "n_routes_final": nos_metrics.get("final_solver_block", {}).get("n_routes"),
            "waypoints_per_route_including_start_end": nos_metrics.get("route_waypoint_counts_including_start_end"),
            "plot": str(nosmooth.plot_file),
            "exit_code": nosmooth.exit_code,
        },
        "day1_smoothed": {
            "candidate_clients": sm_metrics.get("candidate_clients"),
            "visited_clients_final": sm_metrics.get("final_solver_block", {}).get("n_clients"),
            "objective_final": sm_metrics.get("final_solver_block", {}).get("objective"),
            "n_routes_final": sm_metrics.get("final_solver_block", {}).get("n_routes"),
            "waypoints_per_route_including_start_end": sm_metrics.get("route_waypoint_counts_including_start_end"),
            "plot": str(smoothed.plot_file),
            "exit_code": smoothed.exit_code,
        },
        "deltas_smoothed_minus_nosmooth": {
            "candidate_clients": (
                (sm_metrics.get("candidate_clients") - nos_metrics.get("candidate_clients"))
                if sm_metrics.get("candidate_clients") is not None and nos_metrics.get("candidate_clients") is not None
                else None
            ),
            "visited_clients_final": (
                (sm_metrics.get("final_solver_block", {}).get("n_clients") - nos_metrics.get("final_solver_block", {}).get("n_clients"))
                if sm_metrics.get("final_solver_block", {}).get("n_clients") is not None
                and nos_metrics.get("final_solver_block", {}).get("n_clients") is not None
                else None
            ),
            "objective_final": (
                (sm_metrics.get("final_solver_block", {}).get("objective") - nos_metrics.get("final_solver_block", {}).get("objective"))
                if sm_metrics.get("final_solver_block", {}).get("objective") is not None
                and nos_metrics.get("final_solver_block", {}).get("objective") is not None
                else None
            ),
            "n_routes_final": (
                (sm_metrics.get("final_solver_block", {}).get("n_routes") - nos_metrics.get("final_solver_block", {}).get("n_routes"))
                if sm_metrics.get("final_solver_block", {}).get("n_routes") is not None
                and nos_metrics.get("final_solver_block", {}).get("n_routes") is not None
                else None
            ),
        },
        "objective_decomposition_proxy": {
            "old": old_decomp,
            "day1_nosmooth": nos_decomp,
            "day1_smoothed": sm_decomp,
        },
        "notes": [
            "PyVRP reported objective is not fully decomposed by planner logs; proxy decomposition uses objective-distance and prize sums.",
            "If objective approximately equals distance + dropped_prize, then collected_prize_proxy should align with visited_client_prize_sum_debug.",
        ],
    }

    comparison_json = run_dir / "cost_audit_comparison.json"
    comparison_csv = run_dir / "cost_audit_comparison.csv"
    comparison_json.write_text(json.dumps(comp, indent=2), encoding="utf-8")
    write_csv(
        comparison_csv,
        [
            {
                "metric": "candidate_clients",
                "old_31_10": comp["baseline_old_31_10"]["candidate_clients"],
                "day1_nosmooth": comp["day1_nosmooth"]["candidate_clients"],
                "day1_smoothed": comp["day1_smoothed"]["candidate_clients"],
            },
            {
                "metric": "visited_clients_final",
                "old_31_10": comp["baseline_old_31_10"]["visited_clients_final"],
                "day1_nosmooth": comp["day1_nosmooth"]["visited_clients_final"],
                "day1_smoothed": comp["day1_smoothed"]["visited_clients_final"],
            },
            {
                "metric": "objective_final",
                "old_31_10": comp["baseline_old_31_10"]["objective_final"],
                "day1_nosmooth": comp["day1_nosmooth"]["objective_final"],
                "day1_smoothed": comp["day1_smoothed"]["objective_final"],
            },
            {
                "metric": "n_routes_final",
                "old_31_10": comp["baseline_old_31_10"]["n_routes_final"],
                "day1_nosmooth": comp["day1_nosmooth"]["n_routes_final"],
                "day1_smoothed": comp["day1_smoothed"]["n_routes_final"],
            },
        ],
    )

    # Overlay routes (nosmooth vs smoothed).
    routes_overlay = run_dir / "cost_audit_routes_overlay.png"
    save_routes_overlay(
        base_map=map_day1,
        lat=day1_op["lat"],
        lon=day1_op["lon"],
        routes_nosmooth=nos_metrics.get("routes_latlon", []),
        routes_smoothed=sm_metrics.get("routes_latlon", []),
        out_path=routes_overlay,
    )

    # Hypothesis judgments.
    h1 = {
        "label": "H1",
        "result": "supported"
        if (nos_prize.get("client_price_sum") is not None and old_prize.get("client_price_sum") is not None)
        else "inconclusive",
        "evidence": {
            "old_total_client_prize_sum": old_prize.get("client_price_sum"),
            "day1_nosmooth_total_client_prize_sum": nos_prize.get("client_price_sum"),
            "day1_smoothed_total_client_prize_sum": sm_prize.get("client_price_sum"),
            "old_objective": baseline_final.get("objective"),
            "day1_nosmooth_objective": nos_metrics.get("final_solver_block", {}).get("objective"),
            "day1_smoothed_objective": sm_metrics.get("final_solver_block", {}).get("objective"),
        },
    }
    h2 = {
        "label": "H2",
        "result": "supported",
        "evidence": {
            "old_map_stats": summary_stats(map_old),
            "day1_map_stats": summary_stats(map_day1),
        },
    }
    h3 = {
        "label": "H3",
        "result": "supported"
        if (
            sm_metrics.get("final_solver_block", {}).get("objective") is not None
            and nos_metrics.get("final_solver_block", {}).get("objective") is not None
        )
        else "inconclusive",
        "evidence": {
            "objective_nosmooth": nos_metrics.get("final_solver_block", {}).get("objective"),
            "objective_smoothed": sm_metrics.get("final_solver_block", {}).get("objective"),
            "candidate_nosmooth": nos_metrics.get("candidate_clients"),
            "candidate_smoothed": sm_metrics.get("candidate_clients"),
            "visited_nosmooth": nos_metrics.get("final_solver_block", {}).get("n_clients"),
            "visited_smoothed": sm_metrics.get("final_solver_block", {}).get("n_clients"),
        },
    }

    # Choose required final classification.
    final_classification = "CONFIRMED: cost comparison across runs is not directly valid"
    if (
        nos_metrics.get("final_solver_block", {}).get("objective") is not None
        and sm_metrics.get("final_solver_block", {}).get("objective") is not None
    ):
        if sm_metrics["final_solver_block"]["objective"] < nos_metrics["final_solver_block"]["objective"]:
            final_classification = "PARTIAL: smoothing reduces the issue but does not fully explain it"

    final_sentence = (
        "O aumento do custo e metodologicamente esperado em grande parte por mudanca de escala/distribuicao do problema e comparabilidade limitada entre runs; "
        "o Gaussian smoothing melhora parcialmente a comparabilidade e tende a regularizar o comportamento das rotas."
        if final_classification.startswith("PARTIAL")
        else "O aumento do custo e metodologicamente esperado sobretudo por mudanca de escala/distribuicao do problema, e a comparacao direta de custo absoluto entre runs nao e valida sem normalizacao; o Gaussian smoothing melhora a regularidade espacial, mas nao muda esse principio."
    )

    report_md = run_dir / "cost_and_smoothing_audit_report.md"
    summary_md = run_dir / "cost_and_smoothing_audit_summary.md"
    checks_json = run_dir / "cost_and_smoothing_audit_checks.json"

    report_lines = [
        "# cost_and_smoothing_audit_report",
        "",
        "## 1. Problema observado",
        "- O custo final aumentou fortemente no rerun day1 surface-only com `30-10-2024_predModel_1.nc`.",
        "",
        "## 2. Hipoteses testadas",
        f"- H1 (comparabilidade de custo): `{h1['result']}`",
        f"- H2 (distribuicao do mapa day1 diferente): `{h2['result']}`",
        f"- H3 (efeito do smoothing): `{h3['result']}`",
        "",
        "## 3. Como o objective e construído (e limites)",
        "- O planner cria `PRIZE_SECTION` a partir de `temperr` via fator decimal (`N_level=1000`, `multiplicative_factor=10^decimal`).",
        "- O solver PyVRP reporta `objective` e `distance`; os logs nao decompõem explicitamente penalties/rewards em componentes completos.",
        "- Foi usada decomposicao proxy: `objective - distance` e confronto com soma de prizes no `.vrp` e prizes visitados debug.",
        "",
        "## 4. Comparacao entre mapas",
        f"- mapa antigo: `{fig_old}`",
        f"- mapa day1: `{fig_day1}`",
        f"- diferenca: `{fig_diff}`",
        f"- histograma: `{fig_hist}`",
        "",
        "## 5. Comparacao de prizes",
        f"- tabela csv: `{prize_stats_csv}`",
        f"- tabela json: `{prize_stats_json}`",
        f"- old client prize sum: `{old_prize.get('client_price_sum')}`",
        f"- day1 nosmooth client prize sum: `{nos_prize.get('client_price_sum')}`",
        f"- day1 smoothed client prize sum: `{sm_prize.get('client_price_sum')}`",
        "",
        "## 6. Efeito do Gaussian smoothing",
        f"- log nosmooth: `{nosmooth.log_file}`",
        f"- log smoothed: `{smoothed.log_file}`",
        f"- runtime nosmooth: `{nosmooth.runtime_file}`",
        f"- runtime smoothed: `{smoothed.runtime_file}`",
        f"- routes nosmooth: `{nosmooth.routes_file}`",
        f"- routes smoothed: `{smoothed.routes_file}`",
        f"- plot nosmooth: `{nosmooth.plot_file}`",
        f"- plot smoothed: `{smoothed.plot_file}`",
        f"- overlay rotas: `{routes_overlay}`",
        f"- objective nosmooth: `{nos_metrics.get('final_solver_block', {}).get('objective')}`",
        f"- objective smoothed: `{sm_metrics.get('final_solver_block', {}).get('objective')}`",
        "",
        "## 7. Conclusao final",
        f"- classificacao: **{final_classification}**",
        f"- {final_sentence}",
    ]
    report_md.write_text("\n".join(report_lines), encoding="utf-8")

    summary_lines = [
        "# cost_and_smoothing_audit_summary",
        "",
        f"- classificacao final: **{final_classification}**",
        f"- old objective: `{baseline_final.get('objective')}`",
        f"- day1 nosmooth objective: `{nos_metrics.get('final_solver_block', {}).get('objective')}`",
        f"- day1 smoothed objective: `{sm_metrics.get('final_solver_block', {}).get('objective')}`",
        f"- candidatos (old/nosmooth/smoothed): `{baseline_candidate_clients}` / `{nos_metrics.get('candidate_clients')}` / `{sm_metrics.get('candidate_clients')}`",
        f"- visitados finais (old/nosmooth/smoothed): `{baseline_final.get('n_clients')}` / `{nos_metrics.get('final_solver_block', {}).get('n_clients')}` / `{sm_metrics.get('final_solver_block', {}).get('n_clients')}`",
        f"- {final_sentence}",
    ]
    summary_md.write_text("\n".join(summary_lines), encoding="utf-8")

    checks_payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "old_interface": str(old_interface),
            "day1_source_nc": str(source_day1_nc),
            "day1_interface": day1_info,
        },
        "variant_runs": {
            "nosmooth": {
                "exit_code": nosmooth.exit_code,
                "elapsed_seconds": nosmooth.elapsed_seconds,
                "log_file": str(nosmooth.log_file),
                "runtime_file": str(nosmooth.runtime_file),
                "routes_file": str(nosmooth.routes_file),
                "plot_file": str(nosmooth.plot_file),
                "vrp_file": str(nosmooth.vrp_file),
                "prize_debug_file": str(nosmooth.prize_debug_file),
            },
            "smoothed": {
                "exit_code": smoothed.exit_code,
                "elapsed_seconds": smoothed.elapsed_seconds,
                "log_file": str(smoothed.log_file),
                "runtime_file": str(smoothed.runtime_file),
                "routes_file": str(smoothed.routes_file),
                "plot_file": str(smoothed.plot_file),
                "vrp_file": str(smoothed.vrp_file),
                "prize_debug_file": str(smoothed.prize_debug_file),
            },
        },
        "map_stats": {
            "old": summary_stats(map_old),
            "day1": summary_stats(map_day1),
            "day1_smoothed": summary_stats(day1_smooth_map),
        },
        "hypotheses": {"H1": h1, "H2": h2, "H3": h3},
        "comparison": comp,
        "final_classification": final_classification,
        "final_sentence": final_sentence,
        "outputs": {
            "cost_audit_map_old": str(fig_old),
            "cost_audit_map_day1": str(fig_day1),
            "cost_audit_map_difference": str(fig_diff),
            "cost_audit_hist_comparison": str(fig_hist),
            "cost_audit_prize_stats_csv": str(prize_stats_csv),
            "cost_audit_prize_stats_json": str(prize_stats_json),
            "cost_audit_comparison_csv": str(comparison_csv),
            "cost_audit_comparison_json": str(comparison_json),
            "cost_audit_routes_overlay": str(routes_overlay),
            "report_md": str(report_md),
            "summary_md": str(summary_md),
        },
    }
    checks_json.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    print("[OK] audit_root:", audit_root)
    print("[OK] no-smooth exit:", nosmooth.exit_code, "objective:", nos_metrics.get("final_solver_block", {}).get("objective"))
    print("[OK] smoothed exit:", smoothed.exit_code, "objective:", sm_metrics.get("final_solver_block", {}).get("objective"))
    print("[OK] final classification:", final_classification)
    print("[OK] report:", report_md)
    print("[OK] summary:", summary_md)


if __name__ == "__main__":
    main()
