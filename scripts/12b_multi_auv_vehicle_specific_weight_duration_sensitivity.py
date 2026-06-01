#!/usr/bin/env python
"""Step12B: multi-AUV vehicle-specific weight and duration sensitivity.

Native 2-AUV runs are used only for shared-map baselines. Vehicle-specific
maps are implemented as the explicit Step11 proxy: one 1-AUV solve per vehicle,
then combined fleet diagnostics. This keeps the original planner untouched.
"""

from __future__ import annotations

import argparse
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import step12_common as c


PREFIX = "fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity"
DURATIONS = [12.0, 24.0, 48.0]
WEIGHTS = [
    ("vehicle_specific_9010", 0.90, 0.10),
    ("vehicle_specific_8020", 0.80, 0.20),
    ("vehicle_specific_7030", 0.70, 0.30),
    ("vehicle_specific_6040", 0.60, 0.40),
    ("vehicle_specific_5050", 0.50, 0.50),
    ("vehicle_specific_2575", 0.25, 0.75),
    ("vehicle_specific_00100", 0.00, 1.00),
]


def logical_manifest(cases: pd.DataFrame, durations: list[float], include_boundary_support: bool) -> pd.DataFrame:
    rows = []
    for _, case in cases.iterrows():
        for duration in durations:
            rows.append(
                {
                    "case_id": case.case_id,
                    "date": case.date,
                    "predicted_class": int(case.predicted_class),
                    "mission_duration_requested_h": duration,
                    "strategy": "baseline_shared_STD",
                    "scope": "native_2auv_shared_map",
                    "vehicle_id": "fleet",
                    "w_STD": 1.0,
                    "w_region": 0.0,
                    "w_boundary": 0.0,
                    "role_assignment": "shared_STD",
                    "physical_run_id": f"{case.case_id}__multi_auv_{duration:g}h__baseline_shared_STD",
                    "prototype_based_maps": True,
                    "TEMPpred_used_as_objective": False,
                }
            )
            for name, w_std, w_reg in WEIGHTS:
                for vehicle_id, region in [(1, "region_A"), (2, "region_B")]:
                    rows.append(
                        {
                            "case_id": case.case_id,
                            "date": case.date,
                            "predicted_class": int(case.predicted_class),
                            "mission_duration_requested_h": duration,
                            "strategy": name,
                            "scope": "vehicle_specific_proxy_1auv",
                            "vehicle_id": vehicle_id,
                            "w_STD": w_std,
                            "w_region": w_reg,
                            "w_boundary": 0.0,
                            "role_assignment": f"AUV1=region_A;AUV2=region_B",
                            "physical_run_id": f"{case.case_id}__proxy_{duration:g}h__{name}__AUV{vehicle_id}_{region}",
                            "prototype_based_maps": True,
                            "TEMPpred_used_as_objective": False,
                        }
                    )
            if include_boundary_support:
                for vehicle_id, region in [(1, "region_A"), (2, "region_B")]:
                    rows.append(
                        {
                            "case_id": case.case_id,
                            "date": case.date,
                            "predicted_class": int(case.predicted_class),
                            "mission_duration_requested_h": duration,
                            "strategy": "vehicle_specific_603010_boundary_support",
                            "scope": "vehicle_specific_proxy_1auv_optional",
                            "vehicle_id": vehicle_id,
                            "w_STD": 0.60,
                            "w_region": 0.30,
                            "w_boundary": 0.10,
                            "role_assignment": "AUV1=region_A;AUV2=region_B;boundary_support",
                            "physical_run_id": f"{case.case_id}__proxy_{duration:g}h__vehicle_specific_603010_boundary_support__AUV{vehicle_id}_{region}",
                            "prototype_based_maps": True,
                            "TEMPpred_used_as_objective": False,
                        }
                    )
    return pd.DataFrame(rows)


