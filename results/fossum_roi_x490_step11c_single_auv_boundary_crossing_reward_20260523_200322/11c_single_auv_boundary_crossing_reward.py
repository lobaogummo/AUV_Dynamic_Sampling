"""Step11C: single-AUV boundary crossing reward proxy.

This step keeps the Lucrezia planner unchanged. The planner exposes a static
node-prize information map, so Step11C audits route-level reward support and
falls back to a simple crossing-aware map proxy when no trajectory objective
hook is available.
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
except Exception:  # pragma: no cover - scipy is expected in this repo env.
    ndi = None


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
SCRIPTS_ROOT = ROOT / "scripts"

DEFAULT_STEP10F = RESULTS_ROOT / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
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


def load_step11a_module():
    path = SCRIPTS_ROOT / "11a_run_minimal_boundary_planner_comparison.py"
    spec = importlib.util.spec_from_file_location("step11a_utils", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import Step11A utilities from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def minmax01(arr: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        out[mask] = 0.0
        return out, {"vmin": float("nan"), "vmax": float("nan")}
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmax - vmin <= 1e-12:
        out[mask] = 0.0
    else:
        out[mask] = ((arr[mask] - vmin) / (vmax - vmin)).astype(np.float32)
    return out, {"vmin": vmin, "vmax": vmax}


def finite_values(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return arr[mask & np.isfinite(arr)]


def load_cases_and_base_maps(step10f: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    cases = pd.read_csv(require(step10f / "step10f_minimal_boundary_planner_cases.csv", "Step10F cases"))
    cases["date"] = pd.to_datetime(cases["date"]).dt.strftime("%Y-%m-%d")
    order = {"C01_representative": 0, "C06_representative": 1, "October_control": 2}
    cases["case_order"] = cases["case_id"].map(order)
    cases = cases.sort_values("case_order").reset_index(drop=True)
    maps = {
        "TEMPpred": np.load(require(step10f / "planner_cases_TEMPpred_roi_x490.npy", "Step10F TEMPpred")).astype(np.float32),
        "STD_norm": np.load(require(step10f / "planner_cases_STD_norm_roi_x490.npy", "Step10F STD_norm")).astype(np.float32),
        "boundary": np.load(require(step10f / "planner_cases_boundary_score_norm_roi_x490.npy", "Step10F boundary")).astype(np.float32),
    }
    return cases, maps


def load_step09b_region_maps(step09b: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    assignments = pd.read_csv(require(step09b / "step09b_classification_assignments.csv", "Step09B assignments"))
    assignments["date"] = pd.to_datetime(assignments["date"]).dt.strftime("%Y-%m-%d")
    maps = {
        "cold_region": np.load(require(step09b / "step09b_assigned_descriptor_cold_region_map.npy", "Step09B cold_region")).astype(np.float32),
        "warm_region": np.load(require(step09b / "step09b_assigned_descriptor_warm_region_map.npy", "Step09B warm_region")).astype(np.float32),
        "boundary": np.load(require(step09b / "step09b_assigned_descriptor_boundary_map.npy", "Step09B boundary")).astype(np.float32),
    }
    return assignments, maps


def audit_planner_route_reward(planner: Path) -> dict[str, Any]:
    optimal = require(planner / "OptimalPlanning.py", "OptimalPlanning.py").read_text(encoding="utf-8", errors="replace")
    utils = require(planner / "Utils.py", "Utils.py").read_text(encoding="utf-8", errors="replace")
    indicators = {
        "uses_static_node_prizes": "get_nodes_prize" in optimal and "prize" in utils.lower(),
        "uses_pyvrp_model_from_data": "Model.from_data" in optimal,
        "route_prize_is_posthoc": "get_routes_prize" in optimal,
        "route_callback_found": any(token in optimal + utils for token in ["route_reward", "trajectory_reward", "callback", "custom_objective"]),
    }
    available = bool(indicators["route_callback_found"])
    return {
        "route_level_crossing_reward_available": available,
        "implementation_mode": "route_level_objective" if available else "map_proxy_static_node_prize",
        "evidence": indicators,
        "conclusion": (
            "Planner appears to support only static node prizes through temperr/get_nodes_prize."
            if not available
            else "Potential route-level hook found; manual validation still required."
        ),
        "limitation": (
            "Crossing reward is implemented as a map proxy; the real A/B crossing is measured after solving."
            if not available
            else "Route-level reward path should be implemented in planner internals before production use."
        ),
    }


def date_to_step09b_idx(assignments: pd.DataFrame, date: str) -> int | None:
    matches = assignments.index[assignments["date"] == date].tolist()
    return int(matches[0]) if matches else None


def connected_largest(mask: np.ndarray) -> np.ndarray:
    if ndi is None or not np.any(mask):
        return mask
    labels, count = ndi.label(mask)
    if count == 0:
        return mask
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def build_region_masks(
    case_id: str,
    case_date: str,
    case_idx: int,
    mask: np.ndarray,
    base_maps: dict[str, np.ndarray],
    step09b_assignments: pd.DataFrame,
    step09b_maps: dict[str, np.ndarray],
) -> dict[str, Any]:
    boundary = base_maps["boundary"][case_idx].astype(np.float32)
    temp = base_maps["TEMPpred"][case_idx].astype(np.float32)
    source = "TEMPpred_median_split"
    cold = np.full(mask.shape, np.nan, dtype=np.float32)
    warm = np.full(mask.shape, np.nan, dtype=np.float32)

    step09b_idx = date_to_step09b_idx(step09b_assignments, case_date)
    if step09b_idx is not None:
        cold = step09b_maps["cold_region"][step09b_idx].astype(np.float32)
        warm = step09b_maps["warm_region"][step09b_idx].astype(np.float32)
        source = "Step09B cold_region_map/warm_region_map"
        region_a = (cold >= warm) & (cold > 0.0) & mask
        region_b = (warm > cold) & (warm > 0.0) & mask
        if int(region_a.sum()) < 10 or int(region_b.sum()) < 10:
            region_a = (cold >= warm) & mask
            region_b = (warm > cold) & mask
    else:
        vals = finite_values(temp, mask)
        thr = float(np.nanmedian(vals)) if vals.size else float("nan")
        region_a = (temp <= thr) & mask & np.isfinite(temp)
        region_b = (temp > thr) & mask & np.isfinite(temp)

    if np.any(region_a & region_b):
        region_b = region_b & ~region_a
    missing = mask & ~(region_a | region_b)
    if np.any(missing):
        vals = finite_values(temp, mask)
        thr = float(np.nanmedian(vals)) if vals.size else float("nan")
        region_a = region_a | (missing & (temp <= thr))
        region_b = region_b | (missing & (temp > thr))

    bvals = finite_values(boundary, mask)
    boundary_thr = float(np.nanpercentile(bvals, 90)) if bvals.size else 1.0
    boundary_core = (boundary >= boundary_thr) & mask & np.isfinite(boundary)
    boundary_core = connected_largest(boundary_core)

    return {
        "case_id": case_id,
        "date": case_date,
        "region_source": source,
        "region_A_label": "cold_or_lower_TEMPpred",
        "region_B_label": "warm_or_higher_TEMPpred",
        "region_A_mask": region_a.astype(bool),
        "region_B_mask": region_b.astype(bool),
        "boundary_core_mask": boundary_core.astype(bool),
        "boundary_core_threshold_p90": boundary_thr,
        "cold_region_map": cold,
        "warm_region_map": warm,
    }


def build_crossing_proxy(boundary: np.ndarray, region_a: np.ndarray, region_b: np.ndarray, boundary_core: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    if ndi is None:
        proxy = np.where(mask, np.nan_to_num(boundary, nan=0.0), np.nan).astype(np.float32)
        return proxy, {"method": "boundary_fallback_no_scipy"}

    dist_to_core = ndi.distance_transform_edt(~boundary_core)
    valid_dist = dist_to_core[mask]
    scale = float(np.nanpercentile(valid_dist, 25)) if valid_dist.size else 5.0
    scale = max(scale, 3.0)
    boundary_proximity = np.exp(-dist_to_core / scale).astype(np.float32)

    side_band = ((region_a | region_b) & (dist_to_core <= max(4.0, scale))).astype(np.float32)
    core = boundary_core.astype(np.float32)
    raw = (0.55 * boundary_proximity + 0.30 * side_band + 0.15 * core).astype(np.float32)
    raw[~mask] = np.nan
    proxy, scale_meta = minmax01(raw, mask)
    return proxy, {
        "method": "near-boundary two-side band proxy",
        "distance_scale_cells": scale,
        "region_A_side_band_cells": int(np.sum(region_a & (dist_to_core <= max(4.0, scale)))),
        "region_B_side_band_cells": int(np.sum(region_b & (dist_to_core <= max(4.0, scale)))),
        **scale_meta,
    }


def make_information_maps(std: np.ndarray, boundary: np.ndarray, crossing_proxy: np.ndarray, mask: np.ndarray) -> dict[str, dict[str, Any]]:
    maps: dict[str, dict[str, Any]] = {}
    baseline = std.copy()
    boundary_only = (0.5 * std + 0.5 * boundary).astype(np.float32)
    maps["baseline_STD"] = {
        "information_map": baseline,
        "formulation": "information_map = STD_norm",
        "gamma": 0.0,
    }
    maps["boundary_alpha050"] = {
        "information_map": boundary_only,
        "formulation": "information_map = 0.5*STD_norm + 0.5*boundary_score_norm",
        "gamma": 0.0,
    }
    for gamma in [0.25, 0.50]:
        gamma_proxy = ((1.0 - gamma) * boundary + gamma * crossing_proxy).astype(np.float32)
        info = (0.5 * std + 0.3 * boundary + 0.2 * gamma_proxy).astype(np.float32)
        info[~mask] = np.nan
        maps[f"crossing_gamma{int(gamma * 100):03d}"] = {
            "information_map": info,
            "formulation": f"information_map = 0.5*STD_norm + 0.3*boundary_score_norm + 0.2*((1-{gamma:.2f})*boundary_score_norm + {gamma:.2f}*crossing_proxy)",
            "gamma": gamma,
        }
    return maps


def labels_along_points(points: list[tuple[int, int]], region_a_full: np.ndarray, region_b_full: np.ndarray) -> list[int]:
    labels = []
    for row, col in points:
        if row < 0 or col < 0 or row >= region_a_full.shape[0] or col >= region_a_full.shape[1]:
            labels.append(0)
        elif bool(region_a_full[row, col]):
            labels.append(1)
        elif bool(region_b_full[row, col]):
            labels.append(2)
        else:
            labels.append(0)
    return labels


def count_region_crossings(labels: list[int]) -> int:
    compressed = []
    for label in labels:
        if label not in (1, 2):
            continue
        if not compressed or compressed[-1] != label:
            compressed.append(label)
    return int(sum(1 for a, b in zip(compressed[:-1], compressed[1:]) if a != b))


def crossing_metrics(
    points: list[tuple[int, int]],
    routes: list[dict[str, Any]],
    region_a_full: np.ndarray,
    region_b_full: np.ndarray,
    boundary_core_full: np.ndarray,
    crossing_proxy_full: np.ndarray,
    baseline_points: set[tuple[int, int]] | None,
) -> dict[str, Any]:
    unique = list(dict.fromkeys(points))
    valid_points = [
        (r, c)
        for r, c in unique
        if 0 <= r < region_a_full.shape[0] and 0 <= c < region_a_full.shape[1] and np.isfinite(crossing_proxy_full[r, c])
    ]
    if not valid_points:
        return {
            "crossing_reward": 0.0,
            "boundary_crossing_count": 0,
            "number_of_distinct_regions_visited": 0,
            "fraction_path_region_A": float("nan"),
            "fraction_path_region_B": float("nan"),
            "fraction_path_boundary_core": float("nan"),
            "difference_from_baseline": float("nan"),
        }
    rr = np.array([p[0] for p in valid_points], dtype=int)
    cc = np.array([p[1] for p in valid_points], dtype=int)
    in_a = region_a_full[rr, cc].astype(bool)
    in_b = region_b_full[rr, cc].astype(bool)
    in_core = boundary_core_full[rr, cc].astype(bool)
    labels = labels_along_points(points, region_a_full, region_b_full)
    crossing_count = count_region_crossings(labels)
    regions_visited = int(bool(np.any(in_a))) + int(bool(np.any(in_b)))
    if baseline_points is None:
        diff = float("nan")
    else:
        point_set = set(valid_points)
        diff = float(1.0 - len(point_set & baseline_points) / max(len(point_set | baseline_points), 1))
    crossing_reward = float((1.0 if regions_visited >= 2 else 0.0) * (1.0 + crossing_count) * np.nanmean(crossing_proxy_full[rr, cc]))
    return {
        "crossing_reward": crossing_reward,
        "boundary_crossing_count": crossing_count,
        "number_of_distinct_regions_visited": regions_visited,
        "fraction_path_region_A": float(np.mean(in_a)),
        "fraction_path_region_B": float(np.mean(in_b)),
        "fraction_path_boundary_core": float(np.mean(in_core)),
        "difference_from_baseline": diff,
    }


def trajectory_length_and_duration(routes: list[dict[str, Any]]) -> tuple[float, float]:
    length = float(np.nansum([r["length_km"] for r in routes])) if routes else float("nan")
    duration = float(np.nansum([(r.get("mission_duration_h") or 0) + (r.get("mission_duration_m") or 0) / 60 for r in routes])) if routes else float("nan")
    return length, duration


def plot_masks(region_info: dict[str, Any], out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), squeeze=False)
    panels = [
        ("region_A", region_info["region_A_mask"], "Blues"),
        ("region_B", region_info["region_B_mask"], "Reds"),
        ("boundary_core", region_info["boundary_core_mask"], "magma"),
    ]
    for ax, (title, arr, cmap) in zip(axes.ravel(), panels):
        im = ax.imshow(arr.astype(float), origin="lower", cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_title(title)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    fig.suptitle(f"{region_info['case_id']} | {region_info['date']} | region masks")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def roi_points(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in points if ROI_ROW_MIN <= r <= ROI_ROW_MAX and ROI_COL_MIN <= c <= ROI_COL_MAX]


def draw_paths(ax: plt.Axes, run_points: dict[str, list[tuple[int, int]]]) -> None:
    colors = {
        "baseline_STD": "white",
        "boundary_alpha050": "#ffea00",
        "crossing_gamma025": "#00e5ff",
        "crossing_gamma050": "#ff4f7b",
        "baseline_STD_6h": "white",
        "boundary_alpha050_6h": "#d7ff4f",
        "crossing_gamma050_6h": "#00ff9d",
    }
    for run_name, points in run_points.items():
        pts = roi_points(points)
        if len(pts) > 1:
            yy = [p[0] for p in pts]
            xx = [p[1] for p in pts]
            ax.plot(xx, yy, color=colors.get(run_name, "black"), linewidth=1.5, marker="o", markersize=2, label=run_name)


def plot_overlay_panel(case_id: str, date: str, backgrounds: list[tuple[str, np.ndarray, str, float | None, float | None]], run_points: dict[str, list[tuple[int, int]]], out_path: Path) -> None:
    fig, axes = plt.subplots(1, len(backgrounds), figsize=(5 * len(backgrounds), 4.4), squeeze=False)
    for ax, (title, arr, cmap, vmin, vmax) in zip(axes.ravel(), backgrounds):
        im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        draw_paths(ax, run_points)
        ax.set_title(title)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    axes.ravel()[0].legend(loc="lower left", fontsize=7)
    fig.suptitle(f"{case_id} | {date}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_region_overlay(region_info: dict[str, Any], run_points: dict[str, list[tuple[int, int]]], out_path: Path) -> None:
    region_rgb = np.zeros((*ROI_SHAPE, 3), dtype=np.float32)
    region_rgb[region_info["region_A_mask"], 2] = 0.85
    region_rgb[region_info["region_B_mask"], 0] = 0.85
    region_rgb[region_info["boundary_core_mask"]] = [1.0, 0.9, 0.1]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.imshow(region_rgb, origin="lower", aspect="auto")
    draw_paths(ax, run_points)
    ax.set_title("Region masks with trajectories")
    ax.axis("off")
    ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_crossing_metrics(metrics_df: pd.DataFrame, out_path: Path) -> None:
    if metrics_df.empty:
        return
    df = metrics_df.copy()
    labels = [f"{r.case_id}\n{r.run_name}" for r in df.itertuples()]
    x = np.arange(len(df))
    width = 0.35
    fig, ax1 = plt.subplots(figsize=(max(10, len(df) * 0.8), 4.8))
    ax1.bar(x - width / 2, df["boundary_crossing_count"].astype(float), width, label="crossing_count")
    ax1.bar(x + width / 2, df["number_of_distinct_regions_visited"].astype(float), width, label="regions_visited")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=90, fontsize=7)
    ax1.set_title("Crossing metrics")
    ax1.grid(axis="y", alpha=0.25)
    ax1.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def write_reports(
    out_dir: Path,
    audit: dict[str, Any],
    manifest_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    crossing_df: pd.DataFrame,
    mask_meta: dict[str, Any],
    verdict: str,
) -> None:
    successful = int((manifest_df["status"] == "SUCCESS").sum()) if not manifest_df.empty else 0
    planned = int(len(manifest_df))
    primary = crossing_df[crossing_df["case_id"] == "C01_representative"].copy() if not crossing_df.empty else pd.DataFrame()
    if primary.empty and not crossing_df.empty:
        primary = crossing_df[crossing_df["case_id"] == str(crossing_df.iloc[0]["case_id"])].copy()
    primary_12h = primary[primary["mission_duration_requested_h"].astype(float) == 12.0] if not primary.empty else pd.DataFrame()
    baseline = primary_12h[primary_12h["run_name"] == "baseline_STD"]
    crossing_best = primary_12h[primary_12h["run_name"].str.startswith("crossing")]

    def metric_line(row: pd.Series) -> str:
        return (
            f"- {row['run_name']}: crossing_count={int(row['boundary_crossing_count'])}, "
            f"regions={int(row['number_of_distinct_regions_visited'])}, "
            f"frac_A={float(row['fraction_path_region_A']):.3f}, frac_B={float(row['fraction_path_region_B']):.3f}, "
            f"diff_baseline={float(row['difference_from_baseline']):.3f}"
        )

    metric_lines = [metric_line(r) for _, r in primary_12h.iterrows()] if not primary_12h.empty else ["- No primary 12h metrics available."]
    if not crossing_best.empty and not baseline.empty:
        base_regions = int(baseline.iloc[0]["number_of_distinct_regions_visited"])
        best_regions = int(crossing_best["number_of_distinct_regions_visited"].max())
        base_cross = int(baseline.iloc[0]["boundary_crossing_count"])
        best_cross = int(crossing_best["boundary_crossing_count"].max())
        increased_regions = best_regions > base_regions
        increased_crossing = best_cross > base_cross
    else:
        increased_regions = False
        increased_crossing = False

    report_lines = [
        "# Step11C Single-AUV Boundary Crossing Reward",
        "",
        f"- Output: `{out_dir}`",
        f"- Runs: {successful}/{planned} successful",
        f"- Planner route-level reward available: `{audit['route_level_crossing_reward_available']}`",
        f"- Implementation mode: `{audit['implementation_mode']}`",
        f"- Mask source: `{mask_meta.get('region_source', 'see masks/ per case')}`",
        f"- Verdict: `{verdict}`",
        "",
        "## Primary 12h Results",
        *metric_lines,
        "",
        "## Questions",
        f"- O crossing reward aumentou o numero de regimes visitados? {'yes' if increased_regions else 'no/unchanged in this run'}.",
        f"- A trajetoria atravessou mais claramente a boundary? {'yes' if increased_crossing else 'no/unchanged by crossing_count'}.",
        "- O efeito foi maior em 6h ou em 12h? Compare `step11c_crossing_metrics.csv`; 6h is included only when `--include-6h` is used.",
        "- O crossing reward mudou a trajetoria mais que boundary_score sozinho? Use `difference_from_baseline` in the crossing metrics table.",
        f"- Isto e implementavel no planner real? `{audit['implementation_mode']}`; currently proxy/diagnostic unless planner objective is extended.",
    ]
    (out_dir / "step11c_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    (out_dir / "step11c_summary.md").write_text("\n".join(report_lines[:18]), encoding="utf-8")
    next_lines = [
        "# Step11C Next Step Recommendation",
        "",
        "- If proxy crossing improves crossings, implement a real route-level objective in the planner by extending the PyVRP model/solver layer or adding a post-optimization route-selection phase.",
        "- If proxy crossing does not improve crossings, test stronger side-band proxy weights before adding a hard constraint.",
        "- Keep Step11D focused on one successful case before generalizing to multiple AUVs.",
    ]
    (out_dir / "step11c_next_step_recommendation.md").write_text("\n".join(next_lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11C single-AUV boundary crossing reward proxy.")
    parser.add_argument("--cases", choices=["primary", "secondary", "all"], default="primary")
    parser.add_argument("--include-6h", action="store_true", help="Also run baseline/boundary/crossing_gamma050 for 6h on the primary case.")
    parser.add_argument("--report-only-output", type=Path, default=None, help="Regenerate reports for an existing Step11C output without rerunning planners.")
    parser.add_argument("--step10f", type=Path, default=DEFAULT_STEP10F)
    parser.add_argument("--step09b", type=Path, default=DEFAULT_STEP09B)
    parser.add_argument("--step10e", type=Path, default=DEFAULT_STEP10E)
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--hres", type=Path, default=DEFAULT_HRES)
    parser.add_argument("--planner", type=Path, default=DEFAULT_PLANNER)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--timeout-s", type=int, default=1800)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.report_only_output is not None:
        out_dir = args.report_only_output.resolve()
        audit = json.loads(require(out_dir / "step11c_planner_route_reward_audit.json", "Step11C planner audit").read_text(encoding="utf-8"))
        manifest_df = pd.read_csv(require(out_dir / "step11c_run_manifest.csv", "Step11C manifest"))
        metrics_df = pd.read_csv(require(out_dir / "step11c_run_metrics.csv", "Step11C metrics"))
        crossing_df = pd.read_csv(require(out_dir / "step11c_crossing_metrics.csv", "Step11C crossing metrics"))
        checks_path = require(out_dir / "step11c_checks.json", "Step11C checks")
        checks = json.loads(checks_path.read_text(encoding="utf-8"))
        write_reports(out_dir, audit, manifest_df, metrics_df, crossing_df, {}, str(checks.get("verdict", "STEP11C_COMPLETED_WITH_PROXY_LIMITATION")))
        print(f"Reports regenerated: {out_dir}")
        return

    s11a = load_step11a_module()
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    for sub in ["planner_inputs", "planner_configs", "planner_runs", "figures", "masks"]:
        (out_dir / sub).mkdir()
    fig_dir = out_dir / "figures"

    mask = np.load(require(args.step00 / "mask_common_roi_x490.npy", "Step00 mask")).astype(bool)
    if mask.shape != ROI_SHAPE or int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected ROI mask: shape={mask.shape}, valid={int(mask.sum())}")
    lat_hres = np.load(require(args.hres / "LAT_hres.npy", "HRes LAT"))
    lon_hres = np.load(require(args.hres / "LON_hres.npy", "HRes LON"))
    bathy_hres = np.load(require(args.hres / "BATHY_hres.npy", "HRes BATHY"))
    cases, base_maps = load_cases_and_base_maps(args.step10f)
    step09b_assignments, step09b_maps = load_step09b_region_maps(args.step09b)
    selected_cases = CASE_ALIASES[args.cases]
    cases = cases[cases["case_id"].isin(selected_cases)].copy().reset_index(drop=True)

    audit = audit_planner_route_reward(args.planner)
    write_json(out_dir / "step11c_planner_route_reward_audit.json", audit)
    audit_md = [
        "# Step11C Planner Route Reward Audit",
        "",
        f"- Route-level crossing reward available: `{audit['route_level_crossing_reward_available']}`",
        f"- Implementation mode: `{audit['implementation_mode']}`",
        f"- Conclusion: {audit['conclusion']}",
        f"- Limitation: {audit['limitation']}",
    ]
    (out_dir / "step11c_planner_route_reward_audit.md").write_text("\n".join(audit_md), encoding="utf-8")

    original_config = s11a.read_config_text(require(args.planner / "Config_file.py", "Lucrezia Config_file.py"))
    runtime_configs = {
        12.0: s11a.generated_config(original_config, single_auv=True, mission_duration_hours=12.0, auv_number=1),
    }
    if args.include_6h:
        runtime_configs[6.0] = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=6.0, auv_number=1)
    for duration, text in runtime_configs.items():
        (out_dir / "planner_configs" / f"Config_file_step11c_1auv_{duration:g}h.py").write_text(text, encoding="utf-8")

    manifest_rows = []
    metrics_rows = []
    crossing_rows = []
    solver_rows = []
    all_info_maps: dict[str, np.ndarray] = {}
    run_points_by_case_duration: dict[tuple[str, float], dict[str, list[tuple[int, int]]]] = {}
    region_info_by_case: dict[str, dict[str, Any]] = {}
    primary_mask_meta: dict[str, Any] = {}

    for _, case in cases.iterrows():
        case_id = str(case["case_id"])
        case_idx = int(case["case_order"])
        case_date = str(case["date"])
        display_case = CASE_DISPLAY.get(case_id, case_id)
        region_info = build_region_masks(case_id, case_date, case_idx, mask, base_maps, step09b_assignments, step09b_maps)
        region_info_by_case[case_id] = region_info
        if case_id == "C01_representative":
            primary_mask_meta = {k: v for k, v in region_info.items() if not isinstance(v, np.ndarray)}
            np.save(out_dir / "region_A_mask.npy", region_info["region_A_mask"])
            np.save(out_dir / "region_B_mask.npy", region_info["region_B_mask"])
            np.save(out_dir / "boundary_core_mask.npy", region_info["boundary_core_mask"])
            plot_masks(region_info, fig_dir / "region_A_B_boundary_masks.png")
        np.save(out_dir / "masks" / f"{safe_name(case_id)}_region_A_mask.npy", region_info["region_A_mask"])
        np.save(out_dir / "masks" / f"{safe_name(case_id)}_region_B_mask.npy", region_info["region_B_mask"])
        np.save(out_dir / "masks" / f"{safe_name(case_id)}_boundary_core_mask.npy", region_info["boundary_core_mask"])

        std_roi = base_maps["STD_norm"][case_idx].astype(np.float32)
        boundary_roi = base_maps["boundary"][case_idx].astype(np.float32)
        temp_roi = base_maps["TEMPpred"][case_idx].astype(np.float32)
        crossing_proxy, proxy_meta = build_crossing_proxy(
            boundary_roi,
            region_info["region_A_mask"],
            region_info["region_B_mask"],
            region_info["boundary_core_mask"],
            mask,
        )
        info_specs = make_information_maps(std_roi, boundary_roi, crossing_proxy, mask)
        for run_name, spec in info_specs.items():
            all_info_maps[f"{case_id}__{run_name}"] = spec["information_map"]
        all_info_maps[f"{case_id}__crossing_proxy"] = crossing_proxy

        durations = [12.0]
        if args.include_6h and case_id == "C01_representative":
            durations.append(6.0)
        for duration in durations:
            run_names = ["baseline_STD", "boundary_alpha050", "crossing_gamma025", "crossing_gamma050"]
            if duration == 6.0:
                run_names = ["baseline_STD", "boundary_alpha050", "crossing_gamma050"]
            baseline_points: set[tuple[int, int]] | None = None
            run_points_by_case_duration[(case_id, duration)] = {}
            for run_name_base in run_names:
                run_name = run_name_base if duration == 12.0 else f"{run_name_base}_6h"
                spec = info_specs[run_name_base]
                info_roi = spec["information_map"].astype(np.float32)
                run_id = f"{display_case}__1auv_{duration:g}h__{run_name}"
                run_dir = out_dir / "planner_runs" / safe_name(run_id)
                run_dir.mkdir(parents=True, exist_ok=True)
                input_nc = out_dir / "planner_inputs" / f"{safe_name(run_id)}_planner_interface.nc"
                nc_meta = s11a.build_interface_nc(input_nc, info_roi, mask, lat_hres, lon_hres, bathy_hres)
                shutil.copy2(input_nc, run_dir / input_nc.name)
                s11a.copy_planner_runtime(args.planner, run_dir, runtime_configs[duration])
                write_json(
                    run_dir / "run_config.json",
                    {
                        "run_id": run_id,
                        "case_id": case_id,
                        "display_case": display_case,
                        "date": case_date,
                        "run_name": run_name,
                        "base_run_name": run_name_base,
                        "mission_duration_requested_h": duration,
                        "auv_number": 1,
                        "formulation": spec["formulation"],
                        "gamma": spec["gamma"],
                        "route_level_reward_available": audit["route_level_crossing_reward_available"],
                        "proxy_meta": proxy_meta,
                    },
                )
                status = "NOT_RUN"
                error = ""
                try:
                    run_result = s11a.run_planner(run_dir, input_nc, args.timeout_s)
                    status = "SUCCESS" if run_result["returncode"] == 0 and (run_dir / "routes_file.txt").exists() else "FAILED"
                except subprocess.TimeoutExpired as exc:
                    run_result = {"command": " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd), "returncode": -999, "runtime_s": args.timeout_s}
                    status = "TIMEOUT"
                    error = f"Timeout after {args.timeout_s}s"
                    (run_dir / "planner_stdout.txt").write_text(exc.stdout or "", encoding="utf-8", errors="replace")
                    (run_dir / "planner_stderr.txt").write_text((exc.stderr or "") + "\n" + error, encoding="utf-8", errors="replace")
                except Exception as exc:
                    run_result = {"command": f"{sys.executable} OptimalPlanning.py {input_nc}", "returncode": -998, "runtime_s": float("nan")}
                    status = "FAILED"
                    error = repr(exc)
                    (run_dir / "planner_stderr.txt").write_text(error, encoding="utf-8", errors="replace")

                routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
                s11a.save_trajectory_csv_json(run_dir, routes)
                points = s11a.route_grid_points(routes, lat_hres, lon_hres)
                run_points_by_case_duration[(case_id, duration)][run_name] = points

                info_full = s11a.embed_roi_to_hres(info_roi, mask, fill=np.nan)
                std_full = s11a.embed_roi_to_hres(std_roi, mask, fill=np.nan)
                boundary_full = s11a.embed_roi_to_hres(boundary_roi, mask, fill=np.nan)
                region_a_full = s11a.embed_roi_to_hres(region_info["region_A_mask"].astype(float), mask, fill=np.nan) > 0.5
                region_b_full = s11a.embed_roi_to_hres(region_info["region_B_mask"].astype(float), mask, fill=np.nan) > 0.5
                boundary_core_full = s11a.embed_roi_to_hres(region_info["boundary_core_mask"].astype(float), mask, fill=np.nan) > 0.5
                crossing_proxy_full = s11a.embed_roi_to_hres(crossing_proxy, mask, fill=np.nan)
                base_for_metrics = baseline_points
                path_metrics = s11a.path_metrics(routes, lat_hres, lon_hres, info_full, std_full, boundary_full, base_for_metrics)
                if run_name_base == "baseline_STD":
                    baseline_points = set(points)
                    path_metrics["trajectory_overlap_ratio_with_baseline"] = 1.0 if points else float("nan")
                    path_metrics["trajectory_difference_from_baseline"] = 0.0 if points else float("nan")
                cross = crossing_metrics(points, routes, region_a_full, region_b_full, boundary_core_full, crossing_proxy_full, baseline_points)
                length, mission_duration = trajectory_length_and_duration(routes)
                constraints_satisfied = bool(status == "SUCCESS" and len(routes) > 0 and np.isfinite(length))

                common = {
                    "run_id": run_id,
                    "case_id": case_id,
                    "display_case": display_case,
                    "date": case_date,
                    "run_name": run_name,
                    "base_run_name": run_name_base,
                    "mission_duration_requested_h": duration,
                    "mission_duration": mission_duration,
                    "trajectory_length": length,
                    "solver_runtime": run_result["runtime_s"],
                    "solver_status": status,
                    "constraints_satisfied": constraints_satisfied,
                    "gamma": spec["gamma"],
                    "formulation": spec["formulation"],
                    "route_level_reward_available": audit["route_level_crossing_reward_available"],
                }
                manifest_rows.append(
                    {
                        **common,
                        "input_nc": str(input_nc),
                        "run_dir": str(run_dir),
                        "status": status,
                        "returncode": run_result["returncode"],
                    }
                )
                metrics_rows.append({**common, **path_metrics, **cross})
                crossing_rows.append({**common, **cross})
                solver_rows.append(
                    {
                        "run_id": run_id,
                        "case_id": case_id,
                        "run_name": run_name,
                        "status": status,
                        "returncode": run_result["returncode"],
                        "runtime_s": run_result["runtime_s"],
                        "command": run_result["command"],
                        "error": error,
                        **nc_meta,
                    }
                )

        if case_id == "C01_representative":
            primary_points = run_points_by_case_duration.get((case_id, 12.0), {})
            plot_overlay_panel(
                display_case,
                case_date,
                [
                    ("TEMPpred", temp_roi, "coolwarm", None, None),
                    ("STD_norm", std_roi, "viridis", 0, 1),
                    ("boundary_score_norm", boundary_roi, "magma", 0, 1),
                ],
                primary_points,
                fig_dir / "baseline_vs_boundary_vs_crossing_overlay.png",
            )
            plot_overlay_panel(display_case, case_date, [("TEMPpred", temp_roi, "coolwarm", None, None)], primary_points, fig_dir / "trajectory_over_TEMPpred.png")
            plot_overlay_panel(display_case, case_date, [("STD_norm", std_roi, "viridis", 0, 1)], primary_points, fig_dir / "trajectory_over_STD.png")
            plot_overlay_panel(display_case, case_date, [("boundary_score_norm", boundary_roi, "magma", 0, 1)], primary_points, fig_dir / "trajectory_over_boundary.png")
            plot_region_overlay(region_info, primary_points, fig_dir / "trajectory_over_region_masks.png")

    manifest_df = pd.DataFrame(manifest_rows)
    metrics_df = pd.DataFrame(metrics_rows)
    crossing_df = pd.DataFrame(crossing_rows)
    solver_df = pd.DataFrame(solver_rows)
    manifest_df.to_csv(out_dir / "step11c_run_manifest.csv", index=False)
    metrics_df.to_csv(out_dir / "step11c_run_metrics.csv", index=False)
    crossing_df.to_csv(out_dir / "step11c_crossing_metrics.csv", index=False)
    solver_df.to_csv(out_dir / "step11c_solver_diagnostics.csv", index=False)
    np.savez_compressed(out_dir / "step11c_crossing_information_maps.npz", **all_info_maps)
    plot_crossing_metrics(crossing_df, fig_dir / "crossing_metrics_barplot.png")
    for fig_path in fig_dir.glob("*.png"):
        shutil.copy2(fig_path, out_dir / fig_path.name)

    failed = int((manifest_df["status"] != "SUCCESS").sum()) if not manifest_df.empty else 1
    if failed:
        verdict = "STEP11C_FAILED"
    elif audit["route_level_crossing_reward_available"]:
        verdict = "STEP11C_SINGLE_AUV_CROSSING_REWARD_COMPLETED"
    else:
        verdict = "STEP11C_COMPLETED_WITH_PROXY_LIMITATION"
    checks = {
        "planned_runs": int(len(manifest_df)),
        "successful_runs": int((manifest_df["status"] == "SUCCESS").sum()) if not manifest_df.empty else 0,
        "failed_runs": failed,
        "cases": selected_cases,
        "include_6h": bool(args.include_6h),
        "route_level_crossing_reward_available": audit["route_level_crossing_reward_available"],
        "implementation_mode": audit["implementation_mode"],
        "verdict": verdict,
    }
    write_json(out_dir / "step11c_checks.json", checks)
    write_reports(out_dir, audit, manifest_df, metrics_df, crossing_df, primary_mask_meta, verdict)

    print(f"Output: {out_dir}")
    print(f"Runs successful: {checks['successful_runs']}/{checks['planned_runs']}")
    print(f"Route-level reward available: {audit['route_level_crossing_reward_available']}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
