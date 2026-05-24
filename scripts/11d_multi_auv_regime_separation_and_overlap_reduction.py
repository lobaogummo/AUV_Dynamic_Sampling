"""Step11D: multi-AUV regime separation and overlap reduction.

The Lucrezia planner is kept untouched. Native multi-AUV runs are used where a
single shared information map is enough. Vehicle-specific maps, overlap
reduction, and regime separation are implemented as 1-AUV candidate generation
plus post-solver pair selection because the planner exposes one static node
prize map through `temperr`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy import ndimage as ndi
except Exception:  # pragma: no cover
    ndi = None


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
SCRIPTS_ROOT = ROOT / "scripts"

DEFAULT_STEP10F = RESULTS_ROOT / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
DEFAULT_STEP11C_PRIMARY = RESULTS_ROOT / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322"
DEFAULT_STEP11C_SECONDARY = RESULTS_ROOT / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458"
DEFAULT_STEP09B = RESULTS_ROOT / "fossum_roi_x490_step09b_top20_c01_c06_temppred_classification_20260519_190144"
DEFAULT_STEP10E = RESULTS_ROOT / "fossum_roi_x490_step10e_top20_class01_class06_roi_x490_20260519_184636"
DEFAULT_STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_HRES = RESULTS_ROOT / "cmems_370_surface_to_hres_20260509_135642"
DEFAULT_PLANNER = ROOT / "OptimalPlanning_Lucrezia"

ROI_ROW_MIN = 55
ROI_ROW_MAX = 126
ROI_COL_MIN = 47
ROI_COL_MAX = 163
ROI_SHAPE = (72, 117)
EXPECTED_VALID_CELLS = 8004

CASE_ALIASES = {
    "primary": ["C01_representative"],
    "secondary": ["C06_representative", "October_control"],
    "all": ["C01_representative", "C06_representative", "October_control"],
}
CASE_DISPLAY = {"October_control": "October_reference"}
PAIR_WEIGHTS = {
    "lambda_A": 0.25,
    "lambda_B": 0.25,
    "lambda_boundary": 0.10,
    "lambda_overlap": 0.25,
    "lambda_proximity": 0.15,
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_step11a_module():
    return load_module("step11a_utils", SCRIPTS_ROOT / "11a_run_minimal_boundary_planner_comparison.py")


def load_step11c_module():
    return load_module("step11c_utils", SCRIPTS_ROOT / "11c_single_auv_boundary_crossing_reward.py")


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return None if not math.isfinite(value) else value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def short_name(text: str, limit: int = 40) -> str:
    clean = safe_name(text)
    if len(clean) <= limit:
        return clean
    digest = hashlib.sha1(clean.encode("utf-8")).hexdigest()[:10]
    return f"{clean[: limit - 11]}_{digest}"


def minmax01(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        out[mask] = 0.0
        return out
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmax - vmin <= 1e-12:
        out[mask] = 0.0
    else:
        out[mask] = ((arr[mask] - vmin) / (vmax - vmin)).astype(np.float32)
    return out


def audit_multi_auv_planner(planner: Path) -> dict[str, Any]:
    config = require(planner / "Config_file.py", "Config_file.py").read_text(encoding="utf-8", errors="replace")
    optimal = require(planner / "OptimalPlanning.py", "OptimalPlanning.py").read_text(encoding="utf-8", errors="replace")
    utils = require(planner / "Utils.py", "Utils.py").read_text(encoding="utf-8", errors="replace")
    text = "\n".join([config, optimal, utils])
    supports_multi = "AUV_NUMBER" in config and "VehicleType" in optimal and "MISSION_DURATIONS" in optimal
    vehicle_specific_maps = any(token in text for token in ["temperr_vehicle", "vehicle_prize", "prizes_by_vehicle", "vehicle_specific"])
    overlap_penalty = any(token in text.lower() for token in ["overlap penalty", "redundancy penalty", "duplicate penalty", "shared node penalty"])
    unique_nodes = "prize" in utils.lower() and "get_nodes_prize" in optimal
    sequential_viable = supports_multi and "AUV_NUMBER = 1" in config + optimal
    return {
        "auv_number_definition": "Config_file.py::AUV_NUMBER",
        "mission_duration_definition": "Config_file.py::MISSION_DURATIONS; converted to max route distance per VehicleType",
        "trajectory_output": "routes_file.txt contains one route block per AUV",
        "multi_auv_supported": bool(supports_multi),
        "vehicle_specific_maps_supported": bool(vehicle_specific_maps),
        "vehicle_specific_prizes_supported": bool(vehicle_specific_maps),
        "overlap_penalty_supported": bool(overlap_penalty),
        "same_node_revisit_prevented_by_solver": bool(unique_nodes),
        "same_node_revisit_note": "Single shared client set means exact duplicate POI visits are not expected inside one VRP solution; path overlap between segments is not explicitly penalized.",
        "sequential_planning_viable": bool(sequential_viable),
        "post_solver_selection_needed": bool(not vehicle_specific_maps or not overlap_penalty),
        "recommended_mode": "native_shared_map_plus_1auv_candidates_post_solver_selection",
    }


def write_audit(out_dir: Path, audit: dict[str, Any]) -> None:
    write_json(out_dir / "step11d_multi_auv_planner_capability_audit.json", audit)
    lines = [
        "# Step11D Multi-AUV Planner Capability Audit",
        "",
        f"- Multi-AUV support: `{audit['multi_auv_supported']}` via `AUV_NUMBER`, `MISSION_DURATIONS`, and PyVRP `VehicleType`.",
        f"- Vehicle-specific maps supported: `{audit['vehicle_specific_maps_supported']}`.",
        f"- Vehicle-specific prizes supported: `{audit['vehicle_specific_prizes_supported']}`.",
        f"- Real overlap penalty supported: `{audit['overlap_penalty_supported']}`.",
        f"- Same-node duplicate handling: `{audit['same_node_revisit_prevented_by_solver']}`. {audit['same_node_revisit_note']}",
        f"- Sequential planning viable: `{audit['sequential_planning_viable']}`.",
        f"- Post-solver selection needed: `{audit['post_solver_selection_needed']}`.",
        f"- Recommended mode: `{audit['recommended_mode']}`.",
    ]
    (out_dir / "step11d_multi_auv_planner_capability_audit.md").write_text("\n".join(lines), encoding="utf-8")


def find_step11c_run_dir(step11c_primary: Path, step11c_secondary: Path, case_id: str, run_name: str) -> Path | None:
    if case_id == "C01_representative":
        root = step11c_primary
        display = case_id
    else:
        root = step11c_secondary
        display = CASE_DISPLAY.get(case_id, case_id)
    candidates = [
        root / "planner_runs" / safe_name(f"{display}__1auv_12h__{run_name}"),
        root / "planner_runs" / safe_name(f"{case_id}__1auv_12h__{run_name}"),
    ]
    for path in candidates:
        if (path / "routes_file.txt").exists():
            return path
    return None


def route_points_by_route(s11a, routes: list[dict[str, Any]], lat_hres: np.ndarray, lon_hres: np.ndarray) -> dict[int, list[tuple[int, int]]]:
    out = {}
    for route in routes:
        out[int(route["route_id"])] = s11a.route_grid_points([route], lat_hres, lon_hres)
    return out


def valid_unique(points: list[tuple[int, int]], valid_full: np.ndarray) -> list[tuple[int, int]]:
    unique = list(dict.fromkeys(points))
    return [(r, c) for r, c in unique if 0 <= r < valid_full.shape[0] and 0 <= c < valid_full.shape[1] and bool(valid_full[r, c])]


def sample_values(points: list[tuple[int, int]], arr: np.ndarray, valid_full: np.ndarray) -> np.ndarray:
    pts = valid_unique(points, valid_full)
    if not pts:
        return np.array([], dtype=np.float32)
    rr = np.array([p[0] for p in pts], dtype=int)
    cc = np.array([p[1] for p in pts], dtype=int)
    vals = arr[rr, cc]
    return vals[np.isfinite(vals)]


def region_labels(points: list[tuple[int, int]], region_a: np.ndarray, region_b: np.ndarray, valid_full: np.ndarray) -> list[int]:
    labels = []
    for r, c in points:
        if r < 0 or c < 0 or r >= valid_full.shape[0] or c >= valid_full.shape[1] or not bool(valid_full[r, c]):
            continue
        if bool(region_a[r, c]):
            labels.append(1)
        elif bool(region_b[r, c]):
            labels.append(2)
    return labels


def crossing_count(labels: list[int]) -> int:
    compressed = []
    for label in labels:
        if not compressed or compressed[-1] != label:
            compressed.append(label)
    return int(sum(1 for a, b in zip(compressed[:-1], compressed[1:]) if a != b))


def vehicle_metrics(
    run_id: str,
    strategy: str,
    case_id: str,
    vehicle_id: int,
    points: list[tuple[int, int]],
    route: dict[str, Any] | None,
    maps: dict[str, np.ndarray],
    masks: dict[str, np.ndarray],
    valid_full: np.ndarray,
    solver_status: str,
) -> dict[str, Any]:
    pts = valid_unique(points, valid_full)
    labels = region_labels(points, masks["region_A_full"], masks["region_B_full"], valid_full)
    in_a = sample_values(pts, masks["region_A_full"].astype(np.float32), valid_full)
    in_b = sample_values(pts, masks["region_B_full"].astype(np.float32), valid_full)
    in_core = sample_values(pts, masks["boundary_core_full"].astype(np.float32), valid_full)
    length = float(route.get("length_km", float("nan"))) if route else float("nan")
    duration = float((route.get("mission_duration_h") or 0) + (route.get("mission_duration_m") or 0) / 60) if route else float("nan")
    return {
        "run_id": run_id,
        "strategy": strategy,
        "case_id": case_id,
        "vehicle_id": vehicle_id,
        "solver_status": solver_status,
        "collected_STD": float(np.nansum(sample_values(pts, maps["STD_full"], valid_full))),
        "collected_boundary": float(np.nansum(sample_values(pts, maps["boundary_full"], valid_full))),
        "collected_region_A": float(np.nansum(in_a)),
        "collected_region_B": float(np.nansum(in_b)),
        "fraction_path_region_A": float(np.nanmean(in_a)) if in_a.size else float("nan"),
        "fraction_path_region_B": float(np.nanmean(in_b)) if in_b.size else float("nan"),
        "fraction_path_boundary_core": float(np.nanmean(in_core)) if in_core.size else float("nan"),
        "crossing_count": crossing_count(labels),
        "regions_visited": int(bool(np.any(in_a > 0.5))) + int(bool(np.any(in_b > 0.5))),
        "trajectory_length": length,
        "mission_duration": duration,
        "sampled_cells": int(len(pts)),
    }


def pair_distance_metrics(points_a: list[tuple[int, int]], points_b: list[tuple[int, int]], valid_full: np.ndarray) -> dict[str, float]:
    a = np.array(valid_unique(points_a, valid_full), dtype=float)
    b = np.array(valid_unique(points_b, valid_full), dtype=float)
    if a.size == 0 or b.size == 0:
        return {"inter_vehicle_min_distance": float("nan"), "inter_vehicle_mean_distance": float("nan"), "proximity_penalty": float("nan")}
    sample_a = a if len(a) <= 400 else a[np.linspace(0, len(a) - 1, 400).astype(int)]
    sample_b = b if len(b) <= 400 else b[np.linspace(0, len(b) - 1, 400).astype(int)]
    d = np.sqrt(((sample_a[:, None, :] - sample_b[None, :, :]) ** 2).sum(axis=2))
    nearest = np.min(d, axis=1)
    min_dist = float(np.min(d))
    mean_dist = float(np.mean(nearest))
    proximity = float(np.mean(np.exp(-nearest / 5.0)))
    return {"inter_vehicle_min_distance": min_dist, "inter_vehicle_mean_distance": mean_dist, "proximity_penalty": proximity}


def fleet_metrics(
    run_id: str,
    strategy: str,
    case_id: str,
    vehicle_points: dict[int, list[tuple[int, int]]],
    vehicle_df: pd.DataFrame,
    maps: dict[str, np.ndarray],
    masks: dict[str, np.ndarray],
    valid_full: np.ndarray,
    baseline: dict[str, float] | None = None,
) -> dict[str, Any]:
    ids = sorted(vehicle_points)
    points_a = vehicle_points.get(ids[0], []) if ids else []
    points_b = vehicle_points.get(ids[1], []) if len(ids) > 1 else []
    set_a = set(valid_unique(points_a, valid_full))
    set_b = set(valid_unique(points_b, valid_full))
    union = set_a | set_b
    inter = set_a & set_b
    top10 = maps["STD_full"] >= np.nanpercentile(maps["STD_full"][np.isfinite(maps["STD_full"])], 90)
    shared_top10 = int(sum(1 for p in inter if bool(top10[p])))
    dist = pair_distance_metrics(points_a, points_b, valid_full)
    region_a_cells = set(zip(*np.where(masks["region_A_full"] & valid_full)))
    region_b_cells = set(zip(*np.where(masks["region_B_full"] & valid_full)))
    fleet_a_cov = float(len(union & region_a_cells) / max(len(region_a_cells), 1))
    fleet_b_cov = float(len(union & region_b_cells) / max(len(region_b_cells), 1))
    overlap = float(len(inter) / max(len(union), 1))
    complementarity = float(0.5 * (fleet_a_cov + fleet_b_cov) + 0.5 * (1.0 - overlap))
    collected_std = float(vehicle_df["collected_STD"].sum()) if not vehicle_df.empty else 0.0
    collected_boundary = float(vehicle_df["collected_boundary"].sum()) if not vehicle_df.empty else 0.0
    base_region = baseline.get("fleet_region_coverage", 0.0) if baseline else 0.0
    base_overlap = baseline.get("trajectory_overlap_ratio", overlap) if baseline else overlap
    base_std = baseline.get("fleet_collected_STD", collected_std) if baseline else collected_std
    base_boundary = baseline.get("fleet_collected_boundary", collected_boundary) if baseline else collected_boundary
    return {
        "run_id": run_id,
        "strategy": strategy,
        "case_id": case_id,
        "fleet_collected_STD": collected_std,
        "fleet_collected_boundary": collected_boundary,
        "inter_vehicle_min_distance": dist["inter_vehicle_min_distance"],
        "inter_vehicle_mean_distance": dist["inter_vehicle_mean_distance"],
        "trajectory_overlap_ratio": overlap,
        "duplicate_sampled_cells": int(len(inter)),
        "shared_top10_cells": shared_top10,
        "fleet_region_A_coverage": fleet_a_cov,
        "fleet_region_B_coverage": fleet_b_cov,
        "fleet_region_coverage": float(fleet_a_cov + fleet_b_cov),
        "fleet_total_area_covered": int(len(union)),
        "fleet_complementarity_score": complementarity,
        "proximity_penalty": dist["proximity_penalty"],
        "increase_region_coverage": float((fleet_a_cov + fleet_b_cov) - base_region),
        "decrease_overlap": float(base_overlap - overlap),
        "change_in_STD_collected": float(collected_std - base_std),
        "change_in_boundary_collected": float(collected_boundary - base_boundary),
    }


def pair_score(row_a: pd.Series, row_b: pd.Series, pair_metrics: dict[str, Any]) -> float:
    std_norm = (float(row_a["collected_STD"]) + float(row_b["collected_STD"])) / 200.0
    boundary_norm = (float(row_a["collected_boundary"]) + float(row_b["collected_boundary"])) / 300.0
    region_a = max(float(row_a["fraction_path_region_A"]), float(row_b["fraction_path_region_A"]))
    region_b = max(float(row_a["fraction_path_region_B"]), float(row_b["fraction_path_region_B"]))
    overlap = float(pair_metrics["trajectory_overlap_ratio"])
    proximity = float(pair_metrics["proximity_penalty"])
    return float(
        std_norm
        + PAIR_WEIGHTS["lambda_A"] * region_a
        + PAIR_WEIGHTS["lambda_B"] * region_b
        + PAIR_WEIGHTS["lambda_boundary"] * boundary_norm
        - PAIR_WEIGHTS["lambda_overlap"] * overlap
        - PAIR_WEIGHTS["lambda_proximity"] * proximity
    )


def make_maps(std_roi: np.ndarray, boundary_roi: np.ndarray, region_a: np.ndarray, region_b: np.ndarray, boundary_core: np.ndarray, mask: np.ndarray) -> dict[str, np.ndarray]:
    region_a_reward = minmax01(region_a.astype(np.float32), mask)
    region_b_reward = minmax01(region_b.astype(np.float32), mask)
    boundary_core_reward = np.where(mask, boundary_core.astype(np.float32), np.nan).astype(np.float32)
    crossing_proxy = minmax01(0.75 * boundary_roi + 0.25 * boundary_core_reward, mask)
    maps = {
        "multi_baseline_STD": std_roi.astype(np.float32),
        "multi_boundary_alpha050": (0.5 * std_roi + 0.5 * boundary_roi).astype(np.float32),
        "candidate_region_A": (0.6 * std_roi + 0.4 * region_a_reward).astype(np.float32),
        "candidate_region_B": (0.6 * std_roi + 0.4 * region_b_reward).astype(np.float32),
        "candidate_region_A_with_crossing": (0.5 * std_roi + 0.3 * region_a_reward + 0.2 * boundary_core_reward).astype(np.float32),
        "candidate_region_B_with_crossing": (0.5 * std_roi + 0.3 * region_b_reward + 0.2 * boundary_core_reward).astype(np.float32),
        "candidate_crossing_proxy_gamma025": (0.5 * std_roi + 0.3 * boundary_roi + 0.2 * crossing_proxy).astype(np.float32),
        "region_A_reward": region_a_reward,
        "region_B_reward": region_b_reward,
        "boundary_core_reward": boundary_core_reward,
        "crossing_proxy_gamma025": crossing_proxy,
    }
    for arr in maps.values():
        arr[~mask] = np.nan
    return maps


def penalize_near_route(info_roi: np.ndarray, route_points: list[tuple[int, int]], mask: np.ndarray, penalty: float = 0.70, radius: int = 5) -> np.ndarray:
    roi_points = [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in route_points if ROI_ROW_MIN <= r <= ROI_ROW_MAX and ROI_COL_MIN <= c <= ROI_COL_MAX]
    penalized = info_roi.copy()
    if not roi_points or ndi is None:
        return penalized
    covered = np.zeros(mask.shape, dtype=bool)
    for r, c in roi_points:
        if 0 <= r < covered.shape[0] and 0 <= c < covered.shape[1]:
            covered[r, c] = True
    dist = ndi.distance_transform_edt(~covered)
    penalized[(dist <= radius) & mask] *= float(1.0 - penalty)
    return penalized.astype(np.float32)


def plot_masks_and_rewards(out_path: Path, region_a: np.ndarray, region_b: np.ndarray, boundary_core: np.ndarray, maps: dict[str, np.ndarray]) -> None:
    panels = [
        ("region_A_mask", region_a.astype(float), "Blues", 0, 1),
        ("region_B_mask", region_b.astype(float), "Reds", 0, 1),
        ("boundary_core", boundary_core.astype(float), "magma", 0, 1),
        ("region_A_reward", maps["region_A_reward"], "Blues", 0, 1),
        ("region_B_reward", maps["region_B_reward"], "Reds", 0, 1),
        ("crossing_proxy_gamma025", maps["crossing_proxy_gamma025"], "viridis", 0, 1),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), squeeze=False)
    for ax, (title, arr, cmap, vmin, vmax) in zip(axes.ravel(), panels):
        im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(title)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def roi_points(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in points if ROI_ROW_MIN <= r <= ROI_ROW_MAX and ROI_COL_MIN <= c <= ROI_COL_MAX]


def plot_strategy_overlay(out_path: Path, title: str, temp_roi: np.ndarray, region_a: np.ndarray, region_b: np.ndarray, boundary_core: np.ndarray, vehicle_points: dict[int, list[tuple[int, int]]]) -> None:
    rgb = np.zeros((*ROI_SHAPE, 3), dtype=np.float32)
    rgb[..., :] = 0.08
    temp = temp_roi.copy()
    vals = temp[np.isfinite(temp)]
    if vals.size:
        tempn = (temp - np.nanmin(vals)) / max(float(np.nanmax(vals) - np.nanmin(vals)), 1e-9)
        rgb[..., 1] = np.nan_to_num(tempn, nan=0.0) * 0.25
    rgb[region_a] += [0.0, 0.05, 0.65]
    rgb[region_b] += [0.65, 0.05, 0.0]
    rgb[boundary_core] = [1.0, 0.9, 0.05]
    rgb = np.clip(rgb, 0, 1)
    colors = {1: "#00e5ff", 2: "#ff4f7b"}
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.imshow(rgb, origin="lower", aspect="auto")
    for vehicle_id, points in sorted(vehicle_points.items()):
        pts = roi_points(points)
        if len(pts) > 1:
            yy = [p[0] for p in pts]
            xx = [p[1] for p in pts]
            ax.plot(xx, yy, color=colors.get(vehicle_id, "white"), linewidth=1.7, marker="o", markersize=2, label=f"AUV{vehicle_id}")
    ax.set_title(title)
    ax.axis("off")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_bar(df: pd.DataFrame, metric: str, title: str, out_path: Path) -> None:
    if df.empty or metric not in df.columns:
        return
    labels = [f"{r.case_id}\n{r.strategy}" for r in df.itertuples()]
    fig, ax = plt.subplots(figsize=(max(10, len(df) * 0.8), 4.6))
    ax.bar(np.arange(len(df)), df[metric].astype(float))
    ax.set_xticks(np.arange(len(df)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_distance(df: pd.DataFrame, out_path: Path) -> None:
    if df.empty:
        return
    labels = [f"{r.case_id}\n{r.strategy}" for r in df.itertuples()]
    fig, ax = plt.subplots(figsize=(max(10, len(df) * 0.8), 4.6))
    ax.plot(np.arange(len(df)), df["inter_vehicle_mean_distance"].astype(float), marker="o", label="mean")
    ax.plot(np.arange(len(df)), df["inter_vehicle_min_distance"].astype(float), marker="s", label="min")
    ax.set_xticks(np.arange(len(df)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_title("Inter-vehicle distance in grid cells")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_comparison_panel(df: pd.DataFrame, out_path: Path) -> None:
    if df.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), squeeze=False)
    metrics = [
        ("fleet_region_coverage", "Region coverage"),
        ("trajectory_overlap_ratio", "Overlap ratio"),
        ("fleet_complementarity_score", "Complementarity"),
    ]
    labels = [f"{r.case_id}\n{r.strategy}" for r in df.itertuples()]
    for ax, (metric, title) in zip(axes.ravel(), metrics):
        ax.bar(np.arange(len(df)), df[metric].astype(float))
        ax.set_xticks(np.arange(len(df)))
        ax.set_xticklabels(labels, rotation=90, fontsize=6)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def run_planner_case(
    s11a,
    planner: Path,
    out_dir: Path,
    run_id: str,
    info_roi: np.ndarray,
    mask: np.ndarray,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    bathy_hres: np.ndarray,
    config_text: str,
    timeout_s: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    legacy_run_dir = out_dir / "planner_runs" / safe_name(run_id)
    short_run_dir = out_dir / "planner_runs" / short_name(run_id)
    if (legacy_run_dir / "routes_file.txt").exists():
        routes = s11a.parse_routes_file(legacy_run_dir / "routes_file.txt")
        return (
            {
                "command": "reuse existing Step11D run",
                "returncode": 0,
                "runtime_s": 0.0,
                "status": "REUSED_STEP11D",
                "error": "",
                "input_nc": "",
                "path": "",
                "temperr_shape": [],
                "finite_cells": 0,
                "temperr_min": float("nan"),
                "temperr_max": float("nan"),
                "landt_valid_cells": 0,
            },
            routes,
            legacy_run_dir,
        )
    if (short_run_dir / "routes_file.txt").exists():
        routes = s11a.parse_routes_file(short_run_dir / "routes_file.txt")
        return (
            {
                "command": "reuse existing Step11D run",
                "returncode": 0,
                "runtime_s": 0.0,
                "status": "REUSED_STEP11D",
                "error": "",
                "input_nc": "",
                "path": "",
                "temperr_shape": [],
                "finite_cells": 0,
                "temperr_min": float("nan"),
                "temperr_max": float("nan"),
                "landt_valid_cells": 0,
            },
            routes,
            short_run_dir,
        )
    run_dir = short_run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    input_nc = out_dir / "planner_inputs" / f"{short_name(run_id)}_planner_interface.nc"
    nc_meta = s11a.build_interface_nc(input_nc, info_roi, mask, lat_hres, lon_hres, bathy_hres)
    shutil.copy2(input_nc, run_dir / input_nc.name)
    s11a.copy_planner_runtime(planner, run_dir, config_text)
    status = "NOT_RUN"
    error = ""
    try:
        run_result = s11a.run_planner(run_dir, input_nc, timeout_s)
        status = "SUCCESS" if run_result["returncode"] == 0 and (run_dir / "routes_file.txt").exists() else "FAILED"
    except subprocess.TimeoutExpired as exc:
        run_result = {"command": " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd), "returncode": -999, "runtime_s": timeout_s}
        status = "TIMEOUT"
        error = f"Timeout after {timeout_s}s"
        (run_dir / "planner_stdout.txt").write_text(exc.stdout or "", encoding="utf-8", errors="replace")
        (run_dir / "planner_stderr.txt").write_text((exc.stderr or "") + "\n" + error, encoding="utf-8", errors="replace")
    except Exception as exc:
        run_result = {"command": f"{sys.executable} OptimalPlanning.py {input_nc}", "returncode": -998, "runtime_s": float("nan")}
        status = "FAILED"
        error = repr(exc)
        (run_dir / "planner_stderr.txt").write_text(error, encoding="utf-8", errors="replace")
    routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
    s11a.save_trajectory_csv_json(run_dir, routes)
    return ({**run_result, "status": status, "error": error, **nc_meta, "input_nc": str(input_nc)}, routes, run_dir)


def write_reports(out_dir: Path, audit: dict[str, Any], manifest: pd.DataFrame, fleet: pd.DataFrame, selected: pd.DataFrame, verdict: str) -> None:
    best = fleet.sort_values("fleet_complementarity_score", ascending=False).iloc[0] if not fleet.empty else None
    baseline = fleet[fleet["strategy"] == "multi_baseline_STD"]
    boundary = fleet[fleet["strategy"] == "multi_boundary_alpha050"]
    best_strategy = str(best["strategy"]) if best is not None else "none"
    boundary_overlap = float(boundary.iloc[0]["trajectory_overlap_ratio"]) if not boundary.empty else float("nan")
    baseline_overlap = float(baseline.iloc[0]["trajectory_overlap_ratio"]) if not baseline.empty else float("nan")
    lines = [
        "# Step11D Multi-AUV Regime Separation",
        "",
        f"- Output: `{out_dir}`",
        f"- Planned runs/strategies: {len(manifest)}",
        f"- Vehicle-specific maps supported: `{audit['vehicle_specific_maps_supported']}`",
        f"- Overlap penalty supported: `{audit['overlap_penalty_supported']}`",
        f"- Post-solver selection needed: `{audit['post_solver_selection_needed']}`",
        f"- Best strategy by complementarity: `{best_strategy}`",
        f"- Verdict: `{verdict}`",
        "",
        "## Answers",
        f"1. Vehicle-specific maps: `{audit['vehicle_specific_maps_supported']}`.",
        f"2. Real overlap penalty: `{audit['overlap_penalty_supported']}`.",
        f"3. Post-solver selection: `{audit['post_solver_selection_needed']}`.",
        f"4. Boundary-only juntou os veiculos? overlap={boundary_overlap:.3f}; baseline overlap={baseline_overlap:.3f}.",
        "5. Vehicle-specific maps: see `step11d_fleet_level_metrics.csv` and selected pair summary.",
        "6. Overlap/separation: see `step11d_overlap_and_separation_metrics.csv`.",
        "7. Region coverage: see `fleet_region_A_coverage` and `fleet_region_B_coverage`.",
        "8. Operational cost: compare `trajectory_length`/`mission_duration` in vehicle metrics.",
        f"9. Most promising strategy: `{best_strategy}`.",
        "10. Compatibility: native shared-map multi-AUV is real planner behavior; vehicle-specific/sequential/post-solver parts are proxy/diagnostic wrappers.",
    ]
    (out_dir / "step11d_report.md").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "step11d_summary.md").write_text("\n".join(lines[:10]), encoding="utf-8")
    next_lines = [
        "# Step11D Next Step Recommendation",
        "",
        f"- Use `{best_strategy}` as the thesis candidate if its route overlay is operationally acceptable.",
        "- For a production planner change, add vehicle-specific node prizes or route-level pair penalties in the PyVRP layer instead of only selecting routes post hoc.",
        "- Validate the selected pair with the mission team because the current separation logic is a proxy around the unchanged planner.",
    ]
    (out_dir / "step11d_next_step_recommendation.md").write_text("\n".join(next_lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11D multi-AUV regime separation and overlap reduction.")
    parser.add_argument("--cases", choices=["primary", "secondary", "all"], default="primary")
    parser.add_argument("--step10f", type=Path, default=DEFAULT_STEP10F)
    parser.add_argument("--step11c-primary", type=Path, default=DEFAULT_STEP11C_PRIMARY)
    parser.add_argument("--step11c-secondary", type=Path, default=DEFAULT_STEP11C_SECONDARY)
    parser.add_argument("--step09b", type=Path, default=DEFAULT_STEP09B)
    parser.add_argument("--step10e", type=Path, default=DEFAULT_STEP10E)
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--hres", type=Path, default=DEFAULT_HRES)
    parser.add_argument("--planner", type=Path, default=DEFAULT_PLANNER)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--resume-output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    s11a = load_step11a_module()
    s11c = load_step11c_module()
    out_dir = args.resume_output.resolve() if args.resume_output is not None else (args.output_root.resolve() / f"fossum_roi_x490_step11d_multi_auv_regime_separation_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for sub in ["planner_inputs", "planner_configs", "planner_runs", "figures", "masks"]:
        (out_dir / sub).mkdir(exist_ok=True)
    fig_dir = out_dir / "figures"

    audit = audit_multi_auv_planner(args.planner)
    write_audit(out_dir, audit)

    mask = np.load(require(args.step00 / "mask_common_roi_x490.npy", "Step00 mask")).astype(bool)
    if mask.shape != ROI_SHAPE or int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected ROI mask: shape={mask.shape}, valid={int(mask.sum())}")
    lat_hres = np.load(require(args.hres / "LAT_hres.npy", "HRes LAT"))
    lon_hres = np.load(require(args.hres / "LON_hres.npy", "HRes LON"))
    bathy_hres = np.load(require(args.hres / "BATHY_hres.npy", "HRes BATHY"))
    valid_full = s11a.embed_roi_to_hres(mask.astype(np.float32), mask, fill=np.nan) > 0.5

    cases, base_maps = s11c.load_cases_and_base_maps(args.step10f)
    step09b_assignments, step09b_maps = s11c.load_step09b_region_maps(args.step09b)
    selected_cases = CASE_ALIASES[args.cases]
    cases = cases[cases["case_id"].isin(selected_cases)].copy().reset_index(drop=True)

    original_config = s11a.read_config_text(require(args.planner / "Config_file.py", "Lucrezia Config_file.py"))
    config_1auv = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=12.0, auv_number=1)
    config_2auv = s11a.generated_config(original_config, single_auv=False, mission_duration_hours=12.0, auv_number=2)
    (out_dir / "planner_configs" / "Config_file_step11d_1auv_12h.py").write_text(config_1auv, encoding="utf-8")
    (out_dir / "planner_configs" / "Config_file_step11d_2auv_12h.py").write_text(config_2auv, encoding="utf-8")

    manifest_rows = []
    solver_rows = []
    vehicle_rows = []
    fleet_rows = []
    candidate_rows = []
    pair_rows = []
    selected_rows = []
    all_info_maps: dict[str, np.ndarray] = {}
    baseline_by_case: dict[str, dict[str, float]] = {}

    for _, case in cases.iterrows():
        case_id = str(case["case_id"])
        display_case = CASE_DISPLAY.get(case_id, case_id)
        case_idx = int(case["case_order"])
        case_date = str(case["date"])
        std_roi = base_maps["STD_norm"][case_idx].astype(np.float32)
        boundary_roi = base_maps["boundary"][case_idx].astype(np.float32)
        temp_roi = base_maps["TEMPpred"][case_idx].astype(np.float32)
        region_info = s11c.build_region_masks(case_id, case_date, case_idx, mask, base_maps, step09b_assignments, step09b_maps)
        maps_roi = make_maps(std_roi, boundary_roi, region_info["region_A_mask"], region_info["region_B_mask"], region_info["boundary_core_mask"], mask)
        if case_id == "C01_representative":
            np.save(out_dir / "step11d_regime_A_mask.npy", region_info["region_A_mask"])
            np.save(out_dir / "step11d_regime_B_mask.npy", region_info["region_B_mask"])
            np.save(out_dir / "step11d_boundary_core_mask.npy", region_info["boundary_core_mask"])
            np.save(out_dir / "step11d_region_A_reward.npy", maps_roi["region_A_reward"])
            np.save(out_dir / "step11d_region_B_reward.npy", maps_roi["region_B_reward"])
            plot_masks_and_rewards(out_dir / "step11d_regime_masks_and_rewards.png", region_info["region_A_mask"], region_info["region_B_mask"], region_info["boundary_core_mask"], maps_roi)
        np.save(out_dir / "masks" / f"{safe_name(case_id)}_regime_A_mask.npy", region_info["region_A_mask"])
        np.save(out_dir / "masks" / f"{safe_name(case_id)}_regime_B_mask.npy", region_info["region_B_mask"])
        np.save(out_dir / "masks" / f"{safe_name(case_id)}_boundary_core_mask.npy", region_info["boundary_core_mask"])

        full_maps = {
            "STD_full": s11a.embed_roi_to_hres(std_roi, mask, fill=np.nan),
            "boundary_full": s11a.embed_roi_to_hres(boundary_roi, mask, fill=np.nan),
        }
        full_masks = {
            "region_A_full": s11a.embed_roi_to_hres(region_info["region_A_mask"].astype(np.float32), mask, fill=np.nan) > 0.5,
            "region_B_full": s11a.embed_roi_to_hres(region_info["region_B_mask"].astype(np.float32), mask, fill=np.nan) > 0.5,
            "boundary_core_full": s11a.embed_roi_to_hres(region_info["boundary_core_mask"].astype(np.float32), mask, fill=np.nan) > 0.5,
        }
        for name, arr in maps_roi.items():
            all_info_maps[f"{case_id}__{name}"] = arr

        strategy_vehicle_points: dict[str, dict[int, list[tuple[int, int]]]] = {}
        strategy_vehicle_routes: dict[str, dict[int, dict[str, Any] | None]] = {}
        strategy_status: dict[str, str] = {}
        strategy_runtime: dict[str, float] = {}

        for strategy, map_name in [("multi_baseline_STD", "multi_baseline_STD"), ("multi_boundary_alpha050", "multi_boundary_alpha050")]:
            run_id = f"{display_case}__2auv_12h__{strategy}"
            run_result, routes, run_dir = run_planner_case(s11a, args.planner, out_dir, run_id, maps_roi[map_name], mask, lat_hres, lon_hres, bathy_hres, config_2auv, args.timeout_s)
            points_by_route = route_points_by_route(s11a, routes, lat_hres, lon_hres)
            route_by_id = {int(r["route_id"]): r for r in routes}
            strategy_vehicle_points[strategy] = points_by_route
            strategy_vehicle_routes[strategy] = route_by_id
            strategy_status[strategy] = str(run_result["status"])
            strategy_runtime[strategy] = float(run_result["runtime_s"])
            manifest_rows.append({"run_id": run_id, "case_id": case_id, "strategy": strategy, "run_kind": "native_2auv_shared_map", "status": run_result["status"], "run_dir": str(run_dir), "input_nc": run_result["input_nc"]})
            solver_rows.append({"run_id": run_id, "case_id": case_id, "strategy": strategy, **run_result})

        candidate_specs = {
            "baseline_STD": None,
            "boundary_alpha050": None,
            "crossing_gamma025": None,
            "region_A": "candidate_region_A",
            "region_B": "candidate_region_B",
            "region_A_with_crossing": "candidate_region_A_with_crossing",
            "region_B_with_crossing": "candidate_region_B_with_crossing",
        }
        candidates: dict[str, dict[str, Any]] = {}
        for cand_name, map_name in candidate_specs.items():
            routes: list[dict[str, Any]] = []
            run_dir: Path | None = None
            run_result: dict[str, Any]
            if map_name is None:
                step11c_name = cand_name
                run_dir = find_step11c_run_dir(args.step11c_primary, args.step11c_secondary, case_id, step11c_name)
                if run_dir is not None:
                    routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
                    run_result = {"status": "REUSED_STEP11C", "runtime_s": 0.0, "returncode": 0, "command": "reuse Step11C", "error": "", "input_nc": ""}
                else:
                    map_lookup = {"baseline_STD": "multi_baseline_STD", "boundary_alpha050": "multi_boundary_alpha050", "crossing_gamma025": "candidate_crossing_proxy_gamma025"}
                    run_id = f"{display_case}__1auv_12h__candidate_{cand_name}"
                    run_result, routes, run_dir = run_planner_case(s11a, args.planner, out_dir, run_id, maps_roi[map_lookup[cand_name]], mask, lat_hres, lon_hres, bathy_hres, config_1auv, args.timeout_s)
            else:
                run_id = f"{display_case}__1auv_12h__candidate_{cand_name}"
                run_result, routes, run_dir = run_planner_case(s11a, args.planner, out_dir, run_id, maps_roi[map_name], mask, lat_hres, lon_hres, bathy_hres, config_1auv, args.timeout_s)
                if not routes and cand_name.endswith("_with_crossing"):
                    fallback_name = cand_name.replace("_with_crossing", "")
                    if fallback_name in candidates:
                        routes = [candidates[fallback_name]["route"]] if candidates[fallback_name]["route"] else []
                        run_result = {
                            **run_result,
                            "status": f"FALLBACK_TO_{fallback_name}",
                            "returncode": 0,
                            "error": "Planner failed for with-crossing candidate; reused non-crossing regime candidate for proxy comparison.",
                        }
                manifest_rows.append({"run_id": run_id, "case_id": case_id, "strategy": f"candidate_{cand_name}", "run_kind": "1auv_candidate", "status": run_result["status"], "run_dir": str(run_dir), "input_nc": run_result["input_nc"]})
                solver_rows.append({"run_id": run_id, "case_id": case_id, "strategy": f"candidate_{cand_name}", **run_result})
            route = routes[0] if routes else None
            points = s11a.route_grid_points(routes[:1], lat_hres, lon_hres) if routes else []
            cand_run_id = f"{display_case}__candidate__{cand_name}"
            vm = vehicle_metrics(cand_run_id, f"candidate_{cand_name}", case_id, 1, points, route, full_maps, full_masks, valid_full, str(run_result["status"]))
            candidates[cand_name] = {"points": points, "route": route, "metrics": vm, "run_dir": str(run_dir) if run_dir else ""}
            candidate_rows.append({**vm, "candidate_name": cand_name, "source_run_dir": str(run_dir) if run_dir else ""})

        seq_b_map = penalize_near_route(maps_roi["candidate_region_B"], candidates["region_A"]["points"], mask)
        all_info_maps[f"{case_id}__candidate_region_B_sequential_penalized"] = seq_b_map
        run_id = f"{display_case}__1auv_12h__candidate_region_B_sequential_penalized"
        run_result, routes, run_dir = run_planner_case(s11a, args.planner, out_dir, run_id, seq_b_map, mask, lat_hres, lon_hres, bathy_hres, config_1auv, args.timeout_s)
        route = routes[0] if routes else None
        points = s11a.route_grid_points(routes[:1], lat_hres, lon_hres) if routes else []
        vm = vehicle_metrics(f"{display_case}__candidate__region_B_sequential_penalized", "candidate_region_B_sequential_penalized", case_id, 1, points, route, full_maps, full_masks, valid_full, str(run_result["status"]))
        candidates["region_B_sequential_penalized"] = {"points": points, "route": route, "metrics": vm, "run_dir": str(run_dir)}
        candidate_rows.append({**vm, "candidate_name": "region_B_sequential_penalized", "source_run_dir": str(run_dir)})
        manifest_rows.append({"run_id": run_id, "case_id": case_id, "strategy": "candidate_region_B_sequential_penalized", "run_kind": "1auv_candidate_sequential", "status": run_result["status"], "run_dir": str(run_dir), "input_nc": run_result["input_nc"]})
        solver_rows.append({"run_id": run_id, "case_id": case_id, "strategy": "candidate_region_B_sequential_penalized", **run_result})

        synthetic_pairs = {
            "vehicle_specific_regime_maps": ("region_A", "region_B"),
            "vehicle_specific_with_crossing_proxy": ("region_A_with_crossing", "region_B_with_crossing"),
            "sequential_overlap_reduction": ("region_A", "region_B_sequential_penalized"),
        }
        for strategy, (cand_a, cand_b) in synthetic_pairs.items():
            strategy_vehicle_points[strategy] = {1: candidates[cand_a]["points"], 2: candidates[cand_b]["points"]}
            strategy_vehicle_routes[strategy] = {1: candidates[cand_a]["route"], 2: candidates[cand_b]["route"]}
            strategy_status[strategy] = "POST_SOLVER_PROXY"
            strategy_runtime[strategy] = 0.0
            manifest_rows.append({"run_id": f"{display_case}__2auv_12h__{strategy}", "case_id": case_id, "strategy": strategy, "run_kind": "post_solver_proxy_pair", "status": "POST_SOLVER_PROXY", "run_dir": "", "input_nc": ""})

        pair_score_rows = []
        cand_items = list(candidates.items())
        for name_a, cand_a in cand_items:
            for name_b, cand_b in cand_items:
                if name_a == name_b:
                    continue
                vehicle_points = {1: cand_a["points"], 2: cand_b["points"]}
                tmp_vehicle_rows = [
                    vehicle_metrics("pair_tmp", "post_solver_selected_pair", case_id, 1, cand_a["points"], cand_a["route"], full_maps, full_masks, valid_full, "POST_SOLVER_PROXY"),
                    vehicle_metrics("pair_tmp", "post_solver_selected_pair", case_id, 2, cand_b["points"], cand_b["route"], full_maps, full_masks, valid_full, "POST_SOLVER_PROXY"),
                ]
                tmp_vehicle_df = pd.DataFrame(tmp_vehicle_rows)
                fm = fleet_metrics("pair_tmp", "post_solver_selected_pair", case_id, vehicle_points, tmp_vehicle_df, full_maps, full_masks, valid_full)
                score = pair_score(tmp_vehicle_df.iloc[0], tmp_vehicle_df.iloc[1], fm)
                pair_score_rows.append({"case_id": case_id, "candidate_AUV1": name_a, "candidate_AUV2": name_b, "pair_score": score, **fm})
        pair_score_df = pd.DataFrame(pair_score_rows).sort_values("pair_score", ascending=False)
        pair_rows.extend(pair_score_df.to_dict("records"))
        best_pair = pair_score_df.iloc[0]
        best_a = str(best_pair["candidate_AUV1"])
        best_b = str(best_pair["candidate_AUV2"])
        strategy = "post_solver_selected_pair"
        strategy_vehicle_points[strategy] = {1: candidates[best_a]["points"], 2: candidates[best_b]["points"]}
        strategy_vehicle_routes[strategy] = {1: candidates[best_a]["route"], 2: candidates[best_b]["route"]}
        strategy_status[strategy] = "POST_SOLVER_PROXY"
        strategy_runtime[strategy] = 0.0
        selected_rows.append({"case_id": case_id, "strategy": strategy, "selected_AUV1_candidate": best_a, "selected_AUV2_candidate": best_b, "pair_score": float(best_pair["pair_score"])})
        manifest_rows.append({"run_id": f"{display_case}__2auv_12h__{strategy}", "case_id": case_id, "strategy": strategy, "run_kind": "post_solver_selected_pair", "status": "POST_SOLVER_PROXY", "run_dir": "", "input_nc": ""})

        for strategy, vehicle_points in strategy_vehicle_points.items():
            run_id = f"{display_case}__2auv_12h__{strategy}"
            rows_for_strategy = []
            for vehicle_id, points in sorted(vehicle_points.items()):
                route = strategy_vehicle_routes.get(strategy, {}).get(vehicle_id)
                vm = vehicle_metrics(run_id, strategy, case_id, vehicle_id, points, route, full_maps, full_masks, valid_full, strategy_status.get(strategy, "UNKNOWN"))
                vehicle_rows.append(vm)
                rows_for_strategy.append(vm)
            vehicle_df = pd.DataFrame(rows_for_strategy)
            baseline = baseline_by_case.get(case_id)
            fm = fleet_metrics(run_id, strategy, case_id, vehicle_points, vehicle_df, full_maps, full_masks, valid_full, baseline)
            if strategy == "multi_baseline_STD":
                baseline_by_case[case_id] = {
                    "fleet_region_coverage": fm["fleet_region_coverage"],
                    "trajectory_overlap_ratio": fm["trajectory_overlap_ratio"],
                    "fleet_collected_STD": fm["fleet_collected_STD"],
                    "fleet_collected_boundary": fm["fleet_collected_boundary"],
                }
                fm = fleet_metrics(run_id, strategy, case_id, vehicle_points, vehicle_df, full_maps, full_masks, valid_full, baseline_by_case[case_id])
            fleet_rows.append({**fm, "solver_status": strategy_status.get(strategy, "UNKNOWN"), "solver_runtime": strategy_runtime.get(strategy, 0.0)})

            if case_id == "C01_representative":
                fig_name = f"step11d_{strategy}_overlay.png"
                plot_strategy_overlay(fig_dir / fig_name, f"{display_case} | {strategy}", temp_roi, region_info["region_A_mask"], region_info["region_B_mask"], region_info["boundary_core_mask"], vehicle_points)

    manifest_df = pd.DataFrame(manifest_rows)
    solver_df = pd.DataFrame(solver_rows)
    vehicle_df = pd.DataFrame(vehicle_rows)
    fleet_df = pd.DataFrame(fleet_rows)
    overlap_df = fleet_df[[
        "run_id",
        "strategy",
        "case_id",
        "inter_vehicle_min_distance",
        "inter_vehicle_mean_distance",
        "trajectory_overlap_ratio",
        "duplicate_sampled_cells",
        "shared_top10_cells",
        "decrease_overlap",
    ]].copy()
    candidate_df = pd.DataFrame(candidate_rows)
    pair_df = pd.DataFrame(pair_rows)
    selected_df = pd.DataFrame(selected_rows)

    manifest_df.to_csv(out_dir / "step11d_run_manifest.csv", index=False)
    fleet_df.to_csv(out_dir / "step11d_multi_auv_run_metrics.csv", index=False)
    vehicle_df.to_csv(out_dir / "step11d_vehicle_level_metrics.csv", index=False)
    fleet_df.to_csv(out_dir / "step11d_fleet_level_metrics.csv", index=False)
    overlap_df.to_csv(out_dir / "step11d_overlap_and_separation_metrics.csv", index=False)
    candidate_df.to_csv(out_dir / "step11d_candidate_trajectories.csv", index=False)
    pair_df.to_csv(out_dir / "step11d_pair_selection_scores.csv", index=False)
    selected_df.to_csv(out_dir / "step11d_selected_pair_summary.csv", index=False)
    solver_df.to_csv(out_dir / "step11d_solver_diagnostics.csv", index=False)
    np.savez_compressed(out_dir / "step11d_vehicle_specific_information_maps.npz", **all_info_maps)

    plot_comparison_panel(fleet_df, fig_dir / "step11d_all_strategies_comparison_panel.png")
    plot_distance(fleet_df, fig_dir / "step11d_inter_vehicle_distance_plot.png")
    plot_bar(fleet_df, "fleet_region_coverage", "Fleet regime coverage", fig_dir / "step11d_regime_coverage_barplot.png")
    plot_bar(fleet_df, "trajectory_overlap_ratio", "Trajectory overlap ratio", fig_dir / "step11d_overlap_ratio_barplot.png")
    for fig_path in fig_dir.glob("*.png"):
        shutil.copy2(fig_path, out_dir / fig_path.name)
    if (out_dir / "step11d_regime_masks_and_rewards.png").exists():
        shutil.copy2(out_dir / "step11d_regime_masks_and_rewards.png", fig_dir / "step11d_regime_masks_and_rewards.png")

    failures = int((solver_df["status"].isin(["FAILED", "TIMEOUT"])).sum()) if not solver_df.empty else 0
    if failures:
        verdict = "STEP11D_FAILED"
    elif audit["post_solver_selection_needed"]:
        verdict = "STEP11D_COMPLETED_WITH_POST_SOLVER_SELECTION"
    elif not audit["vehicle_specific_maps_supported"] or not audit["overlap_penalty_supported"]:
        verdict = "STEP11D_COMPLETED_WITH_PROXY_LIMITATION"
    else:
        verdict = "STEP11D_MULTI_AUV_REGIME_SEPARATION_COMPLETED"
    checks = {
        "planned_manifest_rows": int(len(manifest_df)),
        "solver_failures": failures,
        "cases": selected_cases,
        "vehicle_specific_maps_supported": audit["vehicle_specific_maps_supported"],
        "overlap_penalty_supported": audit["overlap_penalty_supported"],
        "post_solver_selection_needed": audit["post_solver_selection_needed"],
        "verdict": verdict,
    }
    write_json(out_dir / "step11d_checks.json", checks)
    write_reports(out_dir, audit, manifest_df, fleet_df, selected_df, verdict)
    shutil.copy2(Path(__file__), out_dir / Path(__file__).name)

    print(f"Output: {out_dir}")
    print(f"Solver failures: {failures}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