def route_vehicle_metric(
    run_id: str,
    strategy: str,
    case_id: str,
    vehicle_id: int,
    route: dict[str, Any] | None,
    points: list[tuple[int, int]],
    maps_full: dict[str, np.ndarray],
    masks_full: dict[str, np.ndarray],
    valid_full: np.ndarray,
    solver_status: str,
    solver_runtime: float,
    mission_duration_requested_h: float,
) -> dict[str, Any]:
    pts = c.unique_valid(points, valid_full)
    labels = []
    for r, col in points:
        if 0 <= r < valid_full.shape[0] and 0 <= col < valid_full.shape[1] and bool(valid_full[r, col]):
            if bool(masks_full["region_A_full"][r, col]):
                labels.append(1)
            elif bool(masks_full["region_B_full"][r, col]):
                labels.append(2)
    compressed = []
    for label in labels:
        if not compressed or compressed[-1] != label:
            compressed.append(label)
    crossing_count = int(sum(1 for a, b in zip(compressed[:-1], compressed[1:]) if a != b))
    in_a = c.sample_values(points, masks_full["region_A_full"].astype(np.float32), valid_full)
    in_b = c.sample_values(points, masks_full["region_B_full"].astype(np.float32), valid_full)
    in_core = c.sample_values(points, masks_full["boundary_core_full"].astype(np.float32), valid_full)
    length = float(route.get("length_km", np.nan)) if route else np.nan
    actual_duration = np.nan
    if route and route.get("mission_duration_h") is not None:
        actual_duration = float(route.get("mission_duration_h") or 0) + float(route.get("mission_duration_m") or 0) / 60.0
    return {
        "run_id": run_id,
        "strategy": strategy,
        "case_id": case_id,
        "vehicle_id": vehicle_id,
        "mission_duration_requested_h": mission_duration_requested_h,
        "solver_status": solver_status,
        "solver_runtime": solver_runtime,
        "collected_STD": float(np.nansum(c.sample_values(points, maps_full["STD_full"], valid_full))) if pts else np.nan,
        "collected_region_A": float(np.nansum(in_a)) if in_a.size else np.nan,
        "collected_region_B": float(np.nansum(in_b)) if in_b.size else np.nan,
        "collected_boundary": float(np.nansum(c.sample_values(points, maps_full["boundary_full"], valid_full))) if pts else np.nan,
        "fraction_path_region_A": float(np.nanmean(in_a)) if in_a.size else np.nan,
        "fraction_path_region_B": float(np.nanmean(in_b)) if in_b.size else np.nan,
        "fraction_path_boundary_core": float(np.nanmean(in_core)) if in_core.size else np.nan,
        "crossing_count": crossing_count,
        "regions_visited": int(bool(np.any(in_a > 0.5))) + int(bool(np.any(in_b > 0.5))),
        "trajectory_length": length,
        "mission_duration": actual_duration,
        "sampled_cells": len(pts),
    }


def pair_distance(points_a: list[tuple[int, int]], points_b: list[tuple[int, int]], valid_full: np.ndarray) -> tuple[float, float]:
    a = np.asarray(c.unique_valid(points_a, valid_full), dtype=float)
    b = np.asarray(c.unique_valid(points_b, valid_full), dtype=float)
    if a.size == 0 or b.size == 0:
        return np.nan, np.nan
    if len(a) > 450:
        a = a[np.linspace(0, len(a) - 1, 450).astype(int)]
    if len(b) > 450:
        b = b[np.linspace(0, len(b) - 1, 450).astype(int)]
    d = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2))
    return float(np.min(d)), float(np.mean(np.min(d, axis=1)))


def fleet_metric(
    run_id: str,
    strategy: str,
    case_id: str,
    mission_duration_requested_h: float,
    vehicle_points: dict[int, list[tuple[int, int]]],
    vehicle_rows: list[dict[str, Any]],
    masks_full: dict[str, np.ndarray],
    valid_full: np.ndarray,
    solver_status: str,
    solver_runtime: float,
    role_assignment: str,
    w_std: float,
    w_region: float,
    w_boundary: float,
) -> dict[str, Any]:
    set1 = set(c.unique_valid(vehicle_points.get(1, []), valid_full))
    set2 = set(c.unique_valid(vehicle_points.get(2, []), valid_full))
    union = set1 | set2
    inter = set1 & set2
    region_a_cells = set(zip(*np.where(masks_full["region_A_full"] & valid_full)))
    region_b_cells = set(zip(*np.where(masks_full["region_B_full"] & valid_full)))
    overlap = len(inter) / max(len(union), 1)
    cov_a = len(union & region_a_cells) / max(len(region_a_cells), 1)
    cov_b = len(union & region_b_cells) / max(len(region_b_cells), 1)
    min_d, mean_d = pair_distance(list(set1), list(set2), valid_full)
    vdf = pd.DataFrame(vehicle_rows)
    if not vdf.empty and {1, 2}.issubset(set(vdf["vehicle_id"].astype(int))):
        v1 = vdf[vdf["vehicle_id"].astype(int).eq(1)].iloc[0]
        v2 = vdf[vdf["vehicle_id"].astype(int).eq(2)].iloc[0]
        specialization = max(0.0, float(v1.get("fraction_path_region_A", 0) - v1.get("fraction_path_region_B", 0))) / 2.0
        specialization += max(0.0, float(v2.get("fraction_path_region_B", 0) - v2.get("fraction_path_region_A", 0))) / 2.0
    else:
        specialization = np.nan
    return {
        "run_id": run_id,
        "strategy": strategy,
        "case_id": case_id,
        "mission_duration_requested_h": mission_duration_requested_h,
        "role_assignment": role_assignment,
        "w_STD": w_std,
        "w_region": w_region,
        "w_boundary": w_boundary,
        "solver_status": solver_status,
        "solver_runtime": solver_runtime,
        "fleet_collected_STD": float(vdf["collected_STD"].sum()) if not vdf.empty else np.nan,
        "fleet_collected_boundary": float(vdf["collected_boundary"].sum()) if not vdf.empty else np.nan,
        "fleet_region_A_coverage": float(cov_a),
        "fleet_region_B_coverage": float(cov_b),
        "region_balance": float(1.0 - abs(cov_a - cov_b) / max(cov_a + cov_b, 1e-9)),
        "regime_specialization_score": float(specialization),
        "inter_vehicle_mean_distance": mean_d,
        "inter_vehicle_min_distance": min_d,
        "trajectory_overlap_ratio": float(overlap),
        "duplicate_sampled_cells": int(len(inter)),
        "fleet_total_area_covered": int(len(union)),
        "complementarity_score": float(0.35 * (cov_a + cov_b) + 0.25 * (1.0 - overlap) + 0.25 * np.nan_to_num(specialization, nan=0.0) + 0.15 * (1.0 - abs(cov_a - cov_b) / max(cov_a + cov_b, 1e-9))),
    }


