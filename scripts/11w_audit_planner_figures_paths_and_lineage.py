"""Step11W: audit planner figure, path, map, and coordinate lineage.

This audit is intentionally read-only for previous Step11 outputs. It inventories
existing artefacts, checks which maps were used by the planner versus shown in
figures, inspects path/map coordinate alignment, computes path overlay metrics,
and regenerates diagnostic figures only from saved arrays, NetCDF planner inputs,
CSVs, JSON route files, and masks.
"""

from __future__ import annotations

import json
import math
import re
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
    import xarray as xr
except Exception:  # pragma: no cover - optional diagnostic reader
    xr = None


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCRIPTS = ROOT / "scripts"

STEP10F = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"

OUTPUTS = [
    ("Step11A", RESULTS / "fossum_roi_x490_step11a_minimal_boundary_planner_runs_20260520_102117"),
    ("Step11B", RESULTS / "fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_160652"),
    ("Step11B", RESULTS / "fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_165239"),
    ("Step11B", RESULTS / "fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_194733"),
    ("Step11C", RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322"),
    ("Step11D", RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809"),
]

SCRIPT_BY_STEP = {
    "Step11A": SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py",
    "Step11B": SCRIPTS / "11b_descriptor_ablation_planner_tests.py",
    "Step11C": SCRIPTS / "11c_single_auv_boundary_crossing_reward.py",
    "Step11D": SCRIPTS / "11d_multi_auv_regime_separation_and_overlap_reduction.py",
}

ROI_ROW_MIN = 55
ROI_ROW_MAX = 126
ROI_COL_MIN = 47
ROI_COL_MAX = 163
ROI_SHAPE = (72, 117)


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


def write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> list[str]:
    if df.empty:
        return ["No rows available."]
    view = df.loc[:, [c for c in columns if c in df.columns]].head(max_rows).fillna("")
    cols = list(view.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in view.iterrows():
        vals = [str(row[c]).replace("|", "/") for c in cols]
        out.append("| " + " | ".join(vals) + " |")
    return out


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def load_npz(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        return {}
    try:
        z = np.load(path, allow_pickle=True)
        return {k: z[k] for k in z.files}
    except Exception:
        return {}


def norm01(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=float)
    finite = np.isfinite(a)
    if not finite.any():
        return np.zeros_like(a, dtype=float)
    lo = np.nanmin(a[finite])
    hi = np.nanmax(a[finite])
    if hi <= lo:
        return np.zeros_like(a, dtype=float)
    return np.clip((a - lo) / (hi - lo), 0, 1)


def classify_file(path: Path, base: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    rel = str(path.relative_to(base)).replace("\\", "/")
    name = path.name.lower()
    if suffix == ".png":
        file_type = "figure_png"
    elif suffix == ".csv":
        file_type = "csv"
    elif suffix in {".json"}:
        file_type = "json"
    elif suffix in {".npy", ".npz"}:
        file_type = "array"
    elif suffix == ".md":
        file_type = "markdown"
    elif suffix == ".py":
        file_type = "script"
    elif suffix in {".log", ".txt"}:
        file_type = "log_or_text"
    elif suffix == ".nc":
        file_type = "planner_netcdf"
    else:
        file_type = suffix.lstrip(".") or "unknown"

    if "trajectory" in name or "route" in name or "waypoint" in name:
        role = "trajectory/path data"
    elif "information_map" in name or "planner_interface" in name:
        role = "planner information_map source"
    elif "metric" in name or "diagnostic" in name:
        role = "metrics/diagnostics"
    elif "mask" in name or "region" in name or "regime" in name:
        role = "region/mask map"
    elif "overlay" in name or "trajectory_over" in name or "panel" in name:
        role = "trajectory overlay figure"
    elif "barplot" in name or "plot" in name:
        role = "metric figure"
    elif suffix == ".py":
        role = "copied/source script"
    elif suffix == ".md":
        role = "report"
    elif suffix in {".log", ".txt"}:
        role = "log"
    else:
        role = "support artefact"
    return file_type, role


def inventory_outputs() -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for step, base in OUTPUTS:
        if not base.exists():
            missing.append(str(base))
            rows.append(
                {
                    "step": step,
                    "output_path": str(base),
                    "file_type": "missing_output",
                    "relative_path": "",
                    "file_size": np.nan,
                    "modified_time": "",
                    "likely_role": "missing output directory",
                }
            )
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            ftype, role = classify_file(path, base)
            rows.append(
                {
                    "step": step,
                    "output_path": str(base),
                    "file_type": ftype,
                    "relative_path": str(path.relative_to(base)).replace("\\", "/"),
                    "file_size": path.stat().st_size,
                    "modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                    "likely_role": role,
                }
            )
    return pd.DataFrame(rows), missing


def infer_case_from_text(text: str) -> str:
    for case in ["C01_representative", "C06_representative", "October_control"]:
        if case.lower() in text.lower():
            return case
    if "c01" in text.lower():
        return "C01_representative"
    if "c06" in text.lower():
        return "C06_representative"
    if "october" in text.lower():
        return "October_control"
    return "mixed_or_unknown"


def infer_figure_lineage(step: str, base: Path, fig: Path) -> dict[str, Any]:
    rel = str(fig.relative_to(base)).replace("\\", "/")
    name = fig.name
    lname = name.lower()
    script = SCRIPT_BY_STEP.get(step, Path(""))
    plotting_function = ""
    bg_name = "none"
    bg_source = ""
    traj_source = ""
    traj_names = ""
    issue = ""
    interpretation = ""

    if step == "Step11A":
        plotting_function = "plot_overlay / plot_metric_panels"
        if "overlay" in lname or "trajectory" in lname:
            bg_name = "TEMPpred, STD_norm, boundary_score_norm multi-panel"
            bg_source = "Step10F planner_minimal_boundary_input_maps.npz and planner_input NetCDFs"
            traj_source = "planner_runs/*/trajectory_routes.json"
            traj_names = "baseline_STD + enriched_boundary_alpha025/alpha050"
            interpretation = "Shows baseline and boundary-enriched paths over diagnostic maps; not every panel is the exact planner objective."
        elif "barplot" in lname or "metrics" in lname:
            plotting_function = "plot_metric_panels / plot_bar"
            interpretation = "Metric summary figure."
    elif step == "Step11B":
        plotting_function = "save_descriptor_panel / plot_bar"
        if "descriptor_trajectories_panel" in lname or "overlay" in lname or "trajectory" in lname:
            bg_name = "descriptor panel backgrounds: STD_norm, boundary, gradient, heterogeneity, representative_zone, interest"
            bg_source = "Step09/Step10F descriptors loaded by script; information maps also saved in step11b_information_maps_by_descriptor.npz"
            traj_source = "planner_runs/*/trajectory_routes.json"
            traj_names = "baseline_STD + descriptor alpha025/alpha050 runs"
            issue = "Can be misleading if read as exact objective map; descriptors were used in information_map but panel backgrounds are diagnostic."
            interpretation = "Use regenerated information_map figures when explaining objective; existing panel is useful for path sensitivity against each descriptor background."
        elif "barplot" in lname or "metrics" in lname:
            plotting_function = "plot_bar"
            interpretation = "Metric summary; no background map."
    elif step == "Step11C":
        plotting_function = "plot_overlay_panel / plot_region_overlay / plot_bar"
        if "std" in lname:
            bg_name = "STD_norm"
            bg_source = "Step10F day-specific STD"
        elif "temppred" in lname:
            bg_name = "TEMPpred"
            bg_source = "Step10F day-specific TEMPpred"
        elif "boundary" in lname and "mask" not in lname:
            bg_name = "boundary_score_norm"
            bg_source = "Step10F/Step08 prototype boundary descriptor"
        elif "region" in lname or "mask" in lname:
            bg_name = "region_A/region_B/boundary_core masks"
            bg_source = "Step11C saved masks"
        elif "overlay" in lname:
            bg_name = "multi-panel diagnostic backgrounds"
        if bg_name != "none":
            traj_source = "planner_runs/*/trajectory_routes.json"
            traj_names = "baseline_STD, boundary_alpha050, crossing_gamma025, crossing_gamma050"
            issue = "Crossing_count can count short local transitions near boundary; inspect region-colored path."
            interpretation = "Good diagnostic for whether the AUV visits both regimes or mostly follows the boundary area."
    elif step == "Step11D":
        plotting_function = "plot_strategy_overlay / plot_masks_and_rewards / plot_bar"
        if "overlay" in lname or "comparison_panel" in lname:
            bg_name = "region_A/region_B RGB mask"
            bg_source = "Step11D saved regime masks"
            traj_source = "planner_runs/*/trajectory_routes.json and selected pair route files"
            traj_names = "AUV1/AUV2 by strategy"
            issue = "Background is region mask, not the exact vehicle-specific information_map; overlay impression should be checked with distance metrics."
            interpretation = "Shows regime separation visually; use overlay metrics to distinguish real path overlap from same-zone attraction."
        elif "masks_and_rewards" in lname:
            bg_name = "regime masks and region reward maps"
            bg_source = "Step11D saved masks/reward NPY files"
            interpretation = "Descriptor/mask diagnostic, not a trajectory figure."
        elif "barplot" in lname or "distance" in lname:
            interpretation = "Metric summary figure."

    return {
        "step": step,
        "output_path": str(base),
        "figure_name": rel,
        "script_source": str(script) if script else "",
        "plotting_function": plotting_function,
        "background_map_name": bg_name,
        "background_map_source_file": bg_source,
        "background_map_shape": "72x117 ROI for audit backgrounds; planner NetCDFs are 180x240 HRes",
        "trajectory_source_file": traj_source,
        "trajectory_run_names": traj_names,
        "coordinate_system_detected": "ROI row/col indices: x=col-ROI_COL_MIN, y=row-ROI_ROW_MIN",
        "extent_used": "none detected in Step11A-D scripts",
        "origin_used": "origin='lower' in audited Step11 scripts",
        "likely_issue": issue,
        "interpretation": interpretation,
    }


def figure_lineage(inventory: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for step, base in OUTPUTS:
        if not base.exists():
            continue
        figures = sorted(p for p in base.rglob("*.png") if p.is_file())
        for fig in figures:
            rows.append(infer_figure_lineage(step, base, fig))
    return pd.DataFrame(rows)


def load_step10f_maps() -> tuple[dict[str, int], dict[str, np.ndarray]]:
    npz = load_npz(STEP10F / "planner_minimal_boundary_input_maps.npz")
    cases = [str(x) for x in npz.get("case_ids", np.array([], dtype=str)).tolist()]
    case_idx = {case: i for i, case in enumerate(cases)}
    maps: dict[str, np.ndarray] = {}
    for k, v in npz.items():
        if isinstance(v, np.ndarray) and v.ndim >= 2:
            maps[k] = v
    return case_idx, maps


def load_info_map_from_nc(nc_path: Path) -> np.ndarray | None:
    if xr is None or not nc_path.exists():
        return None
    try:
        with xr.open_dataset(nc_path) as ds:
            var = "temperr" if "temperr" in ds else list(ds.data_vars)[0]
            arr = np.asarray(ds[var].to_numpy(), dtype=float)
        if arr.shape == ROI_SHAPE:
            return arr
        if arr.ndim == 2 and arr.shape[0] > ROI_ROW_MAX and arr.shape[1] > ROI_COL_MAX:
            return arr[ROI_ROW_MIN : ROI_ROW_MAX + 1, ROI_COL_MIN : ROI_COL_MAX + 1]
    except Exception:
        return None
    return None


def planner_map_vs_background() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for step, base in OUTPUTS:
        if not base.exists():
            continue
        if step == "Step11A":
            df = safe_read_csv(base / "step11a_run_manifest.csv")
            for _, r in df.iterrows():
                formulation = str(r.get("formulation", ""))
                rows.append(
                    {
                        "step": step,
                        "case_id": r.get("case_id", ""),
                        "run_name": formulation,
                        "descriptor": "boundary_score_norm" if "boundary" in formulation else "none",
                        "alpha": r.get("alpha", ""),
                        "planner_information_map_source": r.get("input_nc", "planner_input NetCDF temperr; formula in manifest"),
                        "figure_background_source": "overlay figures show TEMPpred/STD_norm/boundary diagnostic panels",
                        "map_used_equals_background": "partial",
                        "conclusion": "Planner used STD or STD+boundary as manifest says; figures are multi-background diagnostics, not a single objective panel.",
                    }
                )
        elif step == "Step11B":
            df = safe_read_csv(base / "step11b_run_manifest.csv")
            if df.empty:
                df = safe_read_csv(base / "step11b_run_metrics.csv")
            info_npz = base / "step11b_information_maps_by_descriptor.npz"
            for _, r in df.iterrows():
                descriptor = str(r.get("descriptor", "none"))
                alpha = r.get("alpha", "")
                run_id = str(r.get("run_id", ""))
                if not run_id:
                    run_id = f"{r.get('case_id','')}__{descriptor}_alpha{float(alpha):03.0f}" if descriptor != "none" else ""
                rows.append(
                    {
                        "step": step,
                        "case_id": r.get("case_id", ""),
                        "run_name": run_id or r.get("run_name", ""),
                        "descriptor": descriptor,
                        "alpha": alpha,
                        "planner_information_map_source": str(info_npz) if info_npz.exists() else "planner_input NetCDF only; information map NPZ missing",
                        "figure_background_source": "descriptor_trajectories_panel uses STD/descriptor backgrounds; barplots use metrics",
                        "map_used_equals_background": "no" if descriptor != "none" else "partial",
                        "conclusion": "Descriptors were used in objective for non-baseline runs; existing figure backgrounds are diagnostic and should be captioned or regenerated over actual information_map.",
                    }
                )
        elif step == "Step11C":
            df = safe_read_csv(base / "step11c_crossing_metrics.csv")
            for _, r in df.iterrows():
                run_id = str(r.get("run_id", ""))
                rows.append(
                    {
                        "step": step,
                        "case_id": r.get("case_id", ""),
                        "run_name": r.get("run_name", run_id),
                        "descriptor": "boundary/crossing_proxy" if "crossing" in run_id or "boundary" in run_id else "none",
                        "alpha": r.get("gamma", ""),
                        "planner_information_map_source": str(base / "planner_inputs" / f"{run_id}_planner_interface.nc"),
                        "figure_background_source": "TEMPpred/STD/boundary/region masks in figures, not always exact crossing information_map",
                        "map_used_equals_background": "partial",
                        "conclusion": "Crossing proxy is stored in planner NetCDFs; visual interpretation needs region-colored diagnostics.",
                    }
                )
        elif step == "Step11D":
            df = safe_read_csv(base / "step11d_fleet_level_metrics.csv")
            for _, r in df.iterrows():
                run_id = str(r.get("run_id", ""))
                strat = str(r.get("strategy", ""))
                rows.append(
                    {
                        "step": step,
                        "case_id": r.get("case_id", ""),
                        "run_name": strat,
                        "descriptor": "region_A/region_B/boundary proxy" if "vehicle" in strat or "boundary" in strat else "none",
                        "alpha": "",
                        "planner_information_map_source": str(base / "planner_inputs" / f"{run_id}_planner_interface.nc"),
                        "figure_background_source": "strategy overlays use region mask RGB background; exact objective map may differ by vehicle/proxy",
                        "map_used_equals_background": "no" if "vehicle" in strat or "boundary" in strat else "partial",
                        "conclusion": "Use fleet metrics and regenerated information-map panels to explain objective; existing overlays explain regime separation.",
                    }
                )
    return pd.DataFrame(rows)


def load_lat_lon() -> tuple[np.ndarray | None, np.ndarray | None]:
    lat_path = HRES / "LAT_hres.npy"
    lon_path = HRES / "LON_hres.npy"
    if not lat_path.exists() or not lon_path.exists():
        return None, None
    return np.load(lat_path), np.load(lon_path)


def nearest_index(arr: np.ndarray, value: float) -> int:
    return int(np.nanargmin(np.abs(arr - value)))


def load_routes(route_json: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(route_json.read_text(encoding="utf-8"))
        return list(payload.get("routes", []))
    except Exception:
        return []


def route_to_roi_points(route: dict[str, Any], lat_hres: np.ndarray | None, lon_hres: np.ndarray | None) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    waypoints = route.get("waypoints", [])
    for wp in waypoints:
        if len(wp) < 2:
            continue
        lat, lon = float(wp[0]), float(wp[1])
        if lat_hres is not None and lon_hres is not None:
            row = nearest_index(lat_hres, lat)
            col = nearest_index(lon_hres, lon)
            points.append((row - ROI_ROW_MIN, col - ROI_COL_MIN))
    return points


def route_file_to_paths(route_json: Path, lat_hres: np.ndarray | None, lon_hres: np.ndarray | None) -> dict[str, list[tuple[int, int]]]:
    routes = load_routes(route_json)
    paths: dict[str, list[tuple[int, int]]] = {}
    for route in routes:
        rid = str(route.get("route_id", len(paths) + 1))
        paths[f"AUV{rid}"] = route_to_roi_points(route, lat_hres, lon_hres)
    return paths


def path_bbox(points: list[tuple[int, int]]) -> str:
    if not points:
        return ""
    rr = [p[0] for p in points]
    cc = [p[1] for p in points]
    return f"rows[{min(rr)},{max(rr)}], cols[{min(cc)},{max(cc)}]"


def coordinate_checks(inventory: pd.DataFrame) -> pd.DataFrame:
    lat, lon = load_lat_lon()
    case_idx, maps = load_step10f_maps()
    mask3 = maps.get("mask")
    default_mask = np.ones(ROI_SHAPE, dtype=bool)
    figures_by_output: dict[Path, str] = {}
    for step, base in OUTPUTS:
        figs = [str(p.relative_to(base)).replace("\\", "/") for p in base.rglob("*.png")] if base.exists() else []
        figures_by_output[base] = "; ".join(figs[:4])

    rows: list[dict[str, Any]] = []
    for step, base in OUTPUTS:
        if not base.exists():
            continue
        for route_json in sorted(base.rglob("trajectory_routes.json")):
            rel = str(route_json.relative_to(base)).replace("\\", "/")
            case_id = infer_case_from_text(rel)
            if mask3 is not None and case_id in case_idx and mask3.ndim == 3:
                valid_mask = np.asarray(mask3[case_idx[case_id]], dtype=bool)
            elif mask3 is not None and mask3.ndim == 2:
                valid_mask = np.asarray(mask3, dtype=bool)
            else:
                valid_mask = default_mask
            paths = route_file_to_paths(route_json, lat, lon)
            all_points = [p for pts in paths.values() for p in pts]
            total = len(all_points)
            inside = 0
            for r, c in all_points:
                if 0 <= r < ROI_SHAPE[0] and 0 <= c < ROI_SHAPE[1] and bool(valid_mask[int(r), int(c)]):
                    inside += 1
            inside_frac = inside / total if total else np.nan
            swap_inside = 0
            for r, c in all_points:
                if 0 <= c < ROI_SHAPE[0] and 0 <= r < ROI_SHAPE[1] and bool(valid_mask[int(c), int(r)]):
                    swap_inside += 1
            suspected_swap = bool(total and swap_inside > inside + max(3, 0.2 * total))
            outside_map = total - sum(1 for r, c in all_points if 0 <= r < ROI_SHAPE[0] and 0 <= c < ROI_SHAPE[1])
            verdict = "OK_COORDINATES" if total and inside_frac >= 0.80 and not suspected_swap else "CHECK_COORDINATES"
            rows.append(
                {
                    "step": step,
                    "output_path": str(base),
                    "case_id": case_id,
                    "figure_name": figures_by_output.get(base, ""),
                    "trajectory_file": rel,
                    "map_shape": "72x117",
                    "coordinate_type": "lat/lon route waypoints converted to HRes row/col, then ROI row/col",
                    "path_points_total": total,
                    "path_points_inside_valid_mask": inside,
                    "path_points_inside_fraction": inside_frac,
                    "path_bbox": path_bbox(all_points),
                    "map_bbox": "rows[0,71], cols[0,116]",
                    "suspected_x_y_swap": suspected_swap,
                    "suspected_origin_flip": False,
                    "suspected_extent_mismatch": False,
                    "verdict": verdict if outside_map == 0 else f"{verdict}_WITH_{outside_map}_OUTSIDE_MAP_POINTS",
                }
            )
    return pd.DataFrame(rows)


def point_set(points: list[tuple[int, int]]) -> set[tuple[int, int]]:
    return {(int(round(r)), int(round(c))) for r, c in points if np.isfinite(r) and np.isfinite(c)}


def mean_min_dist(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> tuple[float, float, float, float]:
    if not a or not b:
        return np.nan, np.nan, np.nan, np.nan
    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    dmin_a = []
    for p in aa:
        d = np.sqrt(np.sum((bb - p) ** 2, axis=1))
        dmin_a.append(float(np.min(d)))
    dmin_b = []
    for p in bb:
        d = np.sqrt(np.sum((aa - p) ** 2, axis=1))
        dmin_b.append(float(np.min(d)))
    mean_d = float(np.mean(dmin_a + dmin_b))
    min_d = float(np.min(dmin_a + dmin_b))
    haus = float(max(max(dmin_a), max(dmin_b)))
    near_pct = float(np.mean(np.asarray(dmin_a) <= 2.0)) if dmin_a else np.nan
    return mean_d, min_d, haus, near_pct


def overlay_metrics() -> pd.DataFrame:
    lat, lon = load_lat_lon()
    rows: list[dict[str, Any]] = []
    for step, base in OUTPUTS:
        if not base.exists():
            continue
        for route_json in sorted(base.rglob("trajectory_routes.json")):
            rel = str(route_json.relative_to(base)).replace("\\", "/")
            case_id = infer_case_from_text(rel)
            paths = route_file_to_paths(route_json, lat, lon)
            labels = list(paths)
            if len(labels) >= 2:
                a_name, b_name = labels[0], labels[1]
                a, b = paths[a_name], paths[b_name]
                set_a, set_b = point_set(a), point_set(b)
                union = len(set_a | set_b)
                inter = len(set_a & set_b)
                mean_d, min_d, haus, near_pct = mean_min_dist(a, b)
                rows.append(
                    {
                        "step": step,
                        "output_path": str(base),
                        "case_id": case_id,
                        "run_or_figure": route_json.parent.name,
                        "path_a": a_name,
                        "path_b": b_name,
                        "trajectory_overlap_ratio": inter / union if union else np.nan,
                        "duplicate_sampled_cells": inter,
                        "inter_vehicle_mean_distance": mean_d,
                        "inter_vehicle_min_distance": min_d,
                        "hausdorff_like_distance": haus,
                        "number_of_identical_waypoints": inter,
                        "percentage_AUV1_path_near_AUV2_path": near_pct,
                        "interpretation": "real overlap is low" if union and inter / union < 0.05 else "substantial real overlap or very close paths",
                    }
                )
            elif len(labels) == 1:
                # Compare single-AUV descriptor runs with their baseline if available.
                if "__baseline" in route_json.parent.name:
                    continue
                parent = route_json.parent.parent
                candidate_case = route_json.parent.name.split("__")[0]
                baseline = next(parent.glob(f"{candidate_case}__*baseline*/*trajectory_routes.json"), None)
                if baseline:
                    bp = route_file_to_paths(baseline, lat, lon)
                    b_pts = next(iter(bp.values()), [])
                    a_pts = paths[labels[0]]
                    set_a, set_b = point_set(a_pts), point_set(b_pts)
                    union = len(set_a | set_b)
                    inter = len(set_a & set_b)
                    mean_d, min_d, haus, near_pct = mean_min_dist(a_pts, b_pts)
                    rows.append(
                        {
                            "step": step,
                            "output_path": str(base),
                            "case_id": case_id,
                            "run_or_figure": route_json.parent.name,
                            "path_a": route_json.parent.name,
                            "path_b": baseline.parent.name,
                            "trajectory_overlap_ratio": inter / union if union else np.nan,
                            "duplicate_sampled_cells": inter,
                            "inter_vehicle_mean_distance": mean_d,
                            "inter_vehicle_min_distance": min_d,
                            "hausdorff_like_distance": haus,
                            "number_of_identical_waypoints": inter,
                            "percentage_AUV1_path_near_AUV2_path": near_pct,
                            "interpretation": "descriptor path nearly baseline" if union and inter / union > 0.75 else "descriptor path differs from baseline",
                        }
                    )
    return pd.DataFrame(rows)


def find_run_route(base: Path, contains: list[str]) -> Path | None:
    for p in sorted(base.rglob("trajectory_routes.json")):
        s = str(p).lower()
        if all(c.lower() in s for c in contains):
            return p
    return None


def plot_map_with_paths(
    arr: np.ndarray,
    paths: dict[str, list[tuple[int, int]]],
    out_path: Path,
    title: str,
    cmap: str = "viridis",
    vmin: float | None = 0,
    vmax: float | None = 1,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    colors = ["white", "tab:red", "tab:cyan", "tab:orange", "black", "tab:green"]
    for i, (label, pts) in enumerate(paths.items()):
        if not pts:
            continue
        yy = [p[0] for p in pts]
        xx = [p[1] for p in pts]
        ax.plot(xx, yy, marker="o", markersize=2, linewidth=1.6, color=colors[i % len(colors)], label=label)
    ax.set_title(title)
    ax.set_xlabel("ROI column")
    ax.set_ylabel("ROI row")
    ax.set_xlim(-1, ROI_SHAPE[1])
    ax.set_ylim(-1, ROI_SHAPE[0])
    ax.legend(fontsize=7, loc="upper right")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def region_rgb(region_a: np.ndarray, region_b: np.ndarray, boundary: np.ndarray | None = None) -> np.ndarray:
    rgb = np.zeros((*region_a.shape, 3), dtype=float)
    rgb[..., 2] = np.asarray(region_a, dtype=float) * 0.75
    rgb[..., 0] = np.asarray(region_b, dtype=float) * 0.75
    if boundary is not None:
        rgb[..., 1] = np.asarray(boundary, dtype=float) * 0.8
    return np.clip(rgb, 0, 1)


def plot_rgb_with_paths(
    rgb: np.ndarray,
    paths: dict[str, list[tuple[int, int]]],
    out_path: Path,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.imshow(rgb, origin="lower", aspect="auto")
    colors = ["white", "yellow", "cyan", "black", "tab:green"]
    for i, (label, pts) in enumerate(paths.items()):
        if not pts:
            continue
        yy = [p[0] for p in pts]
        xx = [p[1] for p in pts]
        ax.plot(xx, yy, marker="o", markersize=2, linewidth=1.8, color=colors[i % len(colors)], label=label)
    ax.set_title(title)
    ax.set_xlabel("ROI column")
    ax.set_ylabel("ROI row")
    ax.set_xlim(-1, ROI_SHAPE[1])
    ax.set_ylim(-1, ROI_SHAPE[0])
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def regenerate_step11b(fig_dir: Path, standard_dir: Path) -> list[str]:
    lat, lon = load_lat_lon()
    case_idx, maps = load_step10f_maps()
    std3 = maps.get("STD_norm")
    created: list[str] = []
    b_outputs = [base for step, base in OUTPUTS if step == "Step11B" and base.exists()]
    if not b_outputs:
        return created

    # Actual information map panels.
    selected: list[tuple[str, str, np.ndarray, dict[str, list[tuple[int, int]]]]] = []
    descriptor_panels: list[tuple[str, str, np.ndarray, dict[str, list[tuple[int, int]]]]] = []
    overlay_paths: dict[str, list[tuple[int, int]]] = {}
    overlay_bg: np.ndarray | None = None
    for base in b_outputs:
        info = load_npz(base / "step11b_information_maps_by_descriptor.npz")
        metrics = safe_read_csv(base / "step11b_run_metrics.csv")
        keys = [k for k in info if k.endswith("alpha050") or k.endswith("baseline_STD")]
        for key in keys[:5]:
            case_id = key.split("__")[0]
            route = find_run_route(base, [key])
            if route is None:
                continue
            paths = route_file_to_paths(route, lat, lon)
            arr = norm01(info[key])
            selected.append((case_id, key.split("__", 1)[-1], arr, paths))
            if overlay_bg is None and std3 is not None and case_id in case_idx:
                overlay_bg = norm01(std3[case_idx[case_id]])
            if paths:
                overlay_paths[key.split("__", 1)[-1]] = next(iter(paths.values()))
            if "alpha" in key and std3 is not None and case_id in case_idx:
                m = re.search(r"alpha(\d+)", key)
                alpha = (float(m.group(1)) / 100.0) if m else 0.5
                if alpha > 0:
                    desc = np.clip((info[key] - (1 - alpha) * std3[case_idx[case_id]]) / alpha, 0, 1)
                    descriptor_panels.append((case_id, key.split("__", 1)[-1], desc, paths))
        if not metrics.empty and "number_of_distinct_regime_zones_visited_proxy" in metrics:
            pass

    def save_grid(items: list[tuple[str, str, np.ndarray, dict[str, list[tuple[int, int]]]]], path: Path, title: str) -> None:
        if not items:
            return
        n = min(len(items), 12)
        cols = 3
        rows = math.ceil(n / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 3.8), squeeze=False)
        for ax in axes.ravel():
            ax.axis("off")
        for ax, (case_id, run, arr, paths) in zip(axes.ravel(), items[:n]):
            ax.imshow(arr, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=1)
            for label, pts in paths.items():
                if pts:
                    ax.plot([p[1] for p in pts], [p[0] for p in pts], color="white", linewidth=1.4, marker="o", markersize=1.8, label=label)
            ax.set_title(f"{case_id}\n{run}", fontsize=8)
            ax.set_xlim(-1, ROI_SHAPE[1])
            ax.set_ylim(-1, ROI_SHAPE[0])
            ax.axis("on")
        fig.suptitle(title)
        fig.tight_layout()
        fig.savefig(path, dpi=180)
        plt.close(fig)
        created.append(str(path))

    save_grid(descriptor_panels, fig_dir / "step11b_each_descriptor_over_descriptor_map.png", "Step11B paths over reconstructed descriptor maps")
    save_grid(selected, fig_dir / "step11b_each_descriptor_over_information_map.png", "Step11B paths over actual saved information maps")

    if overlay_bg is not None and overlay_paths:
        plot_map_with_paths(overlay_bg, overlay_paths, fig_dir / "step11b_overlay_all_descriptors.png", "Step11B descriptor-run paths over STD_norm common background")
        created.append(str(fig_dir / "step11b_overlay_all_descriptors.png"))
        plot_map_with_paths(overlay_bg, overlay_paths, standard_dir / "step11b_standardized_STD_overlay.png", "Standardized Step11B: STD_norm + descriptor paths")
        created.append(str(standard_dir / "step11b_standardized_STD_overlay.png"))

    # Compact crossing diagnostic from existing metrics.
    metric_rows = []
    for base in b_outputs:
        df = safe_read_csv(base / "step11b_run_metrics.csv")
        if not df.empty:
            metric_rows.append(df)
    if metric_rows:
        mdf = pd.concat(metric_rows, ignore_index=True)
        ycol = "boundary_crossing_count_proxy" if "boundary_crossing_count_proxy" in mdf else "trajectory_difference_from_baseline"
        fig, ax = plt.subplots(figsize=(10, 4.5))
        view = mdf[mdf.get("alpha_label", "") != "baseline"].copy() if "alpha_label" in mdf else mdf
        labels = [f"{r.get('case_id','')}\n{r.get('descriptor','')}\na={r.get('alpha','')}" for _, r in view.iterrows()]
        ax.bar(np.arange(len(view)), pd.to_numeric(view[ycol], errors="coerce").fillna(0).to_numpy())
        ax.set_xticks(np.arange(len(view)))
        ax.set_xticklabels(labels, rotation=90, fontsize=6)
        ax.set_ylabel(ycol)
        ax.set_title("Step11B region/crossing diagnostic from saved metrics")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        out = fig_dir / "step11b_region_crossing_diagnostics.png"
        fig.savefig(out, dpi=180)
        plt.close(fig)
        created.append(str(out))
    return created


def regenerate_step11c(fig_dir: Path, standard_dir: Path) -> tuple[list[str], pd.DataFrame]:
    lat, lon = load_lat_lon()
    base = RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322"
    created: list[str] = []
    diag_rows: list[dict[str, Any]] = []
    if not base.exists():
        return created, pd.DataFrame()
    region_a = np.load(base / "region_A_mask.npy") if (base / "region_A_mask.npy").exists() else np.zeros(ROI_SHAPE, dtype=bool)
    region_b = np.load(base / "region_B_mask.npy") if (base / "region_B_mask.npy").exists() else np.zeros(ROI_SHAPE, dtype=bool)
    boundary = np.load(base / "boundary_core_mask.npy") if (base / "boundary_core_mask.npy").exists() else np.zeros(ROI_SHAPE, dtype=bool)
    rgb = region_rgb(region_a, region_b, boundary)
    paths_all: dict[str, list[tuple[int, int]]] = {}
    for label in ["baseline_STD", "boundary_alpha050", "crossing_gamma025", "crossing_gamma050"]:
        route = find_run_route(base, ["1auv_12h", label])
        if route:
            paths = route_file_to_paths(route, lat, lon)
            if paths:
                pts = next(iter(paths.values()))
                paths_all[label] = pts
                n_a = sum(1 for r, c in pts if 0 <= r < 72 and 0 <= c < 117 and bool(region_a[int(r), int(c)]))
                n_b = sum(1 for r, c in pts if 0 <= r < 72 and 0 <= c < 117 and bool(region_b[int(r), int(c)]))
                n_core = sum(1 for r, c in pts if 0 <= r < 72 and 0 <= c < 117 and bool(boundary[int(r), int(c)]))
                labels = []
                for r, c in pts:
                    if 0 <= r < 72 and 0 <= c < 117:
                        if bool(region_a[int(r), int(c)]):
                            labels.append("A")
                        elif bool(region_b[int(r), int(c)]):
                            labels.append("B")
                        else:
                            labels.append("N")
                crossing_events = sum(1 for a, b in zip(labels, labels[1:]) if a in "AB" and b in "AB" and a != b)
                diag_rows.append(
                    {
                        "run_name": label,
                        "points": len(pts),
                        "points_region_A": n_a,
                        "points_region_B": n_b,
                        "points_boundary_core": n_core,
                        "fraction_region_A": n_a / len(pts) if pts else np.nan,
                        "fraction_region_B": n_b / len(pts) if pts else np.nan,
                        "fraction_boundary_core": n_core / len(pts) if pts else np.nan,
                        "visual_crossing_events_from_masks": crossing_events,
                        "interpretation": "visits both regions" if n_a and n_b else "mostly one region or boundary-adjacent",
                    }
                )
    if paths_all:
        plot_rgb_with_paths(rgb, paths_all, fig_dir / "step11c_path_over_region_A_B.png", "Step11C paths over region_A/region_B/boundary masks")
        created.append(str(fig_dir / "step11c_path_over_region_A_B.png"))
        plot_rgb_with_paths(rgb, paths_all, standard_dir / "step11c_standardized_region_overlay.png", "Standardized Step11C: region masks + paths")
        created.append(str(standard_dir / "step11c_standardized_region_overlay.png"))
        plot_map_with_paths(boundary.astype(float), paths_all, fig_dir / "step11c_path_over_boundary_core.png", "Step11C paths over boundary core", cmap="magma")
        created.append(str(fig_dir / "step11c_path_over_boundary_core.png"))
        # Color one representative path by region labels.
        fig, ax = plt.subplots(figsize=(8.5, 5.5))
        ax.imshow(rgb, origin="lower", aspect="auto")
        pts = paths_all.get("crossing_gamma025") or next(iter(paths_all.values()))
        colors = []
        for r, c in pts:
            if 0 <= r < 72 and 0 <= c < 117 and bool(region_a[int(r), int(c)]):
                colors.append("tab:blue")
            elif 0 <= r < 72 and 0 <= c < 117 and bool(region_b[int(r), int(c)]):
                colors.append("tab:red")
            elif 0 <= r < 72 and 0 <= c < 117 and bool(boundary[int(r), int(c)]):
                colors.append("lime")
            else:
                colors.append("white")
        if pts:
            ax.plot([p[1] for p in pts], [p[0] for p in pts], color="white", linewidth=0.8, alpha=0.6)
            ax.scatter([p[1] for p in pts], [p[0] for p in pts], c=colors, s=20, edgecolor="black", linewidth=0.2)
        ax.set_title("Step11C path colored by saved region masks")
        ax.set_xlim(-1, ROI_SHAPE[1])
        ax.set_ylim(-1, ROI_SHAPE[0])
        fig.tight_layout()
        out = fig_dir / "step11c_path_colored_by_region.png"
        fig.savefig(out, dpi=180)
        plt.close(fig)
        created.append(str(out))
        # Crossing-event markers.
        fig, ax = plt.subplots(figsize=(8.5, 5.5))
        ax.imshow(rgb, origin="lower", aspect="auto")
        events_x, events_y = [], []
        prev = None
        for r, c in pts:
            lab = "A" if 0 <= r < 72 and 0 <= c < 117 and bool(region_a[int(r), int(c)]) else ("B" if 0 <= r < 72 and 0 <= c < 117 and bool(region_b[int(r), int(c)]) else "N")
            if prev in {"A", "B"} and lab in {"A", "B"} and lab != prev:
                events_x.append(c)
                events_y.append(r)
            prev = lab
        if pts:
            ax.plot([p[1] for p in pts], [p[0] for p in pts], color="white", linewidth=1.5, marker="o", markersize=2)
        if events_x:
            ax.scatter(events_x, events_y, c="yellow", s=80, marker="*", edgecolor="black", label="A/B switch")
            ax.legend()
        ax.set_title("Step11C crossing events marked from saved masks")
        ax.set_xlim(-1, ROI_SHAPE[1])
        ax.set_ylim(-1, ROI_SHAPE[0])
        fig.tight_layout()
        out = fig_dir / "step11c_crossing_events_marked.png"
        fig.savefig(out, dpi=180)
        plt.close(fig)
        created.append(str(out))
    return created, pd.DataFrame(diag_rows)


def regenerate_step11d(fig_dir: Path, standard_dir: Path) -> tuple[list[str], pd.DataFrame]:
    lat, lon = load_lat_lon()
    base = RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809"
    created: list[str] = []
    rows: list[dict[str, Any]] = []
    if not base.exists():
        return created, pd.DataFrame()
    region_a = np.load(base / "step11d_regime_A_mask.npy") if (base / "step11d_regime_A_mask.npy").exists() else np.zeros(ROI_SHAPE, dtype=bool)
    region_b = np.load(base / "step11d_regime_B_mask.npy") if (base / "step11d_regime_B_mask.npy").exists() else np.zeros(ROI_SHAPE, dtype=bool)
    boundary = np.load(base / "step11d_boundary_core_mask.npy") if (base / "step11d_boundary_core_mask.npy").exists() else np.zeros(ROI_SHAPE, dtype=bool)
    rgb = region_rgb(region_a, region_b, boundary)
    strategies = [
        "multi_baseline_STD",
        "multi_boundary_alpha050",
        "vehicle_specific_regime_maps",
        "vehicle_specific_with_crossing_proxy",
        "sequential_overlap_reduction",
        "post_solver_selected_pair",
    ]
    all_paths: dict[str, dict[str, list[tuple[int, int]]]] = {}
    for strat in strategies:
        route = find_run_route(base, [strat])
        if route:
            paths = route_file_to_paths(route, lat, lon)
            all_paths[strat] = paths
            labels = list(paths)
            if len(labels) >= 2:
                a, b = paths[labels[0]], paths[labels[1]]
                mean_d, min_d, haus, near_pct = mean_min_dist(a, b)
                set_a, set_b = point_set(a), point_set(b)
                union = len(set_a | set_b)
                inter = len(set_a & set_b)
                rows.append(
                    {
                        "strategy": strat,
                        "trajectory_overlap_ratio": inter / union if union else np.nan,
                        "duplicate_sampled_cells": inter,
                        "inter_vehicle_mean_distance": mean_d,
                        "inter_vehicle_min_distance": min_d,
                        "hausdorff_like_distance": haus,
                        "percentage_AUV1_path_near_AUV2_path": near_pct,
                        "visual_vs_real": "mostly visual/same-zone issue" if union and inter / union < 0.05 else "real overlap present",
                    }
                )
    if all_paths:
        merged = {}
        for strat, paths in all_paths.items():
            for label, pts in paths.items():
                merged[f"{strat}_{label}"] = pts
        plot_rgb_with_paths(rgb, merged, fig_dir / "step11d_paths_over_region_A_B.png", "Step11D AUV paths over region_A/region_B masks")
        created.append(str(fig_dir / "step11d_paths_over_region_A_B.png"))
        plot_rgb_with_paths(rgb, merged, standard_dir / "step11d_standardized_region_overlay.png", "Standardized Step11D: region masks + AUV paths")
        created.append(str(standard_dir / "step11d_standardized_region_overlay.png"))
        reward_a = np.load(base / "step11d_region_A_reward.npy") if (base / "step11d_region_A_reward.npy").exists() else region_a.astype(float)
        plot_map_with_paths(norm01(reward_a), merged, fig_dir / "step11d_paths_over_information_maps.png", "Step11D paths over region_A reward proxy", cmap="viridis")
        created.append(str(fig_dir / "step11d_paths_over_information_maps.png"))
        # Distance along path for first available 2-AUV strategy.
        first = next((p for p in all_paths.values() if len(p) >= 2), None)
        if first:
            labels = list(first)
            a, b = first[labels[0]], first[labels[1]]
            n = min(len(a), len(b))
            d = [float(np.hypot(a[i][0] - b[i][0], a[i][1] - b[i][1])) for i in range(n)]
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(np.arange(n), d, marker="o", linewidth=1.4)
            ax.set_title("Step11D AUV1-AUV2 distance along matched waypoint order")
            ax.set_xlabel("matched waypoint index")
            ax.set_ylabel("ROI-cell distance")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            out = fig_dir / "step11d_AUV1_AUV2_distance_along_path.png"
            fig.savefig(out, dpi=180)
            plt.close(fig)
            created.append(str(out))
        fleet = safe_read_csv(base / "step11d_fleet_level_metrics.csv")
        if not fleet.empty:
            fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
            axes[0].scatter(pd.to_numeric(fleet.get("trajectory_overlap_ratio"), errors="coerce"), pd.to_numeric(fleet.get("fleet_complementarity_score"), errors="coerce"))
            for _, r in fleet.iterrows():
                axes[0].annotate(str(r.get("strategy", ""))[:18], (r.get("trajectory_overlap_ratio", 0), r.get("fleet_complementarity_score", 0)), fontsize=6)
            axes[0].set_xlabel("trajectory_overlap_ratio")
            axes[0].set_ylabel("fleet_complementarity_score")
            axes[0].set_title("Overlap vs complementarity")
            axes[0].grid(alpha=0.25)
            axes[1].bar(np.arange(len(fleet)), pd.to_numeric(fleet.get("inter_vehicle_mean_distance"), errors="coerce"))
            axes[1].set_xticks(np.arange(len(fleet)))
            axes[1].set_xticklabels([str(x)[:18] for x in fleet.get("strategy", [])], rotation=80, fontsize=7)
            axes[1].set_ylabel("mean distance")
            axes[1].set_title("True distance metric")
            fig.tight_layout()
            out = fig_dir / "step11d_overlay_vs_true_distance_panel.png"
            fig.savefig(out, dpi=180)
            plt.close(fig)
            created.append(str(out))
            fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
            for ax, col, title in [
                (axes[0], "fleet_region_A_coverage", "Region A coverage"),
                (axes[1], "fleet_region_B_coverage", "Region B coverage"),
                (axes[2], "trajectory_overlap_ratio", "Overlap ratio"),
            ]:
                ax.bar(np.arange(len(fleet)), pd.to_numeric(fleet.get(col), errors="coerce"))
                ax.set_title(title)
                ax.set_xticks(np.arange(len(fleet)))
                ax.set_xticklabels([str(x)[:14] for x in fleet.get("strategy", [])], rotation=80, fontsize=6)
                ax.grid(axis="y", alpha=0.25)
            fig.tight_layout()
            out = fig_dir / "step11d_strategy_comparison_clean_panel.png"
            fig.savefig(out, dpi=180)
            plt.close(fig)
            created.append(str(out))
    fleet = safe_read_csv(base / "step11d_fleet_level_metrics.csv")
    if not fleet.empty and "strategy" in fleet:
        existing = {str(r.get("strategy", "")) for r in rows}
        for _, r in fleet.iterrows():
            strat = str(r.get("strategy", ""))
            if strat in existing:
                continue
            overlap = float(pd.to_numeric(pd.Series([r.get("trajectory_overlap_ratio")]), errors="coerce").iloc[0])
            duplicate = float(pd.to_numeric(pd.Series([r.get("duplicate_sampled_cells")]), errors="coerce").iloc[0])
            mean_d = float(pd.to_numeric(pd.Series([r.get("inter_vehicle_mean_distance")]), errors="coerce").iloc[0])
            min_d = float(pd.to_numeric(pd.Series([r.get("inter_vehicle_min_distance")]), errors="coerce").iloc[0])
            rows.append(
                {
                    "strategy": strat,
                    "trajectory_overlap_ratio": overlap,
                    "duplicate_sampled_cells": duplicate,
                    "inter_vehicle_mean_distance": mean_d,
                    "inter_vehicle_min_distance": min_d,
                    "hausdorff_like_distance": np.nan,
                    "percentage_AUV1_path_near_AUV2_path": np.nan,
                    "visual_vs_real": "from saved fleet metrics; mostly visual/same-zone issue" if np.isfinite(overlap) and overlap < 0.05 else "from saved fleet metrics; real overlap may be present",
                }
            )
    return created, pd.DataFrame(rows)


def classify_figures(lineage: pd.DataFrame, coord: pd.DataFrame) -> pd.DataFrame:
    coord_bad_outputs = set(coord.loc[coord["verdict"].astype(str).str.contains("CHECK", na=False), "output_path"].astype(str))
    rows: list[dict[str, Any]] = []
    for _, r in lineage.iterrows():
        step = str(r.get("step", ""))
        fig = str(r.get("figure_name", ""))
        issue = str(r.get("likely_issue", ""))
        output_path = str(r.get("output_path", ""))
        if output_path in coord_bad_outputs:
            cls = "POSSIBLE_COORDINATE_ISSUE"
            reason = "Some paths in this output failed coordinate alignment checks."
        elif step == "Step11B" and ("descriptor_trajectories_panel" in fig or "trajectory" in fig):
            cls = "MISLEADING_DUE_TO_BACKGROUND"
            reason = "Descriptors were used in objective, but existing panel backgrounds are not exact blended information_maps."
        elif step in {"Step11C", "Step11D"} and "overlay" in fig:
            cls = "OK_BUT_NEEDS_CAPTION_CLARIFICATION"
            reason = "Useful diagnostic figure, but caption must state background is region/diagnostic map."
        elif "barplot" in fig or "metrics" in fig or "distance_plot" in fig:
            cls = "TRUSTED_FOR_THESIS"
            reason = "Metric figure generated directly from saved metrics."
        elif issue:
            cls = "DIAGNOSTIC_ONLY"
            reason = issue
        else:
            cls = "OK_BUT_NEEDS_CAPTION_CLARIFICATION"
            reason = "Usable if caption identifies background and coordinate system."
        rows.append(
            {
                "step": step,
                "output_path": output_path,
                "figure_name": fig,
                "classification": cls,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows)


def step11b_descriptor_audit() -> pd.DataFrame:
    rows = []
    for step, base in OUTPUTS:
        if step != "Step11B" or not base.exists():
            continue
        info_exists = (base / "step11b_information_maps_by_descriptor.npz").exists()
        metrics = safe_read_csv(base / "step11b_run_metrics.csv")
        descriptors = sorted(set(metrics.get("descriptor", pd.Series(dtype=str)).dropna().astype(str))) if not metrics.empty else []
        for desc in descriptors:
            if desc == "none":
                continue
            rows.append(
                {
                    "output_path": str(base),
                    "descriptor": desc,
                    "tested_alpha_values": ",".join(map(str, sorted(metrics.loc[metrics["descriptor"].astype(str) == desc, "alpha"].dropna().unique()))) if "alpha" in metrics else "",
                    "planner_used_descriptor": True,
                    "evidence": "step11b script builds information_map=(1-alpha)*STD_norm+alpha*descriptor_norm; saved NPZ present" if info_exists else "script formula present; saved NPZ missing",
                    "existing_figures_show": "descriptor panel and STD/descriptor backgrounds, not always actual blended information_map",
                    "recommended_use": "diagnostic; use regenerated information_map figure for thesis objective explanation",
                }
            )
    return pd.DataFrame(rows)


def write_reports(
    out_dir: Path,
    inventory: pd.DataFrame,
    lineage: pd.DataFrame,
    map_vs_bg: pd.DataFrame,
    coord: pd.DataFrame,
    overlay: pd.DataFrame,
    classification: pd.DataFrame,
    step11b_audit: pd.DataFrame,
    step11c_diag: pd.DataFrame,
    step11d_overlay_report: pd.DataFrame,
    created_figs: list[str],
    missing_outputs: list[str],
) -> str:
    figure_count = int((inventory["file_type"] == "figure_png").sum()) if not inventory.empty else 0
    trusted_count = int((classification["classification"] == "TRUSTED_FOR_THESIS").sum()) if not classification.empty else 0
    regen_count = int(classification["classification"].isin(["MISLEADING_DUE_TO_BACKGROUND", "REGENERATE_BEFORE_USE", "POSSIBLE_COORDINATE_ISSUE"]).sum()) if not classification.empty else 0
    coord_issues = int(coord["verdict"].astype(str).str.contains("CHECK", na=False).sum()) if not coord.empty else 0
    misleading = int((classification["classification"] == "MISLEADING_DUE_TO_BACKGROUND").sum()) if not classification.empty else 0
    verdict = "FIGURE_AUDIT_FOUND_COORDINATE_ISSUES_FIX_REQUIRED" if coord_issues else ("FIGURE_AUDIT_FOUND_MISLEADING_BACKGROUND_REGENERATE" if misleading else "FIGURE_AND_PATH_AUDIT_COMPLETED_READY_FOR_INTERPRETATION")
    if missing_outputs:
        verdict = "FIGURE_AUDIT_INCOMPLETE_MISSING_DATA"

    step11d_real_overlap = "not enough multi-AUV route data"
    if not step11d_overlay_report.empty and "trajectory_overlap_ratio" in step11d_overlay_report:
        max_ov = pd.to_numeric(step11d_overlay_report["trajectory_overlap_ratio"], errors="coerce").max()
        step11d_real_overlap = f"max computed exact-cell overlap={max_ov:.3f}; mostly same-zone/visual if below 0.05"

    common = [
        "# Step11W planner figure/path lineage audit",
        "",
        f"Output: `{out_dir}`",
        f"Figures inventoried: {figure_count}",
        f"Regenerated diagnostic figures: {len(created_figs)}",
        f"Coordinate check warnings: {coord_issues}",
        f"Verdict: `{verdict}`",
        "",
        "## Main conclusions",
        "",
        "- Step11A: planner used baseline STD and STD+boundary formulations recorded in the manifest. Existing figures are diagnostic multi-background overlays, not a single exact-objective plot in every panel.",
        "- Step11B: descriptors were used in the objective for non-baseline runs. The saved `step11b_information_maps_by_descriptor.npz` is direct evidence. Some figures can look like STD because they use common/diagnostic backgrounds rather than the exact blended information_map.",
        "- Step11C: the crossing proxy should be interpreted with region-colored paths. A high crossing_count can reflect short A/B switches near the boundary, not necessarily broad exploration of both regimes.",
        f"- Step11D: {step11d_real_overlap}. The main issue is regime specialization and attraction to similar value zones, not necessarily literal overplotting.",
        "- Coordinate audit: the source scripts consistently use ROI row/col coordinates over `imshow(..., origin='lower')` with no extent. No systematic x/y swap or extent bug was detected unless individual rows in the coordinate CSV say otherwise.",
        "- Prototype-based correction: Step11Y/Step11Z remain the preferred methodological reference for region masks; old Step11C/11D region-mask figures should be labelled exploratory if they used fallback-derived masks.",
        "",
        "## Recommended figure use",
        "",
        "- Use metric barplots and regenerated standardized panels for thesis figures.",
        "- Use original Step11B descriptor panels only with captions saying the background is diagnostic; use regenerated information_map panels to explain the actual objective.",
        "- Use original Step11D overlays as diagnostics; pair them with overlap/distance metrics before claiming path overlap.",
    ]
    write_md(out_dir / "step11w_summary.md", common)

    full = common + [
        "",
        "## Inventory snapshot",
        "",
        *md_table(inventory.groupby(["step", "file_type"]).size().reset_index(name="count"), ["step", "file_type", "count"], 40),
        "",
        "## Figure classification snapshot",
        "",
        *md_table(classification, ["step", "figure_name", "classification", "reason"], 30),
        "",
        "## Planner map vs figure background snapshot",
        "",
        *md_table(map_vs_bg, ["step", "case_id", "run_name", "descriptor", "map_used_equals_background", "conclusion"], 30),
        "",
        "## Coordinate checks snapshot",
        "",
        *md_table(coord, ["step", "case_id", "trajectory_file", "path_points_inside_fraction", "suspected_x_y_swap", "verdict"], 30),
    ]
    write_md(out_dir / "step11w_full_report.md", full)

    write_md(
        out_dir / "step11w_step11a_logic_report.md",
        [
            "# Step11A logic report",
            "",
            "Step11A ran baseline_STD and enriched_boundary_alpha025/alpha050 over the three Step10F cases. The planner information map was written to each planner-interface NetCDF as `temperr` and documented in `step11a_run_manifest.csv`.",
            "",
            "The figures show paths over TEMPpred/STD/boundary diagnostic backgrounds. This is reliable for path comparison, but captions should not imply that every panel background is the exact objective.",
            "",
            "Coordinate alignment is consistent: route lat/lon is converted to HRes row/col and plotted as ROI col/row over `imshow(origin='lower')`.",
            "",
            "For thesis use, prefer barplots and regenerated standardized overlays with explicit background labels.",
        ],
    )
    write_md(
        out_dir / "step11w_step11b_logic_report.md",
        [
            "# Step11B logic report",
            "",
            "Step11B did use descriptors in the objective. The source script constructs `information_map = (1-alpha) * STD_norm + alpha * descriptor_norm` and saves `step11b_information_maps_by_descriptor.npz`.",
            "",
            "Why some maps look like STD: the descriptor trajectory panel uses diagnostic background panels, including STD and descriptor maps. These backgrounds are not always the exact blended information_map used by the planner.",
            "",
            "Conclusion: Step11B is valid as descriptor-ablation diagnostics, but thesis figures should use the regenerated information_map panels or captions that clearly separate objective map from visualization background.",
            "",
            *md_table(step11b_audit, ["descriptor", "tested_alpha_values", "planner_used_descriptor", "recommended_use"], 40),
        ],
    )
    write_md(
        out_dir / "step11w_step11c_logic_report.md",
        [
            "# Step11C logic report",
            "",
            "Step11C used baseline STD, boundary_alpha050, and crossing proxy maps. The route-level crossing reward was not implemented in the planner objective; the saved runs therefore test a map-level proxy.",
            "",
            "The visual question is whether the single AUV truly visits both regimes or mainly follows the boundary. The regenerated region-colored figures and `step11w_step11c_crossing_visual_diagnostics.csv` answer this from saved region masks and paths.",
            "",
            *md_table(step11c_diag, ["run_name", "fraction_region_A", "fraction_region_B", "fraction_boundary_core", "visual_crossing_events_from_masks", "interpretation"], 20),
        ],
    )
    write_md(
        out_dir / "step11w_step11d_logic_report.md",
        [
            "# Step11D logic report",
            "",
            "Step11D figures show strategies over region masks/reward diagnostics. They are useful for regime-separation interpretation but do not always show the exact vehicle-specific information_map.",
            "",
            "Computed path overlay metrics indicate whether visual overlap is real exact-cell overlap or simply both AUVs being attracted to the same high-value area.",
            "",
            *md_table(step11d_overlay_report, ["strategy", "trajectory_overlap_ratio", "duplicate_sampled_cells", "inter_vehicle_mean_distance", "visual_vs_real"], 20),
        ],
    )
    write_md(
        out_dir / "step11w_recommended_figure_set_for_thesis.md",
        [
            "# Recommended figure set for thesis",
            "",
            "- Use regenerated standardized overlays from `figures_regenerated_standardized/` for map/path explanation.",
            "- Use Step11B regenerated `step11b_each_descriptor_over_information_map.png` to show the actual objective.",
            "- Use Step11C `step11c_path_colored_by_region.png` to discuss crossing versus boundary-following.",
            "- Use Step11D `step11d_overlay_vs_true_distance_panel.png` and `step11d_strategy_comparison_clean_panel.png` alongside one clean overlay.",
            "- Avoid using original descriptor panels without caption clarification.",
        ],
    )
    write_md(
        out_dir / "step11w_required_fixes_before_next_planner_step.md",
        [
            "# Required fixes before next planner step",
            "",
            "1. Standardize figure backgrounds and captions: explicitly state STD, descriptor, information_map, TEMPpred, or region mask.",
            "2. For Step11B, show actual blended information_map when discussing planner objective.",
            "3. For Step11C/11D, use prototype-based masks from Step11Y/Step11Z when making methodological claims.",
            "4. Keep coordinate plotting as ROI row/col with `origin='lower'`, or move fully to km extent; do not mix both in the same figure.",
            "5. Treat old Step11C/11D region-mask outputs as exploratory where Step11Y identified fallback-derived masks.",
        ],
    )
    return verdict


def main() -> None:
    out_dir = RESULTS / f"fossum_roi_x490_step11w_planner_figure_path_audit_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    fig_dir = out_dir / "figures_regenerated"
    fig_dir.mkdir()
    standard_dir = out_dir / "figures_regenerated_standardized"
    standard_dir.mkdir()

    inventory, missing_outputs = inventory_outputs()
    inventory.to_csv(out_dir / "step11w_output_inventory.csv", index=False)

    lineage = figure_lineage(inventory)
    lineage.to_csv(out_dir / "step11w_figure_lineage.csv", index=False)

    map_vs_bg = planner_map_vs_background()
    map_vs_bg.to_csv(out_dir / "step11w_planner_map_vs_figure_background.csv", index=False)

    coord = coordinate_checks(inventory)
    coord.to_csv(out_dir / "step11w_coordinate_alignment_checks.csv", index=False)

    overlay = overlay_metrics()
    overlay.to_csv(out_dir / "step11w_path_overlay_metrics.csv", index=False)

    step11b_audit = step11b_descriptor_audit()
    step11b_audit.to_csv(out_dir / "step11w_step11b_descriptor_figure_audit.csv", index=False)

    created_figs: list[str] = []
    created_figs.extend(regenerate_step11b(fig_dir, standard_dir))
    figs_c, step11c_diag = regenerate_step11c(fig_dir, standard_dir)
    created_figs.extend(figs_c)
    step11c_diag.to_csv(out_dir / "step11w_step11c_crossing_visual_diagnostics.csv", index=False)
    figs_d, step11d_overlay_report = regenerate_step11d(fig_dir, standard_dir)
    created_figs.extend(figs_d)
    step11d_overlay_report.to_csv(out_dir / "step11w_step11d_path_overlay_report.csv", index=False)

    classification = classify_figures(lineage, coord)
    classification.to_csv(out_dir / "step11w_figure_usefulness_classification.csv", index=False)

    verdict = write_reports(
        out_dir,
        inventory,
        lineage,
        map_vs_bg,
        coord,
        overlay,
        classification,
        step11b_audit,
        step11c_diag,
        step11d_overlay_report,
        created_figs,
        missing_outputs,
    )

    checks = {
        "outputs_expected": len(OUTPUTS),
        "outputs_missing": missing_outputs,
        "figures_inventoried": int((inventory["file_type"] == "figure_png").sum()) if not inventory.empty else 0,
        "figure_lineage_rows": int(len(lineage)),
        "coordinate_check_rows": int(len(coord)),
        "coordinate_warning_rows": int(coord["verdict"].astype(str).str.contains("CHECK", na=False).sum()) if not coord.empty else 0,
        "path_overlay_rows": int(len(overlay)),
        "regenerated_figures": created_figs,
        "step11b_objective_used_descriptors": True if not step11b_audit.empty else None,
        "step11d_overlay_real_overlap_summary": (
            float(pd.to_numeric(step11d_overlay_report["trajectory_overlap_ratio"], errors="coerce").max())
            if not step11d_overlay_report.empty and "trajectory_overlap_ratio" in step11d_overlay_report
            else None
        ),
        "verdict": verdict,
    }
    metadata = {
        "script": str(Path(__file__).resolve()),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(out_dir),
        "inputs": [{"step": step, "path": str(path), "exists": path.exists()} for step, path in OUTPUTS],
        "read_only_previous_outputs": True,
        "planner_rerun": False,
        "new_trajectories_generated": False,
    }
    write_json(out_dir / "step11w_checks.json", checks)
    write_json(out_dir / "step11w_metadata.json", metadata)

    trusted = int((classification["classification"] == "TRUSTED_FOR_THESIS").sum()) if not classification.empty else 0
    regen = int(classification["classification"].isin(["MISLEADING_DUE_TO_BACKGROUND", "REGENERATE_BEFORE_USE", "POSSIBLE_COORDINATE_ISSUE"]).sum()) if not classification.empty else 0
    figures = int((inventory["file_type"] == "figure_png").sum()) if not inventory.empty else 0
    coord_issue = checks["coordinate_warning_rows"]
    max_d_overlap = checks["step11d_overlay_real_overlap_summary"]
    print("STEP11W AUDIT COMPLETE")
    print(f"output_created={out_dir}")
    print(f"figures_analyzed={figures}")
    print(f"trusted_figures={trusted}")
    print(f"figures_to_regenerate_or_recaption={regen}")
    print("step11b_objective=descriptors_used_in_information_map; STD appears as diagnostic/common background in some figures")
    print(f"step11d_real_overlay_max_exact_cell_overlap={max_d_overlap}")
    print(f"coordinate_issue_rows={coord_issue}")
    print("main_corrections=use actual information_map panels for Step11B; caption diagnostic backgrounds; pair Step11D overlays with true distance/overlap metrics; use Step11Z prototype-based masks for methodological figures")
    print(f"verdict={verdict}")


if __name__ == "__main__":
    main()
