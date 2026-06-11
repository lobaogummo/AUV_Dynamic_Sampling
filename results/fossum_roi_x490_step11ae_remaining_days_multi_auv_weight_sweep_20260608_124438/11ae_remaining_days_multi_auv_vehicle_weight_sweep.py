#!/usr/bin/env python
"""Step11AE: multi-AUV vehicle-specific weight sweep for remaining days.

Runs the Step11AB multi-AUV experiment pattern for:
- C06_representative / 2023-12-22
- October_control / 2024-10-30

It uses Step11Y prototype-based maps only. Existing Step11Z baseline and
0.6/0.4 vehicle-specific routes are reused where available; missing configs are
run with the planner. Figures use one panel per method over each day's TEMPpred.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
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
DEFAULT_STEP11Z = RESULTS / "fossum_roi_x490_step11z_minimal_prototype_based_rerun_20260525_220614"
CASES = ["C06_representative", "October_control"]
ROI_ROW_MIN = 55
ROI_COL_MIN = 47
ROI_SHAPE = (72, 117)


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
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
    out[valid] = 0.0 if hi <= lo else np.clip((arr[valid] - lo) / (hi - lo), 0, 1)
    return out


def load_mask_and_temp(step10f_dir: Path = STEP10F) -> tuple[dict[str, int], np.ndarray, np.ndarray]:
    z = np.load(step10f_dir / "planner_minimal_boundary_input_maps.npz", allow_pickle=True)
    case_ids = [str(x) for x in z["case_ids"]]
    mask = np.asarray(z["mask"], dtype=bool)
    return {case: i for i, case in enumerate(case_ids)}, np.asarray(z["TEMPpred"], dtype=np.float32), mask


def parse_routes(route_json: Path) -> list[dict[str, Any]]:
    if not route_json.exists():
        return []
    return json.loads(route_json.read_text(encoding="utf-8")).get("routes", [])


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 40) -> str:
    if df.empty:
        return "_No data available._\n"
    view = df[[c for c in cols if c in df.columns]].head(max_rows).copy()
    for c in view.columns:
        if pd.api.types.is_numeric_dtype(view[c]):
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else f"{float(x):.3f}")
        else:
            view[c] = view[c].fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join("---" for _ in view.columns) + " |"]
    for row in view.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines) + "\n"


def plot_case_panel(case_id: str, date: str, temp: np.ndarray, panels: list[dict[str, Any]], out: Path, region_a: np.ndarray, region_b: np.ndarray) -> None:
    ncols = 3
    nrows = int(np.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.8 * ncols, 4.25 * nrows), squeeze=False)
    vmin = float(np.nanpercentile(temp, 2))
    vmax = float(np.nanpercentile(temp, 98))
    im = None
    for ax in axes.ravel():
        ax.axis("off")
    for ax, panel in zip(axes.ravel(), panels):
        im = ax.imshow(temp, origin="lower", aspect="auto", cmap="coolwarm", vmin=vmin, vmax=vmax)
        ax.contour(region_a.astype(float), levels=[0.5], colors=["#2b6cb0"], linewidths=0.75, alpha=0.85)
        ax.contour(region_b.astype(float), levels=[0.5], colors=["#c53030"], linewidths=0.75, alpha=0.85)
        for label, pts_full, color in panel["paths"]:
            pts = [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in pts_full]
            if pts:
                ax.plot([p[1] for p in pts], [p[0] for p in pts], color=color, marker="o", markersize=2, linewidth=1.6, label=label)
        ax.text(0.015, 0.02, "\n".join(panel["metrics"]), transform=ax.transAxes, fontsize=8, bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none", "pad": 3}, va="bottom")
        ax.set_title(panel["title"], fontsize=10)
        ax.set_xlim(-1, ROI_SHAPE[1])
        ax.set_ylim(-1, ROI_SHAPE[0])
        ax.set_xlabel("ROI column")
        ax.set_ylabel("ROI row")
        ax.legend(fontsize=7, loc="upper right")
        ax.axis("on")
    fig.suptitle(f"{case_id} multi-AUV methods over day-specific predModel TEMPpred ({date})", fontsize=15)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.025, pad=0.012)
        cbar.set_label("TEMPpred, degC")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11AE remaining-days multi-AUV vehicle weight sweep.")
    parser.add_argument("--step11y", type=Path, default=DEFAULT_STEP11Y)
    parser.add_argument("--step11z", type=Path, default=DEFAULT_STEP11Z)
    parser.add_argument("--step10f-dir", type=Path, default=STEP10F)
    parser.add_argument("--planner", type=Path, default=PLANNER)
    parser.add_argument("--output-root", type=Path, default=RESULTS)
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--resume-output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    zutils = load_module("step11z_utils", SCRIPTS / "11z_rerun_minimal_prototype_based_planner_tests.py")
    ab = load_module("step11ab_utils", SCRIPTS / "11ab_c01_region_target_and_vehicle_weight_sweep.py")
    ab.STEP10F = args.step10f_dir
    s11a = zutils.load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")

    outdir = args.resume_output.resolve() if args.resume_output else args.output_root.resolve() / f"fossum_roi_x490_step11ae_remaining_days_multi_auv_weight_sweep_{now_tag()}"
    for sub in ["planner_inputs", "planner_runs", "planner_configs", "figures", "masks"]:
        (outdir / sub).mkdir(parents=True, exist_ok=True)

    cases, maps = zutils.load_cases_and_maps(args.step11y)
    cases = cases[cases["case_id"].isin(CASES)].copy().reset_index(drop=True)
    case_idx_10f, temp_all, mask = load_mask_and_temp(args.step10f_dir)
    lat_hres = np.load(HRES / "LAT_hres.npy")
    lon_hres = np.load(HRES / "LON_hres.npy")
    bathy_hres = np.load(HRES / "BATHY_hres.npy")
    valid_full = s11a.embed_roi_to_hres(mask.astype(np.float32), mask, fill=np.nan) > 0.5

    original_config = s11a.read_config_text(args.planner / "Config_file.py")
    config_1auv = s11a.generated_config(original_config, single_auv=True, mission_duration_hours=12.0, auv_number=1)
    config_2auv = s11a.generated_config(original_config, single_auv=False, mission_duration_hours=12.0, auv_number=2)
    (outdir / "planner_configs" / "Config_file_step11ae_1auv_12h.py").write_text(config_1auv, encoding="utf-8")
    (outdir / "planner_configs" / "Config_file_step11ae_2auv_12h.py").write_text(config_2auv, encoding="utf-8")

    configs = {
        "vehicle_specific_conservative": (0.8, 0.2),
        "vehicle_specific_balanced": (0.7, 0.3),
        "vehicle_specific_strong_regime": (0.6, 0.4),
    }
    manifest_rows: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    vehicle_rows: list[dict[str, Any]] = []
    multi_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    def reused_routes(case_id: str, suffix: str) -> tuple[list[dict[str, Any]], Path]:
        run_id = f"{case_id}__multi_auv_12h__{suffix}"
        run_dir = args.step11z / "planner_runs" / zutils.short_name(run_id)
        return parse_routes(run_dir / "trajectory_routes.json"), run_dir

    for _, case in cases.iterrows():
        case_id = str(case["case_id"])
        date = str(case["date"])
        idx = int(case["case_order"])
        std = maps["baseline_STD_norm"][idx]
        boundary = maps["boundary_score_norm"][idx]
        cold = maps["cold_region_norm"][idx]
        warm = maps["warm_region_norm"][idx]
        boundary_alpha050 = maps["enriched_boundary_alpha050"][idx]
        region_a, region_b, region_meta = ab.descriptor_region_masks(cold, warm, mask)
        core = zutils.boundary_core(boundary, mask)
        np.save(outdir / "masks" / f"{case_id}_region_A_mask.npy", region_a)
        np.save(outdir / "masks" / f"{case_id}_region_B_mask.npy", region_b)
        np.save(outdir / "masks" / f"{case_id}_boundary_core_mask.npy", core)
        maps_full = {"STD_full": s11a.embed_roi_to_hres(std, mask, fill=np.nan), "boundary_full": s11a.embed_roi_to_hres(boundary, mask, fill=np.nan)}
        masks_full = {
            "region_A_full": s11a.embed_roi_to_hres(region_a.astype(np.float32), mask, fill=np.nan) > 0.5,
            "region_B_full": s11a.embed_roi_to_hres(region_b.astype(np.float32), mask, fill=np.nan) > 0.5,
            "boundary_core_full": s11a.embed_roi_to_hres(core.astype(np.float32), mask, fill=np.nan) > 0.5,
        }
        info_maps: dict[str, np.ndarray] = {
            f"{case_id}__baseline_STD": std,
            f"{case_id}__prototype_boundary_alpha050": boundary_alpha050,
        }
        for name, (w_std, w_reg) in configs.items():
            info_maps[f"{case_id}__{name}_AUV1"] = normalize_map(w_std * std + w_reg * cold, mask)
            info_maps[f"{case_id}__{name}_AUV2"] = normalize_map(w_std * std + w_reg * warm, mask)
        np.savez_compressed(outdir / f"{case_id}_step11ae_information_maps.npz", **info_maps)

        route_points_by_strategy: dict[str, dict[int, list[tuple[int, int]]]] = {}

        # Reuse Step11Z baseline native 2-AUV route.
        routes, source_dir = reused_routes(case_id, "baseline_STD")
        diag_status = "REUSED_STEP11Z" if routes else "MISSING_STEP11Z_REUSE"
        if not routes:
            warnings.append(f"{case_id} baseline reuse missing; running planner.")
            diag, routes, source_dir = zutils.run_planner_case(s11a, f"{case_id}__multi_auv_12h__baseline_STD", std, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_2auv, outdir, args.timeout_s, args.skip_existing)
            solver_rows.append(diag)
            diag_status = str(diag.get("status", ""))
        vehicle_points = {}
        vrows = []
        for vid, route in enumerate(routes[:2], start=1):
            pts = zutils.route_points(s11a, [route], lat_hres, lon_hres)
            vehicle_points[vid] = pts
            vrows.append(zutils.vehicle_metrics(f"{case_id}__multi_auv_12h__baseline_STD", "baseline_STD", case_id, vid, pts, route, maps_full, masks_full, valid_full, diag_status))
        vdf = pd.DataFrame(vrows)
        vehicle_rows.extend(vrows)
        route_points_by_strategy["baseline_STD"] = vehicle_points
        mrow = zutils.fleet_metrics(f"{case_id}__multi_auv_12h__baseline_STD", "baseline_STD", case_id, vehicle_points, vdf, masks_full, valid_full, diag_status, 0.0)
        mrow["formulation"] = "native 2-AUV shared STD; reused from Step11Z when available"
        mrow["source"] = rel(source_dir)
        multi_rows.append(mrow)
        manifest_rows.append({**mrow, "scope": "multi_AUV_native_shared", "run_dir": rel(source_dir)})

        # Run boundary native 2-AUV.
        run_id = f"{case_id}__multi_auv_12h__prototype_boundary_alpha050"
        diag, routes, run_dir = zutils.run_planner_case(s11a, run_id, boundary_alpha050, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_2auv, outdir, args.timeout_s, args.skip_existing)
        solver_rows.append(diag)
        vehicle_points = {}
        vrows = []
        for vid, route in enumerate(routes[:2], start=1):
            pts = zutils.route_points(s11a, [route], lat_hres, lon_hres)
            vehicle_points[vid] = pts
            vrows.append(zutils.vehicle_metrics(run_id, "prototype_boundary_alpha050", case_id, vid, pts, route, maps_full, masks_full, valid_full, str(diag.get("status", ""))))
        vdf = pd.DataFrame(vrows)
        vehicle_rows.extend(vrows)
        route_points_by_strategy["prototype_boundary_alpha050"] = vehicle_points
        mrow = zutils.fleet_metrics(run_id, "prototype_boundary_alpha050", case_id, vehicle_points, vdf, masks_full, valid_full, str(diag.get("status", "")), float(diag.get("runtime_s", np.nan)))
        mrow["formulation"] = "native 2-AUV shared 0.5*STD + 0.5*prototype_boundary"
        mrow["source"] = rel(run_dir)
        multi_rows.append(mrow)
        manifest_rows.append({**mrow, "scope": "multi_AUV_native_shared", "run_dir": rel(run_dir), "input_nc": diag.get("input_nc", "")})

        # Vehicle-specific proxy runs.
        for strategy, (w_std, w_reg) in configs.items():
            vehicle_points = {}
            vrows = []
            runtime_total = 0.0
            statuses = []
            source_dirs = []
            for vid in [1, 2]:
                if strategy == "vehicle_specific_strong_regime":
                    reuse_id = f"{case_id}__multi_auv_12h__prototype_vehicle_specific_maps__AUV{vid}"
                    source_dir = args.step11z / "planner_runs" / zutils.short_name(reuse_id)
                    routes = parse_routes(source_dir / "trajectory_routes.json")
                    status = "REUSED_STEP11Z" if routes else "MISSING_STEP11Z_REUSE"
                    if not routes:
                        warnings.append(f"{reuse_id} missing; running strong-regime proxy.")
                        info = info_maps[f"{case_id}__{strategy}_AUV{vid}"]
                        diag, routes, source_dir = zutils.run_planner_case(s11a, f"{case_id}__multi_auv_12h__{strategy}__AUV{vid}", info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_1auv, outdir, args.timeout_s, args.skip_existing)
                        solver_rows.append(diag)
                        runtime_total += float(diag.get("runtime_s", 0.0) or 0.0)
                        status = str(diag.get("status", ""))
                else:
                    info = info_maps[f"{case_id}__{strategy}_AUV{vid}"]
                    run_id = f"{case_id}__multi_auv_12h__{strategy}__AUV{vid}"
                    diag, routes, source_dir = zutils.run_planner_case(s11a, run_id, info, mask, lat_hres, lon_hres, bathy_hres, args.planner, config_1auv, outdir, args.timeout_s, args.skip_existing)
                    solver_rows.append(diag)
                    runtime_total += float(diag.get("runtime_s", 0.0) or 0.0)
                    status = str(diag.get("status", ""))
                statuses.append(status)
                source_dirs.append(rel(source_dir))
                route = routes[0] if routes else None
                pts = zutils.route_points(s11a, [route], lat_hres, lon_hres) if route else []
                vehicle_points[vid] = pts
                vrows.append(zutils.vehicle_metrics(f"{case_id}__multi_auv_12h__{strategy}__AUV{vid}", strategy, case_id, vid, pts, route, maps_full, masks_full, valid_full, status))
            vdf = pd.DataFrame(vrows)
            vehicle_rows.extend(vrows)
            route_points_by_strategy[strategy] = vehicle_points
            status = "SUCCESS" if all(s in ["SUCCESS", "REUSED_STEP11Z", "REUSED"] for s in statuses) else "FAILED_OR_PARTIAL"
            mrow = zutils.fleet_metrics(f"{case_id}__multi_auv_12h__{strategy}", strategy, case_id, vehicle_points, vdf, masks_full, valid_full, status, runtime_total)
            mrow["formulation"] = f"proxy pair: AUV1={w_std:.1f}*STD+{w_reg:.1f}*region_A; AUV2={w_std:.1f}*STD+{w_reg:.1f}*region_B"
            mrow["std_weight"] = w_std
            mrow["region_weight"] = w_reg
            mrow["source"] = "; ".join(source_dirs)
            multi_rows.append(mrow)
            manifest_rows.append({**mrow, "scope": "multi_AUV_vehicle_specific_proxy", "run_dir": "; ".join(source_dirs)})

        # Figure for this case.
        case_multi = pd.DataFrame([r for r in multi_rows if r["case_id"] == case_id])
        panels = []
        for _, row in case_multi.iterrows():
            strategy = str(row["strategy"])
            paths = []
            for vid, pts in route_points_by_strategy.get(strategy, {}).items():
                paths.append((f"AUV{vid}", pts, "white" if int(vid) == 1 else "yellow"))
            v = pd.DataFrame([r for r in vehicle_rows if r["case_id"] == case_id and r["strategy"] == strategy])
            spec = []
            if "vehicle_id" in v.columns:
                for vid in [1, 2]:
                    vv = v[v["vehicle_id"].eq(vid)]
                    if not vv.empty:
                        spec.append(f"AUV{vid}: A={float(vv.iloc[0]['fraction_path_region_A']):.2f}, B={float(vv.iloc[0]['fraction_path_region_B']):.2f}")
            panels.append(
                {
                    "title": strategy,
                    "paths": paths,
                    "metrics": [
                        f"Bcov={float(row['fleet_region_B_coverage']):.3f}, STD={float(row['fleet_collected_STD']):.1f}",
                        f"overlap={float(row['trajectory_overlap_ratio']):.3f}, meanD={float(row['inter_vehicle_mean_distance']):.1f}",
                        *spec,
                    ],
                }
            )
        plot_case_panel(case_id, date, temp_all[case_idx_10f[case_id]], panels, outdir / "figures" / f"step11ae_{case_id}_multi_auv_predmodel_panel_by_method.png", region_a, region_b)

    multi_df = pd.DataFrame(multi_rows)
    vehicle_df = pd.DataFrame(vehicle_rows)
    manifest_df = pd.DataFrame(manifest_rows)
    solver_df = pd.DataFrame(solver_rows)
    multi_df.to_csv(outdir / "step11ae_multi_auv_metrics.csv", index=False)
    vehicle_df.to_csv(outdir / "step11ae_vehicle_metrics.csv", index=False)
    manifest_df.to_csv(outdir / "step11ae_run_manifest.csv", index=False)
    solver_df.to_csv(outdir / "step11ae_solver_diagnostics.csv", index=False)

    recommendations = []
    for case_id, grp in multi_df.groupby("case_id", sort=False):
        baseline = grp[grp["strategy"].eq("baseline_STD")].iloc[0]
        baseline_b = float(baseline["fleet_region_B_coverage"])
        baseline_std = float(baseline["fleet_collected_STD"])
        baseline_overlap = float(baseline["trajectory_overlap_ratio"])
        cand = grp[grp["strategy"].astype(str).str.startswith("vehicle_specific")].copy()
        cand["std_retained"] = cand["fleet_collected_STD"].astype(float) / max(baseline_std, 1e-9)
        cand["B_gain"] = cand["fleet_region_B_coverage"].astype(float) / max(baseline_b, 1e-9)
        acceptable = cand[(cand["B_gain"] >= 2.0) & (cand["std_retained"] >= 0.85) & (cand["trajectory_overlap_ratio"].astype(float) <= baseline_overlap + 0.03)]
        if not acceptable.empty:
            best = acceptable.iloc[0]
            rule = "meets 2x B coverage, >=85% STD, low overlap"
        else:
            best = cand.sort_values(["B_gain", "std_retained"], ascending=False).iloc[0]
            rule = "best available tradeoff; criteria not fully met"
        recommendations.append({"case_id": case_id, "recommended_strategy": best["strategy"], "B_gain": best["B_gain"], "std_retained": best["std_retained"], "selection_rule": rule})
    rec_df = pd.DataFrame(recommendations)
    rec_df.to_csv(outdir / "step11ae_recommendations.csv", index=False)

    failures = solver_df[~solver_df.get("status", pd.Series(dtype=str)).astype(str).isin(["SUCCESS", "REUSED", "REUSED_STEP11Z"])] if not solver_df.empty else pd.DataFrame()
    if len(failures):
        warnings.append(f"{len(failures)} planner runs failed/timed out.")
    verdict = "STEP11AE_REMAINING_DAYS_MULTI_AUV_COMPLETED" if not warnings else "STEP11AE_COMPLETED_WITH_WARNINGS"
    checks = {
        "verdict": verdict,
        "output_dir": rel(outdir),
        "cases": CASES,
        "prototype_maps_only": True,
        "TEMPpred_used_for_regions": False,
        "step11z_reuse": True,
        "multi_rows": int(len(multi_df)),
        "vehicle_rows": int(len(vehicle_df)),
        "planner_runs_executed": int(len(solver_df)),
        "figures_created": len(list((outdir / "figures").glob("*.png"))),
        "warnings": warnings,
    }
    write_json(outdir / "step11ae_checks.json", checks)
    write_json(
        outdir / "step11ae_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": rel(Path(__file__)),
            "step11y": rel(args.step11y),
            "step11z_reused": rel(args.step11z),
            "step10f": rel(args.step10f_dir),
            "planner": rel(args.planner),
        },
    )
    report = [
        "# Step11AE remaining-days multi-AUV vehicle sweep",
        "",
        f"- Verdict: `{verdict}`",
        f"- Cases: {', '.join(CASES)}",
        f"- Planner runs executed: {len(solver_df)}",
        f"- Existing Step11Z routes reused: yes",
        "",
        "## Multi-AUV metrics",
        md_table(multi_df, ["case_id", "strategy", "solver_status", "fleet_region_A_coverage", "fleet_region_B_coverage", "fleet_collected_STD", "trajectory_overlap_ratio", "inter_vehicle_mean_distance", "complementarity_score"], 20),
        "",
        "## Recommendations",
        md_table(rec_df, ["case_id", "recommended_strategy", "B_gain", "std_retained", "selection_rule"], 10),
        "",
        "## Visual interpretation",
        "",
        "- Use `figures/step11ae_*_multi_auv_predmodel_panel_by_method.png`.",
        "- Each method is in its own panel over that day's TEMPpred predModel.",
        "- Region maps are contours only; they are not the background.",
    ]
    if warnings:
        report += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    (outdir / "step11ae_report.md").write_text("\n".join(report), encoding="utf-8")
    (outdir / "step11ae_summary.md").write_text("\n".join(report), encoding="utf-8")
    shutil.copy2(Path(__file__), outdir / Path(__file__).name)

    print("STEP11AE REMAINING-DAYS MULTI-AUV SWEEP")
    print(f"Output: {rel(outdir)}")
    print(f"Cases: {', '.join(CASES)}")
    print(f"Planner runs executed: {len(solver_df)}")
    print(f"Figures: {len(list((outdir / 'figures').glob('*.png')))}")
    print(f"Warnings: {len(warnings)}")
    print(f"Verdict: {verdict}")
    return 0 if "WARNINGS" not in verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