def build_map(std: np.ndarray, role_map: np.ndarray, boundary: np.ndarray, mask: np.ndarray, w_std: float, w_region: float, w_boundary: float) -> np.ndarray:
    return c.normalize_map(w_std * std + w_region * role_map + w_boundary * boundary, mask)


def summarize_fleet(fleet: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    f = fleet.copy()
    baseline = (
        f[f["strategy"].eq("baseline_shared_STD")]
        .groupby(["case_id", "mission_duration_requested_h"], as_index=False)
        .agg(baseline_fleet_STD=("fleet_collected_STD", "max"), baseline_runtime=("solver_runtime", "max"))
    )
    f = f.merge(baseline, on=["case_id", "mission_duration_requested_h"], how="left")
    f["STD_retention"] = f["fleet_collected_STD"] / f["baseline_fleet_STD"]
    f["STD_loss_relative_to_baseline"] = 1.0 - f["STD_retention"]
    f["region_B_coverage_gain"] = f["fleet_region_B_coverage"] - f.groupby(["case_id", "mission_duration_requested_h"])["fleet_region_B_coverage"].transform("first")
    f["runtime_score"] = 1.0 / (1.0 + pd.to_numeric(f["solver_runtime"], errors="coerce").fillna(f["solver_runtime"].max()))
    f["recommendation_score"] = (
        0.30 * f["STD_retention"].fillna(0)
        + 0.25 * f["fleet_region_B_coverage"].fillna(0)
        + 0.20 * f["regime_specialization_score"].fillna(0)
        + 0.10 * (1.0 - f["trajectory_overlap_ratio"].fillna(1))
        + 0.10 * f["region_balance"].fillna(0)
        + 0.05 * f["runtime_score"].fillna(0)
    )
    eligible = f[f["solver_status"].astype(str).isin(["SUCCESS", "REUSED"]) & (f["STD_retention"] >= 0.70) & ~f["strategy"].eq("baseline_shared_STD")].copy()
    best = (
        eligible.sort_values(["case_id", "mission_duration_requested_h", "recommendation_score"], ascending=[True, True, False])
        .groupby(["case_id", "mission_duration_requested_h"], as_index=False)
        .head(1)
    )
    weight_summary = (
        f.groupby(["strategy", "w_STD", "w_region", "w_boundary"], as_index=False)
        .agg(
            mean_STD_retention=("STD_retention", "mean"),
            mean_region_B_coverage=("fleet_region_B_coverage", "mean"),
            mean_specialization=("regime_specialization_score", "mean"),
            mean_overlap=("trajectory_overlap_ratio", "mean"),
            mean_runtime=("solver_runtime", "mean"),
            mean_score=("recommendation_score", "mean"),
        )
        .sort_values("mean_score", ascending=False)
    )
    duration_summary = (
        f.groupby(["mission_duration_requested_h", "strategy"], as_index=False)
        .agg(
            mean_fleet_STD=("fleet_collected_STD", "mean"),
            mean_region_B_coverage=("fleet_region_B_coverage", "mean"),
            mean_specialization=("regime_specialization_score", "mean"),
            mean_runtime=("solver_runtime", "mean"),
            success_rate=("solver_status", lambda s: float(s.astype(str).isin(["SUCCESS", "REUSED"]).mean())),
        )
    )
    runtime_summary = (
        f.groupby(["mission_duration_requested_h", "strategy"], as_index=False)
        .agg(mean_solver_runtime=("solver_runtime", "mean"), max_solver_runtime=("solver_runtime", "max"), fleet_rows=("run_id", "count"))
    )
    return f, weight_summary, duration_summary, runtime_summary, best


def run_fleet_strategy(
    zutils,
    s11a,
    case_id: str,
    duration: float,
    strategy: str,
    role_assignment: str,
    info_maps: dict[int, np.ndarray],
    native_2auv: bool,
    std: np.ndarray,
    mask: np.ndarray,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    bathy_hres: np.ndarray,
    planner: Path,
    config_1auv: str,
    config_2auv: str,
    outdir: Path,
    timeout_s: int,
    skip_existing: bool,
    maps_full: dict[str, np.ndarray],
    masks_full: dict[str, np.ndarray],
    valid_full: np.ndarray,
    w_std: float,
    w_region: float,
    w_boundary: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[int, list[tuple[int, int]]]]:
    diagnostics = []
    vehicle_rows = []
    vehicle_points: dict[int, list[tuple[int, int]]] = {}
    if native_2auv:
        run_id = f"{case_id}__multi_auv_{duration:g}h__{strategy}"
        diag, routes, _run_dir = c.run_planner(zutils, s11a, run_id, std, mask, lat_hres, lon_hres, bathy_hres, planner, config_2auv, outdir, timeout_s, skip_existing)
        diagnostics.append(diag)
        for vehicle_id, route in enumerate(routes[:2], start=1):
            pts = c.route_points_for_route(s11a, route, lat_hres, lon_hres)
            vehicle_points[vehicle_id] = pts
            vehicle_rows.append(route_vehicle_metric(run_id, strategy, case_id, vehicle_id, route, pts, maps_full, masks_full, valid_full, str(diag.get("solver_status", "")), float(diag.get("solver_runtime_s", np.nan)), duration))
        fleet = fleet_metric(run_id, strategy, case_id, duration, vehicle_points, vehicle_rows, masks_full, valid_full, str(diag.get("solver_status", "")), float(diag.get("solver_runtime_s", np.nan)), role_assignment, w_std, w_region, w_boundary)
        return diagnostics, fleet, vehicle_rows, vehicle_points

    statuses = []
    runtime_sum = 0.0
    for vehicle_id in [1, 2]:
        role = "region_A" if ("AUV1=region_A" in role_assignment and vehicle_id == 1) or ("AUV2=region_A" in role_assignment and vehicle_id == 2) else "region_B"
        run_id = f"{case_id}__proxy_{duration:g}h__{strategy}__AUV{vehicle_id}_{role}"
        diag, routes, _run_dir = c.run_planner(zutils, s11a, run_id, info_maps[vehicle_id], mask, lat_hres, lon_hres, bathy_hres, planner, config_1auv, outdir, timeout_s, skip_existing)
        diagnostics.append(diag)
        statuses.append(str(diag.get("solver_status", "")))
        runtime_sum += float(diag.get("solver_runtime_s", np.nan)) if pd.notna(diag.get("solver_runtime_s", np.nan)) else 0.0
        route = routes[0] if routes else None
        pts = c.route_points_for_route(s11a, route, lat_hres, lon_hres) if route else []
        vehicle_points[vehicle_id] = pts
        vehicle_rows.append(route_vehicle_metric(run_id, strategy, case_id, vehicle_id, route, pts, maps_full, masks_full, valid_full, str(diag.get("solver_status", "")), float(diag.get("solver_runtime_s", np.nan)), duration))
    fleet_status = "SUCCESS" if statuses and all(s in ["SUCCESS", "REUSED"] for s in statuses) else "FAILED"
    fleet = fleet_metric(f"{case_id}__proxy_{duration:g}h__{strategy}", strategy, case_id, duration, vehicle_points, vehicle_rows, masks_full, valid_full, fleet_status, runtime_sum, role_assignment, w_std, w_region, w_boundary)
    return diagnostics, fleet, vehicle_rows, vehicle_points


def create_figures(outdir: Path, fleet: pd.DataFrame, vehicle: pd.DataFrame, route_points: dict[str, dict[int, list[tuple[int, int]]]], cases: pd.DataFrame, maps: dict[str, np.ndarray], temp: np.ndarray, mask: np.ndarray) -> None:
    figdir = outdir / "figures"
    def fig_strategy_name(strategy: Any) -> str:
        return c.short_name(str(strategy), max_prefix=28)

    for _, case in cases.iterrows():
        idx = int(case.case_order)
        case_id = str(case.case_id)
        std = maps["baseline_STD_norm"][idx]
        cold = maps["cold_region_norm"][idx]
        warm = maps["warm_region_norm"][idx]
        region_a = np.load(outdir / "masks" / f"{case_id}_region_A_mask.npy")
        region_b = np.load(outdir / "masks" / f"{case_id}_region_B_mask.npy")
        for duration in sorted(fleet["mission_duration_requested_h"].dropna().unique()):
            sub = fleet[(fleet["case_id"].eq(case_id)) & (fleet["mission_duration_requested_h"].eq(duration))].copy()
            if sub.empty:
                continue
            for r in sub.itertuples():
                sname = fig_strategy_name(r.strategy)
                paths = {f"AUV{vid}": pts for vid, pts in route_points.get(str(r.run_id), {}).items()}
                c.plot_paths_on_map(std, paths, figdir / f"step12b_{case_id}_{duration:g}h_{sname}_STD.png", f"{case_id} {duration:g}h {r.strategy} over STD_norm", "viridis", 0, 1, color_cycle=["white", "yellow"], region_a=region_a, region_b=region_b)
                c.plot_paths_on_map(temp[idx], paths, figdir / f"step12b_{case_id}_{duration:g}h_{sname}_TEMPpred_diag.png", f"{case_id} {duration:g}h {r.strategy} over TEMPpred diagnostic background", "coolwarm", None, None, color_cycle=["white", "yellow"], diagnostic_note="TEMPpred is diagnostic background only; objective maps are vehicle-specific information_maps.", region_a=region_a, region_b=region_b)
                if str(r.strategy) != "baseline_shared_STD":
                    map1 = build_map(std, cold if "AUV1=region_A" in str(r.role_assignment) else warm, maps["boundary_score_norm"][idx], mask, float(r.w_STD), float(r.w_region), float(r.w_boundary))
                    map2 = build_map(std, warm if "AUV2=region_B" in str(r.role_assignment) else cold, maps["boundary_score_norm"][idx], mask, float(r.w_STD), float(r.w_region), float(r.w_boundary))
                    c.plot_paths_on_map(map1, {"AUV1": paths.get("AUV1", [])}, figdir / f"step12b_{case_id}_{duration:g}h_{sname}_AUV1_info.png", f"{case_id} {duration:g}h {r.strategy} AUV1 over real information_map", "viridis", 0, 1, color_cycle=["white"], region_a=region_a, region_b=region_b)
                    c.plot_paths_on_map(map2, {"AUV2": paths.get("AUV2", [])}, figdir / f"step12b_{case_id}_{duration:g}h_{sname}_AUV2_info.png", f"{case_id} {duration:g}h {r.strategy} AUV2 over real information_map", "viridis", 0, 1, color_cycle=["yellow"], region_a=region_a, region_b=region_b)
            best = sub.sort_values("recommendation_score", ascending=False).head(1)
            if not best.empty:
                r = best.iloc[0]
                paths = {f"AUV{vid}": pts for vid, pts in route_points.get(str(r["run_id"]), {}).items()}
                c.plot_paths_on_map(temp[idx], paths, figdir / f"step12b_{case_id}_{duration:g}h_best_configuration_panel.png", f"{case_id} {duration:g}h best configuration over TEMPpred diagnostic background", "coolwarm", None, None, color_cycle=["white", "yellow"], diagnostic_note=f"Best={r['strategy']}; TEMPpred diagnostic only.", region_a=region_a, region_b=region_b)
    c.plot_grouped_bar(fleet, "strategy", "fleet_region_B_coverage", "mission_duration_requested_h", figdir / "step12b_weight_tradeoff_region_B_coverage.png", "Step12B weight tradeoff: region B coverage")
    c.plot_grouped_bar(fleet, "mission_duration_requested_h", "fleet_collected_STD", "strategy", figdir / "step12b_duration_tradeoff_fleet_STD.png", "Step12B duration tradeoff: fleet STD")
    c.plot_grouped_bar(fleet, "strategy", "solver_runtime", "mission_duration_requested_h", figdir / "step12b_runtime_comparison.png", "Step12B runtime comparison")
    c.plot_scatter(fleet, "fleet_collected_STD", "fleet_region_B_coverage", "strategy", figdir / "step12b_STD_collected_vs_region_coverage.png", "Step12B STD collected vs region B coverage")
    c.plot_scatter(fleet, "trajectory_overlap_ratio", "regime_specialization_score", "strategy", figdir / "step12b_overlap_vs_specialization.png", "Step12B overlap vs specialization")


def write_reports(outdir: Path, fleet: pd.DataFrame, vehicle: pd.DataFrame, weight_summary: pd.DataFrame, duration_summary: pd.DataFrame, runtime_summary: pd.DataFrame, best: pd.DataFrame, checks: dict[str, Any]) -> None:
    lines = [
        "# Step12B multi-AUV vehicle-specific weight sensitivity",
        "",
        f"- Verdict: `{checks['verdict']}`",
        f"- Fleet rows: {len(fleet)}",
        f"- Vehicle rows: {len(vehicle)}",
        f"- Prototype-based maps only: {checks['prototype_based_maps_only']}",
        f"- TEMPpred used as objective: {checks['TEMPpred_used_as_objective']}",
        "",
        "## Best weight recommendation",
        c.md_table(best, ["case_id", "mission_duration_requested_h", "strategy", "w_STD", "w_region", "role_assignment", "STD_retention", "fleet_region_B_coverage", "regime_specialization_score", "trajectory_overlap_ratio", "solver_runtime", "recommendation_score"], 50),
        "",
        "## Weight sensitivity",
        c.md_table(weight_summary, list(weight_summary.columns), 60),
        "",
        "## Duration sensitivity",
        c.md_table(duration_summary, list(duration_summary.columns), 80),
        "",
        "## Methodological note",
        "- baseline_shared_STD is native 2-AUV with one shared STD map.",
        "- vehicle_specific_* strategies are proxy/wrapper runs: AUV1 and AUV2 are solved separately and combined into fleet metrics.",
        "- This is intentionally non-destructive and does not modify the planner objective.",
    ]
    report = "\n".join(lines)
    c.write_text(outdir / "step12b_summary.md", report)
    c.write_text(outdir / "step12b_report.md", report + "\n\n## Runtime summary\n" + c.md_table(runtime_summary, list(runtime_summary.columns), 120))
    c.write_text(outdir / "step12b_next_step_recommendation.md", "# Step12B next step recommendation\n\nUse the best vehicle-specific weight as the main multi-AUV sensitivity result. If this becomes the final method, the next planner improvement should be native vehicle-specific prize maps.\n\n" + c.md_table(best, ["case_id", "mission_duration_requested_h", "strategy", "recommendation_score"], 50))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step12B multi-AUV vehicle-specific weight and duration sensitivity.")
    parser.add_argument("--step11y", type=Path, default=None)
    parser.add_argument("--planner", type=Path, default=c.PLANNER)
    parser.add_argument("--output-root", type=Path, default=c.RESULTS)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--durations", nargs="*", type=float, default=DURATIONS)
    parser.add_argument("--cases", nargs="*", choices=c.CASE_ORDER, default=c.CASE_ORDER)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--include-boundary-support", action="store_true")
    parser.add_argument("--workers", type=int, default=1, help="Number of independent fleet/planner tasks to launch in parallel.")
    parser.add_argument("--resume-output", type=Path, default=None, help="Existing Step12B output folder to reuse with --skip-existing.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")
    if args.workers > 3:
        print("WARNING: --workers > 3 can overload CPU/RAM because each worker launches planner processes.")
    start = time.perf_counter()
    cases, maps, step11y = c.load_step11y_maps(args.step11y)
    cases = cases[cases["case_id"].isin(args.cases)].copy().reset_index(drop=True)
    manifest = logical_manifest(cases, args.durations, args.include_boundary_support)
    initial_physical = int(manifest["physical_run_id"].nunique())
    if args.dry_run:
        role_swap_runs = len(cases) * len(args.durations) * 2
        print(f"Step12B dry-run: initial_physical_runs={initial_physical}, role_swap_runs={role_swap_runs}, total_expected={initial_physical + role_swap_runs}, workers={args.workers}, step11y={c.rel(step11y)}")
        print(manifest.groupby(["case_id", "mission_duration_requested_h"])["physical_run_id"].nunique().to_string())
        return 0

    s11a = c.load_step11a()
    zutils = c.load_step11z()
    ab = c.load_step11ab()
    temp, mask = c.load_step10f_temp_mask()
    lat_hres, lon_hres, bathy_hres = c.load_hres()
    valid_full = s11a.embed_roi_to_hres(mask.astype(np.float32), mask, fill=np.nan) > 0.5
    original_config = s11a.read_config_text(args.planner / "Config_file.py")
    outdir = args.resume_output.resolve() if args.resume_output else c.prepare_outdir(args.output_root, PREFIX)
    if args.resume_output:
        for sub in ["planner_inputs", "planner_runs", "planner_configs", "figures", "masks"]:
            (outdir / sub).mkdir(parents=True, exist_ok=True)
    manifest.to_csv(outdir / "step12b_run_manifest.csv", index=False)

    diagnostics_rows: list[dict[str, Any]] = []
    vehicle_rows: list[dict[str, Any]] = []
    fleet_rows: list[dict[str, Any]] = []
    route_points_by_fleet: dict[str, dict[int, list[tuple[int, int]]]] = {}

    for _, case in cases.iterrows():
        idx = int(case.case_order)
        case_id = str(case.case_id)
        region_a, region_b, region_meta = c.make_region_masks(ab, maps["cold_region_norm"][idx], maps["warm_region_norm"][idx], mask)
        core = c.boundary_core(maps["boundary_score_norm"][idx], mask)
        np.save(outdir / "masks" / f"{case_id}_region_A_mask.npy", region_a)
        np.save(outdir / "masks" / f"{case_id}_region_B_mask.npy", region_b)
        np.save(outdir / "masks" / f"{case_id}_boundary_core_mask.npy", core)
        c.write_json(outdir / "masks" / f"{case_id}_region_meta.json", region_meta)

    initial_tasks: list[dict[str, Any]] = []
    for duration in args.durations:
        config_1auv = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=duration, auv_number=1)
        config_2auv = s11a.generated_config(original_config, single_auv=False, mission_duration_hours=duration, auv_number=2)
        (outdir / "planner_configs" / f"Config_file_step12b_1auv_{duration:g}h.py").write_text(config_1auv, encoding="utf-8")
        (outdir / "planner_configs" / f"Config_file_step12b_2auv_{duration:g}h.py").write_text(config_2auv, encoding="utf-8")
        for _, case in cases.iterrows():
            idx = int(case.case_order)
            case_id = str(case.case_id)
            std = maps["baseline_STD_norm"][idx]
            boundary = maps["boundary_score_norm"][idx]
            cold = maps["cold_region_norm"][idx]
            warm = maps["warm_region_norm"][idx]
            region_a = np.load(outdir / "masks" / f"{case_id}_region_A_mask.npy")
            region_b = np.load(outdir / "masks" / f"{case_id}_region_B_mask.npy")
            core = np.load(outdir / "masks" / f"{case_id}_boundary_core_mask.npy")
            maps_full = {
                "STD_full": s11a.embed_roi_to_hres(std, mask, fill=np.nan),
                "boundary_full": s11a.embed_roi_to_hres(boundary, mask, fill=np.nan),
            }
            masks_full = {
                "region_A_full": s11a.embed_roi_to_hres(region_a.astype(np.float32), mask, fill=np.nan) > 0.5,
                "region_B_full": s11a.embed_roi_to_hres(region_b.astype(np.float32), mask, fill=np.nan) > 0.5,
                "boundary_core_full": s11a.embed_roi_to_hres(core.astype(np.float32), mask, fill=np.nan) > 0.5,
            }
            initial_tasks.append(
                {
                    "case_id": case_id,
                    "duration": duration,
                    "strategy": "baseline_shared_STD",
                    "role_assignment": "shared_STD",
                    "info_maps": {},
                    "native_2auv": True,
                    "std": std,
                    "config_1auv": config_1auv,
                    "config_2auv": config_2auv,
                    "maps_full": maps_full,
                    "masks_full": masks_full,
                    "w_std": 1.0,
                    "w_region": 0.0,
                    "w_boundary": 0.0,
                }
            )
            configs = list(WEIGHTS)
            if args.include_boundary_support:
                configs.append(("vehicle_specific_603010_boundary_support", 0.60, 0.30))
            for name, w_std, w_reg in configs:
                w_boundary = 0.10 if name.endswith("boundary_support") else 0.0
                actual_w_std = 0.60 if name.endswith("boundary_support") else w_std
                actual_w_reg = 0.30 if name.endswith("boundary_support") else w_reg
                info_maps = {
                    1: build_map(std, cold, boundary, mask, actual_w_std, actual_w_reg, w_boundary),
                    2: build_map(std, warm, boundary, mask, actual_w_std, actual_w_reg, w_boundary),
                }
                initial_tasks.append(
                    {
                        "case_id": case_id,
                        "duration": duration,
                        "strategy": name,
                        "role_assignment": "AUV1=region_A;AUV2=region_B",
                        "info_maps": info_maps,
                        "native_2auv": False,
                        "std": std,
                        "config_1auv": config_1auv,
                        "config_2auv": config_2auv,
                        "maps_full": maps_full,
                        "masks_full": masks_full,
                        "w_std": actual_w_std,
                        "w_region": actual_w_reg,
                        "w_boundary": w_boundary,
                    }
                )

    def execute_fleet_task(task: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[int, list[tuple[int, int]]]]:
        return run_fleet_strategy(
            zutils,
            s11a,
            task["case_id"],
            task["duration"],
            task["strategy"],
            task["role_assignment"],
            task["info_maps"],
            task["native_2auv"],
            task["std"],
            mask,
            lat_hres,
            lon_hres,
            bathy_hres,
            args.planner,
            task["config_1auv"],
            task["config_2auv"],
            outdir,
            args.timeout_s,
            args.skip_existing,
            task["maps_full"],
            task["masks_full"],
            valid_full,
            task["w_std"],
            task["w_region"],
            task["w_boundary"],
        )

    def collect_result(result: tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[int, list[tuple[int, int]]]]) -> None:
        diag, fleet, vehicles, points = result
        diagnostics_rows.extend(diag)
        vehicle_rows.extend(vehicles)
        fleet_rows.append(fleet)
        route_points_by_fleet[str(fleet["run_id"])] = points

    print(f"Step12B launching {len(initial_tasks)} initial fleet tasks with workers={args.workers}")
    if args.workers == 1:
        for task in initial_tasks:
            collect_result(execute_fleet_task(task))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(execute_fleet_task, task) for task in initial_tasks]
            for future in as_completed(futures):
                collect_result(future.result())

    initial_fleet = pd.DataFrame(fleet_rows)
    initial_fleet_scored, _ws, _ds, _rs, best_initial = summarize_fleet(initial_fleet)

    # Role swap for the best non-baseline configuration in each case/duration.
    role_swap_tasks: list[dict[str, Any]] = []
    for r in best_initial.itertuples():
        case_id = str(r.case_id)
        duration = float(r.mission_duration_requested_h)
        idx = c.get_case_index(cases, case_id)
        std = maps["baseline_STD_norm"][idx]
        boundary = maps["boundary_score_norm"][idx]
        cold = maps["cold_region_norm"][idx]
        warm = maps["warm_region_norm"][idx]
        region_a = np.load(outdir / "masks" / f"{case_id}_region_A_mask.npy")
        region_b = np.load(outdir / "masks" / f"{case_id}_region_B_mask.npy")
        core = np.load(outdir / "masks" / f"{case_id}_boundary_core_mask.npy")
        maps_full = {"STD_full": s11a.embed_roi_to_hres(std, mask, fill=np.nan), "boundary_full": s11a.embed_roi_to_hres(boundary, mask, fill=np.nan)}
        masks_full = {
            "region_A_full": s11a.embed_roi_to_hres(region_a.astype(np.float32), mask, fill=np.nan) > 0.5,
            "region_B_full": s11a.embed_roi_to_hres(region_b.astype(np.float32), mask, fill=np.nan) > 0.5,
            "boundary_core_full": s11a.embed_roi_to_hres(core.astype(np.float32), mask, fill=np.nan) > 0.5,
        }
        config_1auv = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=duration, auv_number=1)
        config_2auv = s11a.generated_config(original_config, single_auv=False, mission_duration_hours=duration, auv_number=2)
        info_maps = {
            1: build_map(std, warm, boundary, mask, float(r.w_STD), float(r.w_region), float(r.w_boundary)),
            2: build_map(std, cold, boundary, mask, float(r.w_STD), float(r.w_region), float(r.w_boundary)),
        }
        strategy = f"role_swap_of_{r.strategy}"
        role_swap_tasks.append(
            {
                "case_id": case_id,
                "duration": duration,
                "strategy": strategy,
                "role_assignment": "AUV1=region_B;AUV2=region_A",
                "info_maps": info_maps,
                "native_2auv": False,
                "std": std,
                "config_1auv": config_1auv,
                "config_2auv": config_2auv,
                "maps_full": maps_full,
                "masks_full": masks_full,
                "w_std": float(r.w_STD),
                "w_region": float(r.w_region),
                "w_boundary": float(r.w_boundary),
            }
        )

    print(f"Step12B launching {len(role_swap_tasks)} role-swap fleet tasks with workers={args.workers}")
    if args.workers == 1:
        for task in role_swap_tasks:
            collect_result(execute_fleet_task(task))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(execute_fleet_task, task) for task in role_swap_tasks]
            for future in as_completed(futures):
                collect_result(future.result())

    vehicle_df = pd.DataFrame(vehicle_rows)
    fleet_df, weight_summary, duration_summary, runtime_summary, best = summarize_fleet(pd.DataFrame(fleet_rows))
    diagnostics = pd.DataFrame(diagnostics_rows)
    vehicle_df.to_csv(outdir / "step12b_vehicle_level_metrics.csv", index=False)
    fleet_df.to_csv(outdir / "step12b_fleet_level_metrics.csv", index=False)
    weight_summary.to_csv(outdir / "step12b_weight_sensitivity_summary.csv", index=False)
    duration_summary.to_csv(outdir / "step12b_duration_sensitivity_summary.csv", index=False)
    runtime_summary.to_csv(outdir / "step12b_runtime_summary.csv", index=False)
    diagnostics.to_csv(outdir / "step12b_solver_diagnostics.csv", index=False)
    best.to_csv(outdir / "step12b_best_weight_recommendation.csv", index=False)

    create_figures(outdir, fleet_df, vehicle_df, route_points_by_fleet, cases, maps, temp, mask)
    checks = {
        "step": "Step12B",
        "output_dir": c.rel(outdir),
        "step11y": c.rel(step11y),
        "initial_physical_runs": initial_physical,
        "workers": int(args.workers),
        "resume_output": c.rel(outdir) if args.resume_output else "",
        "role_swap_fleet_rows": int(fleet_df["strategy"].astype(str).str.startswith("role_swap").sum()),
        "total_physical_runs_executed_or_reused": int(len(diagnostics)),
        "fleet_rows": int(len(fleet_df)),
        "vehicle_rows": int(len(vehicle_df)),
        "durations_tested": sorted([float(x) for x in fleet_df["mission_duration_requested_h"].dropna().unique()]),
        "weights_tested": sorted(fleet_df["strategy"].dropna().astype(str).unique().tolist()),
        "prototype_based_maps_only": True,
        "TEMPpred_used_as_objective": False,
        "vehicle_specific_is_proxy_wrapper": True,
        "all_runs_have_status": bool(fleet_df["solver_status"].astype(str).ne("").all()),
        "all_runtimes_recorded": bool(pd.to_numeric(fleet_df["solver_runtime"], errors="coerce").notna().all()),
        "figures_created": len(list((outdir / "figures").glob("*.png"))),
        "total_script_runtime_s": float(time.perf_counter() - start),
        "verdict": "STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED" if not best.empty else "STEP12_COMPLETED_WITH_TRADEOFFS_REVIEW_REQUIRED",
    }
    c.write_json(outdir / "step12b_checks.json", checks)
    c.write_json(outdir / "step12b_metadata.json", {"created_at": c.now_tag(), "inputs": {"step11y": c.rel(step11y), "step10f": c.rel(c.STEP10F)}})
    write_reports(outdir, fleet_df, vehicle_df, weight_summary, duration_summary, runtime_summary, best, checks)
    print(f"Step12B complete: {c.rel(outdir)}")
    print(f"Verdict: {checks['verdict']}")
    print(f"Fleet rows: {checks['fleet_rows']}; physical runs: {checks['total_physical_runs_executed_or_reused']}; figures: {checks['figures_created']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
