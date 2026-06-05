#!/usr/bin/env python
"""Step12A: single-AUV weight and mission-duration sensitivity.

Uses prototype-based maps from Step11Y only:
- day-specific STD_norm;
- descriptors from the predicted prototype class;
- TEMPpred only as diagnostic plotting background.
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


PREFIX = "fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity"
DESCRIPTORS = {
    "boundary_score": "boundary_score_norm",
    "boundary_distance_score_r1_cells": "boundary_distance_score_r1_cells_norm",
    "boundary_distance_score_r2_cells": "boundary_distance_score_r2_cells_norm",
    "boundary_distance_score_r3_cells": "boundary_distance_score_r3_cells_norm",
    "boundary_distance_score_r5_cells": "boundary_distance_score_r5_cells_norm",
    "boundary_distance_score_r8_cells": "boundary_distance_score_r8_cells_norm",
    "representative_zone": "representative_zone_norm",
    "interest_map": "interest_map_norm",
}
ALPHAS = [0.0, 0.25, 0.50, 0.75, 1.0]
DURATIONS = [12.0, 24.0, 48.0]


def alpha_tag(alpha: float) -> str:
    return f"alpha{int(round(alpha * 100)):03d}"


def logical_manifest(cases: pd.DataFrame, durations: list[float], descriptors: list[str]) -> pd.DataFrame:
    rows = []
    for _, case in cases.iterrows():
        for duration in durations:
            for descriptor in descriptors:
                for alpha in ALPHAS:
                    run_name = "baseline_STD" if alpha == 0 else f"{descriptor}_{alpha_tag(alpha)}"
                    physical_run_id = (
                        f"{case.case_id}__single_auv_{duration:g}h__baseline_STD"
                        if alpha == 0
                        else f"{case.case_id}__single_auv_{duration:g}h__{descriptor}_{alpha_tag(alpha)}"
                    )
                    rows.append(
                        {
                            "case_id": case.case_id,
                            "date": case.date,
                            "predicted_class": int(case.predicted_class),
                            "mission_duration_requested_h": duration,
                            "descriptor": descriptor,
                            "alpha": alpha,
                            "run_name": run_name,
                            "physical_run_id": physical_run_id,
                            "deduplicated_baseline": bool(alpha == 0),
                            "prototype_based_maps": True,
                            "TEMPpred_used_as_objective": False,
                            "information_map_formula": "STD_norm" if alpha == 0 else f"(1-{alpha:.2f})*STD_norm + {alpha:.2f}*{descriptor}",
                        }
                    )
    return pd.DataFrame(rows)


def regime_metrics(points: list[tuple[int, int]], masks_full: dict[str, np.ndarray], valid_full: np.ndarray) -> dict[str, Any]:
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
    cross = int(sum(1 for a, b in zip(compressed[:-1], compressed[1:]) if a != b))
    in_a = c.sample_values(points, masks_full["region_A_full"].astype(np.float32), valid_full)
    in_b = c.sample_values(points, masks_full["region_B_full"].astype(np.float32), valid_full)
    return {
        "regions_visited": int(bool(np.any(in_a > 0.5))) + int(bool(np.any(in_b > 0.5))),
        "crossing_count": cross,
        "fraction_path_region_A": float(np.nanmean(in_a)) if in_a.size else np.nan,
        "fraction_path_region_B": float(np.nanmean(in_b)) if in_b.size else np.nan,
    }


def single_metrics(
    row: pd.Series,
    routes: list[dict[str, Any]],
    points: list[tuple[int, int]],
    baseline_points: list[tuple[int, int]],
    std_full: np.ndarray,
    descriptor_full: np.ndarray,
    info_full: np.ndarray,
    masks_full: dict[str, np.ndarray],
    valid_full: np.ndarray,
    diag: dict[str, Any],
    script_elapsed_s: float,
) -> dict[str, Any]:
    std_vals = c.sample_values(points, std_full, valid_full)
    desc_vals = c.sample_values(points, descriptor_full, valid_full)
    info_vals = c.sample_values(points, info_full, valid_full)
    top_std = c.threshold_top10(std_full, valid_full)
    top_desc = c.threshold_top10(descriptor_full, valid_full)
    overlap, diff = c.path_overlap_difference(points, baseline_points, valid_full)
    length, mission_duration = c.route_length_duration(routes)
    out = {
        **row.to_dict(),
        "solver_status": diag.get("solver_status", diag.get("status", "")),
        "solver_runtime": float(diag.get("solver_runtime_s", diag.get("runtime_s", np.nan))),
        "solver_gap": diag.get("solver_gap", np.nan),
        "solver_returncode": diag.get("returncode", np.nan),
        "run_dir": diag.get("run_dir", ""),
        "total_script_runtime": script_elapsed_s,
        "trajectory_length": length,
        "mission_duration": mission_duration,
        "number_of_valid_cells_sampled": len(c.unique_valid(points, valid_full)),
        "collected_STD": float(np.nansum(std_vals)) if std_vals.size else np.nan,
        "collected_descriptor": float(np.nansum(desc_vals)) if desc_vals.size else np.nan,
        "collected_information_score": float(np.nansum(info_vals)) if info_vals.size else np.nan,
        "percentage_path_in_top10_STD": float(np.mean(std_vals >= top_std)) if std_vals.size and math.isfinite(top_std) else np.nan,
        "percentage_path_in_top10_descriptor": float(np.mean(desc_vals >= top_desc)) if desc_vals.size and math.isfinite(top_desc) else np.nan,
        "trajectory_overlap_ratio_with_baseline": overlap,
        "path_difference_from_baseline": diff,
    }
    out.update(regime_metrics(points, masks_full, valid_full))
    return out


def summarize(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m = metrics.copy()
    for col in [
        "collected_STD",
        "collected_descriptor",
        "collected_information_score",
        "path_difference_from_baseline",
        "solver_runtime",
        "fraction_path_region_A",
        "fraction_path_region_B",
    ]:
        m[col] = pd.to_numeric(m[col], errors="coerce")
    baselines = (
        m[m["alpha"].eq(0)]
        .groupby(["case_id", "mission_duration_requested_h"], as_index=False)
        .agg(baseline_STD=("collected_STD", "max"), baseline_runtime=("solver_runtime", "max"))
    )
    m = m.merge(baselines, on=["case_id", "mission_duration_requested_h"], how="left")
    m["STD_retention"] = m["collected_STD"] / m["baseline_STD"]
    m["regime_balance"] = 2.0 * np.minimum(m["fraction_path_region_A"].fillna(0), m["fraction_path_region_B"].fillna(0))
    m["runtime_score"] = 1.0 / (1.0 + m["solver_runtime"].fillna(m["solver_runtime"].max()))
    m["recommendation_score"] = (
        0.35 * m["STD_retention"].fillna(0)
        + 0.20 * m["regime_balance"].fillna(0)
        + 0.20 * m.groupby(["case_id", "mission_duration_requested_h", "descriptor"])["collected_descriptor"].transform(lambda s: s / max(float(s.max()), 1e-9)).fillna(0)
        + 0.15 * m["path_difference_from_baseline"].clip(0, 1).fillna(0)
        + 0.10 * m["runtime_score"].fillna(0)
    )
    eligible = m[m["solver_status"].astype(str).isin(["SUCCESS", "REUSED"]) & (m["STD_retention"] >= 0.70)].copy()
    best = (
        eligible.sort_values(["case_id", "mission_duration_requested_h", "descriptor", "recommendation_score"], ascending=[True, True, True, False])
        .groupby(["case_id", "mission_duration_requested_h", "descriptor"], as_index=False)
        .head(1)
    )
    alpha_summary = (
        m.groupby(["descriptor", "alpha"], as_index=False)
        .agg(
            mean_STD=("collected_STD", "mean"),
            mean_descriptor=("collected_descriptor", "mean"),
            mean_difference=("path_difference_from_baseline", "mean"),
            mean_regime_balance=("regime_balance", "mean"),
            mean_runtime=("solver_runtime", "mean"),
            mean_score=("recommendation_score", "mean"),
        )
        .sort_values(["descriptor", "alpha"])
    )
    duration_summary = (
        m.groupby(["mission_duration_requested_h", "descriptor"], as_index=False)
        .agg(
            mean_STD=("collected_STD", "mean"),
            mean_difference=("path_difference_from_baseline", "mean"),
            mean_regime_balance=("regime_balance", "mean"),
            mean_runtime=("solver_runtime", "mean"),
            success_rate=("solver_status", lambda s: float(s.astype(str).isin(["SUCCESS", "REUSED"]).mean())),
        )
        .sort_values(["mission_duration_requested_h", "descriptor"])
    )
    runtime_summary = (
        m.groupby(["mission_duration_requested_h", "descriptor", "alpha"], as_index=False)
        .agg(mean_solver_runtime=("solver_runtime", "mean"), max_solver_runtime=("solver_runtime", "max"), runs=("physical_run_id", "nunique"))
    )
    return m, alpha_summary, duration_summary, runtime_summary, best


def create_figures(outdir: Path, metrics: pd.DataFrame, route_points: dict[str, list[tuple[int, int]]], cases: pd.DataFrame, maps: dict[str, np.ndarray], temp: np.ndarray, mask: np.ndarray) -> None:
    figdir = outdir / "figures"
    plotted_descriptors = [d for d in DESCRIPTORS if d in set(metrics["descriptor"].astype(str)) and DESCRIPTORS[d] in maps]
    for _, case in cases.iterrows():
        idx = int(case.case_order)
        case_id = str(case.case_id)
        std = maps["baseline_STD_norm"][idx]
        region_a, region_b = np.load(outdir / "masks" / f"{case_id}_region_A_mask.npy"), np.load(outdir / "masks" / f"{case_id}_region_B_mask.npy")
        for duration in sorted(metrics["mission_duration_requested_h"].dropna().unique()):
            for descriptor in plotted_descriptors:
                map_key = DESCRIPTORS[descriptor]
                sub = metrics[(metrics["case_id"].eq(case_id)) & (metrics["mission_duration_requested_h"].eq(duration)) & (metrics["descriptor"].eq(descriptor))].copy()
                if sub.empty:
                    continue
                paths = {str(r.run_name): route_points.get(str(r.physical_run_id), []) for r in sub.sort_values("alpha").itertuples()}
                desc = maps[map_key][idx]
                c.plot_paths_on_map(std, paths, figdir / f"step12a_{case_id}_{duration:g}h_{descriptor}_paths_over_STD_norm.png", f"{case_id} {duration:g}h {descriptor} paths over STD_norm", "viridis", 0, 1, region_a=region_a, region_b=region_b)
                c.plot_paths_on_map(desc, paths, figdir / f"step12a_{case_id}_{duration:g}h_{descriptor}_paths_over_descriptor_norm.png", f"{case_id} {duration:g}h {descriptor} paths over descriptor_norm", "magma", 0, 1, region_a=region_a, region_b=region_b)
                c.plot_paths_on_map(temp[idx], paths, figdir / f"step12a_{case_id}_{duration:g}h_{descriptor}_paths_over_TEMPpred_diagnostic.png", f"{case_id} {duration:g}h {descriptor} paths over TEMPpred diagnostic background", "coolwarm", None, None, diagnostic_note="TEMPpred is diagnostic background only; objective is information_map.", region_a=region_a, region_b=region_b)
                for r in sub.itertuples():
                    alpha = float(r.alpha)
                    info = std if alpha == 0 else c.normalize_map((1.0 - alpha) * std + alpha * desc, mask)
                    c.plot_paths_on_map(info, {str(r.run_name): route_points.get(str(r.physical_run_id), [])}, figdir / f"step12a_{case_id}_{duration:g}h_{descriptor}_{alpha_tag(alpha)}_path_over_real_information_map.png", f"{case_id} {duration:g}h {r.run_name} over real information_map", "viridis", 0, 1, region_a=region_a, region_b=region_b)
            plot_boundary_descriptor_comparison(figdir, metrics, route_points, case_id, idx, duration, maps, mask, region_a, region_b)
    plot_df = metrics.copy()
    plot_df["label"] = plot_df["case_id"].astype(str) + "_" + plot_df["mission_duration_requested_h"].astype(str) + "h"
    c.plot_grouped_bar(plot_df, "alpha", "collected_STD", "descriptor", figdir / "step12a_alpha_sensitivity_collected_STD.png", "Step12A alpha sensitivity: collected STD")
    c.plot_grouped_bar(plot_df, "mission_duration_requested_h", "collected_STD", "descriptor", figdir / "step12a_duration_sensitivity_collected_STD.png", "Step12A duration sensitivity: collected STD")
    c.plot_scatter(plot_df, "collected_STD", "collected_descriptor", "descriptor", figdir / "step12a_STD_vs_descriptor_tradeoff.png", "Step12A STD vs descriptor tradeoff")
    c.plot_scatter(plot_df, "solver_runtime", "collected_STD", "mission_duration_requested_h", figdir / "step12a_runtime_vs_STD.png", "Step12A runtime vs collected STD")


def plot_boundary_descriptor_comparison(
    figdir: Path,
    metrics: pd.DataFrame,
    route_points: dict[str, list[tuple[int, int]]],
    case_id: str,
    idx: int,
    duration: float,
    maps: dict[str, np.ndarray],
    mask: np.ndarray,
    region_a: np.ndarray,
    region_b: np.ndarray,
) -> None:
    comparison = [
        ("boundary_score", "boundary_score_norm", "old blended boundary_score"),
        ("boundary_distance_score_r3_cells", "boundary_distance_score_r3_cells_norm", "pure distance score r=3 cells"),
        ("interest_map", "interest_map_norm", "interest_map"),
    ]
    rows = []
    for descriptor, map_key, title in comparison:
        if map_key not in maps:
            continue
        sub = metrics[
            metrics["case_id"].eq(case_id)
            & metrics["mission_duration_requested_h"].eq(duration)
            & metrics["descriptor"].eq(descriptor)
            & metrics["alpha"].eq(0.50)
        ]
        if sub.empty:
            continue
        rows.append((descriptor, map_key, title, sub.iloc[0]))
    if len(rows) < 2:
        return
    fig, axes = c.plt.subplots(1, len(rows), figsize=(6.2 * len(rows), 4.8), squeeze=False)
    for ax, (descriptor, map_key, title, row) in zip(axes.ravel(), rows):
        desc = maps[map_key][idx]
        info = c.normalize_map(0.5 * maps["baseline_STD_norm"][idx] + 0.5 * desc, mask)
        im = ax.imshow(info, origin="lower", cmap="viridis", vmin=0, vmax=1, aspect="auto")
        ax.contour(region_a.astype(float), levels=[0.5], colors=["#2b6cb0"], linewidths=0.8, alpha=0.9)
        ax.contour(region_b.astype(float), levels=[0.5], colors=["#c53030"], linewidths=0.8, alpha=0.9)
        pts = c.route_to_roi(route_points.get(str(row["physical_run_id"]), []))
        if pts:
            ax.plot([p[1] for p in pts], [p[0] for p in pts], color="#00a9c8", lw=1.8, marker="o", markersize=1.8)
        ax.set_title(title)
        ax.set_xlabel("ROI column")
        ax.set_ylabel("ROI row")
        ax.set_xlim(-1, c.ROI_SHAPE[1])
        ax.set_ylim(-1, c.ROI_SHAPE[0])
        fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.suptitle(f"{case_id} {duration:g}h alpha050: old boundary vs pure distance vs interest over real information_map")
    fig.tight_layout()
    fig.savefig(figdir / f"step12a_{case_id}_{duration:g}h_boundary_distance_descriptor_comparison_alpha050.png", dpi=180)
    c.plt.close(fig)


def write_reports(outdir: Path, metrics: pd.DataFrame, alpha_summary: pd.DataFrame, duration_summary: pd.DataFrame, runtime_summary: pd.DataFrame, best: pd.DataFrame, checks: dict[str, Any]) -> None:
    lines = [
        "# Step12A single-AUV weight and duration sensitivity",
        "",
        f"- Verdict: `{checks['verdict']}`",
        f"- Physical planner runs: {checks['physical_runs_executed_or_reused']}",
        f"- Logical sensitivity rows: {checks['logical_rows']}",
        f"- Prototype-based maps only: {checks['prototype_based_maps_only']}",
        f"- TEMPpred used as objective: {checks['TEMPpred_used_as_objective']}",
        "",
        "## Best weight recommendation",
        c.md_table(best, ["case_id", "mission_duration_requested_h", "descriptor", "run_name", "alpha", "STD_retention", "regime_balance", "path_difference_from_baseline", "solver_runtime", "recommendation_score"], 50),
        "",
        "## Alpha sensitivity",
        c.md_table(alpha_summary, list(alpha_summary.columns), 50),
        "",
        "## Duration sensitivity",
        c.md_table(duration_summary, list(duration_summary.columns), 50),
        "",
        "## Interpretation",
        "- alpha=0 is the STD-only baseline.",
        "- alpha=1 is the pure descriptor extreme.",
        "- Recommended weights are selected only from successful runs with acceptable STD retention.",
        "- TEMPpred figures are diagnostic backgrounds; objective figures use the real information_map.",
    ]
    report = "\n".join(lines)
    c.write_text(outdir / "step12a_summary.md", report)
    c.write_text(outdir / "step12a_report.md", report + "\n\n## Runtime summary\n" + c.md_table(runtime_summary, list(runtime_summary.columns), 100))
    next_lines = [
        "# Step12A next step recommendation",
        "",
        "Use the best Step12A weights as single-AUV evidence, but treat Step12B as the stronger test for vehicle-specific regime roles.",
        "",
        "Recommended rows:",
        c.md_table(best, ["case_id", "mission_duration_requested_h", "descriptor", "run_name", "recommendation_score"], 50),
    ]
    c.write_text(outdir / "step12a_next_step_recommendation.md", "\n".join(next_lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step12A single-AUV weight and duration sensitivity.")
    parser.add_argument("--step11y", type=Path, default=None)
    parser.add_argument("--planner", type=Path, default=c.PLANNER)
    parser.add_argument("--output-root", type=Path, default=c.RESULTS)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--durations", nargs="*", type=float, default=DURATIONS)
    parser.add_argument("--cases", nargs="*", choices=c.CASE_ORDER, default=c.CASE_ORDER)
    parser.add_argument("--descriptors", nargs="*", choices=sorted(DESCRIPTORS), default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--workers", type=int, default=1, help="Number of independent planner runs to launch in parallel.")
    parser.add_argument("--resume-output", type=Path, default=None, help="Existing Step12A output folder to reuse with --skip-existing.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")
    if args.workers > 3:
        print("WARNING: --workers > 3 can overload CPU/RAM because each worker launches a planner process.")
    start = time.perf_counter()
    cases, maps, step11y = c.load_step11y_maps(args.step11y)
    cases = cases[cases["case_id"].isin(args.cases)].copy().reset_index(drop=True)
    available_descriptors = [name for name, key in DESCRIPTORS.items() if key in maps]
    missing_descriptors = [name for name, key in DESCRIPTORS.items() if key not in maps]
    if args.descriptors:
        unavailable_requested = [name for name in args.descriptors if DESCRIPTORS[name] not in maps]
        if unavailable_requested:
            raise KeyError(
                "Requested descriptors are not present in the selected Step11Y output. "
                f"Rerun Step08/Step11Y first or remove: {', '.join(unavailable_requested)}"
            )
        descriptor_names = list(args.descriptors)
    else:
        descriptor_names = available_descriptors
        if missing_descriptors:
            print(
                "WARNING: selected Step11Y output does not contain all Step12A descriptors; skipping unavailable descriptors: "
                + ", ".join(missing_descriptors)
            )
    if not descriptor_names:
        raise RuntimeError("No Step12A descriptors are available in the selected Step11Y output.")
    manifest = logical_manifest(cases, args.durations, descriptor_names)
    if args.dry_run:
        physical = manifest["physical_run_id"].nunique()
        print(f"Step12A dry-run: logical_rows={len(manifest)}, physical_planner_runs={physical}, workers={args.workers}, step11y={c.rel(step11y)}")
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
    manifest.to_csv(outdir / "step12a_run_manifest.csv", index=False)
    route_points_by_run: dict[str, list[tuple[int, int]]] = {}
    routes_by_run: dict[str, list[dict[str, Any]]] = {}
    diag_by_run: dict[str, dict[str, Any]] = {}

    for _, case in cases.iterrows():
        idx = int(case.case_order)
        case_id = str(case.case_id)
        region_a, region_b, region_meta = c.make_region_masks(ab, maps["cold_region_norm"][idx], maps["warm_region_norm"][idx], mask)
        np.save(outdir / "masks" / f"{case_id}_region_A_mask.npy", region_a)
        np.save(outdir / "masks" / f"{case_id}_region_B_mask.npy", region_b)
        c.write_json(outdir / "masks" / f"{case_id}_region_meta.json", region_meta)

    planner_tasks: list[dict[str, Any]] = []
    for duration in args.durations:
        config = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=duration, auv_number=1)
        (outdir / "planner_configs" / f"Config_file_step12a_1auv_{duration:g}h.py").write_text(config, encoding="utf-8")
        for _, case in cases.iterrows():
            idx = int(case.case_order)
            case_id = str(case.case_id)
            std = maps["baseline_STD_norm"][idx]
            physical_rows = manifest[(manifest["case_id"].eq(case_id)) & (manifest["mission_duration_requested_h"].eq(duration))].drop_duplicates("physical_run_id")
            for r in physical_rows.sort_values(["alpha", "descriptor"]).itertuples():
                alpha = float(r.alpha)
                if alpha == 0:
                    info = std
                else:
                    desc = maps[DESCRIPTORS[str(r.descriptor)]][idx]
                    info = c.normalize_map((1.0 - alpha) * std + alpha * desc, mask)
                planner_tasks.append({"run_id": str(r.physical_run_id), "info": info, "config": config})

    def execute_task(task: dict[str, Any]) -> tuple[str, dict[str, Any], list[dict[str, Any]], list[tuple[int, int]]]:
        diag, routes, _run_dir = c.run_planner(
            zutils,
            s11a,
            task["run_id"],
            task["info"],
            mask,
            lat_hres,
            lon_hres,
            bathy_hres,
            args.planner,
            task["config"],
            outdir,
            args.timeout_s,
            args.skip_existing,
        )
        return task["run_id"], diag, routes, c.route_points_all(s11a, routes, lat_hres, lon_hres)

    print(f"Step12A launching {len(planner_tasks)} physical planner runs with workers={args.workers}")
    if args.workers == 1:
        for task in planner_tasks:
            run_id, diag, routes, points = execute_task(task)
            diag_by_run[run_id] = diag
            routes_by_run[run_id] = routes
            route_points_by_run[run_id] = points
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(execute_task, task) for task in planner_tasks]
            for future in as_completed(futures):
                run_id, diag, routes, points = future.result()
                diag_by_run[run_id] = diag
                routes_by_run[run_id] = routes
                route_points_by_run[run_id] = points

    metric_rows = []
    for r in manifest.itertuples():
        case_id = str(r.case_id)
        idx = c.get_case_index(cases, case_id)
        descriptor = str(r.descriptor)
        physical_run_id = str(r.physical_run_id)
        baseline_run_id = f"{case_id}__single_auv_{float(r.mission_duration_requested_h):g}h__baseline_STD"
        alpha = float(r.alpha)
        std = maps["baseline_STD_norm"][idx]
        desc = maps[DESCRIPTORS[descriptor]][idx]
        info = std if alpha == 0 else c.normalize_map((1.0 - alpha) * std + alpha * desc, mask)
        std_full = s11a.embed_roi_to_hres(std, mask, fill=np.nan)
        desc_full = s11a.embed_roi_to_hres(desc, mask, fill=np.nan)
        info_full = s11a.embed_roi_to_hres(info, mask, fill=np.nan)
        region_a = np.load(outdir / "masks" / f"{case_id}_region_A_mask.npy")
        region_b = np.load(outdir / "masks" / f"{case_id}_region_B_mask.npy")
        masks_full = {
            "region_A_full": s11a.embed_roi_to_hres(region_a.astype(np.float32), mask, fill=np.nan) > 0.5,
            "region_B_full": s11a.embed_roi_to_hres(region_b.astype(np.float32), mask, fill=np.nan) > 0.5,
        }
        metric_rows.append(
            single_metrics(
                pd.Series(r._asdict()),
                routes_by_run.get(physical_run_id, []),
                route_points_by_run.get(physical_run_id, []),
                route_points_by_run.get(baseline_run_id, []),
                std_full,
                desc_full,
                info_full,
                masks_full,
                valid_full,
                diag_by_run.get(physical_run_id, {}),
                time.perf_counter() - start,
            )
        )

    metrics_raw = pd.DataFrame(metric_rows)
    metrics, alpha_summary, duration_summary, runtime_summary, best = summarize(metrics_raw)
    diagnostics = pd.DataFrame(diag_by_run.values())
    metrics.to_csv(outdir / "step12a_single_auv_metrics.csv", index=False)
    alpha_summary.to_csv(outdir / "step12a_alpha_sensitivity_summary.csv", index=False)
    duration_summary.to_csv(outdir / "step12a_duration_sensitivity_summary.csv", index=False)
    runtime_summary.to_csv(outdir / "step12a_runtime_summary.csv", index=False)
    diagnostics.to_csv(outdir / "step12a_solver_diagnostics.csv", index=False)
    best.to_csv(outdir / "step12a_best_weight_recommendation.csv", index=False)

    create_figures(outdir, metrics, route_points_by_run, cases, maps, temp, mask)
    checks = {
        "step": "Step12A",
        "output_dir": c.rel(outdir),
        "step11y": c.rel(step11y),
        "logical_rows": int(len(manifest)),
        "physical_runs_executed_or_reused": int(manifest["physical_run_id"].nunique()),
        "workers": int(args.workers),
        "resume_output": c.rel(outdir) if args.resume_output else "",
        "durations_tested": sorted([float(x) for x in metrics["mission_duration_requested_h"].dropna().unique()]),
        "alphas_tested": sorted([float(x) for x in metrics["alpha"].dropna().unique()]),
        "descriptors_tested": sorted(metrics["descriptor"].dropna().astype(str).unique().tolist()),
        "available_descriptors": sorted(available_descriptors),
        "missing_descriptors": sorted(missing_descriptors),
        "prototype_based_maps_only": True,
        "TEMPpred_used_as_objective": False,
        "all_runs_have_status": bool(metrics["solver_status"].astype(str).ne("").all()),
        "all_runtimes_recorded": bool(pd.to_numeric(metrics["solver_runtime"], errors="coerce").notna().all()),
        "figures_created": len(list((outdir / "figures").glob("*.png"))),
        "total_script_runtime_s": float(time.perf_counter() - start),
        "verdict": "STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED" if not best.empty else "STEP12_COMPLETED_WITH_TRADEOFFS_REVIEW_REQUIRED",
    }
    c.write_json(outdir / "step12a_checks.json", checks)
    c.write_json(
        outdir / "step12a_metadata.json",
        {
            "created_at": c.now_tag(),
            "inputs": {"step11y": c.rel(step11y), "step10f": c.rel(c.STEP10F)},
            "descriptor_map_keys": {name: DESCRIPTORS[name] for name in descriptor_names},
            "boundary_distance_note": "boundary_distance_score_r*_cells_norm maps are pure prototype-based boundary proximity scores when present in Step11Y.",
        },
    )
    write_reports(outdir, metrics, alpha_summary, duration_summary, runtime_summary, best, checks)
    print(f"Step12A complete: {c.rel(outdir)}")
    print(f"Verdict: {checks['verdict']}")
    print(f"Logical rows: {checks['logical_rows']}; physical runs: {checks['physical_runs_executed_or_reused']}; figures: {checks['figures_created']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
