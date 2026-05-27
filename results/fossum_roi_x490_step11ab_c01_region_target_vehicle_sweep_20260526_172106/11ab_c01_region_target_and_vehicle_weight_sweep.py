#!/usr/bin/env python
"""Step11AB: C01 region-target single-AUV and vehicle-specific weight sweep.

This step runs only C01_representative / 2024-08-24. It uses Step11Y
prototype-based maps only: day-specific STD and Step08 prototype descriptors
for the predicted class. No TEMPpred-derived masks/descriptors are used.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCRIPTS = ROOT / "scripts"
PLANNER = ROOT / "OptimalPlanning_Lucrezia"
HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
STEP10F = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
DEFAULT_STEP11Y = RESULTS / "fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260525_001754"

CASE_ID = "C01_representative"
CASE_DATE = "2024-08-24"
CASE_DISPLAY = "C01 representative"
ROI_ROW_MIN = 55
ROI_COL_MIN = 47
ROI_SHAPE = (72, 117)


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_map(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return out
    lo = float(np.nanmin(arr[valid]))
    hi = float(np.nanmax(arr[valid]))
    if hi <= lo:
        out[valid] = 0.0
    else:
        out[valid] = np.clip((arr[valid] - lo) / (hi - lo), 0, 1)
    return out


def load_step11y_maps(step11y: Path) -> tuple[int, dict[str, np.ndarray], pd.DataFrame]:
    z = np.load(step11y / "prototype_based_all_planner_maps.npz", allow_pickle=True)
    case_ids = [str(x) for x in z["case_ids"]]
    if CASE_ID not in case_ids:
        raise ValueError(f"{CASE_ID} not found in {step11y}")
    idx = case_ids.index(CASE_ID)
    maps = {k: np.asarray(z[k], dtype=np.float32) for k in z.files if k not in ["case_ids", "dates", "predicted_classes"]}
    cases = pd.DataFrame(
        {
            "case_id": case_ids,
            "date": [str(x) for x in z["dates"]],
            "predicted_class": z["predicted_classes"].astype(int),
        }
    )
    return idx, maps, cases


def load_mask() -> np.ndarray:
    z = np.load(STEP10F / "planner_minimal_boundary_input_maps.npz", allow_pickle=True)
    mask = np.asarray(z["mask"], dtype=bool)
    if mask.ndim == 3:
        case_ids = [str(x) for x in z["case_ids"]]
        idx = case_ids.index(CASE_ID)
        return mask[idx]
    return mask


def descriptor_region_masks(cold: np.ndarray, warm: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    valid = mask & np.isfinite(cold) & np.isfinite(warm)
    region_a = (cold >= 0.5) & (cold >= warm) & valid
    region_b = (warm >= 0.5) & (warm > cold) & valid
    fallbacks = []
    if int(region_a.sum()) < 50:
        vals = cold[valid]
        thr = float(np.nanpercentile(vals, 85)) if vals.size else 1.0
        region_a = (cold >= thr) & (cold >= warm) & valid
        fallbacks.append(f"region_A top15 prototype cold threshold {thr:.3f}")
    if int(region_b.sum()) < 50:
        vals = warm[valid]
        thr = float(np.nanpercentile(vals, 85)) if vals.size else 1.0
        region_b = (warm >= thr) & (warm > cold) & valid
        fallbacks.append(f"region_B top15 prototype warm threshold {thr:.3f}")
    if int(region_a.sum()) < 1:
        vals = cold[valid]
        thr = float(np.nanpercentile(vals, 95)) if vals.size else 1.0
        region_a = (cold >= thr) & valid
        fallbacks.append(f"region_A non-exclusive top5 prototype fallback {thr:.3f}")
    if int(region_b.sum()) < 1:
        vals = warm[valid]
        thr = float(np.nanpercentile(vals, 95)) if vals.size else 1.0
        region_b = (warm >= thr) & valid
        fallbacks.append(f"region_B non-exclusive top5 prototype fallback {thr:.3f}")
    return region_a.astype(bool), region_b.astype(bool), {
        "region_A_cells": int(region_a.sum()),
        "region_B_cells": int(region_b.sum()),
        "fallbacks": fallbacks,
        "TEMPpred_used": False,
    }


def choose_target(std: np.ndarray, region: np.ndarray, mask: np.ndarray, avoid: tuple[int, int] | None = None, min_distance: float = 15.0) -> tuple[int, int, float, str]:
    candidates = region & mask & np.isfinite(std)
    method = "max STD inside prototype region"
    if avoid is not None and np.any(candidates):
        rr, cc = np.where(candidates)
        dist = np.sqrt((rr - avoid[0]) ** 2 + (cc - avoid[1]) ** 2)
        far = dist >= min_distance
        if np.any(far):
            filtered = np.zeros_like(candidates, dtype=bool)
            filtered[rr[far], cc[far]] = True
            candidates = filtered
            method += f"; min distance {min_distance:g} cells enforced"
        else:
            method += f"; min distance {min_distance:g} unavailable"
    if not np.any(candidates):
        candidates = mask & np.isfinite(std)
        method = "fallback max STD inside valid mask"
    score = np.where(candidates, std, -np.inf)
    flat = int(np.nanargmax(score))
    r, c = np.unravel_index(flat, std.shape)
    return int(r), int(c), float(std[r, c]), method


def gaussian_bonus(shape: tuple[int, int], targets: list[tuple[int, int]], sigma: float = 2.0, radius: int = 5) -> np.ndarray:
    yy, xx = np.indices(shape)
    bonus = np.zeros(shape, dtype=np.float32)
    for r, c in targets:
        d2 = (yy - r) ** 2 + (xx - c) ** 2
        blob = np.exp(-0.5 * d2 / (sigma**2))
        blob[d2 > radius**2] = 0
        bonus = np.maximum(bonus, blob.astype(np.float32))
    return bonus


def route_to_roi(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in points]


def plot_map_paths(arr: np.ndarray, paths: dict[str, list[tuple[int, int]]], out: Path, title: str, cmap: str = "viridis", targets: list[tuple[int, int]] | None = None) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=1)
    colors = ["white", "yellow", "cyan", "tab:red", "tab:green", "black"]
    for i, (label, pts_full) in enumerate(paths.items()):
        pts = route_to_roi(pts_full)
        if pts:
            ax.plot([p[1] for p in pts], [p[0] for p in pts], marker="o", markersize=2, linewidth=1.5, color=colors[i % len(colors)], label=label)
    if targets:
        ax.scatter([c for _, c in targets], [r for r, _ in targets], s=110, marker="*", c="red", edgecolor="black", label="targets")
    ax.set_title(title)
    ax.set_xlabel("ROI column")
    ax.set_ylabel("ROI row")
    ax.set_xlim(-1, ROI_SHAPE[1])
    ax.set_ylim(-1, ROI_SHAPE[0])
    ax.legend(fontsize=7, loc="upper right")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def region_rgb(region_a: np.ndarray, region_b: np.ndarray, boundary: np.ndarray | None = None) -> np.ndarray:
    rgb = np.zeros((*region_a.shape, 3), dtype=float)
    rgb[..., 2] = region_a.astype(float) * 0.75
    rgb[..., 0] = region_b.astype(float) * 0.75
    if boundary is not None:
        rgb[..., 1] = boundary.astype(float) * 0.75
    return np.clip(rgb, 0, 1)


def plot_rgb_paths(rgb: np.ndarray, paths: dict[str, list[tuple[int, int]]], out: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.imshow(rgb, origin="lower", aspect="auto")
    colors = ["white", "yellow", "cyan", "black", "lime", "tab:orange", "tab:purple", "tab:green"]
    for i, (label, pts_full) in enumerate(paths.items()):
        pts = route_to_roi(pts_full)
        if pts:
            ax.plot([p[1] for p in pts], [p[0] for p in pts], marker="o", markersize=2, linewidth=1.5, color=colors[i % len(colors)], label=label)
    ax.set_title(title)
    ax.set_xlim(-1, ROI_SHAPE[1])
    ax.set_ylim(-1, ROI_SHAPE[0])
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int = 30) -> str:
    if df.empty:
        return "_No data available._\n"
    view = df[[c for c in columns if c in df.columns]].head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.3f}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join("---" for _ in view.columns) + " |",
    ]
    for row in view.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11AB C01 region target and vehicle-specific sweep.")
    parser.add_argument("--step11y", type=Path, default=DEFAULT_STEP11Y)
    parser.add_argument("--planner", type=Path, default=PLANNER)
    parser.add_argument("--output-root", type=Path, default=RESULTS)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--skip-existing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    zutils = load_module("step11z_utils", SCRIPTS / "11z_rerun_minimal_prototype_based_planner_tests.py")
    s11a = zutils.load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")
    s11c = zutils.load_module("step11c_utils", SCRIPTS / "11c_single_auv_boundary_crossing_reward.py")

    outdir = args.output_root.resolve() / f"fossum_roi_x490_step11ab_c01_region_target_vehicle_sweep_{now_tag()}"
    for sub in ["planner_inputs", "planner_runs", "planner_configs", "figures", "masks"]:
        (outdir / sub).mkdir(parents=True, exist_ok=True)

    idx, maps, cases = load_step11y_maps(args.step11y)
    mask = load_mask()
    std = maps["baseline_STD_norm"][idx]
    boundary = maps["boundary_score_norm"][idx]
    cold = maps["cold_region_norm"][idx]
    warm = maps["warm_region_norm"][idx]
    boundary_alpha050 = maps["enriched_boundary_alpha050"][idx]
    region_a, region_b, region_meta = descriptor_region_masks(cold, warm, mask)
    core = zutils.boundary_core(boundary, mask)
    target_a = choose_target(std, region_a, mask)
    target_b = choose_target(std, region_b, mask, avoid=(target_a[0], target_a[1]), min_distance=15.0)
    target_bonus = gaussian_bonus(ROI_SHAPE, [(target_a[0], target_a[1]), (target_b[0], target_b[1])], sigma=2.0, radius=5)
    cross_region_targets = normalize_map(std + 2.0 * target_bonus, mask)

    configs = {
        "vehicle_specific_conservative": (0.8, 0.2),
        "vehicle_specific_balanced": (0.7, 0.3),
        "vehicle_specific_strong_regime": (0.6, 0.4),
    }
    info_maps: dict[str, np.ndarray] = {
        "baseline_STD": std,
        "prototype_boundary_alpha050": boundary_alpha050,
        "cross_region_targets": cross_region_targets,
        "target_bonus": target_bonus,
        "region_A_mask": region_a.astype(np.float32),
        "region_B_mask": region_b.astype(np.float32),
    }
    for name, (w_std, w_region) in configs.items():
        info_maps[f"{name}_AUV1"] = normalize_map(w_std * std + w_region * cold, mask)
        info_maps[f"{name}_AUV2"] = normalize_map(w_std * std + w_region * warm, mask)
    np.savez_compressed(outdir / "step11ab_information_maps.npz", **info_maps)
    np.save(outdir / "masks" / "C01_region_A_mask.npy", region_a)
    np.save(outdir / "masks" / "C01_region_B_mask.npy", region_b)
    np.save(outdir / "masks" / "C01_boundary_core_mask.npy", core)

    lat_hres = np.load(HRES / "LAT_hres.npy")
    lon_hres = np.load(HRES / "LON_hres.npy")
    bathy_hres = np.load(HRES / "BATHY_hres.npy")
    valid_full = s11a.embed_roi_to_hres(mask.astype(np.float32), mask, fill=np.nan) > 0.5
    maps_full = {
        "STD_full": s11a.embed_roi_to_hres(std, mask, fill=np.nan),
        "boundary_full": s11a.embed_roi_to_hres(boundary, mask, fill=np.nan),
    }
    masks_full = {
        "region_A_full": s11a.embed_roi_to_hres(region_a.astype(np.float32), mask, fill=np.nan) > 0.5,
        "region_B_full": s11a.embed_roi_to_hres(region_b.astype(np.float32), mask, fill=np.nan) > 0.5,
        "boundary_core_full": s11a.embed_roi_to_hres(core.astype(np.float32), mask, fill=np.nan) > 0.5,
    }
    crossing_proxy, proxy_meta = s11c.build_crossing_proxy(boundary, region_a, region_b, core, mask)
    crossing_proxy_full = s11a.embed_roi_to_hres(crossing_proxy, mask, fill=np.nan)

    original_config = s11a.read_config_text(args.planner / "Config_file.py")
    config_1auv = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=12.0, auv_number=1)
    config_2auv = s11a.generated_config(original_config, single_auv=False, mission_duration_hours=12.0, auv_number=2)
    (outdir / "planner_configs" / "Config_file_step11ab_1auv_12h.py").write_text(config_1auv, encoding="utf-8")
    (outdir / "planner_configs" / "Config_file_step11ab_2auv_12h.py").write_text(config_2auv, encoding="utf-8")

    target_rows = [
        {"target": "target_A", "roi_row": target_a[0], "roi_col": target_a[1], "std_value": target_a[2], "selection_method": target_a[3]},
        {"target": "target_B", "roi_row": target_b[0], "roi_col": target_b[1], "std_value": target_b[2], "selection_method": target_b[3]},
    ]
    pd.DataFrame(target_rows).to_csv(outdir / "step11ab_target_points.csv", index=False)

    manifest_rows: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    single_rows: list[dict[str, Any]] = []
    vehicle_rows: list[dict[str, Any]] = []
    multi_rows: list[dict[str, Any]] = []
    route_points_by_run: dict[str, dict[Any, list[tuple[int, int]]]] = {}

    baseline_points: set[tuple[int, int]] | None = None
    single_specs = [
        ("baseline_STD", std, "information_map = STD_norm"),
        ("prototype_boundary_alpha050", boundary_alpha050, "information_map = 0.5*STD_norm + 0.5*prototype_boundary"),
        ("cross_region_targets", cross_region_targets, "information_map = normalize(STD_norm + 2.0*Gaussian(target_A,target_B))"),
    ]
    for run_name, info, formulation in single_specs:
        run_id = f"{CASE_ID}__single_auv_12h__{run_name}"
        diag, routes, run_dir = zutils.run_planner_case(s11a, run_id, info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_1auv, outdir, args.timeout_s, args.skip_existing)
        solver_rows.append(diag)
        points = zutils.route_points(s11a, routes, lat_hres, lon_hres)
        if run_name == "baseline_STD":
            baseline_points = set(zutils.valid_unique(points, valid_full))
        route_points_by_run[f"single__{run_name}"] = {"all": points}
        info_full = s11a.embed_roi_to_hres(info, mask, fill=np.nan)
        path = s11a.path_metrics(routes, lat_hres, lon_hres, info_full, maps_full["STD_full"], maps_full["boundary_full"], baseline_points)
        cross = s11c.crossing_metrics(points, routes, masks_full["region_A_full"], masks_full["region_B_full"], masks_full["boundary_core_full"], crossing_proxy_full, baseline_points)
        length, duration = s11c.trajectory_length_and_duration(routes)
        row = {
            "run_id": run_id,
            "case_id": CASE_ID,
            "display_case": CASE_DISPLAY,
            "date": CASE_DATE,
            "run_name": run_name,
            "mission_duration_requested_h": 12.0,
            "mission_duration": duration,
            "trajectory_length": length,
            "solver_runtime": diag.get("runtime_s", np.nan),
            "solver_status": diag.get("status", ""),
            "formulation": formulation,
            "descriptor_source": "Step11Y prototype_based arrays from Step08 predicted-class descriptors",
            "target_proxy": run_name == "cross_region_targets",
            "crossing_proxy_method": proxy_meta.get("method", ""),
            "collected_STD": path["collected_STD_score"],
            "collected_boundary": path["collected_boundary_score"],
            "crossing_count": cross["boundary_crossing_count"],
            "regions_visited": cross["number_of_distinct_regions_visited"],
            "fraction_path_region_A": cross["fraction_path_region_A"],
            "fraction_path_region_B": cross["fraction_path_region_B"],
            "points_in_region_A": int(round(cross["fraction_path_region_A"] * max(path.get("number_of_valid_cells_sampled", 0), 0))) if np.isfinite(cross["fraction_path_region_A"]) else np.nan,
            "points_in_region_B": int(round(cross["fraction_path_region_B"] * max(path.get("number_of_valid_cells_sampled", 0), 0))) if np.isfinite(cross["fraction_path_region_B"]) else np.nan,
            "fraction_path_boundary_core": cross["fraction_path_boundary_core"],
            "difference_from_baseline": cross["difference_from_baseline"],
        }
        single_rows.append(row)
        manifest_rows.append({**row, "scope": "single_AUV", "run_dir": rel(run_dir), "input_nc": diag.get("input_nc", "")})

    multi_shared = [
        ("baseline_STD", std, "native 2-AUV shared STD"),
        ("prototype_boundary_alpha050", boundary_alpha050, "native 2-AUV shared STD+boundary"),
    ]
    for strategy, info, formulation in multi_shared:
        run_id = f"{CASE_ID}__multi_auv_12h__{strategy}"
        diag, routes, run_dir = zutils.run_planner_case(s11a, run_id, info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_2auv, outdir, args.timeout_s, args.skip_existing)
        solver_rows.append(diag)
        vehicle_points = {}
        vrows = []
        for vid, route in enumerate(routes[:2], start=1):
            pts = zutils.route_points(s11a, [route], lat_hres, lon_hres)
            vehicle_points[vid] = pts
            vrows.append(zutils.vehicle_metrics(run_id, strategy, CASE_ID, vid, pts, route, maps_full, masks_full, valid_full, diag.get("status", "")))
        vdf = pd.DataFrame(vrows)
        vehicle_rows.extend(vrows)
        route_points_by_run[f"multi__{strategy}"] = vehicle_points
        mrow = zutils.fleet_metrics(run_id, strategy, CASE_ID, vehicle_points, vdf, masks_full, valid_full, diag.get("status", ""), float(diag.get("runtime_s", np.nan)))
        mrow["formulation"] = formulation
        multi_rows.append(mrow)
        manifest_rows.append({**mrow, "scope": "multi_AUV_native_shared", "run_dir": rel(run_dir), "input_nc": diag.get("input_nc", "")})

    for strategy, (w_std, w_region) in configs.items():
        vehicle_points = {}
        vrows = []
        runtime_total = 0.0
        statuses = []
        for vid, info in [(1, info_maps[f"{strategy}_AUV1"]), (2, info_maps[f"{strategy}_AUV2"])]:
            run_id = f"{CASE_ID}__multi_auv_12h__{strategy}__AUV{vid}"
            diag, routes, run_dir = zutils.run_planner_case(s11a, run_id, info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_1auv, outdir, args.timeout_s, args.skip_existing)
            solver_rows.append(diag)
            runtime_total += float(diag.get("runtime_s", 0.0) or 0.0)
            statuses.append(str(diag.get("status", "")))
            route = routes[0] if routes else None
            pts = zutils.route_points(s11a, [route], lat_hres, lon_hres) if route else []
            vehicle_points[vid] = pts
            vrows.append(zutils.vehicle_metrics(run_id, strategy, CASE_ID, vid, pts, route, maps_full, masks_full, valid_full, str(diag.get("status", ""))))
        vdf = pd.DataFrame(vrows)
        vehicle_rows.extend(vrows)
        route_points_by_run[f"multi__{strategy}"] = vehicle_points
        status = "SUCCESS" if all(s in ["SUCCESS", "REUSED"] for s in statuses) else "FAILED_OR_PARTIAL"
        mrow = zutils.fleet_metrics(f"{CASE_ID}__multi_auv_12h__{strategy}", strategy, CASE_ID, vehicle_points, vdf, masks_full, valid_full, status, runtime_total)
        mrow["formulation"] = f"proxy pair: AUV1={w_std:.1f}*STD+{w_region:.1f}*region_A; AUV2={w_std:.1f}*STD+{w_region:.1f}*region_B"
        mrow["std_weight"] = w_std
        mrow["region_weight"] = w_region
        multi_rows.append(mrow)
        manifest_rows.append({**mrow, "scope": "multi_AUV_vehicle_specific_proxy", "run_dir": "two 1-AUV proxy runs", "input_nc": ""})

    single_df = pd.DataFrame(single_rows)
    multi_df = pd.DataFrame(multi_rows)
    vehicle_df = pd.DataFrame(vehicle_rows)
    solver_df = pd.DataFrame(solver_rows)
    manifest = pd.DataFrame(manifest_rows)

    manifest.to_csv(outdir / "step11ab_run_manifest.csv", index=False)
    single_df.to_csv(outdir / "step11ab_single_auv_metrics.csv", index=False)
    multi_df.to_csv(outdir / "step11ab_multi_auv_metrics.csv", index=False)
    vehicle_df.to_csv(outdir / "step11ab_vehicle_metrics.csv", index=False)
    solver_df.to_csv(outdir / "step11ab_solver_diagnostics.csv", index=False)

    # Figures.
    figdir = outdir / "figures"
    plot_map_paths(cross_region_targets, {"cross_region_targets": route_points_by_run.get("single__cross_region_targets", {}).get("all", [])}, figdir / "single_auv_c01_target_maps.png", "C01 cross-region target information map", targets=[(target_a[0], target_a[1]), (target_b[0], target_b[1])])
    rgb = region_rgb(region_a, region_b, core)
    single_paths = {k.replace("single__", ""): v.get("all", []) for k, v in route_points_by_run.items() if k.startswith("single__")}
    plot_rgb_paths(rgb, single_paths, figdir / "single_auv_c01_paths_over_regions.png", "C01 single-AUV paths over prototype regions")
    plot_rgb_paths(rgb, {"cross_region_targets": route_points_by_run.get("single__cross_region_targets", {}).get("all", [])}, figdir / "single_auv_c01_path_colored_by_region.png", "C01 target path over prototype regions")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    labels = single_df["run_name"].str.replace("prototype_", "", regex=False).str.replace("_", "\n", regex=False)
    x = np.arange(len(single_df))
    axes[0].bar(x, pd.to_numeric(single_df["regions_visited"], errors="coerce"), color="#4c78a8")
    axes[0].set_title("Regions visited")
    axes[1].bar(x - 0.18, pd.to_numeric(single_df["fraction_path_region_A"], errors="coerce"), 0.36, label="A")
    axes[1].bar(x + 0.18, pd.to_numeric(single_df["fraction_path_region_B"], errors="coerce"), 0.36, label="B")
    axes[1].axhline(0.20, color="red", linestyle="--", linewidth=1)
    axes[1].set_title("Path fractions")
    axes[1].legend()
    baseline_std = float(single_df.loc[single_df["run_name"].eq("baseline_STD"), "collected_STD"].iloc[0])
    axes[2].bar(x, pd.to_numeric(single_df["collected_STD"], errors="coerce") / baseline_std, color="#54a24b")
    axes[2].axhline(0.70, color="red", linestyle="--", linewidth=1)
    axes[2].set_title("STD retained vs baseline")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "single_auv_c01_metrics_comparison.png", dpi=180)
    plt.close(fig)

    multi_paths = {}
    for key, paths in route_points_by_run.items():
        if key.startswith("multi__"):
            for vid, pts in paths.items():
                multi_paths[f"{key.replace('multi__','')}_AUV{vid}"] = pts
    plot_rgb_paths(rgb, multi_paths, figdir / "multi_auv_c01_weight_sweep_paths.png", "C01 multi-AUV weight sweep paths")

    labels_m = multi_df["strategy"].str.replace("prototype_", "", regex=False).str.replace("vehicle_specific_", "vs_", regex=False).str.replace("_", "\n", regex=False)
    x = np.arange(len(multi_df))
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    axes[0].bar(x - 0.18, pd.to_numeric(multi_df["fleet_region_A_coverage"], errors="coerce"), 0.36, label="A")
    axes[0].bar(x + 0.18, pd.to_numeric(multi_df["fleet_region_B_coverage"], errors="coerce"), 0.36, label="B")
    axes[0].set_title("Regime coverage")
    axes[0].legend()
    baseline_multi_std = float(multi_df.loc[multi_df["strategy"].eq("baseline_STD"), "fleet_collected_STD"].iloc[0])
    axes[1].bar(x, pd.to_numeric(multi_df["fleet_collected_STD"], errors="coerce") / baseline_multi_std, color="#54a24b")
    axes[1].axhline(0.85, color="red", linestyle="--", linewidth=1)
    axes[1].set_title("STD retained")
    axes[2].scatter(pd.to_numeric(multi_df["fleet_region_B_coverage"], errors="coerce"), pd.to_numeric(multi_df["fleet_collected_STD"], errors="coerce") / baseline_multi_std, color="#e45756")
    for _, row in multi_df.iterrows():
        axes[2].annotate(str(row["strategy"])[:16], (row["fleet_region_B_coverage"], row["fleet_collected_STD"] / baseline_multi_std), fontsize=7)
    axes[2].set_xlabel("B coverage")
    axes[2].set_ylabel("STD retained")
    axes[2].set_title("Coverage vs STD tradeoff")
    for ax in axes[:2]:
        ax.set_xticks(x)
        ax.set_xticklabels(labels_m, fontsize=7, rotation=80)
        ax.grid(axis="y", alpha=0.25)
    axes[2].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "multi_auv_c01_region_coverage_vs_std_tradeoff.png", dpi=180)
    plt.close(fig)

    spec_rows = []
    for strategy in multi_df["strategy"]:
        v = vehicle_df[vehicle_df["strategy"].eq(strategy)]
        if v.empty:
            continue
        r = {"strategy": strategy}
        for _, row in v.iterrows():
            vid = int(row["vehicle_id"])
            r[f"AUV{vid}_frac_A"] = row["fraction_path_region_A"]
            r[f"AUV{vid}_frac_B"] = row["fraction_path_region_B"]
        spec_rows.append(r)
    spec_df = pd.DataFrame(spec_rows)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    if not spec_df.empty:
        xs = np.arange(len(spec_df))
        width = 0.2
        for offset, col, label in [(-1.5, "AUV1_frac_A", "AUV1 A"), (-0.5, "AUV1_frac_B", "AUV1 B"), (0.5, "AUV2_frac_A", "AUV2 A"), (1.5, "AUV2_frac_B", "AUV2 B")]:
            ax.bar(xs + offset * width, pd.to_numeric(spec_df.get(col), errors="coerce"), width, label=label)
        ax.set_xticks(xs)
        ax.set_xticklabels(spec_df["strategy"].str.replace("prototype_", "", regex=False).str.replace("_", "\n", regex=False), fontsize=7, rotation=75)
        ax.legend(fontsize=8)
    ax.set_title("Vehicle specialization by region fraction")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "multi_auv_c01_vehicle_specialization.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(x, pd.to_numeric(multi_df["trajectory_overlap_ratio"], errors="coerce"), color="#f58518")
    axes[0].set_title("Trajectory overlap ratio")
    axes[1].bar(x, pd.to_numeric(multi_df["inter_vehicle_mean_distance"], errors="coerce"), color="#4c78a8")
    axes[1].set_title("Inter-vehicle mean distance")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels_m, fontsize=7, rotation=80)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figdir / "multi_auv_c01_overlap_distance_comparison.png", dpi=180)
    plt.close(fig)

    failures = solver_df[~solver_df["status"].astype(str).isin(["SUCCESS", "REUSED"])] if not solver_df.empty else pd.DataFrame()
    target_row = single_df[single_df["run_name"].eq("cross_region_targets")]
    target_success = False
    if not target_row.empty:
        tr = target_row.iloc[0]
        target_success = bool(
            float(tr["regions_visited"]) >= 2
            and float(tr["fraction_path_region_B"]) > 0.20
            and float(tr["collected_STD"]) >= 0.70 * baseline_std
            and str(tr["solver_status"]) in ["SUCCESS", "REUSED"]
        )
    baseline_b = float(multi_df.loc[multi_df["strategy"].eq("baseline_STD"), "fleet_region_B_coverage"].iloc[0])
    candidate_multi = multi_df[multi_df["strategy"].str.startswith("vehicle_specific")].copy()
    candidate_multi["std_retained"] = pd.to_numeric(candidate_multi["fleet_collected_STD"], errors="coerce") / baseline_multi_std
    candidate_multi["B_gain"] = pd.to_numeric(candidate_multi["fleet_region_B_coverage"], errors="coerce") / max(baseline_b, 1e-9)
    acceptable = candidate_multi[
        (candidate_multi["B_gain"] >= 2.0)
        & (candidate_multi["std_retained"] >= 0.85)
        & (pd.to_numeric(candidate_multi["trajectory_overlap_ratio"], errors="coerce") <= float(multi_df.loc[multi_df["strategy"].eq("baseline_STD"), "trajectory_overlap_ratio"].iloc[0]) + 0.03)
    ]
    best_multi = acceptable.iloc[0]["strategy"] if not acceptable.empty else (candidate_multi.sort_values(["B_gain", "std_retained"], ascending=False).iloc[0]["strategy"] if not candidate_multi.empty else "")
    verdict = "STEP11AB_COMPLETED_RESULTS_READY"
    warnings = []
    if not failures.empty:
        verdict = "STEP11AB_COMPLETED_WITH_WARNINGS"
        warnings.append(f"{len(failures)} planner runs failed/timed out.")
    if single_df.empty or multi_df.empty:
        verdict = "STEP11AB_FAILED"

    checks = {
        "verdict": verdict,
        "output_dir": rel(outdir),
        "case_id": CASE_ID,
        "date": CASE_DATE,
        "prototype_maps_only": True,
        "TEMPpred_used_for_regions_or_targets": False,
        "region_mask_meta": region_meta,
        "target_success": target_success,
        "recommended_single_auv": "cross_region_targets" if target_success else "planner-level mandatory waypoint/route-level reward needed",
        "recommended_multi_auv": str(best_multi),
        "planner_failures": int(len(failures)),
        "figures_created": len(list(figdir.glob("*.png"))),
        "warnings": warnings,
    }
    write_json(outdir / "step11ab_checks.json", checks)
    write_json(
        outdir / "step11ab_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": rel(Path(__file__)),
            "step11y_source": rel(args.step11y),
            "planner": rel(args.planner),
            "case": {"case_id": CASE_ID, "date": CASE_DATE, "predicted_class": int(cases.loc[cases["case_id"].eq(CASE_ID), "predicted_class"].iloc[0])},
        },
    )

    report = [
        "# Step11AB C01 region-target and vehicle-specific weight sweep",
        "",
        f"- Verdict: `{verdict}`",
        f"- Single-AUV target success: `{target_success}`",
        f"- Recommended single-AUV: `{checks['recommended_single_auv']}`",
        f"- Recommended multi-AUV: `{checks['recommended_multi_auv']}`",
        "",
        "## Targets",
        md_table(pd.DataFrame(target_rows), ["target", "roi_row", "roi_col", "std_value", "selection_method"], 10),
        "",
        "## Single-AUV metrics",
        md_table(single_df, ["run_name", "solver_status", "regions_visited", "crossing_count", "fraction_path_region_A", "fraction_path_region_B", "collected_STD", "trajectory_length", "solver_runtime"], 10),
        "",
        "## Multi-AUV metrics",
        md_table(multi_df, ["strategy", "solver_status", "fleet_region_A_coverage", "fleet_region_B_coverage", "fleet_collected_STD", "trajectory_overlap_ratio", "inter_vehicle_mean_distance", "complementarity_score"], 20),
        "",
        "## Interpretation",
        "",
        "- If cross_region_targets still fails to visit both regimes, the map-level proxy is insufficient and the next step should be planner-level mandatory waypoint or route-level reward.",
        "- For multi-AUV, choose the lightest vehicle-specific weight that improves region_B coverage while retaining at least 85% of baseline STD.",
    ]
    if warnings:
        report += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    (outdir / "step11ab_summary.md").write_text("\n".join(report), encoding="utf-8")
    (outdir / "step11ab_report.md").write_text("\n".join(report), encoding="utf-8")
    next_lines = [
        "# Step11AB next step recommendation",
        "",
        f"- Single-AUV: {checks['recommended_single_auv']}",
        f"- Multi-AUV: {checks['recommended_multi_auv']}",
        "- If the selected multi-AUV strategy is robust, repeat only that configuration on C06 and October.",
        "- If single-AUV target proxy fails, do not keep tuning static descriptors; implement mandatory target/route-level reward.",
    ]
    (outdir / "step11ab_next_step_recommendation.md").write_text("\n".join(next_lines), encoding="utf-8")
    shutil.copy2(Path(__file__), outdir / Path(__file__).name)

    print("\n============================================================")
    print("STEP11AB C01 REGION TARGET + VEHICLE SWEEP")
    print("============================================================")
    print(f"Output: {rel(outdir)}")
    print(f"Single rows: {len(single_df)}")
    print(f"Multi rows: {len(multi_df)}")
    print(f"Target success: {target_success}")
    print(f"Recommended single-AUV: {checks['recommended_single_auv']}")
    print(f"Recommended multi-AUV: {checks['recommended_multi_auv']}")
    print(f"Warnings: {len(warnings)}")
    print(f"Verdict: {verdict}")
    print("============================================================\n")
    return 0 if verdict != "STEP11AB_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
