#!/usr/bin/env python
"""
Step11Z minimal prototype-based planner rerun.

Runs a small, explicit rerun using only Step11Y prototype-based arrays:
- Single-AUV 12h: baseline_STD, prototype_boundary_alpha050,
  prototype_crossing_gamma025.
- Multi-AUV 12h: native shared baseline_STD and proxy vehicle-specific pairs
  using AUV1/AUV2 prototype maps.

The planner does not support vehicle-specific node prizes in one native solve,
so vehicle-specific multi-AUV strategies are implemented as an explicit proxy:
two independent 1-AUV solves combined into fleet metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = ""

try:
    from scipy import ndimage as ndi
except Exception:  # pragma: no cover
    ndi = None


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCRIPTS = ROOT / "scripts"
PLANNER = ROOT / "OptimalPlanning_Lucrezia"
HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
STEP10F = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
OLD_STEP11C = [
    RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322",
    RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458",
]
OLD_STEP11D = [
    RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809",
    RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935",
]

CASE_ORDER = ["C01_representative", "C06_representative", "October_control"]
CASE_DISPLAY = {
    "C01_representative": "C01 representative",
    "C06_representative": "C06 representative",
    "October_control": "October reference",
}


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def latest_step11y() -> Path:
    candidates = sorted(
        RESULTS.glob("fossum_roi_x490_step11y_prototype_based_planner_input_audit_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No Step11Y prototype-based audit output found.")
    return candidates[0]


def minmax01(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    valid = mask & np.isfinite(a)
    out = np.full(a.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return out
    mn = float(np.nanmin(a[valid]))
    mx = float(np.nanmax(a[valid]))
    if mx <= mn:
        out[valid] = 0.0
    else:
        out[valid] = (a[valid] - mn) / (mx - mn)
    return out


def connected_largest(mask: np.ndarray) -> np.ndarray:
    if ndi is None or not np.any(mask):
        return mask.astype(bool)
    labels, count = ndi.label(mask)
    if count == 0:
        return mask.astype(bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def boundary_core(boundary: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = boundary[mask & np.isfinite(boundary)]
    if vals.size == 0:
        return np.zeros(boundary.shape, dtype=bool)
    thr = float(np.nanpercentile(vals, 90))
    return connected_largest((boundary >= thr) & mask & np.isfinite(boundary))


def region_masks(cold: np.ndarray, warm: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(cold, dtype=np.float32)
    b = np.asarray(warm, dtype=np.float32)
    region_a = (a >= b) & mask & np.isfinite(a) & np.isfinite(b)
    region_b = (b > a) & mask & np.isfinite(a) & np.isfinite(b)
    missing = mask & ~(region_a | region_b)
    if np.any(missing):
        region_a |= missing & (np.nan_to_num(a, nan=-1) >= np.nan_to_num(b, nan=-1))
        region_b |= missing & ~region_a
    return region_a.astype(bool), region_b.astype(bool)


def safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)


def short_name(run_id: str, max_prefix: int = 42) -> str:
    prefix = safe_name(run_id)[:max_prefix].rstrip("_-.")
    digest = hashlib.sha1(run_id.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}__{digest}"


def route_points(s11a, routes: list[dict[str, Any]], lat_hres: np.ndarray, lon_hres: np.ndarray) -> list[tuple[int, int]]:
    return s11a.route_grid_points(routes, lat_hres, lon_hres)


def valid_unique(points: list[tuple[int, int]], valid_full: np.ndarray) -> list[tuple[int, int]]:
    seen: dict[tuple[int, int], None] = {}
    for r, c in points:
        if 0 <= r < valid_full.shape[0] and 0 <= c < valid_full.shape[1] and bool(valid_full[r, c]):
            seen[(r, c)] = None
    return list(seen.keys())


def sample_values(points: list[tuple[int, int]], arr: np.ndarray, valid_full: np.ndarray) -> np.ndarray:
    pts = valid_unique(points, valid_full)
    if not pts:
        return np.array([], dtype=float)
    rr = np.array([p[0] for p in pts], dtype=int)
    cc = np.array([p[1] for p in pts], dtype=int)
    vals = arr[rr, cc]
    return vals[np.isfinite(vals)]


def load_cases_and_maps(step11y: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    z = np.load(step11y / "prototype_based_all_planner_maps.npz", allow_pickle=True)
    cases = pd.DataFrame(
        {
            "case_id": [str(x) for x in z["case_ids"]],
            "date": [str(x) for x in z["dates"]],
            "predicted_class": z["predicted_classes"].astype(int),
        }
    )
    cases["display_case"] = cases["case_id"].map(CASE_DISPLAY).fillna(cases["case_id"])
    cases["case_order"] = cases["case_id"].map({case: i for i, case in enumerate(CASE_ORDER)})
    cases = cases.sort_values("case_order").reset_index(drop=True)
    maps = {k: np.asarray(z[k], dtype=np.float32) for k in z.files if k not in ["case_ids", "dates", "predicted_classes"]}
    return cases, maps


def load_step10f_temp_and_mask() -> tuple[np.ndarray, np.ndarray]:
    z = np.load(STEP10F / "planner_minimal_boundary_input_maps.npz", allow_pickle=True)
    return np.asarray(z["TEMPpred"], dtype=np.float32), np.asarray(z["mask"], dtype=bool)


def run_planner_case(
    s11a,
    run_id: str,
    info_roi: np.ndarray,
    mask: np.ndarray,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    bathy_hres: np.ndarray,
    planner: Path,
    config_text: str,
    outdir: Path,
    timeout_s: int,
    skip_existing: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    physical_name = short_name(run_id)
    run_dir = outdir / "planner_runs" / physical_name
    input_nc = outdir / "planner_inputs" / f"{physical_name}.nc"
    run_dir.mkdir(parents=True, exist_ok=True)

    if skip_existing and (run_dir / "routes_file.txt").exists():
        routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
        return (
            {
                "run_id": run_id,
                "command": "REUSED_EXISTING",
                "returncode": 0,
                "runtime_s": 0.0,
                "status": "REUSED",
                "error": "",
                "input_nc": str(input_nc),
            },
            routes,
            run_dir,
        )

    nc_meta = s11a.build_interface_nc(input_nc, info_roi, mask, lat_hres, lon_hres, bathy_hres)
    shutil.copy2(input_nc, run_dir / input_nc.name)
    s11a.copy_planner_runtime(planner, run_dir, config_text)
    error = ""
    try:
        result = s11a.run_planner(run_dir, input_nc, timeout_s)
        status = "SUCCESS" if result["returncode"] == 0 and (run_dir / "routes_file.txt").exists() else "FAILED"
    except subprocess.TimeoutExpired as exc:
        result = {"command": " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd), "returncode": -999, "runtime_s": timeout_s}
        status = "TIMEOUT"
        error = f"Timeout after {timeout_s}s"
    except Exception as exc:
        result = {"command": f"{sys.executable} OptimalPlanning.py {input_nc}", "returncode": -998, "runtime_s": float("nan")}
        status = "FAILED"
        error = repr(exc)
        (run_dir / "planner_stderr.txt").write_text(error, encoding="utf-8")
    routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
    s11a.save_trajectory_csv_json(run_dir, routes)
    return ({**result, **nc_meta, "run_id": run_id, "status": status, "error": error, "input_nc": str(input_nc)}, routes, run_dir)


def vehicle_metrics(
    run_id: str,
    strategy: str,
    case_id: str,
    vehicle_id: int,
    points: list[tuple[int, int]],
    route: dict[str, Any] | None,
    maps_full: dict[str, np.ndarray],
    masks_full: dict[str, np.ndarray],
    valid_full: np.ndarray,
    solver_status: str,
) -> dict[str, Any]:
    pts = valid_unique(points, valid_full)
    labels = []
    for p in points:
        r, c = p
        if 0 <= r < valid_full.shape[0] and 0 <= c < valid_full.shape[1] and bool(valid_full[r, c]):
            if bool(masks_full["region_A_full"][r, c]):
                labels.append(1)
            elif bool(masks_full["region_B_full"][r, c]):
                labels.append(2)
    compressed = []
    for label in labels:
        if not compressed or compressed[-1] != label:
            compressed.append(label)
    crossing_count = int(sum(1 for a, b in zip(compressed[:-1], compressed[1:]) if a != b))

    in_a = sample_values(pts, masks_full["region_A_full"].astype(np.float32), valid_full)
    in_b = sample_values(pts, masks_full["region_B_full"].astype(np.float32), valid_full)
    in_core = sample_values(pts, masks_full["boundary_core_full"].astype(np.float32), valid_full)
    length = float(route.get("length_km", float("nan"))) if route else float("nan")
    duration = float((route.get("mission_duration_h") or 0) + (route.get("mission_duration_m") or 0) / 60) if route else float("nan")
    return {
        "run_id": run_id,
        "strategy": strategy,
        "case_id": case_id,
        "vehicle_id": vehicle_id,
        "solver_status": solver_status,
        "collected_STD": float(np.nansum(sample_values(pts, maps_full["STD_full"], valid_full))),
        "collected_boundary": float(np.nansum(sample_values(pts, maps_full["boundary_full"], valid_full))),
        "collected_region_A": float(np.nansum(in_a)),
        "collected_region_B": float(np.nansum(in_b)),
        "fraction_path_region_A": float(np.nanmean(in_a)) if in_a.size else float("nan"),
        "fraction_path_region_B": float(np.nanmean(in_b)) if in_b.size else float("nan"),
        "fraction_path_boundary_core": float(np.nanmean(in_core)) if in_core.size else float("nan"),
        "crossing_count": crossing_count,
        "regions_visited": int(bool(np.any(in_a > 0.5))) + int(bool(np.any(in_b > 0.5))),
        "trajectory_length": length,
        "mission_duration": duration,
        "sampled_cells": int(len(pts)),
    }


def pair_distance(points_a: list[tuple[int, int]], points_b: list[tuple[int, int]], valid_full: np.ndarray) -> dict[str, float]:
    a = np.asarray(valid_unique(points_a, valid_full), dtype=float)
    b = np.asarray(valid_unique(points_b, valid_full), dtype=float)
    if a.size == 0 or b.size == 0:
        return {"inter_vehicle_min_distance": float("nan"), "inter_vehicle_mean_distance": float("nan")}
    a = a if len(a) <= 400 else a[np.linspace(0, len(a) - 1, 400).astype(int)]
    b = b if len(b) <= 400 else b[np.linspace(0, len(b) - 1, 400).astype(int)]
    d = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2))
    return {"inter_vehicle_min_distance": float(np.min(d)), "inter_vehicle_mean_distance": float(np.mean(np.min(d, axis=1)))}


def fleet_metrics(
    run_id: str,
    strategy: str,
    case_id: str,
    vehicle_points: dict[int, list[tuple[int, int]]],
    vehicle_df: pd.DataFrame,
    masks_full: dict[str, np.ndarray],
    valid_full: np.ndarray,
    solver_status: str,
    solver_runtime: float,
) -> dict[str, Any]:
    ids = sorted(vehicle_points)
    set_a = set(valid_unique(vehicle_points.get(ids[0], []) if ids else [], valid_full))
    set_b = set(valid_unique(vehicle_points.get(ids[1], []) if len(ids) > 1 else [], valid_full))
    union = set_a | set_b
    inter = set_a & set_b
    region_a_cells = set(zip(*np.where(masks_full["region_A_full"] & valid_full)))
    region_b_cells = set(zip(*np.where(masks_full["region_B_full"] & valid_full)))
    overlap = float(len(inter) / max(len(union), 1))
    cov_a = float(len(union & region_a_cells) / max(len(region_a_cells), 1))
    cov_b = float(len(union & region_b_cells) / max(len(region_b_cells), 1))
    dist = pair_distance(list(set_a), list(set_b), valid_full)
    return {
        "run_id": run_id,
        "strategy": strategy,
        "case_id": case_id,
        "fleet_collected_STD": float(vehicle_df["collected_STD"].sum()) if not vehicle_df.empty else 0.0,
        "fleet_collected_boundary": float(vehicle_df["collected_boundary"].sum()) if not vehicle_df.empty else 0.0,
        "fleet_region_A_coverage": cov_a,
        "fleet_region_B_coverage": cov_b,
        "fleet_region_coverage": cov_a + cov_b,
        "trajectory_overlap_ratio": overlap,
        "duplicate_sampled_cells": int(len(inter)),
        "inter_vehicle_min_distance": dist["inter_vehicle_min_distance"],
        "inter_vehicle_mean_distance": dist["inter_vehicle_mean_distance"],
        "complementarity_score": float(0.5 * (cov_a + cov_b) + 0.5 * (1.0 - overlap)),
        "fleet_total_area_covered": int(len(union)),
        "solver_status": solver_status,
        "solver_runtime": solver_runtime,
    }


def load_old_metrics() -> tuple[pd.DataFrame, pd.DataFrame]:
    single = []
    for d in OLD_STEP11C:
        p = d / "step11c_run_metrics.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["old_source_output"] = d.name
            single.append(df)
    multi = []
    for d in OLD_STEP11D:
        p = d / "step11d_fleet_level_metrics.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["old_source_output"] = d.name
            multi.append(df)
    return (
        pd.concat(single, ignore_index=True) if single else pd.DataFrame(),
        pd.concat(multi, ignore_index=True) if multi else pd.DataFrame(),
    )


def compare_old_new(single_new: pd.DataFrame, multi_new: pd.DataFrame) -> pd.DataFrame:
    old_single, old_multi = load_old_metrics()
    rows = []
    if not old_single.empty and not single_new.empty:
        old_single = old_single.rename(columns={"boundary_crossing_count": "crossing_count", "number_of_distinct_regions_visited": "regions_visited"})
        old_single["canonical_strategy"] = old_single["run_name"].replace(
            {
                "boundary_alpha050": "prototype_boundary_alpha050",
                "crossing_gamma025": "prototype_crossing_gamma025",
                "baseline_STD": "baseline_STD",
            }
        )
        for _, new in single_new.iterrows():
            old = old_single[(old_single["case_id"].astype(str) == str(new["case_id"])) & (old_single["canonical_strategy"].astype(str) == str(new["run_name"]))]
            if old.empty:
                continue
            old = old.iloc[0]
            rows.append(
                {
                    "scope": "single_AUV",
                    "case_id": new["case_id"],
                    "strategy": new["run_name"],
                    "old_source_output": old.get("old_source_output", ""),
                    "old_crossing_count": old.get("crossing_count", np.nan),
                    "new_crossing_count": new.get("crossing_count", np.nan),
                    "delta_crossing_count": float(new.get("crossing_count", np.nan)) - float(old.get("crossing_count", np.nan)),
                    "old_regions_visited": old.get("regions_visited", np.nan),
                    "new_regions_visited": new.get("regions_visited", np.nan),
                    "old_collected_STD": old.get("collected_STD_score", np.nan),
                    "new_collected_STD": new.get("collected_STD", np.nan),
                    "old_collected_boundary": old.get("collected_boundary_score", np.nan),
                    "new_collected_boundary": new.get("collected_boundary", np.nan),
                }
            )
    if not old_multi.empty and not multi_new.empty:
        old_multi["canonical_strategy"] = old_multi["strategy"].replace(
            {
                "multi_baseline_STD": "baseline_STD",
                "vehicle_specific_regime_maps": "prototype_vehicle_specific_maps",
                "vehicle_specific_with_crossing_proxy": "prototype_vehicle_specific_with_boundary",
            }
        )
        for _, new in multi_new.iterrows():
            old = old_multi[(old_multi["case_id"].astype(str) == str(new["case_id"])) & (old_multi["canonical_strategy"].astype(str) == str(new["strategy"]))]
            if old.empty:
                continue
            old = old.iloc[0]
            rows.append(
                {
                    "scope": "multi_AUV",
                    "case_id": new["case_id"],
                    "strategy": new["strategy"],
                    "old_source_output": old.get("old_source_output", ""),
                    "old_fleet_region_A_coverage": old.get("fleet_region_A_coverage", np.nan),
                    "new_fleet_region_A_coverage": new.get("fleet_region_A_coverage", np.nan),
                    "old_fleet_region_B_coverage": old.get("fleet_region_B_coverage", np.nan),
                    "new_fleet_region_B_coverage": new.get("fleet_region_B_coverage", np.nan),
                    "old_overlap": old.get("trajectory_overlap_ratio", np.nan),
                    "new_overlap": new.get("trajectory_overlap_ratio", np.nan),
                    "old_complementarity": old.get("fleet_complementarity_score", np.nan),
                    "new_complementarity": new.get("complementarity_score", np.nan),
                }
            )
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 30, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_No data available._\n"
    d = df[[c for c in cols if c in df.columns]].head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
        else:
            d[c] = d[c].fillna("").astype(str)
    lines = [
        "| " + " | ".join(d.columns) + " |",
        "| " + " | ".join("---" for _ in d.columns) + " |",
    ]
    for row in d.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines) + "\n"


def plot_panels(outdir: Path, temp: np.ndarray, cases: pd.DataFrame, single_df: pd.DataFrame, multi_df: pd.DataFrame, route_points_by_run: dict[str, dict[str, list[tuple[int, int]]]]) -> None:
    if plt is None:
        return
    figdir = outdir / "figures"
    cmap = {"baseline_STD": "white", "prototype_boundary_alpha050": "gold", "prototype_crossing_gamma025": "cyan"}
    fig, axes = plt.subplots(1, len(cases), figsize=(14, 4))
    for ax, (_, case) in zip(axes, cases.iterrows()):
        case_id = case["case_id"]
        idx = int(case["case_order"])
        ax.imshow(temp[idx], origin="lower", aspect="auto", cmap="coolwarm")
        for strategy, color in cmap.items():
            key = f"{case_id}__single__{strategy}"
            pts = route_points_by_run.get(key, {}).get("all", [])
            if pts:
                rr = [p[0] - 279 for p in pts]
                cc = [p[1] - 312 for p in pts]
                ax.plot(cc, rr, color=color, lw=1, label=strategy)
        ax.set_title(case_id)
        ax.set_xticks([])
        ax.set_yticks([])
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figdir / "prototype_based_single_AUV_comparison_panel.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(cases), figsize=(14, 4))
    colors = {1: "lime", 2: "magenta"}
    for ax, (_, case) in zip(axes, cases.iterrows()):
        case_id = case["case_id"]
        idx = int(case["case_order"])
        ax.imshow(temp[idx], origin="lower", aspect="auto", cmap="coolwarm")
        key = f"{case_id}__multi__prototype_vehicle_specific_maps"
        for vid, pts in route_points_by_run.get(key, {}).items():
            if pts:
                rr = [p[0] - 279 for p in pts]
                cc = [p[1] - 312 for p in pts]
                ax.plot(cc, rr, color=colors.get(vid, "white"), lw=1, label=f"AUV{vid}")
        ax.set_title(case_id)
        ax.set_xticks([])
        ax.set_yticks([])
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figdir / "prototype_based_multi_AUV_comparison_panel.png", dpi=180)
    plt.close(fig)

    for case_id, filename in [
        ("October_control", "October_old_vs_prototype_based_comparison.png"),
        ("C01_representative", "C01_old_vs_prototype_based_comparison.png"),
        ("C06_representative", "C06_old_vs_prototype_based_comparison.png"),
    ]:
        comp = single_df[single_df["case_id"].eq(case_id)]
        fig, ax = plt.subplots(figsize=(6, 4))
        if not comp.empty:
            ax.bar(comp["run_name"], comp["crossing_count"].astype(float), color=["gray", "gold", "cyan"][: len(comp)])
        ax.set_title(f"{case_id}: prototype rerun crossing count")
        ax.tick_params(axis="x", rotation=25)
        fig.tight_layout()
        fig.savefig(figdir / filename, dpi=180)
        plt.close(fig)


def write_reports(outdir: Path, single_df: pd.DataFrame, multi_df: pd.DataFrame, comparison: pd.DataFrame, checks: dict[str, Any], warnings: list[str]) -> None:
    october_comp = comparison[comparison["case_id"].eq("October_control")]
    lines = [
        "# Step11Z minimal prototype-based rerun",
        "",
        f"- Verdict: `{checks['verdict']}`",
        f"- Cases rerun: {', '.join(checks['cases_rerun'])}",
        f"- Single-AUV rows: {len(single_df)}",
        f"- Multi-AUV rows: {len(multi_df)}",
        f"- Warnings: {len(warnings)}",
        "",
        "## Single-AUV metrics",
        md_table(single_df, ["case_id", "run_name", "solver_status", "crossing_count", "regions_visited", "fraction_path_region_A", "fraction_path_region_B", "collected_STD", "collected_boundary", "trajectory_length", "solver_runtime"], 30),
        "",
        "## Multi-AUV metrics",
        md_table(multi_df, ["case_id", "strategy", "solver_status", "fleet_region_A_coverage", "fleet_region_B_coverage", "trajectory_overlap_ratio", "inter_vehicle_mean_distance", "complementarity_score", "fleet_collected_STD", "fleet_collected_boundary"], 30),
        "",
        "## Old vs new",
        md_table(comparison, list(comparison.columns), 60),
        "",
        "## October focus",
        md_table(october_comp, list(october_comp.columns), 20),
    ]
    text = "\n".join(lines)
    write_text(outdir / "step11z_summary.md", text)
    write_text(outdir / "step11z_report.md", text)
    next_lines = [
        "# Step11Z next step recommendation",
        "",
        f"Verdict: `{checks['verdict']}`",
        "",
        "- Use these prototype-based results as the corrected evidence for Step11E.",
        "- If October changed materially, treat old October Step11C/Step11D as exploratory only.",
        "- Next implementation priority remains native vehicle-specific prize maps if the proxy pair is promising.",
    ]
    if warnings:
        next_lines += ["", "## Warnings"] + [f"- {w}" for w in warnings]
    write_text(outdir / "step11z_next_step_recommendation.md", "\n".join(next_lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11Z minimal prototype-based planner rerun.")
    parser.add_argument("--step11y", type=Path, default=None)
    parser.add_argument("--planner", type=Path, default=PLANNER)
    parser.add_argument("--output-root", type=Path, default=RESULTS)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--cases", choices=["all", "C01_representative", "C06_representative", "October_control"], default="all")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--no-optional-boundary", action="store_true")
    parser.add_argument("--resume-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    s11a = load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")
    s11c = load_module("step11c_utils", SCRIPTS / "11c_single_auv_boundary_crossing_reward.py")
    step11y = args.step11y.resolve() if args.step11y else latest_step11y().resolve()

    outdir = args.resume_output.resolve() if args.resume_output else args.output_root.resolve() / f"fossum_roi_x490_step11z_minimal_prototype_based_rerun_{now_tag()}"
    outdir.mkdir(parents=True, exist_ok=True)
    for sub in ["planner_inputs", "planner_runs", "planner_configs", "figures", "masks"]:
        (outdir / sub).mkdir(exist_ok=True)

    cases, maps = load_cases_and_maps(step11y)
    if args.cases != "all":
        cases = cases[cases["case_id"].eq(args.cases)].copy().reset_index(drop=True)
    temp, mask = load_step10f_temp_and_mask()
    lat_hres = np.load(HRES / "LAT_hres.npy")
    lon_hres = np.load(HRES / "LON_hres.npy")
    bathy_hres = np.load(HRES / "BATHY_hres.npy")
    valid_full = s11a.embed_roi_to_hres(mask.astype(np.float32), mask, fill=np.nan) > 0.5

    original_config = s11a.read_config_text(args.planner / "Config_file.py")
    config_1auv = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=12.0, auv_number=1)
    config_2auv = s11a.generated_config(original_config, single_auv=False, mission_duration_hours=12.0, auv_number=2)
    (outdir / "planner_configs" / "Config_file_step11z_1auv_12h.py").write_text(config_1auv, encoding="utf-8")
    (outdir / "planner_configs" / "Config_file_step11z_2auv_12h.py").write_text(config_2auv, encoding="utf-8")

    manifest_rows: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    single_rows: list[dict[str, Any]] = []
    vehicle_rows: list[dict[str, Any]] = []
    multi_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    route_points_by_run: dict[str, dict[Any, list[tuple[int, int]]]] = {}

    for _, case in cases.iterrows():
        idx = int(case["case_order"])
        case_id = str(case["case_id"])
        date = str(case["date"])
        std = maps["baseline_STD_norm"][idx]
        boundary = maps["boundary_score_norm"][idx]
        cold = maps["cold_region_norm"][idx]
        warm = maps["warm_region_norm"][idx]
        auv1 = maps["AUV1_region_map"][idx]
        auv2 = maps["AUV2_region_map"][idx]
        region_a, region_b = region_masks(cold, warm, mask)
        core = boundary_core(boundary, mask)
        crossing_proxy, proxy_meta = s11c.build_crossing_proxy(boundary, region_a, region_b, core, mask)
        crossing_gamma025 = (0.5 * std + 0.3 * boundary + 0.2 * ((1.0 - 0.25) * boundary + 0.25 * crossing_proxy)).astype(np.float32)
        crossing_gamma025[~mask] = np.nan
        prototype_boundary_alpha050 = maps["enriched_boundary_alpha050"][idx]
        with_boundary_1 = (0.50 * std + 0.30 * auv1 + 0.20 * boundary).astype(np.float32)
        with_boundary_2 = (0.50 * std + 0.30 * auv2 + 0.20 * boundary).astype(np.float32)
        with_boundary_1[~mask] = np.nan
        with_boundary_2[~mask] = np.nan

        np.save(outdir / "masks" / f"{case_id}_prototype_region_A_mask.npy", region_a)
        np.save(outdir / "masks" / f"{case_id}_prototype_region_B_mask.npy", region_b)
        np.save(outdir / "masks" / f"{case_id}_prototype_boundary_core_mask.npy", core)

        maps_full = {
            "STD_full": s11a.embed_roi_to_hres(std, mask, fill=np.nan),
            "boundary_full": s11a.embed_roi_to_hres(boundary, mask, fill=np.nan),
        }
        masks_full = {
            "region_A_full": s11a.embed_roi_to_hres(region_a.astype(np.float32), mask, fill=np.nan) > 0.5,
            "region_B_full": s11a.embed_roi_to_hres(region_b.astype(np.float32), mask, fill=np.nan) > 0.5,
            "boundary_core_full": s11a.embed_roi_to_hres(core.astype(np.float32), mask, fill=np.nan) > 0.5,
        }
        crossing_proxy_full = s11a.embed_roi_to_hres(crossing_proxy, mask, fill=np.nan)

        baseline_points: set[tuple[int, int]] | None = None
        single_specs = [
            ("baseline_STD", std, "information_map = STD_norm", 0.0),
            ("prototype_boundary_alpha050", prototype_boundary_alpha050, "information_map = 0.5*STD_norm + 0.5*prototype_boundary_score_norm", 0.0),
            ("prototype_crossing_gamma025", crossing_gamma025, "information_map = 0.5*STD_norm + 0.3*prototype_boundary + 0.2*((1-0.25)*prototype_boundary + 0.25*prototype_crossing_proxy)", 0.25),
        ]
        for run_name, info, formulation, gamma in single_specs:
            run_id = f"{case_id}__single_auv_12h__{run_name}"
            diag, routes, run_dir = run_planner_case(s11a, run_id, info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_1auv, outdir, args.timeout_s, args.skip_existing)
            solver_rows.append(diag)
            points = route_points(s11a, routes, lat_hres, lon_hres)
            if run_name == "baseline_STD":
                baseline_points = set(valid_unique(points, valid_full))
            route_points_by_run[f"{case_id}__single__{run_name}"] = {"all": points}
            info_full = s11a.embed_roi_to_hres(info, mask, fill=np.nan)
            path = s11a.path_metrics(routes, lat_hres, lon_hres, info_full, maps_full["STD_full"], maps_full["boundary_full"], baseline_points)
            cross = s11c.crossing_metrics(points, routes, masks_full["region_A_full"], masks_full["region_B_full"], masks_full["boundary_core_full"], crossing_proxy_full, baseline_points)
            length, duration = s11c.trajectory_length_and_duration(routes)
            row = {
                "run_id": run_id,
                "case_id": case_id,
                "display_case": case.get("display_case", case_id),
                "date": date,
                "run_name": run_name,
                "mission_duration_requested_h": 12.0,
                "mission_duration": duration,
                "trajectory_length": length,
                "solver_runtime": diag.get("runtime_s", np.nan),
                "solver_status": diag.get("status", ""),
                "gamma": gamma,
                "formulation": formulation,
                "descriptor_source": "Step11Y prototype_based arrays from Step08 predicted-class descriptors",
                "crossing_proxy_method": proxy_meta.get("method", ""),
                "collected_STD": path["collected_STD_score"],
                "collected_boundary": path["collected_boundary_score"],
                "crossing_count": cross["boundary_crossing_count"],
                "regions_visited": cross["number_of_distinct_regions_visited"],
                "fraction_path_region_A": cross["fraction_path_region_A"],
                "fraction_path_region_B": cross["fraction_path_region_B"],
                "fraction_path_boundary_core": cross["fraction_path_boundary_core"],
                "difference_from_baseline": cross["difference_from_baseline"],
            }
            single_rows.append(row)
            manifest_rows.append({**row, "scope": "single_AUV", "run_dir": rel(run_dir), "input_nc": diag.get("input_nc", "")})

        multi_run_id = f"{case_id}__multi_auv_12h__baseline_STD"
        diag, routes, run_dir = run_planner_case(s11a, multi_run_id, std, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_2auv, outdir, args.timeout_s, args.skip_existing)
        solver_rows.append(diag)
        vehicle_points = {}
        vrows = []
        for i, route in enumerate(routes[:2], start=1):
            pts = route_points(s11a, [route], lat_hres, lon_hres)
            vehicle_points[i] = pts
            vrows.append(vehicle_metrics(multi_run_id, "baseline_STD", case_id, i, pts, route, maps_full, masks_full, valid_full, diag.get("status", "")))
        vdf = pd.DataFrame(vrows)
        vehicle_rows.extend(vrows)
        route_points_by_run[f"{case_id}__multi__baseline_STD"] = vehicle_points
        mrow = fleet_metrics(multi_run_id, "baseline_STD", case_id, vehicle_points, vdf, masks_full, valid_full, diag.get("status", ""), float(diag.get("runtime_s", np.nan)))
        multi_rows.append(mrow)
        manifest_rows.append({**mrow, "scope": "multi_AUV", "run_dir": rel(run_dir), "input_nc": diag.get("input_nc", "")})

        pair_specs = [("prototype_vehicle_specific_maps", auv1, auv2)]
        if not args.no_optional_boundary:
            pair_specs.append(("prototype_vehicle_specific_with_boundary", with_boundary_1, with_boundary_2))
        for strategy, map1, map2 in pair_specs:
            vehicle_points = {}
            vrows = []
            runtime_total = 0.0
            statuses = []
            for vid, info in [(1, map1), (2, map2)]:
                run_id = f"{case_id}__multi_auv_12h__{strategy}__AUV{vid}"
                diag, routes, run_dir = run_planner_case(s11a, run_id, info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_1auv, outdir, args.timeout_s, args.skip_existing)
                solver_rows.append(diag)
                runtime_total += float(diag.get("runtime_s", 0.0) or 0.0)
                statuses.append(str(diag.get("status", "")))
                route = routes[0] if routes else None
                pts = route_points(s11a, [route], lat_hres, lon_hres) if route else []
                vehicle_points[vid] = pts
                vrows.append(vehicle_metrics(run_id, strategy, case_id, vid, pts, route, maps_full, masks_full, valid_full, str(diag.get("status", ""))))
            vdf = pd.DataFrame(vrows)
            vehicle_rows.extend(vrows)
            route_points_by_run[f"{case_id}__multi__{strategy}"] = vehicle_points
            status = "SUCCESS" if all(s in ["SUCCESS", "REUSED"] for s in statuses) else "FAILED_OR_PARTIAL"
            mrow = fleet_metrics(f"{case_id}__multi_auv_12h__{strategy}", strategy, case_id, vehicle_points, vdf, masks_full, valid_full, status, runtime_total)
            multi_rows.append(mrow)
            manifest_rows.append({**mrow, "scope": "multi_AUV_PROXY", "run_dir": "two 1-AUV proxy runs", "input_nc": ""})

    manifest = pd.DataFrame(manifest_rows)
    single_df = pd.DataFrame(single_rows)
    vehicle_df = pd.DataFrame(vehicle_rows)
    multi_df = pd.DataFrame(multi_rows)
    solver_df = pd.DataFrame(solver_rows)
    comparison = compare_old_new(single_df, multi_df)

    manifest.to_csv(outdir / "step11z_run_manifest.csv", index=False)
    single_df.to_csv(outdir / "step11z_single_auv_metrics.csv", index=False)
    vehicle_df.to_csv(outdir / "step11z_multi_auv_vehicle_metrics.csv", index=False)
    multi_df.to_csv(outdir / "step11z_multi_auv_metrics.csv", index=False)
    comparison.to_csv(outdir / "step11z_old_vs_new_comparison.csv", index=False)
    solver_df.to_csv(outdir / "step11z_solver_diagnostics.csv", index=False)

    plot_panels(outdir, temp, cases, single_df, multi_df, route_points_by_run)

    failures = solver_df[~solver_df["status"].astype(str).isin(["SUCCESS", "REUSED"])] if not solver_df.empty and "status" in solver_df else pd.DataFrame()
    verdict = "PROTOTYPE_BASED_RERUN_COMPLETED_RESULTS_READY"
    if not failures.empty:
        verdict = "PROTOTYPE_BASED_RERUN_COMPLETED_WITH_WARNINGS"
        warnings.append(f"{len(failures)} planner runs failed/timed out.")
    if single_df.empty or multi_df.empty:
        verdict = "PROTOTYPE_BASED_RERUN_FAILED"
    if plt is None:
        warnings.append(f"Matplotlib unavailable: {MATPLOTLIB_ERROR}")

    checks = {
        "verdict": verdict,
        "output_dir": rel(outdir),
        "step11y_source": rel(step11y),
        "cases_rerun": cases["case_id"].astype(str).tolist(),
        "single_runs": int(len(single_df)),
        "multi_fleet_rows": int(len(multi_df)),
        "vehicle_specific_mode": "two independent 1-AUV proxy runs combined into fleet metrics",
        "prototype_descriptors_only": True,
        "TEMPpred_used_for_planner_descriptors": False,
        "planner_failures": int(len(failures)),
        "figures_created": len(list((outdir / "figures").glob("*.png"))),
        "warnings_count": len(warnings),
    }
    write_json(outdir / "step11z_checks.json", checks)
    write_json(
        outdir / "step11z_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": rel(Path(__file__)),
            "command_hint": f"python {rel(Path(__file__))}",
            "inputs": {
                "step11y": rel(step11y),
                "planner": rel(args.planner),
                "step10f": rel(STEP10F),
                "old_step11c": [rel(p) for p in OLD_STEP11C],
                "old_step11d": [rel(p) for p in OLD_STEP11D],
            },
            "warnings": warnings,
        },
    )
    write_reports(outdir, single_df, multi_df, comparison, checks, warnings)
    try:
        shutil.copy2(Path(__file__), outdir / Path(__file__).name)
    except Exception as exc:
        warnings.append(f"Could not copy script: {exc}")

    print("\n============================================================")
    print("STEP11Z MINIMAL PROTOTYPE-BASED RERUN")
    print("============================================================")
    print(f"Script: {rel(Path(__file__))}")
    print(f"Command: python {rel(Path(__file__))}")
    print(f"Output: {rel(outdir)}")
    print(f"Cases rerun: {', '.join(checks['cases_rerun'])}")
    print(f"Single-AUV rows: {len(single_df)}")
    print(f"Multi-AUV rows: {len(multi_df)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Verdict: {verdict}")
    print("============================================================\n")
    return 0 if verdict != "PROTOTYPE_BASED_RERUN_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
